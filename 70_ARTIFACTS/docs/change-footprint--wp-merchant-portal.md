# Assemble the merchant portal on Azure — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Assemble the merchant portal on Azure — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_MERCH_02_01{{"Merchant Credit<br/>Underwriting"}}
    CAP_MERCH_07{{"Merchant Servicing &<br/>Billing"}}
    CAP_MERCH_02{{"Merchant Underwriting &<br/>Risk Vetting"}}
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_MERCHANT[("Merchant master and<br/>underwriting file")]
    DA_MERCHANT_OPERATIONAL[("Merchant Portal<br/>operational data")]
    DA_MERCH_SETTLE[("Merchant settlement and<br/>reserve ledger")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_MERCHANT_011[\"Bill merchant fees and<br/>serve statements"/]
    P_MERCHANT_005[\"Board merchant and<br/>register with networks"/]
    P_MERCHANT_002[\"Capture merchant<br/>application"/]
    P_MERCHANT_009[\"Monitor merchant exposure<br/>and activity"/]
    P_MERCHANT_001[\"Onboard and oversee ISO or<br/>agent"/]
    P_MERCHANT_008[\"Process acquiring<br/>chargeback"/]
    P_MERCHANT_004[\"Screen merchant against<br/>sanctions and network<br/>lists"/]
    P_MERCHANT_007[\"Set and adjust merchant<br/>reserve"/]
    P_MERCHANT_006[\"Settle and fund merchants"/]
    P_MERCHANT_010[\"Terminate merchant and<br/>report to network list"/]
    P_MERCHANT_003[\"Underwrite merchant"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_MERCHANT_STORE["Merchant Portal Database<br/>[Azure SQL]"]
    SYS_MERCHANT_EVENTS["Merchant Portal Event<br/>Publisher<br/>[Service Bus]"]
    SYS_MERCHANT_API["Merchant Portal Service<br/>[AKS · Merchant Portal Cache]"]
    SYS_MERCHANT_WEB["Merchant Portal Web<br/>[AKS]"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_MERCHANT_PORTAL["Assemble the merchant<br/>portal on Azure"]
  end

  WP_MERCHANT_PORTAL -->|"Builds"| SYS_MERCHANT_WEB
  WP_MERCHANT_PORTAL -->|"Builds"| SYS_MERCHANT_API
  WP_MERCHANT_PORTAL -->|"Builds"| SYS_MERCHANT_STORE
  WP_MERCHANT_PORTAL -->|"Builds"| SYS_MERCHANT_EVENTS
  SYS_MERCHANT_API -->|"ReadWrite"| DA_MERCHANT_OPERATIONAL
  SYS_MERCHANT_API -->|"Write"| DA_MERCHANT
  SYS_MERCHANT_API -->|"Read"| DA_MERCH_SETTLE
  SYS_MERCHANT_WEB -->|"realizes"| CAP_MERCH_02
  SYS_MERCHANT_WEB -->|"realizes"| CAP_MERCH_02_01
  SYS_MERCHANT_WEB -->|"realizes"| CAP_MERCH_07
  P_MERCHANT_001 -->|"Read"| DA_MERCHANT
  P_MERCHANT_002 -->|"Write"| DA_MERCHANT
  P_MERCHANT_003 -->|"Both"| DA_MERCHANT
  P_MERCHANT_004 -->|"Read"| DA_MERCHANT
  P_MERCHANT_005 -->|"Both"| DA_MERCHANT
  P_MERCHANT_006 -->|"Write"| DA_MERCH_SETTLE
  P_MERCHANT_007 -->|"Both"| DA_MERCH_SETTLE
  P_MERCHANT_007 -->|"Read"| DA_MERCHANT
  P_MERCHANT_008 -->|"Write"| DA_MERCH_SETTLE
  P_MERCHANT_008 -->|"Read"| DA_MERCHANT
  P_MERCHANT_009 -->|"Read"| DA_MERCH_SETTLE
  P_MERCHANT_009 -->|"Read"| DA_MERCHANT
  P_MERCHANT_010 -->|"Write"| DA_MERCHANT
  P_MERCHANT_010 -->|"Write"| DA_MERCH_SETTLE
  P_MERCHANT_011 -->|"Read"| DA_MERCH_SETTLE
  P_MERCHANT_002 -->|"supports"| CAP_MERCH_02_01
  P_MERCHANT_003 -->|"supports"| CAP_MERCH_02_01
  P_MERCHANT_011 -->|"supports"| CAP_MERCH_07
  P_MERCHANT_002 -->|"supports"| CAP_MERCH_02
  P_MERCHANT_003 -->|"supports"| CAP_MERCH_02
  P_MERCHANT_004 -->|"supports"| CAP_MERCH_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class CAP_MERCH_02,CAP_MERCH_02_01,CAP_MERCH_07 s_capabilities__capabilities;
  class DA_MERCH_SETTLE,DA_MERCHANT,DA_MERCHANT_OPERATIONAL s_data_assets__data_assets;
  class P_MERCHANT_001,P_MERCHANT_002,P_MERCHANT_003,P_MERCHANT_004,P_MERCHANT_005,P_MERCHANT_006,P_MERCHANT_007,P_MERCHANT_008,P_MERCHANT_009,P_MERCHANT_010,P_MERCHANT_011 s_processes__processes;
  class SYS_MERCHANT_API,SYS_MERCHANT_EVENTS,SYS_MERCHANT_STORE,SYS_MERCHANT_WEB s_systems__systems;
  class WP_MERCHANT_PORTAL s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Data_Asset,grp_Process,grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Assemble the merchant portal on Azure — Footprint](../svg/change-footprint--wp-merchant-portal.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |
| `#0d9488` | work packages |

22 entities, 31 relationships. Generated from the model; edit the model, not this file.
