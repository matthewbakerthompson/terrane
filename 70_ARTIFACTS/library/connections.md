# Connection kinds

The ways two systems are connected here: each kind a recurring shape of integration style, protocol and authentication, with the pattern that says how that kind is built. An interface is of a kind when its style is the kind's and its protocol one of the kind's, read off its own fields, so this counts the estate as it is whether or not anyone chose a kind. Generated from `24_CONNECTIONS/` by `terrane render`; edit that, not this.

113 of 115 interfaces are of a kind; 2 of none.

| Kind | Style | Protocols | Pattern | Interfaces |
|---|---|---|---|---:|
| [API call](#api-call) | Request-response | HTTPS | `api-front-door` | 39 |
| [Request on a queue](#queued-request) | Request-response | MQ | none | 6 |
| [Its own datastore](#own-datastore) | Request-response | TDS, PostgreSQL | `stateless-request-service` | 6 |
| [Private path to a vendor](#private-egress) | Request-response | PrivateLink | `private-egress-to-saas` | 3 |
| [Sign-on federation](#sign-on-federation) | Request-response | SAML, OIDC | none | 1 |
| [Event on the bus](#event) | Event | AMQP, Kafka, Pub/Sub | `event-fanout` | 14 |
| [Event over HTTPS](#event-over-https) | Event | HTTPS | `api-front-door` | 10 |
| [Log stream](#log-stream) | Event | Syslog | `observed-service` | 1 |
| [Scheduled file](#scheduled-file) | Batch | FileTransfer | `windowed-batch` | 18 |
| [Partner file](#partner-file) | Batch | SFTP | `partner-file-exchange` | 2 |
| [Pipeline load](#pipeline-load) | Batch | SQL, Snowpipe, S3 | `analytics-landing-zone` | 8 |
| [Scheduled API pull](#scheduled-pull) | Batch | HTTPS | none | 5 |

<a id="api-call"></a>
## API call

`api-call`

One system calls another's API and waits for the answer. The house rule is that every programmatic entry point sits behind the gateway, so the caller is coupled to a contract rather than to a service.

**Proposed with.** integration style Request-response, protocol HTTPS, auth method OAuth2, frequency Realtime, direction Outbound, patterns api-front-door.
**Pattern.** `api-front-door` (API front door, Approved).
**Interfaces.** 39 in the estate:

- Authorization Switch to Tokenization Service (`INT-AUTH-TOKEN`): SYS-AUTH-SWITCH to SYS-TOKEN
- Card Servicing Service to Identity Service (`INT-CARDSVC-API-IDENTITY`): SYS-CARDSVC-API to SYS-IDENTITY-SVC
- Card Servicing Web to API (`INT-CARDSVC-WEB-API`): SYS-CARDSVC-WEB to SYS-CARDSVC-API
- Collections Service to Identity Service (`INT-COLLECT-API-IDENTITY`): SYS-COLLECT-API to SYS-IDENTITY-SVC
- Collections Workspace Web to API (`INT-COLLECT-WEB-API`): SYS-COLLECT-WEB to SYS-COLLECT-API
- Contact Center Platform to CRM (`INT-CONTACT-CRM`): SYS-CONTACT to SYS-CRM
- Contact Center Platform to Identity and Access Management (`INT-CONTACT-IAM`): SYS-CONTACT to SYS-IAM
- CRM to Dispute Gateway (`INT-CRM-DISPUTES`): SYS-CRM to SYS-DISPUTES-GATEWAY
- CRM to Identity and Access Management (`INT-CRM-IAM`): SYS-CRM to SYS-IAM
- Servicing CRM to Core Ledger (`INT-CRM-LEDGER`): SYS-CRM to SYS-CORE-LEDGER
- Dispute Management Platform Gateway to Pegasystems (`INT-DISPUTES-GATEWAY-SAAS`): SYS-DISPUTES-GATEWAY to SYS-DISPUTES-SAAS
- SYS-CORE-LEDGER to Dispute Management Platform Gateway (`INT-DISPUTES-UP-GATEWAY`): SYS-CORE-LEDGER to SYS-DISPUTES-GATEWAY
- Document Management to Servicing Client Portal (`INT-DOC-CLIENT-PORTAL`): SYS-CLIENT-PORTAL to SYS-DOC
- Transaction Fraud Detection to Model Platform (`INT-FRAUD-MODEL`): SYS-FRAUD-DETECT to SYS-MODEL
- SYS-IDENTITY-SVC to Identity Document Verification Gateway (`INT-IDV-CALLER-GATEWAY`): SYS-IDENTITY-SVC to SYS-IDV-GATEWAY
- Identity Document Verification Gateway to Private Egress (`INT-IDV-GATEWAY-EGRESS`): SYS-IDV-GATEWAY to SYS-IDV-EGRESS
- IVR to Card Servicing API (`INT-IVR-CARDSVC`): SYS-IVR to SYS-CARDSVC-API
- Installment Lending Load Balancer to Web (`INT-LENDING-ALB-WEB`): SYS-LENDING-ALB to SYS-LENDING-WEB
- Installment Lending Service to Object Store (`INT-LENDING-API-BUCKET`): SYS-LENDING-API to SYS-LENDING-BUCKET
- Installment Lending Service to Credit Bureau (`INT-LENDING-API-BUREAU`): SYS-LENDING-API to SYS-CREDIT-BUREAU
- Installment Lending Service to Identity Service (`INT-LENDING-API-IDENTITY`): SYS-LENDING-API to SYS-IDENTITY-SVC
- CORE-LEDGER via Installment Lending hub (`INT-LENDING-CORE-LEDGER-HUB`): SYS-CORE-LEDGER to SYS-LENDING-HUB
- CREDIT-BUREAU via Installment Lending hub (`INT-LENDING-CREDIT-BUREAU-HUB`): SYS-CREDIT-BUREAU to SYS-LENDING-HUB
- CRM via Installment Lending hub (`INT-LENDING-CRM-HUB`): SYS-CRM to SYS-LENDING-HUB
- Installment Lending Edge to Load Balancer (`INT-LENDING-EDGE-ALB`): SYS-LENDING-EDGE to SYS-LENDING-ALB
- Installment Lending Web to API (`INT-LENDING-WEB-API`): SYS-LENDING-WEB to SYS-LENDING-API
- Merchant Portal Web to API (`INT-MERCHANT-WEB-API`): SYS-MERCHANT-WEB to SYS-MERCHANT-API
- Cardholder Mobile to Card Servicing API (`INT-MOBILE-CARDSVC`): SYS-MOBILE to SYS-CARDSVC-API
- Cardholder Mobile to Tokenization Service (`INT-MOBILE-TOKEN`): SYS-MOBILE to SYS-TOKEN
- SYS-POSFIN-API to Open Banking Affordability Gateway (`INT-OBAFF-CALLER-GATEWAY`): SYS-POSFIN-API to SYS-OBAFF-GATEWAY
- Open Banking Affordability Gateway to Private Egress (`INT-OBAFF-GATEWAY-EGRESS`): SYS-OBAFF-GATEWAY to SYS-OBAFF-EGRESS
- Originations Decision Engine to Application Fraud Screening (`INT-ORIG-APPFRAUD`): SYS-ORIG-DECISION to SYS-APPFRAUD
- Originations Decision Engine to Credit Data Environment (`INT-ORIG-CREDIT-DATA`): SYS-ORIG-DECISION to SYS-CREDIT-DATA
- Originations Decision Engine to Identity Verification (`INT-ORIG-KYC`): SYS-ORIG-DECISION to SYS-KYC
- Originations Decision Engine to Model Platform (`INT-ORIG-MODEL`): SYS-ORIG-DECISION to SYS-MODEL
- Point-of-Sale Finance Web to API (`INT-POSFIN-WEB-API`): SYS-POSFIN-WEB to SYS-POSFIN-API
- Rewards Redemption Web to API (`INT-REWARDS-WEB-API`): SYS-REWARDS-WEB to SYS-REWARDS-API
- SYS-AUTH-SWITCH to NICE Actimize Screening Gateway (`INT-SCREENING-CALLER-GATEWAY`): SYS-AUTH-SWITCH to SYS-SCREENING-GATEWAY
- NICE Actimize Screening Gateway to Private Egress (`INT-SCREENING-GATEWAY-EGRESS`): SYS-SCREENING-GATEWAY to SYS-SCREENING-EGRESS

<a id="queued-request"></a>
## Request on a queue

`queued-request`

A request put on a message queue for a system that answers in its own time and in order: how a mainframe ledger is spoken to. The queue is the contract, and the answer comes back the same way.

**Proposed with.** integration style Request-response, protocol MQ, auth method MutualTLS, frequency Realtime, direction Outbound.
**Interfaces.** 6 in the estate:

- Authorization Switch to Core Ledger (`INT-AUTH-LEDGER`): SYS-AUTH-SWITCH to SYS-CORE-LEDGER
- Card Servicing Service to Core Ledger (`INT-CARDSVC-API-LEDGER`): SYS-CARDSVC-API to SYS-CORE-LEDGER
- Collections Service to Core Ledger (`INT-COLLECT-API-LEDGER`): SYS-COLLECT-API to SYS-CORE-LEDGER
- Installment Lending Service to Core Card Ledger (`INT-LENDING-API-LEDGER`): SYS-LENDING-API to SYS-CORE-LEDGER
- Payment Capture Gateway to Core Card Ledger (`INT-PAYMENT-GW-LEDGER`): SYS-PAYMENT-GW to SYS-CORE-LEDGER
- Rewards Redemption Worker to Core Ledger (`INT-REWARDS-WORKER-LEDGER`): SYS-REWARDS-WORKER to SYS-CORE-LEDGER

<a id="own-datastore"></a>
## Its own datastore

`own-datastore`

A service reading and writing the store that holds its state. Not an integration between two systems: the store is the service's own, and a second system reaching into it would be the deprecated shared database.

**Proposed with.** integration style Request-response, protocol TDS, auth method ManagedIdentity, frequency Realtime, direction Outbound, patterns stateless-request-service.
**Pattern.** `stateless-request-service` (Stateless request service, Approved).
**Interfaces.** 6 in the estate:

- Card Servicing Service to Datastore (`INT-CARDSVC-API-STORE`): SYS-CARDSVC-API to SYS-CARDSVC-STORE
- Collections Workspace Service to Datastore (`INT-COLLECT-API-STORE`): SYS-COLLECT-API to SYS-COLLECT-STORE
- Installment Lending Service to Database (`INT-LENDING-API-DB`): SYS-LENDING-API to SYS-LENDING-DB
- Merchant Portal Service to Database (`INT-MERCHANT-API-STORE`): SYS-MERCHANT-API to SYS-MERCHANT-STORE
- Point-of-Sale Finance Service to Database (`INT-POSFIN-API-DB`): SYS-POSFIN-API to SYS-POSFIN-DB
- Rewards Redemption Service to Database (`INT-REWARDS-API-STORE`): SYS-REWARDS-API to SYS-REWARDS-STORE

<a id="private-egress"></a>
## Private path to a vendor

`private-egress`

A call out to a bought service over a private endpoint rather than the internet, through a gateway we own: the boundary we run when somebody else runs the software.

**Proposed with.** integration style Request-response, protocol PrivateLink, auth method MutualTLS, frequency Realtime, direction Outbound, patterns private-egress-to-saas.
**Pattern.** `private-egress-to-saas` (Private egress to a bought service, Approved).
**Interfaces.** 3 in the estate:

- Private Egress to Onfido (`INT-IDV-EGRESS-VENDOR`): SYS-IDV-EGRESS to SYS-IDV-VENDOR
- Private Egress to TrueLayer (`INT-OBAFF-EGRESS-VENDOR`): SYS-OBAFF-EGRESS to SYS-OBAFF-VENDOR
- Private Egress to NICE Actimize (`INT-SCREENING-EGRESS-VENDOR`): SYS-SCREENING-EGRESS to SYS-SCREENING-VENDOR

<a id="sign-on-federation"></a>
## Sign-on federation

`sign-on-federation`

A bought service trusting our identity provider rather than keeping its own accounts: one place to grant and revoke, and no vendor holding a password of ours.

**Proposed with.** integration style Request-response, protocol SAML, auth method Certificate, frequency Realtime, direction Outbound.
**Interfaces.** 1 in the estate:

- Identity Federation to NICE Actimize (`INT-SCREENING-FEDERATION-VENDOR`): SYS-SCREENING-FEDERATION to SYS-SCREENING-VENDOR

<a id="event"></a>
## Event on the bus

`event`

A system publishes what happened and never learns who consumed it. Consumers arrive and leave without the producer changing.

**Proposed with.** integration style Event, protocol AMQP, auth method OAuth2, frequency Realtime, direction Outbound, patterns event-fanout.
**Pattern.** `event-fanout` (Event fan-out, Approved).
**Interfaces.** 14 in the estate:

- Card Servicing Service to Event Publisher (`INT-CARDSVC-API-EVENTS`): SYS-CARDSVC-API to SYS-CARDSVC-EVENTS
- Card Servicing Events to Data Ingestion Hub (`INT-CARDSVC-EVENTS-INGEST`): SYS-CARDSVC-EVENTS to SYS-DATA-INGEST
- Collections Platform to Document Management (`INT-COLLECT-DOC`): SYS-COLLECT-API to SYS-DOC
- Outbound Contact Platform to Collections Platform (`INT-DIALER-COLLECT`): SYS-DIALER to SYS-COLLECT-API
- Transaction Fraud Detection to CRM (`INT-FRAUD-CRM`): SYS-FRAUD-DETECT to SYS-CRM
- Identity Verification to Financial Crimes Platform (`INT-KYC-AML`): SYS-KYC to SYS-AML
- Installment Lending Service to Async Worker (`INT-LENDING-API-WORKER`): SYS-LENDING-API to SYS-LENDING-WORKER
- Source events to Lending Portfolio Performance Pipeline (`INT-LENDPERF-INGEST`): SYS-POSFIN-EVENTS to SYS-LENDPERF-PIPELINE
- Campaign Management to CRM (`INT-MARKETING-CRM`): SYS-MARKETING to SYS-CRM
- Merchant Portal Service to Event Publisher (`INT-MERCHANT-API-EVENTS`): SYS-MERCHANT-API to SYS-MERCHANT-EVENTS
- Originations Decision Engine to Document Management (`INT-ORIG-DOC`): SYS-ORIG-DECISION to SYS-DOC
- Point-of-Sale Finance Service to Event Publisher (`INT-POSFIN-API-EVENTS`): SYS-POSFIN-API to SYS-POSFIN-EVENTS
- Rewards Redemption Service to Event Publisher (`INT-REWARDS-API-EVENTS`): SYS-REWARDS-API to SYS-REWARDS-EVENTS
- Rewards Redemption Service to Async Worker (`INT-REWARDS-API-WORKER`): SYS-REWARDS-API to SYS-REWARDS-WORKER

<a id="event-over-https"></a>
## Event over HTTPS

`event-over-https`

An event delivered to an endpoint rather than to the bus: a webhook from a bought service, or a platform's own event delivery. The endpoint is a programmatic entry point, so it sits behind the gateway like any other.

**Proposed with.** integration style Event, protocol HTTPS, auth method OAuth2, frequency Realtime, direction Inbound, patterns api-front-door.
**Pattern.** `api-front-door` (API front door, Approved).
**Interfaces.** 10 in the estate:

- Onfido webhooks (`INT-IDV-VENDOR-WEBHOOKS`): SYS-IDV-VENDOR to SYS-IDV-WEBHOOKS
- Identity Document Verification Webhook Listener to SYS-IDENTITY-SVC (`INT-IDV-WEBHOOKS-CONSUMER`): SYS-IDV-WEBHOOKS to SYS-IDENTITY-SVC
- Enterprise Data Platform to Governance Catalog (`INT-INGEST-CATALOG`): SYS-DATA-INGEST to SYS-CATALOG
- TrueLayer webhooks (`INT-OBAFF-VENDOR-WEBHOOKS`): SYS-OBAFF-VENDOR to SYS-OBAFF-WEBHOOKS
- Open Banking Affordability Webhook Listener to SYS-POSFIN-API (`INT-OBAFF-WEBHOOKS-CONSUMER`): SYS-OBAFF-WEBHOOKS to SYS-POSFIN-API
- Observability Platform to IT Service Management (`INT-OBSERV-ITSM`): SYS-OBSERV to SYS-ITSM
- Source Control and Pipeline to IT Service Management (`INT-SCM-ITSM`): SYS-SCM to SYS-ITSM
- Source Control and Pipeline to Test Management (`INT-SCM-TESTMGMT`): SYS-SCM to SYS-TESTMGMT
- NICE Actimize audit log to security monitoring (`INT-SCREENING-VENDOR-AUDIT`): SYS-SCREENING-VENDOR to SYS-SIEM
- Security Monitoring to IT Service Management (`INT-SIEM-ITSM`): SYS-SIEM to SYS-ITSM

<a id="log-stream"></a>
## Log stream

`log-stream`

Logs shipped as they are written to where they are watched. What makes a service observed rather than merely logging.

**Proposed with.** integration style Event, protocol Syslog, auth method MutualTLS, frequency Realtime, direction Outbound, patterns observed-service.
**Pattern.** `observed-service` (Observed service, Approved).
**Interfaces.** 1 in the estate:

- Identity and Access Management to Security Monitoring (`INT-IAM-SIEM`): SYS-IAM to SYS-SIEM

<a id="scheduled-file"></a>
## Scheduled file

`scheduled-file`

A file produced on a schedule for another system to pick up, with a window it has to arrive in. Lateness is a business event, so the window is modeled rather than assumed.

**Proposed with.** integration style Batch, protocol FileTransfer, auth method MutualTLS, frequency Daily, direction Outbound, patterns windowed-batch.
**Pattern.** `windowed-batch` (Windowed batch, Approved).
**Interfaces.** 18 in the estate:

- Credit Bureau Gateway to Credit Bureau (`INT-BUREAU-GW-BUREAU`): SYS-BUREAU-GW to SYS-CREDIT-BUREAU
- Credit Bureau Gateway to CRM (`INT-BUREAU-GW-CRM`): SYS-BUREAU-GW to SYS-CRM
- Collections Platform to Outbound Contact Platform (`INT-COLLECT-DIALER`): SYS-COLLECT-API to SYS-DIALER
- General Ledger to Treasury Management (`INT-GL-TREASURY`): SYS-GL to SYS-TREASURY
- HR Information System to Identity and Access Management (`INT-HRIS-IAM`): SYS-HRIS to SYS-IAM
- Core Card Ledger to Financial Crimes Platform (`INT-LEDGER-AML`): SYS-CORE-LEDGER to SYS-AML
- Core Card Ledger to Credit Bureau Gateway (`INT-LEDGER-BUREAU-GW`): SYS-CORE-LEDGER to SYS-BUREAU-GW
- Core Card Ledger to Card Production (`INT-LEDGER-CARD-FULFILL`): SYS-CORE-LEDGER to SYS-CARD-FULFILL
- Core Card Ledger to Servicing Client Portal (`INT-LEDGER-CLIENT-PORTAL`): SYS-CORE-LEDGER to SYS-CLIENT-PORTAL
- Core Card Ledger to Document Management (`INT-LEDGER-DOC`): SYS-CORE-LEDGER to SYS-DOC
- Core Card Ledger to General Ledger (`INT-LEDGER-GL`): SYS-CORE-LEDGER to SYS-GL
- Core Ledger to Data Ingestion Hub (`INT-LEDGER-INGEST`): SYS-CORE-LEDGER to SYS-DATA-INGEST
- Core Card Ledger to Reconciliation Platform (`INT-LEDGER-RECON`): SYS-CORE-LEDGER to SYS-RECON
- Core Ledger to Statement Generation (`INT-LEDGER-STATEMENTS`): SYS-CORE-LEDGER to SYS-STATEMENTS
- Originations Decision Engine to Core Card Ledger (`INT-ORIG-LEDGER-BOARD`): SYS-ORIG-DECISION to SYS-CORE-LEDGER
- Payment Capture Gateway to General Ledger (`INT-PAYMENT-GW-GL`): SYS-PAYMENT-GW to SYS-GL
- Prospect Data Services to Campaign Management (`INT-PROSPECT-MARKETING`): SYS-PROSPECT-DATA to SYS-MARKETING
- Statement Generation to Document Management (`INT-STATEMENTS-DOC`): SYS-STATEMENTS to SYS-DOC

<a id="partner-file"></a>
## Partner file

`partner-file`

Files exchanged with a party outside the estate that was never going to build an API: landed under orchestration that knows when one is late.

**Proposed with.** integration style Batch, protocol SFTP, auth method KeyPair, frequency Daily, direction Inbound, patterns partner-file-exchange.
**Pattern.** `partner-file-exchange` (Partner file exchange, Approved).
**Interfaces.** 2 in the estate:

- Pegasystems return feed (`INT-DISPUTES-SAAS-FEED`): SYS-DISPUTES-SAAS to SYS-DATA-INGEST
- NICE Actimize return feed (`INT-SCREENING-VENDOR-RETURN`): SYS-SCREENING-VENDOR to SYS-DATA-INGEST

<a id="pipeline-load"></a>
## Pipeline load

`pipeline-load`

Data landed once and built forward: from ingestion into the warehouse, and from one layer of the warehouse to the next. Where lineage is recorded or lost.

**Proposed with.** integration style Batch, protocol SQL, auth method KeyPair, frequency Daily, direction Outbound, patterns analytics-landing-zone.
**Pattern.** `analytics-landing-zone` (Analytics landing zone, Approved).
**Interfaces.** 8 in the estate:

- Ingest to Customer 360 Pipeline (`INT-CUST360-INGEST`): SYS-DATA-INGEST to SYS-CUST360-PIPELINE
- Customer 360 Pipeline to Semantic Layer (`INT-CUST360-PIPE-SEMANTIC`): SYS-CUST360-PIPELINE to SYS-CUST360-SEMANTIC
- Customer 360 Semantic Layer to Regulatory Reporting Engine (`INT-CUST360-REGREPORTING`): SYS-CUST360-SEMANTIC to SYS-REG-REPORTING
- General Ledger to Reconciliation Platform (`INT-GL-RECON`): SYS-GL to SYS-RECON
- Enterprise Data Platform to Credit Data Environment (`INT-INGEST-CREDIT-DATA`): SYS-DATA-INGEST to SYS-CREDIT-DATA
- Enterprise Data Platform to Model Platform (`INT-INGEST-MODEL`): SYS-DATA-INGEST to SYS-MODEL
- Installment Lending Worker to Data Ingestion Hub (`INT-LENDING-WORKER-INGEST`): SYS-LENDING-WORKER to SYS-DATA-INGEST
- Lending Portfolio Performance Pipeline to Semantic Layer (`INT-LENDPERF-PIPE-SEMANTIC`): SYS-LENDPERF-PIPELINE to SYS-LENDPERF-SEMANTIC

<a id="scheduled-pull"></a>
## Scheduled API pull

`scheduled-pull`

A batch of records fetched over an API on a schedule: evidence gathered for an audit trail, figures collected for a return. An API used as a file.

**Proposed with.** integration style Batch, protocol HTTPS, auth method OAuth2, frequency Weekly, direction Inbound.
**Interfaces.** 5 in the estate:

- Architecture Repository to Governance, Risk and Compliance (`INT-ARCHREPO-GRC`): SYS-ARCHREPO to SYS-GRC
- IT Service Management to Architecture Repository (`INT-ITSM-ARCHREPO`): SYS-ITSM to SYS-ARCHREPO
- IT Service Management to Governance, Risk and Compliance (`INT-ITSM-GRC`): SYS-ITSM to SYS-GRC
- Lending Portfolio Performance Semantic Layer to Regulatory Reporting Engine (`INT-LENDPERF-REGREPORTING`): SYS-LENDPERF-SEMANTIC to SYS-REG-REPORTING
- Work Tracking to Governance, Risk and Compliance (`INT-WORKTRACK-GRC`): SYS-WORKTRACK to SYS-GRC

## Of no kind

Each of these is either built unlike anything around it, or a kind the library has yet to learn; several sharing a shape is a kind waiting to be written.

- Authorization Switch to Transaction Fraud Detection (`INT-AUTH-FRAUD`): SYS-AUTH-SWITCH to SYS-FRAUD-DETECT, Request-response over ISO8583
- IVR to Contact Center Platform (`INT-IVR-CONTACT`): SYS-IVR to SYS-CONTACT, Request-response over SIP
