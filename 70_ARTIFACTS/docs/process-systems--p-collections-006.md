# Handle credit reporting dispute — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Handle credit reporting dispute — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_COLL_08{{"Credit Bureau Reporting &<br/>Dispute Handling"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_METRO2_RECON[["Furnishing and bucketing<br/>reconciliation"]]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_COLLECTIONS_006[\"Handle credit reporting<br/>dispute"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_BUREAU_GW["Credit bureau gateway"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
  end

  P_COLLECTIONS_006 -->|"Primary"| SYS_BUREAU_GW
  P_COLLECTIONS_006 -->|"Supporting"| SYS_CORE_LEDGER
  P_COLLECTIONS_006 -->|"Supporting"| SYS_CRM
  P_COLLECTIONS_006 -->|"governed by"| CTL_METRO2_RECON
  P_COLLECTIONS_006 -->|"supports"| CAP_COLL_08

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_COLL_08 s_capabilities__capabilities;
  class CTL_METRO2_RECON s_controls__controls;
  class P_COLLECTIONS_006 s_processes__processes;
  class SYS_BUREAU_GW,SYS_CORE_LEDGER,SYS_CRM s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Handle credit reporting dispute — Systems, Data and Controls](../svg/process-systems--p-collections-006.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#0369a1` | processes |
| `#4338ca` | systems |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
