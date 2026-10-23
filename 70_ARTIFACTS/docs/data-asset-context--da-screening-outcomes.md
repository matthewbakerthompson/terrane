# NICE Actimize Screening outcomes — Where It Lives and Who Uses It

One data asset in full: the system that masters it, the systems that read or write it, the processes that use it, the controls that govern it and the policies it is subject to. The page a privacy or audit question starts from.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% NICE Actimize Screening outcomes — Where It Lives and Who Uses It
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Control["Control"]
    direction LR
    CTL_RETENTION[["Retention schedule<br/>enforcement"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_SCREENING_OUTCOMES[("NICE Actimize Screening<br/>outcomes")]
  end

  subgraph grp_Policy["Policy"]
    direction LR
    POL_PRIVACY[/"Consumer Privacy & Data<br/>Handling Policy"\]
    POL_RECORDS[/"Records Retention &<br/>Disposition Policy"\]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
  end

  SYS_SCREENING_VENDOR -.->|"masters"| DA_SCREENING_OUTCOMES
  SYS_SCREENING_VENDOR -->|"Write"| DA_SCREENING_OUTCOMES
  SYS_DATA_INGEST -->|"Read"| DA_SCREENING_OUTCOMES
  DA_SCREENING_OUTCOMES -->|"governed by"| CTL_RETENTION
  DA_SCREENING_OUTCOMES -->|"subject to"| POL_RECORDS
  DA_SCREENING_OUTCOMES -->|"subject to"| POL_PRIVACY

  classDef s_controls__default fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.1px;
  classDef s_data_assets__restricted fill:#70c9a7,stroke:#047857,color:#0f172a,stroke-width:2.6px;
  classDef s_policies__default fill:#fecaca,stroke:#dc2626,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.1px;
  class CTL_RETENTION s_controls__default;
  class DA_SCREENING_OUTCOMES s_data_assets__restricted;
  class POL_PRIVACY,POL_RECORDS s_policies__default;
  class SYS_DATA_INGEST,SYS_SCREENING_VENDOR s_systems__default;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Control,grp_Data_Asset,grp_Policy,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![NICE Actimize Screening outcomes — Where It Lives and Who Uses It](../svg/data-asset-context--da-screening-outcomes.svg)

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

6 entities, 6 relationships. Generated from the model; edit the model, not this file.
