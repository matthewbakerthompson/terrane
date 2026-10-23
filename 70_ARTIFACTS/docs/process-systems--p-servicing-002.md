# Deliver and archive statement — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Deliver and archive statement — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_BILL_03{{"Statement Delivery &<br/>Archive"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_002[\"Deliver and archive<br/>statement"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DOC["Document management and<br/>archive"]
    SYS_STATEMENTS["Statement Generation"]
  end

  P_SERVICING_002 -->|"Primary"| SYS_STATEMENTS
  P_SERVICING_002 -->|"Supporting"| SYS_DOC
  P_SERVICING_002 -->|"supports"| CAP_BILL_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_BILL_03 s_capabilities__capabilities;
  class P_SERVICING_002 s_processes__processes;
  class SYS_DOC,SYS_STATEMENTS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Deliver and archive statement — Systems, Data and Controls](../svg/process-systems--p-servicing-002.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

4 entities, 3 relationships. Generated from the model; edit the model, not this file.
