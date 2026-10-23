# Identity Document Verification — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Identity Document Verification — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_System["System"]
    direction LR
    SYS_IDV_VENDOR["Identity Document<br/>Verification<br/>[Onfido]"]
    SYS_IDV_EGRESS["Identity Document<br/>Verification Private<br/>Egress"]
    SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_PRIVATELINK[/"Azure Private Link<br/>[Private egress]"/]
    TS_AZURE_VWAN[/"Azure Virtual WAN hub<br/>[Transit hub]"/]
  end

  SYS_IDV_EGRESS -->|"PrivateLink"| SYS_IDV_VENDOR
  SYS_IDV_VENDOR -->|"HTTPS"| SYS_IDV_WEBHOOKS
  SYS_IDV_EGRESS -.->|"runs on"| TS_AZURE_PRIVATELINK
  SYS_IDV_EGRESS -.->|"runs on"| TS_AZURE_VWAN
  SYS_IDV_WEBHOOKS -.->|"runs on"| TS_AZURE_APIM
  SYS_IDV_WEBHOOKS -.->|"runs on"| TS_AZURE_AKS

  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class SYS_IDV_EGRESS,SYS_IDV_VENDOR,SYS_IDV_WEBHOOKS s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_PRIVATELINK,TS_AZURE_VWAN s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Identity Document Verification — Architecture](../svg/system-architecture--sys-idv-vendor.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#4338ca` | systems |
| `#c2410c` | tech services |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
