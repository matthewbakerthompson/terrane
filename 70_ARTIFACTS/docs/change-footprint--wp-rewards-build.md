# Build rewards redemption on Azure — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Build rewards redemption on Azure — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_BILL_04_03{{"Rewards Delivery"}}
    CAP_BILL_04{{"Rewards Earn, Accrual &<br/>Redemption"}}
    CAP_BILL_04_02{{"Rewards Redemption"}}
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_REWARDS_OPERATIONAL[("Rewards Redemption<br/>operational data")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_REWARDS_001[\"Accrue rewards earn"/]
    P_STMT_GEN_001[\"Cut cycle and generate<br/>statement"/]
    P_REWARDS_002[\"Process rewards redemption"/]
    P_REWARDS_003[\"Reconcile rewards<br/>liability"/]
    P_REWARDS_004[\"Serve redemption catalog<br/>and fulfill orders"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_REWARDS_WORKER["Rewards Redemption Async<br/>Worker<br/>[AKS · Event Hubs]"]
    SYS_REWARDS_STORE["Rewards Redemption<br/>Database<br/>[Azure SQL]"]
    SYS_REWARDS_EVENTS["Rewards Redemption Event<br/>Publisher<br/>[Service Bus]"]
    SYS_REWARDS_API["Rewards Redemption Service<br/>[AKS · Rewards Redemption Cache]"]
    SYS_REWARDS_WEB["Rewards Redemption Web<br/>[AKS]"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_REWARDS_BUILD["Build rewards redemption<br/>on Azure"]
  end

  WP_REWARDS_BUILD -->|"Builds"| SYS_REWARDS_WEB
  WP_REWARDS_BUILD -->|"Builds"| SYS_REWARDS_API
  WP_REWARDS_BUILD -->|"Builds"| SYS_REWARDS_STORE
  WP_REWARDS_BUILD -->|"Builds"| SYS_REWARDS_EVENTS
  WP_REWARDS_BUILD -->|"Builds"| SYS_REWARDS_WORKER
  SYS_REWARDS_API -->|"ReadWrite"| DA_REWARDS_OPERATIONAL
  SYS_REWARDS_STORE -->|"ReadWrite"| DA_REWARDS_OPERATIONAL
  SYS_REWARDS_API -->|"realizes"| CAP_BILL_04
  SYS_REWARDS_API -->|"realizes"| CAP_BILL_04_02
  SYS_REWARDS_API -->|"realizes"| CAP_BILL_04_03
  P_STMT_GEN_001 -->|"supports"| CAP_BILL_04
  P_REWARDS_001 -->|"supports"| CAP_BILL_04
  P_REWARDS_002 -->|"supports"| CAP_BILL_04
  P_REWARDS_003 -->|"supports"| CAP_BILL_04
  P_REWARDS_004 -->|"supports"| CAP_BILL_04_02
  P_REWARDS_004 -->|"supports"| CAP_BILL_04_03
  P_REWARDS_002 -->|"supports"| CAP_BILL_04_02
  P_REWARDS_004 -->|"supports"| CAP_BILL_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class CAP_BILL_04,CAP_BILL_04_02,CAP_BILL_04_03 s_capabilities__capabilities;
  class DA_REWARDS_OPERATIONAL s_data_assets__data_assets;
  class P_REWARDS_001,P_REWARDS_002,P_REWARDS_003,P_REWARDS_004,P_STMT_GEN_001 s_processes__processes;
  class SYS_REWARDS_API,SYS_REWARDS_EVENTS,SYS_REWARDS_STORE,SYS_REWARDS_WEB,SYS_REWARDS_WORKER s_systems__systems;
  class WP_REWARDS_BUILD s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Data_Asset,grp_Process,grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Build rewards redemption on Azure — Footprint](../svg/change-footprint--wp-rewards-build.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |
| `#0d9488` | work packages |

15 entities, 18 relationships. Generated from the model; edit the model, not this file.
