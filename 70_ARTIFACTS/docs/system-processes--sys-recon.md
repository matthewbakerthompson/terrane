# Reconciliation platform — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Reconciliation platform — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_DEP_03{{"Brokered CD Program<br/>Management"}}
    CAP_DEP_03_02{{"Brokered CD Settlement &<br/>Record Keeping"}}
    CAP_FIN_06{{"Cash & Settlement<br/>Reconciliation"}}
    CAP_DATA_02{{"Data Sourcing &<br/>Integration"}}
    CAP_FIN_01{{"General Ledger & Financial<br/>Close"}}
    CAP_FIN_02{{"Interchange & Revenue<br/>Accounting"}}
    CAP_MERCH_04_01{{"Merchant Funding"}}
    CAP_MERCH_04{{"Merchant Settlement &<br/>Funding"}}
    CAP_PAY_06{{"Network & Merchant<br/>Reconciliation"}}
    CAP_PAY_05{{"Network Settlement &<br/>Interchange"}}
    CAP_PAY_03{{"Payment Capture &<br/>Application"}}
    CAP_PAY_03_01{{"Payment Channel Capture"}}
    CAP_TPS_02{{"Portfolio Conversion &<br/>Deconversion"}}
    CAP_BILL_04{{"Rewards Earn, Accrual &<br/>Redemption"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_TPS_002[\"Convert client portfolio"/]
    P_GL_CLOSE_001[\"Execute monthly financial<br/>close"/]
    P_SETTLEMENT_003[\"Investigate and clear<br/>settlement exception"/]
    P_SETTLEMENT_004[\"Monitor and optimize<br/>interchange qualification"/]
    P_PAYMENTS_009[\"Process lockbox and check<br/>payments"/]
    P_SETTLEMENT_002[\"Reconcile cash and<br/>suspense accounts"/]
    P_NETWORK_RECON_001[\"Reconcile network<br/>settlement"/]
    P_REWARDS_003[\"Reconcile rewards<br/>liability"/]
    P_MERCHANT_006[\"Settle and fund merchants"/]
    P_DEPOSITS_004[\"Settle brokered CDs and<br/>keep the position"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_RECON["Reconciliation platform"]
  end

  P_NETWORK_RECON_001 -->|"Primary"| SYS_RECON
  P_SETTLEMENT_002 -->|"Primary"| SYS_RECON
  P_SETTLEMENT_003 -->|"Primary"| SYS_RECON
  P_REWARDS_003 -->|"Supporting"| SYS_RECON
  P_TPS_002 -->|"Supporting"| SYS_RECON
  P_GL_CLOSE_001 -->|"Supporting"| SYS_RECON
  P_SETTLEMENT_004 -->|"Supporting"| SYS_RECON
  P_MERCHANT_006 -->|"Supporting"| SYS_RECON
  P_DEPOSITS_004 -->|"Supporting"| SYS_RECON
  P_PAYMENTS_009 -->|"Supporting"| SYS_RECON
  P_NETWORK_RECON_001 -->|"supports"| CAP_PAY_06
  P_SETTLEMENT_002 -->|"supports"| CAP_FIN_06
  P_SETTLEMENT_003 -->|"supports"| CAP_PAY_06
  P_REWARDS_003 -->|"supports"| CAP_BILL_04
  P_REWARDS_003 -->|"supports"| CAP_FIN_02
  P_TPS_002 -->|"supports"| CAP_TPS_02
  P_TPS_002 -->|"supports"| CAP_DATA_02
  P_GL_CLOSE_001 -->|"supports"| CAP_FIN_01
  P_SETTLEMENT_004 -->|"supports"| CAP_PAY_05
  P_SETTLEMENT_004 -->|"supports"| CAP_FIN_02
  P_MERCHANT_006 -->|"supports"| CAP_MERCH_04_01
  P_DEPOSITS_004 -->|"supports"| CAP_DEP_03_02
  P_PAYMENTS_009 -->|"supports"| CAP_PAY_03_01
  P_PAYMENTS_009 -->|"supports"| CAP_PAY_03
  P_MERCHANT_006 -->|"supports"| CAP_MERCH_04
  P_DEPOSITS_004 -->|"supports"| CAP_DEP_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_BILL_04,CAP_DATA_02,CAP_DEP_03,CAP_DEP_03_02,CAP_FIN_01,CAP_FIN_02,CAP_FIN_06,CAP_MERCH_04,CAP_MERCH_04_01,CAP_PAY_03,CAP_PAY_03_01,CAP_PAY_05,CAP_PAY_06,CAP_TPS_02 s_capabilities__capabilities;
  class P_DEPOSITS_004,P_GL_CLOSE_001,P_MERCHANT_006,P_NETWORK_RECON_001,P_PAYMENTS_009,P_REWARDS_003,P_SETTLEMENT_002,P_SETTLEMENT_003,P_SETTLEMENT_004,P_TPS_002 s_processes__processes;
  class SYS_RECON s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Reconciliation platform — Processes and Capabilities](../svg/system-processes--sys-recon.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

25 entities, 26 relationships. Generated from the model; edit the model, not this file.
