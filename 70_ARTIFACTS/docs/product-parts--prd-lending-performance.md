# Lending Portfolio Performance — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Lending Portfolio Performance — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  TS_GCP_BIGQUERY[/"BigQuery<br/>[Data warehouse]"/]
  TS_GCP_COMPOSER[/"Cloud Composer<br/>[Workflow orchestration]"/]
  TS_COLLIBRA[/"Collibra<br/>[Data catalog]"/]
  TS_GCP_DATAFLOW[/"Dataflow<br/>[Data pipeline]"/]
  DA_LENDPERF_CURATED[("Lending Portfolio<br/>Performance curated<br/>dataset")]
  SYS_LENDPERF_PIPELINE["Lending Portfolio<br/>Performance Pipeline<br/>[BigQuery · Dataflow +3]"]
  SYS_LENDPERF_SEMANTIC["Lending Portfolio<br/>Performance Semantic Layer<br/>[BigQuery · Looker]"]
  TS_GCP_LOOKER[/"Looker<br/>[Business intelligence]"/]
  TS_GCP_PUBSUB[/"Pub/Sub<br/>[Message queue]"/]

  SYS_LENDPERF_PIPELINE -->|"SQL"| SYS_LENDPERF_SEMANTIC
  SYS_LENDPERF_PIPELINE -.->|"runs on"| TS_GCP_PUBSUB
  SYS_LENDPERF_PIPELINE -.->|"runs on"| TS_GCP_DATAFLOW
  SYS_LENDPERF_PIPELINE -.->|"runs on"| TS_GCP_COMPOSER
  SYS_LENDPERF_PIPELINE -.->|"runs on"| TS_GCP_BIGQUERY
  SYS_LENDPERF_PIPELINE -.->|"runs on"| TS_COLLIBRA
  SYS_LENDPERF_SEMANTIC -.->|"runs on"| TS_GCP_BIGQUERY
  SYS_LENDPERF_SEMANTIC -.->|"runs on"| TS_GCP_LOOKER
  SYS_LENDPERF_PIPELINE -->|"Write"| DA_LENDPERF_CURATED
  SYS_LENDPERF_SEMANTIC -->|"Read"| DA_LENDPERF_CURATED

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_LENDPERF_CURATED s_data_assets__data_assets;
  class SYS_LENDPERF_PIPELINE,SYS_LENDPERF_SEMANTIC s_systems__systems;
  class TS_COLLIBRA,TS_GCP_BIGQUERY,TS_GCP_COMPOSER,TS_GCP_DATAFLOW,TS_GCP_LOOKER,TS_GCP_PUBSUB s_tech_services__tech_services;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Lending Portfolio Performance — By part](../svg/product-parts--prd-lending-performance.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

9 entities, 10 relationships. Generated from the model; edit the model, not this file.
