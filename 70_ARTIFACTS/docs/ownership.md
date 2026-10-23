# Who Owns What

Every system and the organizational unit that owns it. This is the "who do I call" lookup for incidents. Check for systems assigned to a unit that does not recognize them.

![Who Owns What](../svg/ownership.svg)

| From | | To | Detail |
|---|---|---|---|
| Collections <br>`ORG-COLLECTIONS` | owner | Collections Workspace Service <br>`SYS-COLLECT-API` | owns |
| Collections <br>`ORG-COLLECTIONS` | owner | Collections Workspace Web <br>`SYS-COLLECT-WEB` | owns |
| Collections <br>`ORG-COLLECTIONS` | owner | Collections Workspace Datastore <br>`SYS-COLLECT-STORE` | owns |
| Compliance <br>`ORG-COMPLIANCE` | owner | Experian Credit Bureau <br>`SYS-CREDIT-BUREAU` | owns |
| Compliance <br>`ORG-COMPLIANCE` | owner | Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | owns |
| Compliance <br>`ORG-COMPLIANCE` | owner | Identity Document Verification <br>`SYS-IDV-VENDOR` | owns |
| Compliance <br>`ORG-COMPLIANCE` | owner | Identity Document Verification Integration Gateway <br>`SYS-IDV-GATEWAY` | owns |
| Compliance <br>`ORG-COMPLIANCE` | owner | Identity Document Verification Webhook Listener <br>`SYS-IDV-WEBHOOKS` | owns |
| Compliance <br>`ORG-COMPLIANCE` | owner | NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | owns |
| Compliance <br>`ORG-COMPLIANCE` | owner | NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | owns |
| Customer Servicing <br>`ORG-SERVICING` | owner | Dynamics 365 Customer Service <br>`SYS-CRM` | owns |
| Customer Servicing <br>`ORG-SERVICING` | owner | Statement Generation <br>`SYS-STATEMENTS` | owns |
| Customer Servicing <br>`ORG-SERVICING` | owner | Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | owns |
| Customer Servicing <br>`ORG-SERVICING` | owner | Dispute Management Platform Integration Gateway <br>`SYS-DISPUTES-GATEWAY` | owns |
| Data Engineering <br>`ORG-DATAENG` | owner | Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | owns |
| Data Engineering <br>`ORG-DATAENG` | owner | Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | owns |
| Data Engineering <br>`ORG-DATAENG` | owner | Customer 360 Semantic Layer <br>`SYS-CUST360-SEMANTIC` | owns |
| Digital Servicing <br>`ORG-DIGITAL` | owner | Card Servicing Service <br>`SYS-CARDSVC-API` | owns |
| Digital Servicing <br>`ORG-DIGITAL` | owner | Card Servicing Web <br>`SYS-CARDSVC-WEB` | owns |
| Digital Servicing <br>`ORG-DIGITAL` | owner | Card Servicing Datastore <br>`SYS-CARDSVC-STORE` | owns |
| Digital Servicing <br>`ORG-DIGITAL` | owner | Card Servicing Event Publisher <br>`SYS-CARDSVC-EVENTS` | owns |
| Information Security <br>`ORG-INFOSEC` | owner | Security Monitoring <br>`SYS-SIEM` | owns |
| Payments Operations <br>`ORG-PAYMENTS` | owner | Authorization Switch <br>`SYS-AUTH-SWITCH` | owns |
| Payments Operations <br>`ORG-PAYMENTS` | owner | Core Card Ledger <br>`SYS-CORE-LEDGER` | owns |
| Product Management <br>`ORG-PRODUCT` | owner | Installment Lending Service <br>`SYS-LENDING-API` | owns |
| Product Management <br>`ORG-PRODUCT` | owner | Installment Lending Web <br>`SYS-LENDING-WEB` | owns |
| Product Management <br>`ORG-PRODUCT` | owner | Installment Lending Edge <br>`SYS-LENDING-EDGE` | owns |
| Product Management <br>`ORG-PRODUCT` | owner | Installment Lending Load Balancer <br>`SYS-LENDING-ALB` | owns |
| Product Management <br>`ORG-PRODUCT` | owner | Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | owns |
| Product Management <br>`ORG-PRODUCT` | owner | Installment Lending Database <br>`SYS-LENDING-DB` | owns |
| Product Management <br>`ORG-PRODUCT` | owner | Installment Lending Object Store <br>`SYS-LENDING-BUCKET` | owns |
| Product Management <br>`ORG-PRODUCT` | owner | Installment Lending Integration Hub <br>`SYS-LENDING-HUB` | owns |
| Rewards Operations <br>`ORG-REWARDS` | owner | Rewards Redemption Service <br>`SYS-REWARDS-API` | owns |
| Rewards Operations <br>`ORG-REWARDS` | owner | Rewards Redemption Web <br>`SYS-REWARDS-WEB` | owns |
| Rewards Operations <br>`ORG-REWARDS` | owner | Rewards Redemption Database <br>`SYS-REWARDS-STORE` | owns |
| Rewards Operations <br>`ORG-REWARDS` | owner | Rewards Redemption Event Publisher <br>`SYS-REWARDS-EVENTS` | owns |
| Rewards Operations <br>`ORG-REWARDS` | owner | Rewards Redemption Async Worker <br>`SYS-REWARDS-WORKER` | owns |
| Technology <br>`ORG-TECH` | owner | Customer Identity Service <br>`SYS-IDENTITY-SVC` | owns |
| Technology <br>`ORG-TECH` | owner | Identity Document Verification Private Egress <br>`SYS-IDV-EGRESS` | owns |
| Technology <br>`ORG-TECH` | owner | Open Banking Affordability Private Egress <br>`SYS-OBAFF-EGRESS` | owns |
| Technology <br>`ORG-TECH` | owner | NICE Actimize Screening Identity Federation <br>`SYS-SCREENING-FEDERATION` | owns |
| Technology <br>`ORG-TECH` | owner | NICE Actimize Screening Private Egress <br>`SYS-SCREENING-EGRESS` | owns |

42 relationships across 90 entities. Generated from the model; this is a report rather than a diagram, so it is a table.
