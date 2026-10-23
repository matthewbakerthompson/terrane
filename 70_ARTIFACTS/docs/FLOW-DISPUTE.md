# Dispute and Chargeback

A cardholder disputes a transaction. Raised in the contact center, handled in the vendor platform, settled back through the ledger.

| | |
|---|---|
| Trigger | Cardholder disputes a transaction |
| Target | scheme deadline, measured in days |
| Criticality | Medium |
| Owner | ORG-SERVICING |

![Dispute and Chargeback](../svg/FLOW-DISPUTE.svg)

```mermaid
%% Dispute and Chargeback
%% Generated from the model by `terrane render`. Do not edit by hand.
sequenceDiagram
  autonumber
  actor ACT_SERVICING_AGENT as Servicing Agent
  participant SYS_CRM as Dynamics 365 Customer Service
  participant SYS_CORE_LEDGER as Core Card Ledger
  participant SYS_DISPUTES_GATEWAY as Dispute Management Platform I…
  participant SYS_DISPUTES_SAAS as Pega Smart Dispute
  participant SYS_DATA_INGEST as Enterprise Data Ingestion Hub
  ACT_SERVICING_AGENT->>SYS_CRM: Cardholder disputes a transaction
  SYS_CRM->>SYS_CORE_LEDGER: HTTPS
  SYS_CORE_LEDGER-->>SYS_CRM: response
  SYS_CORE_LEDGER->>SYS_DISPUTES_GATEWAY: HTTPS
  SYS_DISPUTES_GATEWAY-->>SYS_CORE_LEDGER: response
  SYS_DISPUTES_GATEWAY->>SYS_DISPUTES_SAAS: HTTPS
  SYS_DISPUTES_SAAS-->>SYS_DISPUTES_GATEWAY: response
  SYS_DISPUTES_SAAS-)SYS_DATA_INGEST: SFTP
  Note over SYS_CRM: scheme deadline, measured in days
```

| # | From | To | Via |
|---:|---|---|---|
| 10 | Dynamics 365 Customer Service | Core Card Ledger | `INT-CRM-LEDGER` HTTPS, Request-response |
| 20 | Core Card Ledger | Dispute Management Platform Integration Gateway | `INT-DISPUTES-UP-GATEWAY` HTTPS, Request-response |
| 30 | Dispute Management Platform Integration Gateway | Pega Smart Dispute | `INT-DISPUTES-GATEWAY-SAAS` HTTPS, Request-response |
| 40 | Pega Smart Dispute | Enterprise Data Ingestion Hub | `INT-DISPUTES-SAAS-FEED` SFTP, Batch |

4 step(s). Every hop is a recorded interface, so a hop that is not in the model cannot appear here.
