# Originate point-of-sale installment loan — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Originate point-of-sale installment loan — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_LEND_02_01{{"Dealer Application Intake"}}
    CAP_LEND_02{{"Indirect Application &<br/>Underwriting"}}
    CAP_LEND_02_02{{"Indirect Credit Decision &<br/>Counteroffer"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_ADVERSE_ACT[["Adverse action notice<br/>completeness"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_APPLICATION[("Credit application record")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_LENDING_016[\"Originate point-of-sale<br/>installment loan"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_IDV_VENDOR["Identity Document<br/>Verification<br/>[Onfido]"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
    SYS_OBAFF_VENDOR["Open Banking Affordability<br/>[TrueLayer]"]
    SYS_POSFIN_API["Point-of-Sale Finance<br/>Service<br/>[GKE · Point-of-Sale Finance Cache]"]
  end

  P_LENDING_016 -->|"Primary"| SYS_POSFIN_API
  P_LENDING_016 -->|"Supporting"| SYS_LENDING_API
  P_LENDING_016 -->|"Supporting"| SYS_OBAFF_VENDOR
  P_LENDING_016 -->|"Supporting"| SYS_IDV_VENDOR
  P_LENDING_016 -->|"Supporting"| SYS_CORE_LEDGER
  P_LENDING_016 -->|"Write"| DA_APPLICATION
  P_LENDING_016 -->|"governed by"| CTL_ADVERSE_ACT
  P_LENDING_016 -->|"supports"| CAP_LEND_02_01
  P_LENDING_016 -->|"supports"| CAP_LEND_02_02
  P_LENDING_016 -->|"supports"| CAP_LEND_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_LEND_02,CAP_LEND_02_01,CAP_LEND_02_02 s_capabilities__capabilities;
  class CTL_ADVERSE_ACT s_controls__controls;
  class DA_APPLICATION s_data_assets__data_assets;
  class P_LENDING_016 s_processes__processes;
  class SYS_CORE_LEDGER,SYS_IDV_VENDOR,SYS_LENDING_API,SYS_OBAFF_VENDOR,SYS_POSFIN_API s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Originate point-of-sale installment loan — Systems, Data and Controls](../svg/process-systems--p-lending-016.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

11 entities, 10 relationships. Generated from the model; edit the model, not this file.
