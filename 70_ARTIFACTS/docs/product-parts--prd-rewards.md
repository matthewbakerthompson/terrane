# Rewards Redemption — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Rewards Redemption — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_api_service["api-service"]
    direction LR
    OI_REWARDS_API("Rewards Redemption API<br/>[HTTPS]")
    SYS_REWARDS_API["Rewards Redemption Service<br/>[AKS · Rewards Redemption Cache]"]
  end

  subgraph grp_async_worker["async-worker"]
    direction LR
    SYS_REWARDS_WORKER["Rewards Redemption Async<br/>Worker<br/>[AKS · Event Hubs]"]
  end

  subgraph grp_event_publisher["event-publisher"]
    direction LR
    SYS_REWARDS_EVENTS["Rewards Redemption Event<br/>Publisher<br/>[Service Bus]"]
  end

  subgraph grp_relational_datastore["relational-datastore"]
    direction LR
    SYS_REWARDS_STORE["Rewards Redemption<br/>Database<br/>[Azure SQL]"]
    DA_REWARDS_OPERATIONAL[("Rewards Redemption<br/>operational data")]
  end

  subgraph grp_web_channel["web-channel"]
    direction LR
    SYS_REWARDS_WEB["Rewards Redemption Web<br/>[AKS]"]
  end

  TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
  TS_AZURE_EVENTHUBS[/"Azure Event Hubs<br/>[Event stream]"/]
  TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
  TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
  TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
  TS_AZURE_SERVICEBUS[/"Azure Service Bus<br/>[Message queue]"/]
  TS_AZURE_SQL[/"Azure SQL Database<br/>[Relational database]"/]
  TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
  TS_REWARDS_BACKUP[/"Rewards Redemption Backup<br/>and recovery<br/>[Azure Backup]"/]
  TS_REWARDS_CACHE[/"Rewards Redemption Cache<br/>[Azure Cache for Redis]"/]
  TS_REWARDS_DNS[/"Rewards Redemption DNS<br/>[Azure DNS]"/]
  TS_REWARDS_WAF[/"Rewards Redemption Web<br/>application firewall<br/>[Azure WAF]"/]

  SYS_REWARDS_WEB --> OI_REWARDS_API
  SYS_REWARDS_API -->|"TDS"| SYS_REWARDS_STORE
  SYS_REWARDS_API -->|"AMQP"| SYS_REWARDS_EVENTS
  SYS_REWARDS_API -->|"Kafka"| SYS_REWARDS_WORKER
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
  OI_REWARDS_API --- SYS_REWARDS_API

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_REWARDS_OPERATIONAL s_data_assets__data_assets;
  class OI_REWARDS_API s_offered_interfaces__offered_interfaces;
  class SYS_REWARDS_API,SYS_REWARDS_EVENTS,SYS_REWARDS_STORE,SYS_REWARDS_WEB,SYS_REWARDS_WORKER s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_EVENTHUBS,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_AZURE_SERVICEBUS,TS_AZURE_SQL,TS_ENTRA_ID,TS_REWARDS_BACKUP,TS_REWARDS_CACHE,TS_REWARDS_DNS,TS_REWARDS_WAF s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_api_service,grp_async_worker,grp_event_publisher,grp_relational_datastore,grp_web_channel boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Rewards Redemption — By part](../svg/product-parts--prd-rewards.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |
| `#c2410c` | tech services |

19 entities, 23 relationships. Generated from the model; edit the model, not this file.
