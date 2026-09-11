# Migration Notes — Refined v5

## Baseline used

This package was built from `evsu_extension_revision_2026_09_11_ui_fixed`, because that is the user's confirmed last downloaded/working ZIP. The later dashboard-reference styling was selectively merged into that base.

## Included migration strategy

The September 11 `ui_fixed` package did not ship migration files and instructed the user to run `python manage.py makemigrations dashboard`. A normal first migration from that build would therefore be recorded as `dashboard.0001_initial`.

This v5 package includes:

- `0001_initial.py` — baseline schema matching the `ui_fixed` models.
- `0002_refined_workflows.py` — adds the new field-visit partner signatory fields, QMR variable signatory fields, nullable/conditional phase/status behavior, and updated field-visit ordering.

This is intended to support both a fresh database and the common case where an existing `ui_fixed` database already records `dashboard.0001_initial`.

## Before migrating an existing database

Always copy/back up the existing database first. Then run:

```powershell
python manage.py migrate
```

Do not run `--reset-users` when preserving the existing database.

If your local migration history used a different migration name/schema than the normal `0001_initial`, stop on any migration-history error rather than deleting migration records or the database.

## Data behavior changes that do not require destructive conversion

- Existing Program/Project/Activity records remain the core PPA hierarchy.
- QPAR remains the source for all 24 indicators; only indicators 1–4 feed TAEP dashboard/report surfaces.
- Existing users can remain. If `first_name`/`last_name` are blank, UI/signatories fall back to username until real names are entered.
- Field-visit list now de-duplicates by Project for the selected Year/Quarter and edits the latest Project-period monitoring log instead of creating a new visible row per revision.
