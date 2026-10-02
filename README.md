# University Clinic Management System
**IBBU, Lapai — Final Year Project**

## Setup & Run

1. Install Python 3.10+ from https://python.org
2. Open terminal inside the `clinic/` folder
3. Install dependencies:
   ```
   pip install flask werkzeug
   ```
4. Run the app:
   ```
   python app.py
   ```
5. Open browser at: **http://127.0.0.1:5000**

## First Time Setup

1. Go to **http://127.0.0.1:5000/create-staff**
2. Create your staff (admin) account
3. Log in with those credentials
4. Register patients and optionally create their student login accounts

## Two User Portals

| Role    | Access | Dashboard |
|---------|--------|-----------|
| Staff   | Full read/write access to all modules | `/` |
| Student | Read-only access to own records only | `/student/dashboard` |

## Project Structure
```
clinic/
├── app.py              ← Staff routes
├── auth.py             ← Login / logout / decorators
├── student.py          ← Student portal routes
├── database.py         ← DB setup (5 tables)
├── requirements.txt
└── templates/
    ├── base.html, staff_base.html
    ├── login.html, create_staff.html
    ├── dashboard.html, patients.html, ...
    └── student/
        ├── base.html
        ├── dashboard.html
        ├── appointments.html
        ├── prescriptions.html
        └── billing.html
```
