# Customer 360 — Onboarding

What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart TB
  %% Customer 360 — Onboarding
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction TB
    subgraph grp_Azure__azure_data_prod["subscription azure-data-prod"]
      direction TB
      subgraph grp_Azure__azure_data_prod__uksouth["region uksouth"]
        direction TB
        subgraph grp_Azure__azure_data_prod__uksouth__Private_Data["Private-Data"]
          direction TB
          SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
        end
      end
    end
    subgraph grp_Azure__azure_risk_prod["subscription azure-risk-prod"]
      direction TB
      subgraph grp_Azure__azure_risk_prod__uksouth["region uksouth"]
        direction TB
        subgraph grp_Azure__azure_risk_prod__uksouth__Private_App["Private-App"]
          direction TB
          SYS_REG_REPORTING["Regulatory Reporting<br/>Engine<br/>[AKS · Snowflake Data Cloud]"]
        end
      end
    end
  end

  SYS_CUST360_PIPELINE["Customer 360 Pipeline<br/>[Snowflake Data Cloud +1]"]
  SYS_CUST360_SEMANTIC["Customer 360 Semantic<br/>Layer<br/>[Snowflake Data Cloud]"]

  SYS_CUST360_SEMANTIC -->|"SQL"| SYS_REG_REPORTING
  SYS_DATA_INGEST -->|"Snowpipe"| SYS_CUST360_PIPELINE
  SYS_CUST360_PIPELINE -->|"SQL"| SYS_CUST360_SEMANTIC

  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_app fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_data fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class SYS_CUST360_PIPELINE,SYS_CUST360_SEMANTIC s_systems__default;
  class SYS_REG_REPORTING s_systems__private_app;
  class SYS_DATA_INGEST s_systems__private_data;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_data_prod__uksouth__Private_Data,grp_Azure__azure_risk_prod__uksouth__Private_App boundary1;
  classDef boundary2 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_data_prod,grp_Azure__azure_risk_prod boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary3;
  classDef boundary4 fill:#f8fafc,stroke:#7a8699,color:#4b5563,stroke-dasharray:2 3;
  class grp_Azure__azure_data_prod__uksouth,grp_Azure__azure_risk_prod__uksouth boundary4;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Customer 360 — Onboarding](../svg/onboarding--prd-customer-360.svg)

**network zone** is the boundary each node sits in.

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#0078d4` | Azure |
| dashed `#0078d4` | Azure subscription |
| dotted `#7a8699` | Azure region |
| solid `#5b9bd5` | Azure subnet |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer) — not on this diagram
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe)
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL)
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL)

4 entities, 3 relationships. Generated from the model; edit the model, not this file.
