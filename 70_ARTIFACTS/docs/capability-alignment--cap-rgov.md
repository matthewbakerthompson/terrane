# Risk Governance & Compliance Management — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Risk Governance & Compliance Management — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_RGOV_06{{"Complaint Oversight &<br/>UDAAP Management"}}
    CAP_RGOV_03{{"Compliance Monitoring &<br/>Testing"}}
    CAP_RGOV_07{{"Financial Crimes & BSA/AML<br/>Compliance"}}
    CAP_RGOV_05{{"Internal Audit &<br/>Examination Management"}}
    CAP_RGOV_04{{"Issue & Remediation<br/>Management"}}
    CAP_RGOV_08{{"Model Risk Governance"}}
    CAP_RGOV_02{{"Regulatory Change<br/>Management"}}
    CAP_RGOV_01{{"Risk Appetite & Policy<br/>Management"}}
    CAP_RGOV{{"Risk Governance &<br/>Compliance Management"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_COMPLAINT_REG[["Complaint regulatory<br/>routing"]]
    CTL_REGCHANGE_TRACK[["Regulatory change<br/>implementation tracking"]]
    CTL_REGRPT_CERT[["Regulatory report<br/>certification"]]
    CTL_SANCTIONS[["Sanctions and watchlist<br/>screening"]]
    CTL_SAR_FILING[["Suspicious activity<br/>investigation and filing"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
    FW_COBIT["COBIT 2019"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_COMPLIANCE_005[\"Analyze complaint signal<br/>for conduct risk"/]
    P_COMPLIANCE_001[\"Assess and land regulatory<br/>change"/]
    P_SERVICING_006[\"Capture and resolve<br/>complaint"/]
    P_RISK_003[\"Coordinate regulatory<br/>examination"/]
    P_CREDIT_002[\"Develop and validate<br/>credit model"/]
    P_COMPLIANCE_002[\"Execute compliance<br/>monitoring test"/]
    P_EA_003[\"Grant or decline an<br/>architecture exception"/]
    P_COMPLIANCE_004[\"Investigate and file<br/>suspicious activity report"/]
    P_RISK_001[\"Manage issue and<br/>remediation to closure"/]
    P_COMPLIANCE_003[\"Screen for sanctions and<br/>watchlists"/]
    P_RISK_002[\"Validate model<br/>independently"/]
    P_ORIG_002[\"Verify applicant identity<br/>and satisfy CIP"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_ARCHREPO["Architecture repository<br/>[SaaS]"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_AML["Financial crimes platform"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
    SYS_KYC["Identity verification"]
    SYS_MODEL["Model platform"]
  end

  CAP_RGOV_01 -->|"part of"| CAP_RGOV
  CAP_RGOV_02 -->|"part of"| CAP_RGOV
  CAP_RGOV_03 -->|"part of"| CAP_RGOV
  CAP_RGOV_04 -->|"part of"| CAP_RGOV
  CAP_RGOV_05 -->|"part of"| CAP_RGOV
  CAP_RGOV_06 -->|"part of"| CAP_RGOV
  CAP_RGOV_07 -->|"part of"| CAP_RGOV
  CAP_RGOV_08 -->|"part of"| CAP_RGOV
  CAP_RGOV -->|"Aligned to"| FW_COBIT
  CAP_RGOV_01 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_RGOV_02 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_RGOV_03 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_RGOV_04 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_RGOV_05 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_RGOV_06 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_RGOV_07 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_RGOV_08 -->|"Risk and Compliance #gt…"| FW_BIAN
  P_ORIG_002 -->|"supported by"| CAP_RGOV_07
  P_CREDIT_002 -->|"supported by"| CAP_RGOV_08
  P_SERVICING_006 -->|"supported by"| CAP_RGOV_06
  P_COMPLIANCE_001 -->|"supported by"| CAP_RGOV_02
  P_COMPLIANCE_002 -->|"supported by"| CAP_RGOV_03
  P_COMPLIANCE_003 -->|"supported by"| CAP_RGOV_07
  P_COMPLIANCE_004 -->|"supported by"| CAP_RGOV_07
  P_COMPLIANCE_005 -->|"supported by"| CAP_RGOV_06
  P_RISK_001 -->|"supported by"| CAP_RGOV_04
  P_RISK_002 -->|"supported by"| CAP_RGOV_08
  P_RISK_003 -->|"supported by"| CAP_RGOV_05
  P_EA_003 -->|"supported by"| CAP_RGOV_04
  CAP_RGOV -->|"governed by"| CTL_COMPLAINT_REG
  CAP_RGOV -->|"governed by"| CTL_REGCHANGE_TRACK
  CAP_RGOV -->|"governed by"| CTL_REGRPT_CERT
  CAP_RGOV -->|"governed by"| CTL_SANCTIONS
  CAP_RGOV -->|"governed by"| CTL_SAR_FILING
  CAP_RGOV_02 -->|"governed by"| CTL_REGCHANGE_TRACK
  CAP_RGOV_05 -->|"governed by"| CTL_REGRPT_CERT
  CAP_RGOV_06 -->|"governed by"| CTL_COMPLAINT_REG
  CAP_RGOV_07 -->|"governed by"| CTL_SANCTIONS
  CAP_RGOV_07 -->|"governed by"| CTL_SAR_FILING
  SYS_AML -->|"realizes"| CAP_RGOV_07
  SYS_ARCHREPO -->|"realizes"| CAP_RGOV_04
  SYS_CRM -->|"realizes"| CAP_RGOV_06
  SYS_GRC -->|"realizes"| CAP_RGOV_02
  SYS_GRC -->|"realizes"| CAP_RGOV_03
  SYS_GRC -->|"realizes"| CAP_RGOV_04
  SYS_GRC -->|"realizes"| CAP_RGOV_05
  SYS_GRC -->|"realizes"| CAP_RGOV_06
  SYS_KYC -->|"realizes"| CAP_RGOV_07
  SYS_MODEL -->|"realizes"| CAP_RGOV_08

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_RGOV,CAP_RGOV_01,CAP_RGOV_02,CAP_RGOV_03,CAP_RGOV_04,CAP_RGOV_05,CAP_RGOV_06,CAP_RGOV_07,CAP_RGOV_08 s_capabilities__capabilities;
  class CTL_COMPLAINT_REG,CTL_REGCHANGE_TRACK,CTL_REGRPT_CERT,CTL_SANCTIONS,CTL_SAR_FILING s_controls__controls;
  class FW_BIAN,FW_COBIT s_frameworks__frameworks;
  class P_COMPLIANCE_001,P_COMPLIANCE_002,P_COMPLIANCE_003,P_COMPLIANCE_004,P_COMPLIANCE_005,P_CREDIT_002,P_EA_003,P_ORIG_002,P_RISK_001,P_RISK_002,P_RISK_003,P_SERVICING_006 s_processes__processes;
  class SYS_AML,SYS_ARCHREPO,SYS_CRM,SYS_GRC,SYS_KYC,SYS_MODEL s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Risk Governance & Compliance Management — Frameworks, Controls, Systems](../svg/capability-alignment--cap-rgov.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

34 entities, 49 relationships. Generated from the model; edit the model, not this file.
