# Dispute Management — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Dispute Management — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_api_outbound["api-outbound"]
    direction LR
    SYS_DISPUTES_GATEWAY["Dispute Management<br/>Platform Integration<br/>Gateway<br/>[AKS]"]
  end

  subgraph grp_sftp_return_feed["sftp-return-feed"]
    direction LR
    DA_DISPUTES_VENDOR_FEED[("Dispute Management<br/>Platform vendor feed")]
  end

  subgraph grp_vendor_tenancy["vendor-tenancy"]
    direction LR
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
  end

  TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
  TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
  TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]

  SYS_DISPUTES_GATEWAY -->|"HTTPS"| SYS_DISPUTES_SAAS
  SYS_DISPUTES_GATEWAY -.->|"runs on"| TS_AZURE_AKS
  SYS_DISPUTES_GATEWAY -.->|"runs on"| TS_AZURE_APIM
  SYS_DISPUTES_GATEWAY -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_DISPUTES_SAAS -->|"Write"| DA_DISPUTES_VENDOR_FEED

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_DISPUTES_VENDOR_FEED s_data_assets__data_assets;
  class SYS_DISPUTES_GATEWAY,SYS_DISPUTES_SAAS s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_api_outbound,grp_sftp_return_feed,grp_vendor_tenancy boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Dispute Management — By part](../svg/product-parts--prd-disputes.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Dispute and Chargeback**: A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

1. Dynamics 365 Customer Service → Core Card Ledger (HTTPS) — not on this diagram
2. Core Card Ledger → Dispute Management Platform Integration Gateway (HTTPS) — not on this diagram
3. Dispute Management Platform Integration Gateway → Pega Smart Dispute (HTTPS)
4. Pega Smart Dispute → Enterprise Data Ingestion Hub (SFTP) — not on this diagram

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
