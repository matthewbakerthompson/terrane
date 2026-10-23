# Customer Servicing & Care — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Customer Servicing & Care — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_02{{"Account Maintenance &<br/>Servicing Requests"}}
    CAP_SERV_05{{"Complaint Capture &<br/>Resolution"}}
    CAP_SERV_01{{"Contact Handling & Routing"}}
    CAP_SERV_04{{"Correspondence &<br/>Notification Management"}}
    CAP_SERV{{"Customer Servicing & Care"}}
    CAP_SERV_03{{"Digital Self-Service"}}
    CAP_SERV_07{{"Hardship & Payment<br/>Assistance"}}
    CAP_SERV_06{{"Servicing Knowledge &<br/>Agent Enablement"}}
    CAP_SERV_08{{"Servicing Quality<br/>Monitoring"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_COMPLAINT_REG[["Complaint regulatory<br/>routing"]]
    CTL_REGE_DETERM[["Dispute determination<br/>timeliness and notice"]]
    CTL_NOTICE_CONTENT[["Notice content and<br/>delivery evidence"]]
    CTL_SCRA_MLA[["Servicemember protections<br/>screening"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_011[\"Administer secured card<br/>deposit lifecycle"/]
    P_SERVICING_012[\"Apply servicemember and<br/>military lending<br/>protections"/]
    P_SERVICING_006[\"Capture and resolve<br/>complaint"/]
    P_SERVICING_008[\"Enroll account in hardship<br/>or assistance program"/]
    P_DIGITAL_001[\"Enroll cardholder in<br/>digital servicing"/]
    P_SERVICING_004[\"Execute account<br/>maintenance request"/]
    P_DISPUTE_004[\"Finalize dispute<br/>determination and notify"/]
    P_SERVICING_007[\"Generate and deliver<br/>required notice"/]
    P_CUST_INQ_001[\"Handle cardholder inquiry"/]
    P_SERVICING_009[\"Maintain servicing<br/>knowledge content"/]
    P_SERVICING_010[\"Monitor and score<br/>servicing interactions"/]
    P_DIGITAL_002[\"Serve digital self-service<br/>transaction"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_CONTACT["Contact center platform"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_DOC["Document management and<br/>archive"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
    SYS_STATEMENTS["Statement Generation"]
  end

  CAP_SERV_01 -->|"part of"| CAP_SERV
  CAP_SERV_02 -->|"part of"| CAP_SERV
  CAP_SERV_03 -->|"part of"| CAP_SERV
  CAP_SERV_04 -->|"part of"| CAP_SERV
  CAP_SERV_05 -->|"part of"| CAP_SERV
  CAP_SERV_06 -->|"part of"| CAP_SERV
  CAP_SERV_07 -->|"part of"| CAP_SERV
  CAP_SERV_08 -->|"part of"| CAP_SERV
  CAP_SERV -->|"Aligned to"| FW_BIAN
  CAP_SERV_01 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_SERV_02 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_SERV_03 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_SERV_04 -->|"Business Support #gt; D…"| FW_BIAN
  CAP_SERV_05 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_SERV_06 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_SERV_07 -->|"Operations and Executio…"| FW_BIAN
  CAP_SERV_08 -->|"Sales and Service #gt;…"| FW_BIAN
  P_CUST_INQ_001 -->|"supported by"| CAP_SERV_01
  P_CUST_INQ_001 -->|"supported by"| CAP_SERV_02
  P_SERVICING_004 -->|"supported by"| CAP_SERV_02
  P_SERVICING_006 -->|"supported by"| CAP_SERV_05
  P_SERVICING_007 -->|"supported by"| CAP_SERV_04
  P_SERVICING_008 -->|"supported by"| CAP_SERV_07
  P_SERVICING_009 -->|"supported by"| CAP_SERV_06
  P_SERVICING_010 -->|"supported by"| CAP_SERV_08
  P_DIGITAL_001 -->|"supported by"| CAP_SERV_03
  P_DIGITAL_002 -->|"supported by"| CAP_SERV_03
  P_DISPUTE_004 -->|"supported by"| CAP_SERV_04
  P_SERVICING_011 -->|"supported by"| CAP_SERV_02
  P_SERVICING_012 -->|"supported by"| CAP_SERV_02
  CAP_SERV -->|"governed by"| CTL_COMPLAINT_REG
  CAP_SERV -->|"governed by"| CTL_NOTICE_CONTENT
  CAP_SERV -->|"governed by"| CTL_REGE_DETERM
  CAP_SERV -->|"governed by"| CTL_SCRA_MLA
  CAP_SERV_02 -->|"governed by"| CTL_SCRA_MLA
  CAP_SERV_04 -->|"governed by"| CTL_NOTICE_CONTENT
  CAP_SERV_04 -->|"governed by"| CTL_REGE_DETERM
  CAP_SERV_05 -->|"governed by"| CTL_COMPLAINT_REG
  SYS_CARDSVC_API -->|"realizes"| CAP_SERV
  SYS_CARDSVC_WEB -->|"realizes"| CAP_SERV
  SYS_CORE_LEDGER -->|"realizes"| CAP_SERV
  SYS_CRM -->|"realizes"| CAP_SERV
  SYS_STATEMENTS -->|"realizes"| CAP_SERV
  SYS_CARDSVC_WEB -->|"realizes"| CAP_SERV_03
  SYS_COLLECT_API -->|"realizes"| CAP_SERV_07
  SYS_CONTACT -->|"realizes"| CAP_SERV_01
  SYS_CONTACT -->|"realizes"| CAP_SERV_02
  SYS_CONTACT -->|"realizes"| CAP_SERV_08
  SYS_CORE_LEDGER -->|"realizes"| CAP_SERV_02
  SYS_CRM -->|"realizes"| CAP_SERV_05
  SYS_CRM -->|"realizes"| CAP_SERV_06
  SYS_DISPUTES_SAAS -->|"realizes"| CAP_SERV_04
  SYS_DOC -->|"realizes"| CAP_SERV_04

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SERV,CAP_SERV_01,CAP_SERV_02,CAP_SERV_03,CAP_SERV_04,CAP_SERV_05,CAP_SERV_06,CAP_SERV_07,CAP_SERV_08 s_capabilities__capabilities;
  class CTL_COMPLAINT_REG,CTL_NOTICE_CONTENT,CTL_REGE_DETERM,CTL_SCRA_MLA s_controls__controls;
  class FW_BIAN s_frameworks__frameworks;
  class P_CUST_INQ_001,P_DIGITAL_001,P_DIGITAL_002,P_DISPUTE_004,P_SERVICING_004,P_SERVICING_006,P_SERVICING_007,P_SERVICING_008,P_SERVICING_009,P_SERVICING_010,P_SERVICING_011,P_SERVICING_012 s_processes__processes;
  class SYS_CARDSVC_API,SYS_CARDSVC_WEB,SYS_COLLECT_API,SYS_CONTACT,SYS_CORE_LEDGER,SYS_CRM,SYS_DISPUTES_SAAS,SYS_DOC,SYS_STATEMENTS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Customer Servicing & Care — Frameworks, Controls, Systems](../svg/capability-alignment--cap-serv.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

35 entities, 53 relationships. Generated from the model; edit the model, not this file.
