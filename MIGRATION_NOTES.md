# Merge / Migration Notes

The recovered August build used a generic `ExtensionPPA` record and separate TAEP/QPAR models. This revision restructures PPAs around a real hierarchy and should be migrated carefully rather than pointed directly at the only copy of the old database.

Recommended path: make a copy of the current project and database; run this revision separately; export old `ExtensionPPA` records; map records with type PROGRAM to `PPA(ppa_type=PROGRAM)`, type PROJECT to `PPA(ppa_type=PROJECT)`, and activity-type rows to `Activity` under the correct project; then verify dashboard totals before retiring the old schema.

The QPAR/TAEP redesign keeps all 24 indicators and makes QPAR the source of the dashboard's first four TAEP indicators. If the office later confirms that M&E Heads must directly encode a separate TAEP adjustment form, add an adjustment layer rather than duplicating the QPAR records.

## UI reference alignment (v4)
- Dashboard layout was realigned to the provided EVSU reference screenshots: white institutional header, maroon hero, signed-in unit card, Programs/Projects status table, summary ring, Assessment Overview, Board Confirmation & Agreements, Active Partnerships, and TAEP section.
- The Personnel and Students Involved by Sex / gender visualization was intentionally removed per the latest requirement.
- Role-specific navigation from the revised CAPSTONE requirements is retained; only the visual language/layout was brought back to the approved dashboard aesthetic.
