# Execute network chargeback — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Execute network chargeback — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_FRAUD_04{{"Chargeback & Representment<br/>Processing"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_REGE_DETERM[["Dispute determination<br/>timeliness and notice"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_DISPUTE_CASE[("Dispute case file")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DISPUTE_002[\"Execute network chargeback"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
  end

  P_DISPUTE_002 -->|"Primary"| SYS_DISPUTES_SAAS
  P_DISPUTE_002 -->|"Supporting"| SYS_CORE_LEDGER
  P_DISPUTE_002 -->|"Both"| DA_DISPUTE_CASE
  P_DISPUTE_002 -->|"governed by"| CTL_REGE_DETERM
  P_DISPUTE_002 -->|"supports"| CAP_FRAUD_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_FRAUD_04 s_capabilities__capabilities;
  class CTL_REGE_DETERM s_controls__controls;
  class DA_DISPUTE_CASE s_data_assets__data_assets;
  class P_DISPUTE_002 s_processes__processes;
  class SYS_CORE_LEDGER,SYS_DISPUTES_SAAS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Execute network chargeback — Systems, Data and Controls](../svg/process-systems--p-dispute-002.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
