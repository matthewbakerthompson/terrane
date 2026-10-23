# Credit bureau furnishing file — Where It Lives and Who Uses It

One data asset in full: the system that masters it, the systems that read or write it, the processes that use it, the controls that govern it and the policies it is subject to. The page a privacy or audit question starts from.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Credit bureau furnishing file — Where It Lives and Who Uses It
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_ORIG_004[\"Execute credit decision"/]
    P_COLLECTIONS_005[\"Furnish credit bureau data"/]
    P_ORIG_005[\"Issue adverse action<br/>notice"/]
    P_CREDIT_001[\"Set and deploy credit<br/>decision strategy"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_BUREAU_GW["Credit bureau gateway"]
    SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
  end

  SYS_BUREAU_GW -.->|"masters"| DA_BUREAU_FILE
  SYS_BUREAU_GW -->|"ReadWrite"| DA_BUREAU_FILE
  SYS_CREDIT_BUREAU -->|"Read"| DA_BUREAU_FILE
  P_COLLECTIONS_005 -->|"Writes"| DA_BUREAU_FILE
  P_CREDIT_001 -->|"Reads"| DA_BUREAU_FILE
  P_ORIG_004 -->|"Reads"| DA_BUREAU_FILE
  P_ORIG_005 -->|"Reads"| DA_BUREAU_FILE

  classDef s_data_assets__restricted fill:#70c9a7,stroke:#047857,color:#0f172a,stroke-width:2.6px;
  classDef s_processes__default fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.1px;
  class DA_BUREAU_FILE s_data_assets__restricted;
  class P_COLLECTIONS_005,P_CREDIT_001,P_ORIG_004,P_ORIG_005 s_processes__default;
  class SYS_BUREAU_GW,SYS_CREDIT_BUREAU s_systems__default;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Credit bureau furnishing file — Where It Lives and Who Uses It](../svg/data-asset-context--da-bureau-file.svg)

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

7 entities, 7 relationships. Generated from the model; edit the model, not this file.
