# Merchant Portal — Onboarding

What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart TB
  %% Merchant Portal — Onboarding
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Azure["Azure"]
    direction TB
    subgraph grp_Azure__azure_payments_prod["subscription azure-payments-prod"]
      direction TB
      subgraph grp_Azure__azure_payments_prod__uksouth["region uksouth"]
        direction TB
        SYS_MERCHANT_EVENTS["Merchant Portal Event<br/>Publisher<br/>[Service Bus]"]
        subgraph grp_Azure__azure_payments_prod__uksouth__Private_App["Private-App"]
          direction TB
          OI_MERCHANT_API("Merchant Portal API<br/>[HTTPS]")
          SYS_MERCHANT_API["Merchant Portal Service<br/>[AKS · Merchant Portal Cache]"]
          SYS_MERCHANT_WEB["Merchant Portal Web<br/>[AKS]"]
        end
        subgraph grp_Azure__azure_payments_prod__uksouth__Private_Data["Private-Data"]
          direction TB
          SYS_MERCHANT_STORE["Merchant Portal Database<br/>[Azure SQL]"]
        end
      end
    end
  end

  SYS_MERCHANT_WEB --> OI_MERCHANT_API
  SYS_MERCHANT_API -->|"TDS"| SYS_MERCHANT_STORE
  SYS_MERCHANT_API -->|"AMQP"| SYS_MERCHANT_EVENTS
  OI_MERCHANT_API --- SYS_MERCHANT_API

  classDef s_offered_interfaces__private_app fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_app fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_data fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class OI_MERCHANT_API s_offered_interfaces__private_app;
  class SYS_MERCHANT_EVENTS s_systems__default;
  class SYS_MERCHANT_API,SYS_MERCHANT_WEB s_systems__private_app;
  class SYS_MERCHANT_STORE s_systems__private_data;
  classDef boundary1 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_payments_prod__uksouth__Private_App,grp_Azure__azure_payments_prod__uksouth__Private_Data boundary1;
  classDef boundary2 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_payments_prod boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary3;
  classDef boundary4 fill:#f8fafc,stroke:#7a8699,color:#4b5563,stroke-dasharray:2 3;
  class grp_Azure__azure_payments_prod__uksouth boundary4;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Merchant Portal — Onboarding](../svg/onboarding--prd-merchant-portal.svg)

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
| dashed `#0078d4` | Azure subscription |
| dotted `#7a8699` | Azure region |
| solid `#5b9bd5` | Azure subnet |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
