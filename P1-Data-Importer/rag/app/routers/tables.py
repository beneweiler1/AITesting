from fastapi import APIRouter, HTTPException
from ..db import list_tables, get_table_schema

router = APIRouter()

@router.get("/tables")
def get_tables():
    """Get list of available tables"""
    return {"tables": list_tables()}

@router.get("/tables/{table_name}/schema")
def get_table_schema_endpoint(table_name: str):
    """Get schema for a specific table"""
    try:
        return get_table_schema(table_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))