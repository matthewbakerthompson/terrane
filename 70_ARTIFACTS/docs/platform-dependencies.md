# Platform Dependencies

Which technology services each system runs on. The systems attached to a service are the ones affected if that service changes.

![Platform Dependencies](../svg/platform-dependencies.svg)

| From | | To |
|---|---|---|
| Card Servicing Datastore <br>`SYS-CARDSVC-STORE` | system uses tech service | Azure SQL Database <br>`TS-AZURE-SQL` |
| Card Servicing Datastore <br>`SYS-CARDSVC-STORE` | system uses tech service | Card Servicing Backup and recovery <br>`TS-CARDSVC-BACKUP` |
| Card Servicing Datastore <br>`SYS-CARDSVC-STORE` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Card Servicing Event Publisher <br>`SYS-CARDSVC-EVENTS` | system uses tech service | Azure Service Bus <br>`TS-AZURE-SERVICEBUS` |
| Card Servicing Service <br>`SYS-CARDSVC-API` | system uses tech service | Azure API Management <br>`TS-AZURE-APIM` |
| Card Servicing Service <br>`SYS-CARDSVC-API` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Card Servicing Service <br>`SYS-CARDSVC-API` | system uses tech service | Card Servicing Cache <br>`TS-CARDSVC-CACHE` |
| Card Servicing Service <br>`SYS-CARDSVC-API` | system uses tech service | Azure Monitor <br>`TS-AZURE-MONITOR` |
| Card Servicing Service <br>`SYS-CARDSVC-API` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Card Servicing Web <br>`SYS-CARDSVC-WEB` | system uses tech service | Card Servicing Web application firewall <br>`TS-CARDSVC-WAF` |
| Card Servicing Web <br>`SYS-CARDSVC-WEB` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Card Servicing Web <br>`SYS-CARDSVC-WEB` | system uses tech service | Microsoft Entra ID <br>`TS-ENTRA-ID` |
| Collections Workspace Datastore <br>`SYS-COLLECT-STORE` | system uses tech service | Azure SQL Database <br>`TS-AZURE-SQL` |
| Collections Workspace Datastore <br>`SYS-COLLECT-STORE` | system uses tech service | Collections Workspace Backup and recovery <br>`TS-COLLECT-BACKUP` |
| Collections Workspace Datastore <br>`SYS-COLLECT-STORE` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system uses tech service | Azure API Management <br>`TS-AZURE-APIM` |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system uses tech service | Collections Workspace Cache <br>`TS-COLLECT-CACHE` |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system uses tech service | Azure Monitor <br>`TS-AZURE-MONITOR` |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Collections Workspace Web <br>`SYS-COLLECT-WEB` | system uses tech service | Collections Workspace Web application firewall <br>`TS-COLLECT-WAF` |
| Collections Workspace Web <br>`SYS-COLLECT-WEB` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Collections Workspace Web <br>`SYS-COLLECT-WEB` | system uses tech service | Microsoft Entra ID <br>`TS-ENTRA-ID` |
| Credit data and decisioning environment <br>`SYS-CREDIT-DATA` | system uses tech service | Snowflake <br>`TS-SNOWFLAKE` |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system uses tech service | Snowflake <br>`TS-SNOWFLAKE` |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system uses tech service | Collibra <br>`TS-COLLIBRA` |
| Customer 360 Semantic Layer <br>`SYS-CUST360-SEMANTIC` | system uses tech service | Snowflake <br>`TS-SNOWFLAKE` |
| Customer Identity Service <br>`SYS-IDENTITY-SVC` | system uses tech service | Customer Identity Service Web application firewall <br>`TS-IDENTITY-WAF` |
| Customer Identity Service <br>`SYS-IDENTITY-SVC` | system uses tech service | Azure API Management <br>`TS-AZURE-APIM` |
| Customer Identity Service <br>`SYS-IDENTITY-SVC` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Customer Identity Service <br>`SYS-IDENTITY-SVC` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Dispute Management Platform Integration Gateway <br>`SYS-DISPUTES-GATEWAY` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Dispute Management Platform Integration Gateway <br>`SYS-DISPUTES-GATEWAY` | system uses tech service | Azure API Management <br>`TS-AZURE-APIM` |
| Dispute Management Platform Integration Gateway <br>`SYS-DISPUTES-GATEWAY` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Dynamics 365 Customer Service <br>`SYS-CRM` | system uses tech service | Microsoft Entra ID <br>`TS-ENTRA-ID` |
| Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | system uses tech service | Azure Service Bus <br>`TS-AZURE-SERVICEBUS` |
| Enterprise Data Ingestion Hub <br>`SYS-DATA-INGEST` | system uses tech service | Snowflake <br>`TS-SNOWFLAKE` |
| Governance catalog <br>`SYS-CATALOG` | system uses tech service | Collibra <br>`TS-COLLIBRA` |
| Identity and access management <br>`SYS-IAM` | system uses tech service | Microsoft Entra ID <br>`TS-ENTRA-ID` |
| Identity Document Verification Integration Gateway <br>`SYS-IDV-GATEWAY` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Identity Document Verification Integration Gateway <br>`SYS-IDV-GATEWAY` | system uses tech service | Azure API Management <br>`TS-AZURE-APIM` |
| Identity Document Verification Integration Gateway <br>`SYS-IDV-GATEWAY` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Identity Document Verification Webhook Listener <br>`SYS-IDV-WEBHOOKS` | system uses tech service | Azure API Management <br>`TS-AZURE-APIM` |
| Identity Document Verification Webhook Listener <br>`SYS-IDV-WEBHOOKS` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | system uses tech service | Amazon EKS <br>`TS-AWS-EKS` |
| Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | system uses tech service | Amazon CloudWatch <br>`TS-AWS-CLOUDWATCH` |
| Installment Lending Async Worker <br>`SYS-LENDING-WORKER` | system uses tech service | Amazon MSK <br>`TS-AWS-MSK` |
| Installment Lending Database <br>`SYS-LENDING-DB` | system uses tech service | Amazon RDS for PostgreSQL <br>`TS-AWS-RDS` |
| Installment Lending Database <br>`SYS-LENDING-DB` | system uses tech service | AWS KMS <br>`TS-AWS-KMS` |
| Installment Lending Object Store <br>`SYS-LENDING-BUCKET` | system uses tech service | Amazon S3 <br>`TS-AWS-S3` |
| Installment Lending Object Store <br>`SYS-LENDING-BUCKET` | system uses tech service | AWS KMS <br>`TS-AWS-KMS` |
| Installment Lending Service <br>`SYS-LENDING-API` | system uses tech service | Amazon EKS <br>`TS-AWS-EKS` |
| Installment Lending Service <br>`SYS-LENDING-API` | system uses tech service | Amazon CloudWatch <br>`TS-AWS-CLOUDWATCH` |
| Installment Lending Service <br>`SYS-LENDING-API` | system uses tech service | AWS Secrets Manager <br>`TS-AWS-SECRETS` |
| Installment Lending Web <br>`SYS-LENDING-WEB` | system uses tech service | Amazon EKS <br>`TS-AWS-EKS` |
| Installment Lending Web <br>`SYS-LENDING-WEB` | system uses tech service | Amazon CloudWatch <br>`TS-AWS-CLOUDWATCH` |
| IT service management <br>`SYS-ITSM` | system uses tech service | ServiceNow <br>`TS-SERVICENOW` |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | system uses tech service | Pub/Sub <br>`TS-GCP-PUBSUB` |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | system uses tech service | Dataflow <br>`TS-GCP-DATAFLOW` |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | system uses tech service | Cloud Composer <br>`TS-GCP-COMPOSER` |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | system uses tech service | BigQuery <br>`TS-GCP-BIGQUERY` |
| Lending Portfolio Performance Pipeline <br>`SYS-LENDPERF-PIPELINE` | system uses tech service | Collibra <br>`TS-COLLIBRA` |
| Lending Portfolio Performance Semantic Layer <br>`SYS-LENDPERF-SEMANTIC` | system uses tech service | BigQuery <br>`TS-GCP-BIGQUERY` |
| Lending Portfolio Performance Semantic Layer <br>`SYS-LENDPERF-SEMANTIC` | system uses tech service | Looker <br>`TS-GCP-LOOKER` |
| Merchant Portal Database <br>`SYS-MERCHANT-STORE` | system uses tech service | Azure SQL Database <br>`TS-AZURE-SQL` |
| Merchant Portal Database <br>`SYS-MERCHANT-STORE` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Merchant Portal Event Publisher <br>`SYS-MERCHANT-EVENTS` | system uses tech service | Azure Service Bus <br>`TS-AZURE-SERVICEBUS` |
| Merchant Portal Service <br>`SYS-MERCHANT-API` | system uses tech service | Azure API Management <br>`TS-AZURE-APIM` |
| Merchant Portal Service <br>`SYS-MERCHANT-API` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Merchant Portal Service <br>`SYS-MERCHANT-API` | system uses tech service | Azure Monitor <br>`TS-AZURE-MONITOR` |
| Merchant Portal Service <br>`SYS-MERCHANT-API` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Merchant Portal Web <br>`SYS-MERCHANT-WEB` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Merchant Portal Web <br>`SYS-MERCHANT-WEB` | system uses tech service | Microsoft Entra ID <br>`TS-ENTRA-ID` |
| NICE Actimize Screening Identity Federation <br>`SYS-SCREENING-FEDERATION` | system uses tech service | Microsoft Entra ID <br>`TS-ENTRA-ID` |
| NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | system uses tech service | Amazon EKS <br>`TS-AWS-EKS` |
| NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | system uses tech service | Amazon API Gateway <br>`TS-AWS-APIGW` |
| NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | system uses tech service | AWS Secrets Manager <br>`TS-AWS-SECRETS` |
| NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | system uses tech service | Amazon CloudWatch <br>`TS-AWS-CLOUDWATCH` |
| Open Banking Affordability Integration Gateway <br>`SYS-OBAFF-GATEWAY` | system uses tech service | Google Kubernetes Engine <br>`TS-GCP-GKE` |
| Open Banking Affordability Integration Gateway <br>`SYS-OBAFF-GATEWAY` | system uses tech service | Apigee <br>`TS-GCP-APIGEE` |
| Open Banking Affordability Integration Gateway <br>`SYS-OBAFF-GATEWAY` | system uses tech service | Secret Manager <br>`TS-GCP-SECRET-MANAGER` |
| Open Banking Affordability Webhook Listener <br>`SYS-OBAFF-WEBHOOKS` | system uses tech service | Apigee <br>`TS-GCP-APIGEE` |
| Open Banking Affordability Webhook Listener <br>`SYS-OBAFF-WEBHOOKS` | system uses tech service | Google Kubernetes Engine <br>`TS-GCP-GKE` |
| Point-of-Sale Finance Database <br>`SYS-POSFIN-DB` | system uses tech service | Cloud SQL for PostgreSQL <br>`TS-GCP-CLOUD-SQL` |
| Point-of-Sale Finance Database <br>`SYS-POSFIN-DB` | system uses tech service | Cloud KMS <br>`TS-GCP-KMS` |
| Point-of-Sale Finance Event Publisher <br>`SYS-POSFIN-EVENTS` | system uses tech service | Pub/Sub <br>`TS-GCP-PUBSUB` |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | system uses tech service | Apigee <br>`TS-GCP-APIGEE` |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | system uses tech service | Google Kubernetes Engine <br>`TS-GCP-GKE` |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | system uses tech service | Cloud Monitoring <br>`TS-GCP-MONITORING` |
| Point-of-Sale Finance Service <br>`SYS-POSFIN-API` | system uses tech service | Secret Manager <br>`TS-GCP-SECRET-MANAGER` |
| Point-of-Sale Finance Web <br>`SYS-POSFIN-WEB` | system uses tech service | Google Kubernetes Engine <br>`TS-GCP-GKE` |
| Point-of-Sale Finance Web <br>`SYS-POSFIN-WEB` | system uses tech service | Microsoft Entra ID <br>`TS-ENTRA-ID` |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system uses tech service | Snowflake <br>`TS-SNOWFLAKE` |
| Rewards Redemption Async Worker <br>`SYS-REWARDS-WORKER` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Rewards Redemption Async Worker <br>`SYS-REWARDS-WORKER` | system uses tech service | Azure Monitor <br>`TS-AZURE-MONITOR` |
| Rewards Redemption Async Worker <br>`SYS-REWARDS-WORKER` | system uses tech service | Azure Event Hubs <br>`TS-AZURE-EVENTHUBS` |
| Rewards Redemption Database <br>`SYS-REWARDS-STORE` | system uses tech service | Azure SQL Database <br>`TS-AZURE-SQL` |
| Rewards Redemption Database <br>`SYS-REWARDS-STORE` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Rewards Redemption Event Publisher <br>`SYS-REWARDS-EVENTS` | system uses tech service | Azure Service Bus <br>`TS-AZURE-SERVICEBUS` |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | system uses tech service | Azure API Management <br>`TS-AZURE-APIM` |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | system uses tech service | Azure Monitor <br>`TS-AZURE-MONITOR` |
| Rewards Redemption Service <br>`SYS-REWARDS-API` | system uses tech service | Azure Key Vault <br>`TS-AZURE-KEYVAULT` |
| Rewards Redemption Web <br>`SYS-REWARDS-WEB` | system uses tech service | Azure Kubernetes Service <br>`TS-AZURE-AKS` |
| Rewards Redemption Web <br>`SYS-REWARDS-WEB` | system uses tech service | Microsoft Entra ID <br>`TS-ENTRA-ID` |

106 relationships across 91 entities. Generated from the model; this is a report rather than a diagram, so it is a table.
