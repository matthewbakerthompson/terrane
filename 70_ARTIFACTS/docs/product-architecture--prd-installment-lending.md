# Installment Lending — Architecture

One product in full: the systems it is made of, what each runs on, the data it masters, who uses it, and everything one hop away that it connects to. For a product built from modules, every box corresponds to a part.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Installment Lending — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_AWS["AWS"]
    direction LR
    subgraph grp_AWS__Edge["Edge"]
      direction LR
      TS_AWS_CLOUDFRONT[/"Amazon CloudFront and WAF<br/>[Content delivery network]"/]
    end
    subgraph grp_AWS__prod_lending["account prod-lending"]
      direction LR
      subgraph grp_AWS__prod_lending__Edge["Edge"]
        direction LR
        TS_LENDING_DNS[/"Installment Lending DNS<br/>[Amazon Route 53]"/]
        SYS_LENDING_EDGE["Installment Lending Edge"]
        TS_LENDING_WAF[/"Installment Lending Web<br/>application firewall<br/>[AWS WAF]"/]
      end
      subgraph grp_AWS__prod_lending__Public["Public"]
        direction LR
        SYS_LENDING_ALB["Installment Lending Load<br/>Balancer"]
        TS_NET_SUB_LEND_PUB_A[/"Lending Public Subnet A<br/>[Subnet]"/]
        TS_NET_SUB_LEND_PUB_B[/"Lending Public Subnet B<br/>[Subnet]"/]
      end
      subgraph grp_AWS__prod_lending__Private_App["Private-App"]
        direction LR
        OI_LENDING_API("Installment Lending API<br/>[HTTPS]")
        SYS_LENDING_WORKER["Installment Lending Async<br/>Worker<br/>[EKS · MSK]"]
        TS_LENDING_CACHE[/"Installment Lending Cache<br/>[Amazon ElastiCache]"/]
        SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
        SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
        SYS_LENDING_WEB["Installment Lending Web<br/>[EKS]"]
        TS_NET_SUB_LEND_APP_A[/"Lending App Subnet A<br/>[Subnet]"/]
        TS_NET_SUB_LEND_APP_B[/"Lending App Subnet B<br/>[Subnet]"/]
      end
      subgraph grp_AWS__prod_lending__Private_Data["Private-Data"]
        direction LR
        TS_LENDING_BACKUP[/"Installment Lending Backup<br/>and recovery<br/>[AWS Backup]"/]
        SYS_LENDING_DB["Installment Lending<br/>Database<br/>[RDS]"]
        SYS_LENDING_BUCKET["Installment Lending Object<br/>Store<br/>[S3]"]
        TS_NET_SUB_LEND_DATA_A[/"Lending Data Subnet A<br/>[Subnet]"/]
        TS_NET_SUB_LEND_DATA_B[/"Lending Data Subnet B<br/>[Subnet]"/]
      end
    end
    subgraph grp_AWS__shared_management["account shared-management"]
      direction LR
      subgraph grp_AWS__shared_management__Shared_Services["Shared-Services"]
        direction LR
        TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
      end
    end
    subgraph grp_AWS__shared_network["account shared-network"]
      direction LR
      subgraph grp_AWS__shared_network__Shared_Services["Shared-Services"]
        direction LR
        TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
      end
    end
    subgraph grp_AWS__Public["Public"]
      direction LR
      TS_AWS_ALB[/"Application Load Balancer<br/>[Load balancer]"/]
    end
    subgraph grp_AWS__Private_App["Private-App"]
      direction LR
      TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
      TS_AWS_MSK[/"Amazon MSK<br/>[Event stream]"/]
    end
    subgraph grp_AWS__Private_Data["Private-Data"]
      direction LR
      TS_AWS_RDS[/"Amazon RDS for PostgreSQL<br/>[Relational database]"/]
      TS_AWS_S3[/"Amazon S3<br/>[Object store]"/]
    end
    subgraph grp_AWS__Shared_Services["Shared-Services"]
      direction LR
      TS_AWS_KMS[/"AWS KMS<br/>[Key management]"/]
      TS_AWS_SECRETS[/"AWS Secrets Manager<br/>[Secrets manager]"/]
    end
  end

  subgraph grp_Azure["Azure"]
    direction LR
    subgraph grp_Azure__azure_data_prod["subscription azure-data-prod"]
      direction LR
      subgraph grp_Azure__azure_data_prod__Private_Data["Private-Data"]
        direction LR
        SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
      end
    end
    subgraph grp_Azure__azure_platform_prod["subscription azure-platform-prod"]
      direction LR
      subgraph grp_Azure__azure_platform_prod__Shared_Services["Shared-Services"]
        direction LR
        OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
        SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
      end
    end
  end

  subgraph grp_On_prem["On-prem"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
  end

  subgraph grp_SaaS["SaaS"]
    direction LR
    subgraph grp_SaaS__Edge["Edge"]
      direction LR
      SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
      SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
    end
  end

  ACT_UNDERWRITER(["Credit Underwriter"])
  DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
  ACT_APPLICANT(["Loan Applicant"])

  SYS_CRM -->|"HTTPS"| SYS_CORE_LEDGER
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_LENDING_API --> OI_LEDGER_QUEUE
  SYS_LENDING_API --> OI_IDENTITY_API
  SYS_LENDING_WORKER -->|"S3"| SYS_DATA_INGEST
  SYS_LENDING_API -->|"HTTPS"| SYS_CREDIT_BUREAU
  SYS_LENDING_WEB --> OI_LENDING_API
  SYS_LENDING_EDGE -->|"HTTPS"| SYS_LENDING_ALB
  SYS_LENDING_ALB -->|"HTTPS"| SYS_LENDING_WEB
  SYS_LENDING_API -->|"Kafka"| SYS_LENDING_WORKER
  SYS_LENDING_API -->|"PostgreSQL"| SYS_LENDING_DB
  SYS_LENDING_API -->|"HTTPS"| SYS_LENDING_BUCKET
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CREDIT_BUREAU -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CRM -->|"HTTPS"| SYS_LENDING_HUB
  SYS_LENDING_API -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_API -.->|"runs on"| TS_LENDING_CACHE
  SYS_LENDING_API -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_API -.->|"runs on"| TS_AWS_SECRETS
  SYS_LENDING_API -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_LENDING_WEB -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_WEB -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_EDGE -.->|"runs on"| TS_AWS_CLOUDFRONT
  SYS_LENDING_EDGE -.->|"runs on"| TS_LENDING_WAF
  SYS_LENDING_EDGE -.->|"runs on"| TS_LENDING_DNS
  SYS_LENDING_ALB -.->|"runs on"| TS_AWS_ALB
  SYS_LENDING_WORKER -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_WORKER -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_WORKER -.->|"runs on"| TS_AWS_MSK
  SYS_LENDING_DB -.->|"runs on"| TS_AWS_RDS
  SYS_LENDING_DB -.->|"runs on"| TS_LENDING_BACKUP
  SYS_LENDING_DB -.->|"runs on"| TS_AWS_KMS
  SYS_LENDING_BUCKET -.->|"runs on"| TS_AWS_S3
  SYS_LENDING_BUCKET -.->|"runs on"| TS_AWS_KMS
  SYS_LENDING_ALB -.->|"runs on"| TS_NET_SUB_LEND_PUB_A
  SYS_LENDING_ALB -.->|"runs on"| TS_NET_SUB_LEND_PUB_B
  SYS_LENDING_WEB -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_WEB -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_LENDING_WORKER -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_WORKER -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_LENDING_DB -.->|"runs on"| TS_NET_SUB_LEND_DATA_A
  SYS_LENDING_DB -.->|"runs on"| TS_NET_SUB_LEND_DATA_B
  SYS_LENDING_BUCKET -.->|"runs on"| TS_NET_SUB_LEND_DATA_A
  SYS_LENDING_API -->|"ReadWrite"| DA_LENDING_OPERATIONAL
  SYS_LENDING_WORKER -->|"Read"| DA_LENDING_OPERATIONAL
  ACT_APPLICANT -->|"Applies"| SYS_LENDING_WEB
  ACT_UNDERWRITER -->|"Reviews referrals"| SYS_LENDING_WEB
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER
  OI_LENDING_API --- SYS_LENDING_API

  classDef s_actors__actors fill:#fde68a,stroke:#b45309,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class ACT_APPLICANT,ACT_UNDERWRITER s_actors__actors;
  class DA_LENDING_OPERATIONAL s_data_assets__data_assets;
  class OI_IDENTITY_API,OI_LEDGER_QUEUE,OI_LENDING_API s_offered_interfaces__offered_interfaces;
  class SYS_CORE_LEDGER,SYS_CREDIT_BUREAU,SYS_CRM,SYS_DATA_INGEST,SYS_IDENTITY_SVC,SYS_LENDING_ALB,SYS_LENDING_API,SYS_LENDING_BUCKET,SYS_LENDING_DB,SYS_LENDING_EDGE,SYS_LENDING_HUB,SYS_LENDING_WEB,SYS_LENDING_WORKER s_systems__systems;
  class TS_AWS_ALB,TS_AWS_CLOUDFRONT,TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_KMS,TS_AWS_MSK,TS_AWS_PRIVATELINK,TS_AWS_RDS,TS_AWS_S3,TS_AWS_SECRETS,TS_LENDING_BACKUP,TS_LENDING_CACHE,TS_LENDING_DNS,TS_LENDING_WAF,TS_NET_SUB_LEND_APP_A,TS_NET_SUB_LEND_APP_B,TS_NET_SUB_LEND_DATA_A,TS_NET_SUB_LEND_DATA_B,TS_NET_SUB_LEND_PUB_A,TS_NET_SUB_LEND_PUB_B s_tech_services__tech_services;
  classDef boundary1 fill:#eef5fb,stroke:#147eba,color:#0f5f8c;
  class grp_AWS__Private_App,grp_AWS__Private_Data,grp_AWS__prod_lending__Private_App,grp_AWS__prod_lending__Private_Data boundary1;
  classDef boundary2 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_data_prod__Private_Data,grp_Azure__azure_platform_prod__Shared_Services boundary2;
  classDef boundary3 fill:#f3f7e9,stroke:#7aa116,color:#4f6a0e;
  class grp_AWS__Edge,grp_AWS__Public,grp_AWS__prod_lending__Edge,grp_AWS__prod_lending__Public boundary3;
  classDef boundary4 fill:#f4f0ff,stroke:#8c4fff,color:#5b2fb0;
  class grp_AWS__Shared_Services,grp_AWS__shared_management__Shared_Services,grp_AWS__shared_network__Shared_Services boundary4;
  classDef boundary5 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary5;
  classDef boundary6 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_data_prod,grp_Azure__azure_platform_prod boundary6;
  classDef boundary7 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary7;
  classDef boundary8 fill:#fbfcfd,stroke:#232f3e,color:#232f3e;
  class grp_AWS boundary8;
  classDef boundary9 fill:#fcfbf7,stroke:#9a8f6a,color:#6b6246,stroke-dasharray:6 3;
  class grp_SaaS,grp_SaaS__Edge boundary9;
  classDef boundary10 fill:#fdf6fa,stroke:#c7257e,color:#8b1a58;
  class grp_AWS__prod_lending,grp_AWS__shared_management,grp_AWS__shared_network boundary10;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Installment Lending — Architecture](../svg/product-architecture--prd-installment-lending.svg)

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
| solid `#232f3e` | AWS |
| solid `#0078d4` | Azure |
| solid `#5f6b7a` | On-prem |
| dashed `#9a8f6a` | SaaS |
| solid `#7aa116` | public subnet |
| solid `#c7257e` | AWS account |
| solid `#147eba` | private subnet |
| solid `#8c4fff` | shared services |
| dashed `#0078d4` | Azure subscription |
| dashed `#9a8f6a` | vendor tenancy |
| solid `#5b9bd5` | Azure subnet |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Installment Loan Application**: An applicant applies for point-of-sale credit. Bureau search, affordability and a decision, with referral to an underwriter when the automated decision declines to take it.

1. Installment Lending Edge → Installment Lending Load Balancer (HTTPS)
2. Installment Lending Load Balancer → Installment Lending Web (HTTPS)
3. Installment Lending Web → Installment Lending Service (HTTPS)
4. Installment Lending Service → Customer Identity Service (HTTPS)
5. Installment Lending Service → Experian Credit Bureau (HTTPS)
6. Installment Lending Service → Installment Lending Database (PostgreSQL)
7. Installment Lending Service → Core Card Ledger (MQ)
8. Installment Lending Service → Installment Lending Async Worker (Kafka)

**Dispute and Chargeback**: A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

1. Dynamics 365 Customer Service → Core Card Ledger (HTTPS)
2. Core Card Ledger → Dispute Management Platform Integration Gateway (HTTPS) — not on this diagram
3. Dispute Management Platform Integration Gateway → Pega Smart Dispute (HTTPS) — not on this diagram
4. Pega Smart Dispute → Enterprise Data Ingestion Hub (SFTP) — not on this diagram

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL) — not on this diagram
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

39 entities, 52 relationships. Generated from the model; edit the model, not this file.
