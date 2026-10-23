# Stand up the regulatory reporting engine — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Stand up the regulatory reporting engine — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_DATA_04{{"Analytics, Reporting & BI"}}
    CAP_FIN_04{{"Regulatory & Financial<br/>Reporting"}}
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CUST360_CURATED[("Customer 360 curated<br/>dataset")]
    DA_LENDPERF_CURATED[("Lending Portfolio<br/>Performance curated<br/>dataset")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_REG_DATA_PREP_001[\"Prepare regulatory<br/>reporting data"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CUST360_SEMANTIC["Customer 360 Semantic<br/>Layer<br/>[Snowflake Data Cloud]"]
    SYS_REG_REPORTING["Regulatory Reporting<br/>Engine<br/>[AKS · Snowflake Data Cloud]"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_REG_REPORTING["Stand up the regulatory<br/>reporting engine"]
  end

  WP_REG_REPORTING -->|"Builds"| SYS_REG_REPORTING
  WP_REG_REPORTING -->|"Changes"| SYS_CUST360_SEMANTIC
  SYS_CUST360_SEMANTIC -->|"Read"| DA_CUST360_CURATED
  SYS_REG_REPORTING -->|"Read"| DA_LENDPERF_CURATED
  SYS_REG_REPORTING -->|"Read"| DA_CUST360_CURATED
  SYS_CUST360_SEMANTIC -->|"realizes"| CAP_DATA_04
  SYS_REG_REPORTING -->|"realizes"| CAP_FIN_04
  P_REG_DATA_PREP_001 -->|"supports"| CAP_FIN_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class CAP_DATA_04,CAP_FIN_04 s_capabilities__capabilities;
  class DA_CUST360_CURATED,DA_LENDPERF_CURATED s_data_assets__data_assets;
  class P_REG_DATA_PREP_001 s_processes__processes;
  class SYS_CUST360_SEMANTIC,SYS_REG_REPORTING s_systems__systems;
  class WP_REG_REPORTING s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Data_Asset,grp_Process,grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Stand up the regulatory reporting engine — Footprint](../svg/change-footprint--wp-reg-reporting.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |
| `#0d9488` | work packages |

8 entities, 8 relationships. Generated from the model; edit the model, not this file.
