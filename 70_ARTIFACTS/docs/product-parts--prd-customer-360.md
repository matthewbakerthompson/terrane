# Customer 360 — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Customer 360 — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  DA_CARD_ACCOUNT[("Card account master")]
  DA_TRANSACTION[("Card transaction history")]
  TS_COLLIBRA[/"Collibra<br/>[Data catalog]"/]
  DA_CUST360_CURATED[("Customer 360 curated<br/>dataset")]
  SYS_CUST360_PIPELINE["Customer 360 Pipeline<br/>[Snowflake Data Cloud +1]"]
  SYS_CUST360_SEMANTIC["Customer 360 Semantic<br/>Layer<br/>[Snowflake Data Cloud]"]
  DA_CUSTOMER_PROFILE[("Customer profile")]
  TS_SNOWFLAKE[/"Snowflake<br/>[Data warehouse]"/]

  SYS_CUST360_PIPELINE -->|"SQL"| SYS_CUST360_SEMANTIC
  SYS_CUST360_PIPELINE -.->|"runs on"| TS_SNOWFLAKE
  SYS_CUST360_PIPELINE -.->|"runs on"| TS_COLLIBRA
  SYS_CUST360_SEMANTIC -.->|"runs on"| TS_SNOWFLAKE
  SYS_CUST360_PIPELINE -->|"Write"| DA_CUST360_CURATED
  SYS_CUST360_SEMANTIC -->|"Read"| DA_CUST360_CURATED
  SYS_CUST360_PIPELINE -->|"Read"| DA_CARD_ACCOUNT
  SYS_CUST360_PIPELINE -->|"Read"| DA_CUSTOMER_PROFILE
  SYS_CUST360_PIPELINE -->|"Read"| DA_TRANSACTION

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_CARD_ACCOUNT,DA_CUST360_CURATED,DA_CUSTOMER_PROFILE,DA_TRANSACTION s_data_assets__data_assets;
  class SYS_CUST360_PIPELINE,SYS_CUST360_SEMANTIC s_systems__systems;
  class TS_COLLIBRA,TS_SNOWFLAKE s_tech_services__tech_services;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Customer 360 — By part](../svg/product-parts--prd-customer-360.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer) — not on this diagram
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL)
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

8 entities, 9 relationships. Generated from the model; edit the model, not this file.
