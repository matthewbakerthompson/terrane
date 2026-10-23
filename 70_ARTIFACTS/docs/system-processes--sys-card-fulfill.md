# Card production and fulfillment — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Card production and fulfillment — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_ORIG_07{{"Card Production &<br/>Fulfillment"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_ORIG_007[\"Manage card production and<br/>fulfillment"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARD_FULFILL["Card production and<br/>fulfillment<br/>[external]"]
  end

  P_ORIG_007 -->|"Primary"| SYS_CARD_FULFILL
  P_ORIG_007 -->|"supports"| CAP_ORIG_07

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_ORIG_07 s_capabilities__capabilities;
  class P_ORIG_007 s_processes__processes;
  class SYS_CARD_FULFILL s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card production and fulfillment — Processes and Capabilities](../svg/system-processes--sys-card-fulfill.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

3 entities, 2 relationships. Generated from the model; edit the model, not this file.
