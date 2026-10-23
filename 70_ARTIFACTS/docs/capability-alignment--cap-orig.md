# Originations & Account Opening — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Originations & Account Opening — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_ORIG_06{{"Account Establishment &<br/>Card Issuance"}}
    CAP_ORIG_05{{"Adverse Action & Notice<br/>Generation"}}
    CAP_ORIG_01{{"Application Capture"}}
    CAP_ORIG_03{{"Application Fraud<br/>Screening"}}
    CAP_ORIG_07{{"Card Production &<br/>Fulfillment"}}
    CAP_ORIG_08{{"Digital Wallet<br/>Provisioning"}}
    CAP_ORIG_02{{"Identity Verification &<br/>KYC/CIP"}}
    CAP_ORIG{{"Originations & Account<br/>Opening"}}
    CAP_ORIG_04{{"Underwriting & Credit<br/>Decisioning Execution"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_ADVERSE_ACT[["Adverse action notice<br/>completeness"]]
    CTL_APP_INTAKE[["Application completeness<br/>and disclosure"]]
    CTL_AUTH_POLICY[["Cardholder authentication<br/>to policy"]]
    CTL_SANCTIONS[["Sanctions and watchlist<br/>screening"]]
    CTL_SCRA_MLA[["Servicemember protections<br/>screening"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_ORIG_001[\"Capture card application"/]
    P_ORIG_006[\"Establish account and<br/>issue credentials"/]
    P_ORIG_004[\"Execute credit decision"/]
    P_CREDIT_004[\"Execute credit line<br/>decrease or account action"/]
    P_ORIG_009[\"Handle application<br/>withdrawal and abandonment"/]
    P_ORIG_005[\"Issue adverse action<br/>notice"/]
    P_ORIG_007[\"Manage card production and<br/>fulfillment"/]
    P_ORIG_008[\"Provision credential to<br/>digital wallet"/]
    P_ORIG_003[\"Screen application for<br/>fraud"/]
    P_ORIG_002[\"Verify applicant identity<br/>and satisfy CIP"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_APPFRAUD["Application fraud<br/>screening"]
    SYS_CARD_FULFILL["Card production and<br/>fulfillment<br/>[external]"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_DOC["Document management and<br/>archive"]
    SYS_KYC["Identity verification"]
    SYS_ORIG_DECISION["Originations decision<br/>engine"]
    SYS_TOKEN["Tokenization and<br/>credential management"]
  end

  CAP_ORIG_01 -->|"part of"| CAP_ORIG
  CAP_ORIG_02 -->|"part of"| CAP_ORIG
  CAP_ORIG_03 -->|"part of"| CAP_ORIG
  CAP_ORIG_04 -->|"part of"| CAP_ORIG
  CAP_ORIG_05 -->|"part of"| CAP_ORIG
  CAP_ORIG_06 -->|"part of"| CAP_ORIG
  CAP_ORIG_07 -->|"part of"| CAP_ORIG
  CAP_ORIG_08 -->|"part of"| CAP_ORIG
  CAP_ORIG -->|"Aligned to"| FW_BIAN
  CAP_ORIG_01 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_ORIG_02 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_ORIG_03 -->|"Operations and Executio…"| FW_BIAN
  CAP_ORIG_04 -->|"Operations and Executio…"| FW_BIAN
  CAP_ORIG_05 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_ORIG_06 -->|"Operations and Executio…"| FW_BIAN
  CAP_ORIG_07 -->|"Operations and Executio…"| FW_BIAN
  CAP_ORIG_08 -->|"Operations and Executio…"| FW_BIAN
  P_ORIG_001 -->|"supported by"| CAP_ORIG_01
  P_ORIG_002 -->|"supported by"| CAP_ORIG_02
  P_ORIG_003 -->|"supported by"| CAP_ORIG_03
  P_ORIG_004 -->|"supported by"| CAP_ORIG_04
  P_ORIG_005 -->|"supported by"| CAP_ORIG_05
  P_ORIG_006 -->|"supported by"| CAP_ORIG_06
  P_ORIG_007 -->|"supported by"| CAP_ORIG_07
  P_ORIG_008 -->|"supported by"| CAP_ORIG_08
  P_ORIG_009 -->|"supported by"| CAP_ORIG_01
  P_CREDIT_004 -->|"supported by"| CAP_ORIG_05
  CAP_ORIG -->|"governed by"| CTL_ADVERSE_ACT
  CAP_ORIG -->|"governed by"| CTL_APP_INTAKE
  CAP_ORIG -->|"governed by"| CTL_AUTH_POLICY
  CAP_ORIG -->|"governed by"| CTL_SANCTIONS
  CAP_ORIG -->|"governed by"| CTL_SCRA_MLA
  CAP_ORIG_01 -->|"governed by"| CTL_APP_INTAKE
  CAP_ORIG_01 -->|"governed by"| CTL_SCRA_MLA
  CAP_ORIG_02 -->|"governed by"| CTL_SANCTIONS
  CAP_ORIG_03 -->|"governed by"| CTL_APP_INTAKE
  CAP_ORIG_04 -->|"governed by"| CTL_ADVERSE_ACT
  CAP_ORIG_05 -->|"governed by"| CTL_ADVERSE_ACT
  CAP_ORIG_06 -->|"governed by"| CTL_AUTH_POLICY
  SYS_CORE_LEDGER -->|"realizes"| CAP_ORIG_06
  SYS_APPFRAUD -->|"realizes"| CAP_ORIG_03
  SYS_CARD_FULFILL -->|"realizes"| CAP_ORIG_07
  SYS_CORE_LEDGER -->|"realizes"| CAP_ORIG_05
  SYS_DOC -->|"realizes"| CAP_ORIG_05
  SYS_KYC -->|"realizes"| CAP_ORIG_02
  SYS_ORIG_DECISION -->|"realizes"| CAP_ORIG_01
  SYS_ORIG_DECISION -->|"realizes"| CAP_ORIG_04
  SYS_TOKEN -->|"realizes"| CAP_ORIG_08

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_ORIG,CAP_ORIG_01,CAP_ORIG_02,CAP_ORIG_03,CAP_ORIG_04,CAP_ORIG_05,CAP_ORIG_06,CAP_ORIG_07,CAP_ORIG_08 s_capabilities__capabilities;
  class CTL_ADVERSE_ACT,CTL_APP_INTAKE,CTL_AUTH_POLICY,CTL_SANCTIONS,CTL_SCRA_MLA s_controls__controls;
  class FW_BIAN s_frameworks__frameworks;
  class P_CREDIT_004,P_ORIG_001,P_ORIG_002,P_ORIG_003,P_ORIG_004,P_ORIG_005,P_ORIG_006,P_ORIG_007,P_ORIG_008,P_ORIG_009 s_processes__processes;
  class SYS_APPFRAUD,SYS_CARD_FULFILL,SYS_CORE_LEDGER,SYS_DOC,SYS_KYC,SYS_ORIG_DECISION,SYS_TOKEN s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Originations & Account Opening — Frameworks, Controls, Systems](../svg/capability-alignment--cap-orig.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

32 entities, 48 relationships. Generated from the model; edit the model, not this file.
