import httpx
from typing import Any, Dict, Tuple
from urllib.parse import urljoin, quote
import re

PATH_VAR = re.compile(r"\{([^}/]+)\}")

def _expand_path(path: str, args: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    remaining = dict(args)
    def repl(m):
        key = m.group(1)
        if key not in remaining:
            raise ValueError(f"Missing path parameter: {key}")
        val = remaining.pop(key)
        return quote(str(val), safe="")
    expanded = PATH_VAR.sub(repl, path)
    return expanded, remaining

def _normalize_query(params: Dict[str, Any]) -> Dict[str, Any]:
    q: Dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            q[k] = ",".join(str(x) for x in v)
        else:
            q[k] = v
    return q

def call_swagger_tool(tool: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    base = tool.get("x-mcp", {}).get("base_url", "")
    path_tmpl = tool.get("x-mcp", {}).get("path", "")
    method = tool.get("x-mcp", {}).get("method", "GET").upper()

    try:
        path, leftover = _expand_path(path_tmpl, args or {})
    except ValueError as e:
        return {"status_code": 400, "error": str(e), "url": f"{base}{path_tmpl}"}

    url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    params = _normalize_query({k: v for k, v in leftover.items() if k != "body"})
    body = leftover.get("body")

    print("\n=== MCP TOOL CALL ===")
    print(f"Method: {method}")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"Body: {body}\n")

    headers = {"accept": "application/json"}
    with httpx.Client(timeout=30.0) as client:
        if method == "GET":
            r = client.get(url, params=params, headers=headers)
        elif method == "POST":
            r = client.post(url, params=params, json=body, headers=headers)
        elif method == "PUT":
            r = client.put(url, params=params, json=body, headers=headers)
        elif method == "PATCH":
            r = client.patch(url, params=params, json=body, headers=headers)
        elif method == "DELETE":
            r = client.delete(url, params=params, headers=headers)
        else:
            r = client.get(url, params=params, headers=headers)

    print(f"Response Status: {r.status_code}")
    print(f"Response Text: {r.text[:400]}...\n")

    return {"status_code": r.status_code, "data": _safe_json(r), "url": url}

def _safe_json(r: httpx.Response):
    try:
        return r.json()
    except Exception:
        return {"text": r.text}
