# Merchant Portal — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Merchant Portal — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_api_service["api-service"]
    direction LR
    OI_MERCHANT_API("Merchant Portal API<br/>[HTTPS]")
    SYS_MERCHANT_API["Merchant Portal Service<br/>[AKS · Merchant Portal Cache]"]
  end

  subgraph grp_event_publisher["event-publisher"]
    direction LR
    SYS_MERCHANT_EVENTS["Merchant Portal Event<br/>Publisher<br/>[Service Bus]"]
  end

  subgraph grp_relational_datastore["relational-datastore"]
    direction LR
    SYS_MERCHANT_STORE["Merchant Portal Database<br/>[Azure SQL]"]
    DA_MERCHANT_OPERATIONAL[("Merchant Portal<br/>operational data")]
  end

  subgraph grp_web_channel["web-channel"]
    direction LR
    SYS_MERCHANT_WEB["Merchant Portal Web<br/>[AKS]"]
  end

  TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
  TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
  TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
  TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
  TS_AZURE_SERVICEBUS[/"Azure Service Bus<br/>[Message queue]"/]
  TS_AZURE_SQL[/"Azure SQL Database<br/>[Relational database]"/]
  TS_MERCHANT_BACKUP[/"Merchant Portal Backup and<br/>recovery<br/>[Azure Backup]"/]
  TS_MERCHANT_CACHE[/"Merchant Portal Cache<br/>[Azure Cache for Redis]"/]
  TS_MERCHANT_DNS[/"Merchant Portal DNS<br/>[Azure DNS]"/]
  TS_MERCHANT_WAF[/"Merchant Portal Web<br/>application firewall<br/>[Azure WAF]"/]
  TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]

  SYS_MERCHANT_WEB --> OI_MERCHANT_API
  SYS_MERCHANT_API -->|"TDS"| SYS_MERCHANT_STORE
  SYS_MERCHANT_API -->|"AMQP"| SYS_MERCHANT_EVENTS
  SYS_MERCHANT_API -.->|"runs on"| TS_AZURE_APIM
  SYS_MERCHANT_API -.->|"runs on"| TS_AZURE_AKS
  SYS_MERCHANT_API -.->|"runs on"| TS_MERCHANT_CACHE
  SYS_MERCHANT_API -.->|"runs on"| TS_AZURE_MONITOR
  SYS_MERCHANT_API -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_MERCHANT_WEB -.->|"runs on"| TS_MERCHANT_DNS
  SYS_MERCHANT_WEB -.->|"runs on"| TS_MERCHANT_WAF
  SYS_MERCHANT_WEB -.->|"runs on"| TS_AZURE_AKS
  SYS_MERCHANT_WEB -.->|"runs on"| TS_ENTRA_ID
  SYS_MERCHANT_STORE -.->|"runs on"| TS_AZURE_SQL
  SYS_MERCHANT_STORE -.->|"runs on"| TS_MERCHANT_BACKUP
  SYS_MERCHANT_STORE -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_MERCHANT_EVENTS -.->|"runs on"| TS_AZURE_SERVICEBUS
  SYS_MERCHANT_API -->|"ReadWrite"| DA_MERCHANT_OPERATIONAL
  OI_MERCHANT_API --- SYS_MERCHANT_API

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_MERCHANT_OPERATIONAL s_data_assets__data_assets;
  class OI_MERCHANT_API s_offered_interfaces__offered_interfaces;
  class SYS_MERCHANT_API,SYS_MERCHANT_EVENTS,SYS_MERCHANT_STORE,SYS_MERCHANT_WEB s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_AZURE_SERVICEBUS,TS_AZURE_SQL,TS_ENTRA_ID,TS_MERCHANT_BACKUP,TS_MERCHANT_CACHE,TS_MERCHANT_DNS,TS_MERCHANT_WAF s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_api_service,grp_event_publisher,grp_relational_datastore,grp_web_channel boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Merchant Portal — By part](../svg/product-parts--prd-merchant-portal.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |
| `#c2410c` | tech services |

17 entities, 18 relationships. Generated from the model; edit the model, not this file.
