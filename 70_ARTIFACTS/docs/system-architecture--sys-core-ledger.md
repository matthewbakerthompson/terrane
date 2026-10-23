# Core Card Ledger — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Core Card Ledger — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CARD_ACCOUNT[("Card account master")]
    DA_CARDSVC_OPERATIONAL[("Card Servicing operational<br/>data")]
    DA_TRANSACTION[("Card transaction history")]
    DA_COLLECT_ACT[("Collections activity<br/>record")]
    DA_COLLECT_OPERATIONAL[("Collections Workspace<br/>operational data")]
    DA_APPLICATION[("Credit application record")]
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
    DA_CUSTOMER_PROFILE[("Customer profile")]
    DA_DISPUTE_CASE[("Dispute case file")]
    DA_DISPUTES_VENDOR_FEED[("Dispute Management<br/>Platform vendor feed")]
    DA_GL[("General ledger entries")]
    DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
    DA_MODEL_FEAT[("Model feature store")]
    DA_SCREENING_OUTCOMES[("NICE Actimize Screening<br/>outcomes")]
    DA_PAYMENT_INSTR[("Payment instructions")]
    DA_CLIENT_SERV[("Servicing client program<br/>data")]
    DA_STATEMENTS[("Statement archive")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_CARD_FULFILL["Card production and<br/>fulfillment<br/>[external]"]
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
    SYS_BUREAU_GW["Credit bureau gateway"]
    SYS_DISPUTES_GATEWAY["Dispute Management<br/>Platform Integration<br/>Gateway<br/>[AKS]"]
    SYS_DOC["Document management and<br/>archive"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_AML["Financial crimes platform"]
    SYS_GL["General ledger"]
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
    SYS_ORIG_DECISION["Originations decision<br/>engine"]
    SYS_PAYMENT_GW["Payment capture gateway"]
    SYS_RECON["Reconciliation platform"]
    SYS_REWARDS_WORKER["Rewards Redemption Async<br/>Worker<br/>[AKS · Event Hubs]"]
    SYS_CLIENT_PORTAL["Servicing client portal"]
    SYS_STATEMENTS["Statement Generation"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
    TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
    TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
  end

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
  SYS_REWARDS_WORKER --> OI_LEDGER_QUEUE
  SYS_LENDING_API -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_API -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_API -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_CARDSVC_API -->|"ReadWrite"| DA_CARDSVC_OPERATIONAL
  SYS_COLLECT_API -->|"ReadWrite"| DA_COLLECT_OPERATIONAL
  SYS_DATA_INGEST -->|"Read"| DA_DISPUTES_VENDOR_FEED
  SYS_LENDING_API -->|"ReadWrite"| DA_LENDING_OPERATIONAL
  SYS_DATA_INGEST -->|"Read"| DA_SCREENING_OUTCOMES
  SYS_ORIG_DECISION -->|"ReadWrite"| DA_APPLICATION
  SYS_DATA_INGEST -->|"ReadWrite"| DA_MODEL_FEAT
  SYS_PAYMENT_GW -->|"ReadWrite"| DA_PAYMENT_INSTR
  SYS_CORE_LEDGER -->|"Read"| DA_PAYMENT_INSTR
  SYS_GL -->|"ReadWrite"| DA_GL
  SYS_RECON -->|"Read"| DA_GL
  SYS_RECON -->|"Read"| DA_TRANSACTION
  SYS_BUREAU_GW -->|"ReadWrite"| DA_BUREAU_FILE
  SYS_BUREAU_GW -->|"Read"| DA_DISPUTE_CASE
  SYS_CRM -->|"ReadWrite"| DA_DISPUTE_CASE
  SYS_COLLECT_API -->|"ReadWrite"| DA_COLLECT_ACT
  SYS_DOC -->|"ReadWrite"| DA_STATEMENTS
  SYS_STATEMENTS -->|"ReadWrite"| DA_STATEMENTS
  SYS_CLIENT_PORTAL -->|"ReadWrite"| DA_CLIENT_SERV
  SYS_CLIENT_PORTAL -->|"Read"| DA_STATEMENTS
  SYS_AML -->|"Read"| DA_TRANSACTION
  SYS_AML -->|"Read"| DA_APPLICATION
  SYS_CARD_FULFILL -->|"Read"| DA_CARD_ACCOUNT
  SYS_AUTH_SWITCH -->|"Read"| DA_CARD_ACCOUNT
  SYS_AUTH_SWITCH -->|"ReadWrite"| DA_TRANSACTION
  SYS_CARDSVC_API -->|"Read"| DA_CARD_ACCOUNT
  SYS_CARDSVC_API -->|"Read"| DA_TRANSACTION
  SYS_COLLECT_API -->|"Read"| DA_CARD_ACCOUNT
  SYS_CORE_LEDGER -->|"ReadWrite"| DA_CARD_ACCOUNT
  SYS_CRM -->|"ReadWrite"| DA_CUSTOMER_PROFILE
  SYS_STATEMENTS -->|"Read"| DA_CARD_ACCOUNT
  SYS_STATEMENTS -->|"Read"| DA_TRANSACTION
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_APPLICATION,DA_BUREAU_FILE,DA_CARD_ACCOUNT,DA_CARDSVC_OPERATIONAL,DA_CLIENT_SERV,DA_COLLECT_ACT,DA_COLLECT_OPERATIONAL,DA_CUSTOMER_PROFILE,DA_DISPUTE_CASE,DA_DISPUTES_VENDOR_FEED,DA_GL,DA_LENDING_OPERATIONAL,DA_MODEL_FEAT,DA_PAYMENT_INSTR,DA_SCREENING_OUTCOMES,DA_STATEMENTS,DA_TRANSACTION s_data_assets__data_assets;
  class OI_LEDGER_QUEUE s_offered_interfaces__offered_interfaces;
  class SYS_AML,SYS_AUTH_SWITCH,SYS_BUREAU_GW,SYS_CARD_FULFILL,SYS_CARDSVC_API,SYS_CLIENT_PORTAL,SYS_COLLECT_API,SYS_CORE_LEDGER,SYS_CRM,SYS_DATA_INGEST,SYS_DISPUTES_GATEWAY,SYS_DOC,SYS_GL,SYS_LENDING_API,SYS_LENDING_HUB,SYS_ORIG_DECISION,SYS_PAYMENT_GW,SYS_RECON,SYS_REWARDS_WORKER,SYS_STATEMENTS s_systems__systems;
  class TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_PRIVATELINK s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Core Card Ledger — Architecture](../svg/system-architecture--sys-core-ledger.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |
| `#c2410c` | tech services |

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

41 entities, 64 relationships. Generated from the model; edit the model, not this file.

> 55 entities matched; showing the 1 the scope names and the first 39 of the rest by id. Narrow the scope or raise limits.max_nodes.
