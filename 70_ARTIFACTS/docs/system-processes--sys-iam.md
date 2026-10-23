# Identity and access management — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Identity and access management — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_03{{"Digital Self-Service"}}
    CAP_FRAUD_03{{"Dispute Intake &<br/>Provisional Credit"}}
    CAP_STRAT_04{{"Enterprise Architecture &<br/>Change Portfolio"}}
    CAP_SEC_01{{"Identity & Access<br/>Management"}}
    CAP_FRAUD_06{{"Identity Theft & Account<br/>Takeover Response"}}
    CAP_DATA_07{{"Records Retention &<br/>Disposition"}}
    CAP_TECH_01{{"Solution Delivery &<br/>Engineering"}}
    CAP_SEC_02{{"Threat Detection &<br/>Response"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_005[\"Authenticate cardholder"/]
    P_APPDEV_009[\"Decommission an<br/>application"/]
    P_INFOSEC_002[\"Detect and respond to<br/>security event"/]
    P_DIGITAL_001[\"Enroll cardholder in<br/>digital servicing"/]
    P_DISPUTE_001[\"Process cardholder dispute<br/>claim"/]
    P_INFOSEC_001[\"Provision and certify<br/>access"/]
    P_FRAUD_003[\"Respond to account<br/>takeover event"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_IAM["Identity and access<br/>management"]
  end

  P_SERVICING_005 -->|"Primary"| SYS_IAM
  P_DIGITAL_001 -->|"Supporting"| SYS_IAM
  P_FRAUD_003 -->|"Supporting"| SYS_IAM
  P_DISPUTE_001 -->|"Supporting"| SYS_IAM
  P_INFOSEC_001 -->|"Primary"| SYS_IAM
  P_INFOSEC_002 -->|"Supporting"| SYS_IAM
  P_APPDEV_009 -->|"Supporting"| SYS_IAM
  P_SERVICING_005 -->|"supports"| CAP_SEC_01
  P_SERVICING_005 -->|"supports"| CAP_FRAUD_06
  P_DIGITAL_001 -->|"supports"| CAP_SERV_03
  P_FRAUD_003 -->|"supports"| CAP_FRAUD_06
  P_DISPUTE_001 -->|"supports"| CAP_FRAUD_03
  P_INFOSEC_001 -->|"supports"| CAP_SEC_01
  P_INFOSEC_002 -->|"supports"| CAP_SEC_02
  P_APPDEV_009 -->|"supports"| CAP_TECH_01
  P_APPDEV_009 -->|"supports"| CAP_STRAT_04
  P_APPDEV_009 -->|"supports"| CAP_DATA_07

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_DATA_07,CAP_FRAUD_03,CAP_FRAUD_06,CAP_SEC_01,CAP_SEC_02,CAP_SERV_03,CAP_STRAT_04,CAP_TECH_01 s_capabilities__capabilities;
  class P_APPDEV_009,P_DIGITAL_001,P_DISPUTE_001,P_FRAUD_003,P_INFOSEC_001,P_INFOSEC_002,P_SERVICING_005 s_processes__processes;
  class SYS_IAM s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Identity and access management — Processes and Capabilities](../svg/system-processes--sys-iam.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

16 entities, 17 relationships. Generated from the model; edit the model, not this file.
