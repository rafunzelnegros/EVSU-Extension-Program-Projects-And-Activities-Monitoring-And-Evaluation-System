# EVSU Extension PPAs Monitoring & Evaluation System — Refined v6

This revision was built directly from `evsu_extension_revision_2026_09_12_refined_v5` and keeps the approved EVSU UI/theme while refining the PPA, monitoring, TAEP/QPAR, user-management, and prediction workflows.

## Upgrade from v5 without losing your data

1. **Back up your old database first.** If you are using SQLite, copy your v5 `db.sqlite3` somewhere safe.
2. Extract this v6 ZIP into a **new folder**.
3. Copy your v5 `db.sqlite3` into the new v6 project folder beside `manage.py`.
4. Open PowerShell in the v6 project folder.
5. Activate your existing/new virtual environment and install requirements if needed:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

6. Run the new migration:

```powershell
python manage.py migrate
```

7. Start the server:

```powershell
python manage.py runserver
```

8. In Chrome, hard-refresh once with **Ctrl + Shift + R**. v6 also uses versioned `app.v6.css` and `app.v6.js` files to avoid the old-UI cache problem.

> Do **not** run `seed_system --reset-users` if you are keeping your existing real users/data.

## Major v6 changes

- Structured repeatable SDGs: Goal Description, Target, Description, and Indicator.
- Draft PPAs can be edited or discarded. Drafts appear under All/Drafts but are excluded from Program/Project counts, dashboards, monitoring, reports, and predictions.
- Final Project save enforces at least **3 actually stored Activities** server-side and client-side.
- Work Plan list now shows all approved Projects by default; title search is independent from Year/Quarter filters; legacy revision duplicates are collapsed to the newest Project record; sorting is newest update first.
- Quarterly Monitoring Report now includes derived School/Campus plus editable Department, automatic Director signatory, dynamic print date, and compact/adaptive Evaluation printing.
- TAEP professional print preview is a dedicated printable document with no site header/navigation/filter controls.
- Manage Users now supports editing names, username, email, role, unit, active status, password, and optional post-nominal letters.
- Activity Log supports From/To date filtering.
- Director/Admin dashboards consolidate TAEP across all units and show all schools/campuses on one smooth multi-line prediction chart.
- Saved Coordinator QPAR submissions are read-only to Admin Staff; Admin Staff cannot overwrite them. The Admin Staff QPAR list no longer shows `View TAEP`.

## Prediction method

The current prediction is an explainable **least-squares linear trend** per school/campus:

1. Count **SAVED Project** start dates in Q1, Q2, Q3, and Q4.
2. Convert those quarterly starts into cumulative Project totals.
3. For the current year, fit the trend only to quarters that have already started.
4. Extend the fitted line to estimate the next quarter and Q4/year-end cumulative count.
5. Compare all units; the unit with the highest projected Q4 total is shown as the current top projection.

This is a planning forecast, not a guarantee or AI performance score. With only one observed quarter or very little historical data, the estimate is naturally less stable.

## Work Plan Revision No.

The printable currently keeps **Revision No. 00** because that is what appears on the official Work Plan and Monitoring Log reference form. It is treated as the **document/form revision number**, not a Project edit counter. Change it later only if EVSU confirms a different official revision number.
