# Quote payoff and release title — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Quote payoff and release title — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_LEND_04{{"Collateral, Title & Lien<br/>Management"}}
    CAP_LEND_04_02{{"Payoff & Lien Release"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_LIEN_RELEASE[["Title release within<br/>statutory deadline"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_COLLATERAL[("Collateral, title and lien<br/>record")]
    DA_LOAN_ACCOUNT[("Installment loan account")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_LENDING_008[\"Quote payoff and release<br/>title"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_LOAN_SVC["Installment loan servicing<br/>platform"]
    SYS_PAYMENT_GW["Payment capture gateway"]
    SYS_TITLE["Title and lien management<br/>[external]"]
  end

  P_LENDING_008 -->|"Primary"| SYS_TITLE
  P_LENDING_008 -->|"Supporting"| SYS_LOAN_SVC
  P_LENDING_008 -->|"Supporting"| SYS_PAYMENT_GW
  P_LENDING_008 -->|"Write"| DA_COLLATERAL
  P_LENDING_008 -->|"Both"| DA_LOAN_ACCOUNT
  P_LENDING_008 -->|"governed by"| CTL_LIEN_RELEASE
  P_LENDING_008 -->|"supports"| CAP_LEND_04_02
  P_LENDING_008 -->|"supports"| CAP_LEND_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_LEND_04,CAP_LEND_04_02 s_capabilities__capabilities;
  class CTL_LIEN_RELEASE s_controls__controls;
  class DA_COLLATERAL,DA_LOAN_ACCOUNT s_data_assets__data_assets;
  class P_LENDING_008 s_processes__processes;
  class SYS_LOAN_SVC,SYS_PAYMENT_GW,SYS_TITLE s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Quote payoff and release title — Systems, Data and Controls](../svg/process-systems--p-lending-008.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

9 entities, 8 relationships. Generated from the model; edit the model, not this file.
