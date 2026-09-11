# Migration Notes — Refined v6

Base: `evsu_extension_revision_2026_09_12_refined_v5`

Database migration added: `dashboard/migrations/0003_sdgs_profiles_qmr_units.py`

It adds:
- `UserProfile.post_nominals`
- QMR `school_name`, `campus_name`, and `department`
- `SustainableDevelopmentGoal` child records for repeatable SDGs
- a data migration that preserves legacy text from `PPA.sdgs` as the first structured SDG entry when applicable

Run:

```powershell
python manage.py migrate
```

before opening v6 against your existing database.

## Important behavior changes

- Draft PPAs do not feed dashboards, TAEP/PPA statistics, Work Plan monitoring lists, QMR project choices, or Prediction & Analysis.
- The PPA `Programs` and `Projects` tabs show finalized/saved PPAs; drafts remain under `All` and `Drafts`.
- Project final save is rejected unless at least three Activities are actually persisted.
- Saved Coordinator QPAR records are protected from Admin Staff edits.
