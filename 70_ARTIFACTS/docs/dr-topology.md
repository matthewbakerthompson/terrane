# Disaster Recovery Topology

Primary and recovery regions side by side, with the replication paths between them. Anything in the primary region with no connection to the recovery region would not survive a regional outage.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Disaster Recovery Topology
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_AWS["AWS"]
    direction LR
    subgraph grp_AWS__eu_west_1["region eu-west-1"]
      direction LR
      TS_NET_VPC_LENDING_DR[/"Lending VPC (DR)<br/>[Virtual network]"/]
    end
    subgraph grp_AWS__eu_west_2["region eu-west-2"]
      direction LR
      TS_AWS_PRIVATELINK[/"AWS PrivateLink<br/>[Private egress]"/]
      TS_AWS_TGW[/"AWS Transit Gateway<br/>[Transit hub]"/]
      TS_NET_DX[/"Direct Connect<br/>[Hybrid link]"/]
      TS_NET_SUB_LEND_APP_A[/"Lending App Subnet A<br/>[Subnet]"/]
      TS_NET_SUB_LEND_APP_B[/"Lending App Subnet B<br/>[Subnet]"/]
      TS_NET_SUB_LEND_DATA_A[/"Lending Data Subnet A<br/>[Subnet]"/]
      TS_NET_SUB_LEND_DATA_B[/"Lending Data Subnet B<br/>[Subnet]"/]
      TS_NET_SUB_LEND_PUB_A[/"Lending Public Subnet A<br/>[Subnet]"/]
      TS_NET_SUB_LEND_PUB_B[/"Lending Public Subnet B<br/>[Subnet]"/]
      TS_NET_VPC_LENDING[/"Lending VPC<br/>[Virtual network]"/]
      TS_NET_VPC_RISKOPS[/"Risk Operations VPC<br/>[Virtual network]"/]
      TS_NET_ROUTE53[/"Route 53 Resolver<br/>[DNS]"/]
      TS_NET_VPC_SHARED[/"Shared Services VPC<br/>[Virtual network]"/]
      TS_NET_VPN[/"Site-to-Site VPN<br/>[Hybrid link]"/]
    end
  end

  subgraph grp_GCP["GCP"]
    direction LR
    subgraph grp_GCP__europe_west1["region europe-west1"]
      direction LR
      TS_GCPNET_SUB_ANALYTICS_DATA_DR[/"Analytics Data Subnetwork<br/>(DR)<br/>[Subnet]"/]
      TS_GCPNET_SUB_LEND_APP_DR[/"Lending App Subnetwork<br/>(DR)<br/>[Subnet]"/]
    end
    subgraph grp_GCP__europe_west2["region europe-west2"]
      direction LR
      TS_GCPNET_SUB_ANALYTICS_DATA[/"Analytics Data Subnetwork<br/>[Subnet]"/]
      TS_GCP_CLOUD_DNS[/"Cloud DNS<br/>[DNS]"/]
      TS_GCP_INTERCONNECT[/"Cloud Interconnect<br/>[Hybrid link]"/]
      TS_GCPNET_HA_VPN[/"HA VPN<br/>[Hybrid link]"/]
      TS_GCPNET_SUB_LEND_APP[/"Lending App Subnetwork<br/>[Subnet]"/]
      TS_GCPNET_SUB_LEND_DATA[/"Lending Data Subnetwork<br/>[Subnet]"/]
      TS_GCPNET_PROXY_SUB_LEND[/"Lending Proxy-only<br/>Subnetwork<br/>[Subnet]"/]
      TS_GCP_NCC[/"Network Connectivity<br/>Center<br/>[Transit hub]"/]
      TS_GCP_SHARED_VPC[/"Shared VPC network<br/>[Virtual network]"/]
    end
  end

  subgraph grp_On_prem["On-prem"]
    direction LR
    TS_ONPREM_DC[/"Primary Data Center<br/>[Virtual network]"/]
  end

  TS_NET_DX -->|"Direct Connect"| TS_ONPREM_DC
  TS_NET_VPN -->|"IPsec backup"| TS_ONPREM_DC
  TS_AWS_TGW -->|"DX gateway"| TS_NET_DX
  TS_AWS_TGW -->|"VPN attachment"| TS_NET_VPN
  TS_AWS_TGW -->|"VPC attachment"| TS_NET_VPC_SHARED
  TS_AWS_TGW -->|"VPC attachment"| TS_NET_VPC_LENDING
  TS_AWS_TGW -->|"VPC attachment"| TS_NET_VPC_RISKOPS
  TS_AWS_TGW -->|"VPC attachment (DR)"| TS_NET_VPC_LENDING_DR
  TS_NET_VPC_SHARED -->|"resolver endpoints"| TS_NET_ROUTE53
  TS_NET_VPC_SHARED -->|"endpoint services"| TS_AWS_PRIVATELINK
  TS_NET_VPC_LENDING -->|"subnet"| TS_NET_SUB_LEND_PUB_A
  TS_NET_VPC_LENDING -->|"subnet"| TS_NET_SUB_LEND_PUB_B
  TS_NET_VPC_LENDING -->|"subnet"| TS_NET_SUB_LEND_APP_A
  TS_NET_VPC_LENDING -->|"subnet"| TS_NET_SUB_LEND_APP_B
  TS_NET_VPC_LENDING -->|"subnet"| TS_NET_SUB_LEND_DATA_A
  TS_NET_VPC_LENDING -->|"subnet"| TS_NET_SUB_LEND_DATA_B
  TS_NET_VPC_LENDING -->|"cross-region replication"| TS_NET_VPC_LENDING_DR
  TS_GCP_INTERCONNECT -->|"Dedicated Interconnect"| TS_ONPREM_DC
  TS_GCPNET_HA_VPN -->|"IPsec backup"| TS_ONPREM_DC
  TS_GCP_NCC -->|"VLAN attachment"| TS_GCP_INTERCONNECT
  TS_GCP_NCC -->|"VPN spoke"| TS_GCPNET_HA_VPN
  TS_GCP_NCC -->|"VPC spoke"| TS_GCP_SHARED_VPC
  TS_GCP_SHARED_VPC -->|"DNS peering"| TS_GCP_CLOUD_DNS
  TS_GCP_CLOUD_DNS -->|"forwarding zone"| TS_ONPREM_DC
  TS_GCP_SHARED_VPC -->|"subnetwork"| TS_GCPNET_PROXY_SUB_LEND
  TS_GCP_SHARED_VPC -->|"subnetwork"| TS_GCPNET_SUB_LEND_APP
  TS_GCP_SHARED_VPC -->|"subnetwork"| TS_GCPNET_SUB_LEND_DATA
  TS_GCP_SHARED_VPC -->|"subnetwork (DR)"| TS_GCPNET_SUB_LEND_APP_DR
  TS_GCP_SHARED_VPC -->|"subnetwork"| TS_GCPNET_SUB_ANALYTICS_DATA
  TS_GCP_SHARED_VPC -->|"subnetwork (DR)"| TS_GCPNET_SUB_ANALYTICS_DATA_DR

  classDef s_tech_services__active fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__planned fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px,stroke-dasharray:6 3;
  class TS_AWS_PRIVATELINK,TS_AWS_TGW,TS_GCP_CLOUD_DNS,TS_GCP_INTERCONNECT,TS_GCP_NCC,TS_GCP_SHARED_VPC,TS_GCPNET_HA_VPN,TS_GCPNET_PROXY_SUB_LEND,TS_GCPNET_SUB_ANALYTICS_DATA,TS_GCPNET_SUB_ANALYTICS_DATA_DR,TS_GCPNET_SUB_LEND_APP,TS_GCPNET_SUB_LEND_APP_DR,TS_GCPNET_SUB_LEND_DATA,TS_NET_DX,TS_NET_ROUTE53,TS_NET_SUB_LEND_APP_A,TS_NET_SUB_LEND_APP_B,TS_NET_SUB_LEND_DATA_A,TS_NET_SUB_LEND_DATA_B,TS_NET_SUB_LEND_PUB_A,TS_NET_SUB_LEND_PUB_B,TS_NET_VPC_LENDING,TS_NET_VPC_RISKOPS,TS_NET_VPC_SHARED,TS_NET_VPN,TS_ONPREM_DC s_tech_services__active;
  class TS_NET_VPC_LENDING_DR s_tech_services__planned;
  classDef boundary1 fill:#f4f5f7,stroke:#5f6b7a,color:#3f4a5c;
  class grp_On_prem boundary1;
  classDef boundary2 fill:#f5fbfb,stroke:#00a4a6,color:#0b6e70,stroke-dasharray:6 3;
  class grp_AWS__eu_west_1,grp_AWS__eu_west_2 boundary2;
  classDef boundary3 fill:#f8fafc,stroke:#5f6368,color:#3c4043,stroke-dasharray:2 3;
  class grp_GCP__europe_west1,grp_GCP__europe_west2 boundary3;
  classDef boundary4 fill:#f8fbff,stroke:#4285f4,color:#1a4f9e;
  class grp_GCP boundary4;
  classDef boundary5 fill:#fbfcfd,stroke:#232f3e,color:#232f3e;
  class grp_AWS boundary5;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Disaster Recovery Topology](../svg/dr-topology.svg)

**status** is drawn as the border style: solid for Active, dashed for Planned, dotted for Proposed, and faded for Deprecated and Retired.

**Boundaries** are drawn the way their provider draws them.

| Border | Boundary |
|---|---|
| solid `#232f3e` | AWS |
| solid `#4285f4` | GCP |
| solid `#5f6b7a` | On-prem |
| dashed `#00a4a6` | AWS region |
| dotted `#5f6368` | GCP region |

27 entities, 30 relationships. Generated from the model; edit the model, not this file.
