# Identity Document Verification — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Identity Document Verification — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_api_outbound["api-outbound"]
    direction LR
    SYS_IDV_GATEWAY["Identity Document<br/>Verification Integration<br/>Gateway<br/>[AKS]"]
  end

  subgraph grp_private_egress["private-egress"]
    direction LR
    SYS_IDV_EGRESS["Identity Document<br/>Verification Private<br/>Egress"]
  end

  subgraph grp_vendor_tenancy["vendor-tenancy"]
    direction LR
    SYS_IDV_VENDOR["Identity Document<br/>Verification<br/>[Onfido]"]
  end

  subgraph grp_webhook_inbound["webhook-inbound"]
    direction LR
    SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
  end

  TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
  TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
  TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
  TS_AZURE_PRIVATELINK[/"Azure Private Link<br/>[Private egress]"/]
  TS_AZURE_VWAN[/"Azure Virtual WAN hub<br/>[Transit hub]"/]

  SYS_IDV_GATEWAY -->|"HTTPS"| SYS_IDV_EGRESS
  SYS_IDV_EGRESS -->|"PrivateLink"| SYS_IDV_VENDOR
  SYS_IDV_VENDOR -->|"HTTPS"| SYS_IDV_WEBHOOKS
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_AKS
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_APIM
  SYS_IDV_EGRESS -.->|"runs on"| TS_AZURE_PRIVATELINK
  SYS_IDV_EGRESS -.->|"runs on"| TS_AZURE_VWAN
  SYS_IDV_WEBHOOKS -.->|"runs on"| TS_AZURE_APIM
  SYS_IDV_WEBHOOKS -.->|"runs on"| TS_AZURE_AKS
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_KEYVAULT

  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class SYS_IDV_EGRESS,SYS_IDV_GATEWAY,SYS_IDV_VENDOR,SYS_IDV_WEBHOOKS s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_PRIVATELINK,TS_AZURE_VWAN s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_api_outbound,grp_private_egress,grp_vendor_tenancy,grp_webhook_inbound boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Identity Document Verification — By part](../svg/product-parts--prd-idv.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#4338ca` | systems |
| `#c2410c` | tech services |

9 entities, 10 relationships. Generated from the model; edit the model, not this file.
