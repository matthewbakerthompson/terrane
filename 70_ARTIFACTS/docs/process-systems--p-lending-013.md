# Remarket recovered collateral and pursue deficiency — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Remarket recovered collateral and pursue deficiency — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_LEND_06_02{{"Collateral Remarketing &<br/>Deficiency Recovery"}}
    CAP_LEND_06{{"Repossession & Asset<br/>Remarketing"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_REPO_NOTICE[["Repossession and<br/>disposition notices"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_COLLATERAL[("Collateral, title and lien<br/>record")]
    DA_GL[("General ledger entries")]
    DA_LOAN_ACCOUNT[("Installment loan account")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_LENDING_013[\"Remarket recovered<br/>collateral and pursue<br/>deficiency"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_GL["General ledger"]
    SYS_LOAN_SVC["Installment loan servicing<br/>platform"]
    SYS_REMARKET["Repossession and<br/>remarketing management<br/>[external]"]
  end

  P_LENDING_013 -->|"Primary"| SYS_REMARKET
  P_LENDING_013 -->|"Supporting"| SYS_LOAN_SVC
  P_LENDING_013 -->|"Supporting"| SYS_COLLECT_API
  P_LENDING_013 -->|"Supporting"| SYS_GL
  P_LENDING_013 -->|"Read"| DA_COLLATERAL
  P_LENDING_013 -->|"Both"| DA_LOAN_ACCOUNT
  P_LENDING_013 -->|"Write"| DA_GL
  P_LENDING_013 -->|"governed by"| CTL_REPO_NOTICE
  P_LENDING_013 -->|"supports"| CAP_LEND_06_02
  P_LENDING_013 -->|"supports"| CAP_LEND_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_LEND_06,CAP_LEND_06_02 s_capabilities__capabilities;
  class CTL_REPO_NOTICE s_controls__controls;
  class DA_COLLATERAL,DA_GL,DA_LOAN_ACCOUNT s_data_assets__data_assets;
  class P_LENDING_013 s_processes__processes;
  class SYS_COLLECT_API,SYS_GL,SYS_LOAN_SVC,SYS_REMARKET s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Remarket recovered collateral and pursue deficiency — Systems, Data and Controls](../svg/process-systems--p-lending-013.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

11 entities, 10 relationships. Generated from the model; edit the model, not this file.
