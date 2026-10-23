# NICE Actimize Screening — Onboarding

What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart TB
  %% NICE Actimize Screening — Onboarding
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_AWS["AWS"]
    direction TB
    subgraph grp_AWS__prod_riskops["account prod-riskops"]
      direction TB
      subgraph grp_AWS__prod_riskops__eu_west_2["region eu-west-2"]
        direction TB
        subgraph grp_AWS__prod_riskops__eu_west_2__Private_App["Private-App"]
          direction TB
          SYS_SCREENING_GATEWAY["NICE Actimize Screening<br/>Integration Gateway<br/>[EKS]"]
        end
        subgraph grp_AWS__prod_riskops__eu_west_2__Shared_Services["Shared-Services"]
          direction TB
          SYS_SCREENING_FEDERATION["NICE Actimize Screening<br/>Identity Federation"]
          SYS_SCREENING_EGRESS["NICE Actimize Screening<br/>Private Egress"]
        end
      end
    end
  end

  subgraph grp_Azure["Azure"]
    direction TB
    subgraph grp_Azure__azure_data_prod["subscription azure-data-prod"]
      direction TB
      subgraph grp_Azure__azure_data_prod__uksouth["region uksouth"]
        direction TB
        subgraph grp_Azure__azure_data_prod__uksouth__Private_Data["Private-Data"]
          direction TB
          SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
        end
      end
    end
  end

  subgraph grp_On_prem["On-prem"]
    direction TB
    SYS_AUTH_SWITCH["Authorization Switch"]
  end

  subgraph grp_SaaS["SaaS"]
    direction TB
    subgraph grp_SaaS__Edge["Edge"]
      direction TB
      SYS_SIEM["Security Monitoring<br/>[Microsoft Sentinel]"]
    end
    subgraph grp_SaaS__eu_west_1["region eu-west-1"]
      direction TB
      subgraph grp_SaaS__eu_west_1__Edge["Edge"]
        direction TB
        SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
      end
    end
  end

  SYS_AUTH_SWITCH -->|"HTTPS"| SYS_SCREENING_GATEWAY
  SYS_SCREENING_FEDERATION -->|"SAML"| SYS_SCREENING_VENDOR
  SYS_SCREENING_VENDOR -->|"HTTPS"| SYS_SIEM
  SYS_SCREENING_GATEWAY -->|"HTTPS"| SYS_SCREENING_EGRESS
  SYS_SCREENING_EGRESS -->|"PrivateLink"| SYS_SCREENING_VENDOR
  SYS_SCREENING_VENDOR -->|"SFTP"| SYS_DATA_INGEST

  classDef s_systems__edge fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__on_prem fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_app fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__private_data fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__shared_services fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class SYS_SCREENING_VENDOR,SYS_SIEM s_systems__edge;
  class SYS_AUTH_SWITCH s_systems__on_prem;
  class SYS_SCREENING_GATEWAY s_systems__private_app;
  class SYS_DATA_INGEST s_systems__private_data;
  class SYS_SCREENING_EGRESS,SYS_SCREENING_FEDERATION s_systems__shared_services;
  classDef boundary1 fill:#eef5fb,stroke:#147eba,color:#0f5f8c;
  class grp_AWS__prod_riskops__eu_west_2__Private_App boundary1;
  classDef boundary2 fill:#f1f6fb,stroke:#5b9bd5,color:#2f5d8a;
  class grp_Azure__azure_data_prod__uksouth__Private_Data boundary2;
  classDef boundary3 fill:#f4f0ff,stroke:#8c4fff,color:#5b2fb0;
  class grp_AWS__prod_riskops__eu_west_2__Shared_Services boundary3;
  classDef boundary4 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary4;
  classDef boundary5 fill:#f5fbfb,stroke:#00a4a6,color:#0b6e70,stroke-dasharray:6 3;
  class grp_AWS__prod_riskops__eu_west_2 boundary5;
  classDef boundary6 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a,stroke-dasharray:6 3;
  class grp_Azure__azure_data_prod boundary6;
  classDef boundary7 fill:#f7fbfe,stroke:#0078d4,color:#1b4b7a;
  class grp_Azure boundary7;
  classDef boundary8 fill:#f8fafc,stroke:#7a8699,color:#4b5563,stroke-dasharray:2 3;
  class grp_Azure__azure_data_prod__uksouth boundary8;
  classDef boundary9 fill:#f8fafc,stroke:#8f9bb5,color:#3b4a6b,stroke-dasharray:6 3;
  class grp_SaaS__eu_west_1 boundary9;
  classDef boundary10 fill:#fbfcfd,stroke:#232f3e,color:#232f3e;
  class grp_AWS boundary10;
  classDef boundary11 fill:#fcfbf7,stroke:#9a8f6a,color:#6b6246,stroke-dasharray:6 3;
  class grp_SaaS,grp_SaaS__Edge,grp_SaaS__eu_west_1__Edge boundary11;
  classDef boundary12 fill:#fdf6fa,stroke:#c7257e,color:#8b1a58;
  class grp_AWS__prod_riskops boundary12;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![NICE Actimize Screening — Onboarding](../svg/onboarding--prd-screening.svg)

**network zone** is the boundary each node sits in.

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#232f3e` | AWS |
| solid `#0078d4` | Azure |
| solid `#5f6b7a` | On-prem |
| dashed `#9a8f6a` | SaaS |
| solid `#c7257e` | AWS account |
| dashed `#0078d4` | Azure subscription |
| dashed `#9a8f6a` | vendor tenancy |
| dashed `#8f9bb5` | SaaS region |
| dashed `#00a4a6` | AWS region |
| dotted `#7a8699` | Azure region |
| solid `#147eba` | private subnet |
| solid `#8c4fff` | shared services |
| solid `#5b9bd5` | Azure subnet |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Card Authorization**: A card presented at a merchant, authorized or declined inside the scheme timeout. The tightest latency budget in the estate, and the reason the screening call has a circuit breaker rather than a retry.

1. Authorization Switch → NICE Actimize Screening Integration Gateway (HTTPS)
2. NICE Actimize Screening Integration Gateway → NICE Actimize Screening Private Egress (HTTPS)
3. NICE Actimize Screening Private Egress → NICE Actimize Screening (PrivateLink)
4. Authorization Switch → Core Card Ledger (MQ) — not on this diagram

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
