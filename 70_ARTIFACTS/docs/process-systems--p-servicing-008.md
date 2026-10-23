# Enroll account in hardship or assistance program — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Enroll account in hardship or assistance program — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_07{{"Hardship & Payment<br/>Assistance"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_008[\"Enroll account in hardship<br/>or assistance program"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
  end

  P_SERVICING_008 -->|"Primary"| SYS_COLLECT_API
  P_SERVICING_008 -->|"Supporting"| SYS_CORE_LEDGER
  P_SERVICING_008 -->|"Supporting"| SYS_CRM
  P_SERVICING_008 -->|"supports"| CAP_SERV_07

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SERV_07 s_capabilities__capabilities;
  class P_SERVICING_008 s_processes__processes;
  class SYS_COLLECT_API,SYS_CORE_LEDGER,SYS_CRM s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Enroll account in hardship or assistance program — Systems, Data and Controls](../svg/process-systems--p-servicing-008.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
