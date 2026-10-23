# NICE Actimize Screening Integration Gateway — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% NICE Actimize Screening Integration Gateway — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CARD_ACCOUNT[("Card account master")]
    DA_TRANSACTION[("Card transaction history")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_SCREENING_GATEWAY["NICE Actimize Screening<br/>Integration Gateway<br/>[EKS]"]
    SYS_SCREENING_EGRESS["NICE Actimize Screening<br/>Private Egress"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AWS_APIGW[/"Amazon API Gateway<br/>[API gateway]"/]
    TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
    TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
    TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
    TS_AWS_SECRETS[/"AWS Secrets Manager<br/>[Secrets manager]"/]
    TS_AWS_TGW[/"AWS Transit Gateway<br/>[Transit hub]"/]
    TS_ONPREM_DC[/"Primary Data Center<br/>[Virtual network]"/]
    TS_NET_VPC_RISKOPS[/"Risk Operations VPC<br/>[Virtual network]"/]
    TS_NET_VPC_SHARED[/"Shared Services VPC<br/>[Virtual network]"/]
  end

  SYS_AUTH_SWITCH -->|"HTTPS"| SYS_SCREENING_GATEWAY
  SYS_SCREENING_GATEWAY -->|"HTTPS"| SYS_SCREENING_EGRESS
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_AWS_EKS
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_AWS_APIGW
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_AWS_TGW
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_AWS_SECRETS
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_NET_VPC_RISKOPS
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_NET_VPC_SHARED
  SYS_AUTH_SWITCH -.->|"runs on"| TS_ONPREM_DC
  SYS_AUTH_SWITCH -->|"Read"| DA_CARD_ACCOUNT
  SYS_AUTH_SWITCH -->|"ReadWrite"| DA_TRANSACTION

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_CARD_ACCOUNT,DA_TRANSACTION s_data_assets__data_assets;
  class SYS_AUTH_SWITCH,SYS_SCREENING_EGRESS,SYS_SCREENING_GATEWAY s_systems__systems;
  class TS_AWS_APIGW,TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_PRIVATELINK,TS_AWS_SECRETS,TS_AWS_TGW,TS_NET_VPC_RISKOPS,TS_NET_VPC_SHARED,TS_ONPREM_DC s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![NICE Actimize Screening Integration Gateway — Architecture](../svg/system-architecture--sys-screening-gateway.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Card Authorization**: A card presented at a merchant, authorized or declined inside the scheme timeout. The tightest latency budget in the estate, and the reason the screening call has a circuit breaker rather than a retry.

1. Authorization Switch → NICE Actimize Screening Integration Gateway (HTTPS)
2. NICE Actimize Screening Integration Gateway → NICE Actimize Screening Private Egress (HTTPS)
3. NICE Actimize Screening Private Egress → NICE Actimize Screening (PrivateLink) — not on this diagram
4. Authorization Switch → Core Card Ledger (MQ) — not on this diagram

14 entities, 13 relationships. Generated from the model; edit the model, not this file.
