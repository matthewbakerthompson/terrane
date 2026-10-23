# Work and change tracking — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Work and change tracking — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_TPS_01{{"Client Program<br/>Configuration & Setup"}}
    CAP_TPS_06{{"Client-Directed Change<br/>Management"}}
    CAP_TPRM_02{{"Contract & SLA Management"}}
    CAP_STRAT_04{{"Enterprise Architecture &<br/>Change Portfolio"}}
    CAP_TECH_06{{"Enterprise Integration &<br/>API Management"}}
    CAP_RGOV_04{{"Issue & Remediation<br/>Management"}}
    CAP_PROD_02{{"Pricing, Fee & APR<br/>Management"}}
    CAP_PROD_01{{"Product Design &<br/>Configuration"}}
    CAP_PROD_05{{"Product Lifecycle &<br/>Retirement"}}
    CAP_TECH_08{{"Quality Engineering &<br/>Testing"}}
    CAP_RGOV_02{{"Regulatory Change<br/>Management"}}
    CAP_TECH_04{{"Release & Change<br/>Management"}}
    CAP_TECH_01{{"Solution Delivery &<br/>Engineering"}}
    CAP_TPRM_04{{"Vendor Exit & Continuity<br/>Planning"}}
    CAP_TPRM_01{{"Vendor Sourcing & Due<br/>Diligence"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_COMPLIANCE_001[\"Assess and land regulatory<br/>change"/]
    P_TPS_001[\"Configure client program"/]
    P_TECH_001[\"Deliver software change"/]
    P_PRODUCT_001[\"Design and approve product<br/>change"/]
    P_APPDEV_002[\"Design and build a<br/>software increment"/]
    P_VENDORMGMT_003[\"Execute supplier exit"/]
    P_TPS_008[\"Intake and deliver<br/>client-directed change"/]
    P_PRODUCT_003[\"Launch product to market"/]
    P_QE_006[\"Manage defects to closure"/]
    P_RISK_001[\"Manage issue and<br/>remediation to closure"/]
    P_APPDEV_006[\"Manage technical debt"/]
    P_VENDORMGMT_001[\"Onboard and diligence<br/>supplier"/]
    P_TECH_004[\"Onboard and operate<br/>integration"/]
    P_QE_001[\"Plan the test strategy for<br/>a release"/]
    P_APPDEV_001[\"Refine and prioritize the<br/>product backlog"/]
    P_EA_002[\"Review solution<br/>architecture for an<br/>initiative"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_WORKTRACK["Work and change tracking<br/>[SaaS]"]
  end

  P_TPS_001 -->|"Supporting"| SYS_WORKTRACK
  P_TPS_008 -->|"Primary"| SYS_WORKTRACK
  P_COMPLIANCE_001 -->|"Supporting"| SYS_WORKTRACK
  P_RISK_001 -->|"Supporting"| SYS_WORKTRACK
  P_TECH_001 -->|"Primary"| SYS_WORKTRACK
  P_TECH_004 -->|"Supporting"| SYS_WORKTRACK
  P_VENDORMGMT_001 -->|"Supporting"| SYS_WORKTRACK
  P_VENDORMGMT_003 -->|"Supporting"| SYS_WORKTRACK
  P_PRODUCT_001 -->|"Supporting"| SYS_WORKTRACK
  P_PRODUCT_003 -->|"Supporting"| SYS_WORKTRACK
  P_EA_002 -->|"Supporting"| SYS_WORKTRACK
  P_QE_001 -->|"Supporting"| SYS_WORKTRACK
  P_QE_006 -->|"Primary"| SYS_WORKTRACK
  P_APPDEV_001 -->|"Primary"| SYS_WORKTRACK
  P_APPDEV_002 -->|"Supporting"| SYS_WORKTRACK
  P_APPDEV_006 -->|"Primary"| SYS_WORKTRACK
  P_TPS_001 -->|"supports"| CAP_TPS_01
  P_TPS_008 -->|"supports"| CAP_TPS_06
  P_COMPLIANCE_001 -->|"supports"| CAP_RGOV_02
  P_RISK_001 -->|"supports"| CAP_RGOV_04
  P_TECH_001 -->|"supports"| CAP_TECH_01
  P_TECH_001 -->|"supports"| CAP_TECH_04
  P_TECH_004 -->|"supports"| CAP_TECH_06
  P_VENDORMGMT_001 -->|"supports"| CAP_TPRM_01
  P_VENDORMGMT_001 -->|"supports"| CAP_TPRM_02
  P_VENDORMGMT_003 -->|"supports"| CAP_TPRM_04
  P_PRODUCT_001 -->|"supports"| CAP_PROD_01
  P_PRODUCT_001 -->|"supports"| CAP_PROD_02
  P_PRODUCT_003 -->|"supports"| CAP_PROD_05
  P_EA_002 -->|"supports"| CAP_STRAT_04
  P_QE_001 -->|"supports"| CAP_TECH_08
  P_QE_006 -->|"supports"| CAP_TECH_08
  P_APPDEV_001 -->|"supports"| CAP_TECH_01
  P_APPDEV_002 -->|"supports"| CAP_TECH_01
  P_APPDEV_006 -->|"supports"| CAP_TECH_01
  P_APPDEV_006 -->|"supports"| CAP_STRAT_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PROD_01,CAP_PROD_02,CAP_PROD_05,CAP_RGOV_02,CAP_RGOV_04,CAP_STRAT_04,CAP_TECH_01,CAP_TECH_04,CAP_TECH_06,CAP_TECH_08,CAP_TPRM_01,CAP_TPRM_02,CAP_TPRM_04,CAP_TPS_01,CAP_TPS_06 s_capabilities__capabilities;
  class P_APPDEV_001,P_APPDEV_002,P_APPDEV_006,P_COMPLIANCE_001,P_EA_002,P_PRODUCT_001,P_PRODUCT_003,P_QE_001,P_QE_006,P_RISK_001,P_TECH_001,P_TECH_004,P_TPS_001,P_TPS_008,P_VENDORMGMT_001,P_VENDORMGMT_003 s_processes__processes;
  class SYS_WORKTRACK s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Work and change tracking — Processes and Capabilities](../svg/system-processes--sys-worktrack.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

32 entities, 36 relationships. Generated from the model; edit the model, not this file.
