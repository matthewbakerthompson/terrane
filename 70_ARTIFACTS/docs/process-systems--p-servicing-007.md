# Generate and deliver required notice — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Generate and deliver required notice — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_04{{"Correspondence &<br/>Notification Management"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_NOTICE_CONTENT[["Notice content and<br/>delivery evidence"]]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_007[\"Generate and deliver<br/>required notice"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DOC["Document management and<br/>archive"]
    SYS_STATEMENTS["Statement Generation"]
  end

  P_SERVICING_007 -->|"Primary"| SYS_DOC
  P_SERVICING_007 -->|"Supporting"| SYS_STATEMENTS
  P_SERVICING_007 -->|"governed by"| CTL_NOTICE_CONTENT
  P_SERVICING_007 -->|"supports"| CAP_SERV_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SERV_04 s_capabilities__capabilities;
  class CTL_NOTICE_CONTENT s_controls__controls;
  class P_SERVICING_007 s_processes__processes;
  class SYS_DOC,SYS_STATEMENTS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Generate and deliver required notice — Systems, Data and Controls](../svg/process-systems--p-servicing-007.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
