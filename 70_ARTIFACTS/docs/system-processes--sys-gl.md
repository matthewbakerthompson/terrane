# General ledger — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% General ledger — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_02{{"Account Maintenance &<br/>Servicing Requests"}}
    CAP_FIN_05{{"Accounts Payable &<br/>Procurement Finance"}}
    CAP_LEND_07{{"Ancillary Product & Dealer<br/>Reserve Administration"}}
    CAP_DEP_03{{"Brokered CD Program<br/>Management"}}
    CAP_DEP_03_02{{"Brokered CD Settlement &<br/>Record Keeping"}}
    CAP_FIN_06{{"Cash & Settlement<br/>Reconciliation"}}
    CAP_COLL_04{{"Charge-off Processing"}}
    CAP_TPS_04{{"Client Billing & Revenue<br/>Management"}}
    CAP_PART_05{{"Co-Brand & Program Partner<br/>Management"}}
    CAP_LEND_06_02{{"Collateral Remarketing &<br/>Deficiency Recovery"}}
    CAP_BILL_06{{"Credit Balance Refund &<br/>Unclaimed Property"}}
    CAP_DATA_03{{"Data Quality Management"}}
    CAP_DEP_05{{"Deposit Compliance &<br/>Insurance Administration"}}
    CAP_DEP_04{{"Deposit Servicing,<br/>Interest & Maturities"}}
    CAP_FRAUD_05{{"Fraud Loss Recovery &<br/>Write-off"}}
    CAP_FIN_03{{"Funding & Liquidity<br/>Management"}}
    CAP_FIN_01{{"General Ledger & Financial<br/>Close"}}
    CAP_FIN_02{{"Interchange & Revenue<br/>Accounting"}}
    CAP_DEP_04_01{{"Interest Accrual & Tax<br/>Reporting"}}
    CAP_LEND_03{{"Loan Boarding & Dealer<br/>Funding"}}
    CAP_CRED_05{{"Loss Forecasting &<br/>Allowance"}}
    CAP_MERCH_04_01{{"Merchant Funding"}}
    CAP_MERCH_07{{"Merchant Servicing &<br/>Billing"}}
    CAP_MERCH_04{{"Merchant Settlement &<br/>Funding"}}
    CAP_PAY_06{{"Network & Merchant<br/>Reconciliation"}}
    CAP_PAY_05{{"Network Settlement &<br/>Interchange"}}
    CAP_PART_05_02{{"Partner Revenue Share<br/>Settlement"}}
    CAP_COLL_05{{"Recovery, Agency & Debt<br/>Sale Management"}}
    CAP_FIN_04{{"Regulatory & Financial<br/>Reporting"}}
    CAP_LEND_06{{"Repossession & Asset<br/>Remarketing"}}
    CAP_BILL_04{{"Rewards Earn, Accrual &<br/>Redemption"}}
    CAP_SERV_02_03{{"Secured Card Collateral<br/>Administration"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DEPOSITS_005[\"Accrue and pay deposit<br/>interest"/]
    P_DEPOSITS_008[\"Administer deposit<br/>insurance records and<br/>escheatment"/]
    P_SERVICING_011[\"Administer secured card<br/>deposit lifecycle"/]
    P_TPS_006[\"Bill client servicing fees"/]
    P_MERCHANT_011[\"Bill merchant fees and<br/>serve statements"/]
    P_LENDING_006[\"Board loan and fund dealer"/]
    P_LENDING_015[\"Calculate and settle<br/>dealer reserve"/]
    P_PARTNERSHIPS_003[\"Calculate and settle<br/>partner revenue share"/]
    P_LENDING_014[\"Cancel ancillary products<br/>and refund unearned<br/>premium"/]
    P_FINANCE_003[\"Compile, certify, and file<br/>regulatory reports"/]
    P_COLLECTIONS_004[\"Execute charge-off"/]
    P_RECOVERY_002[\"Execute debt sale"/]
    P_GL_CLOSE_001[\"Execute monthly financial<br/>close"/]
    P_SETTLEMENT_001[\"Fund daily network<br/>settlement position"/]
    P_FUNDING_001[\"Manage daily funding<br/>position"/]
    P_RECOVERY_001[\"Place account with<br/>collection agency"/]
    P_INTERCHANGE_POST_001[\"Post interchange and<br/>settlement entries"/]
    P_RECOVERY_005[\"Post recovery and account<br/>for proceeds"/]
    P_REG_DATA_PREP_001[\"Prepare regulatory<br/>reporting data"/]
    P_FINANCE_002[\"Process supplier payment"/]
    P_CREDIT_006[\"Produce loss forecast and<br/>allowance"/]
    P_FINANCE_001[\"Recognize interchange and<br/>servicing revenue"/]
    P_SETTLEMENT_002[\"Reconcile cash and<br/>suspense accounts"/]
    P_NETWORK_RECON_001[\"Reconcile network<br/>settlement"/]
    P_REWARDS_003[\"Reconcile rewards<br/>liability"/]
    P_FRAUD_004[\"Recover and write off<br/>fraud loss"/]
    P_SERVICING_016[\"Refund credit balance and<br/>report unclaimed property"/]
    P_LENDING_013[\"Remarket recovered<br/>collateral and pursue<br/>deficiency"/]
    P_MERCHANT_006[\"Settle and fund merchants"/]
    P_DEPOSITS_004[\"Settle brokered CDs and<br/>keep the position"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_GL["General ledger"]
  end

  P_CREDIT_006 -->|"Supporting"| SYS_GL
  P_NETWORK_RECON_001 -->|"Supporting"| SYS_GL
  P_INTERCHANGE_POST_001 -->|"Supporting"| SYS_GL
  P_SETTLEMENT_001 -->|"Supporting"| SYS_GL
  P_SETTLEMENT_002 -->|"Supporting"| SYS_GL
  P_REWARDS_003 -->|"Supporting"| SYS_GL
  P_FRAUD_004 -->|"Supporting"| SYS_GL
  P_COLLECTIONS_004 -->|"Supporting"| SYS_GL
  P_RECOVERY_001 -->|"Supporting"| SYS_GL
  P_RECOVERY_002 -->|"Supporting"| SYS_GL
  P_RECOVERY_005 -->|"Supporting"| SYS_GL
  P_TPS_006 -->|"Primary"| SYS_GL
  P_GL_CLOSE_001 -->|"Primary"| SYS_GL
  P_FUNDING_001 -->|"Supporting"| SYS_GL
  P_REG_DATA_PREP_001 -->|"Supporting"| SYS_GL
  P_FINANCE_001 -->|"Primary"| SYS_GL
  P_FINANCE_002 -->|"Primary"| SYS_GL
  P_SERVICING_011 -->|"Supporting"| SYS_GL
  P_LENDING_006 -->|"Supporting"| SYS_GL
  P_LENDING_013 -->|"Supporting"| SYS_GL
  P_LENDING_014 -->|"Supporting"| SYS_GL
  P_LENDING_015 -->|"Supporting"| SYS_GL
  P_MERCHANT_006 -->|"Supporting"| SYS_GL
  P_MERCHANT_011 -->|"Supporting"| SYS_GL
  P_DEPOSITS_004 -->|"Supporting"| SYS_GL
  P_DEPOSITS_005 -->|"Supporting"| SYS_GL
  P_DEPOSITS_008 -->|"Supporting"| SYS_GL
  P_SERVICING_016 -->|"Supporting"| SYS_GL
  P_PARTNERSHIPS_003 -->|"Primary"| SYS_GL
  P_FINANCE_003 -->|"Supporting"| SYS_GL
  P_CREDIT_006 -->|"supports"| CAP_CRED_05
  P_NETWORK_RECON_001 -->|"supports"| CAP_PAY_06
  P_INTERCHANGE_POST_001 -->|"supports"| CAP_PAY_05
  P_INTERCHANGE_POST_001 -->|"supports"| CAP_FIN_02
  P_SETTLEMENT_001 -->|"supports"| CAP_PAY_05
  P_SETTLEMENT_001 -->|"supports"| CAP_FIN_03
  P_SETTLEMENT_002 -->|"supports"| CAP_FIN_06
  P_REWARDS_003 -->|"supports"| CAP_BILL_04
  P_REWARDS_003 -->|"supports"| CAP_FIN_02
  P_FRAUD_004 -->|"supports"| CAP_FRAUD_05
  P_COLLECTIONS_004 -->|"supports"| CAP_COLL_04
  P_COLLECTIONS_004 -->|"supports"| CAP_FIN_01
  P_RECOVERY_001 -->|"supports"| CAP_COLL_05
  P_RECOVERY_002 -->|"supports"| CAP_COLL_05
  P_RECOVERY_005 -->|"supports"| CAP_COLL_05
  P_RECOVERY_005 -->|"supports"| CAP_FIN_02
  P_TPS_006 -->|"supports"| CAP_TPS_04
  P_GL_CLOSE_001 -->|"supports"| CAP_FIN_01
  P_FUNDING_001 -->|"supports"| CAP_FIN_03
  P_REG_DATA_PREP_001 -->|"supports"| CAP_FIN_04
  P_REG_DATA_PREP_001 -->|"supports"| CAP_DATA_03
  P_FINANCE_001 -->|"supports"| CAP_FIN_02
  P_FINANCE_002 -->|"supports"| CAP_FIN_05
  P_SERVICING_011 -->|"supports"| CAP_SERV_02
  P_LENDING_006 -->|"supports"| CAP_LEND_03
  P_LENDING_013 -->|"supports"| CAP_LEND_06_02
  P_LENDING_014 -->|"supports"| CAP_LEND_07
  P_LENDING_015 -->|"supports"| CAP_LEND_07
  P_MERCHANT_006 -->|"supports"| CAP_MERCH_04_01
  P_MERCHANT_011 -->|"supports"| CAP_MERCH_07
  P_DEPOSITS_004 -->|"supports"| CAP_DEP_03_02
  P_DEPOSITS_005 -->|"supports"| CAP_DEP_04_01
  P_DEPOSITS_008 -->|"supports"| CAP_DEP_05
  P_SERVICING_016 -->|"supports"| CAP_BILL_06
  P_PARTNERSHIPS_003 -->|"supports"| CAP_PART_05_02
  P_FINANCE_003 -->|"supports"| CAP_FIN_04
  P_SERVICING_011 -->|"supports"| CAP_SERV_02_03
  P_PARTNERSHIPS_003 -->|"supports"| CAP_PART_05
  P_LENDING_013 -->|"supports"| CAP_LEND_06
  P_MERCHANT_006 -->|"supports"| CAP_MERCH_04
  P_DEPOSITS_004 -->|"supports"| CAP_DEP_03
  P_DEPOSITS_005 -->|"supports"| CAP_DEP_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_BILL_04,CAP_BILL_06,CAP_COLL_04,CAP_COLL_05,CAP_CRED_05,CAP_DATA_03,CAP_DEP_03,CAP_DEP_03_02,CAP_DEP_04,CAP_DEP_04_01,CAP_DEP_05,CAP_FIN_01,CAP_FIN_02,CAP_FIN_03,CAP_FIN_04,CAP_FIN_05,CAP_FIN_06,CAP_FRAUD_05,CAP_LEND_03,CAP_LEND_06,CAP_LEND_06_02,CAP_LEND_07,CAP_MERCH_04,CAP_MERCH_04_01,CAP_MERCH_07,CAP_PART_05,CAP_PART_05_02,CAP_PAY_05,CAP_PAY_06,CAP_SERV_02,CAP_SERV_02_03,CAP_TPS_04 s_capabilities__capabilities;
  class P_COLLECTIONS_004,P_CREDIT_006,P_DEPOSITS_004,P_DEPOSITS_005,P_DEPOSITS_008,P_FINANCE_001,P_FINANCE_002,P_FINANCE_003,P_FRAUD_004,P_FUNDING_001,P_GL_CLOSE_001,P_INTERCHANGE_POST_001,P_LENDING_006,P_LENDING_013,P_LENDING_014,P_LENDING_015,P_MERCHANT_006,P_MERCHANT_011,P_NETWORK_RECON_001,P_PARTNERSHIPS_003,P_RECOVERY_001,P_RECOVERY_002,P_RECOVERY_005,P_REG_DATA_PREP_001,P_REWARDS_003,P_SERVICING_011,P_SERVICING_016,P_SETTLEMENT_001,P_SETTLEMENT_002,P_TPS_006 s_processes__processes;
  class SYS_GL s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![General ledger — Processes and Capabilities](../svg/system-processes--sys-gl.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

63 entities, 72 relationships. Generated from the model; edit the model, not this file.

> 63 entities on an architecture diagram. Past about 40 this has become a landscape: narrow the scope, or mark it `kind: map`.
