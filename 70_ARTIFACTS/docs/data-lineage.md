# Data Lineage

Where each data asset is mastered and which systems read or write it. More than one writer for the same asset means there is no single system of record.

![Data Lineage](../svg/data-lineage.svg)

| From | | To | Detail |
|---|---|---|---|
| Authorization Switch <br>`SYS-AUTH-SWITCH` | sot | Card transaction history <br>`DA-TRANSACTION` | masters |
| Card Servicing Datastore <br>`SYS-CARDSVC-STORE` | sot | Card Servicing operational data <br>`DA-CARDSVC-OPERATIONAL` | masters |
| Collections Workspace Datastore <br>`SYS-COLLECT-STORE` | sot | Collections Workspace operational data <br>`DA-COLLECT-OPERATIONAL` | masters |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | sot | Card account master <br>`DA-CARD-ACCOUNT` | masters |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | sot | Customer 360 curated dataset <br>`DA-CUST360-CURATED` | masters |
| Dynamics 365 Customer Service <br>`SYS-CRM` | sot | Customer profile <br>`DA-CUSTOMER-PROFILE` | masters |
| Installment Lending Database <br>`SYS-LENDING-DB` | sot | Installment Lending operational data <br>`DA-LENDING-OPERATIONAL` | masters |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | sot | Lending Portfolio Performance curated dataset <br>`DA-LENDPERF-CURATED` | masters |
| Merchant Portal Database <br>`SYS-MERCHANT-STORE` | sot | Merchant Portal operational data <br>`DA-MERCHANT-OPERATIONAL` | masters |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | sot | NICE Actimize Screening outcomes <br>`DA-SCREENING-OUTCOMES` | masters |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | sot | Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | masters |
| Point-of-Sale Finance Database <br>`SYS-POSFIN-DB` | sot | Point-of-Sale Finance operational data <br>`DA-POSFIN-OPERATIONAL` | masters |
| Rewards Redemption Database <br>`SYS-REWARDS-STORE` | sot | Rewards Redemption operational data <br>`DA-REWARDS-OPERATIONAL` | masters |
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
| Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | system reads writes | NICE Actimize Screening outcomes <br>`DA-SCREENING-OUTCOMES` | Read |
| Financial crimes platform <br>`SYS-AML` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | system reads writes | Installment Lending operational data <br>`DA-LENDING-OPERATIONAL` | Read |
| Installment Lending Service <br>`SYS-LENDING-API` | system reads writes | Installment Lending operational data <br>`DA-LENDING-OPERATIONAL` | ReadWrite |
| IVR and self-service voice <br>`SYS-IVR` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | system reads writes | Lending Portfolio Performance curated dataset <br>`DA-LENDPERF-CURATED` | Write |
| Lending Portfolio Performance Semantic Layer <br>`SYS-LENDPERF-SEMANTIC` | system reads writes | Lending Portfolio Performance curated dataset <br>`DA-LENDPERF-CURATED` | Read |
| Merchant Portal Service <br>`SYS-MERCHANT-API` | system reads writes | Merchant Portal operational data <br>`DA-MERCHANT-OPERATIONAL` | ReadWrite |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | system reads writes | NICE Actimize Screening outcomes <br>`DA-SCREENING-OUTCOMES` | Write |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | system reads writes | Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | Write |
| Point-of-Sale Finance Database <br>`SYS-POSFIN-DB` | system reads writes | Point-of-Sale Finance operational data <br>`DA-POSFIN-OPERATIONAL` | ReadWrite |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | system reads writes | Point-of-Sale Finance operational data <br>`DA-POSFIN-OPERATIONAL` | ReadWrite |
| Reconciliation platform <br>`SYS-RECON` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system reads writes | Lending Portfolio Performance curated dataset <br>`DA-LENDPERF-CURATED` | Read |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system reads writes | Customer 360 curated dataset <br>`DA-CUST360-CURATED` | Read |
| Rewards Redemption Database <br>`SYS-REWARDS-STORE` | system reads writes | Rewards Redemption operational data <br>`DA-REWARDS-OPERATIONAL` | ReadWrite |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | system reads writes | Rewards Redemption operational data <br>`DA-REWARDS-OPERATIONAL` | ReadWrite |
| Statement Generation <br>`SYS-STATEMENTS` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Statement Generation <br>`SYS-STATEMENTS` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |
| Tokenization and credential management <br>`SYS-TOKEN` | system reads writes | Card account master <br>`DA-CARD-ACCOUNT` | Read |
| Transaction fraud detection <br>`SYS-FRAUD-DETECT` | system reads writes | Card transaction history <br>`DA-TRANSACTION` | Read |

57 relationships across 47 entities. Generated from the model; this is a report rather than a diagram, so it is a table.
