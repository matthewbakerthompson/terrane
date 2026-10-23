# Capture card application — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Capture card application — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_ORIG_01{{"Application Capture"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_APP_INTAKE[["Application completeness<br/>and disclosure"]]
    CTL_SCRA_MLA[["Servicemember protections<br/>screening"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_APPLICATION[("Credit application record")]
    DA_PROSPECT[("Prospect marketing list")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_ORIG_001[\"Capture card application"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
    SYS_MOBILE["Cardholder mobile<br/>application"]
    SYS_CONTACT["Contact center platform"]
    SYS_ORIG_DECISION["Originations decision<br/>engine"]
  end

  P_ORIG_001 -->|"Primary"| SYS_ORIG_DECISION
  P_ORIG_001 -->|"Supporting"| SYS_CARDSVC_WEB
  P_ORIG_001 -->|"Supporting"| SYS_MOBILE
  P_ORIG_001 -->|"Supporting"| SYS_CONTACT
  P_ORIG_001 -->|"Writes"| DA_APPLICATION
  P_ORIG_001 -->|"Both"| DA_PROSPECT
  P_ORIG_001 -->|"governed by"| CTL_APP_INTAKE
  P_ORIG_001 -->|"governed by"| CTL_SCRA_MLA
  P_ORIG_001 -->|"supports"| CAP_ORIG_01

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_ORIG_01 s_capabilities__capabilities;
  class CTL_APP_INTAKE,CTL_SCRA_MLA s_controls__controls;
  class DA_APPLICATION,DA_PROSPECT s_data_assets__data_assets;
  class P_ORIG_001 s_processes__processes;
  class SYS_CARDSVC_WEB,SYS_CONTACT,SYS_MOBILE,SYS_ORIG_DECISION s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Capture card application — Systems, Data and Controls](../svg/process-systems--p-orig-001.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

10 entities, 9 relationships. Generated from the model; edit the model, not this file.
