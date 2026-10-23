# Experian Credit Bureau — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Experian Credit Bureau — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
    DA_DISPUTE_CASE[("Dispute case file")]
    DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_BUREAU_GW["Credit bureau gateway"]
    SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
    TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
    TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
    TS_AWS_SECRETS[/"AWS Secrets Manager<br/>[Secrets manager]"/]
    TS_LENDING_CACHE[/"Installment Lending Cache<br/>[Amazon ElastiCache]"/]
    TS_NET_SUB_LEND_APP_A[/"Lending App Subnet A<br/>[Subnet]"/]
    TS_NET_SUB_LEND_APP_B[/"Lending App Subnet B<br/>[Subnet]"/]
  end

  SYS_BUREAU_GW -->|"FileTransfer"| SYS_CREDIT_BUREAU
  SYS_LENDING_API -->|"HTTPS"| SYS_CREDIT_BUREAU
  SYS_CREDIT_BUREAU -->|"HTTPS"| SYS_LENDING_HUB
  SYS_LENDING_API -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_API -.->|"runs on"| TS_LENDING_CACHE
  SYS_LENDING_API -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_API -.->|"runs on"| TS_AWS_SECRETS
  SYS_LENDING_API -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_LENDING_API -->|"ReadWrite"| DA_LENDING_OPERATIONAL
  SYS_BUREAU_GW -->|"ReadWrite"| DA_BUREAU_FILE
  SYS_BUREAU_GW -->|"Read"| DA_DISPUTE_CASE
  SYS_CREDIT_BUREAU -->|"Read"| DA_BUREAU_FILE

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_BUREAU_FILE,DA_DISPUTE_CASE,DA_LENDING_OPERATIONAL s_data_assets__data_assets;
  class SYS_BUREAU_GW,SYS_CREDIT_BUREAU,SYS_LENDING_API,SYS_LENDING_HUB s_systems__systems;
  class TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_PRIVATELINK,TS_AWS_SECRETS,TS_LENDING_CACHE,TS_NET_SUB_LEND_APP_A,TS_NET_SUB_LEND_APP_B s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Experian Credit Bureau — Architecture](../svg/system-architecture--sys-credit-bureau.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Installment Loan Application**: An applicant applies for point-of-sale credit. Bureau search, affordability and a decision, with referral to an underwriter when the automated decision declines to take it.

1. Installment Lending Edge → Installment Lending Load Balancer (HTTPS) — not on this diagram
2. Installment Lending Load Balancer → Installment Lending Web (HTTPS) — not on this diagram
3. Installment Lending Web → Installment Lending Service (HTTPS) — not on this diagram
4. Installment Lending Service → Customer Identity Service (HTTPS) — not on this diagram
5. Installment Lending Service → Experian Credit Bureau (HTTPS)
6. Installment Lending Service → Installment Lending Database (PostgreSQL) — not on this diagram
7. Installment Lending Service → Core Card Ledger (MQ) — not on this diagram
8. Installment Lending Service → Installment Lending Async Worker (Kafka) — not on this diagram

14 entities, 14 relationships. Generated from the model; edit the model, not this file.
