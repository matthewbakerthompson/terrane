# Process product change or upgrade — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Process product change or upgrade — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_09{{"Retention, Product Change<br/>& Account Closure"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_NOTICE_CONTENT[["Notice content and<br/>delivery evidence"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CUSTOMER_PROFILE[("Customer profile")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_013[\"Process product change or<br/>upgrade"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARD_FULFILL["Card production and<br/>fulfillment<br/>[external]"]
    SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_REWARDS["Rewards ledger"]
  end

  P_SERVICING_013 -->|"Primary"| SYS_CARDSVC_API
  P_SERVICING_013 -->|"Supporting"| SYS_CORE_LEDGER
  P_SERVICING_013 -->|"Supporting"| SYS_REWARDS
  P_SERVICING_013 -->|"Supporting"| SYS_CARD_FULFILL
  P_SERVICING_013 -->|"Read"| DA_CUSTOMER_PROFILE
  P_SERVICING_013 -->|"governed by"| CTL_NOTICE_CONTENT
  P_SERVICING_013 -->|"supports"| CAP_SERV_09

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SERV_09 s_capabilities__capabilities;
  class CTL_NOTICE_CONTENT s_controls__controls;
  class DA_CUSTOMER_PROFILE s_data_assets__data_assets;
  class P_SERVICING_013 s_processes__processes;
  class SYS_CARD_FULFILL,SYS_CARDSVC_API,SYS_CORE_LEDGER,SYS_REWARDS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Process product change or upgrade — Systems, Data and Controls](../svg/process-systems--p-servicing-013.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

8 entities, 7 relationships. Generated from the model; edit the model, not this file.
