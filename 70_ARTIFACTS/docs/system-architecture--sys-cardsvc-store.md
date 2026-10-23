# Card Servicing Datastore — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Card Servicing Datastore — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CARD_ACCOUNT[("Card account master")]
    DA_CARDSVC_OPERATIONAL[("Card Servicing operational<br/>data")]
    DA_TRANSACTION[("Card transaction history")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARDSVC_STORE["Card Servicing Datastore<br/>[Azure SQL]"]
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
    TS_AZURE_SQL[/"Azure SQL Database<br/>[Relational database]"/]
    TS_CARDSVC_BACKUP[/"Card Servicing Backup and<br/>recovery<br/>[Azure Backup]"/]
    TS_CARDSVC_CACHE[/"Card Servicing Cache<br/>[Azure Cache for Redis]"/]
  end

  SYS_CARDSVC_API -->|"TDS"| SYS_CARDSVC_STORE
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_APIM
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_AKS
  SYS_CARDSVC_API -.->|"runs on"| TS_CARDSVC_CACHE
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_MONITOR
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_CARDSVC_STORE -.->|"runs on"| TS_AZURE_SQL
  SYS_CARDSVC_STORE -.->|"runs on"| TS_CARDSVC_BACKUP
  SYS_CARDSVC_STORE -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_CARDSVC_API -->|"ReadWrite"| DA_CARDSVC_OPERATIONAL
  SYS_CARDSVC_STORE -->|"ReadWrite"| DA_CARDSVC_OPERATIONAL
  SYS_CARDSVC_API -->|"Read"| DA_CARD_ACCOUNT
  SYS_CARDSVC_API -->|"Read"| DA_TRANSACTION

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_CARD_ACCOUNT,DA_CARDSVC_OPERATIONAL,DA_TRANSACTION s_data_assets__data_assets;
  class SYS_CARDSVC_API,SYS_CARDSVC_STORE s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_AZURE_SQL,TS_CARDSVC_BACKUP,TS_CARDSVC_CACHE s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card Servicing Datastore — Architecture](../svg/system-architecture--sys-cardsvc-store.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

12 entities, 13 relationships. Generated from the model; edit the model, not this file.
