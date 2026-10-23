# Assemble the merchant portal on Azure — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Assemble the merchant portal on Azure — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_MERCHANT_OPERATIONAL[("Merchant Portal<br/>operational data")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_MERCHANT_STORE["Merchant Portal Database<br/>[Azure SQL]"]
    SYS_MERCHANT_EVENTS["Merchant Portal Event<br/>Publisher<br/>[Service Bus]"]
    SYS_MERCHANT_API["Merchant Portal Service<br/>[AKS · Merchant Portal Cache]"]
    SYS_MERCHANT_WEB["Merchant Portal Web<br/>[AKS]"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_MERCHANT_PORTAL["Assemble the merchant<br/>portal on Azure"]
  end

  WP_MERCHANT_PORTAL -->|"Builds"| SYS_MERCHANT_WEB
  WP_MERCHANT_PORTAL -->|"Builds"| SYS_MERCHANT_API
  WP_MERCHANT_PORTAL -->|"Builds"| SYS_MERCHANT_STORE
  WP_MERCHANT_PORTAL -->|"Builds"| SYS_MERCHANT_EVENTS
  SYS_MERCHANT_API -->|"ReadWrite"| DA_MERCHANT_OPERATIONAL

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class DA_MERCHANT_OPERATIONAL s_data_assets__data_assets;
  class SYS_MERCHANT_API,SYS_MERCHANT_EVENTS,SYS_MERCHANT_STORE,SYS_MERCHANT_WEB s_systems__systems;
  class WP_MERCHANT_PORTAL s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Assemble the merchant portal on Azure — Footprint](../svg/change-footprint--wp-merchant-portal.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#0d9488` | work packages |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
