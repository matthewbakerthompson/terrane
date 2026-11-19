# Support client audit or examination — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Support client audit or examination — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_TPS_05{{"Client Audit & Oversight<br/>Support"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_TPS_007[\"Support client audit or<br/>examination"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DOC["Document management and<br/>archive"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
    SYS_CLIENT_PORTAL["Servicing client portal"]
  end

  P_TPS_007 -->|"Primary"| SYS_GRC
  P_TPS_007 -->|"Supporting"| SYS_DOC
  P_TPS_007 -->|"Supporting"| SYS_CLIENT_PORTAL
  P_TPS_007 -->|"supports"| CAP_TPS_05

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_TPS_05 s_capabilities__capabilities;
  class P_TPS_007 s_processes__processes;
  class SYS_CLIENT_PORTAL,SYS_DOC,SYS_GRC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Support client audit or examination — Systems, Data and Controls](../svg/process-systems--p-tps-007.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
