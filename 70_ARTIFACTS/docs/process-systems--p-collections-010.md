# Collect serviced client portfolio to client strategy — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Collect serviced client portfolio to client strategy — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_COLL_02{{"Outbound Contact<br/>Operations"}}
    CAP_COLL_02_02{{"Serviced-Portfolio<br/>Collections Contact"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_CLIENT_SLA[["Client reporting and feed<br/>monitoring"]]
    CTL_CONTACT_LIM[["Collections contact limits"]]
    CTL_FDCPA_NOTICE[["Statutory collections<br/>notices"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_COLLECT_ACT[("Collections activity<br/>record")]
    DA_CLIENT_SERV[("Servicing client program<br/>data")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_COLLECTIONS_010[\"Collect serviced client<br/>portfolio to client<br/>strategy"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_DIALER["Outbound contact platform"]
    SYS_CLIENT_PORTAL["Servicing client portal"]
  end

  P_COLLECTIONS_010 -->|"Primary"| SYS_COLLECT_API
  P_COLLECTIONS_010 -->|"Supporting"| SYS_DIALER
  P_COLLECTIONS_010 -->|"Supporting"| SYS_CLIENT_PORTAL
  P_COLLECTIONS_010 -->|"Write"| DA_COLLECT_ACT
  P_COLLECTIONS_010 -->|"Read"| DA_CLIENT_SERV
  P_COLLECTIONS_010 -->|"governed by"| CTL_CONTACT_LIM
  P_COLLECTIONS_010 -->|"governed by"| CTL_FDCPA_NOTICE
  P_COLLECTIONS_010 -->|"governed by"| CTL_CLIENT_SLA
  P_COLLECTIONS_010 -->|"supports"| CAP_COLL_02_02
  P_COLLECTIONS_010 -->|"supports"| CAP_COLL_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_COLL_02,CAP_COLL_02_02 s_capabilities__capabilities;
  class CTL_CLIENT_SLA,CTL_CONTACT_LIM,CTL_FDCPA_NOTICE s_controls__controls;
  class DA_CLIENT_SERV,DA_COLLECT_ACT s_data_assets__data_assets;
  class P_COLLECTIONS_010 s_processes__processes;
  class SYS_CLIENT_PORTAL,SYS_COLLECT_API,SYS_DIALER s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Collect serviced client portfolio to client strategy — Systems, Data and Controls](../svg/process-systems--p-collections-010.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

11 entities, 10 relationships. Generated from the model; edit the model, not this file.
