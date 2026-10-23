# Card transaction history — Where It Lives and Who Uses It

One data asset in full: the system that masters it, the systems that read or write it, the processes that use it, the controls that govern it and the policies it is subject to. The page a privacy or audit question starts from.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Card transaction history — Where It Lives and Who Uses It
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Control["Control"]
    direction LR
    CTL_PCI_EVIDENCE[["Cardholder data scope and<br/>evidence maintenance"]]
    CTL_DAILY_RECON[["Daily settlement and<br/>clearing reconciliation"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_TRANSACTION[("Card transaction history")]
  end

  subgraph grp_Policy["Policy"]
    direction LR
    POL_RECORDS[/"Records Retention &<br/>Disposition Policy"\]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_001[\"Assess interest, fees, and<br/>minimum payment"/]
    P_TPS_002[\"Convert client portfolio"/]
    P_STMT_GEN_001[\"Cut cycle and generate<br/>statement"/]
    P_FRAUD_001[\"Detect and action<br/>transaction fraud alert"/]
    P_PAYMENTS_002[\"Ingest clearing file and<br/>post transactions"/]
    P_PAYMENTS_001[\"Process authorization<br/>request"/]
    P_DISPUTE_001[\"Process cardholder dispute<br/>claim"/]
    P_NETWORK_RECON_001[\"Reconcile network<br/>settlement"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_MOBILE["Cardholder mobile<br/>application"]
    SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
    SYS_CUST360_PIPELINE["Customer 360 Pipeline<br/>[Snowflake Data Cloud +1]"]
    SYS_AML["Financial crimes platform"]
    SYS_RECON["Reconciliation platform"]
    SYS_STATEMENTS["Statement Generation"]
    SYS_FRAUD_DETECT["Transaction fraud<br/>detection"]
  end

  SYS_AUTH_SWITCH -.->|"masters"| DA_TRANSACTION
  SYS_CREDIT_DATA -->|"Read"| DA_TRANSACTION
  SYS_FRAUD_DETECT -->|"Read"| DA_TRANSACTION
  SYS_RECON -->|"Read"| DA_TRANSACTION
  SYS_AML -->|"Read"| DA_TRANSACTION
  SYS_MOBILE -->|"Read"| DA_TRANSACTION
  SYS_AUTH_SWITCH -->|"ReadWrite"| DA_TRANSACTION
  SYS_CARDSVC_API -->|"Read"| DA_TRANSACTION
  SYS_CUST360_PIPELINE -->|"Read"| DA_TRANSACTION
  SYS_STATEMENTS -->|"Read"| DA_TRANSACTION
  P_DISPUTE_001 -->|"Reads"| DA_TRANSACTION
  P_PAYMENTS_001 -->|"Writes"| DA_TRANSACTION
  P_PAYMENTS_002 -->|"Writes"| DA_TRANSACTION
  P_NETWORK_RECON_001 -->|"Reads"| DA_TRANSACTION
  P_SERVICING_001 -->|"Both"| DA_TRANSACTION
  P_STMT_GEN_001 -->|"Reads"| DA_TRANSACTION
  P_FRAUD_001 -->|"Reads"| DA_TRANSACTION
  P_TPS_002 -->|"Writes"| DA_TRANSACTION
  DA_TRANSACTION -->|"governed by"| CTL_DAILY_RECON
  DA_TRANSACTION -->|"governed by"| CTL_PCI_EVIDENCE
  DA_TRANSACTION -->|"subject to"| POL_RECORDS

  classDef s_controls__default fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.1px;
  classDef s_data_assets__restricted fill:#70c9a7,stroke:#047857,color:#0f172a,stroke-width:2.6px;
  classDef s_policies__default fill:#fecaca,stroke:#dc2626,color:#0f172a,stroke-width:1.1px;
  classDef s_processes__default fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.1px;
  class CTL_DAILY_RECON,CTL_PCI_EVIDENCE s_controls__default;
  class DA_TRANSACTION s_data_assets__restricted;
  class POL_RECORDS s_policies__default;
  class P_DISPUTE_001,P_FRAUD_001,P_NETWORK_RECON_001,P_PAYMENTS_001,P_PAYMENTS_002,P_SERVICING_001,P_STMT_GEN_001,P_TPS_002 s_processes__default;
  class SYS_AML,SYS_AUTH_SWITCH,SYS_CARDSVC_API,SYS_CREDIT_DATA,SYS_CUST360_PIPELINE,SYS_FRAUD_DETECT,SYS_MOBILE,SYS_RECON,SYS_STATEMENTS s_systems__default;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Control,grp_Data_Asset,grp_Policy,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card transaction history — Where It Lives and Who Uses It](../svg/data-asset-context--da-transaction.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#dc2626` | policies |
| `#0369a1` | processes |
| `#4338ca` | systems |

**classification** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | Restricted |
| 1.1px | default |

21 entities, 21 relationships. Generated from the model; edit the model, not this file.
