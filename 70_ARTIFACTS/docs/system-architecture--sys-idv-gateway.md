# Identity Document Verification Integration Gateway — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Identity Document Verification Integration Gateway — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_System["System"]
    direction LR
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
    SYS_IDV_GATEWAY["Identity Document<br/>Verification Integration<br/>Gateway<br/>[AKS]"]
    SYS_IDV_EGRESS["Identity Document<br/>Verification Private<br/>Egress"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
    TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
    TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
    TS_AZURE_PRIVATELINK[/"Azure Private Link<br/>[Private egress]"/]
    TS_AZURE_VWAN[/"Azure Virtual WAN hub<br/>[Transit hub]"/]
    TS_IDENTITY_DNS[/"Customer Identity Service<br/>DNS<br/>[Azure DNS]"/]
    TS_IDENTITY_WAF[/"Customer Identity Service<br/>Web application firewall<br/>[Azure WAF]"/]
  end

  SYS_IDENTITY_SVC -->|"HTTPS"| SYS_IDV_GATEWAY
  SYS_IDV_GATEWAY -->|"HTTPS"| SYS_IDV_EGRESS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_DNS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_WAF
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_APIM
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_AKS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_KEYVAULT
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_AKS
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_APIM
  SYS_IDV_EGRESS -.->|"runs on"| TS_AZURE_PRIVATELINK
  SYS_IDV_EGRESS -.->|"runs on"| TS_AZURE_VWAN
  SYS_IDV_GATEWAY -.->|"runs on"| TS_AZURE_KEYVAULT

  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class SYS_IDENTITY_SVC,SYS_IDV_EGRESS,SYS_IDV_GATEWAY s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_AZURE_PRIVATELINK,TS_AZURE_VWAN,TS_IDENTITY_DNS,TS_IDENTITY_WAF s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Identity Document Verification Integration Gateway — Architecture](../svg/system-architecture--sys-idv-gateway.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#4338ca` | systems |
| `#c2410c` | tech services |

10 entities, 12 relationships. Generated from the model; edit the model, not this file.
