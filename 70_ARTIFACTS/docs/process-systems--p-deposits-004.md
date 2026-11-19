# Settle brokered CDs and keep the position — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Settle brokered CDs and keep the position — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_DEP_03{{"Brokered CD Program<br/>Management"}}
    CAP_DEP_03_02{{"Brokered CD Settlement &<br/>Record Keeping"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_BROKERED_RECON[["Brokered deposit position<br/>reconciliation"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_DEPOSIT_ACCOUNT[("Deposit account and CD<br/>record")]
    DA_GL[("General ledger entries")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DEPOSITS_004[\"Settle brokered CDs and<br/>keep the position"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_BROKER_GW["Brokered deposit<br/>settlement gateway"]
    SYS_DEPOSIT["Deposit platform"]
    SYS_GL["General ledger"]
    SYS_RECON["Reconciliation platform"]
  end

  P_DEPOSITS_004 -->|"Primary"| SYS_DEPOSIT
  P_DEPOSITS_004 -->|"Supporting"| SYS_BROKER_GW
  P_DEPOSITS_004 -->|"Supporting"| SYS_RECON
  P_DEPOSITS_004 -->|"Supporting"| SYS_GL
  P_DEPOSITS_004 -->|"Both"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_004 -->|"Write"| DA_GL
  P_DEPOSITS_004 -->|"governed by"| CTL_BROKERED_RECON
  P_DEPOSITS_004 -->|"supports"| CAP_DEP_03_02
  P_DEPOSITS_004 -->|"supports"| CAP_DEP_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_DEP_03,CAP_DEP_03_02 s_capabilities__capabilities;
  class CTL_BROKERED_RECON s_controls__controls;
  class DA_DEPOSIT_ACCOUNT,DA_GL s_data_assets__data_assets;
  class P_DEPOSITS_004 s_processes__processes;
  class SYS_BROKER_GW,SYS_DEPOSIT,SYS_GL,SYS_RECON s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Settle brokered CDs and keep the position — Systems, Data and Controls](../svg/process-systems--p-deposits-004.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

10 entities, 9 relationships. Generated from the model; edit the model, not this file.
