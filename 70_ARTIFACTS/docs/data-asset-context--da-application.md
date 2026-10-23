# Credit application record — Where It Lives and Who Uses It

One data asset in full: the system that masters it, the systems that read or write it, the processes that use it, the controls that govern it and the policies it is subject to. The page a privacy or audit question starts from.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Credit application record — Where It Lives and Who Uses It
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_APPLICATION[("Credit application record")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_ORIG_001[\"Capture card application"/]
    P_ORIG_004[\"Execute credit decision"/]
    P_ORIG_005[\"Issue adverse action<br/>notice"/]
    P_ORIG_003[\"Screen application for<br/>fraud"/]
    P_ORIG_002[\"Verify applicant identity<br/>and satisfy CIP"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_APPFRAUD["Application fraud<br/>screening"]
    SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
    SYS_AML["Financial crimes platform"]
    SYS_KYC["Identity verification"]
    SYS_ORIG_DECISION["Originations decision<br/>engine"]
  end

  SYS_ORIG_DECISION -.->|"masters"| DA_APPLICATION
  SYS_ORIG_DECISION -->|"ReadWrite"| DA_APPLICATION
  SYS_APPFRAUD -->|"Read"| DA_APPLICATION
  SYS_KYC -->|"Read"| DA_APPLICATION
  SYS_CREDIT_DATA -->|"Read"| DA_APPLICATION
  SYS_AML -->|"Read"| DA_APPLICATION
  P_ORIG_001 -->|"Writes"| DA_APPLICATION
  P_ORIG_002 -->|"Both"| DA_APPLICATION
  P_ORIG_003 -->|"Reads"| DA_APPLICATION
  P_ORIG_004 -->|"Both"| DA_APPLICATION
  P_ORIG_005 -->|"Reads"| DA_APPLICATION

  classDef s_data_assets__restricted fill:#70c9a7,stroke:#047857,color:#0f172a,stroke-width:2.6px;
  classDef s_processes__default fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.1px;
  class DA_APPLICATION s_data_assets__restricted;
  class P_ORIG_001,P_ORIG_002,P_ORIG_003,P_ORIG_004,P_ORIG_005 s_processes__default;
  class SYS_AML,SYS_APPFRAUD,SYS_CREDIT_DATA,SYS_KYC,SYS_ORIG_DECISION s_systems__default;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Credit application record — Where It Lives and Who Uses It](../svg/data-asset-context--da-application.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

**classification** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | Restricted |
| 1.1px | default |

11 entities, 11 relationships. Generated from the model; edit the model, not this file.
