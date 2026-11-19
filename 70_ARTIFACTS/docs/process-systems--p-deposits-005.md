# Accrue and pay deposit interest — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Accrue and pay deposit interest — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_DEP_04{{"Deposit Servicing,<br/>Interest & Maturities"}}
    CAP_DEP_04_01{{"Interest Accrual & Tax<br/>Reporting"}}
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_DEPOSIT_ACCOUNT[("Deposit account and CD<br/>record")]
    DA_GL[("General ledger entries")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DEPOSITS_005[\"Accrue and pay deposit<br/>interest"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DEPOSIT["Deposit platform"]
    SYS_GL["General ledger"]
  end

  P_DEPOSITS_005 -->|"Primary"| SYS_DEPOSIT
  P_DEPOSITS_005 -->|"Supporting"| SYS_GL
  P_DEPOSITS_005 -->|"Both"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_005 -->|"Write"| DA_GL
  P_DEPOSITS_005 -->|"supports"| CAP_DEP_04_01
  P_DEPOSITS_005 -->|"supports"| CAP_DEP_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_DEP_04,CAP_DEP_04_01 s_capabilities__capabilities;
  class DA_DEPOSIT_ACCOUNT,DA_GL s_data_assets__data_assets;
  class P_DEPOSITS_005 s_processes__processes;
  class SYS_DEPOSIT,SYS_GL s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Accrue and pay deposit interest — Systems, Data and Controls](../svg/process-systems--p-deposits-005.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
