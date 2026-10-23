# Customer Identity Service — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Customer Identity Service — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CARD_ACCOUNT[("Card account master")]
    DA_CARDSVC_OPERATIONAL[("Card Servicing operational<br/>data")]
    DA_TRANSACTION[("Card transaction history")]
    DA_COLLECT_ACT[("Collections activity<br/>record")]
    DA_COLLECT_OPERATIONAL[("Collections Workspace<br/>operational data")]
    DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
    SYS_IDV_GATEWAY["Identity Document<br/>Verification Integration<br/>Gateway<br/>[AKS]"]
    SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
    TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
    TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
    TS_AWS_SECRETS[/"AWS Secrets Manager<br/>[Secrets manager]"/]
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_MONITOR[/"Azure Monitor<br/>[Observability]"/]
    TS_CARDSVC_CACHE[/"Card Servicing Cache<br/>[Azure Cache for Redis]"/]
    TS_COLLECT_CACHE[/"Collections Workspace<br/>Cache<br/>[Azure Cache for Redis]"/]
    TS_IDENTITY_DNS[/"Customer Identity Service<br/>DNS<br/>[Azure DNS]"/]
    TS_IDENTITY_WAF[/"Customer Identity Service<br/>Web application firewall<br/>[Azure WAF]"/]
    TS_LENDING_CACHE[/"Installment Lending Cache<br/>[Amazon ElastiCache]"/]
    TS_NET_SUB_LEND_APP_A[/"Lending App Subnet A<br/>[Subnet]"/]
    TS_NET_SUB_LEND_APP_B[/"Lending App Subnet B<br/>[Subnet]"/]
  end

  SYS_CARDSVC_API --> OI_IDENTITY_API
  SYS_COLLECT_API --> OI_IDENTITY_API
  SYS_LENDING_API --> OI_IDENTITY_API
  SYS_IDENTITY_SVC -->|"HTTPS"| SYS_IDV_GATEWAY
  SYS_IDV_WEBHOOKS -->|"HTTPS"| SYS_IDENTITY_SVC
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_APIM
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_AKS
  SYS_CARDSVC_API -.->|"runs on"| TS_CARDSVC_CACHE
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_MONITOR
  SYS_CARDSVC_API -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_APIM
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_AKS
  SYS_COLLECT_API -.->|"runs on"| TS_COLLECT_CACHE
  SYS_COLLECT_API -.->|"runs on"| TS_AZURE_MONITOR
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
  SYS_LENDING_API -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_API -.->|"runs on"| TS_LENDING_CACHE
  SYS_LENDING_API -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_API -.->|"runs on"| TS_AWS_SECRETS
  SYS_LENDING_API -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_CARDSVC_API -->|"ReadWrite"| DA_CARDSVC_OPERATIONAL
  SYS_COLLECT_API -->|"ReadWrite"| DA_COLLECT_OPERATIONAL
  SYS_LENDING_API -->|"ReadWrite"| DA_LENDING_OPERATIONAL
  SYS_COLLECT_API -->|"ReadWrite"| DA_COLLECT_ACT
  SYS_CARDSVC_API -->|"Read"| DA_CARD_ACCOUNT
  SYS_CARDSVC_API -->|"Read"| DA_TRANSACTION
  SYS_COLLECT_API -->|"Read"| DA_CARD_ACCOUNT
  OI_IDENTITY_API --- SYS_IDENTITY_SVC

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_CARD_ACCOUNT,DA_CARDSVC_OPERATIONAL,DA_COLLECT_ACT,DA_COLLECT_OPERATIONAL,DA_LENDING_OPERATIONAL,DA_TRANSACTION s_data_assets__data_assets;
  class OI_IDENTITY_API s_offered_interfaces__offered_interfaces;
  class SYS_CARDSVC_API,SYS_COLLECT_API,SYS_IDENTITY_SVC,SYS_IDV_GATEWAY,SYS_IDV_WEBHOOKS,SYS_LENDING_API s_systems__systems;
  class TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_PRIVATELINK,TS_AWS_SECRETS,TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_MONITOR,TS_CARDSVC_CACHE,TS_COLLECT_CACHE,TS_IDENTITY_DNS,TS_IDENTITY_WAF,TS_LENDING_CACHE,TS_NET_SUB_LEND_APP_A,TS_NET_SUB_LEND_APP_B s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Customer Identity Service — Architecture](../svg/system-architecture--sys-identity-svc.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |
| `#c2410c` | tech services |

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

28 entities, 40 relationships. Generated from the model; edit the model, not this file.
