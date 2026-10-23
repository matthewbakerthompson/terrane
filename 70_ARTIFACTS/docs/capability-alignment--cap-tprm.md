# Third-Party & Vendor Management — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Third-Party & Vendor Management — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_TPRM_02{{"Contract & SLA Management"}}
    CAP_TPRM_03{{"Ongoing Vendor Risk<br/>Monitoring"}}
    CAP_TPRM{{"Third-Party & Vendor<br/>Management"}}
    CAP_TPRM_04{{"Vendor Exit & Continuity<br/>Planning"}}
    CAP_TPRM_01{{"Vendor Sourcing & Due<br/>Diligence"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_TPRM_DD[["Third-party due diligence<br/>before onboarding"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_APQC["APQC Process<br/>Classification Framework"]
    FW_BIAN["BIAN"]
    FW_CRI["CRI Profile"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_EA_008[\"Evaluate and select a<br/>technology or platform"/]
    P_VENDORMGMT_003[\"Execute supplier exit"/]
    P_VENDORMGMT_002[\"Monitor supplier risk and<br/>performance"/]
    P_VENDORMGMT_001[\"Onboard and diligence<br/>supplier"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_ARCHREPO["Architecture repository<br/>[SaaS]"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
  end

  CAP_TPRM_01 -->|"part of"| CAP_TPRM
  CAP_TPRM_02 -->|"part of"| CAP_TPRM
  CAP_TPRM_03 -->|"part of"| CAP_TPRM
  CAP_TPRM_04 -->|"part of"| CAP_TPRM
  CAP_TPRM -->|"Informed by"| FW_APQC
  CAP_TPRM_01 -->|"Extend #gt; EX.DD-01"| FW_CRI
  CAP_TPRM_02 -->|"Reference Data #gt; Ext…"| FW_BIAN
  CAP_TPRM_02 -->|"Extend #gt; EX.CN-01"| FW_CRI
  CAP_TPRM_03 -->|"Extend #gt; EX.MM-01"| FW_CRI
  CAP_TPRM_04 -->|"Extend #gt; EX.TR-01"| FW_CRI
  P_VENDORMGMT_001 -->|"supported by"| CAP_TPRM_01
  P_VENDORMGMT_001 -->|"supported by"| CAP_TPRM_02
  P_VENDORMGMT_002 -->|"supported by"| CAP_TPRM_03
  P_VENDORMGMT_003 -->|"supported by"| CAP_TPRM_04
  P_EA_008 -->|"supported by"| CAP_TPRM_01
  CAP_TPRM -->|"governed by"| CTL_TPRM_DD
  CAP_TPRM_01 -->|"governed by"| CTL_TPRM_DD
  CAP_TPRM_02 -->|"governed by"| CTL_TPRM_DD
  SYS_ARCHREPO -->|"realizes"| CAP_TPRM_01
  SYS_GRC -->|"realizes"| CAP_TPRM_01
  SYS_GRC -->|"realizes"| CAP_TPRM_02
  SYS_GRC -->|"realizes"| CAP_TPRM_03
  SYS_GRC -->|"realizes"| CAP_TPRM_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_TPRM,CAP_TPRM_01,CAP_TPRM_02,CAP_TPRM_03,CAP_TPRM_04 s_capabilities__capabilities;
  class CTL_TPRM_DD s_controls__controls;
  class FW_APQC,FW_BIAN,FW_CRI s_frameworks__frameworks;
  class P_EA_008,P_VENDORMGMT_001,P_VENDORMGMT_002,P_VENDORMGMT_003 s_processes__processes;
  class SYS_ARCHREPO,SYS_GRC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Third-Party & Vendor Management — Frameworks, Controls, Systems](../svg/capability-alignment--cap-tprm.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

15 entities, 23 relationships. Generated from the model; edit the model, not this file.
