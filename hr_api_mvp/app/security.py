
from fastapi import Header, HTTPException, Depends
from .database import get_conn, get_client_by_api_key

def require_api_key(x_api_key: str = Header(alias="X-API-Key")):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    conn = get_conn()
    try:
        client = get_client_by_api_key(conn, x_api_key)
    finally:
        conn.close()
    if not client:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return dict(client)

def require_employee(employee_id: str, access_code: str | None):
    if not access_code:
        raise HTTPException(status_code=401, detail="Missing access_code")
    return employee_id, access_code
