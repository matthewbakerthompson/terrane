# AAC-02 — Model conventions

## Layout

```
10_MODEL/
  model.yaml                  model-level config: name, palette overrides
  systems/SYS-CORE-LEDGER.yaml       one file per system
  interfaces/*.yaml                  grouped by theme
  data_assets/*.yaml
  tech_services/tech_services.yaml   reference set, one file
  capabilities/capabilities.yaml     reference set, one file
  org_units/org_units.yaml           reference set, one file
  policies/policies.yaml             the register, imported; one file
  controls/controls.yaml             the register, imported; one file
  products/PRD-CARD-SERVICING.yaml   one file per product
  relations/*.yaml                   relation rows, grouped by theme
  relations/governance.yaml          where the estate enforces the register; hand-authored
  relations/governance_from_business_layer.yaml   derived at import; never edited
```

Beside the model sit the shapes it is built from: `20_ARCHETYPES/` (a product
from a handful of answers), `26_BLOCKS/` (the components that arrive
together), `27_PATTERNS/` (a block plus the decision), and `25_COMPONENTS/`
(the vocabulary underneath). None of them is the model; the model's records are
built from them.

A file may hold one record or a list of records. The rule of thumb: **one file per
thing that changes on its own schedule, one file per set that changes together.**
Systems get their own files because they are added, retired and reviewed
individually, and because a per-file layout gives you code ownership and a clean diff.
Org units and capabilities change rarely and as a set, so they live in one file each.

## Identity

Ids have one shape: upper case, hyphen separated, prefixed by type.

| Type | Prefix | Example |
|---|---|---|
| System | `SYS-` | `SYS-CORE-LEDGER` |
| Interface | `INT-` | `INT-CARDSVC-API-LEDGER` |
| Data asset | `DA-` | `DA-CARD-ACCOUNT` |
| Technology service | `TS-` | `TS-AZURE-APIM` |
| Capability | `CAP-` | `CAP-ACCOUNT-SERVICING` |
| Org unit | `ORG-` | `ORG-DIGITAL-CHANNELS` |
| Product | `PRD-` | `PRD-CARD-SERVICING` |

Three rules, all enforced:

- **Ids are unique across every type**, not only within a type. This
  means a reference can be resolved without knowing what it points at, which is what
  makes `expand: {relation: any}` in a view possible.
- **Ids are immutable.** They are business keys. A system that gets renamed keeps its
  id. If the id becomes misleading, retire the entity and create a new one
  rather than rewriting history that other systems, exports and CMDB links point at.
- **Ids are never reused.** Leave gaps.

The prefix rule is a warning rather than an error, because there are legitimate
exceptions to it. The format rule is an error, because a malformed id breaks the exports.

## Required fields

Errors, per type:

| Type | Required |
|---|---|
| All | `name`, `status` |
| Systems | `owner_org_id`, `criticality` |
| Interfaces | `source_system_id`, `target_system_id` |
| Products | `owner_org_id` |

`status` is one of `Planned`, `Active`, `Deprecated`, `Retired`. Planned entities live
in the same model as live ones, so a target-state view is a filter over the same
records rather than a second diagram.

`owner_org_id` is required on systems and has no default, so every system names the
org unit responsible for correcting its record. If the owner is not known, that is a
finding to resolve.

## Warnings and what they mean

These do not fail the build. They are the governance backlog, and the counts are worth
tracking over time.

| Code | Meaning |
|---|---|
| `id.prefix` | Id does not use the conventional prefix for its type |
| `field.unknown` | A field the metamodel does not define. Usually a typo |
| `graph.orphan` | A live system with no recorded interfaces, services, data or capabilities. Usually an incomplete record rather than an isolated system |
| `graph.self_loop` | An interface connecting a system to itself |
| `cmdb.unlinked` | No `cmdb_ci_sys_id`. See AAC-06 |
| `governance.tier` | High criticality with no service tier |
| `governance.classification` | Holds personal data with no classification |
| `view.no_edges` | A view rendering nodes and no relationships. Usually a wrong `edges` clause |
| `view.truncated` | A diagram, map or timeline hit `limits.max_nodes` and is drawn cut |
| `view.past_limit` | A report lists more than `limits.max_nodes`. It is listed whole; the limit says its scope may have stopped filtering |
| `model.load` | Something was dropped during archetype expansion. See AAC-03 |

## Relations

Relationship truth lives in relation rows, not in semicolon-separated columns on the
entity. This follows metamodel v2, where the legacy list columns are explicitly marked
non-authoritative.

```yaml
# 10_MODEL/relations/imported_relations.yaml
system_realizes_capability:
  - system_id: SYS-CORE-LEDGER
    capability_id: CAP-ORIG-06
```

Two relationships are expressed as fields rather than rows, because they are functional
rather than many-to-many, and splitting them out would make the common case worse:

- `interfaces.source_system_id` / `target_system_id` — an interface has one of each.
- `data_assets.source_of_truth` — an asset has one system of record. If it appears to
  have two, that is the finding.

Duplicate relation rows are dropped with a warning rather than an error, because the
same fact arriving from an archetype and from a hand-written file is a normal
consequence of refactoring a shape.

## Extension fields

Fields this repository adds beyond metamodel v2 are listed in
[AAC-07](AAC-07_METAMODEL_CONTRACT.md). The ones you will meet while authoring:

| Field | Purpose |
|---|---|
| `company_domain` | Grouping in views. The organizational cut, not the TOGAF one |
| `tags` | Free-form, list or semicolon string. Used by `tags_any` / `tags_all` filters. Two carry meaning for the engine: `network-fabric` on a service keeps it off the application views, and `landing-zone` on a shared service says a part may resolve to it by kind (see AAC-03) |
| `archetype` / `archetype_instance` | Set by expansion. Do not set by hand |
| `cmdb_ci_sys_id` / `cmdb_ci_class` | The ServiceNow link. See AAC-06 |

## Editor support

```bash
cd 50_ENGINE && python -m terrane schema
```

writes JSON Schemas into `40_SCHEMAS/`. Point the YAML language server at them and you
get field completion and enum checking while typing, rather than at validate time. The
schemas are generated from the same definitions the engine enforces, so they cannot
drift from it.
