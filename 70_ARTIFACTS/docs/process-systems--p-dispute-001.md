# Process cardholder dispute claim — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Process cardholder dispute claim — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_FRAUD_03{{"Dispute Intake &<br/>Provisional Credit"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_REGE_ACK[["Dispute acknowledgment<br/>timeliness"]]
    CTL_REGE_PROVCR[["Provisional credit within<br/>regulatory window"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_TRANSACTION[("Card transaction history")]
    DA_CUSTOMER_PROFILE[("Customer profile")]
    DA_DISPUTE_CASE[("Dispute case file")]
    DA_STATEMENTS[("Statement archive")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DISPUTE_001[\"Process cardholder dispute<br/>claim"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
    SYS_MOBILE["Cardholder mobile<br/>application"]
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_CONTACT["Contact center platform"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_BUREAU_GW["Credit bureau gateway"]
    SYS_DOC["Document management and<br/>archive"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_IAM["Identity and access<br/>management"]
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
    SYS_STATEMENTS["Statement Generation"]
  end

  P_DISPUTE_001 -->|"Primary"| SYS_DISPUTES_SAAS
  P_DISPUTE_001 -->|"Supporting"| SYS_CORE_LEDGER
  P_DISPUTE_001 -->|"Supporting"| SYS_CONTACT
  P_DISPUTE_001 -->|"Supporting"| SYS_DOC
  P_DISPUTE_001 -->|"Supporting"| SYS_CARDSVC_WEB
  P_DISPUTE_001 -->|"Supporting"| SYS_MOBILE
  P_DISPUTE_001 -->|"Supporting"| SYS_IAM
  P_DISPUTE_001 -->|"Supporting"| SYS_COLLECT_API
  P_DISPUTE_001 -->|"Supporting"| SYS_STATEMENTS
  P_DISPUTE_001 -->|"Supporting"| SYS_BUREAU_GW
  P_DISPUTE_001 -->|"Supporting"| SYS_CRM
  P_DISPUTE_001 -->|"Reads"| DA_CUSTOMER_PROFILE
  P_DISPUTE_001 -->|"Both"| DA_DISPUTE_CASE
  P_DISPUTE_001 -->|"Reads"| DA_STATEMENTS
  P_DISPUTE_001 -->|"Reads"| DA_TRANSACTION
  P_DISPUTE_001 -->|"governed by"| CTL_REGE_ACK
  P_DISPUTE_001 -->|"governed by"| CTL_REGE_PROVCR
  P_DISPUTE_001 -->|"supports"| CAP_FRAUD_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_FRAUD_03 s_capabilities__capabilities;
  class CTL_REGE_ACK,CTL_REGE_PROVCR s_controls__controls;
  class DA_CUSTOMER_PROFILE,DA_DISPUTE_CASE,DA_STATEMENTS,DA_TRANSACTION s_data_assets__data_assets;
  class P_DISPUTE_001 s_processes__processes;
  class SYS_BUREAU_GW,SYS_CARDSVC_WEB,SYS_COLLECT_API,SYS_CONTACT,SYS_CORE_LEDGER,SYS_CRM,SYS_DISPUTES_SAAS,SYS_DOC,SYS_IAM,SYS_MOBILE,SYS_STATEMENTS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Process cardholder dispute claim — Systems, Data and Controls](../svg/process-systems--p-dispute-001.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

19 entities, 18 relationships. Generated from the model; edit the model, not this file.
