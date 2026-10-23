# Planned Systems and Interfaces

Planned systems and interfaces, what they connect to today, and the work package delivering each one. Planned and live entities share one model, so this is a status filter rather than a separately maintained diagram.

![Planned Systems and Interfaces](../svg/target-state-change.svg)

| From | | To | Detail |
|---|---|---|---|
| Authorization Switch <br>`SYS-AUTH-SWITCH` | interface | Core Card Ledger <br>`SYS-CORE-LEDGER` | MQ |
| Authorization Switch <br>`SYS-AUTH-SWITCH` | interface | NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | HTTPS |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | interface | Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | FileTransfer |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | interface | Installment Lending Integration Hub <br>`SYS-LENDING-HUB` | HTTPS |
| Customer 360 Semantic Layer <br>`SYS-CUST360-SEMANTIC` | interface | Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | SQL |
| Customer Identity Service <br>`SYS-IDENTITY-SVC` | interface | Identity Document Verification Integration Gateway <br>`SYS-IDV-GATEWAY` | HTTPS |
| Dynamics 365 Customer Service <br>`SYS-CRM` | interface | Core Card Ledger <br>`SYS-CORE-LEDGER` | HTTPS |
| Dynamics 365 Customer Service <br>`SYS-CRM` | interface | Installment Lending Integration Hub <br>`SYS-LENDING-HUB` | HTTPS |
| Experian Credit Bureau <br>`SYS-CREDIT-BUREAU` | interface | Installment Lending Integration Hub <br>`SYS-LENDING-HUB` | HTTPS |
| Identity Document Verification <br>`SYS-IDV-VENDOR` | interface | Identity Document Verification Webhook Listener <br>`SYS-IDV-WEBHOOKS` | HTTPS |
| Identity Document Verification Integration Gateway <br>`SYS-IDV-GATEWAY` | interface | Identity Document Verification Private Egress <br>`SYS-IDV-EGRESS` | HTTPS |
| Identity Document Verification Private Egress <br>`SYS-IDV-EGRESS` | interface | Identity Document Verification <br>`SYS-IDV-VENDOR` | PrivateLink |
| Identity Document Verification Webhook Listener <br>`SYS-IDV-WEBHOOKS` | interface | Customer Identity Service <br>`SYS-IDENTITY-SVC` | HTTPS |
| Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | interface | Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | S3 |
| Installment Lending Edge <br>`SYS-LENDING-EDGE` | interface | Installment Lending Load Balancer <br>`SYS-LENDING-ALB` | HTTPS |
| Installment Lending Load Balancer <br>`SYS-LENDING-ALB` | interface | Installment Lending Web <br>`SYS-LENDING-WEB` | HTTPS |
| Installment Lending Service <br>`SYS-LENDING-API` | interface | Core Card Ledger <br>`SYS-CORE-LEDGER` | MQ |
| Installment Lending Service <br>`SYS-LENDING-API` | interface | Customer Identity Service <br>`SYS-IDENTITY-SVC` | HTTPS |
| Installment Lending Service <br>`SYS-LENDING-API` | interface | Experian Credit Bureau <br>`SYS-CREDIT-BUREAU` | HTTPS |
| Installment Lending Service <br>`SYS-LENDING-API` | interface | Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | Kafka |
| Installment Lending Service <br>`SYS-LENDING-API` | interface | Installment Lending Database <br>`SYS-LENDING-DB` | PostgreSQL |
| Installment Lending Service <br>`SYS-LENDING-API` | interface | Installment Lending Object Store <br>`SYS-LENDING-BUCKET` | HTTPS |
| Installment Lending Web <br>`SYS-LENDING-WEB` | interface | Installment Lending Service <br>`SYS-LENDING-API` | HTTPS |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | interface | Lending Portfolio Performance Semantic Layer <br>`SYS-LENDPERF-SEMANTIC` | SQL |
| Lending Portfolio Performance Semantic Layer <br>`SYS-LENDPERF-SEMANTIC` | interface | Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | HTTPS |
| Merchant Portal Service <br>`SYS-MERCHANT-API` | interface | Merchant Portal Database <br>`SYS-MERCHANT-STORE` | TDS |
| Merchant Portal Service <br>`SYS-MERCHANT-API` | interface | Merchant Portal Event Publisher <br>`SYS-MERCHANT-EVENTS` | AMQP |
| Merchant Portal Web <br>`SYS-MERCHANT-WEB` | interface | Merchant Portal Service <br>`SYS-MERCHANT-API` | HTTPS |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | interface | Security Monitoring <br>`SYS-SIEM` | HTTPS |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | interface | Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | SFTP |
| NICE Actimize Screening Identity Federation <br>`SYS-SCREENING-FEDERATION` | interface | NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | SAML |
| NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | interface | NICE Actimize Screening Private Egress <br>`SYS-SCREENING-EGRESS` | HTTPS |
| NICE Actimize Screening Private Egress <br>`SYS-SCREENING-EGRESS` | interface | NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | PrivateLink |
| Open Banking Affordability <br>`SYS-OBAFF-VENDOR` | interface | Open Banking Affordability Webhook Listener <br>`SYS-OBAFF-WEBHOOKS` | HTTPS |
| Open Banking Affordability Integration Gateway <br>`SYS-OBAFF-GATEWAY` | interface | Open Banking Affordability Private Egress <br>`SYS-OBAFF-EGRESS` | HTTPS |
| Open Banking Affordability Private Egress <br>`SYS-OBAFF-EGRESS` | interface | Open Banking Affordability <br>`SYS-OBAFF-VENDOR` | PrivateLink |
| Open Banking Affordability Webhook Listener <br>`SYS-OBAFF-WEBHOOKS` | interface | Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | HTTPS |
| Point-of-Sale Finance Event Publisher <br>`SYS-POSFIN-EVENTS` | interface | Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | Pub/Sub |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | interface | Open Banking Affordability Integration Gateway <br>`SYS-OBAFF-GATEWAY` | HTTPS |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | interface | Point-of-Sale Finance Database <br>`SYS-POSFIN-DB` | PostgreSQL |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | interface | Point-of-Sale Finance Event Publisher <br>`SYS-POSFIN-EVENTS` | AMQP |
| Point-of-Sale Finance Web <br>`SYS-POSFIN-WEB` | interface | Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | HTTPS |
| Rewards Redemption Async Worker <br>`SYS-REWARDS-WORKER` | interface | Core Card Ledger <br>`SYS-CORE-LEDGER` | MQ |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | interface | Rewards Redemption Database <br>`SYS-REWARDS-STORE` | TDS |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | interface | Rewards Redemption Event Publisher <br>`SYS-REWARDS-EVENTS` | AMQP |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | interface | Rewards Redemption Async Worker <br>`SYS-REWARDS-WORKER` | Kafka |
| Rewards Redemption Web <br>`SYS-REWARDS-WEB` | interface | Rewards Redemption Service <br>`SYS-REWARDS-API` | HTTPS |
| Customer 360 Semantic Layer <br>`SYS-CUST360-SEMANTIC` | system reads writes | Customer 360 curated dataset <br>`DA-CUST360-CURATED` | Read |
| Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | system reads writes | NICE Actimize Screening outcomes <br>`DA-SCREENING-OUTCOMES` | Read |
| Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | system reads writes | Installment Lending operational data <br>`DA-LENDING-OPERATIONAL` | Read |
| Installment Lending Service <br>`SYS-LENDING-API` | system reads writes | Installment Lending operational data <br>`DA-LENDING-OPERATIONAL` | ReadWrite |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | system reads writes | Lending Portfolio Performance curated dataset <br>`DA-LENDPERF-CURATED` | Write |
| Lending Portfolio Performance Semantic Layer <br>`SYS-LENDPERF-SEMANTIC` | system reads writes | Lending Portfolio Performance curated dataset <br>`DA-LENDPERF-CURATED` | Read |
| Merchant Portal Service <br>`SYS-MERCHANT-API` | system reads writes | Merchant Portal operational data <br>`DA-MERCHANT-OPERATIONAL` | ReadWrite |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | system reads writes | NICE Actimize Screening outcomes <br>`DA-SCREENING-OUTCOMES` | Write |
| Point-of-Sale Finance Database <br>`SYS-POSFIN-DB` | system reads writes | Point-of-Sale Finance operational data <br>`DA-POSFIN-OPERATIONAL` | ReadWrite |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | system reads writes | Point-of-Sale Finance operational data <br>`DA-POSFIN-OPERATIONAL` | ReadWrite |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system reads writes | Lending Portfolio Performance curated dataset <br>`DA-LENDPERF-CURATED` | Read |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system reads writes | Customer 360 curated dataset <br>`DA-CUST360-CURATED` | Read |
| Rewards Redemption Database <br>`SYS-REWARDS-STORE` | system reads writes | Rewards Redemption operational data <br>`DA-REWARDS-OPERATIONAL` | ReadWrite |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | system reads writes | Rewards Redemption operational data <br>`DA-REWARDS-OPERATIONAL` | ReadWrite |
| Assemble the merchant portal on Azure <br>`WP-MERCHANT-PORTAL` | work package affects system | Merchant Portal Web <br>`SYS-MERCHANT-WEB` | Builds |
| Assemble the merchant portal on Azure <br>`WP-MERCHANT-PORTAL` | work package affects system | Merchant Portal Service <br>`SYS-MERCHANT-API` | Builds |
| Assemble the merchant portal on Azure <br>`WP-MERCHANT-PORTAL` | work package affects system | Merchant Portal Database <br>`SYS-MERCHANT-STORE` | Builds |
| Assemble the merchant portal on Azure <br>`WP-MERCHANT-PORTAL` | work package affects system | Merchant Portal Event Publisher <br>`SYS-MERCHANT-EVENTS` | Builds |
| Build installment lending on AWS <br>`WP-LENDING-AWS` | work package affects system | Installment Lending Edge <br>`SYS-LENDING-EDGE` | Builds |
| Build installment lending on AWS <br>`WP-LENDING-AWS` | work package affects system | Installment Lending Load Balancer <br>`SYS-LENDING-ALB` | Builds |
| Build installment lending on AWS <br>`WP-LENDING-AWS` | work package affects system | Installment Lending Web <br>`SYS-LENDING-WEB` | Builds |
| Build installment lending on AWS <br>`WP-LENDING-AWS` | work package affects system | Installment Lending Service <br>`SYS-LENDING-API` | Builds |
| Build installment lending on AWS <br>`WP-LENDING-AWS` | work package affects system | Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | Builds |
| Build installment lending on AWS <br>`WP-LENDING-AWS` | work package affects system | Installment Lending Database <br>`SYS-LENDING-DB` | Builds |
| Build installment lending on AWS <br>`WP-LENDING-AWS` | work package affects system | Installment Lending Object Store <br>`SYS-LENDING-BUCKET` | Builds |
| Build installment lending on AWS <br>`WP-LENDING-AWS` | work package affects system | Installment Lending Integration Hub <br>`SYS-LENDING-HUB` | Builds |
| Build rewards redemption on Azure <br>`WP-REWARDS-BUILD` | work package affects system | Rewards Redemption Web <br>`SYS-REWARDS-WEB` | Builds |
| Build rewards redemption on Azure <br>`WP-REWARDS-BUILD` | work package affects system | Rewards Redemption Service <br>`SYS-REWARDS-API` | Builds |
| Build rewards redemption on Azure <br>`WP-REWARDS-BUILD` | work package affects system | Rewards Redemption Database <br>`SYS-REWARDS-STORE` | Builds |
| Build rewards redemption on Azure <br>`WP-REWARDS-BUILD` | work package affects system | Rewards Redemption Event Publisher <br>`SYS-REWARDS-EVENTS` | Builds |
| Build rewards redemption on Azure <br>`WP-REWARDS-BUILD` | work package affects system | Rewards Redemption Async Worker <br>`SYS-REWARDS-WORKER` | Builds |
| Buy affordability data for point-of-sale finance <br>`WP-OB-AFFORDABILITY` | work package affects system | Open Banking Affordability <br>`SYS-OBAFF-VENDOR` | Builds |
| Buy affordability data for point-of-sale finance <br>`WP-OB-AFFORDABILITY` | work package affects system | Open Banking Affordability Integration Gateway <br>`SYS-OBAFF-GATEWAY` | Builds |
| Buy affordability data for point-of-sale finance <br>`WP-OB-AFFORDABILITY` | work package affects system | Open Banking Affordability Private Egress <br>`SYS-OBAFF-EGRESS` | Builds |
| Buy affordability data for point-of-sale finance <br>`WP-OB-AFFORDABILITY` | work package affects system | Open Banking Affordability Webhook Listener <br>`SYS-OBAFF-WEBHOOKS` | Builds |
| Curate lending performance in BigQuery <br>`WP-LENDING-PERFORMANCE` | work package affects system | Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | Builds |
| Curate lending performance in BigQuery <br>`WP-LENDING-PERFORMANCE` | work package affects system | Lending Portfolio Performance Semantic Layer <br>`SYS-LENDPERF-SEMANTIC` | Builds |
| Land point-of-sale finance on Google Cloud <br>`WP-POS-FINANCE` | work package affects system | Point-of-Sale Finance Web <br>`SYS-POSFIN-WEB` | Builds |
| Land point-of-sale finance on Google Cloud <br>`WP-POS-FINANCE` | work package affects system | Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | Builds |
| Land point-of-sale finance on Google Cloud <br>`WP-POS-FINANCE` | work package affects system | Point-of-Sale Finance Database <br>`SYS-POSFIN-DB` | Builds |
| Land point-of-sale finance on Google Cloud <br>`WP-POS-FINANCE` | work package affects system | Point-of-Sale Finance Event Publisher <br>`SYS-POSFIN-EVENTS` | Builds |
| Onboard the identity verification vendor <br>`WP-IDV-ONBOARD` | work package affects system | Identity Document Verification <br>`SYS-IDV-VENDOR` | Builds |
| Onboard the identity verification vendor <br>`WP-IDV-ONBOARD` | work package affects system | Identity Document Verification Integration Gateway <br>`SYS-IDV-GATEWAY` | Builds |
| Onboard the identity verification vendor <br>`WP-IDV-ONBOARD` | work package affects system | Identity Document Verification Private Egress <br>`SYS-IDV-EGRESS` | Builds |
| Onboard the identity verification vendor <br>`WP-IDV-ONBOARD` | work package affects system | Identity Document Verification Webhook Listener <br>`SYS-IDV-WEBHOOKS` | Builds |
| Onboard the identity verification vendor <br>`WP-IDV-ONBOARD` | work package affects system | Customer Identity Service <br>`SYS-IDENTITY-SVC` | Changes |
| Onboard the screening vendor <br>`WP-SCREENING-ONBOARD` | work package affects system | NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | Builds |
| Onboard the screening vendor <br>`WP-SCREENING-ONBOARD` | work package affects system | NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | Builds |
| Onboard the screening vendor <br>`WP-SCREENING-ONBOARD` | work package affects system | NICE Actimize Screening Private Egress <br>`SYS-SCREENING-EGRESS` | Builds |
| Onboard the screening vendor <br>`WP-SCREENING-ONBOARD` | work package affects system | NICE Actimize Screening Identity Federation <br>`SYS-SCREENING-FEDERATION` | Builds |
| Onboard the screening vendor <br>`WP-SCREENING-ONBOARD` | work package affects system | Authorization Switch <br>`SYS-AUTH-SWITCH` | Changes |
| Stand up the regulatory reporting engine <br>`WP-REG-REPORTING` | work package affects system | Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | Builds |
| Stand up the regulatory reporting engine <br>`WP-REG-REPORTING` | work package affects system | Customer 360 Semantic Layer <br>`SYS-CUST360-SEMANTIC` | Changes |

100 relationships across 60 entities. Generated from the model; this is a report rather than a diagram, so it is a table.
