# Cancel ancillary products and refund unearned premium — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Cancel ancillary products and refund unearned premium — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_LEND_07{{"Ancillary Product & Dealer<br/>Reserve Administration"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_ANCILLARY_REFUND[["Ancillary product refund<br/>on early termination"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_LOAN_ACCOUNT[("Installment loan account")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_LENDING_014[\"Cancel ancillary products<br/>and refund unearned<br/>premium"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DEALER_PORTAL["Dealer portal<br/>[SaaS]"]
    SYS_GL["General ledger"]
    SYS_LOAN_SVC["Installment loan servicing<br/>platform"]
  end

  P_LENDING_014 -->|"Primary"| SYS_LOAN_SVC
  P_LENDING_014 -->|"Supporting"| SYS_DEALER_PORTAL
  P_LENDING_014 -->|"Supporting"| SYS_GL
  P_LENDING_014 -->|"Both"| DA_LOAN_ACCOUNT
  P_LENDING_014 -->|"governed by"| CTL_ANCILLARY_REFUND
  P_LENDING_014 -->|"supports"| CAP_LEND_07

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_LEND_07 s_capabilities__capabilities;
  class CTL_ANCILLARY_REFUND s_controls__controls;
  class DA_LOAN_ACCOUNT s_data_assets__data_assets;
  class P_LENDING_014 s_processes__processes;
  class SYS_DEALER_PORTAL,SYS_GL,SYS_LOAN_SVC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Cancel ancillary products and refund unearned premium — Systems, Data and Controls](../svg/process-systems--p-lending-014.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
