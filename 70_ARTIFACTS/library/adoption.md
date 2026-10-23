# Shapes and the estate

Which products sit on a shape and how far each has moved from it, which hand-authored products have the systems a shape's parts would make and are not on one, and which fit no shape. Drift is read from each product's own file, since what a product says beyond its shape is stripped when the shape expands; a candidate is a product whose systems, by category, are the shape's required parts. Generated from `10_MODEL/products/`, `20_ARCHETYPES/` and `28_MODULES/` by `terrane render`; edit those, not this.

12 products on a shape, 1 assembled from parts, 0 candidates, 0 fitting no shape.

## Assembled from parts

Products made of the library's parts with no shape, each from its own `compose` block. The second project like one of these is when a shape is worth naming.

| Product | Provider | Parts |
|---|---|---|
| Merchant Portal (`PRD-MERCHANT-PORTAL`) | Azure | `api-service`, `web-channel`, `relational-datastore`, `event-publisher`, `operator-role` |

## On a shape

Moves counts every way a product differs from a bare instance of its shape: an answer that is not the default, an override, a record under `extra`, a part added or dropped, a slot chosen against its default, an id kept under the estate's name. A high count is not a fault; it is where the shape's next default lives.

| Product | Shape | Answers | Overrides | Extra | Added | Dropped | Choices | Kept ids | Moves |
|---|---|---|---|---|---|---|---|---|---:|
| Card Servicing (`PRD-CARD-SERVICING`) | `azure-digital-product` | `classification`, `criticality` | `DA-CARDSVC-OPERATIONAL`, `INT-CARDSVC-API-STORE`, `SYS-CARDSVC-API`, `SYS-CARDSVC-EVENTS`, `SYS-CARDSVC-STORE`, `SYS-CARDSVC-WEB` | — | — | — | — | — | 8 |
| Collections Workspace (`PRD-COLLECTIONS-WORKSPACE`) | `azure-digital-product` | `classification` | `DA-COLLECT-OPERATIONAL`, `INT-COLLECT-API-STORE`, `SYS-COLLECT-API`, `SYS-COLLECT-STORE`, `SYS-COLLECT-WEB` | — | — | `event-publisher` | — | — | 7 |
| Customer 360 (`PRD-CUSTOMER-360`) | `batch-data-product` | `classification` | `INT-CUST360-INGEST`, `INT-CUST360-PIPE-SEMANTIC` | — | — | — | — | — | 3 |
| Dispute Management (`PRD-DISPUTES`) | `vendor-saas-service` | `classification` | `DA-DISPUTES-VENDOR-FEED`, `INT-DISPUTES-GATEWAY-SAAS`, `INT-DISPUTES-SAAS-FEED`, `INT-DISPUTES-UP-GATEWAY`, `SYS-DISPUTES-GATEWAY`, `SYS-DISPUTES-SAAS` | — | — | — | reach: `public-call`, return: `sftp-return-feed` | `DA-DISPUTES-OUTCOMES`, `INT-DISPUTES-CALLER-GATEWAY`, `INT-DISPUTES-GATEWAY-VENDOR`, `INT-DISPUTES-VENDOR-RETURN`, `SYS-DISPUTES-VENDOR` | 12 |
| Customer Identity Service (`PRD-IDENTITY`) | `core-platform-service` | `classification` | `SYS-IDENTITY-SVC` | — | — | — | — | — | 2 |
| Identity Document Verification (`PRD-IDV`) | `vendor-saas-service` | `classification`, `criticality` | `SYS-IDV-EGRESS`, `SYS-IDV-GATEWAY`, `SYS-IDV-VENDOR`, `SYS-IDV-WEBHOOKS` | 1 relations | — | — | reach: `private-egress` (not the default), return: `webhook-inbound` (not the default) | — | 9 |
| Installment Lending (`PRD-INSTALLMENT-LENDING`) | `aws-product-onboarding` | — | `SYS-LENDING-API`, `SYS-LENDING-BUCKET` | — | `integration-hub`, `applicant-access`, `underwriter-access` | — | — | — | 5 |
| Lending Portfolio Performance (`PRD-LENDING-PERFORMANCE`) | `batch-data-product-gcp` | — | — | 1 interfaces, 2 relations | — | — | — | — | 3 |
| Open Banking Affordability (`PRD-OB-AFFORDABILITY`) | `vendor-saas-service-gcp` | `classification` | `SYS-OBAFF-VENDOR` | 6 relations | — | — | reach: `private-egress`, return: `webhook-inbound` | — | 8 |
| Point-of-Sale Finance (`PRD-POS-FINANCE`) | `gcp-digital-product` | — | `SYS-POSFIN-API` | — | — | — | — | — | 1 |
| Rewards Redemption (`PRD-REWARDS`) | `azure-digital-product` | — | `SYS-REWARDS-API`, `SYS-REWARDS-WORKER` | 1 interfaces | `async-worker` | — | — | — | 4 |
| NICE Actimize Screening (`PRD-SCREENING`) | `saas-onboarding` | — | `SYS-SCREENING-GATEWAY`, `SYS-SCREENING-VENDOR` | 3 relations | `operator-role` | — | reach: `private-egress`, return: `sftp-return-feed` | — | 6 |

## Candidates

Hand-authored products whose systems are, by category, what a shape's required parts make. Not a fault: the shape came after the product. It is a product that is a handful of answers away from being on one, and `terrane validate` says so (`library.shape_candidate`).

None.

## No shape fits

None.
