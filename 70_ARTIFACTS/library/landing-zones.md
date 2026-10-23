# Landing zones

A landing zone is what a provider already runs for whatever lands on it: one shared service of each kind, tagged `landing-zone`, found by kind when a part asks. Nothing about it is written on a shape; a shape says its provider and the parts resolve. Measured here against the providers the shapes land on, with the kinds the parts name that each cannot answer -- where the next onboarding would stop. Generated from `10_MODEL/tech_services/`, `28_MODULES/` and `20_ARCHETYPES/` by `terrane render`; edit those, not this.

| Provider | Shapes | Products | Kinds | Asked for and missing |
|---|---|---:|---:|---|
| [AWS](#aws) | `aws-product-onboarding`, `saas-onboarding` | 2 | 18 | — |
| [Azure](#azure) | `azure-digital-product`, `core-platform-service`, `vendor-saas-service` | 6 | 11 | — |
| [GCP](#gcp) | `batch-data-product-gcp`, `gcp-digital-product`, `vendor-saas-service-gcp` | 3 | 24 | — |

<a id="aws"></a>
## AWS

**Shapes.** `aws-product-onboarding`, `saas-onboarding`.

| Kind | Service | Asked for by |
|---|---|---|
| `api-gateway` | Amazon API Gateway (`TS-AWS-APIGW`) | `api-outbound` (front_door), `mobile-channel` (front_door), `webhook-inbound` (front_door) |
| `cdn` | Amazon CloudFront and WAF (`TS-AWS-CLOUDFRONT`) | — |
| `container-platform` | Amazon EKS (`TS-AWS-EKS`) | `api-outbound` (platform), `webhook-inbound` (platform) |
| `dns` | Route 53 Resolver (`TS-NET-ROUTE53`) | — |
| `event-stream` | Amazon MSK (`TS-AWS-MSK`) | `async-worker` (stream) |
| `foundation-model-service` | Amazon Bedrock (`TS-AWS-BEDROCK`) | `ml-inference-service` (models) |
| `hybrid-link` | Direct Connect (`TS-NET-DX`), Site-to-Site VPN (`TS-NET-VPN`) — ambiguous | — |
| `iac` | AWS Organizations (`TS-AWS-ORG`) | — |
| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`), shared | `admin-console` (idp), `identity-hub` (idp), `sso-federation` (idp) |
| `kms` | AWS KMS (`TS-AWS-KMS`) | `byok-encryption` (kms) |
| `load-balancer` | Application Load Balancer (`TS-AWS-ALB`) | — |
| `message-queue` | Amazon SQS (`TS-AWS-SQS`) | `event-consumer` (bus), `event-hub` (bus), `event-publisher` (bus), `notification-service` (bus) |
| `object-store` | Amazon S3 (`TS-AWS-S3`) | — |
| `observability` | Amazon CloudWatch (`TS-AWS-CLOUDWATCH`) | `vendor-monitoring` (observability) |
| `private-egress` | AWS PrivateLink (`TS-AWS-PRIVATELINK`) | `private-egress` (private_link) |
| `relational-db` | Amazon RDS for PostgreSQL (`TS-AWS-RDS`) | — |
| `secrets-manager` | AWS Secrets Manager (`TS-AWS-SECRETS`) | `partner-adapter` (secrets), `secrets-management` (vault) |
| `transit-gateway` | AWS Transit Gateway (`TS-AWS-TGW`) | `private-egress` (transit) |
| `vpc` | Shared Services VPC (`TS-NET-VPC-SHARED`) | — |

<a id="azure"></a>
## Azure

**Shapes.** `azure-digital-product`, `core-platform-service`, `vendor-saas-service`.

| Kind | Service | Asked for by |
|---|---|---|
| `api-gateway` | Azure API Management (`TS-AZURE-APIM`) | `api-outbound` (front_door), `mobile-channel` (front_door), `webhook-inbound` (front_door) |
| `container-platform` | Azure Kubernetes Service (`TS-AZURE-AKS`) | `api-outbound` (platform), `webhook-inbound` (platform) |
| `event-stream` | Azure Event Hubs (`TS-AZURE-EVENTHUBS`) | `async-worker` (stream) |
| `foundation-model-service` | Microsoft Foundry (`TS-AZURE-FOUNDRY`) | `ml-inference-service` (models) |
| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`), shared | `admin-console` (idp), `identity-hub` (idp), `sso-federation` (idp) |
| `kms` | Azure Key Vault (`TS-AZURE-KEYVAULT`) — a `secrets-manager` that answers for it | `byok-encryption` (kms) |
| `message-queue` | Azure Service Bus (`TS-AZURE-SERVICEBUS`) | `event-consumer` (bus), `event-hub` (bus), `event-publisher` (bus), `notification-service` (bus) |
| `observability` | Azure Monitor (`TS-AZURE-MONITOR`) | `vendor-monitoring` (observability) |
| `private-egress` | Azure Private Link (`TS-AZURE-PRIVATELINK`) | `private-egress` (private_link) |
| `relational-db` | Azure SQL Database (`TS-AZURE-SQL`) | — |
| `secrets-manager` | Azure Key Vault (`TS-AZURE-KEYVAULT`) | `partner-adapter` (secrets), `secrets-management` (vault) |
| `transit-gateway` | Azure Virtual WAN hub (`TS-AZURE-VWAN`) | `private-egress` (transit) |

<a id="gcp"></a>
## GCP

**Shapes.** `batch-data-product-gcp`, `gcp-digital-product`, `vendor-saas-service-gcp`.

| Kind | Service | Asked for by |
|---|---|---|
| `api-gateway` | Apigee (`TS-GCP-APIGEE`) | `api-outbound` (front_door), `mobile-channel` (front_door), `webhook-inbound` (front_door) |
| `backup` | Backup and DR Service (`TS-GCP-BACKUP-DR`) | — |
| `bi` | Looker (`TS-GCP-LOOKER`) | — |
| `cache` | Memorystore for Redis (`TS-GCP-MEMORYSTORE`) | — |
| `cdn` | Cloud CDN (`TS-GCP-CLOUD-CDN`) | — |
| `container-platform` | Google Kubernetes Engine (`TS-GCP-GKE`) | `api-outbound` (platform), `webhook-inbound` (platform) |
| `dns` | Cloud DNS (`TS-GCP-CLOUD-DNS`) | — |
| `etl` | Dataflow (`TS-GCP-DATAFLOW`) | — |
| `event-stream` | Managed Service for Apache Kafka (`TS-GCP-MANAGED-KAFKA`) | `async-worker` (stream) |
| `foundation-model-service` | Gemini Enterprise Agent Platform (`TS-GCP-GEMINI-PLATFORM`) | `ml-inference-service` (models) |
| `hybrid-link` | Cloud Interconnect (`TS-GCP-INTERCONNECT`), HA VPN (`TS-GCPNET-HA-VPN`) — ambiguous | — |
| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`), shared | `admin-console` (idp), `identity-hub` (idp), `sso-federation` (idp) |
| `kms` | Cloud KMS (`TS-GCP-KMS`) | `byok-encryption` (kms) |
| `load-balancer` | Cloud Load Balancing (`TS-GCP-CLOUD-LB`) | — |
| `message-queue` | Pub/Sub (`TS-GCP-PUBSUB`) | `event-consumer` (bus), `event-hub` (bus), `event-publisher` (bus), `notification-service` (bus) |
| `object-store` | Cloud Storage (`TS-GCP-GCS`) | — |
| `observability` | Cloud Monitoring (`TS-GCP-MONITORING`) | `vendor-monitoring` (observability) |
| `private-egress` | Private Service Connect (`TS-GCP-PSC`) | `private-egress` (private_link) |
| `relational-db` | Cloud SQL for PostgreSQL (`TS-GCP-CLOUD-SQL`) | — |
| `secrets-manager` | Secret Manager (`TS-GCP-SECRET-MANAGER`) | `partner-adapter` (secrets), `secrets-management` (vault) |
| `transit-gateway` | Network Connectivity Center (`TS-GCP-NCC`) | `private-egress` (transit) |
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
| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`) | `admin-console` (idp), `identity-hub` (idp), `sso-federation` (idp) |
| `itsm` | ServiceNow (`TS-SERVICENOW`) | — |
| `warehouse` | Snowflake (`TS-SNOWFLAKE`) | — |
