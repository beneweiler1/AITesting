from typing import Dict, Any, List
from urllib.parse import urlparse, urljoin
import httpx

def _origin(u: str) -> str:
    p = urlparse(u)
    if not p.scheme or not p.netloc:
        return ""
    return f"{p.scheme}://{p.netloc}"

def _mk_params_schema() -> Dict[str, Any]:
    return {"type": "object", "properties": {}, "required": []}

def _tool(name: str, desc: str, params: Dict[str, Any], base: str, path: str, method: str) -> Dict[str, Any]:
    return {"name": name, "description": desc, "parameters": params, "x-mcp": {"base_url": base, "path": path, "method": method}}

def _param_schema_from_v2(p: Dict[str, Any]) -> Dict[str, Any]:
    if p.get("schema"):
        return p["schema"]
    t = (p.get("type") or "string").lower()
    if t == "array":
        items = p.get("items") or {}
        itype = (items.get("type") or "string").lower()
        s = {"type": "array", "items": {"type": itype}}
        if "enum" in items:
            s["items"]["enum"] = items["enum"]
        return s
    s = {"type": t}
    if "enum" in p:
        s["enum"] = p["enum"]
    return s

def _param_schema_from_v3(p: Dict[str, Any]) -> Dict[str, Any]:
    sch = p.get("schema")
    if sch:
        if sch.get("type") == "array" and "items" not in sch:
            sch = {"type": "array", "items": {"type": "string"}}
        return sch
    t = (p.get("type") or "string").lower()
    if t == "array":
        return {"type": "array", "items": {"type": "string"}}
    return {"type": t}

def _parse_oas3(spec: Dict[str, Any], spec_url: str) -> List[Dict[str, Any]]:
    servers = spec.get("servers", [{}])
    server_url = servers[0].get("url", "") if servers else ""
    base_origin = _origin(spec_url)
    if server_url.startswith("http://") or server_url.startswith("https://"):
        resolved_base = server_url
    else:
        resolved_base = urljoin(base_origin + "/", server_url.lstrip("/")) if server_url else base_origin
    out: List[Dict[str, Any]] = []
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, op in methods.items():
            if method.upper() not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                continue
            name = op.get("operationId") or f"{method}_{path}".replace("/", "_").replace("{", "_").replace("}", "")
            desc = op.get("description") or op.get("summary") or f"Call {method.upper()} {path}"
            params = _mk_params_schema()
            for p in op.get("parameters", []):
                pname = p.get("name")
                pschema = _param_schema_from_v3(p)
                params["properties"][pname] = pschema
                if p.get("required"):
                    params["required"].append(pname)
            body = op.get("requestBody", {})
            if body:
                content = body.get("content", {})
                if "application/json" in content:
                    js = content["application/json"].get("schema") or {"type": "object"}
                    if js.get("type") == "array" and "items" not in js:
                        js = {"type": "array", "items": {"type": "string"}}
                    params["properties"]["body"] = js
                    params["required"].append("body")
            out.append(_tool(name, desc, params, resolved_base, path, method.upper()))
    return out

def _parse_swagger2(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    scheme = (spec.get("schemes") or ["https"])[0]
    host = spec.get("host", "")
    base_path = spec.get("basePath", "")
    resolved_base = f"{scheme}://{host}{base_path}"
    out: List[Dict[str, Any]] = []
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, op in methods.items():
            if method.upper() not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                continue
            name = op.get("operationId") or f"{method}_{path}".replace("/", "_").replace("{", "_").replace("}", "")
            desc = op.get("description") or op.get("summary") or f"Call {method.upper()} {path}"
            params = _mk_params_schema()
            for p in op.get("parameters", []):
                pname = p.get("name")
                pschema = _param_schema_from_v2(p)
                params["properties"][pname] = pschema
                if p.get("required"):
                    params["required"].append(pname)
            out.append(_tool(name, desc, params, resolved_base, path, method.upper()))
    return out

def _fetch_json(url: str) -> Dict[str, Any]:
    with httpx.Client(timeout=30) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.json()

def _parse_swagger12(spec: Dict[str, Any], spec_url: str) -> List[Dict[str, Any]]:
    base = spec.get("basePath") or _origin(spec_url)
    apis = spec.get("apis", [])
    out: List[Dict[str, Any]] = []
    for a in apis:
        apipath = a.get("path", "")
        decl = None
        if a.get("operations"):
            decl = a
        else:
            base_for_decl = _origin(spec_url)
            cand = urljoin(base_for_decl + "/", apipath.lstrip("/"))
            try:
                decl = _fetch_json(cand)
            except Exception:
                continue
        ops = decl.get("operations") or []
        path_for_ops = decl.get("path") or apipath
        for op in ops:
            method = (op.get("method") or op.get("httpMethod") or "").upper()
            if method not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                continue
            name = op.get("nickname") or f"{method}_{path_for_ops}".replace("/", "_").replace("{", "_").replace("}", "")
            desc = op.get("summary") or op.get("notes") or f"Call {method} {path_for_ops}"
            params = _mk_params_schema()
            for p in op.get("parameters", []):
                pname = p.get("name")
                t = (p.get("type") or "string").lower()
                if t == "array":
                    items = p.get("items") or {"type": "string"}
                    itype = (items.get("type") or "string").lower()
                    s = {"type": "array", "items": {"type": itype}}
                    if "enum" in items:
                        s["items"]["enum"] = items["enum"]
                else:
                    s = {"type": t}
                    if "enum" in p:
                        s["enum"] = p["enum"]
                params["properties"][pname] = s
                if p.get("required"):
                    params["required"].append(pname)
            out.append(_tool(name, desc, params, base, path_for_ops, method))
    return out

def openapi_to_mcp(spec: Dict[str, Any], spec_url: str) -> List[Dict[str, Any]]:
    if "openapi" in spec:
        return _parse_oas3(spec, spec_url)
    if "swagger" in spec and str(spec.get("swagger", "")).startswith("2"):
        return _parse_swagger2(spec)
    if "swaggerVersion" in spec and str(spec.get("swaggerVersion", "")).startswith("1"):
        return _parse_swagger12(spec, spec_url)
    return _parse_oas3(spec, spec_url)
