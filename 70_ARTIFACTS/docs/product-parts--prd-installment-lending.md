# Installment Lending — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Installment Lending — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_api_service["api-service"]
    direction LR
    OI_LENDING_API("Installment Lending API<br/>[HTTPS]")
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
  end

  subgraph grp_async_worker["async-worker"]
    direction LR
    SYS_LENDING_WORKER["Installment Lending Async<br/>Worker<br/>[EKS · MSK]"]
  end

  subgraph grp_integration_hub["integration-hub"]
    direction LR
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
  end

  subgraph grp_object_store["object-store"]
    direction LR
    SYS_LENDING_BUCKET["Installment Lending Object<br/>Store<br/>[S3]"]
  end

  subgraph grp_public_web_entry["public-web-entry"]
    direction LR
    SYS_LENDING_EDGE["Installment Lending Edge"]
    SYS_LENDING_ALB["Installment Lending Load<br/>Balancer"]
  end

  subgraph grp_relational_datastore["relational-datastore"]
    direction LR
    SYS_LENDING_DB["Installment Lending<br/>Database<br/>[RDS]"]
    DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
  end

  subgraph grp_web_channel["web-channel"]
    direction LR
    SYS_LENDING_WEB["Installment Lending Web<br/>[EKS]"]
  end

  TS_AWS_CLOUDFRONT[/"Amazon CloudFront and WAF<br/>[Content delivery network]"/]
  TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
  TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
  TS_AWS_MSK[/"Amazon MSK<br/>[Event stream]"/]
  TS_AWS_RDS[/"Amazon RDS for PostgreSQL<br/>[Relational database]"/]
  TS_AWS_S3[/"Amazon S3<br/>[Object store]"/]
  TS_AWS_ALB[/"Application Load Balancer<br/>[Load balancer]"/]
  TS_AWS_KMS[/"AWS KMS<br/>[Key management]"/]
  TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
  TS_AWS_SECRETS[/"AWS Secrets Manager<br/>[Secrets manager]"/]
  TS_LENDING_BACKUP[/"Installment Lending Backup<br/>and recovery<br/>[AWS Backup]"/]
  TS_LENDING_CACHE[/"Installment Lending Cache<br/>[Amazon ElastiCache]"/]
  TS_LENDING_DNS[/"Installment Lending DNS<br/>[Amazon Route 53]"/]
  TS_LENDING_WAF[/"Installment Lending Web<br/>application firewall<br/>[AWS WAF]"/]
  TS_NET_SUB_LEND_APP_A[/"Lending App Subnet A<br/>[Subnet]"/]
  TS_NET_SUB_LEND_APP_B[/"Lending App Subnet B<br/>[Subnet]"/]
  TS_NET_SUB_LEND_DATA_A[/"Lending Data Subnet A<br/>[Subnet]"/]
  TS_NET_SUB_LEND_DATA_B[/"Lending Data Subnet B<br/>[Subnet]"/]
  TS_NET_SUB_LEND_PUB_A[/"Lending Public Subnet A<br/>[Subnet]"/]
  TS_NET_SUB_LEND_PUB_B[/"Lending Public Subnet B<br/>[Subnet]"/]

  SYS_LENDING_WEB --> OI_LENDING_API
  SYS_LENDING_EDGE -->|"HTTPS"| SYS_LENDING_ALB
  SYS_LENDING_ALB -->|"HTTPS"| SYS_LENDING_WEB
  SYS_LENDING_API -->|"Kafka"| SYS_LENDING_WORKER
  SYS_LENDING_API -->|"PostgreSQL"| SYS_LENDING_DB
  SYS_LENDING_API -->|"HTTPS"| SYS_LENDING_BUCKET
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
  OI_LENDING_API --- SYS_LENDING_API

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_LENDING_OPERATIONAL s_data_assets__data_assets;
  class OI_LENDING_API s_offered_interfaces__offered_interfaces;
  class SYS_LENDING_ALB,SYS_LENDING_API,SYS_LENDING_BUCKET,SYS_LENDING_DB,SYS_LENDING_EDGE,SYS_LENDING_HUB,SYS_LENDING_WEB,SYS_LENDING_WORKER s_systems__systems;
  class TS_AWS_ALB,TS_AWS_CLOUDFRONT,TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_KMS,TS_AWS_MSK,TS_AWS_PRIVATELINK,TS_AWS_RDS,TS_AWS_S3,TS_AWS_SECRETS,TS_LENDING_BACKUP,TS_LENDING_CACHE,TS_LENDING_DNS,TS_LENDING_WAF,TS_NET_SUB_LEND_APP_A,TS_NET_SUB_LEND_APP_B,TS_NET_SUB_LEND_DATA_A,TS_NET_SUB_LEND_DATA_B,TS_NET_SUB_LEND_PUB_A,TS_NET_SUB_LEND_PUB_B s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_api_service,grp_async_worker,grp_integration_hub,grp_object_store,grp_public_web_entry,grp_relational_datastore,grp_web_channel boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Installment Lending — By part](../svg/product-parts--prd-installment-lending.svg)

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

1. Installment Lending Edge → Installment Lending Load Balancer (HTTPS)
2. Installment Lending Load Balancer → Installment Lending Web (HTTPS)
3. Installment Lending Web → Installment Lending Service (HTTPS)
4. Installment Lending Service → Customer Identity Service (HTTPS) — not on this diagram
5. Installment Lending Service → Experian Credit Bureau (HTTPS) — not on this diagram
6. Installment Lending Service → Installment Lending Database (PostgreSQL)
7. Installment Lending Service → Core Card Ledger (MQ) — not on this diagram
8. Installment Lending Service → Installment Lending Async Worker (Kafka)

30 entities, 39 relationships. Generated from the model; edit the model, not this file.
