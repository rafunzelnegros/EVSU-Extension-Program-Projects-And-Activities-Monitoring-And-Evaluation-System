# EVSU Extension PPAs Monitoring & Evaluation System — Refined v5

**Revision date:** September 12, 2026  
**Base:** `evsu_extension_revision_2026_09_11_ui_fixed`

This revision keeps the working September 11 Django system and its EVSU maroon/gold visual identity, then applies the requested workflow, dashboard, form, monitoring, print, and analytics refinements. The desired dashboard appearance from the later dashboard reference was merged into the `ui_fixed` base rather than replacing the project with a different build.

## Main changes in v5

### General / identity
- Larger, more readable application typography, fields, labels, tables, and action buttons.
- Signed-in labels use the Django user's **real first + last name** when available, with the role underneath.
- Coordinator role labels are unit-specific, for example **SAAD Coordinator** or **Carigara Campus Coordinator**.
- User creation now requires real first and last names so these names can also be reused in automatic signatories.
- Forms were reorganized for more consistent visual hierarchy and space usage.

### Coordinator dashboard
- Restores the requested EVSU dashboard structure: status table, summary, assessment overview, board/agreement status, partnerships, and TAEP.
- The old Personnel/Students by Sex (gender) section is removed.
- Coordinator TAEP no longer repeats the small school/campus value box; the displayed total is already the coordinator's own unit data.
- Dashboard TAEP reads the first four **SAVED** QPAR accomplishments for the selected Year + Quarter.

### Programs, Projects & Activities
- Search, type/status filters, sort, Reset, and default **last updated descending** order.
- Drafts are easy to isolate.
- Notice to Proceed No. and Special Order No. use compact aligned fields with clearer placeholders.
- Implementing College/Campus/Office is shown as fixed account/unit information, not an editable field.
- Repeatable one-line **Proponents** and **Management Team Members** controls.
- Partner Agency uses Partner Name plus compact partner-type selector.
- More uniform A–L section hierarchy.
- Add Program remains a nested Program → Projects → Activities workflow; Add Project includes its approved activities and final Save requires at least three activities.

### Work Plan & Monitoring Log for Field Visits
- Year/Quarter filters remain selected after filtering and a Reset control is available.
- Project search is on the main page; the redundant New Log selection page is removed.
- The list is project-based, so the same project is not repeated once per monitoring revision.
- Default order is newest monitoring/project update first.
- Opening a project monitors its **approved Project Design activities**. Approved title/objective/date/time/venue/leader values are read-only.
- No Add Row control: only approved activities can be monitored.
- Result is a dropdown: Completed / Rescheduled / Not Conducted.
- New Date appears only when Result = Rescheduled.
- Printable adds Partner Agency / Industry / Community Authorized Representative name and post-nominal letters.
- Remaining printable signatories use stored project/user data where applicable.
- Printable date uses the current print date instead of a hardcoded date.
- Back and prominent Print/Save controls added.

### QPAR → TAEP data flow
- The first four indicators are the TAEP indicators and are read directly from **saved QPAR submissions**.
- Coordinator dashboard reads the coordinator's own unit.
- Director/Admin/M&E sitewide dashboards aggregate eligible unit data.
- The dashboard has Year + Quarter controls. To see a QPAR submission reflected, view the same Year + Quarter and make sure the QPAR is **Saved**, not Draft.

### Director: Prediction & Analysis
- Prediction overview is included directly on the Director dashboard.
- A detailed **Prediction & Analysis** page remains available.
- Dashboard shows a line graph plus an expected-outcome card naming the unit currently projected to have the most projects.
- The current method is an intentionally explainable **least-squares linear trend** over cumulative quarterly project starts. It is a planning forecast, not an AI claim and not a guarantee.

### M&E: Quarterly Monitoring Report
- Selecting a saved Project loads its Project Design Start Date and End Date automatically, plus available location/funding/cost fields.
- Status-dependent fields:
  - **Ongoing** → Phase 1–7 selection appears.
  - **Inactive** → Inactive Remarks appears.
  - **Terminated** → Date of Termination appears only when termination is eligible.
- Requested automatic-inactive rule is implemented conservatively: after the Project End Date, at least three approved activities whose latest monitoring result is Not Conducted causes the project to be flagged inactive unless all activities are completed.
- Termination remains locked until at least 365 days after Project End Date while the project remains incomplete.
- QMR **Prepared by** uses the logged-in report creator's real name automatically.
- Other QMR signatory names are report inputs because the people holding those positions may change.
- Admin Staff still has QMR access provisionally, as requested; it is easy to remove later.

### M&E: TAEP Report
Only the first four TAEP indicators are shown:
1. Number of active partnerships with LGUs, industries, NGOs, NGAs, SMEs, and other stakeholders as a result of extension activities.
2. Number of trainees weighted by the length of training.
3. Number of extension programs organized and supported consistent with the SUCs mandated and priority programs.
4. Percentage of beneficiaries who rate the training courses and advisory services as satisfactory or higher in terms of quality and relevance.

The other 20 Extension Indicators remain available through QPAR but are not shown in the TAEP Report.

Prediction & Analytics has been removed from the M&E **Admin** menu.

---

## Safest setup — fresh test database

From the extracted v5 folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_system --demo-users
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Temporary demo password if demo users are seeded:

```text
ChangeMe123!
```

Change temporary passwords before any real deployment.

## Preserve the SQLite data from your current `ui_fixed` folder

If your current working copy uses SQLite and already contains PPAs/QPAR/users you want to keep:

1. Stop `runserver`.
2. Back up your current project folder and `db.sqlite3`.
3. Extract this v5 ZIP to a **new folder**.
4. Copy only your existing `db.sqlite3` from the current `ui_fixed` folder into the new v5 folder, replacing an empty/test DB if present.
5. Activate/install the v5 environment as needed.
6. Run:

```powershell
python manage.py migrate
python manage.py runserver
```

Do **not** run `--reset-users` if you want to preserve your users/data.

The included migration chain intentionally keeps the baseline name `0001_initial` used by a typical `makemigrations dashboard` setup from the `ui_fixed` build, then applies `0002_refined_workflows` for the new fields.

If Django reports a migration-history mismatch in your local copy, stop before deleting anything and keep the database backup.

## MySQL / XAMPP

If your existing system uses MySQL, keep your current DB environment configuration and run the included migrations against the backed-up database:

```powershell
$env:DB_ENGINE='mysql'
$env:DB_NAME='evsu_extension'
$env:DB_USER='root'
$env:DB_PASSWORD='your_password'
$env:DB_HOST='127.0.0.1'
$env:DB_PORT='3306'
python manage.py migrate
python manage.py runserver
```

Do not delete the existing database as a troubleshooting step.

## Demo users

`python manage.py seed_system --demo-users` creates placeholder accounts with placeholder real names so the real-name UI/signatory behavior is visible. Existing real users are not replaced by that command when their usernames already exist.

To intentionally wipe/recreate users on a disposable copy only:

```powershell
python manage.py seed_system --reset-users --demo-users
```

This is destructive to Django user records and should not be run on the only copy of your data.

## Print-form references

The provided photographed official forms remain in `reference_forms/` and were used as layout references for the browser-print templates.

## Static assets

This revision uses versioned assets:

- `dashboard/css/app.v5.css`
- `dashboard/js/app.v5.js`

If a browser still shows an older layout after changing folders/restarting the server, use a hard refresh (`Ctrl + Shift + R`).

## Validation performed in this build environment

All Python source files were syntax-compiled successfully with `compileall`. The build environment did not have an installed Django runtime available for a full `manage.py check` / browser launch, so run `python manage.py migrate` and `python manage.py runserver` locally against a backup/test database first.
