# Open Banking Affordability — Architecture

One product in full: the systems it is made of, what each runs on, the data it masters, who uses it, and everything one hop away that it connects to. For a product built from modules, every box corresponds to a part.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Open Banking Affordability — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_GCP["GCP"]
    direction LR
    TS_GCP_APIGEE[/"Apigee<br/>[API gateway]"/]
    TS_GCP_GKE[/"Google Kubernetes Engine<br/>[Container platform]"/]
    TS_GCP_PSC[/"Private Service Connect<br/>[Private egress]"/]
    TS_GCP_SECRET_MANAGER[/"Secret Manager<br/>[Secrets manager]"/]
    subgraph grp_GCP__gcp_lending_prod["project gcp-lending-prod"]
      direction LR
      subgraph grp_GCP__gcp_lending_prod__Public["Public"]
        direction LR
        SYS_OBAFF_WEBHOOKS["Open Banking Affordability<br/>Webhook Listener<br/>[GKE]"]
      end
      subgraph grp_GCP__gcp_lending_prod__Private_App["Private-App"]
        direction LR
        SYS_OBAFF_GATEWAY["Open Banking Affordability<br/>Integration Gateway<br/>[GKE]"]
        SYS_POSFIN_API["Point-of-Sale Finance<br/>Service<br/>[GKE · Point-of-Sale Finance Cache]"]
      end
      subgraph grp_GCP__gcp_lending_prod__Shared_Services["Shared-Services"]
        direction LR
        SYS_OBAFF_EGRESS["Open Banking Affordability<br/>Private Egress"]
      end
    end
    subgraph grp_GCP__gcp_shared_network["project gcp-shared-network"]
      direction LR
      subgraph grp_GCP__gcp_shared_network__Shared_Services["Shared-Services"]
        direction LR
        TS_GCP_NCC[/"Network Connectivity<br/>Center<br/>[Transit hub]"/]
      end
    end
  end

  subgraph grp_SaaS["SaaS"]
    direction LR
    subgraph grp_SaaS__Edge["Edge"]
      direction LR
      SYS_OBAFF_VENDOR["Open Banking Affordability<br/>[TrueLayer]"]
    end
  end

  SYS_POSFIN_API -->|"HTTPS"| SYS_OBAFF_GATEWAY
  SYS_OBAFF_GATEWAY -->|"HTTPS"| SYS_OBAFF_EGRESS
  SYS_OBAFF_EGRESS -->|"PrivateLink"| SYS_OBAFF_VENDOR
  SYS_OBAFF_VENDOR -->|"HTTPS"| SYS_OBAFF_WEBHOOKS
  SYS_OBAFF_WEBHOOKS -->|"HTTPS"| SYS_POSFIN_API
  SYS_OBAFF_GATEWAY -.->|"runs on"| TS_GCP_GKE
  SYS_OBAFF_GATEWAY -.->|"runs on"| TS_GCP_APIGEE
  SYS_OBAFF_EGRESS -.->|"runs on"| TS_GCP_PSC
  SYS_OBAFF_EGRESS -.->|"runs on"| TS_GCP_NCC
  SYS_OBAFF_WEBHOOKS -.->|"runs on"| TS_GCP_APIGEE
  SYS_OBAFF_WEBHOOKS -.->|"runs on"| TS_GCP_GKE
  SYS_OBAFF_GATEWAY -.->|"runs on"| TS_GCP_SECRET_MANAGER
  SYS_POSFIN_API -.->|"runs on"| TS_GCP_APIGEE
  SYS_POSFIN_API -.->|"runs on"| TS_GCP_GKE
  SYS_POSFIN_API -.->|"runs on"| TS_GCP_SECRET_MANAGER

  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class SYS_OBAFF_EGRESS,SYS_OBAFF_GATEWAY,SYS_OBAFF_VENDOR,SYS_OBAFF_WEBHOOKS,SYS_POSFIN_API s_systems__systems;
  class TS_GCP_APIGEE,TS_GCP_GKE,TS_GCP_NCC,TS_GCP_PSC,TS_GCP_SECRET_MANAGER s_tech_services__tech_services;
  classDef boundary1 fill:#f1f6ff,stroke:#4285f4,color:#1a4f9e;
  class grp_GCP__gcp_lending_prod__Public,grp_GCP__gcp_lending_prod__Private_App,grp_GCP__gcp_lending_prod__Shared_Services,grp_GCP__gcp_shared_network__Shared_Services boundary1;
  classDef boundary2 fill:#f8fbff,stroke:#4285f4,color:#1a4f9e,stroke-dasharray:6 3;
  class grp_GCP__gcp_lending_prod,grp_GCP__gcp_shared_network boundary2;
  classDef boundary3 fill:#f8fbff,stroke:#4285f4,color:#1a4f9e;
  class grp_GCP boundary3;
  classDef boundary4 fill:#fcfbf7,stroke:#9a8f6a,color:#6b6246,stroke-dasharray:6 3;
  class grp_SaaS,grp_SaaS__Edge boundary4;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Open Banking Affordability — Architecture](../svg/product-architecture--prd-ob-affordability.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#4338ca` | systems |
| `#c2410c` | tech services |

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#4285f4` | GCP |
| dashed `#9a8f6a` | SaaS |
| dashed `#4285f4` | GCP project |
| dashed `#9a8f6a` | vendor tenancy |
| solid `#4285f4` | GCP subnet |

10 entities, 15 relationships. Generated from the model; edit the model, not this file.
