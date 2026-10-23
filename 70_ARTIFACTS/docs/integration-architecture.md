# Integration Architecture

Every system grouped by its integration role, with the protocol on each connection. Anything that reaches a core system without going through the integration and gateway layer is a point-to-point coupling.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Integration Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Analytics["Analytics"]
    direction LR
    SYS_CUST360_SEMANTIC["Customer 360 Semantic<br/>Layer<br/>[Snowflake Data Cloud]"]
    SYS_LENDPERF_SEMANTIC["Lending Portfolio<br/>Performance Semantic Layer<br/>[BigQuery · Looker]"]
  end

  subgraph grp_Application["Application"]
    direction LR
    OI_CARDSVC_API("Card Servicing API<br/>[HTTPS]")
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    OI_COLLECT_API("Collections Workspace API<br/>[HTTPS]")
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    OI_LENDING_API("Installment Lending API<br/>[HTTPS]")
    SYS_LENDING_WORKER["Installment Lending Async<br/>Worker<br/>[EKS · MSK]"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
    OI_MERCHANT_API("Merchant Portal API<br/>[HTTPS]")
    SYS_MERCHANT_API["Merchant Portal Service<br/>[AKS · Merchant Portal Cache]"]
    SYS_POSFIN_API["Point-of-Sale Finance<br/>Service<br/>[GKE · Point-of-Sale Finance Cache]"]
  end

  subgraph grp_Channel["Channel"]
    direction LR
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
    SYS_COLLECT_WEB["Collections Workspace Web<br/>[AKS]"]
    SYS_LENDING_WEB["Installment Lending Web<br/>[EKS]"]
    SYS_MERCHANT_WEB["Merchant Portal Web<br/>[AKS]"]
  end

  subgraph grp_Core["Core"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
  end

  subgraph grp_Datastore["Datastore"]
    direction LR
    SYS_CARDSVC_STORE["Card Servicing Datastore<br/>[Azure SQL]"]
    SYS_COLLECT_STORE["Collections Workspace<br/>Datastore<br/>[Azure SQL]"]
    SYS_LENDING_DB["Installment Lending<br/>Database<br/>[RDS]"]
    SYS_LENDING_BUCKET["Installment Lending Object<br/>Store<br/>[S3]"]
    SYS_MERCHANT_STORE["Merchant Portal Database<br/>[Azure SQL]"]
  end

  subgraph grp_Edge["Edge"]
    direction LR
    SYS_LENDING_EDGE["Installment Lending Edge"]
  end

  subgraph grp_Integration["Integration"]
    direction LR
    SYS_CARDSVC_EVENTS["Card Servicing Event<br/>Publisher<br/>[Service Bus]"]
    SYS_DISPUTES_GATEWAY["Dispute Management<br/>Platform Integration<br/>Gateway<br/>[AKS]"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_IDV_GATEWAY["Identity Document<br/>Verification Integration<br/>Gateway<br/>[AKS]"]
    SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
    SYS_MERCHANT_EVENTS["Merchant Portal Event<br/>Publisher<br/>[Service Bus]"]
    SYS_OBAFF_GATEWAY["Open Banking Affordability<br/>Integration Gateway<br/>[GKE]"]
    SYS_OBAFF_WEBHOOKS["Open Banking Affordability<br/>Webhook Listener<br/>[GKE]"]
  end

  subgraph grp_Network["Network"]
    direction LR
    SYS_IDV_EGRESS["Identity Document<br/>Verification Private<br/>Egress"]
    SYS_LENDING_ALB["Installment Lending Load<br/>Balancer"]
    SYS_OBAFF_EGRESS["Open Banking Affordability<br/>Private Egress"]
  end

  subgraph grp_Pipeline["Pipeline"]
    direction LR
    SYS_CUST360_PIPELINE["Customer 360 Pipeline<br/>[Snowflake Data Cloud +1]"]
    SYS_LENDPERF_PIPELINE["Lending Portfolio<br/>Performance Pipeline<br/>[BigQuery · Dataflow +3]"]
  end

  subgraph grp_Platform["Platform"]
    direction LR
    OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
  end

  subgraph grp_Vendor["Vendor"]
    direction LR
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
    SYS_IDV_VENDOR["Identity Document<br/>Verification<br/>[Onfido]"]
    SYS_OBAFF_VENDOR["Open Banking Affordability<br/>[TrueLayer]"]
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
  end

  SYS_CRM -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_AUTH_SWITCH --> OI_LEDGER_QUEUE
  SYS_CARDSVC_API --> OI_IDENTITY_API
  SYS_CARDSVC_API --> OI_LEDGER_QUEUE
  SYS_CARDSVC_EVENTS -->|"AMQP"| SYS_DATA_INGEST
  SYS_COLLECT_API --> OI_IDENTITY_API
  SYS_COLLECT_API --> OI_LEDGER_QUEUE
  SYS_CRM -->|"HTTPS"| SYS_CORE_LEDGER
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_LENDING_API --> OI_LEDGER_QUEUE
  SYS_LENDING_API --> OI_IDENTITY_API
  SYS_LENDING_WORKER -->|"S3"| SYS_DATA_INGEST
  SYS_LENDING_API -->|"HTTPS"| SYS_CREDIT_BUREAU
  SYS_CARDSVC_WEB --> OI_CARDSVC_API
  SYS_CARDSVC_API -->|"TDS"| SYS_CARDSVC_STORE
  SYS_CARDSVC_API -->|"AMQP"| SYS_CARDSVC_EVENTS
  SYS_COLLECT_WEB --> OI_COLLECT_API
  SYS_COLLECT_API -->|"TDS"| SYS_COLLECT_STORE
  SYS_DATA_INGEST -->|"Snowpipe"| SYS_CUST360_PIPELINE
  SYS_CUST360_PIPELINE -->|"SQL"| SYS_CUST360_SEMANTIC
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_DISPUTES_GATEWAY -->|"HTTPS"| SYS_DISPUTES_SAAS
  SYS_DISPUTES_SAAS -->|"SFTP"| SYS_DATA_INGEST
  SYS_IDENTITY_SVC -->|"HTTPS"| SYS_IDV_GATEWAY
  SYS_IDV_GATEWAY -->|"HTTPS"| SYS_IDV_EGRESS
  SYS_IDV_EGRESS -->|"PrivateLink"| SYS_IDV_VENDOR
  SYS_IDV_VENDOR -->|"HTTPS"| SYS_IDV_WEBHOOKS
  SYS_IDV_WEBHOOKS -->|"HTTPS"| SYS_IDENTITY_SVC
  SYS_LENDING_WEB --> OI_LENDING_API
  SYS_LENDING_EDGE -->|"HTTPS"| SYS_LENDING_ALB
  SYS_LENDING_ALB -->|"HTTPS"| SYS_LENDING_WEB
  SYS_LENDING_API -->|"Kafka"| SYS_LENDING_WORKER
  SYS_LENDING_API -->|"PostgreSQL"| SYS_LENDING_DB
  SYS_LENDING_API -->|"HTTPS"| SYS_LENDING_BUCKET
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CREDIT_BUREAU -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CRM -->|"HTTPS"| SYS_LENDING_HUB
  SYS_LENDPERF_PIPELINE -->|"SQL"| SYS_LENDPERF_SEMANTIC
  SYS_MERCHANT_WEB --> OI_MERCHANT_API
  SYS_MERCHANT_API -->|"TDS"| SYS_MERCHANT_STORE
  SYS_MERCHANT_API -->|"AMQP"| SYS_MERCHANT_EVENTS
  SYS_POSFIN_API -->|"HTTPS"| SYS_OBAFF_GATEWAY
  SYS_OBAFF_GATEWAY -->|"HTTPS"| SYS_OBAFF_EGRESS
  SYS_OBAFF_EGRESS -->|"PrivateLink"| SYS_OBAFF_VENDOR
  SYS_OBAFF_VENDOR -->|"HTTPS"| SYS_OBAFF_WEBHOOKS
  SYS_OBAFF_WEBHOOKS -->|"HTTPS"| SYS_POSFIN_API
  OI_CARDSVC_API --- SYS_CARDSVC_API
  OI_COLLECT_API --- SYS_COLLECT_API
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER
  OI_LENDING_API --- SYS_LENDING_API
  OI_MERCHANT_API --- SYS_MERCHANT_API

  classDef s_offered_interfaces__high fill:#b9befa,stroke:#6366f1,color:#0f172a,stroke-width:2.6px;
  classDef s_offered_interfaces__medium fill:#dde3fe,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__high fill:#9aa0ed,stroke:#4338ca,color:#0f172a,stroke-width:2.6px;
  classDef s_systems__medium fill:#becbfb,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class OI_CARDSVC_API,OI_IDENTITY_API,OI_LEDGER_QUEUE,OI_LENDING_API s_offered_interfaces__high;
  class OI_COLLECT_API,OI_MERCHANT_API s_offered_interfaces__medium;
  class SYS_AUTH_SWITCH,SYS_CARDSVC_API,SYS_CARDSVC_STORE,SYS_CARDSVC_WEB,SYS_CORE_LEDGER,SYS_CREDIT_BUREAU,SYS_IDENTITY_SVC,SYS_IDV_EGRESS,SYS_IDV_GATEWAY,SYS_IDV_VENDOR,SYS_IDV_WEBHOOKS,SYS_LENDING_ALB,SYS_LENDING_API,SYS_LENDING_BUCKET,SYS_LENDING_DB,SYS_LENDING_EDGE,SYS_LENDING_HUB,SYS_LENDING_WEB s_systems__high;
  class SYS_CARDSVC_EVENTS,SYS_COLLECT_API,SYS_COLLECT_STORE,SYS_COLLECT_WEB,SYS_CRM,SYS_CUST360_PIPELINE,SYS_CUST360_SEMANTIC,SYS_DATA_INGEST,SYS_DISPUTES_GATEWAY,SYS_DISPUTES_SAAS,SYS_LENDING_WORKER,SYS_LENDPERF_PIPELINE,SYS_LENDPERF_SEMANTIC,SYS_MERCHANT_API,SYS_MERCHANT_EVENTS,SYS_MERCHANT_STORE,SYS_MERCHANT_WEB,SYS_OBAFF_EGRESS,SYS_OBAFF_GATEWAY,SYS_OBAFF_VENDOR,SYS_OBAFF_WEBHOOKS,SYS_POSFIN_API s_systems__medium;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Analytics,grp_Application,grp_Channel,grp_Core,grp_Datastore,grp_Edge,grp_Integration,grp_Network,grp_Pipeline,grp_Platform,grp_Vendor boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Integration Architecture](../svg/integration-architecture.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |

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

46 entities, 52 relationships. Generated from the model; edit the model, not this file.

> 55 entities matched; showing the 40 the scope names and the first 0 of the rest by id. Narrow the scope or raise limits.max_nodes.
