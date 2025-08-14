
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
from typing import Optional, List

from .database import init_db, seed_sample_data, get_conn, get_employee, get_leave_type, days_between, get_balances
from .security import require_api_key

app = FastAPI(title="Leave Application and Monitoring API System", version="0.1.0")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB & seed demo data on import
init_db()
seed_sample_data()

class LeaveApplicationIn(BaseModel):
    employee_id: str
    access_code: str
    leave_type: str
    start_date: str  # ISO YYYY-MM-DD
    end_date: str    # ISO YYYY-MM-DD
    reason: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/leave/{employee_id}")
def get_leave(employee_id: str,
              access_code: str = Query(None, description="Employee access code/PIN"),
              year: Optional[int] = Query(None, description="Year for balances (default current year)"),
              client=Depends(require_api_key)):
    conn = get_conn()
    try:
        emp = get_employee(conn, client["id"], employee_id)
        if not emp: raise HTTPException(status_code=404, detail="Employee not found")
        if access_code is None or access_code != emp["access_code"]:
            raise HTTPException(status_code=403, detail="Invalid access_code")

        if year is None:
            year = date.today().year
        balances = get_balances(conn, emp["id"], year)
        # Also return a short recent history (last 10 applications)
        history = conn.execute("""
            SELECT la.id, lt.code as leave_type, la.start_date, la.end_date, la.days, la.status, la.reason, la.created_at
            FROM leave_applications la
            JOIN leave_types lt ON lt.id = la.leave_type_id
            WHERE la.employee_id=?
            ORDER BY la.id DESC
            LIMIT 10;
        """, (emp["id"],)).fetchall()
        return {
            "employee": {"employee_id": emp["employee_code"], "full_name": emp["full_name"]},
            "balances": balances,
            "recent_applications": [dict(row) for row in history]
        }
    finally:
        conn.close()

@app.get("/leave/{employee_id}/{leave_type}")
def get_leave_by_type(employee_id: str,
                      leave_type: str,
                      access_code: str = Query(None, description="Employee access code/PIN"),
                      year: Optional[int] = Query(None),
                      client=Depends(require_api_key)):
    conn = get_conn()
    try:
        emp = get_employee(conn, client["id"], employee_id)
        if not emp: raise HTTPException(status_code=404, detail="Employee not found")
        if access_code is None or access_code != emp["access_code"]:
            raise HTTPException(status_code=403, detail="Invalid access_code")

        lt = get_leave_type(conn, client["id"], leave_type)
        if not lt: raise HTTPException(status_code=404, detail="Leave type not found")

        if year is None:
            year = date.today().year

        # Compute balances for this type only
        from .database import calc_year_bounds
        start_iso, end_iso = calc_year_bounds(year)
        row = conn.execute("""SELECT COALESCE(SUM(days),0) as taken
                              FROM leave_applications
                              WHERE employee_id=? AND leave_type_id=? AND status='approved'
                                AND start_date >= ? AND end_date <= ?""",
                           (emp["id"], lt["id"], start_iso, end_iso)).fetchone()
        taken = row["taken"]
        remaining = max(0, lt["annual_allocation"] + lt["carry_over"] - taken)
        return {
            "employee": {"employee_id": emp["employee_code"], "full_name": emp["full_name"]},
            "leave_type": {"code": lt["code"], "name": lt["name"], "allocation": lt["annual_allocation"], "carry_over": lt["carry_over"]},
            "year": year,
            "taken": taken,
            "remaining": remaining
        }
    finally:
        conn.close()

@app.post("/leave/apply")
def apply_leave(payload: LeaveApplicationIn, client=Depends(require_api_key)):
    conn = get_conn()
    try:
        emp = get_employee(conn, client["id"], payload.employee_id)
        if not emp: raise HTTPException(status_code=404, detail="Employee not found")
        if payload.access_code != emp["access_code"]:
            raise HTTPException(status_code=403, detail="Invalid access_code")

        lt = get_leave_type(conn, client["id"], payload.leave_type)
        if not lt: raise HTTPException(status_code=404, detail="Leave type not found")

        # compute days and validate
        try:
            d = days_between(payload.start_date, payload.end_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # simple policy: cannot request negative or 0 days; and cannot exceed remaining for paid types
        if d <= 0:
            raise HTTPException(status_code=400, detail="Leave duration must be at least 1 day")

        # For paid leave types (allocation > 0), ensure enough remaining if approved immediately.
        # (In real life, applications would be 'pending' and reviewed; here we still store 'pending')
        # We'll allow applying even if it exceeds; approval flow can later enforce.
        conn.execute("""INSERT INTO leave_applications(employee_id, leave_type_id, start_date, end_date, days, status, reason, created_at)
                        VALUES(?,?,?,?,?,?,?,DATE('now'))""",
                     (emp["id"], lt["id"], payload.start_date, payload.end_date, d, "pending", payload.reason))
        conn.commit()
        return {"message": "Leave application submitted (pending review)", "days": d}
    finally:
        conn.close()
