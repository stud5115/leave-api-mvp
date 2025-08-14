
import sqlite3
from pathlib import Path
from datetime import datetime, date

DB_PATH = Path(__file__).parent / "hr.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    api_key TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    employee_code TEXT NOT NULL, -- human-friendly ID employees type in
    full_name TEXT NOT NULL,
    access_code TEXT NOT NULL, -- simple per-employee secret/PIN
    start_date TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    UNIQUE(client_id, employee_code)
);

CREATE TABLE IF NOT EXISTS leave_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    code TEXT NOT NULL,           -- e.g. 'annual', 'sick'
    name TEXT NOT NULL,
    annual_allocation INTEGER NOT NULL,  -- days per year
    carry_over INTEGER NOT NULL DEFAULT 0, -- max carry over days allowed
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    UNIQUE(client_id, code)
);

CREATE TABLE IF NOT EXISTS leave_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    leave_type_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,  -- ISO YYYY-MM-DD
    end_date TEXT NOT NULL,    -- ISO YYYY-MM-DD inclusive
    days INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')) DEFAULT 'pending',
    reason TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (leave_type_id) REFERENCES leave_types(id) ON DELETE CASCADE
);
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()

def seed_sample_data():
    conn = get_conn()
    try:
        # create a demo client with a fixed API key
        conn.execute("INSERT OR IGNORE INTO clients(name, api_key) VALUES(?,?)",
                     ("Acme Bakery", "DEMO-ACME-KEY-123"))
        client_id = conn.execute("SELECT id FROM clients WHERE name=?", ("Acme Bakery",)).fetchone()["id"]

        # leave types
        for code, name, alloc, carry in [
            ("annual","Annual Leave", 15, 5),
            ("sick","Sick Leave", 10, 0),
            ("unpaid","Unpaid Leave", 0, 0),
        ]:
            conn.execute("""INSERT OR IGNORE INTO leave_types(client_id, code, name, annual_allocation, carry_over)
                            VALUES(?,?,?,?,?)""", (client_id, code, name, alloc, carry))

        # employees
        for emp_code, full_name, access_code in [
            ("E001", "James Chikwiti", "1234"),
            ("E002", "Nomsa Dlamini", "4321"),
        ]:
            conn.execute("""INSERT OR IGNORE INTO employees(client_id, employee_code, full_name, access_code, start_date)
                            VALUES(?,?,?,?,?)""", (client_id, emp_code, full_name, access_code, "2023-01-01"))

        # sample approved leave for E002 this year
        emp_id = conn.execute("SELECT id FROM employees WHERE employee_code=? AND client_id=?",
                              ("E002", client_id)).fetchone()["id"]
        lt_annual = conn.execute("SELECT id FROM leave_types WHERE client_id=? AND code=?",
                                 (client_id, "annual")).fetchone()["id"]
        today = date.today().isoformat()
        conn.execute("""INSERT INTO leave_applications(employee_id, leave_type_id, start_date, end_date, days, status, reason, created_at)
                        VALUES(?,?,?,?,?,?,?,?)""",
                     (emp_id, lt_annual, "2025-02-10", "2025-02-12", 3, "approved", "Family event", today))
        conn.commit()
    finally:
        conn.close()

def days_between(start_iso: str, end_iso: str) -> int:
    sd = datetime.fromisoformat(start_iso).date()
    ed = datetime.fromisoformat(end_iso).date()
    if ed < sd:
        raise ValueError("end_date cannot be before start_date")
    return (ed - sd).days + 1

def calc_year_bounds(year: int):
    return date(year,1,1).isoformat(), date(year,12,31).isoformat()

def get_employee(conn, client_id: int, employee_code: str):
    return conn.execute("""SELECT * FROM employees WHERE client_id=? AND employee_code=?""",
                        (client_id, employee_code)).fetchone()

def get_leave_type(conn, client_id: int, code: str):
    return conn.execute("""SELECT * FROM leave_types WHERE client_id=? AND code=?""",
                        (client_id, code)).fetchone()

def get_client_by_api_key(conn, api_key: str):
    return conn.execute("SELECT * FROM clients WHERE api_key=?", (api_key,)).fetchone()

def get_balances(conn, employee_id: int, year: int):
    # For each leave type: allocation + carry, minus approved days in year
    start_iso, end_iso = calc_year_bounds(year)
    types = conn.execute("SELECT * FROM leave_types WHERE client_id = (SELECT client_id FROM employees WHERE id=?)",
                         (employee_id,)).fetchall()
    result = []
    for lt in types:
        alloc = lt["annual_allocation"]
        carry = lt["carry_over"]
        row = conn.execute("""SELECT COALESCE(SUM(days),0) as taken
                              FROM leave_applications
                              WHERE employee_id=? AND leave_type_id=? AND status='approved'
                                AND start_date >= ? AND end_date <= ?""",
                           (employee_id, lt["id"], start_iso, end_iso)).fetchone()
        taken = row["taken"]
        remaining = max(0, alloc + carry - taken)
        result.append({
            "leave_type": lt["code"],
            "name": lt["name"],
            "allocation": alloc,
            "carry_over": carry,
            "taken": taken,
            "remaining": remaining
        })
    return result
