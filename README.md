# EVSU Extension PPAs Monitoring and Evaluation System — Sept. 11, 2026 Revision

This build is a reconstructed revision of the existing Django/Bootstrap system based on the recoverable August source files plus the Sept. 11 workflow changes and the photographed official print forms.

## Implemented in this revision

- Role-based navigation for **M&E Head**, **Coordinator**, **Admin Staff**, and **Director**.
- PPA hierarchy: **Program → Projects → Activities**.
  - **Add Program** is one workflow that saves the Program, nested Projects, and each Project's Activities.
  - **Add Project** saves a Project with a minimum of 3 Activities on final Save.
- Project Design fields A–L requested in the Sept. 11 revision, including approval references, unit auto-assignment for coordinators, partner/MOA/board conditional data, management team, duration, funding, URDEA, SDGs, activities, time-gated termination, and time-gated internal/external impact assessment.
- Work Plan and Monitoring Log for Field Visits with quarter/year filtering, project activity prefill, results, rescheduling, remarks, evaluation, and official-style print output.
- Quarterly Monitoring Report for M&E Heads and **provisionally Admin Staff**, with Phase 1–7, status, evaluation, and official-style print output.
- QPAR Input for Coordinators and Admin Staff. The first 4 saved indicators are automatically reflected on dashboards as the TAEP summary.
- M&E TAEP consolidated report across all 11 schools/campuses.
- Dashboard summaries derived from PPA/QPAR records.
- Prediction/Analytics page using a lightweight least-squares trend over quarterly project starts (no external ML dependency).
- User management and activity log for M&E Heads.
- Seed command for 11 units and the 24 Extension Indicators.

## Important implementation choice

The exact latest project ZIP was not present in the active conversation, so this is a **reconstructed working revision**, not a byte-for-byte patch of the user's latest local folder. The visual language intentionally follows the recovered dark-green EVSU interface. Before replacing an existing database, review/migrate current data.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations dashboard
python manage.py migrate
python manage.py seed_system --demo-users
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Demo password (only if `--demo-users` was used): `ChangeMe123!`. Change immediately.

### If you want a clean set of users

On a COPY/backup of your database only:

```powershell
python manage.py seed_system --reset-users --demo-users
```

This deletes all existing Django users in that database before recreating the placeholder role accounts. Do not run this on the only copy of production data.

## MySQL/XAMPP

SQLite is the default so the project can start without database configuration. To use MySQL, set environment variables first:

```powershell
$env:DB_ENGINE='mysql'
$env:DB_NAME='evsu_extension'
$env:DB_USER='root'
$env:DB_PASSWORD='your_password'
$env:DB_HOST='127.0.0.1'
$env:DB_PORT='3306'
```

Then run migrations. If your old MySQL/MariaDB install still gives authentication-plugin errors, fix the server/client configuration before migrating; do not delete the database as a troubleshooting step.

## Time-gating rules

- **Termination** is enabled after `End Date + 365 days` when there is no completed Field Visit accomplishment and no termination date has already been recorded.
- **Impact Assessment** becomes enabled after `Date of Termination + 365 days`.

These rules are centralized in `PPA.termination_eligible` and `PPA.impact_assessment_eligible` so they can be changed if the Extension Office confirms a different interpretation.

## Provisional item

Quarterly Monitoring Report access currently includes **Admin Staff** as requested in the Sept. 11 change. If this is confirmed wrong, remove `UserProfile.ADMIN_STAFF` from `qmr_list`, `qmr_edit`, and `qmr_print` in `dashboard/views.py`, and remove the Admin Staff nav link in `dashboard/templates/dashboard/base.html`.

## Official printable references

See `reference_forms/`. The print templates are browser-print layouts based on these forms, not scans embedded as the final printable document.

## UI restoration update
This package restores the EVSU institutional visual system across the application: maroon/gold university palette, branded header/login, role-aware active navigation, responsive/mobile navigation, dashboard hero, richer monitoring cards, refined forms/tables, and dynamic add/remove interactions. Backend/data-flow behavior from the September revision is unchanged.


## UI / static files note (v3)
This build uses versioned static assets (`app.v3.css` and `app.v3.js`) and an absolute `/static/` prefix to prevent an older browser-cached stylesheet from being mixed with newer templates. If upgrading over an older extracted copy, replace the whole project folder rather than copying only templates. Restart `python manage.py runserver` after extraction.
