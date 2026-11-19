# Repossession and remarketing management — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Repossession and remarketing management — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_LEND_06_02{{"Collateral Remarketing &<br/>Deficiency Recovery"}}
    CAP_LEND_06{{"Repossession & Asset<br/>Remarketing"}}
    CAP_LEND_06_01{{"Repossession & Redemption<br/>Notices"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_LENDING_012[\"Assign repossession and<br/>send required notices"/]
    P_LENDING_013[\"Remarket recovered<br/>collateral and pursue<br/>deficiency"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_REMARKET["Repossession and<br/>remarketing management<br/>[external]"]
  end

  P_LENDING_012 -->|"Primary"| SYS_REMARKET
  P_LENDING_013 -->|"Primary"| SYS_REMARKET
  P_LENDING_012 -->|"supports"| CAP_LEND_06_01
  P_LENDING_013 -->|"supports"| CAP_LEND_06_02
  P_LENDING_012 -->|"supports"| CAP_LEND_06
  P_LENDING_013 -->|"supports"| CAP_LEND_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_LEND_06,CAP_LEND_06_01,CAP_LEND_06_02 s_capabilities__capabilities;
  class P_LENDING_012,P_LENDING_013 s_processes__processes;
  class SYS_REMARKET s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Repossession and remarketing management — Processes and Capabilities](../svg/system-processes--sys-remarket.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

6 entities, 6 relationships. Generated from the model; edit the model, not this file.
