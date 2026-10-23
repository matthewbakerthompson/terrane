# AAC-07 — Metamodel contract

This repository is downstream of a canonical metamodel, version 2, kept outside it.
Field names, primary keys and relation table names are taken from
it so that `terrane export csv` produces the layout the existing CSV validation and
Collibra import already expect, with no translation layer in between.

What this repository adds is listed here in full. The rule is that every extension is
declared: anything not in this document and not in the canonical metamodel is a typo,
and `terrane validate` warns on it as `field.unknown`.

The machine-readable version of all of this is `50_ENGINE/terrane/schema.py`, which is what
the engine enforces and what the JSON Schemas are generated from. This document
explains the reasoning; where the two differ, the file is authoritative.

## Entities used as-is

| Entity | Primary key |
|---|---|
| `systems` | `system_id` |
| `interfaces` | `interface_id` |
| `data_assets` | `data_asset_id` |
| `tech_services` | `tech_service_id` |
| `capabilities` | `capability_id` |
| `org_units` | `org_unit_id` |
| `value_streams` | `value_stream_id` |
| `policies` | `policy_id` |
| `controls` | `control_id` |
| `roadmaps` | `roadmap_id` |
| `work_packages` | `work_package_id` |
| `architecture_change_requests` | `change_request_id` |

`value_streams` is canonical, not an extension. It arrived here with the
business layer import and uses the canonical primary key; the fields on it
beyond the common set (`value_stream_type`, `stakeholders`,
`value_proposition`) are additions, because the canonical file names the entity
and its key and leaves the field list to the field dictionary.

`policies` and `controls` are canonical too, and were out of scope until the
governance layer ([AAC-13](AAC-13_GOVERNANCE_LAYER.md)). They are still owned
by the register and imported from the business layer rather than authored;
what this repository adds is the relations saying where the estate enforces
them. Three fields on them are extensions: `policy_id` on a control (which
policy it gives effect to), `external_ref` on both, and `cri_ref` on a control.

The metamodel also carries `governance_policy_ids` and `control_ids` as
semicolon-list columns on systems and data assets, and is explicit that those
are compatibility fields rather than the truth. They are declared here so an
import carrying them is not rejected, and nothing reads them: the relation
tables below are what the engine uses and what the export writes.

The three change-management entities are canonical and were out of scope until
the change layer. The metamodel names each entity and its key and leaves the
field list to the field dictionary, so the fields on them are the dictionary's,
including `start_date` and `end_date` as `YYYY-Qn` quarters. Note the key:
`architecture_change_requests` is keyed by `change_request_id`, not by the
table name with `_id` appended, and a consumer joining on the obvious guess
would find nothing.

Two of their fields need the same warning as `control_ids`. `affected_system_ids`
and `affected_process_ids` are semicolon lists on the work package and the
change request; they are declared so a canonical import is not answered with a
page of `field.unknown`, and nothing reads them. What a work package touches is
a relation table, because a list in a cell cannot be joined, filtered or drawn.
What it touches beyond its systems is derived rather than declared:
`change-footprint` reads the data those systems write, the capabilities they
realize and the processes that use either off the model, so the register
answers the business question without a second list to keep in step.

One extension field: `change_request_id` on a work package, which says what
authorized the work. It is a reference field rather than a relation for the
same reason `policy_id` on a control is — a work package proceeds on one
authorization — and without it a change request would have to repeat the system
list its own work package already carries.

## Entities in the metamodel and not modeled here

`steps` and `architecture_principles`.

These are out of scope. Step modeling belongs to a business
architecture capture effort with its own tooling and its own workshop cadence;
duplicating it here would make two copies that can disagree.
Capabilities are modeled because they are the join between the two, and because
a capability with no supporting system is a finding worth surfacing in an
application landscape.

`processes` was in this list until the business layer import brought the
process inventory across. It is modeled now, and registered as an extension
rather than as the canonical entity, because what arrives here is a harvest
rather than the source: the steps, the flows and the BPMN stay upstream, and
what this repository holds is the process and what it touches. See
[AAC-10](AAC-10_BUSINESS_LAYER.md).

## Extension: the `value_stream_stages` entity

**Primary key:** `stage_id`. **Fields:** the common set plus `value_stream_id`,
`stage_order`, `exit_criterion`, `owner_org_id`.

The canonical metamodel decomposes a value stream through `processes` and
`steps`, which is the right granularity for a process capture effort and the
wrong one for saying what the stages of a stream are. A stage is a chunk of a
stream with an exit criterion; a step is a unit of work. Both are useful and
they are not the same thing, so this sits alongside the canonical pair rather
than replacing it.

## Extension: the `products` entity

**Primary key:** `product_id`. **Fields:** the common set, plus `owner_org_id`
(required), `criticality`, `product_category`, `launch_date`.

The canonical metamodel has no entity that groups systems under a business offering.
That grouping is what an archetype instance attaches to, and what a product-scoped
view filters on.

**Proposed upstream.** This is the extension most worth folding into the canonical
metamodel, because any model that relates the application layer to the product
portfolio needs the same grouping.

## Extension: fields

Carried on every entity type:

| Field | Purpose |
|---|---|
| `company_domain` | Organizational grouping, distinct from `architecture_domain`. Already canonical on `capabilities`; extended to the other types for consistent `group_by` |
| `company_subdomain` | As above |
| `tags` | Free-form list or semicolon string. Drives `tags_any` / `tags_all` filters |
| `archetype` | Set by expansion. The archetype this entity came from |
| `archetype_instance` | Set by expansion. The instance that produced it |
| `source` | Provenance, where an entity was imported rather than authored |

On `systems`:

| Field | Purpose |
|---|---|
| `cmdb_ci_sys_id` | The ServiceNow `sys_id` link. See [AAC-06](AAC-06_CMDB_RECONCILIATION.md) |
| `cmdb_ci_class` | The ServiceNow `sys_class_name`. Source of truth is the CMDB |

On `work_packages`:

| Field | Purpose |
|---|---|
| `change_request_id` | Which decision authorized the work. A reference field for the same reason as `policy_id` on a control: work proceeding on two decisions is two work packages that were funded together |

Placement, on `systems` and `tech_services`. The canonical metamodel records
`hosting` as a single enum, which answers "cloud or not" and nothing else.
Operating or securing a workload needs its provider, account, region, zone and
network tier as well, which are what the nested infrastructure views group by;
`cidr`, `deployment_unit` and `resilience` say how it is addressed, shipped and
kept running:

| Field | Purpose |
|---|---|
| `cloud_provider` | AWS, Azure, GCP, On-prem, SaaS. Provider-neutral on purpose |
| `cloud_account` | Vended account or subscription the workload runs in |
| `region` | Cloud region, or `global` for edge services |
| `network_zone` | Edge, Public, Private-App, Private-Data, Shared-Services, On-prem |
| `availability_zone` | The zone a subnet or zonal resource sits in. Systems that span zones leave it blank, so a multi-AZ diagram does not place them in one zone |
| `cidr` | Address range, on VPCs, subnets and the data center |
| `deployment_unit` | How it is shipped: terraform, helm, and so on |
| `resilience` | Multi-region, Multi-AZ, Single-AZ, Single-node |

**Proposed upstream, second only to `products`.** The canonical metamodel has
`hosting` alone where these fields stand, and an estate in more than one account
needs them apart.

On `interfaces`:

| Field | Purpose |
|---|---|
| `integration_style` | Request-response, Event or Batch. Decides which end depends on which: a caller depends on what it calls, a consumer depends on what feeds it. Modeled rather than inferred from protocol, because protocol is a bad proxy — MQ carries both, and Kafka is realtime but still a feed. See [AAC-08](AAC-08_IMPACT_ANALYSIS.md) |
| `patterns` | The patterns from `27_PATTERNS/` this interface applies, the same field a product carries. Three of the method's reference patterns are about how two systems talk, so adoption is asked of the connection rather than of a product that may own neither end. See [AAC-11](AAC-11_DIAGRAM_KINDS_AND_BUILDING_BLOCKS.md) |
| `offered_interface_id` | The interface one end offers that this connection goes through: the API it calls, the topic it reads. Both ends are still written, since every reader of a connection asks for both; the offered interface's own system has to be one of them (`interface.offered_by`, an error), and a protocol that differs from the interface's is a warning (`interface.unlike_offered`) |

On `org_units`:

| Field | Purpose |
|---|---|
| `parent_org_unit_id` | Org hierarchy, for rolling ownership up |

## Extension: the `offered_interfaces` entity

**Primary key:** `offered_interface_id`, ids `OI-...`. **Fields:** the common
set plus `system_id` (required: the system that offers it), `owner_org_id`,
`protocol`, `integration_style`, `auth_method`, `data_classification`,
`frequency`, `specification` (where its contract is written down: an OpenAPI
or AsyncAPI file, a schema registry subject) and `patterns`.

What a system offers for others to connect to: an API, a topic, a file drop.
The canonical `interfaces` are connections between two systems, nearer
ArchiMate's flow than its application interface, so a service with forty
consumers was forty records and nothing the forty were connections to, and a
product's API was a system of its own, named for the door rather than for the
service behind it. In ArchiMate, and in TOGAF's content metamodel, what is
deployed and runs is the application component; the interface is its point of
access. The ArchiMate export writes one as an ApplicationInterface composed in
its component (the exchange format allows a component composition, aggregation
or serving to an interface, not assignment), a connection through it as a flow
ending at it, and Backstage gets it as the `API` its system provides.

A connection names the one it goes through with `offered_interface_id`, and
keeps both its ends. On a diagram its line ends at the interface, which is
drawn on its owner (see [AAC-14](AAC-14_DIAGRAM_CONVENTIONS.md)).

## Extension: the `actors` entity

**Primary key:** `actor_id`. **Fields:** the common set plus `actor_kind`,
`internal`, `owner_org_id`, `volume`.

None of the canonical metamodel's fifteen entities records the people and
organizations outside the estate, and a system context diagram cannot be
drawn without them.

The concept is not invented here even though the entity is. Something outside
the boundary that interacts with what is inside it appears as **actor** in UML
use case diagrams, which is where the word comes from; as **Business Actor**
(with **Business Role** beside it) in ArchiMate; as **Actor** in TOGAF's
content metamodel; and as **Person** on a C4 system context diagram. The
Person / Role split here follows ArchiMate's actor-and-role distinction.

The `actor_kind` list is a synthesis rather than a quotation: no standard
supplies exactly Person, Role, Organization, External system, Regulator,
Device. It is six buckets chosen because each one changes how the thing is
drawn and what questions get asked about it, and few enough that a context
diagram stays readable.

## Extension: the `flows` entity

**Primary key:** `flow_id`. **Fields:** the common set plus `trigger`,
`criticality`, `target_latency`, `owner_org_id`.

Not `processes` and `steps`, which the canonical metamodel already
has and which belong to a business architecture capture effort at a different
granularity. This is the technology question: which interfaces one transaction
traverses, in what order.

## Extension: relations

| Relation | Columns | Why |
|---|---|---|
| `system_realizes_capability` | `system_id`, `capability_id` | The canonical metamodel routes system-to-capability through `processes`. Correct for process modeling, but it leaves an application landscape unable to answer "what capability does this system realize" without a join through work this repository does not hold |
| `system_reads_writes` | `system_id`, `data_asset_id`, `operation` | Mirrors the canonical `step_reads_writes` at system granularity, for the same reason |
| `product_includes_system` | `product_id`, `system_id` | Follows from the `products` extension |
| `product_realizes_capability` | `product_id`, `capability_id` | Follows from the `products` extension |
| `actor_uses_system` | `actor_id`, `system_id`, `interaction` | Entry points only. Recording everything an actor transitively touches turns a context diagram back into a landscape |
| `flow_step` | `flow_id`, `interface_id`, `sequence` | A step is an **interface traversal**, not a system visit, so a hop that is not in the model cannot be written down |
| `tech_service_connects_to` | `from_tech_service_id`, `to_tech_service_id`, `connection` | Infrastructure to infrastructure. The canonical metamodel can say what a system runs on, but not how a VPC reaches a data center, which is what a network topology diagram draws |
| `capability_governed_by_control` | `capability_id`, `control_id`, `basis` | Derived at import from the canonical `process_governed_by_control` × `process_supports_capability`, because processes are not held here. `basis` says whether the pair came from a process directly or was rolled up from a descendant capability. See [AAC-13](AAC-13_GOVERNANCE_LAYER.md) |
| `capability_subject_to_policy` | `capability_id`, `policy_id`, `basis` | The same join, for policies |
| `work_package_affects_system` | `work_package_id`, `system_id`, `effect` | The canonical metamodel carries this as `affected_system_ids`, a semicolon list on the record, which cannot be joined, filtered or drawn. `effect` separates Builds from Changes, because a package that only builds new systems can slip and one that changes a live system is a release |
| `change_request_affects_system` | `change_request_id`, `system_id` | The same, for a decision. An approved request reaches its systems through the work package it authorized; this is for the ones with no delivery behind them, which is what a deferred decision is |

Relations used as-is: `system_uses_tech_service`,
`interface_transports_data_asset`, `system_governed_by_control`,
`system_subject_to_policy`, `data_governed_by_control`,
`data_subject_to_policy`.

## A discrepancy in the upstream metamodel

`architecture_method_field_dictionary.v1.csv` names the interface endpoint columns
`from_system` and `to_system`. `architecture_method_metamodel.v2.canonical.json` names
them `source_system_id` and `target_system_id`.

v2 is canonical, so this repository uses `source_system_id` / `target_system_id`.
`from_system` and `to_system` are accepted on load and normalized, so a file or import
written against the v1 dictionary still works.

**This is worth fixing upstream.** A pipeline that picks the wrong pair gets an
empty column and no error.

## Keeping the two in step

The dependency is a pinned copy rather than a live one, so a change in the upstream
repository does not reach the build here until the copy is updated.

When the canonical metamodel changes:

1. Diff `architecture_method_metamodel.v2.canonical.json` against
   `50_ENGINE/terrane/schema.py`.
2. Update `schema.py` for anything added or renamed.
3. Re-run `python -m terrane schema` to regenerate the JSON Schemas.
4. Run the tests and `terrane validate`.
5. Update this document if the extension set changed.

A field removed upstream that this repository still writes will surface as an unknown
column on the CSV import side rather than as a validation error here. That is the
weakest point in the arrangement: nothing here reports it, so it needs a periodic check.
