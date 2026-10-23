# Contact center platform — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Contact center platform — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_02{{"Account Maintenance &<br/>Servicing Requests"}}
    CAP_ORIG_01{{"Application Capture"}}
    CAP_COLL_07{{"Collections Compliance<br/>Oversight"}}
    CAP_SERV_05{{"Complaint Capture &<br/>Resolution"}}
    CAP_RGOV_06{{"Complaint Oversight &<br/>UDAAP Management"}}
    CAP_SERV_01{{"Contact Handling & Routing"}}
    CAP_FRAUD_03{{"Dispute Intake &<br/>Provisional Credit"}}
    CAP_SEC_01{{"Identity & Access<br/>Management"}}
    CAP_FRAUD_06{{"Identity Theft & Account<br/>Takeover Response"}}
    CAP_COLL_02{{"Outbound Contact<br/>Operations"}}
    CAP_SERV_08{{"Servicing Quality<br/>Monitoring"}}
    CAP_FRAUD_01{{"Transaction Fraud<br/>Detection & Strategy"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_005[\"Authenticate cardholder"/]
    P_SERVICING_006[\"Capture and resolve<br/>complaint"/]
    P_ORIG_001[\"Capture card application"/]
    P_FRAUD_001[\"Detect and action<br/>transaction fraud alert"/]
    P_SERVICING_004[\"Execute account<br/>maintenance request"/]
    P_COLLECTIONS_002[\"Execute outbound<br/>collections contact"/]
    P_CUST_INQ_001[\"Handle cardholder inquiry"/]
    P_SERVICING_010[\"Monitor and score<br/>servicing interactions"/]
    P_DISPUTE_001[\"Process cardholder dispute<br/>claim"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CONTACT["Contact center platform"]
  end

  P_ORIG_001 -->|"Supporting"| SYS_CONTACT
  P_CUST_INQ_001 -->|"Primary"| SYS_CONTACT
  P_SERVICING_004 -->|"Supporting"| SYS_CONTACT
  P_SERVICING_005 -->|"Supporting"| SYS_CONTACT
  P_SERVICING_006 -->|"Supporting"| SYS_CONTACT
  P_SERVICING_010 -->|"Primary"| SYS_CONTACT
  P_FRAUD_001 -->|"Supporting"| SYS_CONTACT
  P_DISPUTE_001 -->|"Supporting"| SYS_CONTACT
  P_COLLECTIONS_002 -->|"Supporting"| SYS_CONTACT
  P_ORIG_001 -->|"supports"| CAP_ORIG_01
  P_CUST_INQ_001 -->|"supports"| CAP_SERV_01
  P_CUST_INQ_001 -->|"supports"| CAP_SERV_02
  P_SERVICING_004 -->|"supports"| CAP_SERV_02
  P_SERVICING_005 -->|"supports"| CAP_SEC_01
  P_SERVICING_005 -->|"supports"| CAP_FRAUD_06
  P_SERVICING_006 -->|"supports"| CAP_SERV_05
  P_SERVICING_006 -->|"supports"| CAP_RGOV_06
  P_SERVICING_010 -->|"supports"| CAP_SERV_08
  P_FRAUD_001 -->|"supports"| CAP_FRAUD_01
  P_DISPUTE_001 -->|"supports"| CAP_FRAUD_03
  P_COLLECTIONS_002 -->|"supports"| CAP_COLL_02
  P_COLLECTIONS_002 -->|"supports"| CAP_COLL_07

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_COLL_02,CAP_COLL_07,CAP_FRAUD_01,CAP_FRAUD_03,CAP_FRAUD_06,CAP_ORIG_01,CAP_RGOV_06,CAP_SEC_01,CAP_SERV_01,CAP_SERV_02,CAP_SERV_05,CAP_SERV_08 s_capabilities__capabilities;
  class P_COLLECTIONS_002,P_CUST_INQ_001,P_DISPUTE_001,P_FRAUD_001,P_ORIG_001,P_SERVICING_004,P_SERVICING_005,P_SERVICING_006,P_SERVICING_010 s_processes__processes;
  class SYS_CONTACT s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Contact center platform — Processes and Capabilities](../svg/system-processes--sys-contact.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

22 entities, 22 relationships. Generated from the model; edit the model, not this file.
