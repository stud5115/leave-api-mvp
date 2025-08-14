
# Leave Application and Monitoring API System (MVP)

**Stack:** Python 3.10+, FastAPI, SQLite.  
**Modules:** Backend Leave System, Leave Enquiry API, Employee Client System (frontend).

## Quickstart

1. **Create & activate venv (recommended)**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the API**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The server initializes the SQLite DB and seeds demo data automatically on first run.

4. **Open the frontend**
   - Open `frontend/index.html` in your browser.
   - Leave the defaults:
     - API Base URL: `http://localhost:8000`
     - Client API Key: `DEMO-ACME-KEY-123`
   - Use the sample employees:
     - **E001 / 1234** (James)
     - **E002 / 4321** (Nomsa)

5. **Explore the docs**
   - Swagger UI: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/health`

## API Summary

- `GET /leave/{employee_id}?access_code=XXXX&year=YYYY`
- `GET /leave/{employee_id}/{leave_type}?access_code=XXXX&year=YYYY`
- `POST /leave/apply`

**Headers:** `X-API-Key: <client-api-key>` (demo: `DEMO-ACME-KEY-123`)

## Security (MVP)
- **Client-level auth:** API key (per client) via `X-API-Key` header.
- **Employee auth:** employee enters a short **access_code** (PIN).  
  _Note: For production, prefer proper user accounts, hashed secrets, and JWT._

## Data Model (SQLite)
- `clients(id, name, api_key)`
- `employees(id, client_id, employee_code, full_name, access_code, start_date)`
- `leave_types(id, client_id, code, name, annual_allocation, carry_over)`
- `leave_applications(id, employee_id, leave_type_id, start_date, end_date, days, status, reason, created_at)`

## Business Logic
- Balances per **year**: `remaining = allocation + carry_over - approved_days_in_year`
- `days` = inclusive difference between start and end dates.
- Applications are stored with status **pending** (simple flow).

## Notes for Capstone Report
- **Design thinking** addressed: user needs (mobile/time-poor, low-cost), API abstraction, no direct DB access.
- **Risk & security**: access-controlled API, per-client isolation via API keys.
- **Scalability**: SQLite for MVP; can swap to hosted DB later with minimal code change.

---

**Enjoy!**
