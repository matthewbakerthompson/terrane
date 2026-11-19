# Qualify, price, and contract servicing client — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Qualify, price, and contract servicing client — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PART_03{{"Servicing Client<br/>Origination & Contracting"}}
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CLIENT_SERV[("Servicing client program<br/>data")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_CLIENTMGMT_001[\"Qualify, price, and<br/>contract servicing client"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DOC["Document management and<br/>archive"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
    SYS_CLIENT_PORTAL["Servicing client portal"]
  end

  P_CLIENTMGMT_001 -->|"Primary"| SYS_CLIENT_PORTAL
  P_CLIENTMGMT_001 -->|"Supporting"| SYS_DOC
  P_CLIENTMGMT_001 -->|"Supporting"| SYS_GRC
  P_CLIENTMGMT_001 -->|"Write"| DA_CLIENT_SERV
  P_CLIENTMGMT_001 -->|"supports"| CAP_PART_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PART_03 s_capabilities__capabilities;
  class DA_CLIENT_SERV s_data_assets__data_assets;
  class P_CLIENTMGMT_001 s_processes__processes;
  class SYS_CLIENT_PORTAL,SYS_DOC,SYS_GRC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Qualify, price, and contract servicing client — Systems, Data and Controls](../svg/process-systems--p-clientmgmt-001.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
