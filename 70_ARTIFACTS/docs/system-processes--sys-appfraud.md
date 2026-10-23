# Application fraud screening — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Application fraud screening — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_ORIG_03{{"Application Fraud<br/>Screening"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_ORIG_003[\"Screen application for<br/>fraud"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_APPFRAUD["Application fraud<br/>screening"]
  end

  P_ORIG_003 -->|"Primary"| SYS_APPFRAUD
  P_ORIG_003 -->|"supports"| CAP_ORIG_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_ORIG_03 s_capabilities__capabilities;
  class P_ORIG_003 s_processes__processes;
  class SYS_APPFRAUD s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Application fraud screening — Processes and Capabilities](../svg/system-processes--sys-appfraud.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

3 entities, 2 relationships. Generated from the model; edit the model, not this file.
