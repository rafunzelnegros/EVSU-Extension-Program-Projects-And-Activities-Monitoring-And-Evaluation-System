# EVSU Extension Monitoring System — V7 Clean Rebuild

This package is a fresh rebuild intended to replace the patched V3–V6 development database. The configured MySQL database name is exactly `evsu_extension`.

## IMPORTANT: Fresh database
If your current `evsu_extension` database contains only test data and you already decided to delete it, open phpMyAdmin → SQL and run the included `reset_database.sql`, or run:

```sql
DROP DATABASE IF EXISTS evsu_extension;
CREATE DATABASE evsu_extension CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Do not manually create tables. Django will create them.

## First-run setup in VS Code PowerShell

```powershell
cd path\to\evsu_extension_v7
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_indicators
python manage.py createsuperuser
python manage.py runserver
```

If your XAMPP database `root` user has a password, edit `evsu_extension/settings.py` and put it in `DATABASES['default']['PASSWORD']` before migrating.

Optional test accounts:

```powershell
python manage.py seed_demo_accounts
```

Temporary password: `ChangeMe123!`

## Main V7 corrections
- Director TAEP/QPAR lists show only reports created by the Director. End-user submissions are reviewed under **Reports** instead of being mixed into the Director's personal history.
- End-user dashboard is scoped to the assigned school/campus.
- End users do not see Reports or Admin navigation.
- Header displays the currently logged-in role/school/campus.
- User notifications are created when the Director approves or returns a report.
- Draft TAEP/QPAR reports can be deleted by their creator, including Director-created drafts.
- Partnership form no longer contains Agreement Type. `Board Confirmed` is a checkbox field.
- PPA Data Entry feeds the Programs/Projects status table/chart, assessment counts, and personnel counts.
- Dashboard donut is dynamic and reads the same PPA summary counts as the table.
- TAEP has PDF MOV uploads, automatic totals, whole-number validation for normal indicators, decimal percentage input, and future-quarter locking for end users.
- QPAR has PDF MOV uploads, integer numeric fields, automatic `(2)`, `(3)` revision naming, creator Edit for Draft/Returned reports, and landscape print styling.
- Reports View keeps Reports active; Return uses a required comment modal.
- Print views use spreadsheet-like tables and compact signatory lines.
- Login uses “Monitoring and Evaluation”.
- `DATA_UPLOAD_MAX_NUMBER_FIELDS=5000` prevents the Director TAEP form from hitting Django's default 1,000-field limit.

## UACS codes
The supplied source material identifies a UACS Code field but does not provide the actual codes for the 24 indicators. V7 therefore does **not invent codes**. After `seed_indicators`, enter official UACS codes through `/django-admin/` → Extension indicators when the Extension Office provides them.

## PDF / MOV storage
PDFs work locally immediately under `media/movs/`. See `GOOGLE_DRIVE_SETUP.md` for the optional Drive migration path.

## Pre-Oral UI / Workflow Notes

### Replace the EVSU logo
The project intentionally ships with a placeholder image so you can swap in the official logo without editing HTML.

1. Prepare the official EVSU logo as a PNG (square image is best).
2. Rename it exactly to `evsu-logo.png`.
3. In VS Code open: `dashboard/static/dashboard/img/`.
4. Replace the existing `evsu-logo.png` file with your official logo.
5. Restart Django if needed, then use **Ctrl + F5** in the browser to force-refresh static files.

The same file is used in the main header and Sign In page.

### UACS codes
UACS codes are stored centrally in the `ExtensionIndicator` master table. They are **not invented by the system** and should not be repeatedly typed into every report. The Extension Office should provide/verify the official UACS code for each indicator; encode it once in the indicator master record (Django Admin), and TAEP forms/reports reuse it automatically. If no official code has been supplied yet, leave it blank instead of guessing.

### Director-created reports
When the Director presses **Submit Report** on a Director-created TAEP or QPAR, the report is automatically marked **Approved** and remains in the Director's own report history. It does not enter the Reports-for-Review queue. The Reports page is reserved for submissions made by other accounts.

### Board Confirmed MOA/MOU dashboard
The supplied partnership data-entry sheet has no separate Agreement Type field. To avoid inventing a field that is not present in the source sheet, the dashboard recognizes confirmed MOA/MOU from the partnership **Remarks** text. Example remarks: `3-year MOA` or `MOU for renewal`. If the office later provides an official separate MOA/MOU field, this logic can be normalized in the database.
