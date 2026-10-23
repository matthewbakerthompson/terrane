# Prospect to Funded Account — Stages and Capabilities

The Prospect to Funded Account value stream, its stages, and the capabilities each stage depends on. A capability used in several stages is on the stream's critical path: if it fails, every one of those stages stops.

![Prospect to Funded Account — Stages and Capabilities](../svg/value-stream-capabilities.svg)

| From | | To | Detail |
|---|---|---|---|
| Activate & First Use <br>`VS-ACQUIRE-CUSTOMER-S07` | stage crosses capability | Authorization Processing <br>`CAP-PAY-01` | needs |
| Activate & First Use <br>`VS-ACQUIRE-CUSTOMER-S07` | stage crosses capability | Digital Self-Service <br>`CAP-SERV-03` | needs |
| Apply <br>`VS-ACQUIRE-CUSTOMER-S02` | stage crosses capability | Application Capture <br>`CAP-ORIG-01` | needs |
| Decide <br>`VS-ACQUIRE-CUSTOMER-S04` | stage crosses capability | Credit Strategy & Scorecard Management <br>`CAP-CRED-01` | needs |
| Decide <br>`VS-ACQUIRE-CUSTOMER-S04` | stage crosses capability | Credit Line Assignment & Management <br>`CAP-CRED-03` | needs |
| Decide <br>`VS-ACQUIRE-CUSTOMER-S04` | stage crosses capability | Authorization Strategy Management <br>`CAP-CRED-06` | needs |
| Decide <br>`VS-ACQUIRE-CUSTOMER-S04` | stage crosses capability | Underwriting & Credit Decisioning Execution <br>`CAP-ORIG-04` | needs |
| Fulfill Card <br>`VS-ACQUIRE-CUSTOMER-S06` | stage crosses capability | Card Production & Fulfillment <br>`CAP-ORIG-07` | needs |
| Fulfill Card <br>`VS-ACQUIRE-CUSTOMER-S06` | stage crosses capability | Digital Wallet Provisioning <br>`CAP-ORIG-08` | needs |
| Fulfill Card <br>`VS-ACQUIRE-CUSTOMER-S06` | stage crosses capability | Tokenization & Credential Management <br>`CAP-PAY-07` | needs |
| Open Account <br>`VS-ACQUIRE-CUSTOMER-S05` | stage crosses capability | Adverse Action & Notice Generation <br>`CAP-ORIG-05` | needs |
| Open Account <br>`VS-ACQUIRE-CUSTOMER-S05` | stage crosses capability | Account Establishment & Card Issuance <br>`CAP-ORIG-06` | needs |
| Target & Offer <br>`VS-ACQUIRE-CUSTOMER-S01` | stage crosses capability | Prospect Data & List Management <br>`CAP-ACQ-01` | needs |
| Target & Offer <br>`VS-ACQUIRE-CUSTOMER-S01` | stage crosses capability | Offer & Pre-Screen Management <br>`CAP-ACQ-02` | needs |
| Target & Offer <br>`VS-ACQUIRE-CUSTOMER-S01` | stage crosses capability | Campaign Execution & Channel Management <br>`CAP-ACQ-03` | needs |
| Target & Offer <br>`VS-ACQUIRE-CUSTOMER-S01` | stage crosses capability | Marketing Compliance & Disclosure Review <br>`CAP-ACQ-04` | needs |
| Verify Identity <br>`VS-ACQUIRE-CUSTOMER-S03` | stage crosses capability | Identity Verification & KYC/CIP <br>`CAP-ORIG-02` | needs |
| Verify Identity <br>`VS-ACQUIRE-CUSTOMER-S03` | stage crosses capability | Application Fraud Screening <br>`CAP-ORIG-03` | needs |
| Verify Identity <br>`VS-ACQUIRE-CUSTOMER-S03` | stage crosses capability | Financial Crimes & BSA/AML Compliance <br>`CAP-RGOV-07` | needs |

19 relationships across 26 entities. Generated from the model; this is a report rather than a diagram, so it is a table.
