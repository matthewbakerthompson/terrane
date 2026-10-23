# Card Servicing — Onboarding

What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart TB
  %% Card Servicing — Onboarding
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction TB
    subgraph grp_Azure__azure_cards_prod["subscription azure-cards-prod"]
      direction TB
      subgraph grp_Azure__azure_cards_prod__uksouth["region uksouth"]
        direction TB
        SYS_CARDSVC_EVENTS["Card Servicing Event<br/>Publisher<br/>[Service Bus]"]
        subgraph grp_Azure__azure_cards_prod__uksouth__Private_App["Private-App"]
          direction TB
          OI_CARDSVC_API("Card Servicing API<br/>[HTTPS]")
          SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
          SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
        end
        subgraph grp_Azure__azure_cards_prod__uksouth__Private_Data["Private-Data"]
          direction TB
          SYS_CARDSVC_STORE["Card Servicing Datastore<br/>[Azure SQL]"]
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
    subgraph grp_Azure__azure_platform_prod["subscription azure-platform-prod"]
      direction TB
      subgraph grp_Azure__azure_platform_prod__uksouth["region uksouth"]
        direction TB
        subgraph grp_Azure__azure_platform_prod__uksouth__Shared_Services["Shared-Services"]
          direction TB
          OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
          SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
        end
      end
    end
  end

  subgraph grp_On_prem["On-prem"]
    direction TB
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
  end

  SYS_MOBILE["Cardholder mobile<br/>application"]
  SYS_IVR["IVR and self-service voice"]

  SYS_MOBILE --> OI_CARDSVC_API
  SYS_IVR --> OI_CARDSVC_API
  SYS_CARDSVC_API --> OI_IDENTITY_API
  SYS_CARDSVC_API --> OI_LEDGER_QUEUE
  SYS_CARDSVC_EVENTS -->|"AMQP"| SYS_DATA_INGEST
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_CARDSVC_WEB --> OI_CARDSVC_API
  SYS_CARDSVC_API -->|"TDS"| SYS_CARDSVC_STORE
  SYS_CARDSVC_API -->|"AMQP"| SYS_CARDSVC_EVENTS
  OI_CARDSVC_API --- SYS_CARDSVC_API
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER

  classDef s_offered_interfaces__on_prem fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__private_app fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__shared_services fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__on_prem fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_app fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_data fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__shared_services fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class OI_LEDGER_QUEUE s_offered_interfaces__on_prem;
  class OI_CARDSVC_API s_offered_interfaces__private_app;
  class OI_IDENTITY_API s_offered_interfaces__shared_services;
  class SYS_CARDSVC_EVENTS,SYS_IVR,SYS_MOBILE s_systems__default;
  class SYS_CORE_LEDGER s_systems__on_prem;
  class SYS_CARDSVC_API,SYS_CARDSVC_WEB s_systems__private_app;
  class SYS_CARDSVC_STORE,SYS_DATA_INGEST s_systems__private_data;
  class SYS_IDENTITY_SVC s_systems__shared_services;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_cards_prod__uksouth__Private_App,grp_Azure__azure_cards_prod__uksouth__Private_Data,grp_Azure__azure_data_prod__uksouth__Private_Data,grp_Azure__azure_platform_prod__uksouth__Shared_Services boundary1;
  classDef boundary2 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_cards_prod,grp_Azure__azure_data_prod,grp_Azure__azure_platform_prod boundary3;
  classDef boundary4 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary4;
  classDef boundary5 fill:#f8fafc,stroke:#7a8699,color:#4b5563,stroke-dasharray:2 3;
  class grp_Azure__azure_cards_prod__uksouth,grp_Azure__azure_data_prod__uksouth,grp_Azure__azure_platform_prod__uksouth boundary5;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card Servicing — Onboarding](../svg/onboarding--prd-card-servicing.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |

**network zone** is the boundary each node sits in.

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#0078d4` | Azure |
| solid `#5f6b7a` | On-prem |
| dashed `#0078d4` | Azure subscription |
| dotted `#7a8699` | Azure region |
| solid `#5b9bd5` | Azure subnet |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL) — not on this diagram
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

12 entities, 12 relationships. Generated from the model; edit the model, not this file.
