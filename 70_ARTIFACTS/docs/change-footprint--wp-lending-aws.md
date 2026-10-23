# Build installment lending on AWS — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Build installment lending on AWS — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_LENDING_WORKER["Installment Lending Async<br/>Worker<br/>[EKS · MSK]"]
    SYS_LENDING_DB["Installment Lending<br/>Database<br/>[RDS]"]
    SYS_LENDING_EDGE["Installment Lending Edge"]
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
    SYS_LENDING_ALB["Installment Lending Load<br/>Balancer"]
    SYS_LENDING_BUCKET["Installment Lending Object<br/>Store<br/>[S3]"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
    SYS_LENDING_WEB["Installment Lending Web<br/>[EKS]"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_LENDING_AWS["Build installment lending<br/>on AWS"]
  end

  WP_LENDING_AWS -->|"Builds"| SYS_LENDING_EDGE
  WP_LENDING_AWS -->|"Builds"| SYS_LENDING_ALB
  WP_LENDING_AWS -->|"Builds"| SYS_LENDING_WEB
  WP_LENDING_AWS -->|"Builds"| SYS_LENDING_API
  WP_LENDING_AWS -->|"Builds"| SYS_LENDING_WORKER
  WP_LENDING_AWS -->|"Builds"| SYS_LENDING_DB
  WP_LENDING_AWS -->|"Builds"| SYS_LENDING_BUCKET
  WP_LENDING_AWS -->|"Builds"| SYS_LENDING_HUB
  SYS_LENDING_API -->|"ReadWrite"| DA_LENDING_OPERATIONAL
  SYS_LENDING_WORKER -->|"Read"| DA_LENDING_OPERATIONAL

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class DA_LENDING_OPERATIONAL s_data_assets__data_assets;
  class SYS_LENDING_ALB,SYS_LENDING_API,SYS_LENDING_BUCKET,SYS_LENDING_DB,SYS_LENDING_EDGE,SYS_LENDING_HUB,SYS_LENDING_WEB,SYS_LENDING_WORKER s_systems__systems;
  class WP_LENDING_AWS s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Build installment lending on AWS — Footprint](../svg/change-footprint--wp-lending-aws.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#0d9488` | work packages |

10 entities, 10 relationships. Generated from the model; edit the model, not this file.
