# Dispute Management — Architecture

One product in full: the systems it is made of, what each runs on, the data it masters, who uses it, and everything one hop away that it connects to. For a product built from modules, every box corresponds to a part.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Dispute Management — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    subgraph grp_Azure__azure_cards_prod["subscription azure-cards-prod"]
      direction LR
      subgraph grp_Azure__azure_cards_prod__Private_App["Private-App"]
        direction LR
        SYS_DISPUTES_GATEWAY["Dispute Management<br/>Platform Integration<br/>Gateway<br/>[AKS]"]
      end
    end
    subgraph grp_Azure__azure_data_prod["subscription azure-data-prod"]
      direction LR
      subgraph grp_Azure__azure_data_prod__Private_Data["Private-Data"]
        direction LR
        SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
      end
    end
  end

  subgraph grp_On_prem["On-prem"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
  end

  subgraph grp_SaaS["SaaS"]
    direction LR
    subgraph grp_SaaS__Edge["Edge"]
      direction LR
      SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
      SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
    end
  end

  DA_DISPUTES_VENDOR_FEED[("Dispute Management<br/>Platform vendor feed")]
  ACT_SERVICING_AGENT(["Servicing Agent"])

  SYS_CRM -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_CRM -->|"HTTPS"| SYS_CORE_LEDGER
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_DISPUTES_GATEWAY -->|"HTTPS"| SYS_DISPUTES_SAAS
  SYS_DISPUTES_SAAS -->|"SFTP"| SYS_DATA_INGEST
  SYS_DISPUTES_GATEWAY -.->|"runs on"| TS_AZURE_AKS
  SYS_DISPUTES_GATEWAY -.->|"runs on"| TS_AZURE_APIM
  SYS_DISPUTES_GATEWAY -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_DISPUTES_SAAS -->|"Write"| DA_DISPUTES_VENDOR_FEED
  SYS_DATA_INGEST -->|"Read"| DA_DISPUTES_VENDOR_FEED
  ACT_SERVICING_AGENT -->|"Handles cases"| SYS_CRM
  ACT_SERVICING_AGENT -->|"Raises disputes"| SYS_DISPUTES_SAAS

  classDef s_actors__actors fill:#fde68a,stroke:#b45309,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class ACT_SERVICING_AGENT s_actors__actors;
  class DA_DISPUTES_VENDOR_FEED s_data_assets__data_assets;
  class SYS_CORE_LEDGER,SYS_CRM,SYS_DATA_INGEST,SYS_DISPUTES_GATEWAY,SYS_DISPUTES_SAAS s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT s_tech_services__tech_services;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_cards_prod__Private_App,grp_Azure__azure_data_prod__Private_Data boundary1;
  classDef boundary2 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_cards_prod,grp_Azure__azure_data_prod boundary3;
  classDef boundary4 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary4;
  classDef boundary5 fill:#fcfbf7,stroke:#9a8f6a,color:#6b6246,stroke-dasharray:6 3;
  class grp_SaaS,grp_SaaS__Edge boundary5;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Dispute Management — Architecture](../svg/product-architecture--prd-disputes.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#b45309` | actors |
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#0078d4` | Azure |
| solid `#5f6b7a` | On-prem |
| dashed `#9a8f6a` | SaaS |
| dashed `#0078d4` | Azure subscription |
| dashed `#9a8f6a` | vendor tenancy |
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

10 entities, 13 relationships. Generated from the model; edit the model, not this file.
