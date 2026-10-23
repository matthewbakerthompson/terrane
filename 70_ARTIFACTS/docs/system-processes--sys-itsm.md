# IT service management — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% IT service management — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_TECH_05{{"Business Continuity &<br/>Disaster Recovery"}}
    CAP_SEC_04{{"Data Protection &<br/>Cryptography"}}
    CAP_TECH_07{{"End-User Computing &<br/>Workplace Technology"}}
    CAP_STRAT_04{{"Enterprise Architecture &<br/>Change Portfolio"}}
    CAP_TECH_06{{"Enterprise Integration &<br/>API Management"}}
    CAP_SEC_01{{"Identity & Access<br/>Management"}}
    CAP_TECH_08{{"Quality Engineering &<br/>Testing"}}
    CAP_TECH_04{{"Release & Change<br/>Management"}}
    CAP_TECH_03{{"Service Management &<br/>Incident Response"}}
    CAP_TECH_01{{"Solution Delivery &<br/>Engineering"}}
    CAP_SEC_02{{"Threat Detection &<br/>Response"}}
    CAP_SEC_03{{"Vulnerability & Patch<br/>Management"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_EA_007[\"Assess change impact of a<br/>proposed system change"/]
    P_QE_008[\"Certify a release for<br/>production"/]
    P_TECH_001[\"Deliver software change"/]
    P_INFOSEC_002[\"Detect and respond to<br/>security event"/]
    P_TECH_003[\"Execute disaster recovery<br/>test"/]
    P_INFOSEC_004[\"Maintain cardholder data<br/>scope and evidence"/]
    P_EA_009[\"Maintain the application<br/>and technology inventory"/]
    P_APPDEV_007[\"Manage application<br/>configuration and feature<br/>flags"/]
    P_TECH_004[\"Onboard and operate<br/>integration"/]
    P_INFOSEC_001[\"Provision and certify<br/>access"/]
    P_INFOSEC_003[\"Remediate vulnerability"/]
    P_TECH_002[\"Respond to service<br/>incident"/]
    P_APPDEV_008[\"Support a production<br/>application"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_ITSM["IT service management<br/>[SaaS]"]
  end

  P_TECH_001 -->|"Supporting"| SYS_ITSM
  P_TECH_002 -->|"Primary"| SYS_ITSM
  P_TECH_003 -->|"Primary"| SYS_ITSM
  P_TECH_004 -->|"Primary"| SYS_ITSM
  P_INFOSEC_001 -->|"Supporting"| SYS_ITSM
  P_INFOSEC_002 -->|"Primary"| SYS_ITSM
  P_INFOSEC_003 -->|"Primary"| SYS_ITSM
  P_INFOSEC_004 -->|"Supporting"| SYS_ITSM
  P_EA_007 -->|"Supporting"| SYS_ITSM
  P_EA_009 -->|"Supporting"| SYS_ITSM
  P_QE_008 -->|"Supporting"| SYS_ITSM
  P_APPDEV_007 -->|"Supporting"| SYS_ITSM
  P_APPDEV_008 -->|"Primary"| SYS_ITSM
  P_TECH_001 -->|"supports"| CAP_TECH_01
  P_TECH_001 -->|"supports"| CAP_TECH_04
  P_TECH_002 -->|"supports"| CAP_TECH_03
  P_TECH_003 -->|"supports"| CAP_TECH_05
  P_TECH_004 -->|"supports"| CAP_TECH_06
  P_INFOSEC_001 -->|"supports"| CAP_SEC_01
  P_INFOSEC_002 -->|"supports"| CAP_SEC_02
  P_INFOSEC_003 -->|"supports"| CAP_SEC_03
  P_INFOSEC_004 -->|"supports"| CAP_SEC_04
  P_EA_007 -->|"supports"| CAP_STRAT_04
  P_EA_007 -->|"supports"| CAP_TECH_04
  P_EA_009 -->|"supports"| CAP_STRAT_04
  P_EA_009 -->|"supports"| CAP_TECH_07
  P_QE_008 -->|"supports"| CAP_TECH_08
  P_QE_008 -->|"supports"| CAP_TECH_04
  P_APPDEV_007 -->|"supports"| CAP_TECH_01
  P_APPDEV_007 -->|"supports"| CAP_TECH_04
  P_APPDEV_008 -->|"supports"| CAP_TECH_01
  P_APPDEV_008 -->|"supports"| CAP_TECH_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SEC_01,CAP_SEC_02,CAP_SEC_03,CAP_SEC_04,CAP_STRAT_04,CAP_TECH_01,CAP_TECH_03,CAP_TECH_04,CAP_TECH_05,CAP_TECH_06,CAP_TECH_07,CAP_TECH_08 s_capabilities__capabilities;
  class P_APPDEV_007,P_APPDEV_008,P_EA_007,P_EA_009,P_INFOSEC_001,P_INFOSEC_002,P_INFOSEC_003,P_INFOSEC_004,P_QE_008,P_TECH_001,P_TECH_002,P_TECH_003,P_TECH_004 s_processes__processes;
  class SYS_ITSM s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![IT service management — Processes and Capabilities](../svg/system-processes--sys-itsm.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

26 entities, 32 relationships. Generated from the model; edit the model, not this file.
