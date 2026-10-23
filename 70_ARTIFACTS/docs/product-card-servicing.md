# Card Servicing in Context

The Card Servicing product, the systems it is made of, and everything one interface away from them. The scope follows the product relationship, so it stays correct whether the product was generated, imported or written by hand.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Card Servicing in Context
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Card_Issuing["Card Issuing"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
  end

  subgraph grp_Data_and_Analytics["Data and Analytics"]
    direction LR
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
  end

  subgraph grp_Enterprise_Platform["Enterprise Platform"]
    direction LR
    OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
  end

  subgraph grp_Servicing["Servicing"]
    direction LR
    PRD_CARD_SERVICING(["Card Servicing"])
    OI_CARDSVC_API("Card Servicing API<br/>[HTTPS]")
    SYS_CARDSVC_STORE["Card Servicing Datastore<br/>[Azure SQL]"]
    SYS_CARDSVC_EVENTS["Card Servicing Event<br/>Publisher<br/>[Service Bus]"]
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
  end

  SYS_MOBILE["Cardholder mobile<br/>application"]
  SYS_IVR["IVR and self-service voice"]

  PRD_CARD_SERVICING -->|"includes"| SYS_CARDSVC_API
  PRD_CARD_SERVICING -->|"includes"| SYS_CARDSVC_WEB
  PRD_CARD_SERVICING -->|"includes"| SYS_CARDSVC_STORE
  PRD_CARD_SERVICING -->|"includes"| SYS_CARDSVC_EVENTS
  SYS_MOBILE --> OI_CARDSVC_API
  SYS_IVR --> OI_CARDSVC_API
  SYS_CARDSVC_API --> OI_IDENTITY_API
  SYS_CARDSVC_API --> OI_LEDGER_QUEUE
  SYS_CARDSVC_EVENTS -->|"AMQP"| SYS_DATA_INGEST
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_CARDSVC_WEB --> OI_CARDSVC_API
  SYS_CARDSVC_API -->|"TDS"| SYS_CARDSVC_STORE
  SYS_CARDSVC_API -->|"AMQP"| SYS_CARDSVC_EVENTS
  OI_CARDSVC_API --- SYS_CARDSVC_API
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER

  classDef s_offered_interfaces__high fill:#b9befa,stroke:#6366f1,color:#0f172a,stroke-width:2.6px;
  classDef s_products__high fill:#e691b9,stroke:#be185d,color:#0f172a,stroke-width:2.6px;
  classDef s_systems__high fill:#9aa0ed,stroke:#4338ca,color:#0f172a,stroke-width:2.6px;
  classDef s_systems__medium fill:#becbfb,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class OI_CARDSVC_API,OI_IDENTITY_API,OI_LEDGER_QUEUE s_offered_interfaces__high;
  class PRD_CARD_SERVICING s_products__high;
  class SYS_CARDSVC_API,SYS_CARDSVC_STORE,SYS_CARDSVC_WEB,SYS_CORE_LEDGER,SYS_IDENTITY_SVC s_systems__high;
  class SYS_CARDSVC_EVENTS,SYS_DATA_INGEST,SYS_IVR,SYS_MOBILE s_systems__medium;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Card_Issuing,grp_Data_and_Analytics,grp_Enterprise_Platform,grp_Servicing boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card Servicing in Context](../svg/product-card-servicing.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6366f1` | offered interfaces |
| `#be185d` | products |
| `#4338ca` | systems |

**criticality** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | High |
| 1.4px | Medium |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL) — not on this diagram
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

13 entities, 16 relationships. Generated from the model; edit the model, not this file.
