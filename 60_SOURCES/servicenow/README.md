# ServiceNow inputs

Read-only. Nothing in this folder is written to ServiceNow, and nothing here is written
back into the model. See [AAC-06](../../00_METHOD/AAC-06_CMDB_RECONCILIATION.md) for
the reasoning.

| File | What it is |
|---|---|
| `sample_cmdb_ci_export.csv` | A sample `cmdb_ci` export, deliberately messy. Print servers, a SharePoint site, a decommissioned tool and a row called `APP-4471` are all in there on purpose, because a clean sample would make the tooling look better than the situation is |
| `field_sot.yaml` | Per-field source of truth. Everything starts on `model`. Flipping a field to `cmdb` is a governance decision recorded here, and needs no code change |

## Getting a real export

A saved list export of `cmdb_ci` (or a filtered subclass such as `cmdb_ci_appl`) as CSV.
Columns read: `sys_id`, `name`, `sys_class_name`, `operational_status`,
`business_criticality`, `owned_by`, `environment`, `u_hosting`. Extra columns are
ignored; missing ones produce no comparison for that field.

Filtering to the application classes before exporting is worth doing. Reconciliation
happens at the application layer, and an unfiltered export mostly produces `CMDB_ONLY`
rows for hardware nobody intended to model.

```bash
cd 50_ENGINE && python -m terrane cmdb drift --export ../60_SOURCES/servicenow/your_export.csv
```

Do not commit a real export. It is an inventory of the estate and it does not belong in
version control.
