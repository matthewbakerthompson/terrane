# AAC-10 — The business layer

The capability map, the value streams and the org structure are not authored
here. They are authored in the business architecture repository, in workshops
with the people who own the work, and imported.

## Why it is imported and not owned

Two repositories held capabilities. This one had nine, written to make the
application landscape draw; that one has a hundred and ninety-four, agreed with
the business. Both were called `capabilities`, and a system here realized a
capability the business had never heard of.

A shared metamodel did not prevent that; shared ids do. So the ids are taken
verbatim: `CAP-CRED` means Credit Decisioning & Portfolio Management on both
sides, and a sentence about it means the same thing in either repository.

```
python 50_ENGINE/tools/import_business_layer.py --from ../business-architecture
```

It runs one way, by hand rather than on every build. The business layer changes
after workshops rather than with commits, and a build should not rewrite the
model whenever a sibling repository changes.

Nothing about the application or technology estate is touched. What the import
rewrites is `10_MODEL/capabilities/`, `10_MODEL/value_streams/`,
`10_MODEL/value_stream_stages/`, `10_MODEL/org_units/`, `10_MODEL/policies/`,
`10_MODEL/controls/`, and the two relation files it owns.

## What arrived, and what it cost

| | |
|---|---|
| Capabilities | 194 — 22 level-0 domains, 136 level-1, 36 level-2 |
| Value streams | 9, with 60 stages between them |
| Org units | 40 |
| Stage-to-capability links | 139 |
| Policies and controls | 10 and 40, the governance register. See [AAC-13](AAC-13_GOVERNANCE_LAYER.md) |
| Capability-to-control and -policy links | 237, derived through the processes the business layer holds and this repository does not |

The nine capabilities and eight org units authored here were replaced, and
every reference to them re-pointed. That mapping is a judgment and is worth
recording, because it was made from the descriptions rather than the names —
the two sets were written independently and the names do not line up:

| Was | Now | |
|---|---|---|
| `CAP-ACCOUNT-SERVICING` | `CAP-SERV` | Customer Servicing & Care |
| `CAP-CARD-ISSUING` | `CAP-ORIG-06` | Account Establishment & Card Issuance |
| `CAP-COLLECTIONS` | `CAP-COLL` | Collections & Recovery |
| `CAP-CREDIT-DECISIONING` | `CAP-CRED` | Credit Decisioning & Portfolio Management |
| `CAP-CUSTOMER-ANALYTICS` | `CAP-DATA-04` | Analytics, Reporting & BI |
| `CAP-CUSTOMER-IDENTITY` | `CAP-SEC-01` | Identity & Access Management |
| `CAP-DISPUTE-MGMT` | `CAP-FRAUD` | Fraud, Disputes & Chargeback Management |
| `CAP-PAYMENT-PROCESSING` | `CAP-PAY` | Payments & Transaction Processing |
| `CAP-REGULATORY-REPORTING` | `CAP-FIN-04` | Regulatory & Financial Reporting |

Card issuing landed under originations rather than staying a domain of its
own, because in this capability model issuing a card is a step in establishing
an account. An organization that treats issuing as a business in itself changes
the map.

Org units resolve to the accountable business unit rather than to a technology
team — `ORG-PAYMENTS-ENG` became `ORG-PAYMENTS`, Payments Operations — because
`owner_org_id` answers "who do I call", and in an incident that is not the
build team. One exception is stated in the mapping script rather than inferred:
a credit underwriter reports to credit risk, not to compliance.

## The estate side of the business layer

The second import brings across what the business layer records about the
estate: the process inventory, the systems and data the processes were mapped
against in workshops, and what each process touches.

| | |
|---|---|
| Processes | 149, every one Proposed, with its value stream, owner, criticality, trigger and frequency. The steps, the flows and the BPMN stay in the business repository |
| Harvested systems | 33 that this estate did not hold, Proposed and Medium until someone who owns one says otherwise. Six more are the same thing under another id and are mapped instead |
| Harvested data assets | 10, each naming the system that is its source of truth |
| What a process touches | 713 rows: the capabilities it supports, the systems it uses and in what role, the data it uses and how, the controls and policies on it |
| Realizations | 142 derived: a system a process uses in the Primary role realizes what that process supports |
| Framework placements | 221: where in BIAN, ITIL, CRI, DMBOK or APQC each capability sits, as a path in the framework's own terms |

Two rules apply. **Aliases, not duplicates:** where the two
repositories name the same system differently, `60_SOURCES/business_layer/aliases.yaml`
says so, and a process lands on the id this estate uses; `SYS-CORE` in the
business layer is `SYS-CORE-LEDGER` here, and it arrives once. A
placeholder that is not a system, "manual, no system", is excluded with
every row that names it. **Harvested is a status:** a harvested system
carries `source: Business architecture repository`, sits in
`10_MODEL/systems/from_business_layer.yaml`, and is promoted by moving it
into its own file with a hosting, an account and a tier. The import will
not write it again once it is held.

With it the model records reach: a system's reach across the organization is
the processes that use it and the capabilities those support. The
`system-processes` view draws it, `process-systems` draws a process against
the estate, and the capability alignment diagrams carry the processes and the
framework references.

## Two fields, not one

`abstraction_level` is the TOGAF one and already meant something here.
`capability_level` is the map level: L0, L1, L2. They answer different
questions, and a capability map is conceptual at every level of itself, so the
map level needs a field of its own.

`Proposed` was added to the status vocabulary for the same reason. Proposed is
drafted and not agreed; planned is agreed and not built. Every capability in
this map is proposed — it is a straw man drafted for a workshop, not a ratified
model.

## Where the tiering comes from, and what it is worth

`capability_tier` — Direct, Core, Enable — arrived with the data. The executive
view is banded by it, which can make it look more settled than it is.

The business architecture repository's method document describes it:

> The tiering is a communication device: it lets an executive see at a glance
> which capabilities are differentiating and which are table stakes. It carries
> no structural meaning in the metamodel beyond ordering.

It is a practitioner convention, not a standard. TOGAF does not define it.
BIZBOK does not mandate it. BIAN does not use it — that repository cites BIAN
for service domain naming and APQC's process classification framework for the
enabling tier, and neither of those supplies the three bands. The nearest
formal antecedent is Porter's value chain, and that is a two-way split of
primary and support activities rather than a three-way one. Tool vendors in
this space ship versions of it under other names — Strategic / Core /
Supporting, Governing / Operating / Enabling — as a convention rather than a
defined thing.

Use it to lay out a one-page view, not to decide anything. The same goes for
`strategic_importance`. Both are judgments recorded in a straw-man model
drafted for a workshop, and no assessment has been made of either.

## The views

| View | What it answers |
|---|---|
| `capability-map` | All 136 level-1 capabilities in their 22 domains, banded Direct / Core / Enable, on one page |
| `frameworks` | Every framework against every domain: how firmly each domain follows it, and how many of its capabilities are placed in it |
| `value-streams` | The nine streams and their stages, in order, each with its exit criterion |
| `value-stream-capabilities` | One stream, its stages, and what each stage depends on |
| `capability-realization` | Which systems realize which capabilities — drawn from the systems outward, so only realized capabilities appear |

A capability map has no arrows on it. The nesting is the structure, and
dependencies between capabilities belong in a process model rather than on
the map.

The opposite question — capabilities nothing realizes — is answered by
**Coverage** as a list rather than a diagram: a diagram shows what is there,
and a report shows what is not.

## Two engine changes it forced

**Grouping by a reference field labels the boundary with the name.**
`group_by: value_stream_id` drew boxes labeled `VS-ACQUIRE-CUSTOMER`. It now
resolves the reference and uses the name, which labels the ownership view's
boundaries by name as well.

**`order_by` on a view.** Nodes inside a boundary were always sorted by label,
which is right for a landscape and wrong for anything with a sequence in it: a
value stream came out alphabetically, so *Configure Platform* preceded *Qualify
Opportunity*. `order_by` names the field the nodes are sorted by instead.
