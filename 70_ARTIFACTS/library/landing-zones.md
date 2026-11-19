# Landing zones

A landing zone is what a provider already runs for whatever lands on it: one shared service of each kind, tagged `landing-zone`, found by kind when a part asks. Nothing about it is written on a shape; a shape says its provider and the parts resolve. Measured here against the providers the shapes land on, with the kinds the parts name that each cannot answer -- where the next onboarding would stop. Generated from `10_MODEL/tech_services/`, `28_MODULES/` and `20_ARCHETYPES/` by `terrane render`; edit those, not this.

| Provider | Shapes | Products | Kinds | Asked for and missing |
|---|---|---:|---:|---|
| [AWS](#aws) | `aws-product-onboarding`, `aws-workload-network`, `saas-onboarding` | 2 | 23 | — |
| [Azure](#azure) | `azure-digital-product`, `azure-workload-network`, `core-platform-service`, `vendor-saas-service` | 23 | 19 | — |
| [GCP](#gcp) | `batch-data-product-gcp`, `gcp-digital-product`, `gcp-workload-network`, `vendor-saas-service-gcp` | 3 | 29 | — |

<a id="aws"></a>
## AWS

**Shapes.** `aws-product-onboarding`, `aws-workload-network`, `saas-onboarding`.

| Kind | Service | Asked for by |
|---|---|---|
| `agent-platform` | Amazon Bedrock AgentCore (`TS-AWS-AGENTCORE`) | `agent-service` (platform) |
| `ai-gateway` | Amazon Bedrock Guardrails (`TS-AWS-BEDROCK-GUARDRAILS`) | `agent-service` (gateway), `ml-inference-service` (gateway) |
| `api-gateway` | Amazon API Gateway (`TS-AWS-APIGW`) | `api-outbound` (front_door), `mobile-channel` (front_door), `partner-api` (front_door), `webhook-inbound` (front_door) |
| `cdn` | Amazon CloudFront and WAF (`TS-AWS-CLOUDFRONT`) | — |
| `container-platform` | Amazon EKS (`TS-AWS-EKS`) | `api-outbound` (platform), `webhook-inbound` (platform) |
| `customer-identity` | Amazon Cognito (`TS-AWS-COGNITO`) | `customer-sign-in` (ciam) |
| `dns` | Route 53 Resolver (`TS-NET-ROUTE53`) | `workload-network` (dns) |
| `document-ai` | Amazon Textract (`TS-AWS-TEXTRACT`) | `document-intake` (reader) |
| `event-stream` | Amazon MSK (`TS-AWS-MSK`) | `async-worker` (stream) |
| `foundation-model-service` | Amazon Bedrock (`TS-AWS-BEDROCK`) | `agent-service` (models), `ml-inference-service` (models), `retrieval-index` (models) |
| `hybrid-link` | Direct Connect (`TS-NET-DX`), Site-to-Site VPN (`TS-NET-VPN`) — ambiguous | — |
| `iac` | AWS Organizations (`TS-AWS-ORG`) | — |
| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`), shared | `admin-console` (idp), `assistant-chat` (idp), `identity-hub` (idp), `sso-federation` (idp) |
| `kms` | AWS KMS (`TS-AWS-KMS`) | `byok-encryption` (kms) |
| `load-balancer` | Application Load Balancer (`TS-AWS-ALB`) | — |
| `message-queue` | Amazon SQS (`TS-AWS-SQS`) | `event-consumer` (bus), `event-hub` (bus), `event-publisher` (bus), `notification-service` (bus) |
| `object-store` | Amazon S3 (`TS-AWS-S3`) | — |
| `observability` | Amazon CloudWatch (`TS-AWS-CLOUDWATCH`) | `vendor-monitoring` (observability) |
| `private-egress` | AWS PrivateLink (`TS-AWS-PRIVATELINK`) | `private-egress` (private_link) |
| `relational-db` | Amazon RDS for PostgreSQL (`TS-AWS-RDS`) | — |
| `secrets-manager` | AWS Secrets Manager (`TS-AWS-SECRETS`) | `partner-adapter` (secrets), `secrets-management` (vault) |
| `transit-gateway` | AWS Transit Gateway (`TS-AWS-TGW`) | `private-egress` (transit), `workload-network` (transit) |
| `vector-database` | Amazon OpenSearch Service (`TS-AWS-OPENSEARCH`) | `retrieval-index` (vectors) |
| `vpc` | Shared Services VPC (`TS-NET-VPC-SHARED`) | — |

<a id="azure"></a>
## Azure

**Shapes.** `azure-digital-product`, `azure-workload-network`, `core-platform-service`, `vendor-saas-service`.

| Kind | Service | Asked for by |
|---|---|---|
| `agent-platform` | Microsoft Foundry (`TS-AZURE-FOUNDRY`) — a `foundation-model-service` that answers for it | `agent-service` (platform) |
| `ai-gateway` | Azure API Management (`TS-AZURE-APIM`) — a `api-gateway` that answers for it | `agent-service` (gateway), `ml-inference-service` (gateway) |
| `api-gateway` | Azure API Management (`TS-AZURE-APIM`) | `api-outbound` (front_door), `mobile-channel` (front_door), `partner-api` (front_door), `webhook-inbound` (front_door) |
| `container-platform` | Azure Kubernetes Service (`TS-AZURE-AKS`) | `api-outbound` (platform), `webhook-inbound` (platform) |
| `customer-identity` | Microsoft Entra External ID (`TS-AZURE-EXTERNAL-ID`) | `customer-sign-in` (ciam) |
| `dns` | Azure Private DNS Resolver (`TS-AZURE-PRIVATE-DNS`) | `workload-network` (dns) |
| `document-ai` | Azure AI Document Intelligence (`TS-AZURE-DOC-INTELLIGENCE`) | `document-intake` (reader) |
| `enterprise-search` | Azure AI Search (`TS-AZURE-AI-SEARCH`) — a `vector-database` that answers for it | — |
| `event-stream` | Azure Event Hubs (`TS-AZURE-EVENTHUBS`) | `async-worker` (stream) |
| `foundation-model-service` | Microsoft Foundry (`TS-AZURE-FOUNDRY`) | `agent-service` (models), `ml-inference-service` (models), `retrieval-index` (models) |
| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`), shared | `admin-console` (idp), `assistant-chat` (idp), `identity-hub` (idp), `sso-federation` (idp) |
| `kms` | Azure Key Vault (`TS-AZURE-KEYVAULT`) — a `secrets-manager` that answers for it | `byok-encryption` (kms) |
| `message-queue` | Azure Service Bus (`TS-AZURE-SERVICEBUS`) | `event-consumer` (bus), `event-hub` (bus), `event-publisher` (bus), `notification-service` (bus) |
| `object-store` | Azure Blob Storage (`TS-AZURE-BLOB`) | — |
| `observability` | Azure Monitor (`TS-AZURE-MONITOR`) | `vendor-monitoring` (observability) |
| `private-egress` | Azure Private Link (`TS-AZURE-PRIVATELINK`) | `private-egress` (private_link) |
| `relational-db` | Azure SQL Database (`TS-AZURE-SQL`) | — |
| `secrets-manager` | Azure Key Vault (`TS-AZURE-KEYVAULT`) | `partner-adapter` (secrets), `secrets-management` (vault) |
| `transit-gateway` | Azure Virtual WAN hub (`TS-AZURE-VWAN`) | `private-egress` (transit), `workload-network` (transit) |
| `vector-database` | Azure AI Search (`TS-AZURE-AI-SEARCH`) | `retrieval-index` (vectors) |

<a id="gcp"></a>
## GCP

**Shapes.** `batch-data-product-gcp`, `gcp-digital-product`, `gcp-workload-network`, `vendor-saas-service-gcp`.

| Kind | Service | Asked for by |
|---|---|---|
| `agent-platform` | Gemini Enterprise Agent Platform (`TS-GCP-GEMINI-PLATFORM`) — a `foundation-model-service` that answers for it | `agent-service` (platform) |
| `ai-gateway` | Model Armor (`TS-GCP-MODEL-ARMOR`) | `agent-service` (gateway), `ml-inference-service` (gateway) |
| `api-gateway` | Apigee (`TS-GCP-APIGEE`) | `api-outbound` (front_door), `mobile-channel` (front_door), `partner-api` (front_door), `webhook-inbound` (front_door) |
| `backup` | Backup and DR Service (`TS-GCP-BACKUP-DR`) | — |
| `bi` | Looker (`TS-GCP-LOOKER`) | — |
| `cache` | Memorystore for Redis (`TS-GCP-MEMORYSTORE`) | — |
| `cdn` | Cloud CDN (`TS-GCP-CLOUD-CDN`) | — |
| `container-platform` | Google Kubernetes Engine (`TS-GCP-GKE`) | `api-outbound` (platform), `webhook-inbound` (platform) |
| `customer-identity` | Identity Platform (`TS-GCP-IDENTITY-PLATFORM`) | `customer-sign-in` (ciam) |
| `dns` | Cloud DNS (`TS-GCP-CLOUD-DNS`) | `workload-network` (dns) |
| `document-ai` | Document AI (`TS-GCP-DOCUMENT-AI`) | `document-intake` (reader) |
| `etl` | Dataflow (`TS-GCP-DATAFLOW`) | — |
| `event-stream` | Managed Service for Apache Kafka (`TS-GCP-MANAGED-KAFKA`) | `async-worker` (stream) |
| `foundation-model-service` | Gemini Enterprise Agent Platform (`TS-GCP-GEMINI-PLATFORM`) | `agent-service` (models), `ml-inference-service` (models), `retrieval-index` (models) |
| `hybrid-link` | Cloud Interconnect (`TS-GCP-INTERCONNECT`), HA VPN (`TS-GCPNET-HA-VPN`) — ambiguous | — |
| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`), shared | `admin-console` (idp), `assistant-chat` (idp), `identity-hub` (idp), `sso-federation` (idp) |
| `kms` | Cloud KMS (`TS-GCP-KMS`) | `byok-encryption` (kms) |
| `load-balancer` | Cloud Load Balancing (`TS-GCP-CLOUD-LB`) | — |
| `message-queue` | Pub/Sub (`TS-GCP-PUBSUB`) | `event-consumer` (bus), `event-hub` (bus), `event-publisher` (bus), `notification-service` (bus) |
| `object-store` | Cloud Storage (`TS-GCP-GCS`) | — |
| `observability` | Cloud Monitoring (`TS-GCP-MONITORING`) | `vendor-monitoring` (observability) |
| `private-egress` | Private Service Connect (`TS-GCP-PSC`) | `private-egress` (private_link) |
| `relational-db` | Cloud SQL for PostgreSQL (`TS-GCP-CLOUD-SQL`) | — |
| `secrets-manager` | Secret Manager (`TS-GCP-SECRET-MANAGER`) | `partner-adapter` (secrets), `secrets-management` (vault) |
| `transit-gateway` | Network Connectivity Center (`TS-GCP-NCC`) | `private-egress` (transit), `workload-network` (transit) |
| `vector-database` | Vector Search (`TS-GCP-VECTOR-SEARCH`) | `retrieval-index` (vectors) |
| `vpc` | Shared VPC network (`TS-GCP-SHARED-VPC`) | — |
| `waf` | Cloud Armor (`TS-GCP-CLOUD-ARMOR`) | — |
| `warehouse` | BigQuery (`TS-GCP-BIGQUERY`) | — |
| `workflow` | Cloud Composer (`TS-GCP-COMPOSER`) | — |

<a id="shared"></a>
## Shared

Services with no provider of their own, answering for any landing zone that has none of their kind.

| Kind | Service | Asked for by |
|---|---|---|
| `catalog` | Collibra (`TS-COLLIBRA`) | — |
| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`) | `admin-console` (idp), `assistant-chat` (idp), `identity-hub` (idp), `sso-federation` (idp) |
| `itsm` | ServiceNow (`TS-SERVICENOW`) | — |
| `warehouse` | Snowflake (`TS-SNOWFLAKE`) | — |
