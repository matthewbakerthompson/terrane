# Exchange client data feed — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Exchange client data feed — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_TPS_03{{"Client Reporting & Data<br/>Exchange"}}
    CAP_DATA_02{{"Data Sourcing &<br/>Integration"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_CLIENT_SLA[["Client reporting and feed<br/>monitoring"]]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_TPS_005[\"Exchange client data feed"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_CLIENT_PORTAL["Servicing client portal"]
  end

  P_TPS_005 -->|"Primary"| SYS_CLIENT_PORTAL
  P_TPS_005 -->|"Supporting"| SYS_DATA_INGEST
  P_TPS_005 -->|"governed by"| CTL_CLIENT_SLA
  P_TPS_005 -->|"supports"| CAP_TPS_03
  P_TPS_005 -->|"supports"| CAP_DATA_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_DATA_02,CAP_TPS_03 s_capabilities__capabilities;
  class CTL_CLIENT_SLA s_controls__controls;
  class P_TPS_005 s_processes__processes;
  class SYS_CLIENT_PORTAL,SYS_DATA_INGEST s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Exchange client data feed — Systems, Data and Controls](../svg/process-systems--p-tps-005.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#0369a1` | processes |
| `#4338ca` | systems |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
