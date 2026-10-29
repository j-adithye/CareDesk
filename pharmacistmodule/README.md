# CareDesk pharmacist API (DRF, API only)

Uses the shared models in `adminmodule/models.py` (Medicine, PrescriptionMedicine, ActivityLog, Role, Staff).
Rules follow FR-PHM-01..10 of Clinic_Management_System_Django v1.1. All endpoints need role **Pharmacist**
(`Staff.roleid.title`). Business rules are in `services.py`; views only call them.

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/pharmacist/medicines/` | List active medicines. `?search=` matches name or code; `?include_inactive=true` shows disabled ones |
| POST | `/api/pharmacist/medicines/` | Add medicine `{name, generic_name, company_name, unit_price}`; stock starts at 0 |
| GET | `/api/pharmacist/medicines/{id}/` | One medicine |
| DELETE | `/api/pharmacist/medicines/{id}/` | Disable (soft delete) |
| POST | `/api/pharmacist/medicines/{id}/add-stock/` | `{quantity}` positive whole number (1 to 1,000,000) |
| GET | `/api/pharmacist/prescription-medicines/` | PENDING lines (`?status=ISSUED` for issued) with patient, doctor, medicine, quantity_required, current_stock |
| POST | `/api/pharmacist/prescription-medicines/{id}/issue/` | Issue a line: lock, reduce stock, mark ISSUED |

There is no PUT/PATCH: the pharmacist cannot edit price or stock directly (FR-PHM-05).
Logged actions: MEDICINE_ADD, MEDICINE_DISABLE, MEDICINE_STOCK_ADD, MEDICINE_ISSUE.

## Install

1. Check whether the old pharmacist migration was applied. In the terminal (venv active, in the folder that contains `manage.py`) run:
   `python manage.py showmigrations pharmacistmodule`
   If it shows `[X] 0001_initial`, undo it **before** deleting the file (Django needs the file to undo it):
   `python manage.py migrate pharmacistmodule zero`
   This only drops the duplicate pharmacistmodule tables; adminmodule tables are untouched.
   If it shows `[ ] 0001_initial`, it was never applied and you can skip the undo.
2. Delete the old `pharmacistmodule/migrations/0001_initial.py`.
3. Copy these files over `pharmacistmodule/` (keep your `__init__.py`, `apps.py`, `admin.py`).
4. In `CareDeskProject/urls.py` add the trailing slash to every include, e.g. `path('api/pharmacist/', include('pharmacistmodule.urls'))`.
5. `python manage.py migrate` then `python manage.py test pharmacistmodule`.
6. Get a token: `POST /api/auth/login/` with `{"username": "...", "password": "..."}` and use the `access` value as a Bearer token.

## Needed from teammates (not pharmacist code)

- JWT is configured in `settings.py` (`REST_FRAMEWORK`, `SIMPLE_JWT`) with the login route `POST /api/auth/login/` in the project `urls.py`.
  Log in with username and password, then send `Authorization: Bearer <access token>` on every request.
- Role titles must be exactly `Administrator, Receptionist, Doctor, Pharmacist, Lab Technician`
  (`create_superuser` currently creates the title "Admin").
- `adminmodule.Medicine` should get UNIQUE(name, company_name) and CHECK constraints (stock >= 0, price > 0);
  `PrescriptionMedicine.status` should default to `PENDING`.

## My assumptions

- Issuing is refused for a disabled medicine (the spec is silent).
- Add Stock is capped at 1,000,000 per call to avoid integer overflow.
- Prices on a prescription line are never rewritten at issue time (A11).