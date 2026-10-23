# Data & Analytics Management — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Data & Analytics Management — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_DATA_06{{"AI/ML Model Operations"}}
    CAP_DATA_04{{"Analytics, Reporting & BI"}}
    CAP_DATA{{"Data & Analytics<br/>Management"}}
    CAP_DATA_01{{"Data Governance &<br/>Stewardship"}}
    CAP_DATA_03{{"Data Quality Management"}}
    CAP_DATA_02{{"Data Sourcing &<br/>Integration"}}
    CAP_DATA_05{{"Metadata, Lineage &<br/>Catalog"}}
    CAP_DATA_07{{"Records Retention &<br/>Disposition"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_CLIENT_SLA[["Client reporting and feed<br/>monitoring"]]
    CTL_CONV_VERIFY[["Conversion balance and<br/>record verification"]]
    CTL_DQ_GATE[["Ingestion data quality<br/>gate"]]
    CTL_REGRPT_CERT[["Regulatory report<br/>certification"]]
    CTL_RETENTION[["Retention schedule<br/>enforcement"]]
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
    FW_DMBOK["DAMA-DMBOK"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_TPS_002[\"Convert client portfolio"/]
    P_APPDEV_009[\"Decommission an<br/>application"/]
    P_DATAENG_002[\"Deploy and monitor<br/>production model"/]
    P_TPS_005[\"Exchange client data feed"/]
    P_DATAGOV_004[\"Execute records retention<br/>and disposition"/]
    P_DATAENG_001[\"Ingest and integrate<br/>source data"/]
    P_DATAGOV_002[\"Measure and remediate data<br/>quality"/]
    P_DATAGOV_001[\"Onboard and classify data<br/>asset"/]
    P_REG_DATA_PREP_001[\"Prepare regulatory<br/>reporting data"/]
    P_DATAGOV_003[\"Publish metadata and<br/>lineage to catalog"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_ARCHREPO["Architecture repository<br/>[SaaS]"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_CUST360_PIPELINE["Customer 360 Pipeline<br/>[Snowflake Data Cloud +1]"]
    SYS_CUST360_SEMANTIC["Customer 360 Semantic<br/>Layer<br/>[Snowflake Data Cloud]"]
    SYS_DOC["Document management and<br/>archive"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_CATALOG["Governance catalog<br/>[Collibra Data Intelligence]"]
    SYS_MODEL["Model platform"]
    SYS_CLIENT_PORTAL["Servicing client portal"]
  end

  CAP_DATA_01 -->|"part of"| CAP_DATA
  CAP_DATA_02 -->|"part of"| CAP_DATA
  CAP_DATA_03 -->|"part of"| CAP_DATA
  CAP_DATA_04 -->|"part of"| CAP_DATA
  CAP_DATA_05 -->|"part of"| CAP_DATA
  CAP_DATA_06 -->|"part of"| CAP_DATA
  CAP_DATA_07 -->|"part of"| CAP_DATA
  CAP_DATA -->|"Aligned to"| FW_DMBOK
  CAP_DATA_01 -->|"Data Governance"| FW_DMBOK
  CAP_DATA_02 -->|"Data Integration and In…"| FW_DMBOK
  CAP_DATA_03 -->|"Data Quality"| FW_DMBOK
  CAP_DATA_04 -->|"Data Warehousing and Bu…"| FW_DMBOK
  CAP_DATA_05 -->|"Metadata Management"| FW_DMBOK
  CAP_DATA_06 -->|"Risk and Compliance #gt…"| FW_BIAN
  CAP_DATA_07 -->|"Business Support #gt; D…"| FW_BIAN
  CAP_DATA_07 -->|"Document and Content Ma…"| FW_DMBOK
  P_TPS_002 -->|"supported by"| CAP_DATA_02
  P_TPS_005 -->|"supported by"| CAP_DATA_02
  P_REG_DATA_PREP_001 -->|"supported by"| CAP_DATA_03
  P_DATAGOV_001 -->|"supported by"| CAP_DATA_01
  P_DATAGOV_002 -->|"supported by"| CAP_DATA_03
  P_DATAGOV_003 -->|"supported by"| CAP_DATA_05
  P_DATAGOV_004 -->|"supported by"| CAP_DATA_07
  P_DATAENG_001 -->|"supported by"| CAP_DATA_02
  P_DATAENG_002 -->|"supported by"| CAP_DATA_06
  P_APPDEV_009 -->|"supported by"| CAP_DATA_07
  CAP_DATA -->|"governed by"| CTL_CLIENT_SLA
  CAP_DATA -->|"governed by"| CTL_CONV_VERIFY
  CAP_DATA -->|"governed by"| CTL_DQ_GATE
  CAP_DATA -->|"governed by"| CTL_REGRPT_CERT
  CAP_DATA -->|"governed by"| CTL_RETENTION
  CAP_DATA_02 -->|"governed by"| CTL_CLIENT_SLA
  CAP_DATA_02 -->|"governed by"| CTL_CONV_VERIFY
  CAP_DATA_02 -->|"governed by"| CTL_DQ_GATE
  CAP_DATA_03 -->|"governed by"| CTL_DQ_GATE
  CAP_DATA_03 -->|"governed by"| CTL_REGRPT_CERT
  CAP_DATA_07 -->|"governed by"| CTL_RETENTION
  SYS_CUST360_PIPELINE -->|"realizes"| CAP_DATA_04
  SYS_CUST360_SEMANTIC -->|"realizes"| CAP_DATA_04
  SYS_ARCHREPO -->|"realizes"| CAP_DATA_07
  SYS_CATALOG -->|"realizes"| CAP_DATA_01
  SYS_CATALOG -->|"realizes"| CAP_DATA_05
  SYS_CLIENT_PORTAL -->|"realizes"| CAP_DATA_02
  SYS_CORE_LEDGER -->|"realizes"| CAP_DATA_02
  SYS_DATA_INGEST -->|"realizes"| CAP_DATA_02
  SYS_DATA_INGEST -->|"realizes"| CAP_DATA_03
  SYS_DOC -->|"realizes"| CAP_DATA_07
  SYS_MODEL -->|"realizes"| CAP_DATA_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_DATA,CAP_DATA_01,CAP_DATA_02,CAP_DATA_03,CAP_DATA_04,CAP_DATA_05,CAP_DATA_06,CAP_DATA_07 s_capabilities__capabilities;
  class CTL_CLIENT_SLA,CTL_CONV_VERIFY,CTL_DQ_GATE,CTL_REGRPT_CERT,CTL_RETENTION s_controls__controls;
  class FW_BIAN,FW_DMBOK s_frameworks__frameworks;
  class P_APPDEV_009,P_DATAENG_001,P_DATAENG_002,P_DATAGOV_001,P_DATAGOV_002,P_DATAGOV_003,P_DATAGOV_004,P_REG_DATA_PREP_001,P_TPS_002,P_TPS_005 s_processes__processes;
  class SYS_ARCHREPO,SYS_CATALOG,SYS_CLIENT_PORTAL,SYS_CORE_LEDGER,SYS_CUST360_PIPELINE,SYS_CUST360_SEMANTIC,SYS_DATA_INGEST,SYS_DOC,SYS_MODEL s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Data & Analytics Management — Frameworks, Controls, Systems](../svg/capability-alignment--cap-data.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

34 entities, 48 relationships. Generated from the model; edit the model, not this file.
