# AAC-06 — ServiceNow CMDB reconciliation

## The position

ServiceNow is the intended long-term system of record for the application inventory.
It is not accurate enough to rely on today. The design follows from both facts.

Treating an immature CMDB as authoritative would import its errors into the
architecture model. Ignoring it would build a parallel inventory that has to be
reconciled eventually, at a cost that grows every quarter, and would leave the CMDB's
errors unreported.

So: **the model is authoritative, the CMDB is an input, and the output is a drift
report.** Nothing is written to ServiceNow. Nothing is written to the model. What the
adapter produces is a list of differences for a human.

The drift report also gives the CMDB owner a list of corrections: "Here are eleven CIs
that do not correspond to anything real, here are eight applications missing entirely,
here are nine attributes that disagree".

## Running it

```bash
cd 50_ENGINE && python -m terrane cmdb drift --export ../60_SOURCES/servicenow/sample_cmdb_ci_export.csv
```

Writes `70_ARTIFACTS/cmdb/drift_report.md` and `drift.csv`. `terrane render`
writes the same two from the sample export whenever it runs, so the committed
report is regenerated with the diagrams and CI's staleness check covers it; it
had said thirty systems when the model held seventy-four before that. The
app's **Drift** panel is the same reconciliation, read-only, off
`/api/cmdb/drift`.

The input is a CSV export of `cmdb_ci`. Columns read are `sys_id`, `name`,
`sys_class_name`, `operational_status`, `business_criticality`, `owned_by`,
`environment`, `u_hosting`. Extra columns are ignored; missing ones produce no
comparison for that field. There is no live API call — an export is easier to get
approved, easier to reproduce, and cannot have a side effect.

## Matching

Three passes, weakest last:

1. **`cmdb_ci_sys_id` on the system.** Exact and durable. This is the goal state.
2. **Normalized name, exact.** Case, punctuation and noise words (`system`, `service`,
   `application`, `app`, `platform`) removed. Reported as `UNLINKED_MATCH` so somebody
   records the sys_id and makes it durable.
3. **Name, scored**, 0.86 or more by the engine's matcher (`terrane.match`), and
   only against a system with no sys_id yet. The matcher reads a name as words,
   weighs each by how rare it is among the systems, counts an abbreviation (`gen`,
   `general`) as most of a shared word, adds Jaro-Winkler and the cosine of
   three-letter pieces, and holds two names with different numbers apart
   (`prd-lon-web-01` is not `prd-lon-web-02`). Distinct systems of the sample
   estate score at most 0.825 against each other. Reported as `CANDIDATE_MATCH`
   and **never applied**. A human confirms and records the sys_id.

If two systems normalize to the same name, that is `AMBIGUOUS` and no match is made.
The finding is in the model naming, not in the CMDB.

## Reading the report

| Category | Meaning | Action |
|---|---|---|
| `LINKED_OK` | Linked and agreeing | None |
| `ATTR_MISMATCH` | Linked, one or more fields disagree | Decide per field, per `field_sot.yaml` |
| `UNLINKED_MATCH` | Matched on name, no sys_id recorded | Record `cmdb_ci_sys_id` |
| `CANDIDATE_MATCH` | Probable match, not applied | Confirm, then record the sys_id |
| `AMBIGUOUS` | Several systems share a normalized name | Disambiguate the model names |
| `MODEL_ONLY` | In the model, not in the export | Either the CI is missing, or the system is stale |
| `CMDB_ONLY` | In the export, not in the model | Either the model is incomplete, or the CI is junk |

**A high `CMDB_ONLY` count is expected and is not a defect in the model.** A CMDB
accumulates print servers, SharePoint sites, decommissioned tools and rows called
`APP-4471`. The sample export in `60_SOURCES/` contains such rows, so the sample
report shows what a real export produces.

Two numbers are worth tracking:

- **Model coverage** — the share of modeled systems reconciled to a CI. It should
  climb. It measures how far the two inventories have converged.
- **`ATTR_MISMATCH` on fields the CMDB is supposed to own.** That is the escalation
  number.

## Per-field source of truth

`60_SOURCES/servicenow/field_sot.yaml` records who wins per field:

```yaml
fields:
  name: model
  status: model
  criticality: model
  environment: model
  cmdb_ci_class: cmdb
```

This file is the migration mechanism. Everything starts on `model` because nothing in
the CMDB is trusted yet. As a field becomes reliable, flip it — one field, as a recorded
governance decision, with no code change. The drift report then reads every difference
on that field as a gap in the model rather than drift in the CMDB.

A sequence for flipping fields:

1. **`cmdb_ci_class` first**, and it already is. It is ServiceNow taxonomy, which the
   model has no reason to own.
2. **`environment` next.** Discovery is usually right about where something runs even
   when it is wrong about what the thing is for.
3. **`status` after discovery is trusted**, because at that point the CMDB knows about
   decommissioning before the architecture team does.
4. **`owner_org_id` only once CMDB ownership is maintained**, which is a
   process question and not a data one.
5. **`criticality` last, if ever.** Business criticality in a CMDB is typically an
   unreviewed default from whoever created the CI.

## Getting to the point where this matters

The reconciliation runs now; the destination — ServiceNow owning the inventory — needs
three things that are not code:

**A shared key.** `cmdb_ci_sys_id` on every system, populated. The drift report gives
you a work list, and `UNLINKED_MATCH` plus `CANDIDATE_MATCH` are the quickest to close.

**A CI creation path that runs at the same time as the model entry.** As long as CIs
are created by a separate process at a different time, the two inventories diverge
faster than reconciliation closes the gap. This is the most important of the three.

**An agreed granularity.** A CMDB models runtime configuration items. This model holds
applications and services. `SYS-CARDSVC-API` is one entity here and could be forty CIs
there. Reconciliation is at the application layer, and the `sys_class_name` filter is
where that boundary gets drawn. Agree it in advance, including whether a load balancer
counts as an application.

## Safety

The adapter is read-only by construction. It takes a file path, opens it for reading,
and writes only into `70_ARTIFACTS/`. There is no ServiceNow credential, no client and
no write path anywhere in `50_ENGINE/terrane/cmdb.py`, and a test asserts that
reconciliation does not mutate the loaded model.

Keep it that way. A write-back to ServiceNow is a different project with a different
approval, and once this becomes bidirectional nothing in the code enforces the "model
is authoritative" position.
