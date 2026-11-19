# Onboard the screening vendor — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Onboard the screening vendor — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PAY_01{{"Authorization Processing"}}
    CAP_RGOV_07{{"Financial Crimes & BSA/AML<br/>Compliance"}}
    CAP_MERCH_02_02{{"Merchant Screening & Brand<br/>Risk"}}
    CAP_MERCH_02{{"Merchant Underwriting &<br/>Risk Vetting"}}
    CAP_PAY{{"Payments & Transaction<br/>Processing"}}
    CAP_RGOV_07_01{{"Sanctions Screening"}}
    CAP_PAY_01_04{{"Stand-In Processing"}}
    CAP_PAY_01_05{{"Transaction Switching"}}
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_AUTH_LOG[("Authorization log")]
    DA_CARD_ACCOUNT[("Card account master")]
    DA_TRANSACTION[("Card transaction history")]
    DA_SCREENING_OUTCOMES[("NICE Actimize Screening<br/>outcomes")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_PAYMENTS_010[\"Allocate payment across<br/>balances"/]
    P_SERVICING_001[\"Assess interest, fees, and<br/>minimum payment"/]
    P_MERCHANT_002[\"Capture merchant<br/>application"/]
    P_TPS_002[\"Convert client portfolio"/]
    P_STMT_GEN_001[\"Cut cycle and generate<br/>statement"/]
    P_FRAUD_007[\"Detect and act on<br/>first-party fraud and<br/>bust-out"/]
    P_FRAUD_001[\"Detect and action<br/>transaction fraud alert"/]
    P_PAYMENTS_002[\"Ingest clearing file and<br/>post transactions"/]
    P_COMPLIANCE_004[\"Investigate and file<br/>suspicious activity report"/]
    P_PAYMENTS_007[\"Maintain authorization<br/>routing and network<br/>connectivity"/]
    P_COMPLIANCE_007[\"Monitor transactions for<br/>suspicious activity"/]
    P_PAYMENTS_006[\"Operate stand-in<br/>authorization during a<br/>host outage"/]
    P_PAYMENTS_001[\"Process authorization<br/>request"/]
    P_DISPUTE_001[\"Process cardholder dispute<br/>claim"/]
    P_NETWORK_RECON_001[\"Reconcile network<br/>settlement"/]
    P_COMPLIANCE_003[\"Screen for sanctions and<br/>watchlists"/]
    P_MERCHANT_004[\"Screen merchant against<br/>sanctions and network<br/>lists"/]
    P_COMPLIANCE_008[\"Screen transactions and<br/>parties against sanctions<br/>in line"/]
    P_MERCHANT_003[\"Underwrite merchant"/]
    P_ORIG_002[\"Verify applicant identity<br/>and satisfy CIP"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
    SYS_SCREENING_FEDERATION["NICE Actimize Screening<br/>Identity Federation"]
    SYS_SCREENING_GATEWAY["NICE Actimize Screening<br/>Integration Gateway<br/>[EKS]"]
    SYS_SCREENING_EGRESS["NICE Actimize Screening<br/>Private Egress"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_SCREENING_ONBOARD["Onboard the screening<br/>vendor"]
  end

  WP_SCREENING_ONBOARD -->|"Builds"| SYS_SCREENING_VENDOR
  WP_SCREENING_ONBOARD -->|"Builds"| SYS_SCREENING_GATEWAY
  WP_SCREENING_ONBOARD -->|"Builds"| SYS_SCREENING_EGRESS
  WP_SCREENING_ONBOARD -->|"Builds"| SYS_SCREENING_FEDERATION
  WP_SCREENING_ONBOARD -->|"Changes"| SYS_AUTH_SWITCH
  SYS_SCREENING_VENDOR -->|"Write"| DA_SCREENING_OUTCOMES
  SYS_AUTH_SWITCH -->|"ReadWrite"| DA_AUTH_LOG
  SYS_AUTH_SWITCH -->|"Read"| DA_CARD_ACCOUNT
  SYS_AUTH_SWITCH -->|"ReadWrite"| DA_TRANSACTION
  SYS_AUTH_SWITCH -->|"realizes"| CAP_PAY
  SYS_AUTH_SWITCH -->|"realizes"| CAP_PAY_01
  SYS_AUTH_SWITCH -->|"realizes"| CAP_PAY_01_04
  SYS_AUTH_SWITCH -->|"realizes"| CAP_PAY_01_05
  SYS_SCREENING_VENDOR -->|"realizes"| CAP_MERCH_02
  SYS_SCREENING_VENDOR -->|"realizes"| CAP_MERCH_02_02
  SYS_SCREENING_VENDOR -->|"realizes"| CAP_RGOV_07
  SYS_SCREENING_VENDOR -->|"realizes"| CAP_RGOV_07_01
  P_DISPUTE_001 -->|"Reads"| DA_TRANSACTION
  P_PAYMENTS_001 -->|"Writes"| DA_TRANSACTION
  P_PAYMENTS_002 -->|"Writes"| DA_TRANSACTION
  P_NETWORK_RECON_001 -->|"Reads"| DA_TRANSACTION
  P_SERVICING_001 -->|"Both"| DA_TRANSACTION
  P_STMT_GEN_001 -->|"Reads"| DA_TRANSACTION
  P_FRAUD_001 -->|"Reads"| DA_TRANSACTION
  P_TPS_002 -->|"Writes"| DA_TRANSACTION
  P_PAYMENTS_006 -->|"Both"| DA_AUTH_LOG
  P_PAYMENTS_007 -->|"Read"| DA_AUTH_LOG
  P_PAYMENTS_010 -->|"Write"| DA_TRANSACTION
  P_FRAUD_007 -->|"Read"| DA_TRANSACTION
  P_COMPLIANCE_007 -->|"Read"| DA_TRANSACTION
  P_COMPLIANCE_008 -->|"Read"| DA_AUTH_LOG
  P_ORIG_002 -->|"supports"| CAP_RGOV_07
  P_PAYMENTS_001 -->|"supports"| CAP_PAY_01
  P_COMPLIANCE_003 -->|"supports"| CAP_RGOV_07
  P_COMPLIANCE_004 -->|"supports"| CAP_RGOV_07
  P_MERCHANT_004 -->|"supports"| CAP_MERCH_02_02
  P_PAYMENTS_006 -->|"supports"| CAP_PAY_01_04
  P_PAYMENTS_007 -->|"supports"| CAP_PAY_01_05
  P_COMPLIANCE_008 -->|"supports"| CAP_RGOV_07_01
  P_PAYMENTS_001 -->|"supports"| CAP_PAY_01_05
  P_COMPLIANCE_003 -->|"supports"| CAP_RGOV_07_01
  P_PAYMENTS_006 -->|"supports"| CAP_PAY_01
  P_PAYMENTS_007 -->|"supports"| CAP_PAY_01
  P_COMPLIANCE_007 -->|"supports"| CAP_RGOV_07
  P_COMPLIANCE_008 -->|"supports"| CAP_RGOV_07
  P_MERCHANT_002 -->|"supports"| CAP_MERCH_02
  P_MERCHANT_003 -->|"supports"| CAP_MERCH_02
  P_MERCHANT_004 -->|"supports"| CAP_MERCH_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class CAP_MERCH_02,CAP_MERCH_02_02,CAP_PAY,CAP_PAY_01,CAP_PAY_01_04,CAP_PAY_01_05,CAP_RGOV_07,CAP_RGOV_07_01 s_capabilities__capabilities;
  class DA_AUTH_LOG,DA_CARD_ACCOUNT,DA_SCREENING_OUTCOMES,DA_TRANSACTION s_data_assets__data_assets;
  class P_COMPLIANCE_003,P_COMPLIANCE_004,P_COMPLIANCE_007,P_COMPLIANCE_008,P_DISPUTE_001,P_FRAUD_001,P_FRAUD_007,P_MERCHANT_002,P_MERCHANT_003,P_MERCHANT_004,P_NETWORK_RECON_001,P_ORIG_002,P_PAYMENTS_001,P_PAYMENTS_002,P_PAYMENTS_006,P_PAYMENTS_007,P_PAYMENTS_010,P_SERVICING_001,P_STMT_GEN_001,P_TPS_002 s_processes__processes;
  class SYS_AUTH_SWITCH,SYS_SCREENING_EGRESS,SYS_SCREENING_FEDERATION,SYS_SCREENING_GATEWAY,SYS_SCREENING_VENDOR s_systems__systems;
  class WP_SCREENING_ONBOARD s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Data_Asset,grp_Process,grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Onboard the screening vendor — Footprint](../svg/change-footprint--wp-screening-onboard.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |
| `#0d9488` | work packages |

38 entities, 48 relationships. Generated from the model; edit the model, not this file.
