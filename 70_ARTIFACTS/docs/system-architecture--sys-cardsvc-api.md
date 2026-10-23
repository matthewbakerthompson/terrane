# Card Servicing Service — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Card Servicing Service — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CARD_ACCOUNT[("Card account master")]
    DA_CARDSVC_OPERATIONAL[("Card Servicing operational<br/>data")]
    DA_TRANSACTION[("Card transaction history")]
    DA_PAYMENT_INSTR[("Payment instructions")]
  end

  subgraph grp_System["System"]
    direction LR
    OI_CARDSVC_API("Card Servicing API<br/>[HTTPS]")
    SYS_CARDSVC_STORE["Card Servicing Datastore<br/>[Azure SQL]"]
    SYS_CARDSVC_EVENTS["Card Servicing Event<br/>Publisher<br/>[Service Bus]"]
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
    SYS_MOBILE["Cardholder mobile<br/>application"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
    OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
    SYS_IVR["IVR and self-service voice"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
    TS_AZURE_SERVICEBUS[/"Azure Service Bus<br/>[Message queue]"/]
    TS_AZURE_SQL[/"Azure SQL Database<br/>[Relational database]"/]
    TS_CARDSVC_BACKUP[/"Card Servicing Backup and<br/>recovery<br/>[Azure Backup]"/]
    TS_CARDSVC_CACHE[/"Card Servicing Cache<br/>[Azure Cache for Redis]"/]
    TS_CARDSVC_DNS[/"Card Servicing DNS<br/>[Azure DNS]"/]
    TS_CARDSVC_WAF[/"Card Servicing Web<br/>application firewall<br/>[Azure WAF]"/]
    TS_IDENTITY_DNS[/"Customer Identity Service<br/>DNS<br/>[Azure DNS]"/]
    TS_IDENTITY_WAF[/"Customer Identity Service<br/>Web application firewall<br/>[Azure WAF]"/]
    TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
    TS_ONPREM_DC[/"Primary Data Center<br/>[Virtual network]"/]
  end

  SYS_MOBILE --> OI_CARDSVC_API
  SYS_IVR --> OI_CARDSVC_API
  SYS_CARDSVC_API --> OI_IDENTITY_API
  SYS_CARDSVC_API --> OI_LEDGER_QUEUE
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
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_DNS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_WAF
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_APIM
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_AKS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_CORE_LEDGER -.->|"runs on"| TS_ONPREM_DC
  SYS_CARDSVC_API -->|"ReadWrite"| DA_CARDSVC_OPERATIONAL
  SYS_CARDSVC_STORE -->|"ReadWrite"| DA_CARDSVC_OPERATIONAL
  SYS_CORE_LEDGER -->|"Read"| DA_PAYMENT_INSTR
  SYS_MOBILE -->|"Read"| DA_CARD_ACCOUNT
  SYS_MOBILE -->|"Read"| DA_TRANSACTION
  SYS_IVR -->|"Read"| DA_CARD_ACCOUNT
  SYS_CARDSVC_API -->|"Read"| DA_CARD_ACCOUNT
  SYS_CARDSVC_API -->|"Read"| DA_TRANSACTION
  SYS_CORE_LEDGER -->|"ReadWrite"| DA_CARD_ACCOUNT
  OI_CARDSVC_API --- SYS_CARDSVC_API
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_CARD_ACCOUNT,DA_CARDSVC_OPERATIONAL,DA_PAYMENT_INSTR,DA_TRANSACTION s_data_assets__data_assets;
  class OI_CARDSVC_API,OI_IDENTITY_API,OI_LEDGER_QUEUE s_offered_interfaces__offered_interfaces;
  class SYS_CARDSVC_API,SYS_CARDSVC_EVENTS,SYS_CARDSVC_STORE,SYS_CARDSVC_WEB,SYS_CORE_LEDGER,SYS_IDENTITY_SVC,SYS_IVR,SYS_MOBILE s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_AZURE_SERVICEBUS,TS_AZURE_SQL,TS_CARDSVC_BACKUP,TS_CARDSVC_CACHE,TS_CARDSVC_DNS,TS_CARDSVC_WAF,TS_ENTRA_ID,TS_IDENTITY_DNS,TS_IDENTITY_WAF,TS_ONPREM_DC s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card Servicing Service — Architecture](../svg/system-architecture--sys-cardsvc-api.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |
| `#c2410c` | tech services |

29 entities, 38 relationships. Generated from the model; edit the model, not this file.
