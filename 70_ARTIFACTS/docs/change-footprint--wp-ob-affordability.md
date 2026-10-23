# Buy affordability data for point-of-sale finance — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Buy affordability data for point-of-sale finance — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_System["System"]
    direction LR
    SYS_OBAFF_VENDOR["Open Banking Affordability<br/>[TrueLayer]"]
    SYS_OBAFF_GATEWAY["Open Banking Affordability<br/>Integration Gateway<br/>[GKE]"]
    SYS_OBAFF_EGRESS["Open Banking Affordability<br/>Private Egress"]
    SYS_OBAFF_WEBHOOKS["Open Banking Affordability<br/>Webhook Listener<br/>[GKE]"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_OB_AFFORDABILITY["Buy affordability data for<br/>point-of-sale finance"]
  end

  WP_OB_AFFORDABILITY -->|"Builds"| SYS_OBAFF_VENDOR
  WP_OB_AFFORDABILITY -->|"Builds"| SYS_OBAFF_GATEWAY
  WP_OB_AFFORDABILITY -->|"Builds"| SYS_OBAFF_EGRESS
  WP_OB_AFFORDABILITY -->|"Builds"| SYS_OBAFF_WEBHOOKS

  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class SYS_OBAFF_EGRESS,SYS_OBAFF_GATEWAY,SYS_OBAFF_VENDOR,SYS_OBAFF_WEBHOOKS s_systems__systems;
  class WP_OB_AFFORDABILITY s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Buy affordability data for point-of-sale finance — Footprint](../svg/change-footprint--wp-ob-affordability.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#4338ca` | systems |
| `#0d9488` | work packages |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
