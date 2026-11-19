# Payments & Transaction Processing — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Payments & Transaction Processing — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PAY_01{{"Authorization Processing"}}
    CAP_PAY_02{{"Clearing & Transaction<br/>Posting"}}
    CAP_PAY_06{{"Network & Merchant<br/>Reconciliation"}}
    CAP_PAY_05{{"Network Settlement &<br/>Interchange"}}
    CAP_PAY_03{{"Payment Capture &<br/>Application"}}
    CAP_PAY{{"Payments & Transaction<br/>Processing"}}
    CAP_PAY_04{{"Returned Payment & NSF<br/>Handling"}}
    CAP_PAY_07{{"Tokenization & Credential<br/>Management"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_AUTH_AVAIL[["Authorization availability<br/>and stand-in"]]
    CTL_DAILY_RECON[["Daily settlement and<br/>clearing reconciliation"]]
    CTL_FRAUD_SLA[["Fraud alert handling<br/>service level"]]
    CTL_PMT_ALLOC[["Payment allocation to rule"]]
    CTL_PMT_POSTING[["Payment posting timeliness"]]
    CTL_CHG_APPROVAL[["Production change approval"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
    FW_CRI["CRI Profile"]
    FW_PCI_DSS["PCI DSS"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_PAYMENTS_010[\"Allocate payment across<br/>balances"/]
    P_CARD_PMT_001[\"Capture and apply<br/>cardholder payment"/]
    P_PAYMENTS_008[\"Enroll and run automatic<br/>payments"/]
    P_SETTLEMENT_001[\"Fund daily network<br/>settlement position"/]
    P_PAYMENTS_002[\"Ingest clearing file and<br/>post transactions"/]
    P_SETTLEMENT_003[\"Investigate and clear<br/>settlement exception"/]
    P_PAYMENTS_007[\"Maintain authorization<br/>routing and network<br/>connectivity"/]
    P_PAYMENTS_004[\"Manage token and<br/>credential lifecycle"/]
    P_SETTLEMENT_004[\"Monitor and optimize<br/>interchange qualification"/]
    P_PAYMENTS_006[\"Operate stand-in<br/>authorization during a<br/>host outage"/]
    P_INTERCHANGE_POST_001[\"Post interchange and<br/>settlement entries"/]
    P_PAYMENTS_001[\"Process authorization<br/>request"/]
    P_PAYMENTS_009[\"Process lockbox and check<br/>payments"/]
    P_PAYMENTS_003[\"Process returned payment<br/>and assess NSF"/]
    P_ORIG_008[\"Provision credential to<br/>digital wallet"/]
    P_NETWORK_RECON_001[\"Reconcile network<br/>settlement"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_PAYMENT_GW["Payment capture gateway"]
    SYS_RECON["Reconciliation platform"]
    SYS_TOKEN["Tokenization and<br/>credential management"]
  end

  CAP_PAY_01 -->|"part of"| CAP_PAY
  CAP_PAY_02 -->|"part of"| CAP_PAY
  CAP_PAY_03 -->|"part of"| CAP_PAY
  CAP_PAY_04 -->|"part of"| CAP_PAY
  CAP_PAY_05 -->|"part of"| CAP_PAY
  CAP_PAY_06 -->|"part of"| CAP_PAY
  CAP_PAY_07 -->|"part of"| CAP_PAY
  CAP_PAY -->|"Aligned to"| FW_BIAN
  CAP_PAY -->|"Governed by"| FW_PCI_DSS
  CAP_PAY_01 -->|"Operations and Executio…"| FW_BIAN
  CAP_PAY_02 -->|"Operations and Executio…"| FW_BIAN
  CAP_PAY_03 -->|"Operations and Executio…"| FW_BIAN
  CAP_PAY_04 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_PAY_05 -->|"Operations and Executio…"| FW_BIAN
  CAP_PAY_06 -->|"Operations and Executio…"| FW_BIAN
  CAP_PAY_07 -->|"Operations and Executio…"| FW_BIAN
  CAP_PAY_07 -->|"Protect #gt; PR.DS-01"| FW_CRI
  P_ORIG_008 -->|"supported by"| CAP_PAY_07
  P_PAYMENTS_001 -->|"supported by"| CAP_PAY_01
  P_PAYMENTS_002 -->|"supported by"| CAP_PAY_02
  P_CARD_PMT_001 -->|"supported by"| CAP_PAY_03
  P_PAYMENTS_003 -->|"supported by"| CAP_PAY_04
  P_PAYMENTS_004 -->|"supported by"| CAP_PAY_07
  P_NETWORK_RECON_001 -->|"supported by"| CAP_PAY_06
  P_INTERCHANGE_POST_001 -->|"supported by"| CAP_PAY_05
  P_SETTLEMENT_001 -->|"supported by"| CAP_PAY_05
  P_SETTLEMENT_003 -->|"supported by"| CAP_PAY_06
  P_SETTLEMENT_004 -->|"supported by"| CAP_PAY_05
  P_PAYMENTS_006 -->|"supported by"| CAP_PAY_01
  P_PAYMENTS_007 -->|"supported by"| CAP_PAY_01
  P_PAYMENTS_008 -->|"supported by"| CAP_PAY_03
  P_PAYMENTS_009 -->|"supported by"| CAP_PAY_03
  P_PAYMENTS_010 -->|"supported by"| CAP_PAY_03
  CAP_PAY -->|"governed by"| CTL_AUTH_AVAIL
  CAP_PAY -->|"governed by"| CTL_CHG_APPROVAL
  CAP_PAY -->|"governed by"| CTL_DAILY_RECON
  CAP_PAY -->|"governed by"| CTL_FRAUD_SLA
  CAP_PAY -->|"governed by"| CTL_PMT_ALLOC
  CAP_PAY -->|"governed by"| CTL_PMT_POSTING
  CAP_PAY_01 -->|"governed by"| CTL_AUTH_AVAIL
  CAP_PAY_01 -->|"governed by"| CTL_CHG_APPROVAL
  CAP_PAY_01 -->|"governed by"| CTL_FRAUD_SLA
  CAP_PAY_02 -->|"governed by"| CTL_DAILY_RECON
  CAP_PAY_03 -->|"governed by"| CTL_PMT_ALLOC
  CAP_PAY_03 -->|"governed by"| CTL_PMT_POSTING
  CAP_PAY_05 -->|"governed by"| CTL_DAILY_RECON
  CAP_PAY_06 -->|"governed by"| CTL_DAILY_RECON
  SYS_AUTH_SWITCH -->|"realizes"| CAP_PAY
  SYS_AUTH_SWITCH -->|"realizes"| CAP_PAY_01
  SYS_CORE_LEDGER -->|"realizes"| CAP_PAY_01
  SYS_CORE_LEDGER -->|"realizes"| CAP_PAY_02
  SYS_CORE_LEDGER -->|"realizes"| CAP_PAY_03
  SYS_CORE_LEDGER -->|"realizes"| CAP_PAY_05
  SYS_DATA_INGEST -->|"realizes"| CAP_PAY_05
  SYS_PAYMENT_GW -->|"realizes"| CAP_PAY_03
  SYS_PAYMENT_GW -->|"realizes"| CAP_PAY_04
  SYS_RECON -->|"realizes"| CAP_PAY_06
  SYS_TOKEN -->|"realizes"| CAP_PAY_07

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PAY,CAP_PAY_01,CAP_PAY_02,CAP_PAY_03,CAP_PAY_04,CAP_PAY_05,CAP_PAY_06,CAP_PAY_07 s_capabilities__capabilities;
  class CTL_AUTH_AVAIL,CTL_CHG_APPROVAL,CTL_DAILY_RECON,CTL_FRAUD_SLA,CTL_PMT_ALLOC,CTL_PMT_POSTING s_controls__controls;
  class FW_BIAN,FW_CRI,FW_PCI_DSS s_frameworks__frameworks;
  class P_CARD_PMT_001,P_INTERCHANGE_POST_001,P_NETWORK_RECON_001,P_ORIG_008,P_PAYMENTS_001,P_PAYMENTS_002,P_PAYMENTS_003,P_PAYMENTS_004,P_PAYMENTS_006,P_PAYMENTS_007,P_PAYMENTS_008,P_PAYMENTS_009,P_PAYMENTS_010,P_SETTLEMENT_001,P_SETTLEMENT_003,P_SETTLEMENT_004 s_processes__processes;
  class SYS_AUTH_SWITCH,SYS_CORE_LEDGER,SYS_DATA_INGEST,SYS_PAYMENT_GW,SYS_RECON,SYS_TOKEN s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Payments & Transaction Processing — Frameworks, Controls, Systems](../svg/capability-alignment--cap-pay.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

39 entities, 58 relationships. Generated from the model; edit the model, not this file.
