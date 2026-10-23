# Review marketing creative for compliance — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Review marketing creative for compliance — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_ACQ_04{{"Marketing Compliance &<br/>Disclosure Review"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_MKT_REVIEW[["Marketing material<br/>compliance review"]]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_MARKETING_004[\"Review marketing creative<br/>for compliance"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DOC["Document management and<br/>archive"]
  end

  P_MARKETING_004 -->|"Supporting"| SYS_DOC
  P_MARKETING_004 -->|"governed by"| CTL_MKT_REVIEW
  P_MARKETING_004 -->|"supports"| CAP_ACQ_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_ACQ_04 s_capabilities__capabilities;
  class CTL_MKT_REVIEW s_controls__controls;
  class P_MARKETING_004 s_processes__processes;
  class SYS_DOC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Review marketing creative for compliance — Systems, Data and Controls](../svg/process-systems--p-marketing-004.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#0369a1` | processes |
| `#4338ca` | systems |

4 entities, 3 relationships. Generated from the model; edit the model, not this file.
