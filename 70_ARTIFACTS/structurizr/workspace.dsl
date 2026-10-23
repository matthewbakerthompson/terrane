// Generated from the model by `terrane render`. Do not edit by hand.
// C4 has no capability or org-unit element; those are exported as
// tagged software systems and are only present when a view selects them.
workspace "Architecture Model" "The application, data and technology landscape. Populate it with `terrane import csv` from an existing inventory, with the app in `80_APP/`, or by hand." {

    model {
        group "Card Issuing" {
            oi_ledger_queue = softwareSystem "Core Ledger request queue" "Postings, holds and balance requests put on the ledger's MQ request queue, answered on the reply queue in the order they arrived." "Element,Active" {
                properties {
                    "aac.type" "offered_interfaces"
                    "aac.id" "OI-LEDGER-QUEUE"
                    "aac.company_domain" "Card Issuing"
                }
            }
            oi_rewards_api = softwareSystem "Rewards Redemption API" "The domain API Rewards Redemption offers its channels, its jobs and its partners." "Element,Planned" {
                properties {
                    "aac.type" "offered_interfaces"
                    "aac.id" "OI-REWARDS-API"
                    "aac.company_domain" "Card Issuing"
                }
            }
        }
        group "Collections" {
            act_collections_agent = softwareSystem "Collections Agent" "Handles arrears treatment and payment arrangements." "Element,Active" {
                properties {
                    "aac.type" "actors"
                    "aac.id" "ACT-COLLECTIONS-AGENT"
                    "aac.company_domain" "Collections"
                    "aac.actor_kind" "Role"
                    "aac.internal" "Yes"
                }
            }
            oi_collect_api = softwareSystem "Collections Workspace API" "The domain API Collections Workspace offers its channels, its jobs and its partners." "Element,Active" {
                properties {
                    "aac.type" "offered_interfaces"
                    "aac.id" "OI-COLLECT-API"
                    "aac.company_domain" "Collections"
                }
            }
        }
        group "Data and Analytics" {
            sys_cust360_pipeline = softwareSystem "Customer 360 Pipeline" "Ingestion and curation jobs building Customer 360." "System,Medium,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CUST360-PIPELINE"
                    "aac.company_domain" "Data and Analytics"
                    "aac.hosting" "Azure"
                }
            }
            sys_cust360_semantic = softwareSystem "Customer 360 Semantic Layer" "Governed models and metrics exposed to analysts for Customer 360." "System,Medium,Active,SaaS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CUST360-SEMANTIC"
                    "aac.company_domain" "Data and Analytics"
                    "aac.hosting" "SaaS"
                }
            }
        }
        group "Edge" {
            sys_credit_bureau = softwareSystem "Experian Credit Bureau" "External credit reference agency used for affordability and bureau search at application time. Reached over PrivateLink from the lending workload account." "System,High,Active,SaaS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CREDIT-BUREAU"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.hosting" "SaaS"
                }
            }
            sys_crm = softwareSystem "Dynamics 365 Customer Service" "Contact center desktop and case management for servicing agents." "System,Medium,Active,SaaS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CRM"
                    "aac.company_domain" "Servicing"
                    "aac.hosting" "SaaS"
                }
            }
            sys_siem = softwareSystem "Security Monitoring" "Security information and event management: the audit trails of the estate and of every bought service, correlated in one place, and the console the incident response playbook runs from." "System,High,Active,SaaS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-SIEM"
                    "aac.company_domain" "Enterprise Platform"
                    "aac.hosting" "SaaS"
                }
            }
        }
        group "Enterprise Platform" {
            oi_identity_api = softwareSystem "Customer Identity API" "Customer authentication and the profile behind it, for every product that signs a customer in." "Element,Active" {
                properties {
                    "aac.type" "offered_interfaces"
                    "aac.id" "OI-IDENTITY-API"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
        }
        group "Lending" {
            act_applicant = softwareSystem "Loan Applicant" "A prospect applying for installment credit, not yet a customer." "Element,Active" {
                properties {
                    "aac.type" "actors"
                    "aac.id" "ACT-APPLICANT"
                    "aac.company_domain" "Lending"
                    "aac.actor_kind" "Person"
                    "aac.internal" "No"
                }
            }
            oi_lending_api = softwareSystem "Installment Lending API" "The domain API Installment Lending offers its channels, its jobs and its partners." "Element,Planned" {
                properties {
                    "aac.type" "offered_interfaces"
                    "aac.id" "OI-LENDING-API"
                    "aac.company_domain" "Lending"
                }
            }
            oi_posfin_api = softwareSystem "Point-of-Sale Finance API" "The domain API Point-of-Sale Finance offers its channels, its jobs and its partners." "Element,Planned" {
                properties {
                    "aac.type" "offered_interfaces"
                    "aac.id" "OI-POSFIN-API"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "On-prem" {
            sys_auth_switch = softwareSystem "Authorization Switch" "Real-time card authorization switch connected to the scheme networks." "System,High,Active,On-prem" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-AUTH-SWITCH"
                    "aac.company_domain" "Payments"
                    "aac.hosting" "On-prem"
                }
            }
            sys_core_ledger = softwareSystem "Core Card Ledger" "The mainframe card ledger holding balances, limits, postings and interest. Everything else in the estate is downstream of this." "System,High,Active,On-prem" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CORE-LEDGER"
                    "aac.company_domain" "Card Issuing"
                    "aac.hosting" "On-prem"
                }
            }
            sys_statements = softwareSystem "Statement Generation" "Composes, renders and dispatches customer statements." "System,Medium,Active,On-prem" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-STATEMENTS"
                    "aac.company_domain" "Servicing"
                    "aac.hosting" "On-prem"
                }
            }
            ts_onprem_dc = softwareSystem "Primary Data Center" "The data center the mainframe and the authorization switch live in. Modeled because half the integration cost of any cloud onboarding is the path back to here." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-ONPREM-DC"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
        }
        group "Payments" {
            act_card_scheme = softwareSystem "Card Scheme" "The network carrying authorization and clearing. An external system we integrate with on their terms, not ours, which is why their availability is a design constraint rather than a requirement." "Element,Active" {
                properties {
                    "aac.type" "actors"
                    "aac.id" "ACT-CARD-SCHEME"
                    "aac.company_domain" "Payments"
                    "aac.actor_kind" "External system"
                    "aac.internal" "No"
                }
            }
            act_merchant = softwareSystem "Merchant" "Accepts the card at point of sale. Reached through the scheme, never directly." "Element,Active" {
                properties {
                    "aac.type" "actors"
                    "aac.id" "ACT-MERCHANT"
                    "aac.company_domain" "Payments"
                    "aac.actor_kind" "Organization"
                    "aac.internal" "No"
                }
            }
            oi_merchant_api = softwareSystem "Merchant Portal API" "The domain API Merchant Portal offers its channels, its jobs and its partners." "Element,Planned" {
                properties {
                    "aac.type" "offered_interfaces"
                    "aac.id" "OI-MERCHANT-API"
                    "aac.company_domain" "Payments"
                }
            }
        }
        group "Risk and Compliance" {
            act_regulator = softwareSystem "Regulator" "Consumes periodic regulatory returns. Never integrates directly; the relationship is a reporting obligation with a deadline." "Element,Active" {
                properties {
                    "aac.type" "actors"
                    "aac.id" "ACT-REGULATOR"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.actor_kind" "Regulator"
                    "aac.internal" "No"
                }
            }
            act_underwriter = softwareSystem "Credit Underwriter" "Reviews referred applications the automated decision would not take." "Element,Active" {
                properties {
                    "aac.type" "actors"
                    "aac.id" "ACT-UNDERWRITER"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.actor_kind" "Role"
                    "aac.internal" "Yes"
                }
            }
        }
        group "Servicing" {
            act_cardholder = softwareSystem "Cardholder" "The customer. Uses the self-service channels, and is the reason the authorization path has a latency budget rather than a throughput one." "Element,Active" {
                properties {
                    "aac.type" "actors"
                    "aac.id" "ACT-CARDHOLDER"
                    "aac.company_domain" "Servicing"
                    "aac.actor_kind" "Person"
                    "aac.internal" "No"
                }
            }
            act_servicing_agent = softwareSystem "Servicing Agent" "Contact center staff handling balance, dispute and account queries." "Element,Active" {
                properties {
                    "aac.type" "actors"
                    "aac.id" "ACT-SERVICING-AGENT"
                    "aac.company_domain" "Servicing"
                    "aac.actor_kind" "Role"
                    "aac.internal" "Yes"
                }
            }
            oi_cardsvc_api = softwareSystem "Card Servicing API" "The domain API Card Servicing offers its channels, its jobs and its partners." "Element,Active" {
                properties {
                    "aac.type" "offered_interfaces"
                    "aac.id" "OI-CARDSVC-API"
                    "aac.company_domain" "Servicing"
                }
            }
            prd_card_servicing = softwareSystem "Card Servicing" "Self-service balance, statement, limit and payment servicing for cardholders." "Product,High,Active" {
                properties {
                    "aac.type" "products"
                    "aac.id" "PRD-CARD-SERVICING"
                    "aac.company_domain" "Servicing"
                }
            }
        }
        group "Unassigned" {
            sys_contact = softwareSystem "Contact center platform" "Contact center routing, voice, and digital channels." "System,Medium,Proposed" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CONTACT"
                    "aac.company_domain" ""
                }
            }
            sys_credit_data = softwareSystem "Credit data and decisioning environment" "Credit data, analytics, and decisioning environment." "System,Medium,Proposed" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CREDIT-DATA"
                    "aac.company_domain" ""
                }
            }
            sys_dialer = softwareSystem "Outbound contact platform" "Outbound dialer and contact campaign execution." "System,Medium,Proposed" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-DIALER"
                    "aac.company_domain" ""
                }
            }
            sys_doc = softwareSystem "Document management and archive" "Document generation, management, and archive." "System,Medium,Proposed" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-DOC"
                    "aac.company_domain" ""
                }
            }
            sys_ivr = softwareSystem "IVR and self-service voice" "Interactive voice response and voice self-service." "System,Medium,Proposed" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-IVR"
                    "aac.company_domain" ""
                }
            }
            sys_mobile = softwareSystem "Cardholder mobile application" "Cardholder mobile self-service." "System,Medium,Proposed" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-MOBILE"
                    "aac.company_domain" ""
                }
            }
            sys_orig_decision = softwareSystem "Originations decision engine" "Application processing and credit decision execution." "System,Medium,Proposed" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-ORIG-DECISION"
                    "aac.company_domain" ""
                }
            }
        }
        group "azure-cards-prod / uksouth" {
            sys_cardsvc_events = softwareSystem "Card Servicing Event Publisher" "Publishes Card Servicing domain events onto the enterprise bus." "System,Medium,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CARDSVC-EVENTS"
                    "aac.company_domain" "Servicing"
                    "aac.hosting" "Azure"
                }
            }
            sys_rewards_events = softwareSystem "Rewards Redemption Event Publisher" "Publishes Rewards Redemption domain events onto the enterprise bus." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-REWARDS-EVENTS"
                    "aac.company_domain" "Card Issuing"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-cards-prod / uksouth / Private-App" {
            sys_cardsvc_api = softwareSystem "Card Servicing Service" "The service behind the Card Servicing API, backing the channel." "System,High,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CARDSVC-API"
                    "aac.company_domain" "Servicing"
                    "aac.hosting" "Azure"
                }
            }
            sys_cardsvc_web = softwareSystem "Card Servicing Web" "Browser front end for Card Servicing." "System,High,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CARDSVC-WEB"
                    "aac.company_domain" "Servicing"
                    "aac.hosting" "Azure"
                }
            }
            sys_collect_api = softwareSystem "Collections Workspace Service" "The service behind the Collections Workspace API, backing the channel." "System,Medium,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-COLLECT-API"
                    "aac.company_domain" "Collections"
                    "aac.hosting" "Azure"
                }
            }
            sys_collect_web = softwareSystem "Collections Workspace Web" "Browser front end for Collections Workspace." "System,Medium,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-COLLECT-WEB"
                    "aac.company_domain" "Collections"
                    "aac.hosting" "Azure"
                }
            }
            sys_disputes_gateway = softwareSystem "Dispute Management Platform Integration Gateway" "Our side of the Pegasystems integration: mapping, retry and audit." "System,Medium,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-DISPUTES-GATEWAY"
                    "aac.company_domain" "Servicing"
                    "aac.hosting" "Azure"
                }
            }
            sys_rewards_api = softwareSystem "Rewards Redemption Service" "Domain service for Rewards Redemption, behind the Rewards Redemption API." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-REWARDS-API"
                    "aac.company_domain" "Card Issuing"
                    "aac.hosting" "Azure"
                }
            }
            sys_rewards_web = softwareSystem "Rewards Redemption Web" "Customer-facing front end for Rewards Redemption." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-REWARDS-WEB"
                    "aac.company_domain" "Card Issuing"
                    "aac.hosting" "Azure"
                }
            }
            sys_rewards_worker = softwareSystem "Rewards Redemption Async Worker" "Consumes redemption events and fulfills them: statement credits posted to the ledger, gift-card orders placed with the fulfillment partner." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-REWARDS-WORKER"
                    "aac.company_domain" "Card Issuing"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-cards-prod / uksouth / Private-Data" {
            sys_cardsvc_store = softwareSystem "Card Servicing Datastore" "Operational datastore owned by Card Servicing." "System,High,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-CARDSVC-STORE"
                    "aac.company_domain" "Servicing"
                    "aac.hosting" "Azure"
                }
            }
            sys_collect_store = softwareSystem "Collections Workspace Datastore" "Operational datastore owned by Collections Workspace." "System,Medium,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-COLLECT-STORE"
                    "aac.company_domain" "Collections"
                    "aac.hosting" "Azure"
                }
            }
            sys_rewards_store = softwareSystem "Rewards Redemption Database" "Relational database for Rewards Redemption, encrypted with a customer managed key." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-REWARDS-STORE"
                    "aac.company_domain" "Card Issuing"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-data-prod / uksouth / Private-Data" {
            sys_data_ingest = softwareSystem "Enterprise Data Ingestion Hub" "Landing zone and ingestion orchestration for inbound file and event feeds before they reach the warehouse." "System,Medium,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-DATA-INGEST"
                    "aac.company_domain" "Data and Analytics"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-payments-prod / uksouth" {
            sys_merchant_events = softwareSystem "Merchant Portal Event Publisher" "Publishes Merchant Portal domain events onto the enterprise bus." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-MERCHANT-EVENTS"
                    "aac.company_domain" "Payments"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-payments-prod / uksouth / Private-App" {
            sys_merchant_api = softwareSystem "Merchant Portal Service" "Domain API for the merchant portal: applications, settlement inquiries, chargeback responses and statement downloads." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-MERCHANT-API"
                    "aac.company_domain" "Payments"
                    "aac.hosting" "Azure"
                }
            }
            sys_merchant_web = softwareSystem "Merchant Portal Web" "Customer-facing front end for Merchant Portal." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-MERCHANT-WEB"
                    "aac.company_domain" "Payments"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-payments-prod / uksouth / Private-Data" {
            sys_merchant_store = softwareSystem "Merchant Portal Database" "Relational database for Merchant Portal, encrypted with a customer managed key." "System,Medium,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-MERCHANT-STORE"
                    "aac.company_domain" "Payments"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-platform-prod / uksouth / Shared-Services" {
            sys_identity_svc = softwareSystem "Customer Identity Service" "Shared platform service: Customer Identity Service." "System,High,Active,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-IDENTITY-SVC"
                    "aac.company_domain" "Enterprise Platform"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-risk-prod / uksouth / Private-App" {
            sys_idv_gateway = softwareSystem "Identity Document Verification Integration Gateway" "Our side of the Onfido integration: request mapping, retry and back-off, circuit breaking when the vendor is down, and the audit trail of what we sent them." "System,High,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-IDV-GATEWAY"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.hosting" "Azure"
                }
            }
            sys_reg_reporting = softwareSystem "Regulatory Reporting Engine" "Planned replacement for the spreadsheet-based regulatory reporting process, sourcing from the warehouse rather than from the ledger directly." "System,High,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-REG-REPORTING"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-risk-prod / uksouth / Public" {
            sys_idv_webhooks = softwareSystem "Identity Document Verification Webhook Listener" "Receives Onfido callbacks, verifies their signature, and forwards the event. Public by necessity, small by design." "System,High,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-IDV-WEBHOOKS"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "azure-risk-prod / uksouth / Shared-Services" {
            sys_idv_egress = softwareSystem "Identity Document Verification Private Egress" "PrivateLink endpoint and egress allow-list for Onfido. The control that keeps regulated data off the public internet, and the thing a security review asks to see first." "System,High,Planned,Azure" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-IDV-EGRESS"
                    "aac.company_domain" "Enterprise Platform"
                    "aac.hosting" "Azure"
                }
            }
        }
        group "eu-west-1 / Edge" {
            sys_disputes_saas = softwareSystem "Pega Smart Dispute" "Dispute Management Platform, provided by Pegasystems and running in the vendor tenancy." "System,Medium,Active,SaaS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-DISPUTES-SAAS"
                    "aac.company_domain" "Servicing"
                    "aac.hosting" "SaaS"
                }
            }
            sys_idv_vendor = softwareSystem "Identity Document Verification" "Document and liveness verification, operated by Onfido in their own tenancy. Contractually pinned to EU processing; images are deleted at the vendor once the result is returned." "System,High,Planned,SaaS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-IDV-VENDOR"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.hosting" "SaaS"
                }
            }
            sys_obaff_vendor = softwareSystem "Open Banking Affordability" "Open banking data access and affordability categorization, operated by TrueLayer in their own tenancy under the UK open banking framework; bank data is held for the assessment and deleted at the vendor once the result is returned." "System,Medium,Planned,SaaS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-OBAFF-VENDOR"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "SaaS"
                }
            }
            sys_screening_vendor = softwareSystem "NICE Actimize Screening" "Financial Crime Screening, operated by NICE Actimize in their own tenancy. Contractually pinned to EU processing; the DPA restricts sub-processors and sets a 90-day retention ceiling." "System,High,Planned,SaaS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-SCREENING-VENDOR"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.hosting" "SaaS"
                }
            }
        }
        group "gcp-analytics-prod / europe-west1 / Private-Data" {
            ts_gcpnet_sub_analytics_data_dr = softwareSystem "Analytics Data Subnetwork (DR)" "The warm-standby region's subnetwork for the analytics jobs, empty until a failover. BigQuery keeps the dataset in a multi-region of its own, so what fails over is the jobs and the schedule, not the data." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-SUB-ANALYTICS-DATA-DR"
                    "aac.company_domain" "Data and Analytics"
                }
            }
        }
        group "gcp-analytics-prod / europe-west2 / Private-Data" {
            sys_lendperf_pipeline = softwareSystem "Lending Portfolio Performance Pipeline" "Dataflow jobs on a Composer schedule, ingesting the source events of Lending Portfolio Performance from Pub/Sub and curating them into BigQuery." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDPERF-PIPELINE"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "GCP"
                }
            }
            sys_lendperf_semantic = softwareSystem "Lending Portfolio Performance Semantic Layer" "Governed models and metrics exposed to analysts for Lending Portfolio Performance, served from BigQuery through Looker." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDPERF-SEMANTIC"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "GCP"
                }
            }
            ts_gcpnet_sub_analytics_data = softwareSystem "Analytics Data Subnetwork" "The analytics project's one subnetwork, for the Dataflow workers and the Composer environment; BigQuery and Pub/Sub are reached over Private Google Access rather than through it." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-SUB-ANALYTICS-DATA"
                    "aac.company_domain" "Data and Analytics"
                }
            }
        }
        group "gcp-analytics-prod / europe-west2 / Public" {
            ts_gcpnet_nat_analytics = softwareSystem "Analytics Cloud NAT" "Regional NAT for the Dataflow workers' egress to the package mirrors and nothing else; the data never leaves by it." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-NAT-ANALYTICS"
                    "aac.company_domain" "Data and Analytics"
                }
            }
        }
        group "gcp-lending-prod / europe-west1 / Private-App" {
            ts_gcpnet_sub_lend_app_dr = softwareSystem "Lending App Subnetwork (DR)" "The warm-standby region's application tier, empty until a failover; the same VPC, since a Google Cloud VPC is global, so no peering to maintain." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-SUB-LEND-APP-DR"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "gcp-lending-prod / europe-west2" {
            sys_posfin_events = softwareSystem "Point-of-Sale Finance Event Publisher" "Publishes Point-of-Sale Finance domain events onto the enterprise bus." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-POSFIN-EVENTS"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "GCP"
                }
            }
        }
        group "gcp-lending-prod / europe-west2 / Edge" {
            ts_gcpnet_ext_lb_lend = softwareSystem "Lending External Load Balancer" "The external HTTPS load balancer in front of the product's channel, with Cloud Armor attached; the edge of the lending workload on Google Cloud." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-EXT-LB-LEND"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "gcp-lending-prod / europe-west2 / Private-App" {
            sys_obaff_gateway = softwareSystem "Open Banking Affordability Integration Gateway" "Our side of the TrueLayer integration: request mapping, retry and back-off, circuit breaking when the vendor is down, and the audit trail of what we sent them." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-OBAFF-GATEWAY"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "GCP"
                }
            }
            sys_posfin_api = softwareSystem "Point-of-Sale Finance Service" "Domain API for point-of-sale finance: dealer applications, shopper identity and consent, decisions, and the payment schedule that follows." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-POSFIN-API"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "GCP"
                }
            }
            sys_posfin_web = softwareSystem "Point-of-Sale Finance Web" "Customer-facing front end for Point-of-Sale Finance." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-POSFIN-WEB"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "GCP"
                }
            }
            ts_gcpnet_sub_lend_app = softwareSystem "Lending App Subnetwork" "Where the GKE nodes land. Regional, shared to the lending project from the host project, so the zones are the cluster's to spread across." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-SUB-LEND-APP"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "gcp-lending-prod / europe-west2 / Private-Data" {
            sys_posfin_db = softwareSystem "Point-of-Sale Finance Database" "Relational database for Point-of-Sale Finance, encrypted with a customer managed key." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-POSFIN-DB"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "GCP"
                }
            }
            ts_gcpnet_sub_lend_data = softwareSystem "Lending Data Subnetwork" "Cloud SQL's private services access range and the Memorystore endpoints; no route to the internet, in or out." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-SUB-LEND-DATA"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "gcp-lending-prod / europe-west2 / Public" {
            sys_obaff_webhooks = softwareSystem "Open Banking Affordability Webhook Listener" "Receives TrueLayer callbacks, verifies their signature, and forwards the event. Public by necessity, small by design." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-OBAFF-WEBHOOKS"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "GCP"
                }
            }
            ts_gcpnet_nat_lend = softwareSystem "Lending Cloud NAT" "Regional NAT for the private subnetworks' egress, the only way out that is not a Private Service Connect endpoint; one gateway per region, not one per zone." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-NAT-LEND"
                    "aac.company_domain" "Lending"
                }
            }
            ts_gcpnet_proxy_sub_lend = softwareSystem "Lending Proxy-only Subnetwork" "The proxy-only subnetwork the regional external load balancer's proxies sit in; nothing of ours runs there, and nothing of ours may." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-PROXY-SUB-LEND"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "gcp-lending-prod / europe-west2 / Shared-Services" {
            sys_obaff_egress = softwareSystem "Open Banking Affordability Private Egress" "PrivateLink endpoint and egress allow-list for TrueLayer. The control that keeps regulated data off the public internet, and the thing a security review asks to see first." "System,Medium,Planned,GCP" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-OBAFF-EGRESS"
                    "aac.company_domain" "Enterprise Platform"
                    "aac.hosting" "GCP"
                }
            }
        }
        group "gcp-shared-network / europe-west2 / Shared-Services" {
            ts_gcp_cloud_dns = softwareSystem "Cloud DNS" "Public and private zones for the Google Cloud estate, peered to the data center's resolvers." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCP-CLOUD-DNS"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_gcp_interconnect = softwareSystem "Cloud Interconnect" "Dedicated Interconnect back to the data center, two attachments in two edge availability domains; the failover between them is tested quarterly." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCP-INTERCONNECT"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_gcp_ncc = softwareSystem "Network Connectivity Center" "The hub the workload VPC spokes and the interconnect attach to; the transit of the Google Cloud zone." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCP-NCC"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_gcp_shared_vpc = softwareSystem "Shared VPC network" "The host project's network the workload projects attach to, with the tiers as subnetworks." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCP-SHARED-VPC"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_gcpnet_ha_vpn = softwareSystem "HA VPN" "The backup path to the data center: HA VPN over the internet, two tunnels with BGP, carrying the traffic when the Interconnect does not. Tested on the same quarterly failover as the Interconnect's second attachment." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-GCPNET-HA-VPN"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
        }
        group "prod-lending / eu-west-1 / Private-App" {
            ts_net_vpc_lending_dr = softwareSystem "Lending VPC (DR)" "Warm standby VPC in the recovery region. Built by the same Terraform as the primary; capacity is scaled to zero until a declaration." "Technology Service,Planned" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-VPC-LENDING-DR"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "prod-lending / eu-west-2 / Edge" {
            ts_net_igw_lending = softwareSystem "Lending Internet Gateway" "The only route to the internet, and only from the public subnets." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-IGW-LENDING"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "prod-lending / eu-west-2 / Private-App" {
            sys_lending_api = softwareSystem "Installment Lending Service" "Domain service for Installment Lending, behind the Installment Lending API." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDING-API"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "AWS"
                }
            }
            sys_lending_hub = softwareSystem "Installment Lending Integration Hub" "Mediates every Installment Lending integration: one place for mapping, routing, retry and the audit trail, so the spokes do not each carry their own." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDING-HUB"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "AWS"
                }
            }
            sys_lending_web = softwareSystem "Installment Lending Web" "Customer-facing front end for Installment Lending." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDING-WEB"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "AWS"
                }
            }
            sys_lending_worker = softwareSystem "Installment Lending Async Worker" "Consumes Installment Lending domain events and drives long-running work." "System,Medium,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDING-WORKER"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "AWS"
                }
            }
            ts_net_sub_lend_app_a = softwareSystem "Lending App Subnet A" "" "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-SUB-LEND-APP-A"
                    "aac.company_domain" "Lending"
                }
            }
            ts_net_sub_lend_app_b = softwareSystem "Lending App Subnet B" "" "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-SUB-LEND-APP-B"
                    "aac.company_domain" "Lending"
                }
            }
            ts_net_vpc_lending = softwareSystem "Lending VPC" "Workload VPC for the lending product, three tiers across two zones." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-VPC-LENDING"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "prod-lending / eu-west-2 / Private-Data" {
            sys_lending_bucket = softwareSystem "Installment Lending Object Store" "S3 bucket holding signed credit agreements and disbursement evidence. Seven-year retention with Object Lock; a records-management obligation rather than ordinary product storage." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDING-BUCKET"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "AWS"
                }
            }
            sys_lending_db = softwareSystem "Installment Lending Database" "Relational database for Installment Lending, encrypted with a customer managed key." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDING-DB"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "AWS"
                }
            }
            ts_net_sub_lend_data_a = softwareSystem "Lending Data Subnet A" "" "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-SUB-LEND-DATA-A"
                    "aac.company_domain" "Lending"
                }
            }
            ts_net_sub_lend_data_b = softwareSystem "Lending Data Subnet B" "" "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-SUB-LEND-DATA-B"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "prod-lending / eu-west-2 / Public" {
            sys_lending_alb = softwareSystem "Installment Lending Load Balancer" "Public load balancer terminating TLS for Installment Lending." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDING-ALB"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "AWS"
                }
            }
            ts_net_nat_lend_a = softwareSystem "Lending NAT Gateway A" "Outbound-only egress for the private tiers. One per zone, so a zone loss is not an outage." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-NAT-LEND-A"
                    "aac.company_domain" "Lending"
                }
            }
            ts_net_nat_lend_b = softwareSystem "Lending NAT Gateway B" "" "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-NAT-LEND-B"
                    "aac.company_domain" "Lending"
                }
            }
            ts_net_sub_lend_pub_a = softwareSystem "Lending Public Subnet A" "" "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-SUB-LEND-PUB-A"
                    "aac.company_domain" "Lending"
                }
            }
            ts_net_sub_lend_pub_b = softwareSystem "Lending Public Subnet B" "" "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-SUB-LEND-PUB-B"
                    "aac.company_domain" "Lending"
                }
            }
        }
        group "prod-lending / global / Edge" {
            sys_lending_edge = softwareSystem "Installment Lending Edge" "CDN distribution and WAF ruleset for Installment Lending." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-LENDING-EDGE"
                    "aac.company_domain" "Lending"
                    "aac.hosting" "AWS"
                }
            }
        }
        group "prod-riskops / eu-west-2 / Private-App" {
            sys_screening_gateway = softwareSystem "NICE Actimize Screening Integration Gateway" "Our side of the NICE Actimize integration: request mapping, retry and back-off, circuit breaking when the vendor is down, and the audit trail of what we sent them." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-SCREENING-GATEWAY"
                    "aac.company_domain" "Risk and Compliance"
                    "aac.hosting" "AWS"
                }
            }
            ts_net_vpc_riskops = softwareSystem "Risk Operations VPC" "Workload VPC for screening and risk tooling." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-VPC-RISKOPS"
                    "aac.company_domain" "Risk and Compliance"
                }
            }
        }
        group "prod-riskops / eu-west-2 / Shared-Services" {
            sys_screening_egress = softwareSystem "NICE Actimize Screening Private Egress" "PrivateLink endpoint and egress allow-list for NICE Actimize. The control that keeps regulated data off the public internet, and the thing a security review asks to see first." "System,High,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-SCREENING-EGRESS"
                    "aac.company_domain" "Enterprise Platform"
                    "aac.hosting" "AWS"
                }
            }
            sys_screening_federation = softwareSystem "NICE Actimize Screening Identity Federation" "Single sign-on into NICE Actimize: assertions from our identity provider, so access is granted and revoked where the joiner and leaver process already runs." "System,Medium,Planned,AWS" {
                properties {
                    "aac.type" "systems"
                    "aac.id" "SYS-SCREENING-FEDERATION"
                    "aac.company_domain" "Enterprise Platform"
                    "aac.hosting" "AWS"
                }
            }
        }
        group "shared-network / eu-west-2 / Shared-Services" {
            ts_aws_privatelink = softwareSystem "AWS PrivateLink" "Private egress to partner and vendor endpoints without internet transit." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-AWS-PRIVATELINK"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_aws_tgw = softwareSystem "AWS Transit Gateway" "Hub for VPC-to-VPC and hybrid routing back to the data center." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-AWS-TGW"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_net_dx = softwareSystem "Direct Connect" "Dual 10G circuits to the data center, one per carrier hall. The primary hybrid path, and the long-lead item on any onboarding that touches the mainframe." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-DX"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_net_route53 = softwareSystem "Route 53 Resolver" "Private hosted zones and inbound/outbound resolution to on-premise DNS." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-ROUTE53"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_net_vpc_shared = softwareSystem "Shared Services VPC" "Hub VPC holding the transit attachments, egress and resolver endpoints." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-VPC-SHARED"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
            ts_net_vpn = softwareSystem "Site-to-Site VPN" "Encrypted backup path over the internet, used only when Direct Connect is down." "Technology Service,Active" {
                properties {
                    "aac.type" "tech_services"
                    "aac.id" "TS-NET-VPN"
                    "aac.company_domain" "Enterprise Platform"
                }
            }
        }

        sys_orig_decision -> sys_credit_data "Originations Decision Engine to Credit Data Environment" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-ORIG-CREDIT-DATA"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "api-front-door"
            }
        }
        sys_orig_decision -> sys_core_ledger "Originations Decision Engine to Core Card Ledger" "FileTransfer" "scheduled-file" {
            properties {
                "aac.interface_id" "INT-ORIG-LEDGER-BOARD"
                "aac.kind" "scheduled-file"
                "aac.integration_style" "Batch"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
                "aac.patterns" "windowed-batch"
            }
        }
        sys_orig_decision -> sys_doc "Originations Decision Engine to Document Management" "AMQP" "event" {
            properties {
                "aac.interface_id" "INT-ORIG-DOC"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "customer-communication-archive"
            }
        }
        sys_mobile -> sys_cardsvc_api "Cardholder Mobile to Card Servicing API" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-MOBILE-CARDSVC"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "api-front-door"
                "aac.offered_interface_id" "OI-CARDSVC-API"
            }
        }
        sys_collect_api -> sys_dialer "Collections Platform to Outbound Contact Platform" "FileTransfer" "scheduled-file" {
            properties {
                "aac.interface_id" "INT-COLLECT-DIALER"
                "aac.kind" "scheduled-file"
                "aac.integration_style" "Batch"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
                "aac.patterns" "contact-center-integration"
            }
        }
        sys_dialer -> sys_collect_api "Outbound Contact Platform to Collections Platform" "AMQP" "event" {
            properties {
                "aac.interface_id" "INT-DIALER-COLLECT"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "contact-center-integration;event-fanout"
            }
        }
        sys_collect_api -> sys_doc "Collections Platform to Document Management" "AMQP" "event" {
            properties {
                "aac.interface_id" "INT-COLLECT-DOC"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "customer-communication-archive"
            }
        }
        sys_core_ledger -> sys_doc "Core Card Ledger to Document Management" "FileTransfer" "scheduled-file" {
            properties {
                "aac.interface_id" "INT-LEDGER-DOC"
                "aac.kind" "scheduled-file"
                "aac.integration_style" "Batch"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
                "aac.patterns" "customer-communication-archive"
            }
        }
        sys_statements -> sys_doc "Statement Generation to Document Management" "FileTransfer" "scheduled-file" {
            properties {
                "aac.interface_id" "INT-STATEMENTS-DOC"
                "aac.kind" "scheduled-file"
                "aac.integration_style" "Batch"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
                "aac.patterns" "customer-communication-archive"
            }
        }
        sys_contact -> sys_crm "Contact Center Platform to CRM" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-CONTACT-CRM"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "contact-center-integration"
            }
        }
        sys_ivr -> sys_contact "IVR to Contact Center Platform" "SIP" {
            properties {
                "aac.interface_id" "INT-IVR-CONTACT"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "contact-center-integration"
            }
        }
        sys_ivr -> sys_cardsvc_api "IVR to Card Servicing API" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-IVR-CARDSVC"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "contact-center-integration;api-front-door"
                "aac.offered_interface_id" "OI-CARDSVC-API"
            }
        }
        sys_crm -> sys_disputes_gateway "CRM to Dispute Gateway" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-CRM-DISPUTES"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.patterns" "private-egress-to-saas"
            }
        }
        sys_data_ingest -> sys_credit_data "Enterprise Data Platform to Credit Data Environment" "SQL" "pipeline-load" {
            properties {
                "aac.interface_id" "INT-INGEST-CREDIT-DATA"
                "aac.kind" "pipeline-load"
                "aac.integration_style" "Batch"
                "aac.auth_method" "ManagedIdentity"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
                "aac.patterns" "analytics-landing-zone"
            }
        }
        sys_auth_switch -> sys_core_ledger "Authorization Switch to Core Ledger" "MQ" "queued-request" {
            properties {
                "aac.interface_id" "INT-AUTH-LEDGER"
                "aac.kind" "queued-request"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-LEDGER-QUEUE"
            }
        }
        sys_cardsvc_api -> sys_identity_svc "Card Servicing Service to Identity Service" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-CARDSVC-API-IDENTITY"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-IDENTITY-API"
            }
        }
        sys_cardsvc_api -> sys_core_ledger "Card Servicing Service to Core Ledger" "MQ" "queued-request" {
            properties {
                "aac.interface_id" "INT-CARDSVC-API-LEDGER"
                "aac.kind" "queued-request"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-LEDGER-QUEUE"
            }
        }
        sys_cardsvc_events -> sys_data_ingest "Card Servicing Events to Data Ingestion Hub" "AMQP" "event" {
            properties {
                "aac.interface_id" "INT-CARDSVC-EVENTS-INGEST"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "ManagedIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_collect_api -> sys_identity_svc "Collections Service to Identity Service" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-COLLECT-API-IDENTITY"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-IDENTITY-API"
            }
        }
        sys_collect_api -> sys_core_ledger "Collections Service to Core Ledger" "MQ" "queued-request" {
            properties {
                "aac.interface_id" "INT-COLLECT-API-LEDGER"
                "aac.kind" "queued-request"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-LEDGER-QUEUE"
            }
        }
        sys_crm -> sys_core_ledger "Servicing CRM to Core Ledger" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-CRM-LEDGER"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_cust360_semantic -> sys_reg_reporting "Customer 360 Semantic Layer to Regulatory Reporting Engine" "SQL" "pipeline-load" {
            properties {
                "aac.interface_id" "INT-CUST360-REGREPORTING"
                "aac.kind" "pipeline-load"
                "aac.integration_style" "Batch"
                "aac.auth_method" "KeyPair"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
            }
        }
        sys_core_ledger -> sys_data_ingest "Core Ledger to Data Ingestion Hub" "FileTransfer" "scheduled-file" {
            properties {
                "aac.interface_id" "INT-LEDGER-INGEST"
                "aac.kind" "scheduled-file"
                "aac.integration_style" "Batch"
                "aac.auth_method" "KeyPair"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
            }
        }
        sys_core_ledger -> sys_statements "Core Ledger to Statement Generation" "FileTransfer" "scheduled-file" {
            properties {
                "aac.interface_id" "INT-LEDGER-STATEMENTS"
                "aac.kind" "scheduled-file"
                "aac.integration_style" "Batch"
                "aac.auth_method" "KeyPair"
                "aac.frequency" "Monthly"
                "aac.direction" "Outbound"
            }
        }
        sys_lending_api -> sys_core_ledger "Installment Lending Service to Core Card Ledger" "MQ" "queued-request" {
            properties {
                "aac.interface_id" "INT-LENDING-API-LEDGER"
                "aac.kind" "queued-request"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-LEDGER-QUEUE"
            }
        }
        sys_lending_api -> sys_identity_svc "Installment Lending Service to Identity Service" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-API-IDENTITY"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-IDENTITY-API"
            }
        }
        sys_lending_worker -> sys_data_ingest "Installment Lending Worker to Data Ingestion Hub" "S3" "pipeline-load" {
            properties {
                "aac.interface_id" "INT-LENDING-WORKER-INGEST"
                "aac.kind" "pipeline-load"
                "aac.integration_style" "Batch"
                "aac.auth_method" "IAM"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
            }
        }
        sys_lending_api -> sys_credit_bureau "Installment Lending Service to Credit Bureau" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-API-BUREAU"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_cardsvc_web -> sys_cardsvc_api "Card Servicing Web to API" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-CARDSVC-WEB-API"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-CARDSVC-API"
            }
        }
        sys_cardsvc_api -> sys_cardsvc_store "Card Servicing Service to Datastore" "TDS" "own-datastore" {
            properties {
                "aac.interface_id" "INT-CARDSVC-API-STORE"
                "aac.kind" "own-datastore"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "ManagedIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_cardsvc_api -> sys_cardsvc_events "Card Servicing Service to Event Publisher" "AMQP" "event" {
            properties {
                "aac.interface_id" "INT-CARDSVC-API-EVENTS"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "ManagedIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_collect_web -> sys_collect_api "Collections Workspace Web to API" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-COLLECT-WEB-API"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-COLLECT-API"
            }
        }
        sys_collect_api -> sys_collect_store "Collections Workspace Service to Datastore" "TDS" "own-datastore" {
            properties {
                "aac.interface_id" "INT-COLLECT-API-STORE"
                "aac.kind" "own-datastore"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "ManagedIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_data_ingest -> sys_cust360_pipeline "Ingest to Customer 360 Pipeline" "Snowpipe" "pipeline-load" {
            properties {
                "aac.interface_id" "INT-CUST360-INGEST"
                "aac.kind" "pipeline-load"
                "aac.integration_style" "Batch"
                "aac.auth_method" "KeyPair"
                "aac.frequency" "Daily"
                "aac.direction" "Inbound"
            }
        }
        sys_cust360_pipeline -> sys_cust360_semantic "Customer 360 Pipeline to Semantic Layer" "SQL" "pipeline-load" {
            properties {
                "aac.interface_id" "INT-CUST360-PIPE-SEMANTIC"
                "aac.kind" "pipeline-load"
                "aac.integration_style" "Batch"
                "aac.auth_method" "KeyPair"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
            }
        }
        sys_core_ledger -> sys_disputes_gateway "SYS-CORE-LEDGER to Dispute Management Platform Gateway" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-DISPUTES-UP-GATEWAY"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_disputes_gateway -> sys_disputes_saas "Dispute Management Platform Gateway to Pegasystems" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-DISPUTES-GATEWAY-SAAS"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_disputes_saas -> sys_data_ingest "Pegasystems return feed" "SFTP" "partner-file" {
            properties {
                "aac.interface_id" "INT-DISPUTES-SAAS-FEED"
                "aac.kind" "partner-file"
                "aac.integration_style" "Batch"
                "aac.auth_method" "KeyPair"
                "aac.frequency" "Daily"
                "aac.direction" "Inbound"
            }
        }
        sys_identity_svc -> sys_idv_gateway "SYS-IDENTITY-SVC to Identity Document Verification Gateway" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-IDV-CALLER-GATEWAY"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_idv_gateway -> sys_idv_egress "Identity Document Verification Gateway to Private Egress" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-IDV-GATEWAY-EGRESS"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_idv_egress -> sys_idv_vendor "Private Egress to Onfido" "PrivateLink" "private-egress" {
            properties {
                "aac.interface_id" "INT-IDV-EGRESS-VENDOR"
                "aac.kind" "private-egress"
                "aac.integration_style" "Request-response"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_idv_vendor -> sys_idv_webhooks "Onfido webhooks" "HTTPS" "event-over-https" {
            properties {
                "aac.interface_id" "INT-IDV-VENDOR-WEBHOOKS"
                "aac.kind" "event-over-https"
                "aac.integration_style" "Event"
                "aac.auth_method" "HMAC"
                "aac.frequency" "Realtime"
                "aac.direction" "Inbound"
            }
        }
        sys_idv_webhooks -> sys_identity_svc "Identity Document Verification Webhook Listener to SYS-IDENTITY-SVC" "HTTPS" "event-over-https" {
            properties {
                "aac.interface_id" "INT-IDV-WEBHOOKS-CONSUMER"
                "aac.kind" "event-over-https"
                "aac.integration_style" "Event"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_lending_web -> sys_lending_api "Installment Lending Web to API" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-WEB-API"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-LENDING-API"
            }
        }
        sys_lending_edge -> sys_lending_alb "Installment Lending Edge to Load Balancer" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-EDGE-ALB"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Inbound"
            }
        }
        sys_lending_alb -> sys_lending_web "Installment Lending Load Balancer to Web" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-ALB-WEB"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Inbound"
            }
        }
        sys_lending_api -> sys_lending_worker "Installment Lending Service to Async Worker" "Kafka" "event" {
            properties {
                "aac.interface_id" "INT-LENDING-API-WORKER"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_lending_api -> sys_lending_db "Installment Lending Service to Database" "PostgreSQL" "own-datastore" {
            properties {
                "aac.interface_id" "INT-LENDING-API-DB"
                "aac.kind" "own-datastore"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_lending_api -> sys_lending_bucket "Installment Lending Service to Object Store" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-API-BUCKET"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_core_ledger -> sys_lending_hub "CORE-LEDGER via Installment Lending hub" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-CORE-LEDGER-HUB"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_credit_bureau -> sys_lending_hub "CREDIT-BUREAU via Installment Lending hub" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-CREDIT-BUREAU-HUB"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_crm -> sys_lending_hub "CRM via Installment Lending hub" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-LENDING-CRM-HUB"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_posfin_events -> sys_lendperf_pipeline "Source events to Lending Portfolio Performance Pipeline" "Pub/Sub" "event" {
            properties {
                "aac.interface_id" "INT-LENDPERF-INGEST"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "WorkloadIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Inbound"
            }
        }
        sys_lendperf_pipeline -> sys_lendperf_semantic "Lending Portfolio Performance Pipeline to Semantic Layer" "SQL" "pipeline-load" {
            properties {
                "aac.interface_id" "INT-LENDPERF-PIPE-SEMANTIC"
                "aac.kind" "pipeline-load"
                "aac.integration_style" "Batch"
                "aac.auth_method" "WorkloadIdentity"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
            }
        }
        sys_lendperf_semantic -> sys_reg_reporting "Lending Portfolio Performance Semantic Layer to Regulatory Reporting Engine" "HTTPS" "scheduled-pull" {
            properties {
                "aac.interface_id" "INT-LENDPERF-REGREPORTING"
                "aac.kind" "scheduled-pull"
                "aac.integration_style" "Batch"
                "aac.auth_method" "WorkloadIdentity"
                "aac.frequency" "Daily"
                "aac.direction" "Outbound"
            }
        }
        sys_merchant_web -> sys_merchant_api "Merchant Portal Web to API" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-MERCHANT-WEB-API"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-MERCHANT-API"
            }
        }
        sys_merchant_api -> sys_merchant_store "Merchant Portal Service to Database" "TDS" "own-datastore" {
            properties {
                "aac.interface_id" "INT-MERCHANT-API-STORE"
                "aac.kind" "own-datastore"
                "aac.integration_style" "Request-response"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_merchant_api -> sys_merchant_events "Merchant Portal Service to Event Publisher" "AMQP" "event" {
            properties {
                "aac.interface_id" "INT-MERCHANT-API-EVENTS"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_posfin_api -> sys_obaff_gateway "SYS-POSFIN-API to Open Banking Affordability Gateway" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-OBAFF-CALLER-GATEWAY"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_obaff_gateway -> sys_obaff_egress "Open Banking Affordability Gateway to Private Egress" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-OBAFF-GATEWAY-EGRESS"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_obaff_egress -> sys_obaff_vendor "Private Egress to TrueLayer" "PrivateLink" "private-egress" {
            properties {
                "aac.interface_id" "INT-OBAFF-EGRESS-VENDOR"
                "aac.kind" "private-egress"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "WorkloadIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_obaff_vendor -> sys_obaff_webhooks "TrueLayer webhooks" "HTTPS" "event-over-https" {
            properties {
                "aac.interface_id" "INT-OBAFF-VENDOR-WEBHOOKS"
                "aac.kind" "event-over-https"
                "aac.integration_style" "Event"
                "aac.auth_method" "HMAC"
                "aac.frequency" "Realtime"
                "aac.direction" "Inbound"
            }
        }
        sys_obaff_webhooks -> sys_posfin_api "Open Banking Affordability Webhook Listener to SYS-POSFIN-API" "HTTPS" "event-over-https" {
            properties {
                "aac.interface_id" "INT-OBAFF-WEBHOOKS-CONSUMER"
                "aac.kind" "event-over-https"
                "aac.integration_style" "Event"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_posfin_web -> sys_posfin_api "Point-of-Sale Finance Web to API" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-POSFIN-WEB-API"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-POSFIN-API"
            }
        }
        sys_posfin_api -> sys_posfin_db "Point-of-Sale Finance Service to Database" "PostgreSQL" "own-datastore" {
            properties {
                "aac.interface_id" "INT-POSFIN-API-DB"
                "aac.kind" "own-datastore"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "WorkloadIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_posfin_api -> sys_posfin_events "Point-of-Sale Finance Service to Event Publisher" "AMQP" "event" {
            properties {
                "aac.interface_id" "INT-POSFIN-API-EVENTS"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "WorkloadIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_rewards_web -> sys_rewards_api "Rewards Redemption Web to API" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-REWARDS-WEB-API"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "OAuth2"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-REWARDS-API"
            }
        }
        sys_rewards_api -> sys_rewards_store "Rewards Redemption Service to Database" "TDS" "own-datastore" {
            properties {
                "aac.interface_id" "INT-REWARDS-API-STORE"
                "aac.kind" "own-datastore"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "ManagedIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_rewards_api -> sys_rewards_events "Rewards Redemption Service to Event Publisher" "AMQP" "event" {
            properties {
                "aac.interface_id" "INT-REWARDS-API-EVENTS"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "ManagedIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_rewards_api -> sys_rewards_worker "Rewards Redemption Service to Async Worker" "Kafka" "event" {
            properties {
                "aac.interface_id" "INT-REWARDS-API-WORKER"
                "aac.kind" "event"
                "aac.integration_style" "Event"
                "aac.auth_method" "ManagedIdentity"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_rewards_worker -> sys_core_ledger "Rewards Redemption Worker to Core Ledger" "MQ" "queued-request" {
            properties {
                "aac.interface_id" "INT-REWARDS-WORKER-LEDGER"
                "aac.kind" "queued-request"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
                "aac.offered_interface_id" "OI-LEDGER-QUEUE"
            }
        }
        sys_auth_switch -> sys_screening_gateway "SYS-AUTH-SWITCH to NICE Actimize Screening Gateway" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-SCREENING-CALLER-GATEWAY"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_screening_federation -> sys_screening_vendor "Identity Federation to NICE Actimize" "SAML" "sign-on-federation" {
            properties {
                "aac.interface_id" "INT-SCREENING-FEDERATION-VENDOR"
                "aac.kind" "sign-on-federation"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "Certificate"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_screening_vendor -> sys_siem "NICE Actimize audit log to security monitoring" "HTTPS" "event-over-https" {
            properties {
                "aac.interface_id" "INT-SCREENING-VENDOR-AUDIT"
                "aac.kind" "event-over-https"
                "aac.integration_style" "Event"
                "aac.auth_method" "Token"
                "aac.frequency" "Realtime"
                "aac.direction" "Inbound"
            }
        }
        sys_screening_gateway -> sys_screening_egress "NICE Actimize Screening Gateway to Private Egress" "HTTPS" "api-call" {
            properties {
                "aac.interface_id" "INT-SCREENING-GATEWAY-EGRESS"
                "aac.kind" "api-call"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "IAM"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_screening_egress -> sys_screening_vendor "Private Egress to NICE Actimize" "PrivateLink" "private-egress" {
            properties {
                "aac.interface_id" "INT-SCREENING-EGRESS-VENDOR"
                "aac.kind" "private-egress"
                "aac.integration_style" "Request-response"
                "aac.auth_method" "MutualTLS"
                "aac.frequency" "Realtime"
                "aac.direction" "Outbound"
            }
        }
        sys_screening_vendor -> sys_data_ingest "NICE Actimize return feed" "SFTP" "partner-file" {
            properties {
                "aac.interface_id" "INT-SCREENING-VENDOR-RETURN"
                "aac.kind" "partner-file"
                "aac.integration_style" "Batch"
                "aac.auth_method" "KeyPair"
                "aac.frequency" "Daily"
                "aac.direction" "Inbound"
            }
        }
        sys_lending_api -> ts_aws_privatelink "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_obaff_egress -> ts_gcp_ncc "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_screening_egress -> ts_aws_privatelink "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_screening_egress -> ts_aws_tgw "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_alb -> ts_net_sub_lend_pub_a "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_alb -> ts_net_sub_lend_pub_b "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_web -> ts_net_sub_lend_app_a "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_web -> ts_net_sub_lend_app_b "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_api -> ts_net_sub_lend_app_a "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_api -> ts_net_sub_lend_app_b "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_worker -> ts_net_sub_lend_app_a "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_worker -> ts_net_sub_lend_app_b "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_db -> ts_net_sub_lend_data_a "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_db -> ts_net_sub_lend_data_b "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_lending_bucket -> ts_net_sub_lend_data_a "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_screening_gateway -> ts_net_vpc_riskops "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_screening_egress -> ts_net_vpc_shared "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_core_ledger -> ts_onprem_dc "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_auth_switch -> ts_onprem_dc "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        sys_statements -> ts_onprem_dc "system uses tech service" {
            properties {
                "aac.relation" "system_uses_tech_service"
            }
        }
        prd_card_servicing -> sys_cardsvc_api "product includes system" {
            properties {
                "aac.relation" "product_includes_system"
            }
        }
        prd_card_servicing -> sys_cardsvc_web "product includes system" {
            properties {
                "aac.relation" "product_includes_system"
            }
        }
        prd_card_servicing -> sys_cardsvc_store "product includes system" {
            properties {
                "aac.relation" "product_includes_system"
            }
        }
        prd_card_servicing -> sys_cardsvc_events "product includes system" {
            properties {
                "aac.relation" "product_includes_system"
            }
        }
        act_applicant -> sys_lending_web "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Applies"
            }
        }
        act_underwriter -> sys_lending_web "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Reviews referrals"
            }
        }
        act_cardholder -> sys_cardsvc_web "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Self-service"
            }
        }
        act_cardholder -> sys_statements "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Receives statements"
            }
        }
        act_servicing_agent -> sys_crm "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Handles cases"
            }
        }
        act_servicing_agent -> sys_disputes_saas "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Raises disputes"
            }
        }
        act_collections_agent -> sys_collect_web "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Works arrears"
            }
        }
        act_merchant -> sys_auth_switch "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Presents transactions"
            }
        }
        act_card_scheme -> sys_auth_switch "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Carries authorization"
            }
        }
        act_regulator -> sys_reg_reporting "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Receives returns"
            }
        }
        act_cardholder -> sys_mobile "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Mobile self-service"
            }
        }
        act_cardholder -> sys_ivr "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Voice self-service"
            }
        }
        act_servicing_agent -> sys_contact "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Agent desktop"
            }
        }
        act_collections_agent -> sys_dialer "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Outbound campaigns"
            }
        }
        act_underwriter -> sys_orig_decision "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Manual review queue"
            }
        }
        act_underwriter -> sys_credit_data "actor uses system" {
            properties {
                "aac.relation" "actor_uses_system"
                "aac.interaction" "Strategy analysis"
            }
        }
        ts_net_dx -> ts_onprem_dc "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "Direct Connect"
            }
        }
        ts_net_vpn -> ts_onprem_dc "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "IPsec backup"
            }
        }
        ts_aws_tgw -> ts_net_dx "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "DX gateway"
            }
        }
        ts_aws_tgw -> ts_net_vpn "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "VPN attachment"
            }
        }
        ts_aws_tgw -> ts_net_vpc_shared "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "VPC attachment"
            }
        }
        ts_aws_tgw -> ts_net_vpc_lending "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "VPC attachment"
            }
        }
        ts_aws_tgw -> ts_net_vpc_riskops "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "VPC attachment"
            }
        }
        ts_aws_tgw -> ts_net_vpc_lending_dr "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "VPC attachment (DR)"
            }
        }
        ts_net_vpc_shared -> ts_net_route53 "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "resolver endpoints"
            }
        }
        ts_net_vpc_shared -> ts_aws_privatelink "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "endpoint services"
            }
        }
        ts_net_vpc_lending -> ts_net_sub_lend_pub_a "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnet"
            }
        }
        ts_net_vpc_lending -> ts_net_sub_lend_pub_b "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnet"
            }
        }
        ts_net_vpc_lending -> ts_net_sub_lend_app_a "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnet"
            }
        }
        ts_net_vpc_lending -> ts_net_sub_lend_app_b "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnet"
            }
        }
        ts_net_vpc_lending -> ts_net_sub_lend_data_a "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnet"
            }
        }
        ts_net_vpc_lending -> ts_net_sub_lend_data_b "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnet"
            }
        }
        ts_net_sub_lend_pub_a -> ts_net_igw_lending "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "default route"
            }
        }
        ts_net_sub_lend_pub_b -> ts_net_igw_lending "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "default route"
            }
        }
        ts_net_sub_lend_app_a -> ts_net_nat_lend_a "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "egress route"
            }
        }
        ts_net_sub_lend_app_b -> ts_net_nat_lend_b "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "egress route"
            }
        }
        ts_net_nat_lend_a -> ts_net_igw_lending "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "egress route"
            }
        }
        ts_net_nat_lend_b -> ts_net_igw_lending "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "egress route"
            }
        }
        ts_net_vpc_lending -> ts_net_vpc_lending_dr "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "cross-region replication"
            }
        }
        ts_gcp_interconnect -> ts_onprem_dc "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "Dedicated Interconnect"
            }
        }
        ts_gcpnet_ha_vpn -> ts_onprem_dc "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "IPsec backup"
            }
        }
        ts_gcp_ncc -> ts_gcp_interconnect "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "VLAN attachment"
            }
        }
        ts_gcp_ncc -> ts_gcpnet_ha_vpn "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "VPN spoke"
            }
        }
        ts_gcp_ncc -> ts_gcp_shared_vpc "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "VPC spoke"
            }
        }
        ts_gcp_shared_vpc -> ts_gcp_cloud_dns "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "DNS peering"
            }
        }
        ts_gcp_cloud_dns -> ts_onprem_dc "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "forwarding zone"
            }
        }
        ts_gcp_shared_vpc -> ts_gcpnet_proxy_sub_lend "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnetwork"
            }
        }
        ts_gcp_shared_vpc -> ts_gcpnet_sub_lend_app "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnetwork"
            }
        }
        ts_gcp_shared_vpc -> ts_gcpnet_sub_lend_data "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnetwork"
            }
        }
        ts_gcp_shared_vpc -> ts_gcpnet_sub_lend_app_dr "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnetwork (DR)"
            }
        }
        ts_gcpnet_sub_lend_app -> ts_gcpnet_nat_lend "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "egress route"
            }
        }
        ts_gcpnet_ext_lb_lend -> ts_gcpnet_proxy_sub_lend "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "proxy-only subnet"
            }
        }
        ts_gcpnet_ext_lb_lend -> ts_gcpnet_sub_lend_app "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "backend"
            }
        }
        ts_gcp_shared_vpc -> ts_gcpnet_sub_analytics_data "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnetwork"
            }
        }
        ts_gcpnet_sub_analytics_data -> ts_gcpnet_nat_analytics "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "egress route"
            }
        }
        ts_gcp_shared_vpc -> ts_gcpnet_sub_analytics_data_dr "tech service connects to" {
            properties {
                "aac.relation" "tech_service_connects_to"
                "aac.connection" "subnetwork (DR)"
            }
        }
        sys_identity_svc -> oi_identity_api "offers" {
            properties {
                "aac.field" "system_id"
            }
        }
        sys_core_ledger -> oi_ledger_queue "offers" {
            properties {
                "aac.field" "system_id"
            }
        }
        sys_cardsvc_api -> oi_cardsvc_api "offers" {
            properties {
                "aac.field" "system_id"
            }
        }
        sys_collect_api -> oi_collect_api "offers" {
            properties {
                "aac.field" "system_id"
            }
        }
        sys_lending_api -> oi_lending_api "offers" {
            properties {
                "aac.field" "system_id"
            }
        }
        sys_merchant_api -> oi_merchant_api "offers" {
            properties {
                "aac.field" "system_id"
            }
        }
        sys_posfin_api -> oi_posfin_api "offers" {
            properties {
                "aac.field" "system_id"
            }
        }
        sys_rewards_api -> oi_rewards_api "offers" {
            properties {
                "aac.field" "system_id"
            }
        }
    }

    views {
        systemLandscape system_context {
            title "System Context"
            description "External actors and the systems they use, and nothing else. Internal systems are left out on purpose, so the diagram stays small."
            include act_applicant
            include act_card_scheme
            include act_cardholder
            include act_collections_agent
            include act_merchant
            include act_regulator
            include act_servicing_agent
            include act_underwriter
            include sys_auth_switch
            include sys_cardsvc_web
            include sys_collect_web
            include sys_contact
            include sys_credit_data
            include sys_crm
            include sys_dialer
            include sys_disputes_saas
            include sys_ivr
            include sys_lending_web
            include sys_mobile
            include sys_orig_decision
            include sys_reg_reporting
            include sys_statements
            autoLayout lr
        }

        systemLandscape application_landscape {
            title "Application Landscape"
            description "All current and planned systems, grouped by business domain and shaded by criticality. New systems appear here automatically when they are added to the model."
            include sys_auth_switch
            include sys_cardsvc_api
            include sys_cardsvc_events
            include sys_cardsvc_store
            include sys_cardsvc_web
            include sys_collect_api
            include sys_collect_store
            include sys_collect_web
            include sys_core_ledger
            include sys_credit_bureau
            include sys_crm
            include sys_cust360_pipeline
            include sys_cust360_semantic
            include sys_data_ingest
            include sys_disputes_gateway
            include sys_disputes_saas
            include sys_identity_svc
            include sys_idv_egress
            include sys_idv_gateway
            include sys_idv_vendor
            include sys_idv_webhooks
            include sys_lending_alb
            include sys_lending_api
            include sys_lending_bucket
            include sys_lending_db
            include sys_lending_edge
            include sys_lending_hub
            include sys_lending_web
            include sys_lending_worker
            include sys_lendperf_pipeline
            include sys_lendperf_semantic
            include sys_merchant_api
            include sys_merchant_events
            include sys_merchant_store
            include sys_merchant_web
            include sys_obaff_egress
            include sys_obaff_gateway
            include sys_obaff_vendor
            include sys_obaff_webhooks
            include sys_posfin_api
            include sys_posfin_db
            include sys_posfin_events
            include sys_posfin_web
            include sys_reg_reporting
            include sys_rewards_api
            include sys_rewards_events
            include sys_rewards_store
            include sys_rewards_web
            include sys_rewards_worker
            include sys_screening_egress
            include sys_screening_federation
            include sys_screening_gateway
            include sys_screening_vendor
            include sys_siem
            include sys_statements
            autoLayout lr
        }

        systemLandscape product_card_servicing {
            title "Card Servicing in Context"
            description "The Card Servicing product, the systems it is made of, and everything one interface away from them. The scope follows the product relationship, so it stays correct whether the product was generated, imported or written by hand."
            include oi_cardsvc_api
            include oi_identity_api
            include oi_ledger_queue
            include prd_card_servicing
            include sys_cardsvc_api
            include sys_cardsvc_events
            include sys_cardsvc_store
            include sys_cardsvc_web
            include sys_core_ledger
            include sys_data_ingest
            include sys_identity_svc
            include sys_ivr
            include sys_mobile
            autoLayout lr
        }

        systemLandscape dr_topology {
            title "Disaster Recovery Topology"
            description "Primary and recovery regions side by side, with the replication paths between them. Anything in the primary region with no connection to the recovery region would not survive a regional outage."
            include ts_aws_privatelink
            include ts_aws_tgw
            include ts_gcp_cloud_dns
            include ts_gcp_interconnect
            include ts_gcp_ncc
            include ts_gcp_shared_vpc
            include ts_gcpnet_ha_vpn
            include ts_gcpnet_proxy_sub_lend
            include ts_gcpnet_sub_analytics_data
            include ts_gcpnet_sub_analytics_data_dr
            include ts_gcpnet_sub_lend_app
            include ts_gcpnet_sub_lend_app_dr
            include ts_gcpnet_sub_lend_data
            include ts_net_dx
            include ts_net_route53
            include ts_net_sub_lend_app_a
            include ts_net_sub_lend_app_b
            include ts_net_sub_lend_data_a
            include ts_net_sub_lend_data_b
            include ts_net_sub_lend_pub_a
            include ts_net_sub_lend_pub_b
            include ts_net_vpc_lending
            include ts_net_vpc_lending_dr
            include ts_net_vpc_riskops
            include ts_net_vpc_shared
            include ts_net_vpn
            include ts_onprem_dc
            autoLayout lr
        }

        systemLandscape multi_az_deployment {
            title "Multi-AZ Deployment"
            description "One workload account laid out for a resilience review: region, then availability zone, then tier. Each tier should appear in both zones. A tier that appears in only one zone is a resilience gap."
            include sys_lending_alb
            include sys_lending_api
            include sys_lending_bucket
            include sys_lending_db
            include sys_lending_web
            include sys_lending_worker
            include ts_net_nat_lend_a
            include ts_net_nat_lend_b
            include ts_net_sub_lend_app_a
            include ts_net_sub_lend_app_b
            include ts_net_sub_lend_data_a
            include ts_net_sub_lend_data_b
            include ts_net_sub_lend_pub_a
            include ts_net_sub_lend_pub_b
            autoLayout tb
        }

        systemLandscape network_topology {
            title "Network Topology"
            description "The network layer: VPCs, subnets, gateways and the connections back to the data center, grouped by cloud account and region. The transit hub is shown between the workload accounts."
            include ts_aws_privatelink
            include ts_aws_tgw
            include ts_gcp_cloud_dns
            include ts_gcp_interconnect
            include ts_gcp_ncc
            include ts_gcp_shared_vpc
            include ts_gcpnet_ext_lb_lend
            include ts_gcpnet_ha_vpn
            include ts_gcpnet_nat_analytics
            include ts_gcpnet_nat_lend
            include ts_gcpnet_proxy_sub_lend
            include ts_gcpnet_sub_analytics_data
            include ts_gcpnet_sub_analytics_data_dr
            include ts_gcpnet_sub_lend_app
            include ts_gcpnet_sub_lend_app_dr
            include ts_gcpnet_sub_lend_data
            include ts_net_dx
            include ts_net_igw_lending
            include ts_net_nat_lend_a
            include ts_net_nat_lend_b
            include ts_net_route53
            include ts_net_sub_lend_app_a
            include ts_net_sub_lend_app_b
            include ts_net_sub_lend_data_a
            include ts_net_sub_lend_data_b
            include ts_net_sub_lend_pub_a
            include ts_net_sub_lend_pub_b
            include ts_net_vpc_lending
            include ts_net_vpc_lending_dr
            include ts_net_vpc_riskops
            include ts_net_vpc_shared
            include ts_net_vpn
            include ts_onprem_dc
            autoLayout tb
        }

        systemLandscape tiered_architecture {
            title "Tiered Architecture"
            description "Systems arranged by tier: edge, public, application, data, shared services and on-premise. The tier is a field on each system, not a layout choice. Traffic should cross one boundary at a time; anywhere it does not is worth a look."
            include oi_cardsvc_api
            include oi_collect_api
            include oi_identity_api
            include oi_ledger_queue
            include oi_lending_api
            include oi_merchant_api
            include oi_posfin_api
            include oi_rewards_api
            include sys_auth_switch
            include sys_cardsvc_api
            include sys_cardsvc_store
            include sys_cardsvc_web
            include sys_collect_api
            include sys_collect_store
            include sys_collect_web
            include sys_core_ledger
            include sys_credit_bureau
            include sys_crm
            include sys_data_ingest
            include sys_disputes_gateway
            include sys_disputes_saas
            include sys_identity_svc
            include sys_idv_egress
            include sys_idv_gateway
            include sys_idv_vendor
            include sys_idv_webhooks
            include sys_lending_alb
            include sys_lending_api
            include sys_lending_bucket
            include sys_lending_db
            include sys_lending_edge
            include sys_lending_hub
            include sys_lending_web
            include sys_lending_worker
            include sys_lendperf_pipeline
            include sys_lendperf_semantic
            include sys_merchant_api
            include sys_merchant_store
            include sys_merchant_web
            include sys_obaff_egress
            include sys_obaff_gateway
            include sys_obaff_vendor
            include sys_obaff_webhooks
            include sys_posfin_api
            include sys_posfin_db
            include sys_posfin_web
            include sys_reg_reporting
            include sys_rewards_api
            include sys_rewards_store
            include sys_rewards_web
            include sys_rewards_worker
            include sys_screening_egress
            include sys_screening_federation
            include sys_screening_gateway
            include sys_screening_vendor
            include sys_siem
            include sys_statements
            autoLayout tb
        }

        systemLandscape hosting_estate {
            title "Where the Estate Runs"
            description "The same systems as the Application Landscape, grouped by where they are hosted. The on-premise column is the migration backlog. Connections between columns are the integrations that make moving a system harder."
            include sys_auth_switch
            include sys_cardsvc_api
            include sys_cardsvc_events
            include sys_cardsvc_store
            include sys_cardsvc_web
            include sys_collect_api
            include sys_collect_store
            include sys_collect_web
            include sys_core_ledger
            include sys_credit_bureau
            include sys_crm
            include sys_cust360_pipeline
            include sys_cust360_semantic
            include sys_data_ingest
            include sys_disputes_gateway
            include sys_disputes_saas
            include sys_identity_svc
            include sys_idv_egress
            include sys_idv_gateway
            include sys_idv_vendor
            include sys_idv_webhooks
            include sys_lending_alb
            include sys_lending_api
            include sys_lending_bucket
            include sys_lending_db
            include sys_lending_edge
            include sys_lending_hub
            include sys_lending_web
            include sys_lending_worker
            include sys_lendperf_pipeline
            include sys_lendperf_semantic
            include sys_merchant_api
            include sys_merchant_events
            include sys_merchant_store
            include sys_merchant_web
            include sys_obaff_egress
            include sys_obaff_gateway
            include sys_obaff_vendor
            include sys_obaff_webhooks
            include sys_posfin_api
            include sys_posfin_db
            include sys_posfin_events
            include sys_posfin_web
            include sys_reg_reporting
            include sys_rewards_api
            include sys_rewards_events
            include sys_rewards_store
            include sys_rewards_web
            include sys_rewards_worker
            include sys_screening_egress
            include sys_screening_federation
            include sys_screening_gateway
            include sys_screening_vendor
            include sys_siem
            include sys_statements
            autoLayout tb
        }

        systemLandscape onboarding__prd_card_servicing {
            title "Card Servicing — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include oi_cardsvc_api
            include oi_identity_api
            include oi_ledger_queue
            include sys_cardsvc_api
            include sys_cardsvc_events
            include sys_cardsvc_store
            include sys_cardsvc_web
            include sys_core_ledger
            include sys_data_ingest
            include sys_identity_svc
            include sys_ivr
            include sys_mobile
            autoLayout tb
        }

        systemLandscape onboarding__prd_collections_workspace {
            title "Collections Workspace — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include oi_collect_api
            include oi_identity_api
            include oi_ledger_queue
            include sys_collect_api
            include sys_collect_store
            include sys_collect_web
            include sys_core_ledger
            include sys_dialer
            include sys_doc
            include sys_identity_svc
            autoLayout tb
        }

        systemLandscape onboarding__prd_customer_360 {
            title "Customer 360 — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include sys_cust360_pipeline
            include sys_cust360_semantic
            include sys_data_ingest
            include sys_reg_reporting
            autoLayout tb
        }

        systemLandscape onboarding__prd_disputes {
            title "Dispute Management — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include sys_core_ledger
            include sys_crm
            include sys_data_ingest
            include sys_disputes_gateway
            include sys_disputes_saas
            autoLayout tb
        }

        systemLandscape onboarding__prd_identity {
            title "Customer Identity Service — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include oi_identity_api
            include sys_cardsvc_api
            include sys_collect_api
            include sys_identity_svc
            include sys_idv_gateway
            include sys_idv_webhooks
            include sys_lending_api
            autoLayout tb
        }

        systemLandscape onboarding__prd_idv {
            title "Identity Document Verification — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include sys_identity_svc
            include sys_idv_egress
            include sys_idv_gateway
            include sys_idv_vendor
            include sys_idv_webhooks
            autoLayout tb
        }

        systemLandscape onboarding__prd_installment_lending {
            title "Installment Lending — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include oi_identity_api
            include oi_ledger_queue
            include oi_lending_api
            include sys_core_ledger
            include sys_credit_bureau
            include sys_crm
            include sys_data_ingest
            include sys_identity_svc
            include sys_lending_alb
            include sys_lending_api
            include sys_lending_bucket
            include sys_lending_db
            include sys_lending_edge
            include sys_lending_hub
            include sys_lending_web
            include sys_lending_worker
            autoLayout tb
        }

        systemLandscape onboarding__prd_lending_performance {
            title "Lending Portfolio Performance — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include sys_lendperf_pipeline
            include sys_lendperf_semantic
            include sys_posfin_events
            include sys_reg_reporting
            autoLayout tb
        }

        systemLandscape onboarding__prd_merchant_portal {
            title "Merchant Portal — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include oi_merchant_api
            include sys_merchant_api
            include sys_merchant_events
            include sys_merchant_store
            include sys_merchant_web
            autoLayout tb
        }

        systemLandscape onboarding__prd_ob_affordability {
            title "Open Banking Affordability — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include sys_obaff_egress
            include sys_obaff_gateway
            include sys_obaff_vendor
            include sys_obaff_webhooks
            include sys_posfin_api
            autoLayout tb
        }

        systemLandscape onboarding__prd_pos_finance {
            title "Point-of-Sale Finance — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include oi_posfin_api
            include sys_lendperf_pipeline
            include sys_obaff_gateway
            include sys_obaff_webhooks
            include sys_posfin_api
            include sys_posfin_db
            include sys_posfin_events
            include sys_posfin_web
            autoLayout tb
        }

        systemLandscape onboarding__prd_rewards {
            title "Rewards Redemption — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include oi_ledger_queue
            include oi_rewards_api
            include sys_core_ledger
            include sys_rewards_api
            include sys_rewards_events
            include sys_rewards_store
            include sys_rewards_web
            include sys_rewards_worker
            autoLayout tb
        }

        systemLandscape onboarding__prd_screening {
            title "NICE Actimize Screening — Onboarding"
            description "What onboarding this product creates, nested by account, region and network tier. Everything inside the boundaries comes from the product's shape; the systems outside are the ones it must connect to, which are usually the long- lead items. For a bought product, the vendor's environment sits outside our accounts."
            include sys_auth_switch
            include sys_data_ingest
            include sys_screening_egress
            include sys_screening_federation
            include sys_screening_gateway
            include sys_screening_vendor
            include sys_siem
            autoLayout tb
        }

        styles {
            element "Active" {
                background #dcfce7
                stroke #16a34a
                color #0f172a
            }
            element "Capability" {
                background #fee2e2
                stroke #dc2626
                color #0f172a
            }
            element "Control" {
                background #cffafe
                stroke #06b6d4
                color #0f172a
            }
            element "Data Asset" {
                background #fff7ed
                stroke #ea580c
                color #0f172a
            }
            element "Edge" {
                background #cffafe
                stroke #06b6d4
                color #0f172a
            }
            element "External system" {
                background #cffafe
                stroke #06b6d4
                color #0f172a
            }
            element "High" {
                background #fee2e2
                stroke #dc2626
                color #0f172a
            }
            element "Interface" {
                background #eef2ff
                stroke #6366f1
                color #0f172a
            }
            element "Medium" {
                background #fef3c7
                stroke #f59e0b
                color #0f172a
            }
            element "On-prem" {
                background #f1f5f9
                stroke #64748b
                color #0f172a
            }
            element "Org Unit" {
                background #cffafe
                stroke #06b6d4
                color #0f172a
            }
            element "Organization" {
                background #fef3c7
                stroke #f59e0b
                color #0f172a
            }
            element "Person" {
                background #eef2ff
                stroke #6366f1
                color #0f172a
            }
            element "Planned" {
                background #eef2ff
                stroke #6366f1
                color #0f172a
            }
            element "Policy" {
                background #fee2e2
                stroke #dc2626
                color #0f172a
            }
            element "Private-App" {
                background #fee2e2
                stroke #dc2626
                color #0f172a
            }
            element "Private-Data" {
                background #fff7ed
                stroke #ea580c
                color #0f172a
            }
            element "Product" {
                background #fdf2f8
                stroke #db2777
                color #0f172a
            }
            element "Public" {
                background #fae8ff
                stroke #a855f7
                color #0f172a
            }
            element "Regulator" {
                background #fae8ff
                stroke #a855f7
                color #0f172a
            }
            element "Role" {
                background #dcfce7
                stroke #16a34a
                color #0f172a
            }
            element "Shared-Services" {
                background #fdf2f8
                stroke #db2777
                color #0f172a
            }
            element "System" {
                background #fdf2f8
                stroke #db2777
                color #0f172a
            }
            element "Technology Service" {
                background #fff7ed
                stroke #ea580c
                color #0f172a
            }
            element "default" {
                background #f1f5f9
                stroke #64748b
                color #0f172a
            }
        }
    }
}
