# Refer account to legal and manage litigation — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Refer account to legal and manage litigation — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_COLL_06{{"Bankruptcy, Deceased &<br/>Legal Account Handling"}}
    CAP_COLL_06_03{{"Legal Placement &<br/>Litigation"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_FDCPA_NOTICE[["Statutory collections<br/>notices"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_COLLECT_ACT[("Collections activity<br/>record")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_RECOVERY_006[\"Refer account to legal and<br/>manage litigation"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_DOC["Document management and<br/>archive"]
    SYS_LEGAL_MATTER["Legal matter management<br/>[SaaS]"]
  end

  P_RECOVERY_006 -->|"Primary"| SYS_LEGAL_MATTER
  P_RECOVERY_006 -->|"Supporting"| SYS_COLLECT_API
  P_RECOVERY_006 -->|"Supporting"| SYS_DOC
  P_RECOVERY_006 -->|"Read"| DA_COLLECT_ACT
  P_RECOVERY_006 -->|"governed by"| CTL_FDCPA_NOTICE
  P_RECOVERY_006 -->|"supports"| CAP_COLL_06_03
  P_RECOVERY_006 -->|"supports"| CAP_COLL_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_COLL_06,CAP_COLL_06_03 s_capabilities__capabilities;
  class CTL_FDCPA_NOTICE s_controls__controls;
  class DA_COLLECT_ACT s_data_assets__data_assets;
  class P_RECOVERY_006 s_processes__processes;
  class SYS_COLLECT_API,SYS_DOC,SYS_LEGAL_MATTER s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Refer account to legal and manage litigation — Systems, Data and Controls](../svg/process-systems--p-recovery-006.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

8 entities, 7 relationships. Generated from the model; edit the model, not this file.
