# Manage co-brand program agreement — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Manage co-brand program agreement — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PART_05{{"Co-Brand & Program Partner<br/>Management"}}
    CAP_PART_05_01{{"Partner Agreement &<br/>Program Governance"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_MKT_REVIEW[["Marketing material<br/>compliance review"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_PARTNER_PROGRAM[("Partner program terms and<br/>economics")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_PARTNERSHIPS_002[\"Manage co-brand program<br/>agreement"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_MARKETING["Campaign management"]
    SYS_DOC["Document management and<br/>archive"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
  end

  P_PARTNERSHIPS_002 -->|"Primary"| SYS_GRC
  P_PARTNERSHIPS_002 -->|"Supporting"| SYS_DOC
  P_PARTNERSHIPS_002 -->|"Supporting"| SYS_MARKETING
  P_PARTNERSHIPS_002 -->|"Write"| DA_PARTNER_PROGRAM
  P_PARTNERSHIPS_002 -->|"governed by"| CTL_MKT_REVIEW
  P_PARTNERSHIPS_002 -->|"supports"| CAP_PART_05_01
  P_PARTNERSHIPS_002 -->|"supports"| CAP_PART_05

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PART_05,CAP_PART_05_01 s_capabilities__capabilities;
  class CTL_MKT_REVIEW s_controls__controls;
  class DA_PARTNER_PROGRAM s_data_assets__data_assets;
  class P_PARTNERSHIPS_002 s_processes__processes;
  class SYS_DOC,SYS_GRC,SYS_MARKETING s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Manage co-brand program agreement — Systems, Data and Controls](../svg/process-systems--p-partnerships-002.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

8 entities, 7 relationships. Generated from the model; edit the model, not this file.
