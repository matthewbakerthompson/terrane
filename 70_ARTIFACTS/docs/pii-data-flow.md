# Personal Data and the Systems That Hold It

Every data asset flagged as personal data, its system of record, and the systems that read or write it. This is the information a privacy assessment needs, kept current from the model instead of maintained by hand.

![Personal Data and the Systems That Hold It](../svg/pii-data-flow.svg)

| From | | To | Detail |
|---|---|---|---|
| Authorization Switch <br>`SYS-AUTH-SWITCH` | sot | Card transaction history <br>`DA-TRANSACTION` | system of record |
| Card Servicing Datastore <br>`SYS-CARDSVC-STORE` | sot | Card Servicing operational data <br>`DA-CARDSVC-OPERATIONAL` | system of record |
| Collections Workspace Datastore <br>`SYS-COLLECT-STORE` | sot | Collections Workspace operational data <br>`DA-COLLECT-OPERATIONAL` | system of record |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | sot | Card account master <br>`DA-CARD-ACCOUNT` | system of record |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | sot | Customer 360 curated dataset <br>`DA-CUST360-CURATED` | system of record |
| Dynamics 365 Customer Service <br>`SYS-CRM` | sot | Customer profile <br>`DA-CUSTOMER-PROFILE` | system of record |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | sot | Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | system of record |
| Authorization Switch <br>`SYS-AUTH-SWITCH` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Authorization Switch <br>`SYS-AUTH-SWITCH` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | ReadWrite |
| Card production and fulfillment <br>`SYS-CARD-FULFILL` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Card Servicing Datastore <br>`SYS-CARDSVC-STORE` | system reads writes | Card Servicing operational data <br>`DA-CARDSVC-OPERATIONAL` | ReadWrite |
| Card Servicing Service <br>`SYS-CARDSVC-API` | system reads writes | Card Servicing operational data <br>`DA-CARDSVC-OPERATIONAL` | ReadWrite |
| Card Servicing Service <br>`SYS-CARDSVC-API` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Card Servicing Service <br>`SYS-CARDSVC-API` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Cardholder mobile application <br>`SYS-MOBILE` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Cardholder mobile application <br>`SYS-MOBILE` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Collections Workspace Datastore <br>`SYS-COLLECT-STORE` | system reads writes | Collections Workspace operational data <br>`DA-COLLECT-OPERATIONAL` | ReadWrite |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system reads writes | Collections Workspace operational data <br>`DA-COLLECT-OPERATIONAL` | ReadWrite |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Contact center platform <br>`SYS-CONTACT` | system reads writes | Customer profile <br>`DA-CUSTOMER-PROFILE` | Read |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | ReadWrite |
| Credit data and decisioning environment <br>`SYS-CREDIT-DATA` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Credit data and decisioning environment <br>`SYS-CREDIT-DATA` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system reads writes | Customer 360 curated dataset <br>`DA-CUST360-CURATED` | Write |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system reads writes | Customer profile <br>`DA-CUSTOMER-PROFILE` | Read |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Customer 360 Semantic Layer <br>`SYS-CUST360-SEMANTIC` | system reads writes | Customer 360 curated dataset <br>`DA-CUST360-CURATED` | Read |
| Dynamics 365 Customer Service <br>`SYS-CRM` | system reads writes | Customer profile <br>`DA-CUSTOMER-PROFILE` | ReadWrite |
| Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | system reads writes | Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | Read |
| Financial crimes platform <br>`SYS-AML` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| IVR and self-service voice <br>`SYS-IVR` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | system reads writes | Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | Write |
| Reconciliation platform <br>`SYS-RECON` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system reads writes | Customer 360 curated dataset <br>`DA-CUST360-CURATED` | Read |
| Statement Generation <br>`SYS-STATEMENTS` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Statement Generation <br>`SYS-STATEMENTS` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Tokenization and credential management <br>`SYS-TOKEN` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Transaction fraud detection <br>`SYS-FRAUD-DETECT` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |

39 relationships across 29 entities. Generated from the model; this is a report rather than a diagram, so it is a table.
