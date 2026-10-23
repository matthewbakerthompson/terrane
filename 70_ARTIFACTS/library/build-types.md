# Build types

The kinds of thing the organization builds, and the standard build of each: the parts every build of a kind has, the parts it includes unless there is a reason not to, the parts it offers as additions, and the shape that is the type on each provider. A product records its type as `build_type`, and `terrane validate` lists where it departs from the standard. Generated from `29_TYPES/` by `terrane render`; edit that, not this.

| Type | Requires | Includes | Offers | Shapes | Products |
|---|---:|---:|---:|---|---:|
| [AI inference service](#ai-service) | 1 | 0 | 5 | none | 0 |
| [Batch application](#batch-application) | 1 | 0 | 4 | none | 0 |
| [Batch data product](#data-product) | 0 | 0 | 1 | GCP: `batch-data-product-gcp`, any: `batch-data-product` | 2 |
| [Bought SaaS capability](#bought-saas) | 1 | 0 | 12 | AWS: `saas-onboarding`, Azure: `vendor-saas-service`, GCP: `vendor-saas-service-gcp` | 4 |
| [Customer-facing digital product](#digital-product) | 1 | 2 | 15 | AWS: `aws-product-onboarding`, Azure: `azure-digital-product`, GCP: `gcp-digital-product` | 6 |
| [Event-driven service](#event-driven-service) | 1 | 0 | 4 | none | 0 |
| [Integration adapter](#integration-adapter) | 1 | 0 | 3 | none | 0 |
| [Internal platform service](#platform-service) | 0 | 0 | 11 | Azure: `core-platform-service` | 1 |
| [Internal tool](#internal-tool) | 1 | 0 | 8 | none | 0 |
| [Mobile application](#mobile-application) | 1 | 0 | 7 | none | 0 |
| [Reporting application](#reporting-application) | 1 | 0 | 3 | none | 0 |
| [Shared hub](#shared-hub) | 0 | 0 | 5 | none | 0 |
| [Web application](#web-application) | 1 | 0 | 11 | none | 0 |

<a id="ai-service"></a>
## AI inference service

`ai-service`

A service that calls foundation models on the organization's behalf, with the prompts, retrieval, guardrails and audit log in one place.

**Requires.** `ml-service-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `event-consumer`, `async-worker`, `relational-datastore`, `object-store`, `search-index`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.

<a id="batch-application"></a>
## Batch application

`batch-application`

Scheduled processing with a window and an external deadline, over its own database, behind an API for whatever asks in between runs.

**Requires.** `batch-app-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `object-store`, `report-service`, `event-publisher`, `notification-service`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.

<a id="data-product"></a>
## Batch data product

`data-product`

A curated dataset on the analytics platform: an ingestion pipeline, a semantic layer the business queries, and the catalog registration that makes it governed. A tenant of the analytics landing zone, not an instance of its infrastructure.

**Requires.** nothing.
**Includes.** nothing beyond what it requires.
**Offers.** `data-hub`.
**Shapes.** GCP: `batch-data-product-gcp` (Batch data product on Google Cloud), any: `batch-data-product` (Batch data product).
**Products.** Customer 360 (`PRD-CUSTOMER-360`); Lending Portfolio Performance (`PRD-LENDING-PERFORMANCE`).

<a id="bought-saas"></a>
## Bought SaaS capability

`bought-saas`

A capability bought from a vendor and run in the vendor's own tenancy. What we build is the boundary around it: the outbound integration, the secrets it needs, how our side reaches it, and what comes back.

**Requires.** `vendor-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `private-egress`, `public-call`, `sftp-return-feed`, `webhook-inbound`, `sso-federation`, `scim-provisioning`, `audit-forwarding`, `vendor-monitoring`, `byok-encryption`, `embedded-ui`, `operator-role`, `operator-access`.
**Shapes.** AWS: `saas-onboarding` (SaaS onboarding), Azure: `vendor-saas-service` (Vendor SaaS service), GCP: `vendor-saas-service-gcp` (Vendor SaaS service on Google Cloud).
**Products.** Dispute Management (`PRD-DISPUTES`); Identity Document Verification (`PRD-IDV`); NICE Actimize Screening (`PRD-SCREENING`); Open Banking Affordability (`PRD-OB-AFFORDABILITY`).

<a id="digital-product"></a>
## Customer-facing digital product

`digital-product`

A product customers use directly: a web or mobile front end, the API behind it, its own datastore, and an event publisher onto the enterprise bus so the rest of the estate hears what happened.

**Requires.** `api-service`.
**Includes.** `web-channel`, `relational-datastore`.
**Offers.** `event-publisher`, `public-web-entry`, `async-worker`, `object-store`, `operator-role`, `operator-access`, `mobile-channel`, `admin-console`, `scheduled-job`, `event-consumer`, `notification-service`, `search-index`, `partner-adapter`, `report-service`, `ml-inference-service`.
**Shapes.** AWS: `aws-product-onboarding` (AWS product onboarding), Azure: `azure-digital-product` (Azure digital product), GCP: `gcp-digital-product` (Google Cloud digital product).
**Products.** Card Servicing (`PRD-CARD-SERVICING`); Collections Workspace (`PRD-COLLECTIONS-WORKSPACE`); Installment Lending (`PRD-INSTALLMENT-LENDING`), with integration-hub; Merchant Portal (`PRD-MERCHANT-PORTAL`); Point-of-Sale Finance (`PRD-POS-FINANCE`); Rewards Redemption (`PRD-REWARDS`).

<a id="event-driven-service"></a>
## Event-driven service

`event-driven-service`

A service that consumes another system's events, does the work in a worker, and publishes its own events for whoever is next.

**Requires.** `event-service-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `relational-datastore`, `scheduled-job`, `notification-service`, `search-index`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.

<a id="integration-adapter"></a>
## Integration adapter

`integration-adapter`

Our side of an integration with a partner system we neither run nor bought as a product: an adapter that owns the mapping, retry and credentials.

**Requires.** `adapter-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `event-publisher`, `scheduled-job`, `relational-datastore`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.

<a id="platform-service"></a>
## Internal platform service

`platform-service`

A shared service other products call through the API gateway. It has no channel of its own, and its value is measured by who consumes it.

**Requires.** nothing.
**Includes.** nothing beyond what it requires.
**Offers.** `api-service`, `relational-datastore`, `event-publisher`, `async-worker`, `operator-role`, `admin-console`, `scheduled-job`, `event-consumer`, `notification-service`, `partner-adapter`, `ml-inference-service`.
**Shapes.** Azure: `core-platform-service` (Core platform service).
**Products.** Customer Identity Service (`PRD-IDENTITY`).

<a id="internal-tool"></a>
## Internal tool

`internal-tool`

A web application staff use to operate something, behind workforce sign-on rather than the public front door, with its own database.

**Requires.** `internal-tool-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `scheduled-job`, `report-service`, `event-publisher`, `notification-service`, `search-index`, `object-store`, `operator-role`, `operator-access`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.

<a id="mobile-application"></a>
## Mobile application

`mobile-application`

A product whose channel is an app in the stores, calling its API through the shared gateway, with its own database.

**Requires.** `mobile-app-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `web-channel`, `public-web-entry`, `event-publisher`, `async-worker`, `notification-service`, `search-index`, `object-store`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.

<a id="reporting-application"></a>
## Reporting application

`reporting-application`

Reports and extracts over an operational database, behind an API and out of the transaction path.

**Requires.** `reporting-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `scheduled-job`, `admin-console`, `search-index`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.

<a id="shared-hub"></a>
## Shared hub

`shared-hub`

A hub the estate integrates through: an integration hub, an event bus, an identity provider, a network hub or a data hub. One of each kind per estate, assembled from its part rather than built on a shape.

**Requires.** nothing.
**Includes.** nothing beyond what it requires.
**Offers.** `integration-hub`, `event-hub`, `identity-hub`, `network-hub`, `data-hub`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.

<a id="web-application"></a>
## Web application

`web-application`

A browser front end behind the public front door, the API behind it, and its own database. The plainest thing the organization builds.

**Requires.** `web-app-baseline`.
**Includes.** nothing beyond what it requires.
**Offers.** `mobile-channel`, `admin-console`, `scheduled-job`, `event-publisher`, `async-worker`, `notification-service`, `search-index`, `report-service`, `object-store`, `operator-role`, `operator-access`.
**Shapes.** None: assembled from its parts against the landing zone.
**Products.** None yet.
