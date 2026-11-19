# Bill installment loan and post payments — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Bill installment loan and post payments — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_LEND_05{{"Installment Loan Servicing"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_PMT_POSTING[["Payment posting timeliness"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_LOAN_ACCOUNT[("Installment loan account")]
    DA_PAYMENT_INSTR[("Payment instructions")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_LENDING_009[\"Bill installment loan and<br/>post payments"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_LOAN_SVC["Installment loan servicing<br/>platform"]
    SYS_PAYMENT_GW["Payment capture gateway"]
    SYS_STATEMENTS["Statement Generation"]
  end

  P_LENDING_009 -->|"Primary"| SYS_LOAN_SVC
  P_LENDING_009 -->|"Supporting"| SYS_PAYMENT_GW
  P_LENDING_009 -->|"Supporting"| SYS_STATEMENTS
  P_LENDING_009 -->|"Both"| DA_LOAN_ACCOUNT
  P_LENDING_009 -->|"Read"| DA_PAYMENT_INSTR
  P_LENDING_009 -->|"governed by"| CTL_PMT_POSTING
  P_LENDING_009 -->|"supports"| CAP_LEND_05

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_LEND_05 s_capabilities__capabilities;
  class CTL_PMT_POSTING s_controls__controls;
  class DA_LOAN_ACCOUNT,DA_PAYMENT_INSTR s_data_assets__data_assets;
  class P_LENDING_009 s_processes__processes;
  class SYS_LOAN_SVC,SYS_PAYMENT_GW,SYS_STATEMENTS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Bill installment loan and post payments — Systems, Data and Controls](../svg/process-systems--p-lending-009.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

8 entities, 7 relationships. Generated from the model; edit the model, not this file.
