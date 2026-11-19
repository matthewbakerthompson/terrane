# Deposit Products & Funding — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Deposit Products & Funding — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_DEP_03{{"Brokered CD Program<br/>Management"}}
    CAP_DEP_02{{"Deposit Account Opening"}}
    CAP_DEP_05{{"Deposit Compliance &<br/>Insurance Administration"}}
    CAP_DEP_01{{"Deposit Product Management"}}
    CAP_DEP{{"Deposit Products & Funding"}}
    CAP_DEP_04{{"Deposit Servicing,<br/>Interest & Maturities"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_BROKERED_RECON[["Brokered deposit position<br/>reconciliation"]]
    CTL_TAX_REPORT[["Deposit interest tax<br/>reporting"]]
    CTL_MKT_REVIEW[["Marketing material<br/>compliance review"]]
    CTL_RETENTION[["Retention schedule<br/>enforcement"]]
    CTL_SANCTIONS[["Sanctions and watchlist<br/>screening"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
    FW_CRI["CRI Profile"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DEPOSITS_005[\"Accrue and pay deposit<br/>interest"/]
    P_DEPOSITS_008[\"Administer deposit<br/>insurance records and<br/>escheatment"/]
    P_DEPOSITS_003[\"Issue brokered CDs through<br/>the broker network"/]
    P_DEPOSITS_002[\"Open and fund direct<br/>deposit account"/]
    P_DEPOSITS_007[\"Process CD maturity,<br/>renewal, and early<br/>withdrawal"/]
    P_DEPOSITS_006[\"Produce deposit tax<br/>reporting"/]
    P_DEPOSITS_001[\"Set deposit rates and<br/>product terms"/]
    P_DEPOSITS_004[\"Settle brokered CDs and<br/>keep the position"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_BROKER_GW["Brokered deposit<br/>settlement gateway"]
    SYS_DEPOSIT["Deposit platform"]
  end

  CAP_DEP_01 -->|"part of"| CAP_DEP
  CAP_DEP_02 -->|"part of"| CAP_DEP
  CAP_DEP_03 -->|"part of"| CAP_DEP
  CAP_DEP_04 -->|"part of"| CAP_DEP
  CAP_DEP_05 -->|"part of"| CAP_DEP
  CAP_DEP -->|"Aligned to"| FW_BIAN
  CAP_DEP_01 -->|"Operations and Executio…"| FW_BIAN
  CAP_DEP_02 -->|"Operations and Executio…"| FW_BIAN
  CAP_DEP_03 -->|"Operations and Executio…"| FW_BIAN
  CAP_DEP_04 -->|"Operations and Executio…"| FW_BIAN
  CAP_DEP_05 -->|"Govern #gt; GV.OC-03"| FW_CRI
  P_DEPOSITS_001 -->|"supported by"| CAP_DEP_01
  P_DEPOSITS_002 -->|"supported by"| CAP_DEP_02
  P_DEPOSITS_008 -->|"supported by"| CAP_DEP_05
  P_DEPOSITS_003 -->|"supported by"| CAP_DEP_03
  P_DEPOSITS_004 -->|"supported by"| CAP_DEP_03
  P_DEPOSITS_005 -->|"supported by"| CAP_DEP_04
  P_DEPOSITS_006 -->|"supported by"| CAP_DEP_04
  P_DEPOSITS_007 -->|"supported by"| CAP_DEP_04
  CAP_DEP -->|"governed by"| CTL_BROKERED_RECON
  CAP_DEP -->|"governed by"| CTL_MKT_REVIEW
  CAP_DEP -->|"governed by"| CTL_RETENTION
  CAP_DEP -->|"governed by"| CTL_SANCTIONS
  CAP_DEP -->|"governed by"| CTL_TAX_REPORT
  CAP_DEP_01 -->|"governed by"| CTL_MKT_REVIEW
  CAP_DEP_02 -->|"governed by"| CTL_SANCTIONS
  CAP_DEP_03 -->|"governed by"| CTL_BROKERED_RECON
  CAP_DEP_04 -->|"governed by"| CTL_TAX_REPORT
  CAP_DEP_05 -->|"governed by"| CTL_RETENTION
  SYS_BROKER_GW -->|"realizes"| CAP_DEP_03
  SYS_DEPOSIT -->|"realizes"| CAP_DEP_01
  SYS_DEPOSIT -->|"realizes"| CAP_DEP_02
  SYS_DEPOSIT -->|"realizes"| CAP_DEP_03
  SYS_DEPOSIT -->|"realizes"| CAP_DEP_04
  SYS_DEPOSIT -->|"realizes"| CAP_DEP_05

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_DEP,CAP_DEP_01,CAP_DEP_02,CAP_DEP_03,CAP_DEP_04,CAP_DEP_05 s_capabilities__capabilities;
  class CTL_BROKERED_RECON,CTL_MKT_REVIEW,CTL_RETENTION,CTL_SANCTIONS,CTL_TAX_REPORT s_controls__controls;
  class FW_BIAN,FW_CRI s_frameworks__frameworks;
  class P_DEPOSITS_001,P_DEPOSITS_002,P_DEPOSITS_003,P_DEPOSITS_004,P_DEPOSITS_005,P_DEPOSITS_006,P_DEPOSITS_007,P_DEPOSITS_008 s_processes__processes;
  class SYS_BROKER_GW,SYS_DEPOSIT s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Deposit Products & Funding — Frameworks, Controls, Systems](../svg/capability-alignment--cap-dep.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

23 entities, 35 relationships. Generated from the model; edit the model, not this file.
