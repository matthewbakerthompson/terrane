# Finance, Treasury & Settlement Accounting — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Finance, Treasury & Settlement Accounting — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_FIN_05{{"Accounts Payable &<br/>Procurement Finance"}}
    CAP_FIN_06{{"Cash & Settlement<br/>Reconciliation"}}
    CAP_FIN{{"Finance, Treasury &<br/>Settlement Accounting"}}
    CAP_FIN_03{{"Funding & Liquidity<br/>Management"}}
    CAP_FIN_01{{"General Ledger & Financial<br/>Close"}}
    CAP_FIN_02{{"Interchange & Revenue<br/>Accounting"}}
    CAP_FIN_04{{"Regulatory & Financial<br/>Reporting"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_CHARGEOFF_TIME[["Charge-off timing to<br/>policy"]]
    CTL_CLOSE_SIGNOFF[["Close reconciliation<br/>sign-off"]]
    CTL_DAILY_RECON[["Daily settlement and<br/>clearing reconciliation"]]
    CTL_DQ_GATE[["Ingestion data quality<br/>gate"]]
    CTL_REGRPT_CERT[["Regulatory report<br/>certification"]]
    CTL_FUNDING_CONF[["Settlement funding<br/>confirmation"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_APQC["APQC Process<br/>Classification Framework"]
    FW_BIAN["BIAN"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_COLLECTIONS_004[\"Execute charge-off"/]
    P_GL_CLOSE_001[\"Execute monthly financial<br/>close"/]
    P_SETTLEMENT_001[\"Fund daily network<br/>settlement position"/]
    P_FUNDING_001[\"Manage daily funding<br/>position"/]
    P_SETTLEMENT_004[\"Monitor and optimize<br/>interchange qualification"/]
    P_INTERCHANGE_POST_001[\"Post interchange and<br/>settlement entries"/]
    P_RECOVERY_005[\"Post recovery and account<br/>for proceeds"/]
    P_REG_DATA_PREP_001[\"Prepare regulatory<br/>reporting data"/]
    P_FINANCE_002[\"Process supplier payment"/]
    P_FINANCE_001[\"Recognize interchange and<br/>servicing revenue"/]
    P_SETTLEMENT_002[\"Reconcile cash and<br/>suspense accounts"/]
    P_REWARDS_003[\"Reconcile rewards<br/>liability"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_GL["General ledger"]
    SYS_RECON["Reconciliation platform"]
    SYS_REG_REPORTING["Regulatory Reporting<br/>Engine<br/>[AKS · Snowflake Data Cloud]"]
    SYS_REWARDS["Rewards ledger"]
    SYS_TREASURY["Treasury management"]
  end

  CAP_FIN_01 -->|"part of"| CAP_FIN
  CAP_FIN_02 -->|"part of"| CAP_FIN
  CAP_FIN_03 -->|"part of"| CAP_FIN
  CAP_FIN_04 -->|"part of"| CAP_FIN
  CAP_FIN_05 -->|"part of"| CAP_FIN
  CAP_FIN_06 -->|"part of"| CAP_FIN
  CAP_FIN -->|"Aligned to"| FW_APQC
  CAP_FIN_01 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_FIN_02 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_FIN_03 -->|"Operations and Executio…"| FW_BIAN
  CAP_FIN_04 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_FIN_05 -->|"8.0 Manage Financial Re…"| FW_APQC
  CAP_FIN_06 -->|"Operations and Executio…"| FW_BIAN
  P_INTERCHANGE_POST_001 -->|"supported by"| CAP_FIN_02
  P_SETTLEMENT_001 -->|"supported by"| CAP_FIN_03
  P_SETTLEMENT_002 -->|"supported by"| CAP_FIN_06
  P_REWARDS_003 -->|"supported by"| CAP_FIN_02
  P_COLLECTIONS_004 -->|"supported by"| CAP_FIN_01
  P_RECOVERY_005 -->|"supported by"| CAP_FIN_02
  P_GL_CLOSE_001 -->|"supported by"| CAP_FIN_01
  P_FUNDING_001 -->|"supported by"| CAP_FIN_03
  P_REG_DATA_PREP_001 -->|"supported by"| CAP_FIN_04
  P_FINANCE_001 -->|"supported by"| CAP_FIN_02
  P_FINANCE_002 -->|"supported by"| CAP_FIN_05
  P_SETTLEMENT_004 -->|"supported by"| CAP_FIN_02
  CAP_FIN -->|"governed by"| CTL_CHARGEOFF_TIME
  CAP_FIN -->|"governed by"| CTL_CLOSE_SIGNOFF
  CAP_FIN -->|"governed by"| CTL_DAILY_RECON
  CAP_FIN -->|"governed by"| CTL_DQ_GATE
  CAP_FIN -->|"governed by"| CTL_FUNDING_CONF
  CAP_FIN -->|"governed by"| CTL_REGRPT_CERT
  CAP_FIN_01 -->|"governed by"| CTL_CHARGEOFF_TIME
  CAP_FIN_01 -->|"governed by"| CTL_CLOSE_SIGNOFF
  CAP_FIN_02 -->|"governed by"| CTL_DAILY_RECON
  CAP_FIN_03 -->|"governed by"| CTL_DAILY_RECON
  CAP_FIN_03 -->|"governed by"| CTL_FUNDING_CONF
  CAP_FIN_04 -->|"governed by"| CTL_DQ_GATE
  CAP_FIN_04 -->|"governed by"| CTL_REGRPT_CERT
  SYS_REG_REPORTING -->|"realizes"| CAP_FIN_04
  SYS_COLLECT_API -->|"realizes"| CAP_FIN_02
  SYS_CORE_LEDGER -->|"realizes"| CAP_FIN_01
  SYS_CORE_LEDGER -->|"realizes"| CAP_FIN_02
  SYS_CORE_LEDGER -->|"realizes"| CAP_FIN_03
  SYS_DATA_INGEST -->|"realizes"| CAP_FIN_02
  SYS_DATA_INGEST -->|"realizes"| CAP_FIN_04
  SYS_GL -->|"realizes"| CAP_FIN_01
  SYS_GL -->|"realizes"| CAP_FIN_02
  SYS_GL -->|"realizes"| CAP_FIN_05
  SYS_RECON -->|"realizes"| CAP_FIN_06
  SYS_REWARDS -->|"realizes"| CAP_FIN_02
  SYS_TREASURY -->|"realizes"| CAP_FIN_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_FIN,CAP_FIN_01,CAP_FIN_02,CAP_FIN_03,CAP_FIN_04,CAP_FIN_05,CAP_FIN_06 s_capabilities__capabilities;
  class CTL_CHARGEOFF_TIME,CTL_CLOSE_SIGNOFF,CTL_DAILY_RECON,CTL_DQ_GATE,CTL_FUNDING_CONF,CTL_REGRPT_CERT s_controls__controls;
  class FW_APQC,FW_BIAN s_frameworks__frameworks;
  class P_COLLECTIONS_004,P_FINANCE_001,P_FINANCE_002,P_FUNDING_001,P_GL_CLOSE_001,P_INTERCHANGE_POST_001,P_RECOVERY_005,P_REG_DATA_PREP_001,P_REWARDS_003,P_SETTLEMENT_001,P_SETTLEMENT_002,P_SETTLEMENT_004 s_processes__processes;
  class SYS_COLLECT_API,SYS_CORE_LEDGER,SYS_DATA_INGEST,SYS_GL,SYS_RECON,SYS_REG_REPORTING,SYS_REWARDS,SYS_TREASURY s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Finance, Treasury & Settlement Accounting — Frameworks, Controls, Systems](../svg/capability-alignment--cap-fin.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

35 entities, 51 relationships. Generated from the model; edit the model, not this file.
