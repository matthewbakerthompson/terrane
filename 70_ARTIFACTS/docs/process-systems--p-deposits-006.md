# Produce deposit tax reporting — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Produce deposit tax reporting — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_DEP_04{{"Deposit Servicing,<br/>Interest & Maturities"}}
    CAP_DEP_04_01{{"Interest Accrual & Tax<br/>Reporting"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_TAX_REPORT[["Deposit interest tax<br/>reporting"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_DEPOSIT_ACCOUNT[("Deposit account and CD<br/>record")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DEPOSITS_006[\"Produce deposit tax<br/>reporting"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DEPOSIT["Deposit platform"]
    SYS_DOC["Document management and<br/>archive"]
  end

  P_DEPOSITS_006 -->|"Primary"| SYS_DEPOSIT
  P_DEPOSITS_006 -->|"Supporting"| SYS_DOC
  P_DEPOSITS_006 -->|"Read"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_006 -->|"governed by"| CTL_TAX_REPORT
  P_DEPOSITS_006 -->|"supports"| CAP_DEP_04_01
  P_DEPOSITS_006 -->|"supports"| CAP_DEP_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_DEP_04,CAP_DEP_04_01 s_capabilities__capabilities;
  class CTL_TAX_REPORT s_controls__controls;
  class DA_DEPOSIT_ACCOUNT s_data_assets__data_assets;
  class P_DEPOSITS_006 s_processes__processes;
  class SYS_DEPOSIT,SYS_DOC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Produce deposit tax reporting — Systems, Data and Controls](../svg/process-systems--p-deposits-006.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
