# NICE Actimize Screening — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% NICE Actimize Screening — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_DISPUTES_VENDOR_FEED[("Dispute Management<br/>Platform vendor feed")]
    DA_MODEL_FEAT[("Model feature store")]
    DA_SCREENING_OUTCOMES[("NICE Actimize Screening<br/>outcomes")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
    SYS_SCREENING_FEDERATION["NICE Actimize Screening<br/>Identity Federation"]
    SYS_SCREENING_EGRESS["NICE Actimize Screening<br/>Private Egress"]
    SYS_SIEM["Security Monitoring<br/>[Microsoft Sentinel]"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
    TS_AWS_TGW[/"AWS Transit Gateway<br/>[Transit hub]"/]
    TS_AZURE_SERVICEBUS[/"Azure Service Bus<br/>[Message queue]"/]
    TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
    TS_NET_VPC_SHARED[/"Shared Services VPC<br/>[Virtual network]"/]
    TS_SNOWFLAKE[/"Snowflake<br/>[Data warehouse]"/]
  end

  SYS_SCREENING_FEDERATION -->|"SAML"| SYS_SCREENING_VENDOR
  SYS_SCREENING_VENDOR -->|"HTTPS"| SYS_SIEM
  SYS_SCREENING_EGRESS -->|"PrivateLink"| SYS_SCREENING_VENDOR
  SYS_SCREENING_VENDOR -->|"SFTP"| SYS_DATA_INGEST
  SYS_SCREENING_FEDERATION -.->|"runs on"| TS_ENTRA_ID
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_AWS_TGW
  SYS_DATA_INGEST -.->|"runs on"| TS_AZURE_SERVICEBUS
  SYS_DATA_INGEST -.->|"runs on"| TS_SNOWFLAKE
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_NET_VPC_SHARED
  SYS_DATA_INGEST -->|"Read"| DA_DISPUTES_VENDOR_FEED
  SYS_SCREENING_VENDOR -->|"Write"| DA_SCREENING_OUTCOMES
  SYS_DATA_INGEST -->|"Read"| DA_SCREENING_OUTCOMES
  SYS_DATA_INGEST -->|"ReadWrite"| DA_MODEL_FEAT

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_DISPUTES_VENDOR_FEED,DA_MODEL_FEAT,DA_SCREENING_OUTCOMES s_data_assets__data_assets;
  class SYS_DATA_INGEST,SYS_SCREENING_EGRESS,SYS_SCREENING_FEDERATION,SYS_SCREENING_VENDOR,SYS_SIEM s_systems__systems;
  class TS_AWS_PRIVATELINK,TS_AWS_TGW,TS_AZURE_SERVICEBUS,TS_ENTRA_ID,TS_NET_VPC_SHARED,TS_SNOWFLAKE s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![NICE Actimize Screening — Architecture](../svg/system-architecture--sys-screening-vendor.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Card Authorization**: A card presented at a merchant, authorized or declined inside the scheme timeout. The tightest latency budget in the estate, and the reason the screening call has a circuit breaker rather than a retry.

1. Authorization Switch → NICE Actimize Screening Integration Gateway (HTTPS) — not on this diagram
2. NICE Actimize Screening Integration Gateway → NICE Actimize Screening Private Egress (HTTPS) — not on this diagram
3. NICE Actimize Screening Private Egress → NICE Actimize Screening (PrivateLink)
4. Authorization Switch → Core Card Ledger (MQ) — not on this diagram

14 entities, 14 relationships. Generated from the model; edit the model, not this file.
