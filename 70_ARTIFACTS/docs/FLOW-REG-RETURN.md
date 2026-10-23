# Regulatory Return

The monthly supervisory return. Entirely batch, and the only flow whose deadline is external and non-negotiable.

| | |
|---|---|
| Trigger | Month end |
| Target | filed within 10 working days |
| Criticality | High |
| Owner | ORG-COMPLIANCE |

![Regulatory Return](../svg/FLOW-REG-RETURN.svg)

```mermaid
%% Regulatory Return
%% Generated from the model by `terrane render`. Do not edit by hand.
sequenceDiagram
  autonumber
  participant SYS_CORE_LEDGER as Core Card Ledger
  participant SYS_DATA_INGEST as Enterprise Data Ingestion Hub
  participant SYS_CUST360_PIPELINE as Customer 360 Pipeline
  participant SYS_CUST360_SEMANTIC as Customer 360 Semantic Layer
  participant SYS_REG_REPORTING as Regulatory Reporting Engine
  SYS_CORE_LEDGER-)SYS_DATA_INGEST: FileTransfer
  SYS_DATA_INGEST-)SYS_CUST360_PIPELINE: Snowpipe
  SYS_CUST360_PIPELINE-)SYS_CUST360_SEMANTIC: SQL
  SYS_CUST360_SEMANTIC-)SYS_REG_REPORTING: SQL
  Note over SYS_CORE_LEDGER: filed within 10 working days
```

| # | From | To | Via |
|---:|---|---|---|
| 10 | Core Card Ledger | Enterprise Data Ingestion Hub | `INT-LEDGER-INGEST` FileTransfer, Batch |
| 20 | Enterprise Data Ingestion Hub | Customer 360 Pipeline | `INT-CUST360-INGEST` Snowpipe, Batch |
| 30 | Customer 360 Pipeline | Customer 360 Semantic Layer | `INT-CUST360-PIPE-SEMANTIC` SQL, Batch |
| 40 | Customer 360 Semantic Layer | Regulatory Reporting Engine | `INT-CUST360-REGREPORTING` SQL, Batch |

4 step(s). Every hop is a recorded interface, so a hop that is not in the model cannot appear here.
