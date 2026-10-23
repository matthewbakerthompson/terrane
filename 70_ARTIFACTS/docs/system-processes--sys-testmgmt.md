# Test management and automation — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Test management and automation — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SEC_04{{"Data Protection &<br/>Cryptography"}}
    CAP_TECH_02{{"Platform & Infrastructure<br/>Operations"}}
    CAP_TECH_08{{"Quality Engineering &<br/>Testing"}}
    CAP_TECH_04{{"Release & Change<br/>Management"}}
    CAP_TECH_01{{"Solution Delivery &<br/>Engineering"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_QE_002[\"Build and maintain the<br/>automated regression suite"/]
    P_QE_008[\"Certify a release for<br/>production"/]
    P_QE_003[\"Execute functional and<br/>regression testing"/]
    P_QE_004[\"Execute performance and<br/>resilience testing"/]
    P_QE_006[\"Manage defects to closure"/]
    P_QE_001[\"Plan the test strategy for<br/>a release"/]
    P_QE_007[\"Provision test<br/>environments and masked<br/>data"/]
    P_APPDEV_004[\"Run the build and<br/>deployment pipeline"/]
    P_QE_005[\"Run user acceptance<br/>testing with the business"/]
    P_QE_009[\"Verify a release in<br/>production"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_TESTMGMT["Test management and<br/>automation<br/>[SaaS]"]
  end

  P_QE_001 -->|"Primary"| SYS_TESTMGMT
  P_QE_002 -->|"Primary"| SYS_TESTMGMT
  P_QE_003 -->|"Primary"| SYS_TESTMGMT
  P_QE_004 -->|"Primary"| SYS_TESTMGMT
  P_QE_005 -->|"Primary"| SYS_TESTMGMT
  P_QE_006 -->|"Supporting"| SYS_TESTMGMT
  P_QE_007 -->|"Primary"| SYS_TESTMGMT
  P_QE_008 -->|"Primary"| SYS_TESTMGMT
  P_QE_009 -->|"Supporting"| SYS_TESTMGMT
  P_APPDEV_004 -->|"Supporting"| SYS_TESTMGMT
  P_QE_001 -->|"supports"| CAP_TECH_08
  P_QE_002 -->|"supports"| CAP_TECH_08
  P_QE_003 -->|"supports"| CAP_TECH_08
  P_QE_004 -->|"supports"| CAP_TECH_08
  P_QE_004 -->|"supports"| CAP_TECH_02
  P_QE_005 -->|"supports"| CAP_TECH_08
  P_QE_006 -->|"supports"| CAP_TECH_08
  P_QE_007 -->|"supports"| CAP_TECH_08
  P_QE_007 -->|"supports"| CAP_TECH_02
  P_QE_007 -->|"supports"| CAP_SEC_04
  P_QE_008 -->|"supports"| CAP_TECH_08
  P_QE_008 -->|"supports"| CAP_TECH_04
  P_QE_009 -->|"supports"| CAP_TECH_08
  P_QE_009 -->|"supports"| CAP_TECH_04
  P_APPDEV_004 -->|"supports"| CAP_TECH_01
  P_APPDEV_004 -->|"supports"| CAP_TECH_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SEC_04,CAP_TECH_01,CAP_TECH_02,CAP_TECH_04,CAP_TECH_08 s_capabilities__capabilities;
  class P_APPDEV_004,P_QE_001,P_QE_002,P_QE_003,P_QE_004,P_QE_005,P_QE_006,P_QE_007,P_QE_008,P_QE_009 s_processes__processes;
  class SYS_TESTMGMT s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Test management and automation — Processes and Capabilities](../svg/system-processes--sys-testmgmt.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

16 entities, 26 relationships. Generated from the model; edit the model, not this file.
