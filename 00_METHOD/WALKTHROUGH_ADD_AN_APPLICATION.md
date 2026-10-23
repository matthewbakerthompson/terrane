# Walkthrough — adding a new product

This walkthrough adds a product to the model and shows which views change. Every
number below was measured by running the commands on 2026-10-22, against the
sample estate as it stood that day: 902 entities and 48 views. The sample grows,
so a run today starts from wherever it has got to, and the counts differ by that.

You can do all of this in the app instead — `python 80_APP/app/server.py`, then
**New**, **Product**, and pick a shape. The commands are shown here because they are easier to
quote.

The scenario: the business is launching Spend Insights, spending by category and
merchant with budgets, for cardholders. It is built in-house on Azure, on the shape
Card Servicing and Rewards are on (`azure-digital-product`).

## Where we start

```bash
cd 50_ENGINE && python -m terrane validate --errors-only
```

```
902 entities, 2099 relationships, 48 views
0 error(s), 110 warning(s)
```

```bash
cd 50_ENGINE && python -m terrane render
```

`render` prints a line per drawing, 243 of them, since a view that takes a subject
is drawn once per subject. They are compared below.

## Step 1 — scaffold the product

```bash
cd 50_ENGINE && python -m terrane new products PRD-INSIGHTS --archetype azure-digital-product
```

That writes `10_MODEL/products/PRD-INSIGHTS.yaml` with the required fields present and
the shape's parameters listed with their descriptions. Fill it in:

```yaml
product_id: PRD-INSIGHTS
name: Spend Insights
description: Spending by category and merchant, with budgets, for cardholders.
status: Active
owner_org_id: ORG-DIGITAL
criticality: Medium
product_category: Digital channel
company_domain: Servicing

archetype: azure-digital-product
parameters:
  slug: insights
  product_name: Spend Insights
  owner_org: ORG-DIGITAL
  domain: Servicing
  account: azure-cards-prod
  criticality: Medium
  classification: Confidential
```

The edit is these seventeen lines of YAML.

## Step 2 — see what it produced

```bash
cd 50_ENGINE && python -m terrane validate --errors-only
```

```
916 entities, 2122 relationships, 48 views
0 error(s), 114 warning(s)
```

Fourteen entities, the product among them, and twenty-three relationships:

| Produced | |
|---|---|
| `SYS-INSIGHTS-WEB` | Browser front end |
| `SYS-INSIGHTS-API` | The service behind the product's API |
| `SYS-INSIGHTS-STORE` | Its database |
| `SYS-INSIGHTS-EVENTS` | Event publisher |
| `OI-INSIGHTS-API` | The API the service offers, over HTTPS |
| `INT-INSIGHTS-WEB-API` | Web to API, HTTPS, OAuth2, through `OI-INSIGHTS-API` |
| `INT-INSIGHTS-API-STORE` | API to database, TDS, managed identity |
| `INT-INSIGHTS-API-EVENTS` | API to event publisher, AMQP, managed identity |
| `DA-INSIGHTS-OPERATIONAL` | Operational data, Confidential, PII flagged, mastered in the database |
| `TS-INSIGHTS-DNS`, `TS-INSIGHTS-WAF` | DNS and a web application firewall in front of the web tier |
| `TS-INSIGHTS-CACHE` | A cache beside the service |
| `TS-INSIGHTS-BACKUP` | Backup and recovery for the database |
| plus 23 relations | product membership (4), platform dependencies (13), data use (2), the services' own wiring (4) |

The shape supplies "this API runs on AKS, is published through APIM, reads its
secrets from Key Vault and reports to Azure Monitor", because that is how this
organization builds digital products.

## Step 3 — render

```bash
cd 50_ENGINE && python -m terrane render
```

The lines that changed, with what they were:

```
ownership                          report    94 nodes   46 edges   <- was 90 / 42
application-landscape              map       59 nodes   67 edges   <- was 55 / 64
capability-realization             report    60 nodes    1 edges   <- was 60 / 5
integration-architecture           diagram   47 nodes   51 edges   <- was 46 / 52
parts-in-use                       map       46 nodes   36 edges   <- was 42 / 33
lifecycle-portfolio                map       50 nodes   62 edges   <- was 50 / 64
domain-servicing                   diagram   28 nodes   34 edges   <- was 23 / 30
product-architecture--prd-insights diagram   17 nodes   19 edges   <- new
product-parts--prd-insights        diagram   17 nodes   19 edges   <- new
data-landscape                     map       24 nodes    0 edges   <- was 23 / 0
data-lineage                       report    50 nodes   60 edges   <- was 47 / 57
pii-data-flow                      report    32 nodes   42 edges   <- was 29 / 39
data-dissemination                 diagram   47 nodes   24 edges   <- was 45 / 23
platform-dependencies              report    98 nodes  118 edges   <- was 91 / 106
tiered-architecture                diagram   61 nodes   66 edges   <- was 57 / 63
hosting-estate                     map       59 nodes   67 edges   <- was 55 / 64
onboarding--prd-insights           diagram    5 nodes    4 edges   <- new
```

**No file in `30_VIEWS/` was touched.** Spend Insights appears in the landscape, the
hosting, lifecycle and tier views because its systems are active and placed; in the
servicing domain's drawing because its domain is Servicing; under its owner in
`ownership`; in `platform-dependencies` because it uses AKS, APIM and Key Vault; in
the four data views because it holds a data asset, PII flagged; and among the parts
in use because the shape built it from parts. A product on a shape is drawn three
times on its own: whole, by part, and as its onboarding. It is in no other
product's drawing, in no system architecture (those are drawn for the
high-criticality systems, and these are Medium), and in nothing in the change layer,
since no work package builds it.

`capability-realization`, `integration-architecture` and `lifecycle-portfolio` were
past their `limits.max_nodes` before Spend Insights, and `render` says so on their
lines. Four more systems change which entities make the cut, which is why those three
lose edges.

No step in this walkthrough opens a diagram.

## Step 4 — read the output

Two things in that output need attention.

**Warnings went from 110 to 114.** Four new `cmdb.unlinked` warnings, one per new
system, because none of them has a ServiceNow CI recorded yet. A system that exists
in the architecture and not in the CMDB is a gap, and the warning count records it.

**Nothing says which capability Spend Insights realizes.** `terrane needs` says what a
view needs from the records and how many lack it:

```bash
cd 50_ENGINE && python -m terrane needs capability-realization
```

Its line for the capability link reads `43 of 59 lack it`, where it read 39 of 55
before: the four new systems are among them. Add the link to the product's own file,
under `extra`, which keeps relations an instance owns with the instance:

```yaml
extra:
  relations:
    system_realizes_capability:
      - system_id: SYS-INSIGHTS-WEB
        capability_id: CAP-SERV-03
      - system_id: SYS-INSIGHTS-API
        capability_id: CAP-SERV-03
    product_realizes_capability:
      - product_id: PRD-INSIGHTS
        capability_id: CAP-SERV-03
```

`CAP-SERV-03` is Digital Self-Service, under Customer Servicing & Care. Validate reads
2,125 relationships and `needs` reads 41 of 59. Re-render, and the domain's own
drawing, `capability-alignment--cap-serv`, reads 37 nodes and 55 edges, from 35 and
53: the two systems that realize it.

## Step 5 — the departures

A product can depart from its shape. Say Spend Insights publishes no events, since
nothing downstream listens to it, and its web tier is Tier 1:

```yaml
overrides:
  SYS-INSIGHTS-WEB:
    service_tier: Tier 1

exclude:
  - SYS-INSIGHTS-EVENTS
```

Excluding the event publisher also drops `INT-INSIGHTS-API-EVENTS`, the publisher's
membership of the product and its dependency on Service Bus, and names the interface
in a warning:

```
warn  model.load  PRD-INSIGHTS: INT-INSIGHTS-API-EVENTS dropped because it
                  referenced excluded SYS-INSIGHTS-EVENTS
```

Validate reads 914 entities and 2,123 relationships, with no errors; the warnings stay
at 114, one `cmdb.unlinked` gone with the publisher and the `model.load` line added.

A connection the shape cannot know about, such as Spend Insights reading transactions
from the core ledger, is written by hand: under `extra.interfaces` in the same file,
the way `PRD-REWARDS` connects its worker to the ledger, or in `10_MODEL/interfaces/`.

## Step 6 — commit

```bash
cd 50_ENGINE && python -m terrane validate
```

```bash
cd 50_ENGINE && python -m terrane refresh
```

`refresh` regenerates everything that is committed: the drawings, the schemas and the
exports. Commit the model file and what it rewrote. The pull request shows the change
to one file and the diagram changes it caused, in one diff, for a reviewer who does
not have to run anything.

## What this cost

One file: seventeen lines of YAML, ten more for the capability link and five for the
departures. The first render changed fourteen views and added three drawings, the
capability link changed one more, and none was edited.
