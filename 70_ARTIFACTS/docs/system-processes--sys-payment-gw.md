# Payment capture gateway — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Payment capture gateway — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_02{{"Account Maintenance &<br/>Servicing Requests"}}
    CAP_PAY_03{{"Payment Capture &<br/>Application"}}
    CAP_PAY_04{{"Returned Payment & NSF<br/>Handling"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_011[\"Administer secured card<br/>deposit lifecycle"/]
    P_CARD_PMT_001[\"Capture and apply<br/>cardholder payment"/]
    P_PAYMENTS_003[\"Process returned payment<br/>and assess NSF"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_PAYMENT_GW["Payment capture gateway"]
  end

  P_CARD_PMT_001 -->|"Primary"| SYS_PAYMENT_GW
  P_PAYMENTS_003 -->|"Primary"| SYS_PAYMENT_GW
  P_SERVICING_011 -->|"Supporting"| SYS_PAYMENT_GW
  P_CARD_PMT_001 -->|"supports"| CAP_PAY_03
  P_PAYMENTS_003 -->|"supports"| CAP_PAY_04
  P_SERVICING_011 -->|"supports"| CAP_SERV_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PAY_03,CAP_PAY_04,CAP_SERV_02 s_capabilities__capabilities;
  class P_CARD_PMT_001,P_PAYMENTS_003,P_SERVICING_011 s_processes__processes;
  class SYS_PAYMENT_GW s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Payment capture gateway — Processes and Capabilities](../svg/system-processes--sys-payment-gw.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
