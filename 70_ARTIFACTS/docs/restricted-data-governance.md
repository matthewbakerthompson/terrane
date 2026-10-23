# Restricted Data and What Governs It

The data assets classified Restricted, the system that masters each, the controls that govern them and the policies they are subject to. A Restricted asset with no control is the first thing an auditor will ask about.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Restricted Data and What Governs It
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Control["Control"]
    direction LR
    CTL_PCI_EVIDENCE[["Cardholder data scope and<br/>evidence maintenance"]]
    CTL_PRIV_REQ[["Consumer privacy request<br/>fulfillment"]]
    CTL_DAILY_RECON[["Daily settlement and<br/>clearing reconciliation"]]
    CTL_DQ_GATE[["Ingestion data quality<br/>gate"]]
    CTL_MASK_NONPROD[["Masked data outside<br/>production"]]
    CTL_RETENTION[["Retention schedule<br/>enforcement"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CARD_ACCOUNT[("Card account master")]
    DA_CARDSVC_OPERATIONAL[("Card Servicing operational<br/>data")]
    DA_TRANSACTION[("Card transaction history")]
    DA_COLLECT_OPERATIONAL[("Collections Workspace<br/>operational data")]
    DA_APPLICATION[("Credit application record")]
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
    DA_CUST360_CURATED[("Customer 360 curated<br/>dataset")]
    DA_CUSTOMER_PROFILE[("Customer profile")]
    DA_DISPUTES_VENDOR_FEED[("Dispute Management<br/>Platform vendor feed")]
    DA_LENDING_OPERATIONAL[("Installment Lending<br/>operational data")]
    DA_SCREENING_OUTCOMES[("NICE Actimize Screening<br/>outcomes")]
    DA_PAYMENT_INSTR[("Payment instructions")]
  end

  subgraph grp_Policy["Policy"]
    direction LR
    POL_PRIVACY[/"Consumer Privacy & Data<br/>Handling Policy"\]
    POL_RECORDS[/"Records Retention &<br/>Disposition Policy"\]
    POL_TPRM[/"Third-Party Risk<br/>Management Policy"\]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_CARDSVC_STORE["Card Servicing Datastore<br/>[Azure SQL]"]
    SYS_COLLECT_STORE["Collections Workspace<br/>Datastore<br/>[Azure SQL]"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_BUREAU_GW["Credit bureau gateway"]
    SYS_CUST360_PIPELINE["Customer 360 Pipeline<br/>[Snowflake Data Cloud +1]"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_LENDING_DB["Installment Lending<br/>Database<br/>[RDS]"]
    SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
    SYS_ORIG_DECISION["Originations decision<br/>engine"]
    SYS_PAYMENT_GW["Payment capture gateway"]
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
  end

  SYS_CORE_LEDGER -.->|"masters"| DA_CARD_ACCOUNT
  SYS_CRM -.->|"masters"| DA_CUSTOMER_PROFILE
  SYS_AUTH_SWITCH -.->|"masters"| DA_TRANSACTION
  SYS_ORIG_DECISION -.->|"masters"| DA_APPLICATION
  SYS_BUREAU_GW -.->|"masters"| DA_BUREAU_FILE
  SYS_PAYMENT_GW -.->|"masters"| DA_PAYMENT_INSTR
  SYS_CARDSVC_STORE -.->|"masters"| DA_CARDSVC_OPERATIONAL
  SYS_COLLECT_STORE -.->|"masters"| DA_COLLECT_OPERATIONAL
  SYS_CUST360_PIPELINE -.->|"masters"| DA_CUST360_CURATED
  SYS_DISPUTES_SAAS -.->|"masters"| DA_DISPUTES_VENDOR_FEED
  SYS_LENDING_DB -.->|"masters"| DA_LENDING_OPERATIONAL
  SYS_SCREENING_VENDOR -.->|"masters"| DA_SCREENING_OUTCOMES
  DA_DISPUTES_VENDOR_FEED -->|"governed by"| CTL_RETENTION
  DA_SCREENING_OUTCOMES -->|"governed by"| CTL_RETENTION
  DA_CARD_ACCOUNT -->|"governed by"| CTL_PCI_EVIDENCE
  DA_CARD_ACCOUNT -->|"governed by"| CTL_RETENTION
  DA_CUSTOMER_PROFILE -->|"governed by"| CTL_PRIV_REQ
  DA_TRANSACTION -->|"governed by"| CTL_DAILY_RECON
  DA_TRANSACTION -->|"governed by"| CTL_PCI_EVIDENCE
  DA_CUST360_CURATED -->|"governed by"| CTL_MASK_NONPROD
  DA_CUST360_CURATED -->|"governed by"| CTL_DQ_GATE
  DA_DISPUTES_VENDOR_FEED -->|"subject to"| POL_RECORDS
  DA_DISPUTES_VENDOR_FEED -->|"subject to"| POL_PRIVACY
  DA_SCREENING_OUTCOMES -->|"subject to"| POL_RECORDS
  DA_SCREENING_OUTCOMES -->|"subject to"| POL_PRIVACY
  DA_CARD_ACCOUNT -->|"subject to"| POL_PRIVACY
  DA_CARD_ACCOUNT -->|"subject to"| POL_RECORDS
  DA_CUSTOMER_PROFILE -->|"subject to"| POL_PRIVACY
  DA_TRANSACTION -->|"subject to"| POL_RECORDS
  DA_CUST360_CURATED -->|"subject to"| POL_PRIVACY
  DA_DISPUTES_VENDOR_FEED -->|"subject to"| POL_TPRM

  classDef s_controls__default fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.1px;
  classDef s_data_assets__restricted fill:#70c9a7,stroke:#047857,color:#0f172a,stroke-width:2.6px;
  classDef s_policies__default fill:#fecaca,stroke:#dc2626,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.1px;
  class CTL_DAILY_RECON,CTL_DQ_GATE,CTL_MASK_NONPROD,CTL_PCI_EVIDENCE,CTL_PRIV_REQ,CTL_RETENTION s_controls__default;
  class DA_APPLICATION,DA_BUREAU_FILE,DA_CARD_ACCOUNT,DA_CARDSVC_OPERATIONAL,DA_COLLECT_OPERATIONAL,DA_CUST360_CURATED,DA_CUSTOMER_PROFILE,DA_DISPUTES_VENDOR_FEED,DA_LENDING_OPERATIONAL,DA_PAYMENT_INSTR,DA_SCREENING_OUTCOMES,DA_TRANSACTION s_data_assets__restricted;
  class POL_PRIVACY,POL_RECORDS,POL_TPRM s_policies__default;
  class SYS_AUTH_SWITCH,SYS_BUREAU_GW,SYS_CARDSVC_STORE,SYS_COLLECT_STORE,SYS_CORE_LEDGER,SYS_CRM,SYS_CUST360_PIPELINE,SYS_DISPUTES_SAAS,SYS_LENDING_DB,SYS_ORIG_DECISION,SYS_PAYMENT_GW,SYS_SCREENING_VENDOR s_systems__default;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Control,grp_Data_Asset,grp_Policy,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Restricted Data and What Governs It](../svg/restricted-data-governance.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#dc2626` | policies |
| `#4338ca` | systems |

**classification** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | Restricted |
| 1.1px | default |

33 entities, 31 relationships. Generated from the model; edit the model, not this file.
