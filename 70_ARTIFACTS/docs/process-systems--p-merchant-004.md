# Screen merchant against sanctions and network lists — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Screen merchant against sanctions and network lists — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_MERCH_02_02{{"Merchant Screening & Brand<br/>Risk"}}
    CAP_MERCH_02{{"Merchant Underwriting &<br/>Risk Vetting"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_MERCH_SCREEN[["Merchant screening before<br/>boarding"]]
    CTL_SANCTIONS[["Sanctions and watchlist<br/>screening"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_MERCHANT[("Merchant master and<br/>underwriting file")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_MERCHANT_004[\"Screen merchant against<br/>sanctions and network<br/>lists"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AML["Financial crimes platform"]
    SYS_MERCH_RISK["Merchant risk monitoring"]
    SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
  end

  P_MERCHANT_004 -->|"Primary"| SYS_SCREENING_VENDOR
  P_MERCHANT_004 -->|"Supporting"| SYS_MERCH_RISK
  P_MERCHANT_004 -->|"Supporting"| SYS_AML
  P_MERCHANT_004 -->|"Read"| DA_MERCHANT
  P_MERCHANT_004 -->|"governed by"| CTL_MERCH_SCREEN
  P_MERCHANT_004 -->|"governed by"| CTL_SANCTIONS
  P_MERCHANT_004 -->|"supports"| CAP_MERCH_02_02
  P_MERCHANT_004 -->|"supports"| CAP_MERCH_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_MERCH_02,CAP_MERCH_02_02 s_capabilities__capabilities;
  class CTL_MERCH_SCREEN,CTL_SANCTIONS s_controls__controls;
  class DA_MERCHANT s_data_assets__data_assets;
  class P_MERCHANT_004 s_processes__processes;
  class SYS_AML,SYS_MERCH_RISK,SYS_SCREENING_VENDOR s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Screen merchant against sanctions and network lists — Systems, Data and Controls](../svg/process-systems--p-merchant-004.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

9 entities, 8 relationships. Generated from the model; edit the model, not this file.
