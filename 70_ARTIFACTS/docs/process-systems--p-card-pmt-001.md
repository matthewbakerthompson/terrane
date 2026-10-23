# Capture and apply cardholder payment — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Capture and apply cardholder payment — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PAY_03{{"Payment Capture &<br/>Application"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_PMT_POSTING[["Payment posting timeliness"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_PAYMENT_INSTR[("Payment instructions")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_CARD_PMT_001[\"Capture and apply<br/>cardholder payment"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
    SYS_MOBILE["Cardholder mobile<br/>application"]
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_IVR["IVR and self-service voice"]
    SYS_PAYMENT_GW["Payment capture gateway"]
  end

  P_CARD_PMT_001 -->|"Primary"| SYS_PAYMENT_GW
  P_CARD_PMT_001 -->|"Supporting"| SYS_CORE_LEDGER
  P_CARD_PMT_001 -->|"Supporting"| SYS_CARDSVC_WEB
  P_CARD_PMT_001 -->|"Supporting"| SYS_MOBILE
  P_CARD_PMT_001 -->|"Supporting"| SYS_IVR
  P_CARD_PMT_001 -->|"Both"| DA_PAYMENT_INSTR
  P_CARD_PMT_001 -->|"governed by"| CTL_PMT_POSTING
  P_CARD_PMT_001 -->|"supports"| CAP_PAY_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PAY_03 s_capabilities__capabilities;
  class CTL_PMT_POSTING s_controls__controls;
  class DA_PAYMENT_INSTR s_data_assets__data_assets;
  class P_CARD_PMT_001 s_processes__processes;
  class SYS_CARDSVC_WEB,SYS_CORE_LEDGER,SYS_IVR,SYS_MOBILE,SYS_PAYMENT_GW s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Capture and apply cardholder payment — Systems, Data and Controls](../svg/process-systems--p-card-pmt-001.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

9 entities, 8 relationships. Generated from the model; edit the model, not this file.
