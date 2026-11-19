# Credit data and decisioning environment — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Credit data and decisioning environment — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_CRED_07{{"Account Review & Reissue<br/>Decisioning"}}
    CAP_ACQ_05{{"Acquisition Performance<br/>Analytics"}}
    CAP_CRED_03{{"Credit Line Assignment &<br/>Management"}}
    CAP_CRED_01{{"Credit Strategy &<br/>Scorecard Management"}}
    CAP_RGOV_09{{"Fair Lending Monitoring"}}
    CAP_FRAUD_08{{"First-Party Fraud &<br/>Bust-Out Management"}}
    CAP_LEND_02{{"Indirect Application &<br/>Underwriting"}}
    CAP_LEND_02_02{{"Indirect Credit Decision &<br/>Counteroffer"}}
    CAP_ACQ_04{{"Marketing Compliance &<br/>Disclosure Review"}}
    CAP_MERCH_02_01{{"Merchant Credit<br/>Underwriting"}}
    CAP_MERCH_02{{"Merchant Underwriting &<br/>Risk Vetting"}}
    CAP_ACQ_02{{"Offer & Pre-Screen<br/>Management"}}
    CAP_ACQ_02_01{{"Offer Construction"}}
    CAP_CRED_04{{"Portfolio Risk Monitoring<br/>& Segmentation"}}
    CAP_SERV_09{{"Retention, Product Change<br/>& Account Closure"}}
    CAP_ORIG_04{{"Underwriting & Credit<br/>Decisioning Execution"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_CREDIT_009[\"Acquire and refresh credit<br/>bureau data"/]
    P_CREDIT_005[\"Conduct monthly portfolio<br/>credit review"/]
    P_MARKETING_002[\"Construct and approve firm<br/>offer of credit"/]
    P_LENDING_004[\"Decide indirect loan and<br/>return terms"/]
    P_FRAUD_007[\"Detect and act on<br/>first-party fraud and<br/>bust-out"/]
    P_ORIG_004[\"Execute credit decision"/]
    P_CREDIT_008[\"Perform account review and<br/>reissue decision"/]
    P_SERVICING_014[\"Retain account at closure<br/>request"/]
    P_MARKETING_005[\"Review campaign<br/>performance and adjust<br/>targeting"/]
    P_CREDIT_001[\"Set and deploy credit<br/>decision strategy"/]
    P_COMPLIANCE_006[\"Test credit decisions and<br/>pricing for fair lending"/]
    P_MERCHANT_003[\"Underwrite merchant"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
  end

  P_MARKETING_002 -->|"Primary"| SYS_CREDIT_DATA
  P_MARKETING_005 -->|"Supporting"| SYS_CREDIT_DATA
  P_ORIG_004 -->|"Supporting"| SYS_CREDIT_DATA
  P_CREDIT_001 -->|"Supporting"| SYS_CREDIT_DATA
  P_CREDIT_005 -->|"Supporting"| SYS_CREDIT_DATA
  P_CREDIT_008 -->|"Supporting"| SYS_CREDIT_DATA
  P_CREDIT_009 -->|"Primary"| SYS_CREDIT_DATA
  P_LENDING_004 -->|"Supporting"| SYS_CREDIT_DATA
  P_MERCHANT_003 -->|"Supporting"| SYS_CREDIT_DATA
  P_SERVICING_014 -->|"Supporting"| SYS_CREDIT_DATA
  P_FRAUD_007 -->|"Supporting"| SYS_CREDIT_DATA
  P_COMPLIANCE_006 -->|"Primary"| SYS_CREDIT_DATA
  P_MARKETING_002 -->|"supports"| CAP_ACQ_02
  P_MARKETING_002 -->|"supports"| CAP_ACQ_04
  P_MARKETING_005 -->|"supports"| CAP_ACQ_05
  P_ORIG_004 -->|"supports"| CAP_ORIG_04
  P_ORIG_004 -->|"supports"| CAP_CRED_01
  P_ORIG_004 -->|"supports"| CAP_CRED_03
  P_CREDIT_001 -->|"supports"| CAP_CRED_01
  P_CREDIT_005 -->|"supports"| CAP_CRED_04
  P_CREDIT_008 -->|"supports"| CAP_CRED_07
  P_CREDIT_009 -->|"supports"| CAP_CRED_04
  P_CREDIT_009 -->|"supports"| CAP_ACQ_02
  P_LENDING_004 -->|"supports"| CAP_LEND_02_02
  P_MERCHANT_003 -->|"supports"| CAP_MERCH_02_01
  P_SERVICING_014 -->|"supports"| CAP_SERV_09
  P_FRAUD_007 -->|"supports"| CAP_FRAUD_08
  P_COMPLIANCE_006 -->|"supports"| CAP_RGOV_09
  P_MARKETING_002 -->|"supports"| CAP_ACQ_02_01
  P_LENDING_004 -->|"supports"| CAP_LEND_02
  P_MERCHANT_003 -->|"supports"| CAP_MERCH_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_ACQ_02,CAP_ACQ_02_01,CAP_ACQ_04,CAP_ACQ_05,CAP_CRED_01,CAP_CRED_03,CAP_CRED_04,CAP_CRED_07,CAP_FRAUD_08,CAP_LEND_02,CAP_LEND_02_02,CAP_MERCH_02,CAP_MERCH_02_01,CAP_ORIG_04,CAP_RGOV_09,CAP_SERV_09 s_capabilities__capabilities;
  class P_COMPLIANCE_006,P_CREDIT_001,P_CREDIT_005,P_CREDIT_008,P_CREDIT_009,P_FRAUD_007,P_LENDING_004,P_MARKETING_002,P_MARKETING_005,P_MERCHANT_003,P_ORIG_004,P_SERVICING_014 s_processes__processes;
  class SYS_CREDIT_DATA s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Credit data and decisioning environment — Processes and Capabilities](../svg/system-processes--sys-credit-data.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

29 entities, 31 relationships. Generated from the model; edit the model, not this file.
