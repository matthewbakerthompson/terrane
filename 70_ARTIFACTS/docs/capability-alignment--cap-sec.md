# Information Security & Privacy — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Information Security & Privacy — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SEC_04{{"Data Protection &<br/>Cryptography"}}
    CAP_SEC_01{{"Identity & Access<br/>Management"}}
    CAP_SEC{{"Information Security &<br/>Privacy"}}
    CAP_SEC_05{{"Privacy Management"}}
    CAP_SEC_02{{"Threat Detection &<br/>Response"}}
    CAP_SEC_03{{"Vulnerability & Patch<br/>Management"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_AUTH_POLICY[["Cardholder authentication<br/>to policy"]]
    CTL_PCI_EVIDENCE[["Cardholder data scope and<br/>evidence maintenance"]]
    CTL_PRIV_REQ[["Consumer privacy request<br/>fulfillment"]]
    CTL_MASK_NONPROD[["Masked data outside<br/>production"]]
    CTL_ACCESS_CERT[["Periodic access<br/>certification"]]
    CTL_IR_PLAYBOOK[["Security incident response<br/>execution"]]
    CTL_VULN_SLA[["Vulnerability remediation<br/>service level"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_CRI["CRI Profile"]
    FW_ISO27001["ISO/IEC 27001"]
    FW_NIST_CSF["NIST Cybersecurity<br/>Framework"]
    FW_PCI_DSS["PCI DSS"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_005[\"Authenticate cardholder"/]
    P_INFOSEC_002[\"Detect and respond to<br/>security event"/]
    P_PRIVACY_001[\"Fulfill consumer privacy<br/>request"/]
    P_INFOSEC_004[\"Maintain cardholder data<br/>scope and evidence"/]
    P_INFOSEC_001[\"Provision and certify<br/>access"/]
    P_QE_007[\"Provision test<br/>environments and masked<br/>data"/]
    P_INFOSEC_003[\"Remediate vulnerability"/]
    P_APPDEV_005[\"Scan code and dependencies<br/>for security defects"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
    SYS_IAM["Identity and access<br/>management"]
    SYS_ITSM["IT service management<br/>[SaaS]"]
    SYS_SCM["Source control and CI/CD<br/>pipeline<br/>[SaaS]"]
    SYS_TESTMGMT["Test management and<br/>automation<br/>[SaaS]"]
  end

  CAP_SEC_01 -->|"part of"| CAP_SEC
  CAP_SEC_02 -->|"part of"| CAP_SEC
  CAP_SEC_03 -->|"part of"| CAP_SEC
  CAP_SEC_04 -->|"part of"| CAP_SEC
  CAP_SEC_05 -->|"part of"| CAP_SEC
  CAP_SEC -->|"Aligned to"| FW_NIST_CSF
  CAP_SEC -->|"Governed by"| FW_ISO27001
  CAP_SEC -->|"Governed by"| FW_PCI_DSS
  CAP_SEC -->|"Governed by"| FW_CRI
  CAP_SEC_01 -->|"Protect #gt; PR.AA-01"| FW_CRI
  CAP_SEC_02 -->|"Detect #gt; DE.CM-01"| FW_CRI
  CAP_SEC_03 -->|"Identify #gt; ID.RA-01"| FW_CRI
  CAP_SEC_04 -->|"Protect #gt; PR.DS-01"| FW_CRI
  CAP_SEC_05 -->|"Govern #gt; GV.PO-01"| FW_CRI
  P_SERVICING_005 -->|"supported by"| CAP_SEC_01
  P_INFOSEC_001 -->|"supported by"| CAP_SEC_01
  P_INFOSEC_002 -->|"supported by"| CAP_SEC_02
  P_INFOSEC_003 -->|"supported by"| CAP_SEC_03
  P_INFOSEC_004 -->|"supported by"| CAP_SEC_04
  P_PRIVACY_001 -->|"supported by"| CAP_SEC_05
  P_QE_007 -->|"supported by"| CAP_SEC_04
  P_APPDEV_005 -->|"supported by"| CAP_SEC_03
  CAP_SEC -->|"governed by"| CTL_ACCESS_CERT
  CAP_SEC -->|"governed by"| CTL_AUTH_POLICY
  CAP_SEC -->|"governed by"| CTL_IR_PLAYBOOK
  CAP_SEC -->|"governed by"| CTL_MASK_NONPROD
  CAP_SEC -->|"governed by"| CTL_PCI_EVIDENCE
  CAP_SEC -->|"governed by"| CTL_PRIV_REQ
  CAP_SEC -->|"governed by"| CTL_VULN_SLA
  CAP_SEC_01 -->|"governed by"| CTL_ACCESS_CERT
  CAP_SEC_01 -->|"governed by"| CTL_AUTH_POLICY
  CAP_SEC_02 -->|"governed by"| CTL_IR_PLAYBOOK
  CAP_SEC_03 -->|"governed by"| CTL_VULN_SLA
  CAP_SEC_04 -->|"governed by"| CTL_MASK_NONPROD
  CAP_SEC_04 -->|"governed by"| CTL_PCI_EVIDENCE
  CAP_SEC_05 -->|"governed by"| CTL_PRIV_REQ
  SYS_IDENTITY_SVC -->|"realizes"| CAP_SEC_01
  SYS_GRC -->|"realizes"| CAP_SEC_04
  SYS_GRC -->|"realizes"| CAP_SEC_05
  SYS_IAM -->|"realizes"| CAP_SEC_01
  SYS_ITSM -->|"realizes"| CAP_SEC_02
  SYS_ITSM -->|"realizes"| CAP_SEC_03
  SYS_SCM -->|"realizes"| CAP_SEC_03
  SYS_TESTMGMT -->|"realizes"| CAP_SEC_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SEC,CAP_SEC_01,CAP_SEC_02,CAP_SEC_03,CAP_SEC_04,CAP_SEC_05 s_capabilities__capabilities;
  class CTL_ACCESS_CERT,CTL_AUTH_POLICY,CTL_IR_PLAYBOOK,CTL_MASK_NONPROD,CTL_PCI_EVIDENCE,CTL_PRIV_REQ,CTL_VULN_SLA s_controls__controls;
  class FW_CRI,FW_ISO27001,FW_NIST_CSF,FW_PCI_DSS s_frameworks__frameworks;
  class P_APPDEV_005,P_INFOSEC_001,P_INFOSEC_002,P_INFOSEC_003,P_INFOSEC_004,P_PRIVACY_001,P_QE_007,P_SERVICING_005 s_processes__processes;
  class SYS_GRC,SYS_IAM,SYS_IDENTITY_SVC,SYS_ITSM,SYS_SCM,SYS_TESTMGMT s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Information Security & Privacy — Frameworks, Controls, Systems](../svg/capability-alignment--cap-sec.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

31 entities, 44 relationships. Generated from the model; edit the model, not this file.
