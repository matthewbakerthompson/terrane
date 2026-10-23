# Card Authorization

A card presented at a merchant, authorized or declined inside the scheme timeout. The tightest latency budget in the estate, and the reason the screening call has a circuit breaker rather than a retry.

| | |
|---|---|
| Trigger | Cardholder presents a card at a merchant |
| Target | under 500ms end to end |
| Criticality | High |
| Owner | ORG-PAYMENTS |

![Card Authorization](../svg/FLOW-CARD-AUTH.svg)

```mermaid
%% Card Authorization
%% Generated from the model by `terrane render`. Do not edit by hand.
sequenceDiagram
  autonumber
  actor ACT_MERCHANT as Merchant
  participant SYS_AUTH_SWITCH as Authorization Switch
  participant SYS_SCREENING_GATEWAY as NICE Actimize Screening Integ…
  participant SYS_SCREENING_EGRESS as NICE Actimize Screening Priva…
  participant SYS_SCREENING_VENDOR as NICE Actimize Screening
  participant SYS_CORE_LEDGER as Core Card Ledger
  ACT_MERCHANT->>SYS_AUTH_SWITCH: Cardholder presents a card at a merchant
  SYS_AUTH_SWITCH->>SYS_SCREENING_GATEWAY: HTTPS
  SYS_SCREENING_GATEWAY-->>SYS_AUTH_SWITCH: response
  SYS_SCREENING_GATEWAY->>SYS_SCREENING_EGRESS: HTTPS
  SYS_SCREENING_EGRESS-->>SYS_SCREENING_GATEWAY: response
  SYS_SCREENING_EGRESS->>SYS_SCREENING_VENDOR: PrivateLink
  SYS_SCREENING_VENDOR-->>SYS_SCREENING_EGRESS: response
  SYS_AUTH_SWITCH->>SYS_CORE_LEDGER: MQ
  SYS_CORE_LEDGER-->>SYS_AUTH_SWITCH: response
  Note over SYS_AUTH_SWITCH: under 500ms end to end
```

| # | From | To | Via |
|---:|---|---|---|
| 10 | Authorization Switch | NICE Actimize Screening Integration Gateway | `INT-SCREENING-CALLER-GATEWAY` HTTPS, Request-response |
| 20 | NICE Actimize Screening Integration Gateway | NICE Actimize Screening Private Egress | `INT-SCREENING-GATEWAY-EGRESS` HTTPS, Request-response |
| 30 | NICE Actimize Screening Private Egress | NICE Actimize Screening | `INT-SCREENING-EGRESS-VENDOR` PrivateLink, Request-response |
| 40 | Authorization Switch | Core Card Ledger | `INT-AUTH-LEDGER` MQ, Request-response |

4 step(s). Every hop is a recorded interface, so a hop that is not in the model cannot appear here.
