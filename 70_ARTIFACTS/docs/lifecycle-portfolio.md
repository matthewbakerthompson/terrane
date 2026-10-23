# Portfolio Lifecycle

Systems grouped by lifecycle status and shaded by criticality. Check the Planned and Deprecated columns: what is arriving that nothing depends on yet, and what is leaving that other systems still depend on.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Portfolio Lifecycle
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Proposed["Proposed"]
    direction LR
    SYS_APPFRAUD["Application fraud<br/>screening"]
    SYS_ARCHREPO["Architecture repository<br/>[SaaS]"]
    SYS_CARD_FULFILL["Card production and<br/>fulfillment<br/>[external]"]
    SYS_CONTACT["Contact center platform"]
    SYS_BUREAU_GW["Credit bureau gateway"]
    SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
    SYS_DOC["Document management and<br/>archive"]
    SYS_AML["Financial crimes platform"]
    SYS_GL["General ledger"]
    SYS_CATALOG["Governance catalog<br/>[Collibra Data Intelligence]"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
    SYS_HRIS["Human resources<br/>information system"]
    SYS_IAM["Identity and access<br/>management"]
    SYS_KYC["Identity verification"]
    SYS_ITSM["IT service management<br/>[SaaS]"]
    SYS_IVR["IVR and self-service voice"]
    SYS_DIALER["Outbound contact platform"]
    SYS_CLIENT_PORTAL["Servicing client portal"]
    SYS_FRAUD_DETECT["Transaction fraud<br/>detection"]
  end

  subgraph grp_Planned["Planned"]
    direction LR
    SYS_IDV_VENDOR["Identity Document<br/>Verification<br/>[Onfido]"]
    SYS_IDV_GATEWAY["Identity Document<br/>Verification Integration<br/>Gateway<br/>[AKS]"]
    SYS_IDV_EGRESS["Identity Document<br/>Verification Private<br/>Egress"]
    SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
    SYS_LENDING_WORKER["Installment Lending Async<br/>Worker<br/>[EKS · MSK]"]
    SYS_LENDING_DB["Installment Lending<br/>Database<br/>[RDS]"]
    SYS_LENDING_EDGE["Installment Lending Edge"]
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
    SYS_LENDING_ALB["Installment Lending Load<br/>Balancer"]
    SYS_LENDING_BUCKET["Installment Lending Object<br/>Store<br/>[S3]"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
    SYS_LENDING_WEB["Installment Lending Web<br/>[EKS]"]
    SYS_LENDPERF_PIPELINE["Lending Portfolio<br/>Performance Pipeline<br/>[BigQuery · Dataflow +3]"]
    SYS_LENDPERF_SEMANTIC["Lending Portfolio<br/>Performance Semantic Layer<br/>[BigQuery · Looker]"]
  end

  subgraph grp_Active["Active"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_CARDSVC_STORE["Card Servicing Datastore<br/>[Azure SQL]"]
    SYS_CARDSVC_EVENTS["Card Servicing Event<br/>Publisher<br/>[Service Bus]"]
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
    SYS_COLLECT_STORE["Collections Workspace<br/>Datastore<br/>[Azure SQL]"]
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_COLLECT_WEB["Collections Workspace Web<br/>[AKS]"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_CUST360_PIPELINE["Customer 360 Pipeline<br/>[Snowflake Data Cloud +1]"]
    SYS_CUST360_SEMANTIC["Customer 360 Semantic<br/>Layer<br/>[Snowflake Data Cloud]"]
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
    SYS_DISPUTES_GATEWAY["Dispute Management<br/>Platform Integration<br/>Gateway<br/>[AKS]"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
  end

  SYS_CORE_LEDGER --> SYS_CARD_FULFILL
  SYS_CORE_LEDGER --> SYS_GL
  SYS_AUTH_SWITCH --> SYS_FRAUD_DETECT
  SYS_FRAUD_DETECT --> SYS_CRM
  SYS_CORE_LEDGER --> SYS_BUREAU_GW
  SYS_BUREAU_GW --> SYS_CREDIT_BUREAU
  SYS_BUREAU_GW --> SYS_CRM
  SYS_COLLECT_API --> SYS_DIALER
  SYS_DIALER --> SYS_COLLECT_API
  SYS_COLLECT_API --> SYS_DOC
  SYS_CORE_LEDGER --> SYS_DOC
  SYS_CLIENT_PORTAL --> SYS_DOC
  SYS_CORE_LEDGER --> SYS_CLIENT_PORTAL
  SYS_CONTACT --> SYS_CRM
  SYS_IVR --> SYS_CONTACT
  SYS_IVR --> SYS_CARDSVC_API
  SYS_CRM --> SYS_DISPUTES_GATEWAY
  SYS_DATA_INGEST --> SYS_CATALOG
  SYS_DATA_INGEST --> SYS_CREDIT_DATA
  SYS_KYC --> SYS_AML
  SYS_CORE_LEDGER --> SYS_AML
  SYS_HRIS --> SYS_IAM
  SYS_CRM --> SYS_IAM
  SYS_CONTACT --> SYS_IAM
  SYS_ITSM --> SYS_GRC
  SYS_ARCHREPO --> SYS_GRC
  SYS_ITSM --> SYS_ARCHREPO
  SYS_AUTH_SWITCH --> SYS_CORE_LEDGER
  SYS_CARDSVC_API --> SYS_IDENTITY_SVC
  SYS_CARDSVC_API --> SYS_CORE_LEDGER
  SYS_CARDSVC_EVENTS --> SYS_DATA_INGEST
  SYS_COLLECT_API --> SYS_IDENTITY_SVC
  SYS_COLLECT_API --> SYS_CORE_LEDGER
  SYS_CRM --> SYS_CORE_LEDGER
  SYS_CORE_LEDGER --> SYS_DATA_INGEST
  SYS_LENDING_API --> SYS_CORE_LEDGER
  SYS_LENDING_API --> SYS_IDENTITY_SVC
  SYS_LENDING_WORKER --> SYS_DATA_INGEST
  SYS_LENDING_API --> SYS_CREDIT_BUREAU
  SYS_CARDSVC_WEB --> SYS_CARDSVC_API
  SYS_CARDSVC_API --> SYS_CARDSVC_STORE
  SYS_CARDSVC_API --> SYS_CARDSVC_EVENTS
  SYS_COLLECT_WEB --> SYS_COLLECT_API
  SYS_COLLECT_API --> SYS_COLLECT_STORE
  SYS_DATA_INGEST --> SYS_CUST360_PIPELINE
  SYS_CUST360_PIPELINE --> SYS_CUST360_SEMANTIC
  SYS_CORE_LEDGER --> SYS_DISPUTES_GATEWAY
  SYS_DISPUTES_GATEWAY --> SYS_DISPUTES_SAAS
  SYS_DISPUTES_SAAS --> SYS_DATA_INGEST
  SYS_IDENTITY_SVC --> SYS_IDV_GATEWAY
  SYS_IDV_GATEWAY --> SYS_IDV_EGRESS
  SYS_IDV_EGRESS --> SYS_IDV_VENDOR
  SYS_IDV_VENDOR --> SYS_IDV_WEBHOOKS
  SYS_IDV_WEBHOOKS --> SYS_IDENTITY_SVC
  SYS_LENDING_WEB --> SYS_LENDING_API
  SYS_LENDING_EDGE --> SYS_LENDING_ALB
  SYS_LENDING_ALB --> SYS_LENDING_WEB
  SYS_LENDING_API --> SYS_LENDING_WORKER
  SYS_LENDING_API --> SYS_LENDING_DB
  SYS_LENDING_API --> SYS_LENDING_BUCKET
  SYS_CORE_LEDGER --> SYS_LENDING_HUB
  SYS_CREDIT_BUREAU --> SYS_LENDING_HUB
  SYS_CRM --> SYS_LENDING_HUB
  SYS_LENDPERF_PIPELINE --> SYS_LENDPERF_SEMANTIC

  classDef s_systems__high fill:#9aa0ed,stroke:#4338ca,color:#0f172a,stroke-width:2.6px;
  classDef s_systems__medium fill:#becbfb,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class SYS_AUTH_SWITCH,SYS_CARDSVC_API,SYS_CARDSVC_STORE,SYS_CARDSVC_WEB,SYS_CORE_LEDGER,SYS_CREDIT_BUREAU,SYS_IDENTITY_SVC,SYS_IDV_EGRESS,SYS_IDV_GATEWAY,SYS_IDV_VENDOR,SYS_IDV_WEBHOOKS,SYS_LENDING_ALB,SYS_LENDING_API,SYS_LENDING_BUCKET,SYS_LENDING_DB,SYS_LENDING_EDGE,SYS_LENDING_HUB,SYS_LENDING_WEB s_systems__high;
  class SYS_AML,SYS_APPFRAUD,SYS_ARCHREPO,SYS_BUREAU_GW,SYS_CARD_FULFILL,SYS_CARDSVC_EVENTS,SYS_CATALOG,SYS_CLIENT_PORTAL,SYS_COLLECT_API,SYS_COLLECT_STORE,SYS_COLLECT_WEB,SYS_CONTACT,SYS_CREDIT_DATA,SYS_CRM,SYS_CUST360_PIPELINE,SYS_CUST360_SEMANTIC,SYS_DATA_INGEST,SYS_DIALER,SYS_DISPUTES_GATEWAY,SYS_DISPUTES_SAAS,SYS_DOC,SYS_FRAUD_DETECT,SYS_GL,SYS_GRC,SYS_HRIS,SYS_IAM,SYS_ITSM,SYS_IVR,SYS_KYC,SYS_LENDING_WORKER,SYS_LENDPERF_PIPELINE,SYS_LENDPERF_SEMANTIC s_systems__medium;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Proposed,grp_Planned,grp_Active boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Portfolio Lifecycle](../svg/lifecycle-portfolio.svg)

**criticality** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | High |
| 1.4px | Medium |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Installment Loan Application**: An applicant applies for point-of-sale credit. Bureau search, affordability and a decision, with referral to an underwriter when the automated decision declines to take it.

1. Installment Lending Edge → Installment Lending Load Balancer (HTTPS)
2. Installment Lending Load Balancer → Installment Lending Web (HTTPS)
3. Installment Lending Web → Installment Lending Service (HTTPS)
4. Installment Lending Service → Customer Identity Service (HTTPS)
5. Installment Lending Service → Experian Credit Bureau (HTTPS)
6. Installment Lending Service → Installment Lending Database (PostgreSQL)
7. Installment Lending Service → Core Card Ledger (MQ)
8. Installment Lending Service → Installment Lending Async Worker (Kafka)

**Dispute and Chargeback**: A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

1. Dynamics 365 Customer Service → Core Card Ledger (HTTPS)
2. Core Card Ledger → Dispute Management Platform Integration Gateway (HTTPS)
3. Dispute Management Platform Integration Gateway → Pega Smart Dispute (HTTPS)
4. Pega Smart Dispute → Enterprise Data Ingestion Hub (SFTP)

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe)
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL)
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

**Card Authorization**: A card presented at a merchant, authorized or declined inside the scheme timeout. The tightest latency budget in the estate, and the reason the screening call has a circuit breaker rather than a retry.

1. Authorization Switch → NICE Actimize Screening Integration Gateway (HTTPS) — not on this diagram
2. NICE Actimize Screening Integration Gateway → NICE Actimize Screening Private Egress (HTTPS) — not on this diagram
3. NICE Actimize Screening Private Egress → NICE Actimize Screening (PrivateLink) — not on this diagram
4. Authorization Switch → Core Card Ledger (MQ)

50 entities, 64 relationships. Generated from the model; edit the model, not this file.

> 88 entities matched; showing the 50 the scope names and the first 0 of the rest by id. Narrow the scope or raise limits.max_nodes.
