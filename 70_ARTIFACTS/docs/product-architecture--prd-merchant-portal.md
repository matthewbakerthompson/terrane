# Merchant Portal — Architecture

One product in full: the systems it is made of, what each runs on, the data it masters, who uses it, and everything one hop away that it connects to. For a product built from modules, every box corresponds to a part.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Merchant Portal — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
    TS_AZURE_SERVICEBUS[/"Azure Service Bus<br/>[Message queue]"/]
    TS_AZURE_SQL[/"Azure SQL Database<br/>[Relational database]"/]
    subgraph grp_Azure__azure_payments_prod["subscription azure-payments-prod"]
      direction LR
      SYS_MERCHANT_EVENTS["Merchant Portal Event<br/>Publisher<br/>[Service Bus]"]
      subgraph grp_Azure__azure_payments_prod__Edge["Edge"]
        direction LR
        TS_MERCHANT_DNS[/"Merchant Portal DNS<br/>[Azure DNS]"/]
        TS_MERCHANT_WAF[/"Merchant Portal Web<br/>application firewall<br/>[Azure WAF]"/]
      end
      subgraph grp_Azure__azure_payments_prod__Private_App["Private-App"]
        direction LR
        OI_MERCHANT_API("Merchant Portal API<br/>[HTTPS]")
        TS_MERCHANT_CACHE[/"Merchant Portal Cache<br/>[Azure Cache for Redis]"/]
        SYS_MERCHANT_API["Merchant Portal Service<br/>[AKS · Merchant Portal Cache]"]
        SYS_MERCHANT_WEB["Merchant Portal Web<br/>[AKS]"]
      end
      subgraph grp_Azure__azure_payments_prod__Private_Data["Private-Data"]
        direction LR
        TS_MERCHANT_BACKUP[/"Merchant Portal Backup and<br/>recovery<br/>[Azure Backup]"/]
        SYS_MERCHANT_STORE["Merchant Portal Database<br/>[Azure SQL]"]
      end
    end
  end

  ACT_MERCHANT_ONBOARDING_ANALYST(["Merchant Onboarding<br/>Analyst"])
  DA_MERCHANT_OPERATIONAL[("Merchant Portal<br/>operational data")]
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
  ACT_MERCHANT_ONBOARDING_ANALYST -->|"Reviews applications"| SYS_MERCHANT_API
  OI_MERCHANT_API --- SYS_MERCHANT_API

  classDef s_actors__actors fill:#fde68a,stroke:#b45309,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class ACT_MERCHANT_ONBOARDING_ANALYST s_actors__actors;
  class DA_MERCHANT_OPERATIONAL s_data_assets__data_assets;
  class OI_MERCHANT_API s_offered_interfaces__offered_interfaces;
  class SYS_MERCHANT_API,SYS_MERCHANT_EVENTS,SYS_MERCHANT_STORE,SYS_MERCHANT_WEB s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_AZURE_SERVICEBUS,TS_AZURE_SQL,TS_ENTRA_ID,TS_MERCHANT_BACKUP,TS_MERCHANT_CACHE,TS_MERCHANT_DNS,TS_MERCHANT_WAF s_tech_services__tech_services;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_payments_prod__Edge,grp_Azure__azure_payments_prod__Private_App,grp_Azure__azure_payments_prod__Private_Data boundary1;
  classDef boundary2 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_payments_prod boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary3;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Merchant Portal — Architecture](../svg/product-architecture--prd-merchant-portal.svg)

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
| dashed `#0078d4` | Azure subscription |
| solid `#5b9bd5` | Azure subnet |

18 entities, 19 relationships. Generated from the model; edit the model, not this file.
