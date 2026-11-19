# Authorization log — Where It Lives and Who Uses It

One data asset in full: the system that masters it, the systems that read or write it, the processes that use it, the controls that govern it and the policies it is subject to. The page a privacy or audit question starts from.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Authorization log — Where It Lives and Who Uses It
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_AUTH_LOG[("Authorization log")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_PAYMENTS_007[\"Maintain authorization<br/>routing and network<br/>connectivity"/]
    P_PAYMENTS_006[\"Operate stand-in<br/>authorization during a<br/>host outage"/]
    P_COMPLIANCE_008[\"Screen transactions and<br/>parties against sanctions<br/>in line"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
    SYS_FRAUD_DETECT["Transaction fraud<br/>detection"]
  end

  SYS_AUTH_SWITCH -.->|"masters"| DA_AUTH_LOG
  SYS_AUTH_SWITCH -->|"ReadWrite"| DA_AUTH_LOG
  SYS_FRAUD_DETECT -->|"Read"| DA_AUTH_LOG
  P_PAYMENTS_006 -->|"Both"| DA_AUTH_LOG
  P_PAYMENTS_007 -->|"Read"| DA_AUTH_LOG
  P_COMPLIANCE_008 -->|"Read"| DA_AUTH_LOG

  classDef s_data_assets__restricted fill:#70c9a7,stroke:#047857,color:#0f172a,stroke-width:2.6px;
  classDef s_processes__default fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.1px;
  class DA_AUTH_LOG s_data_assets__restricted;
  class P_COMPLIANCE_008,P_PAYMENTS_006,P_PAYMENTS_007 s_processes__default;
  class SYS_AUTH_SWITCH,SYS_FRAUD_DETECT s_systems__default;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Authorization log — Where It Lives and Who Uses It](../svg/data-asset-context--da-auth-log.svg)

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

6 entities, 6 relationships. Generated from the model; edit the model, not this file.
