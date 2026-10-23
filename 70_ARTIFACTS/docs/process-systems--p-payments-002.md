# Ingest clearing file and post transactions — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Ingest clearing file and post transactions — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PAY_02{{"Clearing & Transaction<br/>Posting"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_DAILY_RECON[["Daily settlement and<br/>clearing reconciliation"]]
  end

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_TRANSACTION[("Card transaction history")]
    DA_CUSTOMER_PROFILE[("Customer profile")]
    DA_PAYMENT_INSTR[("Payment instructions")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_PAYMENTS_002[\"Ingest clearing file and<br/>post transactions"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
  end

  P_PAYMENTS_002 -->|"Primary"| SYS_CORE_LEDGER
  P_PAYMENTS_002 -->|"Writes"| DA_TRANSACTION
  P_PAYMENTS_002 -->|"Reads"| DA_CUSTOMER_PROFILE
  P_PAYMENTS_002 -->|"Reads"| DA_PAYMENT_INSTR
  P_PAYMENTS_002 -->|"governed by"| CTL_DAILY_RECON
  P_PAYMENTS_002 -->|"supports"| CAP_PAY_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PAY_02 s_capabilities__capabilities;
  class CTL_DAILY_RECON s_controls__controls;
  class DA_CUSTOMER_PROFILE,DA_PAYMENT_INSTR,DA_TRANSACTION s_data_assets__data_assets;
  class P_PAYMENTS_002 s_processes__processes;
  class SYS_CORE_LEDGER s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Ingest clearing file and post transactions — Systems, Data and Controls](../svg/process-systems--p-payments-002.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
