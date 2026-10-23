# Furnish credit bureau data — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Furnish credit bureau data — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_COLL_08{{"Credit Bureau Reporting &<br/>Dispute Handling"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_BUREAU_ACC[["Bureau furnishing accuracy"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_COLLECTIONS_005[\"Furnish credit bureau data"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_BUREAU_GW["Credit bureau gateway"]
  end

  P_COLLECTIONS_005 -->|"Primary"| SYS_BUREAU_GW
  P_COLLECTIONS_005 -->|"Supporting"| SYS_CORE_LEDGER
  P_COLLECTIONS_005 -->|"Writes"| DA_BUREAU_FILE
  P_COLLECTIONS_005 -->|"governed by"| CTL_BUREAU_ACC
  P_COLLECTIONS_005 -->|"supports"| CAP_COLL_08

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_COLL_08 s_capabilities__capabilities;
  class CTL_BUREAU_ACC s_controls__controls;
  class DA_BUREAU_FILE s_data_assets__data_assets;
  class P_COLLECTIONS_005 s_processes__processes;
  class SYS_BUREAU_GW,SYS_CORE_LEDGER s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Furnish credit bureau data — Systems, Data and Controls](../svg/process-systems--p-collections-005.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
