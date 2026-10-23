# Installment Lending Service — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Installment Lending Service — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CARD_ACCOUNT[("Card account master")]
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
    DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
    DA_PAYMENT_INSTR[("Payment instructions")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
    OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
    SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
    OI_LENDING_API("Installment Lending API<br/>[HTTPS]")
    SYS_LENDING_WORKER["Installment Lending Async<br/>Worker<br/>[EKS · MSK]"]
    SYS_LENDING_DB["Installment Lending<br/>Database<br/>[RDS]"]
    SYS_LENDING_BUCKET["Installment Lending Object<br/>Store<br/>[S3]"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
    SYS_LENDING_WEB["Installment Lending Web<br/>[EKS]"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
    TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
    TS_AWS_MSK[/"Amazon MSK<br/>[Event stream]"/]
    TS_AWS_RDS[/"Amazon RDS for PostgreSQL<br/>[Relational database]"/]
    TS_AWS_S3[/"Amazon S3<br/>[Object store]"/]
    TS_AWS_KMS[/"AWS KMS<br/>[Key management]"/]
    TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
    TS_AWS_SECRETS[/"AWS Secrets Manager<br/>[Secrets manager]"/]
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_IDENTITY_DNS[/"Customer Identity Service<br/>DNS<br/>[Azure DNS]"/]
    TS_IDENTITY_WAF[/"Customer Identity Service<br/>Web application firewall<br/>[Azure WAF]"/]
    TS_LENDING_BACKUP[/"Installment Lending Backup<br/>and recovery<br/>[AWS Backup]"/]
    TS_LENDING_CACHE[/"Installment Lending Cache<br/>[Amazon ElastiCache]"/]
    TS_NET_SUB_LEND_APP_A[/"Lending App Subnet A<br/>[Subnet]"/]
    TS_NET_SUB_LEND_APP_B[/"Lending App Subnet B<br/>[Subnet]"/]
    TS_NET_SUB_LEND_DATA_A[/"Lending Data Subnet A<br/>[Subnet]"/]
    TS_NET_SUB_LEND_DATA_B[/"Lending Data Subnet B<br/>[Subnet]"/]
    TS_ONPREM_DC[/"Primary Data Center<br/>[Virtual network]"/]
  end

  SYS_LENDING_API --> OI_LEDGER_QUEUE
  SYS_LENDING_API --> OI_IDENTITY_API
  SYS_LENDING_API -->|"HTTPS"| SYS_CREDIT_BUREAU
  SYS_LENDING_WEB --> OI_LENDING_API
  SYS_LENDING_API -->|"Kafka"| SYS_LENDING_WORKER
  SYS_LENDING_API -->|"PostgreSQL"| SYS_LENDING_DB
  SYS_LENDING_API -->|"HTTPS"| SYS_LENDING_BUCKET
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_DNS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_WAF
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_APIM
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_AKS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_LENDING_API -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_API -.->|"runs on"| TS_LENDING_CACHE
  SYS_LENDING_API -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_API -.->|"runs on"| TS_AWS_SECRETS
  SYS_LENDING_API -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_LENDING_WEB -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_WEB -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_WORKER -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_WORKER -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_WORKER -.->|"runs on"| TS_AWS_MSK
  SYS_LENDING_DB -.->|"runs on"| TS_AWS_RDS
  SYS_LENDING_DB -.->|"runs on"| TS_LENDING_BACKUP
  SYS_LENDING_DB -.->|"runs on"| TS_AWS_KMS
  SYS_LENDING_BUCKET -.->|"runs on"| TS_AWS_S3
  SYS_LENDING_BUCKET -.->|"runs on"| TS_AWS_KMS
  SYS_LENDING_WEB -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_WEB -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_LENDING_WORKER -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_WORKER -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_LENDING_DB -.->|"runs on"| TS_NET_SUB_LEND_DATA_A
  SYS_LENDING_DB -.->|"runs on"| TS_NET_SUB_LEND_DATA_B
  SYS_LENDING_BUCKET -.->|"runs on"| TS_NET_SUB_LEND_DATA_A
  SYS_CORE_LEDGER -.->|"runs on"| TS_ONPREM_DC
  SYS_LENDING_API -->|"ReadWrite"| DA_LENDING_OPERATIONAL
  SYS_LENDING_WORKER -->|"Read"| DA_LENDING_OPERATIONAL
  SYS_CORE_LEDGER -->|"Read"| DA_PAYMENT_INSTR
  SYS_CREDIT_BUREAU -->|"Read"| DA_BUREAU_FILE
  SYS_CORE_LEDGER -->|"ReadWrite"| DA_CARD_ACCOUNT
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER
  OI_LENDING_API --- SYS_LENDING_API

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_BUREAU_FILE,DA_CARD_ACCOUNT,DA_LENDING_OPERATIONAL,DA_PAYMENT_INSTR s_data_assets__data_assets;
  class OI_IDENTITY_API,OI_LEDGER_QUEUE,OI_LENDING_API s_offered_interfaces__offered_interfaces;
  class SYS_CORE_LEDGER,SYS_CREDIT_BUREAU,SYS_IDENTITY_SVC,SYS_LENDING_API,SYS_LENDING_BUCKET,SYS_LENDING_DB,SYS_LENDING_WEB,SYS_LENDING_WORKER s_systems__systems;
  class TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_KMS,TS_AWS_MSK,TS_AWS_PRIVATELINK,TS_AWS_RDS,TS_AWS_S3,TS_AWS_SECRETS,TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_IDENTITY_DNS,TS_IDENTITY_WAF,TS_LENDING_BACKUP,TS_LENDING_CACHE,TS_NET_SUB_LEND_APP_A,TS_NET_SUB_LEND_APP_B,TS_NET_SUB_LEND_DATA_A,TS_NET_SUB_LEND_DATA_B,TS_ONPREM_DC s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Installment Lending Service — Architecture](../svg/system-architecture--sys-lending-api.svg)

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
3. Installment Lending Web → Installment Lending Service (HTTPS)
4. Installment Lending Service → Customer Identity Service (HTTPS)
5. Installment Lending Service → Experian Credit Bureau (HTTPS)
6. Installment Lending Service → Installment Lending Database (PostgreSQL)
7. Installment Lending Service → Core Card Ledger (MQ)
8. Installment Lending Service → Installment Lending Async Worker (Kafka)

35 entities, 45 relationships. Generated from the model; edit the model, not this file.
