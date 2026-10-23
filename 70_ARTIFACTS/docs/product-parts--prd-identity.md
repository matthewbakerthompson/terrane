# Customer Identity Service — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Customer Identity Service — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  TS_AZURE_APIM[/"Azure API Management<br/>[API gateway]"/]
  TS_AZURE_KEYVAULT[/"Azure Key Vault<br/>[Secrets manager]"/]
  TS_AZURE_AKS[/"Azure Kubernetes Service<br/>[Container platform]"/]
  SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
  TS_IDENTITY_DNS[/"Customer Identity Service<br/>DNS<br/>[Azure DNS]"/]
  TS_IDENTITY_WAF[/"Customer Identity Service<br/>Web application firewall<br/>[Azure WAF]"/]

  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_DNS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_IDENTITY_WAF
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_APIM
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_AKS
  SYS_IDENTITY_SVC -.->|"runs on"| TS_AZURE_KEYVAULT

  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class SYS_IDENTITY_SVC s_systems__systems;
  class TS_AZURE_AKS,TS_AZURE_APIM,TS_AZURE_KEYVAULT,TS_IDENTITY_DNS,TS_IDENTITY_WAF s_tech_services__tech_services;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Customer Identity Service — By part](../svg/product-parts--prd-identity.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#4338ca` | systems |
| `#c2410c` | tech services |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
