# Underwrite merchant — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Underwrite merchant — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_MERCH_02_01{{"Merchant Credit<br/>Underwriting"}}
    CAP_MERCH_02{{"Merchant Underwriting &<br/>Risk Vetting"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_MERCH_EXPOSURE[["Merchant exposure limit<br/>monitoring"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_MERCHANT[("Merchant master and<br/>underwriting file")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_MERCHANT_003[\"Underwrite merchant"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
    SYS_MERCH_ACQ["Merchant acquiring<br/>platform<br/>[external]"]
    SYS_MERCH_RISK["Merchant risk monitoring"]
  end

  P_MERCHANT_003 -->|"Primary"| SYS_MERCH_RISK
  P_MERCHANT_003 -->|"Supporting"| SYS_MERCH_ACQ
  P_MERCHANT_003 -->|"Supporting"| SYS_CREDIT_DATA
  P_MERCHANT_003 -->|"Both"| DA_MERCHANT
  P_MERCHANT_003 -->|"governed by"| CTL_MERCH_EXPOSURE
  P_MERCHANT_003 -->|"supports"| CAP_MERCH_02_01
  P_MERCHANT_003 -->|"supports"| CAP_MERCH_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_MERCH_02,CAP_MERCH_02_01 s_capabilities__capabilities;
  class CTL_MERCH_EXPOSURE s_controls__controls;
  class DA_MERCHANT s_data_assets__data_assets;
  class P_MERCHANT_003 s_processes__processes;
  class SYS_CREDIT_DATA,SYS_MERCH_ACQ,SYS_MERCH_RISK s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Underwrite merchant — Systems, Data and Controls](../svg/process-systems--p-merchant-003.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

8 entities, 7 relationships. Generated from the model; edit the model, not this file.
