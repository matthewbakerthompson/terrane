# Card Issuing — Landscape

One business domain and its immediate neighbors: every system in the domain plus everything one interface away. Smaller and easier to read than the full landscape, and drawn for every domain the systems name.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Card Issuing — Landscape
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Card_Issuing["Card Issuing"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
    OI_REWARDS_API("Rewards Redemption API<br/>[HTTPS]")
    SYS_REWARDS_WORKER["Rewards Redemption Async<br/>Worker<br/>[AKS · Event Hubs]"]
    SYS_REWARDS_STORE["Rewards Redemption<br/>Database<br/>[Azure SQL]"]
    SYS_REWARDS_EVENTS["Rewards Redemption Event<br/>Publisher<br/>[Service Bus]"]
    SYS_REWARDS_API["Rewards Redemption Service<br/>[AKS · Rewards Redemption Cache]"]
    SYS_REWARDS_WEB["Rewards Redemption Web<br/>[AKS]"]
  end

  subgraph grp_Collections["Collections"]
    direction LR
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
  end

  subgraph grp_Data_and_Analytics["Data and Analytics"]
    direction LR
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
  end

  subgraph grp_Lending["Lending"]
    direction LR
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
  end

  subgraph grp_Payments["Payments"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
  end

  subgraph grp_Servicing["Servicing"]
    direction LR
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_DISPUTES_GATEWAY["Dispute Management<br/>Platform Integration<br/>Gateway<br/>[AKS]"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_STATEMENTS["Statement Generation"]
  end

  SYS_CARD_FULFILL["Card production and<br/>fulfillment<br/>[external]"]
  SYS_BUREAU_GW["Credit bureau gateway"]
  SYS_DOC["Document management and<br/>archive"]
  SYS_AML["Financial crimes platform"]
  SYS_GL["General ledger"]
  SYS_ORIG_DECISION["Originations decision<br/>engine"]
  SYS_PAYMENT_GW["Payment capture gateway"]
  SYS_RECON["Reconciliation platform"]
  SYS_CLIENT_PORTAL["Servicing client portal"]

  SYS_ORIG_DECISION -->|"FileTransfer"| SYS_CORE_LEDGER
  SYS_ORIG_DECISION -->|"AMQP"| SYS_DOC
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_CARD_FULFILL
  SYS_PAYMENT_GW --> OI_LEDGER_QUEUE
  SYS_PAYMENT_GW -->|"FileTransfer"| SYS_GL
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_GL
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_RECON
  SYS_GL -->|"SQL"| SYS_RECON
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_BUREAU_GW
  SYS_BUREAU_GW -->|"FileTransfer"| SYS_CRM
  SYS_COLLECT_API -->|"AMQP"| SYS_DOC
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DOC
  SYS_STATEMENTS -->|"FileTransfer"| SYS_DOC
  SYS_CLIENT_PORTAL -->|"HTTPS"| SYS_DOC
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_CLIENT_PORTAL
  SYS_CRM -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_AML
  SYS_AUTH_SWITCH --> OI_LEDGER_QUEUE
  SYS_CARDSVC_API --> OI_LEDGER_QUEUE
  SYS_COLLECT_API --> OI_LEDGER_QUEUE
  SYS_CRM -->|"HTTPS"| SYS_CORE_LEDGER
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_STATEMENTS
  SYS_LENDING_API --> OI_LEDGER_QUEUE
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CRM -->|"HTTPS"| SYS_LENDING_HUB
  SYS_REWARDS_WEB --> OI_REWARDS_API
  SYS_REWARDS_API -->|"TDS"| SYS_REWARDS_STORE
  SYS_REWARDS_API -->|"AMQP"| SYS_REWARDS_EVENTS
  SYS_REWARDS_API -->|"Kafka"| SYS_REWARDS_WORKER
  SYS_REWARDS_WORKER --> OI_LEDGER_QUEUE
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER
  OI_REWARDS_API --- SYS_REWARDS_API

  classDef s_offered_interfaces__high fill:#b9befa,stroke:#6366f1,color:#0f172a,stroke-width:2.6px;
  classDef s_offered_interfaces__medium fill:#dde3fe,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__high fill:#9aa0ed,stroke:#4338ca,color:#0f172a,stroke-width:2.6px;
  classDef s_systems__medium fill:#becbfb,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class OI_LEDGER_QUEUE s_offered_interfaces__high;
  class OI_REWARDS_API s_offered_interfaces__medium;
  class SYS_AUTH_SWITCH,SYS_CARDSVC_API,SYS_CORE_LEDGER,SYS_LENDING_API,SYS_LENDING_HUB s_systems__high;
  class SYS_AML,SYS_BUREAU_GW,SYS_CARD_FULFILL,SYS_CLIENT_PORTAL,SYS_COLLECT_API,SYS_CRM,SYS_DATA_INGEST,SYS_DISPUTES_GATEWAY,SYS_DOC,SYS_GL,SYS_ORIG_DECISION,SYS_PAYMENT_GW,SYS_RECON,SYS_REWARDS_API,SYS_REWARDS_EVENTS,SYS_REWARDS_STORE,SYS_REWARDS_WEB,SYS_REWARDS_WORKER,SYS_STATEMENTS s_systems__medium;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Card_Issuing,grp_Collections,grp_Data_and_Analytics,grp_Lending,grp_Payments,grp_Servicing boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card Issuing — Landscape](../svg/domain-landscape--card-issuing.svg)

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

**Dispute and Chargeback**: A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

1. Dynamics 365 Customer Service → Core Card Ledger (HTTPS)
2. Core Card Ledger → Dispute Management Platform Integration Gateway (HTTPS)
3. Dispute Management Platform Integration Gateway → Pega Smart Dispute (HTTPS) — not on this diagram
4. Pega Smart Dispute → Enterprise Data Ingestion Hub (SFTP) — not on this diagram

**Card Authorization**: A card presented at a merchant, authorized or declined inside the scheme timeout. The tightest latency budget in the estate, and the reason the screening call has a circuit breaker rather than a retry.

1. Authorization Switch → NICE Actimize Screening Integration Gateway (HTTPS) — not on this diagram
2. NICE Actimize Screening Integration Gateway → NICE Actimize Screening Private Egress (HTTPS) — not on this diagram
3. NICE Actimize Screening Private Egress → NICE Actimize Screening (PrivateLink) — not on this diagram
4. Authorization Switch → Core Card Ledger (MQ)

**Installment Loan Application**: An applicant applies for point-of-sale credit. Bureau search, affordability and a decision, with referral to an underwriter when the automated decision declines to take it.

1. Installment Lending Edge → Installment Lending Load Balancer (HTTPS) — not on this diagram
2. Installment Lending Load Balancer → Installment Lending Web (HTTPS) — not on this diagram
3. Installment Lending Web → Installment Lending Service (HTTPS) — not on this diagram
4. Installment Lending Service → Customer Identity Service (HTTPS) — not on this diagram
5. Installment Lending Service → Experian Credit Bureau (HTTPS) — not on this diagram
6. Installment Lending Service → Installment Lending Database (PostgreSQL) — not on this diagram
7. Installment Lending Service → Core Card Ledger (MQ)
8. Installment Lending Service → Installment Lending Async Worker (Kafka) — not on this diagram

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL) — not on this diagram
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

26 entities, 34 relationships. Generated from the model; edit the model, not this file.
