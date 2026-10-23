# Treasury management — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Treasury management — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_FIN_06{{"Cash & Settlement<br/>Reconciliation"}}
    CAP_FIN_03{{"Funding & Liquidity<br/>Management"}}
    CAP_PAY_05{{"Network Settlement &<br/>Interchange"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SETTLEMENT_001[\"Fund daily network<br/>settlement position"/]
    P_FUNDING_001[\"Manage daily funding<br/>position"/]
    P_SETTLEMENT_002[\"Reconcile cash and<br/>suspense accounts"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_TREASURY["Treasury management"]
  end

  P_SETTLEMENT_001 -->|"Supporting"| SYS_TREASURY
  P_SETTLEMENT_002 -->|"Supporting"| SYS_TREASURY
  P_FUNDING_001 -->|"Primary"| SYS_TREASURY
  P_SETTLEMENT_001 -->|"supports"| CAP_PAY_05
  P_SETTLEMENT_001 -->|"supports"| CAP_FIN_03
  P_SETTLEMENT_002 -->|"supports"| CAP_FIN_06
  P_FUNDING_001 -->|"supports"| CAP_FIN_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_FIN_03,CAP_FIN_06,CAP_PAY_05 s_capabilities__capabilities;
  class P_FUNDING_001,P_SETTLEMENT_001,P_SETTLEMENT_002 s_processes__processes;
  class SYS_TREASURY s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Treasury management — Processes and Capabilities](../svg/system-processes--sys-treasury.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 7 relationships. Generated from the model; edit the model, not this file.
