# Capture and resolve complaint — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Capture and resolve complaint — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_05{{"Complaint Capture &<br/>Resolution"}}
    CAP_RGOV_06{{"Complaint Oversight &<br/>UDAAP Management"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_COMPLAINT_REG[["Complaint regulatory<br/>routing"]]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_006[\"Capture and resolve<br/>complaint"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CONTACT["Contact center platform"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
  end

  P_SERVICING_006 -->|"Primary"| SYS_CRM
  P_SERVICING_006 -->|"Supporting"| SYS_GRC
  P_SERVICING_006 -->|"Supporting"| SYS_CONTACT
  P_SERVICING_006 -->|"governed by"| CTL_COMPLAINT_REG
  P_SERVICING_006 -->|"supports"| CAP_SERV_05
  P_SERVICING_006 -->|"supports"| CAP_RGOV_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_RGOV_06,CAP_SERV_05 s_capabilities__capabilities;
  class CTL_COMPLAINT_REG s_controls__controls;
  class P_SERVICING_006 s_processes__processes;
  class SYS_CONTACT,SYS_CRM,SYS_GRC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Capture and resolve complaint — Systems, Data and Controls](../svg/process-systems--p-servicing-006.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
