# Post recovery and account for proceeds — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Post recovery and account for proceeds — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_FIN_02{{"Interchange & Revenue<br/>Accounting"}}
    CAP_COLL_05{{"Recovery, Agency & Debt<br/>Sale Management"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_RECOVERY_005[\"Post recovery and account<br/>for proceeds"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_GL["General ledger"]
  end

  P_RECOVERY_005 -->|"Primary"| SYS_COLLECT_API
  P_RECOVERY_005 -->|"Supporting"| SYS_GL
  P_RECOVERY_005 -->|"supports"| CAP_COLL_05
  P_RECOVERY_005 -->|"supports"| CAP_FIN_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_COLL_05,CAP_FIN_02 s_capabilities__capabilities;
  class P_RECOVERY_005 s_processes__processes;
  class SYS_COLLECT_API,SYS_GL s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Post recovery and account for proceeds — Systems, Data and Controls](../svg/process-systems--p-recovery-005.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
