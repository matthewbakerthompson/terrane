# Refund credit balance and report unclaimed property — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Refund credit balance and report unclaimed property — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_BILL_06{{"Credit Balance Refund &<br/>Unclaimed Property"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_CREDIT_BAL[["Credit balance refund and<br/>escheatment"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CUSTOMER_PROFILE[("Customer profile")]
    DA_GL[("General ledger entries")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_016[\"Refund credit balance and<br/>report unclaimed property"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_GL["General ledger"]
    SYS_PAYMENT_GW["Payment capture gateway"]
  end

  P_SERVICING_016 -->|"Primary"| SYS_CORE_LEDGER
  P_SERVICING_016 -->|"Supporting"| SYS_PAYMENT_GW
  P_SERVICING_016 -->|"Supporting"| SYS_GL
  P_SERVICING_016 -->|"Read"| DA_CUSTOMER_PROFILE
  P_SERVICING_016 -->|"Write"| DA_GL
  P_SERVICING_016 -->|"governed by"| CTL_CREDIT_BAL
  P_SERVICING_016 -->|"supports"| CAP_BILL_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_BILL_06 s_capabilities__capabilities;
  class CTL_CREDIT_BAL s_controls__controls;
  class DA_CUSTOMER_PROFILE,DA_GL s_data_assets__data_assets;
  class P_SERVICING_016 s_processes__processes;
  class SYS_CORE_LEDGER,SYS_GL,SYS_PAYMENT_GW s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Refund credit balance and report unclaimed property — Systems, Data and Controls](../svg/process-systems--p-servicing-016.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

8 entities, 7 relationships. Generated from the model; edit the model, not this file.
