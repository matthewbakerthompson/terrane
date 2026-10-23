# Third-Party Exposure

Every system run by a vendor rather than by us, and what it connects to. The filter is the vendor tag, so new vendor systems appear automatically. It answers the third-party risk question: if this vendor disappeared, what would stop working?

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Third-Party Exposure
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Card_Issuing["Card Issuing"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
  end

  subgraph grp_Data_and_Analytics["Data and Analytics"]
    direction LR
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
  end

  subgraph grp_Enterprise_Platform["Enterprise Platform"]
    direction LR
    SYS_IDV_EGRESS["Identity Document<br/>Verification Private<br/>Egress"]
    SYS_SCREENING_FEDERATION["NICE Actimize Screening<br/>Identity Federation"]
    SYS_SCREENING_EGRESS["NICE Actimize Screening<br/>Private Egress"]
    SYS_OBAFF_EGRESS["Open Banking Affordability<br/>Private Egress"]
    SYS_SIEM["Security Monitoring<br/>[Microsoft Sentinel]"]
  end

  subgraph grp_Lending["Lending"]
    direction LR
    SYS_LENDING_HUB["Installment Lending<br/>Integration Hub"]
    SYS_LENDING_API["Installment Lending<br/>Service<br/>[EKS · Installment Lending Cache]"]
    SYS_OBAFF_VENDOR["Open Banking Affordability<br/>[TrueLayer]"]
    SYS_OBAFF_WEBHOOKS["Open Banking Affordability<br/>Webhook Listener<br/>[GKE]"]
  end

  subgraph grp_Risk_and_Compliance["Risk and Compliance"]
    direction LR
    SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
    SYS_IDV_VENDOR["Identity Document<br/>Verification<br/>[Onfido]"]
    SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
    SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
  end

  subgraph grp_Servicing["Servicing"]
    direction LR
    SYS_DISPUTES_GATEWAY["Dispute Management<br/>Platform Integration<br/>Gateway<br/>[AKS]"]
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
  end

  SYS_MARKETING["Campaign management"]
  SYS_CONTACT["Contact center platform"]
  SYS_BUREAU_GW["Credit bureau gateway"]
  SYS_IAM["Identity and access<br/>management"]
  SYS_FRAUD_DETECT["Transaction fraud<br/>detection"]

  SYS_FRAUD_DETECT -->|"AMQP"| SYS_CRM
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_BUREAU_GW
  SYS_BUREAU_GW -->|"FileTransfer"| SYS_CREDIT_BUREAU
  SYS_BUREAU_GW -->|"FileTransfer"| SYS_CRM
  SYS_CONTACT -->|"HTTPS"| SYS_CRM
  SYS_CRM -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_MARKETING -->|"AMQP"| SYS_CRM
  SYS_IAM -->|"Syslog"| SYS_SIEM
  SYS_CRM -->|"HTTPS"| SYS_IAM
  SYS_CONTACT -->|"HTTPS"| SYS_IAM
  SYS_CRM -->|"HTTPS"| SYS_CORE_LEDGER
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DATA_INGEST
  SYS_LENDING_API -->|"MQ"| SYS_CORE_LEDGER
  SYS_LENDING_API -->|"HTTPS"| SYS_CREDIT_BUREAU
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_DISPUTES_GATEWAY
  SYS_DISPUTES_GATEWAY -->|"HTTPS"| SYS_DISPUTES_SAAS
  SYS_DISPUTES_SAAS -->|"SFTP"| SYS_DATA_INGEST
  SYS_IDV_EGRESS -->|"PrivateLink"| SYS_IDV_VENDOR
  SYS_IDV_VENDOR -->|"HTTPS"| SYS_IDV_WEBHOOKS
  SYS_CORE_LEDGER -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CREDIT_BUREAU -->|"HTTPS"| SYS_LENDING_HUB
  SYS_CRM -->|"HTTPS"| SYS_LENDING_HUB
  SYS_OBAFF_EGRESS -->|"PrivateLink"| SYS_OBAFF_VENDOR
  SYS_OBAFF_VENDOR -->|"HTTPS"| SYS_OBAFF_WEBHOOKS
  SYS_SCREENING_FEDERATION -->|"SAML"| SYS_SCREENING_VENDOR
  SYS_SCREENING_VENDOR -->|"HTTPS"| SYS_SIEM
  SYS_SCREENING_EGRESS -->|"PrivateLink"| SYS_SCREENING_VENDOR
  SYS_SCREENING_VENDOR -->|"SFTP"| SYS_DATA_INGEST

  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__experian fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__in_house fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__microsoft fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__microsoft_sentinel fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__nice_actimize fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__onfido fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__pegasystems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__truelayer fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class SYS_BUREAU_GW,SYS_CONTACT,SYS_DISPUTES_GATEWAY,SYS_FRAUD_DETECT,SYS_IAM,SYS_IDV_EGRESS,SYS_IDV_WEBHOOKS,SYS_LENDING_API,SYS_LENDING_HUB,SYS_MARKETING,SYS_OBAFF_EGRESS,SYS_OBAFF_WEBHOOKS,SYS_SCREENING_EGRESS,SYS_SCREENING_FEDERATION s_systems__default;
  class SYS_CREDIT_BUREAU s_systems__experian;
  class SYS_CORE_LEDGER,SYS_DATA_INGEST s_systems__in_house;
  class SYS_CRM s_systems__microsoft;
  class SYS_SIEM s_systems__microsoft_sentinel;
  class SYS_SCREENING_VENDOR s_systems__nice_actimize;
  class SYS_IDV_VENDOR s_systems__onfido;
  class SYS_DISPUTES_SAAS s_systems__pegasystems;
  class SYS_OBAFF_VENDOR s_systems__truelayer;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Card_Issuing,grp_Data_and_Analytics,grp_Enterprise_Platform,grp_Lending,grp_Risk_and_Compliance,grp_Servicing boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Third-Party Exposure](../svg/vendor-exposure.svg)

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Dispute and Chargeback**: A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

1. Dynamics 365 Customer Service → Core Card Ledger (HTTPS)
2. Core Card Ledger → Dispute Management Platform Integration Gateway (HTTPS)
3. Dispute Management Platform Integration Gateway → Pega Smart Dispute (HTTPS)
4. Pega Smart Dispute → Enterprise Data Ingestion Hub (SFTP)

**Installment Loan Application**: An applicant applies for point-of-sale credit. Bureau search, affordability and a decision, with referral to an underwriter when the automated decision declines to take it.

1. Installment Lending Edge → Installment Lending Load Balancer (HTTPS) — not on this diagram
2. Installment Lending Load Balancer → Installment Lending Web (HTTPS) — not on this diagram
3. Installment Lending Web → Installment Lending Service (HTTPS) — not on this diagram
4. Installment Lending Service → Customer Identity Service (HTTPS) — not on this diagram
5. Installment Lending Service → Experian Credit Bureau (HTTPS)
6. Installment Lending Service → Installment Lending Database (PostgreSQL) — not on this diagram
7. Installment Lending Service → Core Card Ledger (MQ)
8. Installment Lending Service → Installment Lending Async Worker (Kafka) — not on this diagram

**Card Authorization**: A card presented at a merchant, authorized or declined inside the scheme timeout. The tightest latency budget in the estate, and the reason the screening call has a circuit breaker rather than a retry.

1. Authorization Switch → NICE Actimize Screening Integration Gateway (HTTPS) — not on this diagram
2. NICE Actimize Screening Integration Gateway → NICE Actimize Screening Private Egress (HTTPS) — not on this diagram
3. NICE Actimize Screening Private Egress → NICE Actimize Screening (PrivateLink)
4. Authorization Switch → Core Card Ledger (MQ) — not on this diagram

**Regulatory Return**: The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

1. Core Card Ledger → Enterprise Data Ingestion Hub (FileTransfer)
2. Enterprise Data Ingestion Hub → Customer 360 Pipeline (Snowpipe) — not on this diagram
3. Customer 360 Pipeline → Customer 360 Semantic Layer (SQL) — not on this diagram
4. Customer 360 Semantic Layer → Regulatory Reporting Engine (SQL) — not on this diagram

23 entities, 28 relationships. Generated from the model; edit the model, not this file.
