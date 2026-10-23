# Rewards Redemption — Architecture

One product in full: the systems it is made of, what each runs on, the data it masters, who uses it, and everything one hop away that it connects to. For a product built from modules, every box corresponds to a part.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Rewards Redemption — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_EVENTHUBS[/"Azure Event Hubs<br/>[Event stream]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
    TS_AZURE_SERVICEBUS[/"Azure Service Bus<br/>[Message queue]"/]
    TS_AZURE_SQL[/"Azure SQL Database<br/>[Relational database]"/]
    subgraph grp_Azure__azure_cards_prod["subscription azure-cards-prod"]
      direction LR
      SYS_REWARDS_EVENTS["Rewards Redemption Event<br/>Publisher<br/>[Service Bus]"]
      subgraph grp_Azure__azure_cards_prod__Edge["Edge"]
        direction LR
        TS_REWARDS_DNS[/"Rewards Redemption DNS<br/>[Azure DNS]"/]
        TS_REWARDS_WAF[/"Rewards Redemption Web<br/>application firewall<br/>[Azure WAF]"/]
      end
      subgraph grp_Azure__azure_cards_prod__Private_App["Private-App"]
        direction LR
        OI_REWARDS_API("Rewards Redemption API<br/>[HTTPS]")
        SYS_REWARDS_WORKER["Rewards Redemption Async<br/>Worker<br/>[AKS · Event Hubs]"]
        TS_REWARDS_CACHE[/"Rewards Redemption Cache<br/>[Azure Cache for Redis]"/]
        SYS_REWARDS_API["Rewards Redemption Service<br/>[AKS · Rewards Redemption Cache]"]
        SYS_REWARDS_WEB["Rewards Redemption Web<br/>[AKS]"]
      end
      subgraph grp_Azure__azure_cards_prod__Private_Data["Private-Data"]
        direction LR
        TS_REWARDS_BACKUP[/"Rewards Redemption Backup<br/>and recovery<br/>[Azure Backup]"/]
        SYS_REWARDS_STORE["Rewards Redemption<br/>Database<br/>[Azure SQL]"]
      end
    end
  end

  subgraph grp_On_prem["On-prem"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
  end

  TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
  DA_REWARDS_OPERATIONAL[("Rewards Redemption<br/>operational data")]

  SYS_REWARDS_WEB --> OI_REWARDS_API
  SYS_REWARDS_API -->|"TDS"| SYS_REWARDS_STORE
  SYS_REWARDS_API -->|"AMQP"| SYS_REWARDS_EVENTS
  SYS_REWARDS_API -->|"Kafka"| SYS_REWARDS_WORKER
  SYS_REWARDS_WORKER --> OI_LEDGER_QUEUE
  SYS_REWARDS_API -.->|"runs on"| TS_AZURE_APIM
  SYS_REWARDS_API -.->|"runs on"| TS_AZURE_AKS
  SYS_REWARDS_API -.->|"runs on"| TS_REWARDS_CACHE
  SYS_REWARDS_API -.->|"runs on"| TS_AZURE_MONITOR
  SYS_REWARDS_API -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_REWARDS_WEB -.->|"runs on"| TS_REWARDS_DNS
  SYS_REWARDS_WEB -.->|"runs on"| TS_REWARDS_WAF
  SYS_REWARDS_WEB -.->|"runs on"| TS_AZURE_AKS
  SYS_REWARDS_WEB -.->|"runs on"| TS_ENTRA_ID
  SYS_REWARDS_STORE -.->|"runs on"| TS_AZURE_SQL
  SYS_REWARDS_STORE -.->|"runs on"| TS_REWARDS_BACKUP
  SYS_REWARDS_STORE -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_REWARDS_EVENTS -.->|"runs on"| TS_AZURE_SERVICEBUS
  SYS_REWARDS_WORKER -.->|"runs on"| TS_AZURE_AKS
  SYS_REWARDS_WORKER -.->|"runs on"| TS_AZURE_MONITOR
  SYS_REWARDS_WORKER -.->|"runs on"| TS_AZURE_EVENTHUBS
  SYS_REWARDS_API -->|"ReadWrite"| DA_REWARDS_OPERATIONAL
  SYS_REWARDS_STORE -->|"ReadWrite"| DA_REWARDS_OPERATIONAL
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER
  OI_REWARDS_API --- SYS_REWARDS_API

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_REWARDS_OPERATIONAL s_data_assets__data_assets;
  class OI_LEDGER_QUEUE,OI_REWARDS_API s_offered_interfaces__offered_interfaces;
  class SYS_CORE_LEDGER,SYS_REWARDS_API,SYS_REWARDS_EVENTS,SYS_REWARDS_STORE,SYS_REWARDS_WEB,SYS_REWARDS_WORKER s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_EVENTHUBS,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_AZURE_SERVICEBUS,TS_AZURE_SQL,TS_ENTRA_ID,TS_REWARDS_BACKUP,TS_REWARDS_CACHE,TS_REWARDS_DNS,TS_REWARDS_WAF s_tech_services__tech_services;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_cards_prod__Edge,grp_Azure__azure_cards_prod__Private_App,grp_Azure__azure_cards_prod__Private_Data boundary1;
  classDef boundary2 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_cards_prod boundary3;
  classDef boundary4 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary4;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Rewards Redemption — Architecture](../svg/product-architecture--prd-rewards.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
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

21 entities, 25 relationships. Generated from the model; edit the model, not this file.
