# Point-of-Sale Finance — Onboarding

What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart TB
  %% Point-of-Sale Finance — Onboarding
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_GCP["GCP"]
    direction TB
    subgraph grp_GCP__gcp_analytics_prod["project gcp-analytics-prod"]
      direction TB
      subgraph grp_GCP__gcp_analytics_prod__europe_west2["region europe-west2"]
        direction TB
        subgraph grp_GCP__gcp_analytics_prod__europe_west2__Private_Data["Private-Data"]
          direction TB
          SYS_LENDPERF_PIPELINE["Lending Portfolio<br/>Performance Pipeline<br/>[BigQuery · Dataflow +3]"]
        end
      end
    end
    subgraph grp_GCP__gcp_lending_prod["project gcp-lending-prod"]
      direction TB
      subgraph grp_GCP__gcp_lending_prod__europe_west2["region europe-west2"]
        direction TB
        SYS_POSFIN_EVENTS["Point-of-Sale Finance<br/>Event Publisher<br/>[Pub/Sub]"]
        subgraph grp_GCP__gcp_lending_prod__europe_west2__Public["Public"]
          direction TB
          SYS_OBAFF_WEBHOOKS["Open Banking Affordability<br/>Webhook Listener<br/>[GKE]"]
        end
        subgraph grp_GCP__gcp_lending_prod__europe_west2__Private_App["Private-App"]
          direction TB
          SYS_OBAFF_GATEWAY["Open Banking Affordability<br/>Integration Gateway<br/>[GKE]"]
          OI_POSFIN_API("Point-of-Sale Finance API<br/>[HTTPS]")
          SYS_POSFIN_API["Point-of-Sale Finance<br/>Service<br/>[GKE · Point-of-Sale Finance Cache]"]
          SYS_POSFIN_WEB["Point-of-Sale Finance Web<br/>[GKE]"]
        end
        subgraph grp_GCP__gcp_lending_prod__europe_west2__Private_Data["Private-Data"]
          direction TB
          SYS_POSFIN_DB["Point-of-Sale Finance<br/>Database<br/>[Cloud SQL]"]
        end
      end
    end
  end

  SYS_POSFIN_EVENTS -->|"Pub/Sub"| SYS_LENDPERF_PIPELINE
  SYS_POSFIN_API -->|"HTTPS"| SYS_OBAFF_GATEWAY
  SYS_OBAFF_WEBHOOKS -->|"HTTPS"| SYS_POSFIN_API
  SYS_POSFIN_WEB --> OI_POSFIN_API
  SYS_POSFIN_API -->|"PostgreSQL"| SYS_POSFIN_DB
  SYS_POSFIN_API -->|"AMQP"| SYS_POSFIN_EVENTS
  OI_POSFIN_API --- SYS_POSFIN_API

  classDef s_offered_interfaces__private_app fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_app fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_data fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__public fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class OI_POSFIN_API s_offered_interfaces__private_app;
  class SYS_POSFIN_EVENTS s_systems__default;
  class SYS_OBAFF_GATEWAY,SYS_POSFIN_API,SYS_POSFIN_WEB s_systems__private_app;
  class SYS_LENDPERF_PIPELINE,SYS_POSFIN_DB s_systems__private_data;
  class SYS_OBAFF_WEBHOOKS s_systems__public;
  classDef boundary1 fill:#f1f6ff,stroke:#4285f4,color:#1a4f9e;
  class grp_GCP__gcp_analytics_prod__europe_west2__Private_Data,grp_GCP__gcp_lending_prod__europe_west2__Public,grp_GCP__gcp_lending_prod__europe_west2__Private_App,grp_GCP__gcp_lending_prod__europe_west2__Private_Data boundary1;
  classDef boundary2 fill:#f8fafc,stroke:#5f6368,color:#3c4043,stroke-dasharray:2 3;
  class grp_GCP__gcp_analytics_prod__europe_west2,grp_GCP__gcp_lending_prod__europe_west2 boundary2;
  classDef boundary3 fill:#f8fbff,stroke:#4285f4,color:#1a4f9e,stroke-dasharray:6 3;
  class grp_GCP__gcp_analytics_prod,grp_GCP__gcp_lending_prod boundary3;
  classDef boundary4 fill:#f8fbff,stroke:#4285f4,color:#1a4f9e;
  class grp_GCP boundary4;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Point-of-Sale Finance — Onboarding](../svg/onboarding--prd-pos-finance.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |

**network zone** is the boundary each node sits in.

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#4285f4` | GCP |
| dashed `#4285f4` | GCP project |
| dotted `#5f6368` | GCP region |
| solid `#4285f4` | GCP subnet |

8 entities, 7 relationships. Generated from the model; edit the model, not this file.
