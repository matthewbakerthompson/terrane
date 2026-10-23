# Collections Workspace — Architecture

One product in full: the systems it is made of, what each runs on, the data it masters, who uses it, and everything one hop away that it connects to. For a product built from modules, every box corresponds to a part.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Collections Workspace — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
    TS_AZURE_SQL[/"Azure SQL Database<br/>[Relational database]"/]
    subgraph grp_Azure__azure_cards_prod["subscription azure-cards-prod"]
      direction LR
      subgraph grp_Azure__azure_cards_prod__Edge["Edge"]
        direction LR
        TS_COLLECT_DNS[/"Collections Workspace DNS<br/>[Azure DNS]"/]
        TS_COLLECT_WAF[/"Collections Workspace Web<br/>application firewall<br/>[Azure WAF]"/]
      end
      subgraph grp_Azure__azure_cards_prod__Private_App["Private-App"]
        direction LR
        OI_COLLECT_API("Collections Workspace API<br/>[HTTPS]")
        TS_COLLECT_CACHE[/"Collections Workspace<br/>Cache<br/>[Azure Cache for Redis]"/]
        SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
        SYS_COLLECT_WEB["Collections Workspace Web<br/>[AKS]"]
      end
      subgraph grp_Azure__azure_cards_prod__Private_Data["Private-Data"]
        direction LR
        TS_COLLECT_BACKUP[/"Collections Workspace<br/>Backup and recovery<br/>[Azure Backup]"/]
        SYS_COLLECT_STORE["Collections Workspace<br/>Datastore<br/>[Azure SQL]"]
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
  DA_COLLECT_ACT[("Collections activity<br/>record")]
  ACT_COLLECTIONS_AGENT(["Collections Agent"])
  DA_COLLECT_OPERATIONAL[("Collections Workspace<br/>operational data")]
  SYS_DOC["Document management and<br/>archive"]
  TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
  SYS_DIALER["Outbound contact platform"]

  SYS_COLLECT_API -->|"FileTransfer"| SYS_DIALER
  SYS_DIALER -->|"AMQP"| SYS_COLLECT_API
  SYS_COLLECT_API -->|"AMQP"| SYS_DOC
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DOC
  SYS_COLLECT_API --> OI_IDENTITY_API
  SYS_COLLECT_API --> OI_LEDGER_QUEUE
  SYS_COLLECT_WEB --> OI_COLLECT_API
  SYS_COLLECT_API -->|"TDS"| SYS_COLLECT_STORE
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_APIM
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_AKS
  SYS_COLLECT_API -.->|"runs on"| TS_COLLECT_CACHE
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_MONITOR
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_COLLECT_WEB -.->|"runs on"| TS_COLLECT_DNS
  SYS_COLLECT_WEB -.->|"runs on"| TS_COLLECT_WAF
  SYS_COLLECT_WEB -.->|"runs on"| TS_AZURE_AKS
  SYS_COLLECT_WEB -.->|"runs on"| TS_ENTRA_ID
  SYS_COLLECT_STORE -.->|"runs on"| TS_AZURE_SQL
  SYS_COLLECT_STORE -.->|"runs on"| TS_COLLECT_BACKUP
  SYS_COLLECT_STORE -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_APIM
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_AKS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_COLLECT_API -->|"ReadWrite"| DA_COLLECT_OPERATIONAL
  SYS_COLLECT_STORE -->|"ReadWrite"| DA_COLLECT_OPERATIONAL
  SYS_COLLECT_API -->|"ReadWrite"| DA_COLLECT_ACT
  SYS_DIALER -->|"ReadWrite"| DA_COLLECT_ACT
  SYS_COLLECT_API -->|"Read"| DA_CARD_ACCOUNT
  SYS_CORE_LEDGER -->|"ReadWrite"| DA_CARD_ACCOUNT
  ACT_COLLECTIONS_AGENT -->|"Works arrears"| SYS_COLLECT_WEB
  ACT_COLLECTIONS_AGENT -->|"Outbound campaigns"| SYS_DIALER
  OI_COLLECT_API --- SYS_COLLECT_API
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER

  classDef s_actors__actors fill:#fde68a,stroke:#b45309,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class ACT_COLLECTIONS_AGENT s_actors__actors;
  class DA_CARD_ACCOUNT,DA_COLLECT_ACT,DA_COLLECT_OPERATIONAL s_data_assets__data_assets;
  class OI_COLLECT_API,OI_IDENTITY_API,OI_LEDGER_QUEUE s_offered_interfaces__offered_interfaces;
  class SYS_COLLECT_API,SYS_COLLECT_STORE,SYS_COLLECT_WEB,SYS_CORE_LEDGER,SYS_DIALER,SYS_DOC,SYS_IDENTITY_SVC s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_AZURE_SQL,TS_COLLECT_BACKUP,TS_COLLECT_CACHE,TS_COLLECT_DNS,TS_COLLECT_WAF,TS_ENTRA_ID s_tech_services__tech_services;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_cards_prod__Edge,grp_Azure__azure_cards_prod__Private_App,grp_Azure__azure_cards_prod__Private_Data,grp_Azure__azure_platform_prod__Shared_Services boundary1;
  classDef boundary2 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_cards_prod,grp_Azure__azure_platform_prod boundary3;
  classDef boundary4 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary4;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Collections Workspace — Architecture](../svg/product-architecture--prd-collections-workspace.svg)

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

24 entities, 34 relationships. Generated from the model; edit the model, not this file.
