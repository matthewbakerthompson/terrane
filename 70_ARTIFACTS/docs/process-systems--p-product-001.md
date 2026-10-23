# Design and approve product change — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Design and approve product change — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PROD_02{{"Pricing, Fee & APR<br/>Management"}}
    CAP_PROD_01{{"Product Design &<br/>Configuration"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_PRODUCT_001[\"Design and approve product<br/>change"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_WORKTRACK["Work and change tracking<br/>[SaaS]"]
  end

  P_PRODUCT_001 -->|"Primary"| SYS_CORE_LEDGER
  P_PRODUCT_001 -->|"Supporting"| SYS_WORKTRACK
  P_PRODUCT_001 -->|"supports"| CAP_PROD_01
  P_PRODUCT_001 -->|"supports"| CAP_PROD_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PROD_01,CAP_PROD_02 s_capabilities__capabilities;
  class P_PRODUCT_001 s_processes__processes;
  class SYS_CORE_LEDGER,SYS_WORKTRACK s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Design and approve product change — Systems, Data and Controls](../svg/process-systems--p-product-001.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
