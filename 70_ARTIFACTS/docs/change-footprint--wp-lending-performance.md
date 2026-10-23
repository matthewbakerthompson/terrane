# Curate lending performance in BigQuery — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Curate lending performance in BigQuery — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_LENDPERF_CURATED[("Lending Portfolio<br/>Performance curated<br/>dataset")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_LENDPERF_PIPELINE["Lending Portfolio<br/>Performance Pipeline<br/>[BigQuery · Dataflow +3]"]
    SYS_LENDPERF_SEMANTIC["Lending Portfolio<br/>Performance Semantic Layer<br/>[BigQuery · Looker]"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_LENDING_PERFORMANCE["Curate lending performance<br/>in BigQuery"]
  end

  WP_LENDING_PERFORMANCE -->|"Builds"| SYS_LENDPERF_PIPELINE
  WP_LENDING_PERFORMANCE -->|"Builds"| SYS_LENDPERF_SEMANTIC
  SYS_LENDPERF_PIPELINE -->|"Write"| DA_LENDPERF_CURATED
  SYS_LENDPERF_SEMANTIC -->|"Read"| DA_LENDPERF_CURATED

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class DA_LENDPERF_CURATED s_data_assets__data_assets;
  class SYS_LENDPERF_PIPELINE,SYS_LENDPERF_SEMANTIC s_systems__systems;
  class WP_LENDING_PERFORMANCE s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Curate lending performance in BigQuery — Footprint](../svg/change-footprint--wp-lending-performance.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#0d9488` | work packages |

4 entities, 4 relationships. Generated from the model; edit the model, not this file.
