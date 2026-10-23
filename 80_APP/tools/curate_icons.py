"""Curate the marks the app ships.

Usage:

    python 80_APP/tools/curate_icons.py --source <dir> [--colors simple-icons.json]

`<dir>` holds the official packages unpacked side by side: `aws/` (the AWS
Architecture Icons release), `azure/` (the Azure Public Service Icons),
`gcp-core/` and `gcp-category/` (the Google Cloud product and category sets),
and `brands/` (the Simple Icons SVGs named below). The tool copies the subset
the component library's kinds need into `80_APP/web/icons/`, writes
`map.json` (which file a word or a kind of component points at) and
`CREDITS.md` (whose each mark is, on what terms), and gives each vendor mark
the brand color Simple Icons records for it, since those files carry no fill
and would draw black. The provider icons are copied unmodified.

The packages are the providers' to distribute, so they are not in this
repository; the sources are named in CREDITS.md.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve()
OUT = HERE.parents[1] / "web" / "icons"

#: The ink the house glyphs use, for a mark whose brand color is not known.
INK = "#3f4a5c"

AWS_RELEASE = "07312026"


def find(root: pathlib.Path, *patterns: str) -> pathlib.Path:
    """The first file under root matching the first pattern that matches
    anything; patterns are tried in order so the plainest name wins."""
    for pattern in patterns:
        hits = sorted(p for p in root.rglob(pattern) if "__MACOSX" not in str(p))
        if hits:
            return hits[0]
    raise SystemExit("no file for %s under %s" % (patterns, root))


def picks(source: pathlib.Path):
    aws_svc = source / "aws" / ("Architecture-Service-Icons_%s" % AWS_RELEASE)
    aws_res = source / "aws" / ("Resource-Icons_%s" % AWS_RELEASE)
    aws_grp = source / "aws" / ("Architecture-Group-Icons_%s" % AWS_RELEASE)
    az = source / "azure" / "Azure_Public_Service_Icons" / "Icons"
    core = source / "gcp-core"
    cat = source / "gcp-category"
    aws = {
        "eks": find(aws_svc, "Arch_Amazon-Elastic-Kubernetes-Service_48.svg"),
        "api-gateway": find(aws_svc, "Arch_Amazon-API-Gateway_48.svg"),
        "cloudfront": find(aws_svc, "Arch_Amazon-CloudFront_48.svg"),
        "waf": find(aws_svc, "Arch_AWS-WAF_48.svg"),
        "cloudwatch": find(aws_svc, "Arch_Amazon-CloudWatch_48.svg"),
        "msk": find(aws_svc, "Arch_Amazon-Managed-Streaming-for-Apache-Kafka_48.svg"),
        "rds": find(aws_svc, "Arch_Amazon-RDS_48.svg"),
        "aurora": find(aws_svc, "Arch_Amazon-Aurora_48.svg"),
        "s3": find(aws_svc, "Arch_Amazon-Simple-Storage-Service_48.svg"),
        "sqs": find(aws_svc, "Arch_Amazon-Simple-Queue-Service_48.svg"),
        "sns": find(aws_svc, "Arch_Amazon-Simple-Notification-Service_48.svg"),
        "elb": find(aws_svc, "Arch_Elastic-Load-Balancing_48.svg"),
        "direct-connect": find(aws_svc, "Arch_AWS-Direct-Connect_48.svg"),
        "site-to-site-vpn": find(aws_svc, "Arch_AWS-Site-to-Site-VPN_48.svg"),
        "privatelink": find(aws_svc, "Arch_AWS-PrivateLink_48.svg"),
        "transit-gateway": find(aws_svc, "Arch_AWS-Transit-Gateway_48.svg"),
        "kms": find(aws_svc, "Arch_AWS-Key-Management-Service_48.svg"),
        "secrets-manager": find(aws_svc, "Arch_AWS-Secrets-Manager_48.svg"),
        "organizations": find(aws_svc, "Arch_AWS-Organizations_48.svg"),
        "backup": find(aws_svc, "Arch_AWS-Backup_48.svg"),
        "elasticache": find(aws_svc, "Arch_Amazon-ElastiCache_48.svg"),
        "route53": find(aws_svc, "Arch_Amazon-Route-53_48.svg"),
        "vpc": find(aws_svc, "Arch_Amazon-Virtual-Private-Cloud_48.svg"),
        "cloudformation": find(aws_svc, "Arch_AWS-CloudFormation_48.svg"),
        "iam-identity-center": find(aws_svc, "Arch_AWS-IAM-Identity-Center_48.svg"),
        "iam": find(aws_svc, "Arch_AWS-Identity-and-Access-Management_48.svg"),
        "redshift": find(aws_svc, "Arch_Amazon-Redshift_48.svg"),
        "glue": find(aws_svc, "Arch_AWS-Glue_48.svg"),
        "lambda": find(aws_svc, "Arch_AWS-Lambda_48.svg"),
        "dynamodb": find(aws_svc, "Arch_Amazon-DynamoDB_48.svg"),
        "ecs": find(aws_svc, "Arch_Amazon-Elastic-Container-Service_48.svg"),
        "fargate": find(aws_svc, "Arch_AWS-Fargate_48.svg"),
        "kinesis": find(aws_svc, "Arch_Amazon-Kinesis_48.svg"),
        "eventbridge": find(aws_svc, "Arch_Amazon-EventBridge_48.svg"),
        "step-functions": find(aws_svc, "Arch_AWS-Step-Functions_48.svg"),
        "cognito": find(aws_svc, "Arch_Amazon-Cognito_48.svg"),
        "shield": find(aws_svc, "Arch_AWS-Shield_48.svg"),
        "guardduty": find(aws_svc, "Arch_Amazon-GuardDuty_48.svg"),
        "security-hub": find(aws_svc, "Arch_AWS-Security-Hub_48.svg"),
        "cloudtrail": find(aws_svc, "Arch_AWS-CloudTrail_48.svg"),
        "ec2": find(aws_svc, "Arch_Amazon-EC2_48.svg"),
        "opensearch": find(aws_svc, "Arch_Amazon-OpenSearch-Service_48.svg"),
        "sagemaker": find(aws_svc, "Arch_Amazon-SageMaker_48.svg"),
        "bedrock": find(aws_svc, "Arch_Amazon-Bedrock_48.svg"),
        "athena": find(aws_svc, "Arch_Amazon-Athena_48.svg"),
        "lake-formation": find(aws_svc, "Arch_AWS-Lake-Formation_48.svg"),
        "emr": find(aws_svc, "Arch_Amazon-EMR_48.svg"),
        "systems-manager": find(aws_svc, "Arch_AWS-Systems-Manager_48.svg"),
        "config": find(aws_svc, "Arch_AWS-Config_48.svg"),
        "control-tower": find(aws_svc, "Arch_AWS-Control-Tower_48.svg"),
        "network-firewall": find(aws_svc, "Arch_AWS-Network-Firewall_48.svg"),
        "acm": find(aws_svc, "Arch_AWS-Certificate-Manager_48.svg"),
        "mq": find(aws_svc, "Arch_Amazon-MQ_48.svg"),
        "documentdb": find(aws_svc, "Arch_Amazon-DocumentDB_48.svg"),
        "internet-gateway": find(aws_res, "Res_Amazon-VPC_Internet-Gateway_48.svg"),
        "nat-gateway": find(aws_res, "Res_Amazon-VPC_NAT-Gateway_48.svg"),
        "vpc-endpoints": find(aws_res, "Res_Amazon-VPC_Endpoints_48.svg"),
        "public-subnet": find(aws_grp, "Public-subnet_32.svg"),
        "private-subnet": find(aws_grp, "Private-subnet_32.svg"),
        # The group icons AWS publishes for its containers, drawn on the
        # boundaries that are those things.
        "group-cloud": find(aws_grp, "AWS-Cloud_32.svg"),
        "group-account": find(aws_grp, "AWS-Account_32.svg"),
        "group-region": find(aws_grp, "Region_32.svg"),
        "group-data-center": find(aws_grp, "Corporate-data-center_32.svg"),
        "data-center": find(aws_grp, "Corporate-data-center_32.svg"),
    }
    azure = {
        "aks": find(az, "*-icon-service-Kubernetes-Services.svg"),
        "subscriptions": find(az, "*-icon-service-Subscriptions.svg"),
        "apim": find(az, "*-icon-service-API-Management-Services.svg"),
        "event-hubs": find(az, "*-icon-service-Event-Hubs.svg"),
        "key-vault": find(az, "*-icon-service-Key-Vaults.svg"),
        "monitor": find(az, "00001-icon-service-Monitor.svg"),
        "log-analytics": find(az, "*-icon-service-Log-Analytics-Workspaces.svg"),
        "app-insights": find(az, "*-icon-service-Application-Insights.svg"),
        "private-link": find(az, "00427-icon-service-Private-Link.svg"),
        "sql-database": find(az, "10130-icon-service-SQL-Database.svg"),
        "azure-sql": find(az, "*-icon-service-Azure-SQL.svg"),
        "service-bus": find(az, "*-icon-service-Azure-Service-Bus.svg"),
        "virtual-wan": find(az, "*-icon-service-Virtual-WANs.svg"),
        "backup": find(az, "*-icon-service-Azure-Backup-Center.svg"),
        "cache-redis": find(az, "*-icon-service-Cache-Redis.svg"),
        "dns-zones": find(az, "*-icon-service-DNS-Zones.svg"),
        "waf": find(az, "*-icon-service-Web-Application-Firewall-Policies(WAF).svg"),
        "front-door": find(az, "*-icon-service-Front-Door-and-CDN-Profiles.svg"),
        "entra-id": find(az, "*-icon-service-Microsoft-Entra-ID.svg", "*-icon-service-Entra-ID.svg",
                         "*-icon-service-Entra-Identity.svg", "*-icon-service-Entra-ID-Protection.svg"),
        "sentinel": find(az, "*-icon-service-Azure-Sentinel.svg"),
        "virtual-network": find(az, "10061-icon-service-Virtual-Networks.svg"),
        "subnet": find(az, "*-icon-service-Subnet.svg"),
        "load-balancer": find(az, "10062-icon-service-Load-Balancers.svg"),
        "application-gateway": find(az, "10076-icon-service-Application-Gateways.svg"),
        "storage-account": find(az, "10086-icon-service-Storage-Accounts.svg"),
        "container-apps": find(az, "*-icon-service-Container-Apps-Environments.svg"),
        "functions": find(az, "*-icon-service-Function-Apps.svg"),
        "cosmos-db": find(az, "*-icon-service-Azure-Cosmos-DB.svg"),
        "data-factory": find(az, "*-icon-service-Data-Factories.svg"),
        "synapse": find(az, "*-icon-service-Azure-Synapse-Analytics.svg"),
        "databricks": find(az, "*-icon-service-Azure-Databricks.svg"),
        "firewall": find(az, "10084-icon-service-Firewalls.svg"),
        "expressroute": find(az, "*-icon-service-ExpressRoute-Circuits.svg"),
        "vnet-gateway": find(az, "*-icon-service-Virtual-Network-Gateways.svg"),
        "vm": find(az, "10021-icon-service-Virtual-Machine.svg"),
        "app-service": find(az, "10035-icon-service-App-Services.svg"),
        "logic-apps": find(az, "02631-icon-service-Logic-Apps.svg"),
        "event-grid": find(az, "*-icon-service-Event-Grid-Topics.svg"),
        "machine-learning": find(az, "10166-icon-service-Machine-Learning.svg"),
        "openai": find(az, "*-icon-service-Azure-OpenAI.svg"),
        "ai-services": find(az, "10162-icon-service-Cognitive-Services.svg"),
        "managed-identity": find(az, "10227-icon-service-Managed-Identities.svg"),
        "bastion": find(az, "*-icon-service-Bastions.svg"),
        "nat": find(az, "10310-icon-service-NAT.svg"),
        "traffic-manager": find(az, "*-icon-service-Traffic-Manager-Profiles.svg"),
        "cdn": find(az, "00056-icon-service-CDN-Profiles.svg"),
        "container-registry": find(az, "*-icon-service-Container-Registries.svg"),
        "devops": find(az, "*-icon-service-Azure-DevOps.svg"),
        "postgresql": find(az, "10131-icon-service-Azure-Database-PostgreSQL-Server.svg"),
        "mysql": find(az, "*-icon-service-Azure-Database-MySQL-Server.svg"),
        "storage-queue": find(az, "*-icon-service-Storage-Queue.svg"),
        "static-apps": find(az, "*-icon-service-Static-Apps.svg"),
        "subscriptions": find(az, "10002-icon-service-Subscriptions.svg"),
        "resource-groups": find(az, "10007-icon-service-Resource-Groups.svg"),
        "management-groups": find(az, "*-icon-service-Management-Groups.svg"),
        "arc": find(az, "*-icon-service-Azure-Arc.svg"),
    }
    gcp = {
        "gke": find(core, "GKE-*.svg"),
        "cloud-run": find(core, "CloudRun-*.svg"),
        "cloud-sql": find(core, "CloudSQL-*.svg"),
        "spanner": find(core, "CloudSpanner-*.svg"),
        "alloydb": find(core, "AlloyDB-*.svg"),
        "cloud-storage": find(core, "Cloud_Storage-*.svg"),
        "bigquery": find(core, "BigQuery-*.svg"),
        "apigee": find(core, "Apigee-*.svg"),
        "compute-engine": find(core, "ComputeEngine-*.svg"),
        "vertex-ai": find(core, "VertexAI-*.svg"),
        "looker": find(core, "Looker-*.svg"),
        "security-command-center": find(core, "SecurityCommandCenter-*.svg"),
        "anthos": find(core, "Anthos-*.svg"),
        "cat-networking": find(cat, "Networking-*.svg"),
        "cat-observability": find(cat, "Observability-*.svg"),
        "cat-security": find(cat, "SecurityIdentity-*.svg"),
        "cat-integration": find(cat, "IntegrationServices-*.svg"),
        "cat-databases": find(cat, "Databases-*.svg"),
        "cat-storage": find(cat, "Storage-*.svg"),
        "cat-management": find(cat, "ManagementTools-*.svg"),
        "cat-data-analytics": find(cat, "DataAnalytics-*.svg"),
        "cat-containers": find(cat, "Containers-*.svg"),
        "cat-compute": find(cat, "Compute-*.svg"),
        "cat-devops": find(cat, "DevOps-*.svg"),
    }
    return aws, azure, gcp


MAP = {
    "providers": {
        "AWS": {
            "names": {
                "eks": "aws/eks.svg", "elastic kubernetes": "aws/eks.svg", "api gateway": "aws/api-gateway.svg",
                "cloudfront": "aws/cloudfront.svg", "waf": "aws/waf.svg", "cloudwatch": "aws/cloudwatch.svg",
                "msk": "aws/msk.svg", "managed streaming": "aws/msk.svg", "kafka": "aws/msk.svg",
                "rds": "aws/rds.svg", "aurora": "aws/aurora.svg", "s3": "aws/s3.svg", "simple storage": "aws/s3.svg",
                "sqs": "aws/sqs.svg", "simple queue": "aws/sqs.svg", "sns": "aws/sns.svg",
                "alb": "aws/elb.svg", "elb": "aws/elb.svg", "load balancer": "aws/elb.svg", "load balancing": "aws/elb.svg",
                "direct connect": "aws/direct-connect.svg", "vpn": "aws/site-to-site-vpn.svg",
                "privatelink": "aws/privatelink.svg", "private link": "aws/privatelink.svg",
                "transit gateway": "aws/transit-gateway.svg", "kms": "aws/kms.svg", "key management": "aws/kms.svg",
                "secrets manager": "aws/secrets-manager.svg", "organizations": "aws/organizations.svg",
                "backup": "aws/backup.svg", "elasticache": "aws/elasticache.svg", "route 53": "aws/route53.svg",
                "route53": "aws/route53.svg", "vpc": "aws/vpc.svg", "virtual private cloud": "aws/vpc.svg",
                "cloudformation": "aws/cloudformation.svg", "iam identity center": "aws/iam-identity-center.svg",
                "iam": "aws/iam.svg", "redshift": "aws/redshift.svg", "glue": "aws/glue.svg", "lambda": "aws/lambda.svg",
                "dynamodb": "aws/dynamodb.svg", "ecs": "aws/ecs.svg", "fargate": "aws/fargate.svg",
                "kinesis": "aws/kinesis.svg", "eventbridge": "aws/eventbridge.svg", "step functions": "aws/step-functions.svg",
                "cognito": "aws/cognito.svg", "shield": "aws/shield.svg", "guardduty": "aws/guardduty.svg",
                "security hub": "aws/security-hub.svg", "cloudtrail": "aws/cloudtrail.svg", "ec2": "aws/ec2.svg",
                "opensearch": "aws/opensearch.svg", "sagemaker": "aws/sagemaker.svg", "bedrock": "aws/bedrock.svg",
                "athena": "aws/athena.svg", "lake formation": "aws/lake-formation.svg", "emr": "aws/emr.svg",
                "systems manager": "aws/systems-manager.svg", "config": "aws/config.svg",
                "control tower": "aws/control-tower.svg", "network firewall": "aws/network-firewall.svg",
                "certificate manager": "aws/acm.svg", "amazon mq": "aws/mq.svg", "documentdb": "aws/documentdb.svg",
                "internet gateway": "aws/internet-gateway.svg", "nat gateway": "aws/nat-gateway.svg",
                "vpc endpoint": "aws/vpc-endpoints.svg", "public subnet": "aws/public-subnet.svg",
                "subnet": "aws/private-subnet.svg", "data center": "aws/data-center.svg",
            },
            "kinds": {
                "container-platform": "aws/eks.svg", "api-gateway": "aws/api-gateway.svg", "cdn": "aws/cloudfront.svg",
                "waf": "aws/waf.svg", "observability": "aws/cloudwatch.svg", "event-stream": "aws/msk.svg",
                "relational-db": "aws/rds.svg", "object-store": "aws/s3.svg", "message-queue": "aws/sqs.svg",
                "load-balancer": "aws/elb.svg", "hybrid-link": "aws/direct-connect.svg", "private-egress": "aws/privatelink.svg",
                "transit-gateway": "aws/transit-gateway.svg", "kms": "aws/kms.svg", "secrets-manager": "aws/secrets-manager.svg",
                "iac": "aws/cloudformation.svg", "backup": "aws/backup.svg", "cache": "aws/elasticache.svg",
                "dns": "aws/route53.svg", "vpc": "aws/vpc.svg", "subnet": "aws/private-subnet.svg",
                "identity-provider": "aws/iam-identity-center.svg", "warehouse": "aws/redshift.svg", "catalog": "aws/glue.svg",
                "function": "aws/lambda.svg", "serverless": "aws/lambda.svg", "nosql": "aws/dynamodb.svg",
                "document-db": "aws/documentdb.svg", "search": "aws/opensearch.svg", "ml-platform": "aws/sagemaker.svg",
                "siem": "aws/security-hub.svg", "firewall": "aws/network-firewall.svg", "certificate": "aws/acm.svg",
                "compute": "aws/ec2.svg", "vm": "aws/ec2.svg",
            },
        },
        "Azure": {
            "names": {
                "aks": "azure/aks.svg", "kubernetes": "azure/aks.svg", "api management": "azure/apim.svg", "apim": "azure/apim.svg",
                "event hubs": "azure/event-hubs.svg", "event hub": "azure/event-hubs.svg", "key vault": "azure/key-vault.svg",
                "monitor": "azure/monitor.svg", "log analytics": "azure/log-analytics.svg",
                "application insights": "azure/app-insights.svg", "private link": "azure/private-link.svg",
                "sql database": "azure/sql-database.svg", "azure sql": "azure/azure-sql.svg", "service bus": "azure/service-bus.svg",
                "virtual wan": "azure/virtual-wan.svg", "backup": "azure/backup.svg", "redis": "azure/cache-redis.svg",
                "dns": "azure/dns-zones.svg", "web application firewall": "azure/waf.svg", "waf": "azure/waf.svg",
                "front door": "azure/front-door.svg", "entra": "azure/entra-id.svg", "sentinel": "azure/sentinel.svg",
                "virtual network": "azure/virtual-network.svg", "vnet": "azure/virtual-network.svg", "subnet": "azure/subnet.svg",
                "load balancer": "azure/load-balancer.svg", "application gateway": "azure/application-gateway.svg",
                "storage account": "azure/storage-account.svg", "blob": "azure/storage-account.svg",
                "container apps": "azure/container-apps.svg", "functions": "azure/functions.svg", "function app": "azure/functions.svg",
                "cosmos": "azure/cosmos-db.svg", "data factory": "azure/data-factory.svg", "synapse": "azure/synapse.svg",
                "databricks": "azure/databricks.svg", "firewall": "azure/firewall.svg", "expressroute": "azure/expressroute.svg",
                "vpn gateway": "azure/vnet-gateway.svg", "virtual network gateway": "azure/vnet-gateway.svg",
                "virtual machine": "azure/vm.svg", "app service": "azure/app-service.svg", "logic apps": "azure/logic-apps.svg",
                "event grid": "azure/event-grid.svg", "machine learning": "azure/machine-learning.svg", "openai": "azure/openai.svg",
                "ai services": "azure/ai-services.svg", "cognitive": "azure/ai-services.svg",
                "managed identity": "azure/managed-identity.svg", "managed identities": "azure/managed-identity.svg",
                "bastion": "azure/bastion.svg", "nat gateway": "azure/nat.svg", "traffic manager": "azure/traffic-manager.svg",
                "cdn": "azure/cdn.svg", "container registry": "azure/container-registry.svg", "acr": "azure/container-registry.svg",
                "devops": "azure/devops.svg", "postgresql": "azure/postgresql.svg", "mysql": "azure/mysql.svg",
                "storage queue": "azure/storage-queue.svg", "static web": "azure/static-apps.svg",
                "subscription": "azure/subscriptions.svg", "resource group": "azure/resource-groups.svg",
                "management group": "azure/management-groups.svg", "arc": "azure/arc.svg",
            },
            "kinds": {
                "container-platform": "azure/aks.svg", "api-gateway": "azure/apim.svg", "event-stream": "azure/event-hubs.svg",
                "secrets-manager": "azure/key-vault.svg", "kms": "azure/key-vault.svg", "observability": "azure/monitor.svg",
                "private-egress": "azure/private-link.svg", "relational-db": "azure/sql-database.svg",
                "message-queue": "azure/service-bus.svg", "transit-gateway": "azure/virtual-wan.svg", "backup": "azure/backup.svg",
                "cache": "azure/cache-redis.svg", "dns": "azure/dns-zones.svg", "waf": "azure/waf.svg", "cdn": "azure/front-door.svg",
                "identity-provider": "azure/entra-id.svg", "siem": "azure/sentinel.svg", "vpc": "azure/virtual-network.svg",
                "subnet": "azure/subnet.svg", "load-balancer": "azure/load-balancer.svg", "object-store": "azure/storage-account.svg",
                "warehouse": "azure/synapse.svg", "hybrid-link": "azure/expressroute.svg", "function": "azure/functions.svg",
                "serverless": "azure/functions.svg", "nosql": "azure/cosmos-db.svg", "document-db": "azure/cosmos-db.svg",
                "firewall": "azure/firewall.svg", "compute": "azure/vm.svg", "vm": "azure/vm.svg",
                "ml-platform": "azure/machine-learning.svg", "iac": "azure/resource-groups.svg",
                "container-registry": "azure/container-registry.svg", "etl": "azure/data-factory.svg",
            },
        },
        "GCP": {
            "names": {
                "gke": "gcp/gke.svg", "kubernetes": "gcp/gke.svg", "cloud run": "gcp/cloud-run.svg", "cloud sql": "gcp/cloud-sql.svg",
                "spanner": "gcp/spanner.svg", "alloydb": "gcp/alloydb.svg", "cloud storage": "gcp/cloud-storage.svg",
                "gcs": "gcp/cloud-storage.svg", "bigquery": "gcp/bigquery.svg", "apigee": "gcp/apigee.svg",
                "compute engine": "gcp/compute-engine.svg", "gce": "gcp/compute-engine.svg", "vertex": "gcp/vertex-ai.svg",
                "looker": "gcp/looker.svg", "dataflow": "gcp/cat-data-analytics.svg",
                "cloud composer": "gcp/cat-data-analytics.svg", "security command center": "gcp/security-command-center.svg", "anthos": "gcp/anthos.svg",
            },
            "kinds": {
                "container-platform": "gcp/gke.svg", "relational-db": "gcp/cloud-sql.svg", "object-store": "gcp/cloud-storage.svg",
                "warehouse": "gcp/bigquery.svg", "api-gateway": "gcp/apigee.svg", "serverless": "gcp/cloud-run.svg",
                "function": "gcp/cloud-run.svg", "compute": "gcp/compute-engine.svg", "vm": "gcp/compute-engine.svg",
                "ml-platform": "gcp/vertex-ai.svg", "siem": "gcp/security-command-center.svg",
                "dns": "gcp/cat-networking.svg", "vpc": "gcp/cat-networking.svg", "subnet": "gcp/cat-networking.svg",
                "load-balancer": "gcp/cat-networking.svg", "private-egress": "gcp/cat-networking.svg",
                "transit-gateway": "gcp/cat-networking.svg", "hybrid-link": "gcp/cat-networking.svg", "cdn": "gcp/cat-networking.svg",
                "observability": "gcp/cat-observability.svg", "secrets-manager": "gcp/cat-security.svg", "kms": "gcp/cat-security.svg",
                "identity-provider": "gcp/cat-security.svg", "waf": "gcp/cat-security.svg", "firewall": "gcp/cat-security.svg",
                "message-queue": "gcp/cat-integration.svg", "event-stream": "gcp/cat-integration.svg",
                "cache": "gcp/cat-databases.svg", "nosql": "gcp/cat-databases.svg", "backup": "gcp/cat-storage.svg",
                "iac": "gcp/cat-management.svg", "catalog": "gcp/cat-data-analytics.svg", "etl": "gcp/cat-data-analytics.svg",
                "workflow": "gcp/cat-data-analytics.svg", "bi": "gcp/looker.svg",
                "container-registry": "gcp/cat-containers.svg", "devops": "gcp/cat-devops.svg",
            },
        },
    },
    # Group marks: the provider's own mark for a kind of boundary, keyed by
    # the key the palette gives the boundary. AWS publishes group icons for
    # its containers and they are used as such; Microsoft's subscription
    # mark stands for a subscription; the corporate data center is AWS's
    # group icon for exactly that and reads the same beside any cloud.
    # Google draws its containers as labeled boxes, and so do we.
    "groups": {
        "AWS": "aws/group-cloud.svg", "AWS account": "aws/group-account.svg", "AWS region": "aws/group-region.svg",
        "public subnet": "aws/public-subnet.svg", "private subnet": "aws/private-subnet.svg",
        "on-prem": "aws/group-data-center.svg", "On-prem": "aws/group-data-center.svg",
        "Azure subscription": "azure/subscriptions.svg",
    },
    # Vendor marks, from the Simple Icons collection, keyed by the words a
    # vendor, product or system name carries. Two point into the Azure set
    # because Microsoft publishes those marks there.
    "vendors": {
        "salesforce": "brands/salesforce.svg", "snowflake": "brands/snowflake.svg",
        "microsoft": "brands/microsoft.svg", "dynamics 365": "brands/microsoft.svg", "dynamics": "brands/microsoft.svg",
        "microsoft sentinel": "azure/sentinel.svg", "entra": "azure/entra-id.svg",
        "sap": "brands/sap.svg", "oracle": "brands/oracle.svg", "atlassian": "brands/atlassian.svg", "jira": "brands/jira.svg",
        "confluence": "brands/confluence.svg", "github": "brands/github.svg", "gitlab": "brands/gitlab.svg",
        "splunk": "brands/splunk.svg", "datadog": "brands/datadog.svg", "okta": "brands/okta.svg",
        "pagerduty": "brands/pagerduty.svg", "zendesk": "brands/zendesk.svg", "slack": "brands/slack.svg",
        "tableau": "brands/tableau.svg", "power bi": "brands/powerbi.svg", "databricks": "brands/databricks.svg",
        "kafka": "brands/apachekafka.svg", "redis": "brands/redis.svg", "postgresql": "brands/postgresql.svg",
        "postgres": "brands/postgresql.svg", "mongodb": "brands/mongodb.svg", "elastic": "brands/elastic.svg",
        "hashicorp": "brands/hashicorp.svg", "terraform": "brands/terraform.svg", "new relic": "brands/newrelic.svg",
        "dynatrace": "brands/dynatrace.svg", "twilio": "brands/twilio.svg", "stripe": "brands/stripe.svg",
        "adobe": "brands/adobe.svg", "docusign": "brands/docusign.svg", "mulesoft": "brands/mulesoft.svg",
        "informatica": "brands/informatica.svg", "alteryx": "brands/alteryx.svg", "qlik": "brands/qlik.svg",
    },
}

SOURCES = {
    "aws": {
        "set": "AWS Architecture Icons, release %s (Icon-package_%s.zip, 14.0 MB)" % (AWS_RELEASE, AWS_RELEASE),
        "url": "https://aws.amazon.com/architecture/icons/",
        "terms": "AWS publishes the icons for customers and partners to use in architecture diagrams; the package's "
                 "guidelines ask that icons are not modified or used to imply endorsement. The marks remain AWS's.",
    },
    "azure": {
        "set": "Azure Public Service Icons V24 (Azure_Public_Service_Icons_V24.zip, 1.0 MB)",
        "url": "https://learn.microsoft.com/en-us/azure/architecture/icons/",
        "terms": "\"Microsoft permits the use of these icons in architectural diagrams, training materials, or "
                 "documentation. You can copy, distribute, and display the icons only for the permitted use unless "
                 "granted explicit permission by Microsoft. Microsoft reserves all other rights.\"",
    },
    "gcp": {
        "set": "Google Cloud product and category icons (core-products-icons.zip, 319 KB; category-icons.zip, 796 KB)",
        "url": "https://cloud.google.com/icons",
        "terms": "Google publishes the icons for use in architecture diagrams of Google Cloud solutions; they are not to be "
                 "altered, and the marks remain Google's.",
    },
    "brands": {
        "set": "Simple Icons 16.34.0, the marks named in map.json",
        "url": "https://simpleicons.org/",
        "terms": "The SVG files are released under CC0 1.0 by the Simple Icons project; each mark is the trademark of its "
                 "owner, and its use here is to name the vendor's product on a diagram, nothing more. Each file is "
                 "given the brand color the collection records for it as a fill, since the files carry none.",
    },
}


def brand_colors(path: pathlib.Path | None) -> dict:
    """slug -> #hex from the collection's own data file, when given."""
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    icons = data.get("icons", data) if isinstance(data, dict) else data
    out = {}
    for entry in icons:
        slug = entry.get("slug") or re.sub(r"[^a-z0-9]", "", str(entry.get("title", "")).lower())
        if slug and entry.get("hex"):
            out[slug] = "#" + entry["hex"]
    return out


def colored(svg: str, fill: str) -> str:
    """The brand's color on the root element; the file carries none."""
    if re.search(r"<svg[^>]*\sfill=", svg):
        return svg
    return re.sub(r"<svg\b", '<svg fill="%s"' % fill, svg, count=1)


#: The sets a curation writes under OUT, beside `map.json` and `CREDITS.md`.
SETS = ("aws", "azure", "gcp", "brands")


def curated_files(out: pathlib.Path) -> list:
    """Every file an earlier curation left under `out`, or a refusal naming
    the first thing no curation writes.

    The folder used to go whole, `shutil.rmtree(OUT)` on a path worked out
    from this file's own place: the kind of delete that emptied most of
    AppData\\Local on 2026-10-18, when a path worked out the same way came
    out a level wrong. Now each file goes by name, and only while the folder
    holds nothing but the four sets of SVGs, `map.json` and `CREDITS.md`, so
    a wrong folder is refused rather than emptied."""
    def refuse(path: pathlib.Path) -> None:
        raise SystemExit("%s holds %s, which no curation writes; nothing was removed"
                         % (out, path.relative_to(out)))

    found = []
    for entry in sorted(out.iterdir()):
        if entry.is_symlink():
            refuse(entry)
        elif entry.name in ("map.json", "CREDITS.md") and entry.is_file():
            found.append(entry)
        elif entry.name in SETS and entry.is_dir():
            for svg in sorted(entry.iterdir()):
                if svg.is_symlink() or not svg.is_file() or svg.suffix != ".svg":
                    refuse(svg)
                found.append(svg)
        else:
            refuse(entry)
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", required=True, help="folder with aws/, azure/, gcp-core/, gcp-category/, brands/")
    parser.add_argument("--colors", help="the Simple Icons data file (simple-icons.json) for the brand colors")
    args = parser.parse_args(argv)
    source = pathlib.Path(args.source)
    aws, azure, gcp = picks(source)
    colors = brand_colors(pathlib.Path(args.colors) if args.colors else None)
    available = sorted(p.stem for p in (source / "brands").glob("*.svg"))
    # A mark the collection no longer lists is one its owner asked to have
    # withdrawn, even where the file still downloads; it is not shipped, and
    # the technology line names the vendor in words instead.
    withdrawn = [b for b in available if colors and b not in colors]
    brands = [b for b in available if b not in withdrawn]

    if OUT.exists():
        for path in curated_files(OUT):
            path.unlink()
        for folder in SETS:
            if (OUT / folder).is_dir():
                (OUT / folder).rmdir()
    for folder, chosen in (("aws", aws), ("azure", azure), ("gcp", gcp)):
        (OUT / folder).mkdir(parents=True)
        for slug, src in chosen.items():
            shutil.copy2(src, OUT / folder / (slug + ".svg"))
    (OUT / "brands").mkdir()
    for slug in brands:
        text = (source / "brands" / (slug + ".svg")).read_text(encoding="utf-8")
        (OUT / "brands" / (slug + ".svg")).write_text(colored(text, colors.get(slug, INK)), encoding="utf-8")

    vendors = {key: file for key, file in MAP["vendors"].items() if (OUT / file).exists()}
    referenced = set(vendors.values())
    for table in MAP["providers"].values():
        referenced.update(table["names"].values())
        referenced.update(table["kinds"].values())
    referenced.update(MAP["groups"].values())
    missing = sorted(f for f in referenced if not (OUT / f).exists())
    if missing:
        raise SystemExit("mapped but not shipped: %s" % missing)
    data = dict(MAP)
    data["vendors"] = vendors
    data["sources"] = SOURCES
    (OUT / "map.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    credits = ["# Icons and whose they are", "",
               "The marks in this folder are the providers' and vendors' own, shipped as a curated subset so a",
               "technology service or a bought system can carry the mark its reader already knows. `map.json`",
               "says which file a name or a kind of component points at; `50_ENGINE/terrane/icons.py` does the matching;",
               "`80_APP/tools/curate_icons.py` made the subset from the packages named below, which are theirs to",
               "distribute and so are not in this repository. The provider icons are copied unmodified; the vendor",
               "marks carry their brand color as a fill. Each set's terms, as published where it was taken from:", ""]
    for key in ("aws", "azure", "gcp", "brands"):
        s = SOURCES[key]
        credits += ["## %s" % s["set"], "", "Source: %s" % s["url"], "", s["terms"], ""]
    credits += ["## What is not here", "",
                "ServiceNow, Workday, Collibra, Pegasystems, Experian, Onfido and NICE keep their marks out of",
                "redistributable collections, so no file of theirs is shipped. A bought system from one of them",
                "names its vendor in the technology line under its name instead, which says the same thing in words.", ""]
    if withdrawn:
        credits += ["The collection no longer lists these marks, which is how it records one withdrawn at its",
                    "owner's request, so they are not shipped either, whatever the file server still serves:",
                    ", ".join(withdrawn) + ".", ""]
    (OUT / "CREDITS.md").write_text("\n".join(credits), encoding="utf-8")

    counts = {folder: len(list((OUT / folder).glob("*.svg"))) for folder in ("aws", "azure", "gcp", "brands")}
    size = sum(p.stat().st_size for p in OUT.rglob("*.svg"))
    print("shipped:", counts, "total %.0f KB" % (size / 1024))
    if withdrawn:
        print("withdrawn from the collection, not shipped:", ", ".join(withdrawn))
    return 0


if __name__ == "__main__":
    sys.exit(main())
