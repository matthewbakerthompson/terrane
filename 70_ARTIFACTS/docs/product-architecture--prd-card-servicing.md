# Card Servicing — Architecture

One product in full: the systems it is made of, what each runs on, the data it masters, who uses it, and everything one hop away that it connects to. For a product built from modules, every box corresponds to a part.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Card Servicing — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
    TS_AZURE_SERVICEBUS[/"Azure Service Bus<br/>[Message queue]"/]
    TS_AZURE_SQL[/"Azure SQL Database<br/>[Relational database]"/]
    subgraph grp_Azure__azure_cards_prod["subscription azure-cards-prod"]
      direction LR
      SYS_CARDSVC_EVENTS["Card Servicing Event<br/>Publisher<br/>[Service Bus]"]
      subgraph grp_Azure__azure_cards_prod__Edge["Edge"]
        direction LR
        TS_CARDSVC_DNS[/"Card Servicing DNS<br/>[Azure DNS]"/]
        TS_CARDSVC_WAF[/"Card Servicing Web<br/>application firewall<br/>[Azure WAF]"/]
      end
      subgraph grp_Azure__azure_cards_prod__Private_App["Private-App"]
        direction LR
        OI_CARDSVC_API("Card Servicing API<br/>[HTTPS]")
        TS_CARDSVC_CACHE[/"Card Servicing Cache<br/>[Azure Cache for Redis]"/]
        SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
        SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
      end
      subgraph grp_Azure__azure_cards_prod__Private_Data["Private-Data"]
        direction LR
        TS_CARDSVC_BACKUP[/"Card Servicing Backup and<br/>recovery<br/>[Azure Backup]"/]
        SYS_CARDSVC_STORE["Card Servicing Datastore<br/>[Azure SQL]"]
      end
    end
    subgraph grp_Azure__azure_data_prod["subscription azure-data-prod"]
      direction LR
      subgraph grp_Azure__azure_data_prod__Private_Data["Private-Data"]
        direction LR
        SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
      end
    end
    subgraph grp_Azure__azure_platform_prod["subscription azure-platform-prod"]
      direction LR
      subgraph grp_Azure__azure_platform_prod__Shared_Services["Shared-Services"]
        direction LR
        OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
        SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
      end
    end
  end

  subgraph grp_On_prem["On-prem"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
  end

  DA_CARD_ACCOUNT[("Card account master")]
  DA_CARDSVC_OPERATIONAL[("Card Servicing operational<br/>data")]
  DA_TRANSACTION[("Card transaction history")]
  ACT_CARDHOLDER(["Cardholder"])
  SYS_MOBILE["Cardholder mobile<br/>application"]
  SYS_IVR["IVR and self-service voice"]
  TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]

  SYS_MOBILE --> OI_CARDSVC_API
  SYS_IVR --> OI_CARDSVC_API
  SYS_CARDSVC_API --> OI_IDENTITY_API
  SYS_CARDSVC_API --> OI_LEDGER_QUEUE
  SYS_CARDSVC_EVENTS -->|"AMQP"| SYS_DATA_INGEST
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_CARDSVC_WEB --> OI_CARDSVC_API
  SYS_CARDSVC_API -->|"TDS"| SYS_CARDSVC_STORE
  SYS_CARDSVC_API -->|"AMQP"| SYS_CARDSVC_EVENTS
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_APIM
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_AKS
  SYS_CARDSVC_API -.->|"runs on"| TS_CARDSVC_CACHE
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_MONITOR
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_CARDSVC_WEB -.->|"runs on"| TS_CARDSVC_DNS
  SYS_CARDSVC_WEB -.->|"runs on"| TS_CARDSVC_WAF
  SYS_CARDSVC_WEB -.->|"runs on"| TS_AZURE_AKS
  SYS_CARDSVC_WEB -.->|"runs on"| TS_ENTRA_ID
  SYS_CARDSVC_STORE -.->|"runs on"| TS_AZURE_SQL
  SYS_CARDSVC_STORE -.->|"runs on"| TS_CARDSVC_BACKUP
  SYS_CARDSVC_STORE -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_CARDSVC_EVENTS -.->|"runs on"| TS_AZURE_SERVICEBUS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_APIM
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_AKS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_DATA_INGEST -.->|"runs on"| TS_AZURE_SERVICEBUS
  SYS_CARDSVC_API -->|"ReadWrite"| DA_CARDSVC_OPERATIONAL
  SYS_CARDSVC_STORE -->|"ReadWrite"| DA_CARDSVC_OPERATIONAL
  SYS_MOBILE -->|"Read"| DA_CARD_ACCOUNT
  SYS_MOBILE -->|"Read"| DA_TRANSACTION
  SYS_IVR -->|"Read"| DA_CARD_ACCOUNT
  SYS_CARDSVC_API -->|"Read"| DA_CARD_ACCOUNT
  SYS_CARDSVC_API -->|"Read"| DA_TRANSACTION
  SYS_CORE_LEDGER -->|"ReadWrite"| DA_CARD_ACCOUNT
  ACT_CARDHOLDER -->|"Self-service"| SYS_CARDSVC_WEB
  ACT_CARDHOLDER -->|"Mobile self-service"| SYS_MOBILE
  ACT_CARDHOLDER -->|"Voice self-service"| SYS_IVR
  OI_CARDSVC_API --- SYS_CARDSVC_API
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER

  classDef s_actors__actors fill:#fde68a,stroke:#b45309,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class ACT_CARDHOLDER s_actors__actors;
  class DA_CARD_ACCOUNT,DA_CARDSVC_OPERATIONAL,DA_TRANSACTION s_data_assets__data_assets;
  class OI_CARDSVC_API,OI_IDENTITY_API,OI_LEDGER_QUEUE s_offered_interfaces__offered_interfaces;
  class SYS_CARDSVC_API,SYS_CARDSVC_EVENTS,SYS_CARDSVC_STORE,SYS_CARDSVC_WEB,SYS_CORE_LEDGER,SYS_DATA_INGEST,SYS_IDENTITY_SVC,SYS_IVR,SYS_MOBILE s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_AZURE_SERVICEBUS,TS_AZURE_SQL,TS_CARDSVC_BACKUP,TS_CARDSVC_CACHE,TS_CARDSVC_DNS,TS_CARDSVC_WAF,TS_ENTRA_ID s_tech_services__tech_services;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_cards_prod__Edge,grp_Azure__azure_cards_prod__Private_App,grp_Azure__azure_cards_prod__Private_Data,grp_Azure__azure_data_prod__Private_Data,grp_Azure__azure_platform_prod__Shared_Services boundary1;
  classDef boundary2 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_cards_prod,grp_Azure__azure_data_prod,grp_Azure__azure_platform_prod boundary3;
  classDef boundary4 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary4;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card Servicing — Architecture](../svg/product-architecture--prd-card-servicing.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#b45309` | actors |
| `#047857` | data assets |
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |
| `#c2410c` | tech services |

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#0078d4` | Azure |
| solid `#5f6b7a` | On-prem |
| dashed `#0078d4` | Azure subscription |
| solid `#5b9bd5` | Azure subnet |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL) — not on this diagram
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

27 entities, 40 relationships. Generated from the model; edit the model, not this file.
