# Payment instructions — Where It Lives and Who Uses It

One data asset in full: the system that masters it, the systems that read or write it, the processes that use it, the controls that govern it and the policies it is subject to. The page a privacy or audit question starts from.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Payment instructions — Where It Lives and Who Uses It
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_PAYMENT_INSTR[("Payment instructions")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_CARD_PMT_001[\"Capture and apply<br/>cardholder payment"/]
    P_PAYMENTS_002[\"Ingest clearing file and<br/>post transactions"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_PAYMENT_GW["Payment capture gateway"]
  end

  SYS_PAYMENT_GW -.->|"masters"| DA_PAYMENT_INSTR
  SYS_PAYMENT_GW -->|"ReadWrite"| DA_PAYMENT_INSTR
  SYS_CORE_LEDGER -->|"Read"| DA_PAYMENT_INSTR
  P_CARD_PMT_001 -->|"Both"| DA_PAYMENT_INSTR
  P_PAYMENTS_002 -->|"Reads"| DA_PAYMENT_INSTR

  classDef s_data_assets__restricted fill:#70c9a7,stroke:#047857,color:#0f172a,stroke-width:2.6px;
  classDef s_processes__default fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.1px;
  class DA_PAYMENT_INSTR s_data_assets__restricted;
  class P_CARD_PMT_001,P_PAYMENTS_002 s_processes__default;
  class SYS_CORE_LEDGER,SYS_PAYMENT_GW s_systems__default;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Payment instructions — Where It Lives and Who Uses It](../svg/data-asset-context--da-payment-instr.svg)

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

5 entities, 5 relationships. Generated from the model; edit the model, not this file.
