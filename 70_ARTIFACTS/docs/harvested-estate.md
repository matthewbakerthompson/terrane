# The Harvested Estate, Connected

The systems the business layer harvested that serve customers and the books, with the connections drafted from the process map and the pattern library, and the estate systems they reach. Every connection carries its integration style and names its pattern in the inspector; the operations chain is its own drawing. Proposed throughout, so an owner has something to confirm or strike.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% The Harvested Estate, Connected
  %% Generated from the model by `terrane render`. Do not edit by hand.

  SYS_APPFRAUD["Application fraud<br/>screening"]
  SYS_AUTH_SWITCH["Authorization Switch"]
  SYS_BROKER_GW["Brokered deposit<br/>settlement gateway"]
  SYS_MARKETING["Campaign management"]
  SYS_CARD_FULFILL["Card production and<br/>fulfillment<br/>[external]"]
  OI_CARDSVC_API("Card Servicing API<br/>[HTTPS]")
  SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
  SYS_MOBILE["Cardholder mobile<br/>application"]
  SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
  SYS_CONTACT["Contact center platform"]
  SYS_CORE_LEDGER["Core Card Ledger"]
  OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
  SYS_BUREAU_GW["Credit bureau gateway"]
  SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
  SYS_DEALER_PORTAL["Dealer portal<br/>[SaaS]"]
  SYS_DEPOSIT["Deposit platform"]
  SYS_DOC["Document management and<br/>archive"]
  SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
  SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
  SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
  SYS_AML["Financial crimes platform"]
  SYS_GL["General ledger"]
  SYS_CATALOG["Governance catalog<br/>[Collibra Data Intelligence]"]
  SYS_KYC["Identity verification"]
  SYS_LOS["Indirect loan origination<br/>system"]
  SYS_LOAN_SVC["Installment loan servicing<br/>platform"]
  SYS_IVR["IVR and self-service voice"]
  SYS_LEGAL_MATTER["Legal matter management<br/>[SaaS]"]
  SYS_MERCH_ACQ["Merchant acquiring<br/>platform<br/>[external]"]
  SYS_MERCHANT_API["Merchant Portal Service<br/>[AKS · Merchant Portal Cache]"]
  SYS_MERCH_RISK["Merchant risk monitoring"]
  SYS_MODEL["Model platform"]
  SYS_SCREENING_GATEWAY["NICE Actimize Screening<br/>Integration Gateway<br/>[EKS]"]
  SYS_ORIG_DECISION["Originations decision<br/>engine"]
  SYS_DIALER["Outbound contact platform"]
  SYS_PAYMENT_GW["Payment capture gateway"]
  SYS_PROSPECT_DATA["Prospect and marketing<br/>data services"]
  SYS_RECON["Reconciliation platform"]
  SYS_REMARKET["Repossession and<br/>remarketing management<br/>[external]"]
  SYS_REWARDS["Rewards ledger"]
  SYS_CLIENT_PORTAL["Servicing client portal"]
  SYS_STATEMENTS["Statement Generation"]
  SYS_TITLE["Title and lien management<br/>[external]"]
  SYS_TOKEN["Tokenization and<br/>credential management"]
  SYS_FRAUD_DETECT["Transaction fraud<br/>detection"]
  SYS_TREASURY["Treasury management"]

  SYS_ORIG_DECISION -->|"Request-response"| SYS_CREDIT_DATA
  SYS_ORIG_DECISION -->|"Request-response"| SYS_APPFRAUD
  SYS_ORIG_DECISION -->|"Request-response"| SYS_KYC
  SYS_ORIG_DECISION -->|"Request-response"| SYS_MODEL
  SYS_ORIG_DECISION -->|"Batch"| SYS_CORE_LEDGER
  SYS_ORIG_DECISION -->|"Event"| SYS_DOC
  SYS_CORE_LEDGER -->|"Batch"| SYS_CARD_FULFILL
  SYS_PAYMENT_GW --> OI_LEDGER_QUEUE
  SYS_PAYMENT_GW -->|"Batch"| SYS_GL
  SYS_CORE_LEDGER -->|"Batch"| SYS_GL
  SYS_CORE_LEDGER -->|"Batch"| SYS_RECON
  SYS_GL -->|"Batch"| SYS_RECON
  SYS_GL -->|"Batch"| SYS_TREASURY
  SYS_AUTH_SWITCH -->|"Request-response"| SYS_FRAUD_DETECT
  SYS_FRAUD_DETECT -->|"Request-response"| SYS_MODEL
  SYS_FRAUD_DETECT -->|"Event"| SYS_CRM
  SYS_AUTH_SWITCH -->|"Request-response"| SYS_TOKEN
  SYS_MOBILE -->|"Request-response"| SYS_TOKEN
  SYS_MOBILE --> OI_CARDSVC_API
  SYS_CORE_LEDGER -->|"Batch"| SYS_BUREAU_GW
  SYS_BUREAU_GW -->|"Batch"| SYS_CREDIT_BUREAU
  SYS_BUREAU_GW -->|"Batch"| SYS_CRM
  SYS_COLLECT_API -->|"Batch"| SYS_DIALER
  SYS_DIALER -->|"Event"| SYS_COLLECT_API
  SYS_COLLECT_API -->|"Event"| SYS_DOC
  SYS_CORE_LEDGER -->|"Batch"| SYS_DOC
  SYS_STATEMENTS -->|"Batch"| SYS_DOC
  SYS_CLIENT_PORTAL -->|"Request-response"| SYS_DOC
  SYS_CORE_LEDGER -->|"Batch"| SYS_CLIENT_PORTAL
  SYS_CONTACT -->|"Request-response"| SYS_CRM
  SYS_IVR -->|"Request-response"| SYS_CONTACT
  SYS_IVR --> OI_CARDSVC_API
  SYS_PROSPECT_DATA -->|"Batch"| SYS_MARKETING
  SYS_MARKETING -->|"Event"| SYS_CRM
  SYS_DATA_INGEST -->|"Batch"| SYS_MODEL
  SYS_DATA_INGEST -->|"Event"| SYS_CATALOG
  SYS_DATA_INGEST -->|"Batch"| SYS_CREDIT_DATA
  SYS_KYC -->|"Event"| SYS_AML
  SYS_CORE_LEDGER -->|"Batch"| SYS_AML
  SYS_DEALER_PORTAL -->|"Request-response"| SYS_LOS
  SYS_LOS -->|"Request-response"| SYS_BUREAU_GW
  SYS_LOS -->|"Request-response"| SYS_KYC
  SYS_LOS -->|"Request-response"| SYS_APPFRAUD
  SYS_LOS -->|"Batch"| SYS_LOAN_SVC
  SYS_LOAN_SVC -->|"Batch"| SYS_TITLE
  SYS_PAYMENT_GW -->|"Batch"| SYS_LOAN_SVC
  SYS_LOAN_SVC -->|"Batch"| SYS_GL
  SYS_LOAN_SVC -->|"Batch"| SYS_COLLECT_API
  SYS_LOAN_SVC -->|"Batch"| SYS_BUREAU_GW
  SYS_LOAN_SVC -->|"Batch"| SYS_REMARKET
  SYS_MERCHANT_API -->|"Request-response"| SYS_MERCH_ACQ
  SYS_MERCH_ACQ -->|"Batch"| SYS_MERCH_RISK
  SYS_MERCH_RISK -->|"Request-response"| SYS_SCREENING_GATEWAY
  SYS_MERCH_ACQ -->|"Batch"| SYS_GL
  SYS_MERCH_ACQ -->|"Batch"| SYS_RECON
  SYS_DEPOSIT -->|"Request-response"| SYS_KYC
  SYS_DEPOSIT -->|"Request-response"| SYS_SCREENING_GATEWAY
  SYS_BROKER_GW -->|"Batch"| SYS_DEPOSIT
  SYS_DEPOSIT -->|"Batch"| SYS_GL
  SYS_DEPOSIT -->|"Batch"| SYS_TREASURY
  SYS_COLLECT_API -->|"Batch"| SYS_LEGAL_MATTER
  SYS_AUTH_SWITCH --> OI_LEDGER_QUEUE
  SYS_CARDSVC_API --> OI_LEDGER_QUEUE
  SYS_COLLECT_API --> OI_LEDGER_QUEUE
  SYS_CRM -->|"Request-response"| SYS_CORE_LEDGER
  SYS_CORE_LEDGER -->|"Batch"| SYS_DATA_INGEST
  SYS_CORE_LEDGER -->|"Batch"| SYS_STATEMENTS
  SYS_AUTH_SWITCH -->|"Request-response"| SYS_SCREENING_GATEWAY
  OI_CARDSVC_API --- SYS_CARDSVC_API
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER

  classDef s_offered_interfaces__active fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__active fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__planned fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px,stroke-dasharray:6 3;
  classDef s_systems__proposed fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px,stroke-dasharray:2 3;
  class OI_CARDSVC_API,OI_LEDGER_QUEUE s_offered_interfaces__active;
  class SYS_AUTH_SWITCH,SYS_CARDSVC_API,SYS_COLLECT_API,SYS_CORE_LEDGER,SYS_CREDIT_BUREAU,SYS_CRM,SYS_DATA_INGEST,SYS_STATEMENTS s_systems__active;
  class SYS_MERCHANT_API,SYS_SCREENING_GATEWAY s_systems__planned;
  class SYS_AML,SYS_APPFRAUD,SYS_BROKER_GW,SYS_BUREAU_GW,SYS_CARD_FULFILL,SYS_CATALOG,SYS_CLIENT_PORTAL,SYS_CONTACT,SYS_CREDIT_DATA,SYS_DEALER_PORTAL,SYS_DEPOSIT,SYS_DIALER,SYS_DOC,SYS_FRAUD_DETECT,SYS_GL,SYS_IVR,SYS_KYC,SYS_LEGAL_MATTER,SYS_LOAN_SVC,SYS_LOS,SYS_MARKETING,SYS_MERCH_ACQ,SYS_MERCH_RISK,SYS_MOBILE,SYS_MODEL,SYS_ORIG_DECISION,SYS_PAYMENT_GW,SYS_PROSPECT_DATA,SYS_RECON,SYS_REMARKET,SYS_REWARDS,SYS_TITLE,SYS_TOKEN,SYS_TREASURY s_systems__proposed;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![The Harvested Estate, Connected](../svg/harvested-estate.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |

**status** is drawn as the border style: solid for Active, dashed for Planned, dotted for Proposed, and faded for Deprecated and Retired.

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Card Authorization**: A card presented at a merchant, authorized or declined inside the scheme timeout. The tightest latency budget in the estate, and the reason the screening call has a circuit breaker rather than a retry.

1. Authorization Switch → NICE Actimize Screening Integration Gateway (HTTPS)
2. NICE Actimize Screening Integration Gateway → NICE Actimize Screening Private Egress (HTTPS) — not on this diagram
3. NICE Actimize Screening Private Egress → NICE Actimize Screening (PrivateLink) — not on this diagram
4. Authorization Switch → Core Card Ledger (MQ)

**Dispute and Chargeback**: A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

1. Dynamics 365 Customer Service → Core Card Ledger (HTTPS)
2. Core Card Ledger → Dispute Management Platform Integration Gateway (HTTPS) — not on this diagram
3. Dispute Management Platform Integration Gateway → Pega Smart Dispute (HTTPS) — not on this diagram
4. Pega Smart Dispute → Enterprise Data Ingestion Hub (SFTP) — not on this diagram

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL) — not on this diagram
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

46 entities, 70 relationships. Generated from the model; edit the model, not this file.

> 44 entities on an architecture diagram. Past about 40 this has become a landscape: narrow the scope, or mark it `kind: map`.
