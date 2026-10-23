# Dispute Management — Onboarding

What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart TB
  %% Dispute Management — Onboarding
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction TB
    subgraph grp_Azure__azure_cards_prod["subscription azure-cards-prod"]
      direction TB
      subgraph grp_Azure__azure_cards_prod__uksouth["region uksouth"]
        direction TB
        subgraph grp_Azure__azure_cards_prod__uksouth__Private_App["Private-App"]
          direction TB
          SYS_DISPUTES_GATEWAY["Dispute Management<br/>Platform Integration<br/>Gateway<br/>[AKS]"]
        end
      end
    end
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
  end

  subgraph grp_On_prem["On-prem"]
    direction TB
    SYS_CORE_LEDGER["Core Card Ledger"]
  end

  subgraph grp_SaaS["SaaS"]
    direction TB
    subgraph grp_SaaS__Edge["Edge"]
      direction TB
      SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    end
    subgraph grp_SaaS__eu_west_1["region eu-west-1"]
      direction TB
      subgraph grp_SaaS__eu_west_1__Edge["Edge"]
        direction TB
        SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
      end
    end
  end

  SYS_CRM -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_CRM -->|"HTTPS"| SYS_CORE_LEDGER
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_DISPUTES_GATEWAY -->|"HTTPS"| SYS_DISPUTES_SAAS
  SYS_DISPUTES_SAAS -->|"SFTP"| SYS_DATA_INGEST

  classDef s_systems__edge fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__on_prem fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_app fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_data fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class SYS_CRM,SYS_DISPUTES_SAAS s_systems__edge;
  class SYS_CORE_LEDGER s_systems__on_prem;
  class SYS_DISPUTES_GATEWAY s_systems__private_app;
  class SYS_DATA_INGEST s_systems__private_data;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_cards_prod__uksouth__Private_App,grp_Azure__azure_data_prod__uksouth__Private_Data boundary1;
  classDef boundary2 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_cards_prod,grp_Azure__azure_data_prod boundary3;
  classDef boundary4 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary4;
  classDef boundary5 fill:#f8fafc,stroke:#7a8699,color:#4b5563,stroke-dasharray:2 3;
  class grp_Azure__azure_cards_prod__uksouth,grp_Azure__azure_data_prod__uksouth boundary5;
  classDef boundary6 fill:#f8fafc,stroke:#8f9bb5,color:#3b4a6b,stroke-dasharray:6 3;
  class grp_SaaS__eu_west_1 boundary6;
  classDef boundary7 fill:#fcfbf7,stroke:#9a8f6a,color:#6b6246,stroke-dasharray:6 3;
  class grp_SaaS,grp_SaaS__Edge,grp_SaaS__eu_west_1__Edge boundary7;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Dispute Management — Onboarding](../svg/onboarding--prd-disputes.svg)

**network zone** is the boundary each node sits in.

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#0078d4` | Azure |
| solid `#5f6b7a` | On-prem |
| dashed `#9a8f6a` | SaaS |
| dashed `#0078d4` | Azure subscription |
| dashed `#9a8f6a` | vendor tenancy |
| dashed `#8f9bb5` | SaaS region |
| dotted `#7a8699` | Azure region |
| solid `#5b9bd5` | Azure subnet |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Dispute and Chargeback**: A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

1. Dynamics 365 Customer Service → Core Card Ledger (HTTPS)
2. Core Card Ledger → Dispute Management Platform Integration Gateway (HTTPS)
3. Dispute Management Platform Integration Gateway → Pega Smart Dispute (HTTPS)
4. Pega Smart Dispute → Enterprise Data Ingestion Hub (SFTP)

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL) — not on this diagram
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

5 entities, 6 relationships. Generated from the model; edit the model, not this file.
