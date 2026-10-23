# Customer Identity Service — Onboarding

What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart TB
  %% Customer Identity Service — Onboarding
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_AWS["AWS"]
    direction TB
    subgraph grp_AWS__prod_lending["account prod-lending"]
      direction TB
      subgraph grp_AWS__prod_lending__eu_west_2["region eu-west-2"]
        direction TB
        subgraph grp_AWS__prod_lending__eu_west_2__Private_App["Private-App"]
          direction TB
          SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
        end
      end
    end
  end

  subgraph grp_Azure["Azure"]
    direction TB
    subgraph grp_Azure__azure_cards_prod["subscription azure-cards-prod"]
      direction TB
      subgraph grp_Azure__azure_cards_prod__uksouth["region uksouth"]
        direction TB
        subgraph grp_Azure__azure_cards_prod__uksouth__Private_App["Private-App"]
          direction TB
          SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
          SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
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
    subgraph grp_Azure__azure_risk_prod["subscription azure-risk-prod"]
      direction TB
      subgraph grp_Azure__azure_risk_prod__uksouth["region uksouth"]
        direction TB
        subgraph grp_Azure__azure_risk_prod__uksouth__Public["Public"]
          direction TB
          SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
        end
        subgraph grp_Azure__azure_risk_prod__uksouth__Private_App["Private-App"]
          direction TB
          SYS_IDV_GATEWAY["Identity Document<br/>Verification Integration<br/>Gateway<br/>[AKS]"]
        end
      end
    end
  end

  SYS_CARDSVC_API --> OI_IDENTITY_API
  SYS_COLLECT_API --> OI_IDENTITY_API
  SYS_LENDING_API --> OI_IDENTITY_API
  SYS_IDENTITY_SVC -->|"HTTPS"| SYS_IDV_GATEWAY
  SYS_IDV_WEBHOOKS -->|"HTTPS"| SYS_IDENTITY_SVC
  OI_IDENTITY_API --- SYS_IDENTITY_SVC

  classDef s_offered_interfaces__shared_services fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_app fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__public fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__shared_services fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class OI_IDENTITY_API s_offered_interfaces__shared_services;
  class SYS_CARDSVC_API,SYS_COLLECT_API,SYS_IDV_GATEWAY,SYS_LENDING_API s_systems__private_app;
  class SYS_IDV_WEBHOOKS s_systems__public;
  class SYS_IDENTITY_SVC s_systems__shared_services;
  classDef boundary1 fill:#eef5fb,stroke:#147eba,color:#0f5f8c;
  class grp_AWS__prod_lending__eu_west_2__Private_App boundary1;
  classDef boundary2 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_cards_prod__uksouth__Private_App,grp_Azure__azure_platform_prod__uksouth__Shared_Services,grp_Azure__azure_risk_prod__uksouth__Public,grp_Azure__azure_risk_prod__uksouth__Private_App boundary2;
  classDef boundary3 fill:#f5fbfb,stroke:#00a4a6,color:#0b6e70,stroke-dasharray:6 3;
  class grp_AWS__prod_lending__eu_west_2 boundary3;
  classDef boundary4 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_cards_prod,grp_Azure__azure_platform_prod,grp_Azure__azure_risk_prod boundary4;
  classDef boundary5 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary5;
  classDef boundary6 fill:#f8fafc,stroke:#7a8699,color:#4b5563,stroke-dasharray:2 3;
  class grp_Azure__azure_cards_prod__uksouth,grp_Azure__azure_platform_prod__uksouth,grp_Azure__azure_risk_prod__uksouth boundary6;
  classDef boundary7 fill:#fbfcfd,stroke:#232f3e,color:#232f3e;
  class grp_AWS boundary7;
  classDef boundary8 fill:#fdf6fa,stroke:#c7257e,color:#8b1a58;
  class grp_AWS__prod_lending boundary8;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Customer Identity Service — Onboarding](../svg/onboarding--prd-identity.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |

**network zone** is the boundary each node sits in.

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#232f3e` | AWS |
| solid `#0078d4` | Azure |
| solid `#c7257e` | AWS account |
| dashed `#0078d4` | Azure subscription |
| dashed `#00a4a6` | AWS region |
| dotted `#7a8699` | Azure region |
| solid `#147eba` | private subnet |
| solid `#5b9bd5` | Azure subnet |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Installment Loan Application**: An applicant applies for point-of-sale credit. Bureau search, affordability and a decision, with referral to an underwriter when the automated decision declines to take it.

1. Installment Lending Edge → Installment Lending Load Balancer (HTTPS) — not on this diagram
2. Installment Lending Load Balancer → Installment Lending Web (HTTPS) — not on this diagram
3. Installment Lending Web → Installment Lending Service (HTTPS) — not on this diagram
4. Installment Lending Service → Customer Identity Service (HTTPS)
5. Installment Lending Service → Experian Credit Bureau (HTTPS) — not on this diagram
6. Installment Lending Service → Installment Lending Database (PostgreSQL) — not on this diagram
7. Installment Lending Service → Core Card Ledger (MQ) — not on this diagram
8. Installment Lending Service → Installment Lending Async Worker (Kafka) — not on this diagram

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
