# Set and deploy credit decision strategy — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Set and deploy credit decision strategy — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_CRED_01{{"Credit Strategy &<br/>Scorecard Management"}}
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
    DA_MODEL_FEAT[("Model feature store")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_CREDIT_001[\"Set and deploy credit<br/>decision strategy"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
    SYS_MODEL["Model platform"]
    SYS_ORIG_DECISION["Originations decision<br/>engine"]
  end

  P_CREDIT_001 -->|"Primary"| SYS_ORIG_DECISION
  P_CREDIT_001 -->|"Supporting"| SYS_MODEL
  P_CREDIT_001 -->|"Supporting"| SYS_CREDIT_DATA
  P_CREDIT_001 -->|"Reads"| DA_BUREAU_FILE
  P_CREDIT_001 -->|"Reads"| DA_MODEL_FEAT
  P_CREDIT_001 -->|"supports"| CAP_CRED_01

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_CRED_01 s_capabilities__capabilities;
  class DA_BUREAU_FILE,DA_MODEL_FEAT s_data_assets__data_assets;
  class P_CREDIT_001 s_processes__processes;
  class SYS_CREDIT_DATA,SYS_MODEL,SYS_ORIG_DECISION s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Set and deploy credit decision strategy — Systems, Data and Controls](../svg/process-systems--p-credit-001.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
