# Installment Lending Integration Hub — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Installment Lending Integration Hub — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_CARD_ACCOUNT[("Card account master")]
    DA_BUREAU_FILE[("Credit bureau furnishing<br/>file")]
    DA_CUSTOMER_PROFILE[("Customer profile")]
    DA_DISPUTE_CASE[("Dispute case file")]
    DA_PAYMENT_INSTR[("Payment instructions")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
    TS_ONPREM_DC[/"Primary Data Center<br/>[Virtual network]"/]
  end

  SYS_CRM -->|"HTTPS"| SYS_CORE_LEDGER
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CREDIT_BUREAU -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CRM -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CRM -.->|"runs on"| TS_ENTRA_ID
  SYS_CORE_LEDGER -.->|"runs on"| TS_ONPREM_DC
  SYS_CORE_LEDGER -->|"Read"| DA_PAYMENT_INSTR
  SYS_CREDIT_BUREAU -->|"Read"| DA_BUREAU_FILE
  SYS_CRM -->|"ReadWrite"| DA_DISPUTE_CASE
  SYS_CORE_LEDGER -->|"ReadWrite"| DA_CARD_ACCOUNT
  SYS_CRM -->|"ReadWrite"| DA_CUSTOMER_PROFILE

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_BUREAU_FILE,DA_CARD_ACCOUNT,DA_CUSTOMER_PROFILE,DA_DISPUTE_CASE,DA_PAYMENT_INSTR s_data_assets__data_assets;
  class SYS_CORE_LEDGER,SYS_CREDIT_BUREAU,SYS_CRM,SYS_LENDING_HUB s_systems__systems;
  class TS_ENTRA_ID,TS_ONPREM_DC s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Installment Lending Integration Hub — Architecture](../svg/system-architecture--sys-lending-hub.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Dispute and Chargeback**: A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

1. Dynamics 365 Customer Service → Core Card Ledger (HTTPS)
2. Core Card Ledger → Dispute Management Platform Integration Gateway (HTTPS) — not on this diagram
3. Dispute Management Platform Integration Gateway → Pega Smart Dispute (HTTPS) — not on this diagram
4. Pega Smart Dispute → Enterprise Data Ingestion Hub (SFTP) — not on this diagram

11 entities, 11 relationships. Generated from the model; edit the model, not this file.
