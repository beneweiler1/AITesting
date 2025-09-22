from fastapi import APIRouter, HTTPException, Response
from ..db import list_files_meta, file_blob

router = APIRouter(prefix="/files")

@router.get("")
def files():
    return {"files": list_files_meta()}

@router.get("/{fid}/inline")
def file_inline(fid: int):
    r = file_blob(fid)
    if not r:
        raise HTTPException(status_code=404, detail="not found")
    fname, ctype, data = r
    return Response(content=data, media_type=ctype or "application/octet-stream", headers={"Content-Disposition": f'inline; filename="{fname}"'})
