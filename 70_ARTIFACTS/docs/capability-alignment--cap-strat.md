# Enterprise Strategy & Planning — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Enterprise Strategy & Planning — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_STRAT_03{{"Business Performance<br/>Management"}}
    CAP_STRAT_04{{"Enterprise Architecture &<br/>Change Portfolio"}}
    CAP_STRAT{{"Enterprise Strategy &<br/>Planning"}}
    CAP_STRAT_01{{"Market & Competitive<br/>Analysis"}}
    CAP_STRAT_05{{"Merger, Acquisition &<br/>Portfolio Transaction"}}
    CAP_STRAT_02{{"Portfolio Strategy &<br/>Investment Planning"}}
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_APQC["APQC Process<br/>Classification Framework"]
    FW_BIAN["BIAN"]
    FW_BIZBOK["BIZBOK"]
    FW_ITIL["ITIL 4"]
    FW_TOGAF["TOGAF"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_EA_007[\"Assess change impact of a<br/>proposed system change"/]
    P_EA_005[\"Assess technology<br/>lifecycle and<br/>rationalization"/]
    P_APPDEV_009[\"Decommission an<br/>application"/]
    P_STRATEGY_001[\"Evaluate and execute<br/>portfolio transaction"/]
    P_EA_008[\"Evaluate and select a<br/>technology or platform"/]
    P_EA_003[\"Grant or decline an<br/>architecture exception"/]
    P_EA_004[\"Maintain architecture<br/>standards and reference<br/>models"/]
    P_EA_001[\"Maintain target-state<br/>architecture and roadmap"/]
    P_EA_009[\"Maintain the application<br/>and technology inventory"/]
    P_EA_006[\"Maintain the capability<br/>map and process inventory"/]
    P_APPDEV_006[\"Manage technical debt"/]
    P_EA_002[\"Review solution<br/>architecture for an<br/>initiative"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_ARCHREPO["Architecture repository<br/>[SaaS]"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_WORKTRACK["Work and change tracking<br/>[SaaS]"]
  end

  CAP_STRAT_01 -->|"part of"| CAP_STRAT
  CAP_STRAT_02 -->|"part of"| CAP_STRAT
  CAP_STRAT_03 -->|"part of"| CAP_STRAT
  CAP_STRAT_04 -->|"part of"| CAP_STRAT
  CAP_STRAT_05 -->|"part of"| CAP_STRAT
  CAP_STRAT -->|"Informed by"| FW_TOGAF
  CAP_STRAT -->|"Informed by"| FW_BIZBOK
  CAP_STRAT_01 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_STRAT_02 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_STRAT_03 -->|"1.0 Develop Vision and…"| FW_APQC
  CAP_STRAT_04 -->|"12.0 Develop and Manage…"| FW_APQC
  CAP_STRAT_04 -->|"General management #gt;…"| FW_ITIL
  CAP_STRAT_05 -->|"1.0 Develop Vision and…"| FW_APQC
  P_STRATEGY_001 -->|"supported by"| CAP_STRAT_05
  P_EA_001 -->|"supported by"| CAP_STRAT_04
  P_EA_001 -->|"supported by"| CAP_STRAT_02
  P_EA_002 -->|"supported by"| CAP_STRAT_04
  P_EA_003 -->|"supported by"| CAP_STRAT_04
  P_EA_004 -->|"supported by"| CAP_STRAT_04
  P_EA_005 -->|"supported by"| CAP_STRAT_04
  P_EA_006 -->|"supported by"| CAP_STRAT_04
  P_EA_007 -->|"supported by"| CAP_STRAT_04
  P_EA_008 -->|"supported by"| CAP_STRAT_04
  P_EA_009 -->|"supported by"| CAP_STRAT_04
  P_APPDEV_006 -->|"supported by"| CAP_STRAT_04
  P_APPDEV_009 -->|"supported by"| CAP_STRAT_04
  SYS_ARCHREPO -->|"realizes"| CAP_STRAT_02
  SYS_ARCHREPO -->|"realizes"| CAP_STRAT_04
  SYS_DATA_INGEST -->|"realizes"| CAP_STRAT_05
  SYS_WORKTRACK -->|"realizes"| CAP_STRAT_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_STRAT,CAP_STRAT_01,CAP_STRAT_02,CAP_STRAT_03,CAP_STRAT_04,CAP_STRAT_05 s_capabilities__capabilities;
  class FW_APQC,FW_BIAN,FW_BIZBOK,FW_ITIL,FW_TOGAF s_frameworks__frameworks;
  class P_APPDEV_006,P_APPDEV_009,P_EA_001,P_EA_002,P_EA_003,P_EA_004,P_EA_005,P_EA_006,P_EA_007,P_EA_008,P_EA_009,P_STRATEGY_001 s_processes__processes;
  class SYS_ARCHREPO,SYS_DATA_INGEST,SYS_WORKTRACK s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Enterprise Strategy & Planning — Frameworks, Controls, Systems](../svg/capability-alignment--cap-strat.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

26 entities, 30 relationships. Generated from the model; edit the model, not this file.
