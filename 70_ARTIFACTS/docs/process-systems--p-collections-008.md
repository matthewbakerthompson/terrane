# Negotiate settlement offer — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Negotiate settlement offer — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_COLL_03{{"Payment Arrangement &<br/>Settlement Offers"}}
    CAP_COLL_03_02{{"Settlement Offers"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_TREATMENT_APPR[["Treatment strategy<br/>approval"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_COLLECT_ACT[("Collections activity<br/>record")]
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_COLLECTIONS_008[\"Negotiate settlement offer"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_BUREAU_GW["Credit bureau gateway"]
    SYS_DOC["Document management and<br/>archive"]
  end

  P_COLLECTIONS_008 -->|"Primary"| SYS_COLLECT_API
  P_COLLECTIONS_008 -->|"Supporting"| SYS_DOC
  P_COLLECTIONS_008 -->|"Supporting"| SYS_BUREAU_GW
  P_COLLECTIONS_008 -->|"Write"| DA_COLLECT_ACT
  P_COLLECTIONS_008 -->|"Write"| DA_BUREAU_FILE
  P_COLLECTIONS_008 -->|"governed by"| CTL_TREATMENT_APPR
  P_COLLECTIONS_008 -->|"supports"| CAP_COLL_03_02
  P_COLLECTIONS_008 -->|"supports"| CAP_COLL_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_COLL_03,CAP_COLL_03_02 s_capabilities__capabilities;
  class CTL_TREATMENT_APPR s_controls__controls;
  class DA_BUREAU_FILE,DA_COLLECT_ACT s_data_assets__data_assets;
  class P_COLLECTIONS_008 s_processes__processes;
  class SYS_BUREAU_GW,SYS_COLLECT_API,SYS_DOC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Negotiate settlement offer — Systems, Data and Controls](../svg/process-systems--p-collections-008.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

9 entities, 8 relationships. Generated from the model; edit the model, not this file.
