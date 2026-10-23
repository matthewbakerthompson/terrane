# Installment Lending Object Store — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Installment Lending Object Store — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_LENDING_BUCKET["Installment Lending Object<br/>Store<br/>[S3]"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
    TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
    TS_AWS_S3[/"Amazon S3<br/>[Object store]"/]
    TS_AWS_KMS[/"AWS KMS<br/>[Key management]"/]
    TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
    TS_AWS_SECRETS[/"AWS Secrets Manager<br/>[Secrets manager]"/]
    TS_LENDING_CACHE[/"Installment Lending Cache<br/>[Amazon ElastiCache]"/]
    TS_NET_SUB_LEND_APP_A[/"Lending App Subnet A<br/>[Subnet]"/]
    TS_NET_SUB_LEND_APP_B[/"Lending App Subnet B<br/>[Subnet]"/]
    TS_NET_SUB_LEND_DATA_A[/"Lending Data Subnet A<br/>[Subnet]"/]
  end

  SYS_LENDING_API -->|"HTTPS"| SYS_LENDING_BUCKET
  SYS_LENDING_API -.->|"runs on"| TS_AWS_EKS
  SYS_LENDING_API -.->|"runs on"| TS_LENDING_CACHE
  SYS_LENDING_API -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_LENDING_API -.->|"runs on"| TS_AWS_SECRETS
  SYS_LENDING_API -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_LENDING_BUCKET -.->|"runs on"| TS_AWS_S3
  SYS_LENDING_BUCKET -.->|"runs on"| TS_AWS_KMS
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_A
  SYS_LENDING_API -.->|"runs on"| TS_NET_SUB_LEND_APP_B
  SYS_LENDING_BUCKET -.->|"runs on"| TS_NET_SUB_LEND_DATA_A
  SYS_LENDING_API -->|"ReadWrite"| DA_LENDING_OPERATIONAL

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_LENDING_OPERATIONAL s_data_assets__data_assets;
  class SYS_LENDING_API,SYS_LENDING_BUCKET s_systems__systems;
  class TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_KMS,TS_AWS_PRIVATELINK,TS_AWS_S3,TS_AWS_SECRETS,TS_LENDING_CACHE,TS_NET_SUB_LEND_APP_A,TS_NET_SUB_LEND_APP_B,TS_NET_SUB_LEND_DATA_A s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Installment Lending Object Store — Architecture](../svg/system-architecture--sys-lending-bucket.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

13 entities, 12 relationships. Generated from the model; edit the model, not this file.
