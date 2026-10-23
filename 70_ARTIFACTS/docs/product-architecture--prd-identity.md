# Customer Identity Service — Architecture

One product in full: the systems it is made of, what each runs on, the data it masters, who uses it, and everything one hop away that it connects to. For a product built from modules, every box corresponds to a part.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Customer Identity Service — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_AWS["AWS"]
    direction LR
    subgraph grp_AWS__prod_lending["account prod-lending"]
      direction LR
      subgraph grp_AWS__prod_lending__Private_App["Private-App"]
        direction LR
        SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
      end
    end
  end

  subgraph grp_Azure["Azure"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    subgraph grp_Azure__azure_cards_prod["subscription azure-cards-prod"]
      direction LR
      subgraph grp_Azure__azure_cards_prod__Private_App["Private-App"]
        direction LR
        SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
        SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
      end
    end
    subgraph grp_Azure__azure_platform_prod["subscription azure-platform-prod"]
      direction LR
      subgraph grp_Azure__azure_platform_prod__Edge["Edge"]
        direction LR
        TS_IDENTITY_DNS[/"Customer Identity Service<br/>DNS<br/>[Azure DNS]"/]
        TS_IDENTITY_WAF[/"Customer Identity Service<br/>Web application firewall<br/>[Azure WAF]"/]
      end
      subgraph grp_Azure__azure_platform_prod__Shared_Services["Shared-Services"]
        direction LR
        OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
        SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
      end
    end
    subgraph grp_Azure__azure_risk_prod["subscription azure-risk-prod"]
      direction LR
      subgraph grp_Azure__azure_risk_prod__Public["Public"]
        direction LR
        SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
      end
      subgraph grp_Azure__azure_risk_prod__Private_App["Private-App"]
        direction LR
        SYS_IDV_GATEWAY["Identity Document<br/>Verification Integration<br/>Gateway<br/>[AKS]"]
      end
    end
  end

  SYS_CARDSVC_API --> OI_IDENTITY_API
  SYS_COLLECT_API --> OI_IDENTITY_API
  SYS_LENDING_API --> OI_IDENTITY_API
  SYS_IDENTITY_SVC -->|"HTTPS"| SYS_IDV_GATEWAY
  SYS_IDV_WEBHOOKS -->|"HTTPS"| SYS_IDENTITY_SVC
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_APIM
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_AKS
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_APIM
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_AKS
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_DNS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_WAF
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_APIM
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_AKS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_AKS
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_APIM
  SYS_IDV_WEBHOOKS -.->|"runs on"| TS_AZURE_APIM
  SYS_IDV_WEBHOOKS -.->|"runs on"| TS_AZURE_AKS
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_KEYVAULT
  OI_IDENTITY_API --- SYS_IDENTITY_SVC

  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class OI_IDENTITY_API s_offered_interfaces__offered_interfaces;
  class SYS_CARDSVC_API,SYS_COLLECT_API,SYS_IDENTITY_SVC,SYS_IDV_GATEWAY,SYS_IDV_WEBHOOKS,SYS_LENDING_API s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_IDENTITY_DNS,TS_IDENTITY_WAF s_tech_services__tech_services;
  classDef boundary1 fill:#eef5fb,stroke:#147eba,color:#0f5f8c;
  class grp_AWS__prod_lending__Private_App boundary1;
  classDef boundary2 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_cards_prod__Private_App,grp_Azure__azure_platform_prod__Edge,grp_Azure__azure_platform_prod__Shared_Services,grp_Azure__azure_risk_prod__Public,grp_Azure__azure_risk_prod__Private_App boundary2;
  classDef boundary3 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_cards_prod,grp_Azure__azure_platform_prod,grp_Azure__azure_risk_prod boundary3;
  classDef boundary4 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary4;
  classDef boundary5 fill:#fbfcfd,stroke:#232f3e,color:#232f3e;
  class grp_AWS boundary5;
  classDef boundary6 fill:#fdf6fa,stroke:#c7257e,color:#8b1a58;
  class grp_AWS__prod_lending boundary6;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Customer Identity Service — Architecture](../svg/product-architecture--prd-identity.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |
| `#c2410c` | tech services |

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#232f3e` | AWS |
| solid `#0078d4` | Azure |
| solid `#c7257e` | AWS account |
| dashed `#0078d4` | Azure subscription |
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

12 entities, 22 relationships. Generated from the model; edit the model, not this file.
