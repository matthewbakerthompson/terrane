# Open Banking Affordability — Onboarding

What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart TB
  %% Open Banking Affordability — Onboarding
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_GCP["GCP"]
    direction TB
    subgraph grp_GCP__gcp_lending_prod["project gcp-lending-prod"]
      direction TB
      subgraph grp_GCP__gcp_lending_prod__europe_west2["region europe-west2"]
        direction TB
        subgraph grp_GCP__gcp_lending_prod__europe_west2__Public["Public"]
          direction TB
          SYS_OBAFF_WEBHOOKS["Open Banking Affordability<br/>Webhook Listener<br/>[GKE]"]
        end
        subgraph grp_GCP__gcp_lending_prod__europe_west2__Private_App["Private-App"]
          direction TB
          SYS_OBAFF_GATEWAY["Open Banking Affordability<br/>Integration Gateway<br/>[GKE]"]
          SYS_POSFIN_API["Point-of-Sale Finance<br/>Service<br/>[GKE · Point-of-Sale Finance Cache]"]
        end
        subgraph grp_GCP__gcp_lending_prod__europe_west2__Shared_Services["Shared-Services"]
          direction TB
          SYS_OBAFF_EGRESS["Open Banking Affordability<br/>Private Egress"]
        end
      end
    end
  end

  subgraph grp_SaaS["SaaS"]
    direction TB
    subgraph grp_SaaS__eu_west_1["region eu-west-1"]
      direction TB
      subgraph grp_SaaS__eu_west_1__Edge["Edge"]
        direction TB
        SYS_OBAFF_VENDOR["Open Banking Affordability<br/>[TrueLayer]"]
      end
    end
  end

  SYS_POSFIN_API -->|"HTTPS"| SYS_OBAFF_GATEWAY
  SYS_OBAFF_GATEWAY -->|"HTTPS"| SYS_OBAFF_EGRESS
  SYS_OBAFF_EGRESS -->|"PrivateLink"| SYS_OBAFF_VENDOR
  SYS_OBAFF_VENDOR -->|"HTTPS"| SYS_OBAFF_WEBHOOKS
  SYS_OBAFF_WEBHOOKS -->|"HTTPS"| SYS_POSFIN_API

  classDef s_systems__edge fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_app fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__public fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__shared_services fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class SYS_OBAFF_VENDOR s_systems__edge;
  class SYS_OBAFF_GATEWAY,SYS_POSFIN_API s_systems__private_app;
  class SYS_OBAFF_WEBHOOKS s_systems__public;
  class SYS_OBAFF_EGRESS s_systems__shared_services;
  classDef boundary1 fill:#f1f6ff,stroke:#4285f4,color:#1a4f9e;
  class grp_GCP__gcp_lending_prod__europe_west2__Public,grp_GCP__gcp_lending_prod__europe_west2__Private_App,grp_GCP__gcp_lending_prod__europe_west2__Shared_Services boundary1;
  classDef boundary2 fill:#f8fafc,stroke:#5f6368,color:#3c4043,stroke-dasharray:2 3;
  class grp_GCP__gcp_lending_prod__europe_west2 boundary2;
  classDef boundary3 fill:#f8fafc,stroke:#8f9bb5,color:#3b4a6b,stroke-dasharray:6 3;
  class grp_SaaS__eu_west_1 boundary3;
  classDef boundary4 fill:#f8fbff,stroke:#4285f4,color:#1a4f9e,stroke-dasharray:6 3;
  class grp_GCP__gcp_lending_prod boundary4;
  classDef boundary5 fill:#f8fbff,stroke:#4285f4,color:#1a4f9e;
  class grp_GCP boundary5;
  classDef boundary6 fill:#fcfbf7,stroke:#9a8f6a,color:#6b6246,stroke-dasharray:6 3;
  class grp_SaaS,grp_SaaS__eu_west_1__Edge boundary6;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Open Banking Affordability — Onboarding](../svg/onboarding--prd-ob-affordability.svg)

**network zone** is the boundary each node sits in.

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#4285f4` | GCP |
| dashed `#9a8f6a` | SaaS |
| dashed `#4285f4` | GCP project |
| dashed `#8f9bb5` | SaaS region |
| dotted `#5f6368` | GCP region |
| dashed `#9a8f6a` | vendor tenancy |
| solid `#4285f4` | GCP subnet |

5 entities, 5 relationships. Generated from the model; edit the model, not this file.
