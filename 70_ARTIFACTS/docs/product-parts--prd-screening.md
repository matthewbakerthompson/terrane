# NICE Actimize Screening — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% NICE Actimize Screening — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_api_outbound["api-outbound"]
    direction LR
    SYS_SCREENING_GATEWAY["NICE Actimize Screening<br/>Integration Gateway<br/>[EKS]"]
  end

  subgraph grp_private_egress["private-egress"]
    direction LR
    SYS_SCREENING_EGRESS["NICE Actimize Screening<br/>Private Egress"]
  end

  subgraph grp_sftp_return_feed["sftp-return-feed"]
    direction LR
    DA_SCREENING_OUTCOMES[("NICE Actimize Screening<br/>outcomes")]
  end

  subgraph grp_sso_federation["sso-federation"]
    direction LR
    SYS_SCREENING_FEDERATION["NICE Actimize Screening<br/>Identity Federation"]
  end

  subgraph grp_vendor_tenancy["vendor-tenancy"]
    direction LR
    SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
  end

  TS_AWS_APIGW[/"Amazon API Gateway<br/>[API gateway]"/]
  TS_AWS_CLOUDWATCH[/"Amazon CloudWatch<br/>[Observability]"/]
  TS_AWS_EKS[/"Amazon EKS<br/>[Container platform]"/]
  TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
  TS_AWS_SECRETS[/"AWS Secrets Manager<br/>[Secrets manager]"/]
  TS_AWS_TGW[/"AWS Transit Gateway<br/>[Transit hub]"/]
  TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
  TS_NET_VPC_RISKOPS[/"Risk Operations VPC<br/>[Virtual network]"/]
  TS_NET_VPC_SHARED[/"Shared Services VPC<br/>[Virtual network]"/]

  SYS_SCREENING_FEDERATION -->|"SAML"| SYS_SCREENING_VENDOR
  SYS_SCREENING_GATEWAY -->|"HTTPS"| SYS_SCREENING_EGRESS
  SYS_SCREENING_EGRESS -->|"PrivateLink"| SYS_SCREENING_VENDOR
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_AWS_EKS
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_AWS_APIGW
  SYS_SCREENING_FEDERATION -.->|"runs on"| TS_ENTRA_ID
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_AWS_PRIVATELINK
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_AWS_TGW
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_AWS_SECRETS
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_AWS_CLOUDWATCH
  SYS_SCREENING_GATEWAY -.->|"runs on"| TS_NET_VPC_RISKOPS
  SYS_SCREENING_EGRESS -.->|"runs on"| TS_NET_VPC_SHARED
  SYS_SCREENING_VENDOR -->|"Write"| DA_SCREENING_OUTCOMES

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_SCREENING_OUTCOMES s_data_assets__data_assets;
  class SYS_SCREENING_EGRESS,SYS_SCREENING_FEDERATION,SYS_SCREENING_GATEWAY,SYS_SCREENING_VENDOR s_systems__systems;
  class TS_AWS_APIGW,TS_AWS_CLOUDWATCH,TS_AWS_EKS,TS_AWS_PRIVATELINK,TS_AWS_SECRETS,TS_AWS_TGW,TS_ENTRA_ID,TS_NET_VPC_RISKOPS,TS_NET_VPC_SHARED s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_api_outbound,grp_private_egress,grp_sftp_return_feed,grp_sso_federation,grp_vendor_tenancy boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![NICE Actimize Screening — By part](../svg/product-parts--prd-screening.svg)

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
2. NICE Actimize Screening Integration Gateway → NICE Actimize Screening Private Egress (HTTPS)
3. NICE Actimize Screening Private Egress → NICE Actimize Screening (PrivateLink)
4. Authorization Switch → Core Card Ledger (MQ) — not on this diagram

14 entities, 13 relationships. Generated from the model; edit the model, not this file.
