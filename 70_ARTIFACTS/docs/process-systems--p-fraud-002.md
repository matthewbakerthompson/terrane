# Investigate and adjudicate fraud case — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Investigate and adjudicate fraud case — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_FRAUD_02{{"Fraud Case Investigation"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_FRAUD_SLA[["Fraud alert handling<br/>service level"]]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_FRAUD_002[\"Investigate and adjudicate<br/>fraud case"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
    SYS_FRAUD_DETECT["Transaction fraud<br/>detection"]
  end

  P_FRAUD_002 -->|"Primary"| SYS_DISPUTES_SAAS
  P_FRAUD_002 -->|"Supporting"| SYS_FRAUD_DETECT
  P_FRAUD_002 -->|"Supporting"| SYS_CRM
  P_FRAUD_002 -->|"governed by"| CTL_FRAUD_SLA
  P_FRAUD_002 -->|"supports"| CAP_FRAUD_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_FRAUD_02 s_capabilities__capabilities;
  class CTL_FRAUD_SLA s_controls__controls;
  class P_FRAUD_002 s_processes__processes;
  class SYS_CRM,SYS_DISPUTES_SAAS,SYS_FRAUD_DETECT s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Investigate and adjudicate fraud case — Systems, Data and Controls](../svg/process-systems--p-fraud-002.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#0369a1` | processes |
| `#4338ca` | systems |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
