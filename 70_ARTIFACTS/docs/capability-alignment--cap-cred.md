# Credit Decisioning & Portfolio Management — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Credit Decisioning & Portfolio Management — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_CRED_07{{"Account Review & Reissue<br/>Decisioning"}}
    CAP_CRED_06{{"Authorization Strategy<br/>Management"}}
    CAP_CRED{{"Credit Decisioning &<br/>Portfolio Management"}}
    CAP_CRED_03{{"Credit Line Assignment &<br/>Management"}}
    CAP_CRED_01{{"Credit Strategy &<br/>Scorecard Management"}}
    CAP_CRED_05{{"Loss Forecasting &<br/>Allowance"}}
    CAP_CRED_02{{"Model Development &<br/>Validation"}}
    CAP_CRED_04{{"Portfolio Risk Monitoring<br/>& Segmentation"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_ADVERSE_ACT[["Adverse action notice<br/>completeness"]]
    CTL_AUTH_AVAIL[["Authorization availability<br/>and stand-in"]]
    CTL_TREATMENT_APPR[["Treatment strategy<br/>approval"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_CREDIT_009[\"Acquire and refresh credit<br/>bureau data"/]
    P_CREDIT_005[\"Conduct monthly portfolio<br/>credit review"/]
    P_CREDIT_002[\"Develop and validate<br/>credit model"/]
    P_ORIG_004[\"Execute credit decision"/]
    P_CREDIT_004[\"Execute credit line<br/>decrease or account action"/]
    P_CREDIT_003[\"Execute credit line<br/>increase program"/]
    P_CREDIT_007[\"Maintain authorization<br/>strategy"/]
    P_CREDIT_008[\"Perform account review and<br/>reissue decision"/]
    P_PAYMENTS_001[\"Process authorization<br/>request"/]
    P_CREDIT_006[\"Produce loss forecast and<br/>allowance"/]
    P_CREDIT_001[\"Set and deploy credit<br/>decision strategy"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_MODEL["Model platform"]
    SYS_ORIG_DECISION["Originations decision<br/>engine"]
  end

  CAP_CRED_01 -->|"part of"| CAP_CRED
  CAP_CRED_02 -->|"part of"| CAP_CRED
  CAP_CRED_03 -->|"part of"| CAP_CRED
  CAP_CRED_04 -->|"part of"| CAP_CRED
  CAP_CRED_05 -->|"part of"| CAP_CRED
  CAP_CRED_06 -->|"part of"| CAP_CRED
  CAP_CRED_07 -->|"part of"| CAP_CRED
  CAP_CRED -->|"Aligned to"| FW_BIAN
  CAP_CRED_01 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_CRED_02 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_CRED_03 -->|"Operations and Executio…"| FW_BIAN
  CAP_CRED_04 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_CRED_05 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_CRED_06 -->|"Operations and Executio…"| FW_BIAN
  CAP_CRED_07 -->|"Operations and Executio…"| FW_BIAN
  P_ORIG_004 -->|"supported by"| CAP_CRED_01
  P_ORIG_004 -->|"supported by"| CAP_CRED_03
  P_CREDIT_001 -->|"supported by"| CAP_CRED_01
  P_CREDIT_002 -->|"supported by"| CAP_CRED_02
  P_CREDIT_003 -->|"supported by"| CAP_CRED_03
  P_CREDIT_004 -->|"supported by"| CAP_CRED_03
  P_CREDIT_005 -->|"supported by"| CAP_CRED_04
  P_CREDIT_006 -->|"supported by"| CAP_CRED_05
  P_CREDIT_007 -->|"supported by"| CAP_CRED_06
  P_CREDIT_008 -->|"supported by"| CAP_CRED_07
  P_PAYMENTS_001 -->|"supported by"| CAP_CRED_06
  P_CREDIT_009 -->|"supported by"| CAP_CRED_04
  CAP_CRED -->|"governed by"| CTL_ADVERSE_ACT
  CAP_CRED -->|"governed by"| CTL_AUTH_AVAIL
  CAP_CRED -->|"governed by"| CTL_TREATMENT_APPR
  CAP_CRED_01 -->|"governed by"| CTL_ADVERSE_ACT
  CAP_CRED_03 -->|"governed by"| CTL_ADVERSE_ACT
  CAP_CRED_06 -->|"governed by"| CTL_AUTH_AVAIL
  CAP_CRED_06 -->|"governed by"| CTL_TREATMENT_APPR
  SYS_CORE_LEDGER -->|"realizes"| CAP_CRED_03
  SYS_CORE_LEDGER -->|"realizes"| CAP_CRED_06
  SYS_CORE_LEDGER -->|"realizes"| CAP_CRED_07
  SYS_CREDIT_DATA -->|"realizes"| CAP_CRED_04
  SYS_DATA_INGEST -->|"realizes"| CAP_CRED_04
  SYS_MODEL -->|"realizes"| CAP_CRED_02
  SYS_MODEL -->|"realizes"| CAP_CRED_05
  SYS_ORIG_DECISION -->|"realizes"| CAP_CRED_01
  SYS_ORIG_DECISION -->|"realizes"| CAP_CRED_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_CRED,CAP_CRED_01,CAP_CRED_02,CAP_CRED_03,CAP_CRED_04,CAP_CRED_05,CAP_CRED_06,CAP_CRED_07 s_capabilities__capabilities;
  class CTL_ADVERSE_ACT,CTL_AUTH_AVAIL,CTL_TREATMENT_APPR s_controls__controls;
  class FW_BIAN s_frameworks__frameworks;
  class P_CREDIT_001,P_CREDIT_002,P_CREDIT_003,P_CREDIT_004,P_CREDIT_005,P_CREDIT_006,P_CREDIT_007,P_CREDIT_008,P_CREDIT_009,P_ORIG_004,P_PAYMENTS_001 s_processes__processes;
  class SYS_CORE_LEDGER,SYS_CREDIT_DATA,SYS_DATA_INGEST,SYS_MODEL,SYS_ORIG_DECISION s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Credit Decisioning & Portfolio Management — Frameworks, Controls, Systems](../svg/capability-alignment--cap-cred.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

28 entities, 43 relationships. Generated from the model; edit the model, not this file.
