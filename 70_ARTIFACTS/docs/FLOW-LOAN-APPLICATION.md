# Installment Loan Application

An applicant applies for point-of-sale credit. Bureau search, affordability and a decision, with referral to an underwriter when the automated decision declines to take it.

| | |
|---|---|
| Trigger | Applicant submits an application |
| Target | under 20s to a decision |
| Criticality | High |
| Owner | ORG-PRODUCT |

![Installment Loan Application](../svg/FLOW-LOAN-APPLICATION.svg)

```mermaid
%% Installment Loan Application
%% Generated from the model by `terrane render`. Do not edit by hand.
sequenceDiagram
  autonumber
  participant SYS_LENDING_EDGE as Installment Lending Edge
  participant SYS_LENDING_ALB as Installment Lending Load Bala…
  participant SYS_LENDING_WEB as Installment Lending Web
  participant SYS_LENDING_API as Installment Lending Service
  participant SYS_IDENTITY_SVC as Customer Identity Service
  participant SYS_CREDIT_BUREAU as Experian Credit Bureau
  participant SYS_LENDING_DB as Installment Lending Database
  participant SYS_CORE_LEDGER as Core Card Ledger
  participant SYS_LENDING_WORKER as Installment Lending Async Wor…
  SYS_LENDING_EDGE->>SYS_LENDING_ALB: HTTPS
  SYS_LENDING_ALB-->>SYS_LENDING_EDGE: response
  SYS_LENDING_ALB->>SYS_LENDING_WEB: HTTPS
  SYS_LENDING_WEB-->>SYS_LENDING_ALB: response
  SYS_LENDING_WEB->>SYS_LENDING_API: HTTPS
  SYS_LENDING_API-->>SYS_LENDING_WEB: response
  SYS_LENDING_API->>SYS_IDENTITY_SVC: HTTPS
  SYS_IDENTITY_SVC-->>SYS_LENDING_API: response
  SYS_LENDING_API->>SYS_CREDIT_BUREAU: HTTPS
  SYS_CREDIT_BUREAU-->>SYS_LENDING_API: response
  SYS_LENDING_API->>SYS_LENDING_DB: PostgreSQL
  SYS_LENDING_DB-->>SYS_LENDING_API: response
  SYS_LENDING_API->>SYS_CORE_LEDGER: MQ
  SYS_CORE_LEDGER-->>SYS_LENDING_API: response
  SYS_LENDING_API-)SYS_LENDING_WORKER: Kafka
  Note over SYS_LENDING_EDGE: under 20s to a decision
```

| # | From | To | Via |
|---:|---|---|---|
| 10 | Installment Lending Edge | Installment Lending Load Balancer | `INT-LENDING-EDGE-ALB` HTTPS, Request-response |
| 20 | Installment Lending Load Balancer | Installment Lending Web | `INT-LENDING-ALB-WEB` HTTPS, Request-response |
| 30 | Installment Lending Web | Installment Lending Service | `INT-LENDING-WEB-API` HTTPS, Request-response |
| 40 | Installment Lending Service | Customer Identity Service | `INT-LENDING-API-IDENTITY` HTTPS, Request-response |
| 50 | Installment Lending Service | Experian Credit Bureau | `INT-LENDING-API-BUREAU` HTTPS, Request-response |
| 60 | Installment Lending Service | Installment Lending Database | `INT-LENDING-API-DB` PostgreSQL, Request-response |
| 70 | Installment Lending Service | Core Card Ledger | `INT-LENDING-API-LEDGER` MQ, Request-response |
| 80 | Installment Lending Service | Installment Lending Async Worker | `INT-LENDING-API-WORKER` Kafka, Event |

8 step(s). Every hop is a recorded interface, so a hop that is not in the model cannot appear here.
