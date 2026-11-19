# Receive and validate dealer-submitted application — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Receive and validate dealer-submitted application — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_LEND_02_01{{"Dealer Application Intake"}}
    CAP_LEND_02{{"Indirect Application &<br/>Underwriting"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_APP_INTAKE[["Application completeness<br/>and disclosure"]]
    CTL_SANCTIONS[["Sanctions and watchlist<br/>screening"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_APPLICATION[("Credit application record")]
    DA_DEALER[("Dealer master and<br/>agreement")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_LENDING_003[\"Receive and validate<br/>dealer-submitted<br/>application"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_APPFRAUD["Application fraud<br/>screening"]
    SYS_DEALER_PORTAL["Dealer portal<br/>[SaaS]"]
    SYS_KYC["Identity verification"]
    SYS_LOS["Indirect loan origination<br/>system"]
  end

  P_LENDING_003 -->|"Primary"| SYS_LOS
  P_LENDING_003 -->|"Supporting"| SYS_DEALER_PORTAL
  P_LENDING_003 -->|"Supporting"| SYS_KYC
  P_LENDING_003 -->|"Supporting"| SYS_APPFRAUD
  P_LENDING_003 -->|"Write"| DA_APPLICATION
  P_LENDING_003 -->|"Read"| DA_DEALER
  P_LENDING_003 -->|"governed by"| CTL_APP_INTAKE
  P_LENDING_003 -->|"governed by"| CTL_SANCTIONS
  P_LENDING_003 -->|"supports"| CAP_LEND_02_01
  P_LENDING_003 -->|"supports"| CAP_LEND_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_LEND_02,CAP_LEND_02_01 s_capabilities__capabilities;
  class CTL_APP_INTAKE,CTL_SANCTIONS s_controls__controls;
  class DA_APPLICATION,DA_DEALER s_data_assets__data_assets;
  class P_LENDING_003 s_processes__processes;
  class SYS_APPFRAUD,SYS_DEALER_PORTAL,SYS_KYC,SYS_LOS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Receive and validate dealer-submitted application — Systems, Data and Controls](../svg/process-systems--p-lending-003.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

11 entities, 10 relationships. Generated from the model; edit the model, not this file.
