# Policies, Their Controls, and Their Subjects

Each policy, the controls that implement it, and the systems and data it applies to directly. A policy with subjects but no controls is only a statement of intent; a policy with controls but no subjects is enforced somewhere the model has not recorded.

![Policies, Their Controls, and Their Subjects](../svg/policy-landscape.svg)

| From | | To | Detail |
|---|---|---|---|
| Card account master <br>`DA-CARD-ACCOUNT` | data subject to policy | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | binds |
| Card account master <br>`DA-CARD-ACCOUNT` | data subject to policy | Records Retention & Disposition Policy <br>`POL-RECORDS` | binds |
| Card transaction history <br>`DA-TRANSACTION` | data subject to policy | Records Retention & Disposition Policy <br>`POL-RECORDS` | binds |
| Customer 360 curated dataset <br>`DA-CUST360-CURATED` | data subject to policy | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | binds |
| Customer profile <br>`DA-CUSTOMER-PROFILE` | data subject to policy | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | binds |
| Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | data subject to policy | Records Retention & Disposition Policy <br>`POL-RECORDS` | binds |
| Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | data subject to policy | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | binds |
| Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | data subject to policy | Third-Party Risk Management Policy <br>`POL-TPRM` | binds |
| NICE Actimize Screening outcomes <br>`DA-SCREENING-OUTCOMES` | data subject to policy | Records Retention & Disposition Policy <br>`POL-RECORDS` | binds |
| NICE Actimize Screening outcomes <br>`DA-SCREENING-OUTCOMES` | data subject to policy | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | binds |
| Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | policy id | Fair Lending & Credit Decision Policy <br>`POL-FAIR-LEND` | gives effect to |
| Application completeness and disclosure <br>`CTL-APP-INTAKE` | policy id | Fair Lending & Credit Decision Policy <br>`POL-FAIR-LEND` | gives effect to |
| Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | policy id | Technology Change Management Policy <br>`POL-CHANGE` | gives effect to |
| Bureau furnishing accuracy <br>`CTL-BUREAU-ACC` | policy id | Fair Lending & Credit Decision Policy <br>`POL-FAIR-LEND` | gives effect to |
| Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | policy id | Information Security Policy <br>`POL-INFOSEC` | gives effect to |
| Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | policy id | Information Security Policy <br>`POL-INFOSEC` | gives effect to |
| Charge-off timing to policy <br>`CTL-CHARGEOFF-TIME` | policy id | Collections Conduct Policy <br>`POL-COLLECT` | gives effect to |
| Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | policy id | Third-Party Risk Management Policy <br>`POL-TPRM` | gives effect to |
| Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | policy id | Records Retention & Disposition Policy <br>`POL-RECORDS` | gives effect to |
| Collections contact limits <br>`CTL-CONTACT-LIM` | policy id | Collections Conduct Policy <br>`POL-COLLECT` | gives effect to |
| Complaint regulatory routing <br>`CTL-COMPLAINT-REG` | policy id | Marketing Review & UDAAP Policy <br>`POL-MKT-UDAAP` | gives effect to |
| Consumer privacy request fulfillment <br>`CTL-PRIV-REQ` | policy id | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | gives effect to |
| Conversion balance and record verification <br>`CTL-CONV-VERIFY` | policy id | Third-Party Risk Management Policy <br>`POL-TPRM` | gives effect to |
| Cycle assessment validation <br>`CTL-CYCLE-VALID` | policy id | Error Resolution & Billing Dispute Policy <br>`POL-ERROR-RES` | gives effect to |
| Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | policy id | Records Retention & Disposition Policy <br>`POL-RECORDS` | gives effect to |
| Dispute acknowledgment timeliness <br>`CTL-REGE-ACK` | policy id | Error Resolution & Billing Dispute Policy <br>`POL-ERROR-RES` | gives effect to |
| Dispute determination timeliness and notice <br>`CTL-REGE-DETERM` | policy id | Error Resolution & Billing Dispute Policy <br>`POL-ERROR-RES` | gives effect to |
| Fraud alert handling service level <br>`CTL-FRAUD-SLA` | policy id | Error Resolution & Billing Dispute Policy <br>`POL-ERROR-RES` | gives effect to |
| Furnishing and bucketing reconciliation <br>`CTL-METRO2-RECON` | policy id | Fair Lending & Credit Decision Policy <br>`POL-FAIR-LEND` | gives effect to |
| Ingestion data quality gate <br>`CTL-DQ-GATE` | policy id | Records Retention & Disposition Policy <br>`POL-RECORDS` | gives effect to |
| Marketing material compliance review <br>`CTL-MKT-REVIEW` | policy id | Marketing Review & UDAAP Policy <br>`POL-MKT-UDAAP` | gives effect to |
| Masked data outside production <br>`CTL-MASK-NONPROD` | policy id | Information Security Policy <br>`POL-INFOSEC` | gives effect to |
| Notice content and delivery evidence <br>`CTL-NOTICE-CONTENT` | policy id | Error Resolution & Billing Dispute Policy <br>`POL-ERROR-RES` | gives effect to |
| Payment posting timeliness <br>`CTL-PMT-POSTING` | policy id | Error Resolution & Billing Dispute Policy <br>`POL-ERROR-RES` | gives effect to |
| Periodic access certification <br>`CTL-ACCESS-CERT` | policy id | Information Security Policy <br>`POL-INFOSEC` | gives effect to |
| Production change approval <br>`CTL-CHG-APPROVAL` | policy id | Technology Change Management Policy <br>`POL-CHANGE` | gives effect to |
| Provisional credit within regulatory window <br>`CTL-REGE-PROVCR` | policy id | Error Resolution & Billing Dispute Policy <br>`POL-ERROR-RES` | gives effect to |
| Recovery test against committed objectives <br>`CTL-DR-TEST` | policy id | Technology Change Management Policy <br>`POL-CHANGE` | gives effect to |
| Regulatory change implementation tracking <br>`CTL-REGCHANGE-TRACK` | policy id | BSA/AML & Sanctions Policy <br>`POL-BSA-AML` | gives effect to |
| Regulatory report certification <br>`CTL-REGRPT-CERT` | policy id | Records Retention & Disposition Policy <br>`POL-RECORDS` | gives effect to |
| Retention schedule enforcement <br>`CTL-RETENTION` | policy id | Records Retention & Disposition Policy <br>`POL-RECORDS` | gives effect to |
| Sanctions and watchlist screening <br>`CTL-SANCTIONS` | policy id | BSA/AML & Sanctions Policy <br>`POL-BSA-AML` | gives effect to |
| Security incident response execution <br>`CTL-IR-PLAYBOOK` | policy id | Information Security Policy <br>`POL-INFOSEC` | gives effect to |
| Servicemember protections screening <br>`CTL-SCRA-MLA` | policy id | Fair Lending & Credit Decision Policy <br>`POL-FAIR-LEND` | gives effect to |
| Settlement funding confirmation <br>`CTL-FUNDING-CONF` | policy id | Records Retention & Disposition Policy <br>`POL-RECORDS` | gives effect to |
| Statutory collections notices <br>`CTL-FDCPA-NOTICE` | policy id | Collections Conduct Policy <br>`POL-COLLECT` | gives effect to |
| Suspicious activity investigation and filing <br>`CTL-SAR-FILING` | policy id | BSA/AML & Sanctions Policy <br>`POL-BSA-AML` | gives effect to |
| Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | policy id | Third-Party Risk Management Policy <br>`POL-TPRM` | gives effect to |
| Treatment strategy approval <br>`CTL-TREATMENT-APPR` | policy id | Fair Lending & Credit Decision Policy <br>`POL-FAIR-LEND` | gives effect to |
| Vulnerability remediation service level <br>`CTL-VULN-SLA` | policy id | Information Security Policy <br>`POL-INFOSEC` | gives effect to |
| Authorization Switch <br>`SYS-AUTH-SWITCH` | system subject to policy | Information Security Policy <br>`POL-INFOSEC` | binds |
| Authorization Switch <br>`SYS-AUTH-SWITCH` | system subject to policy | Technology Change Management Policy <br>`POL-CHANGE` | binds |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system subject to policy | Collections Conduct Policy <br>`POL-COLLECT` | binds |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system subject to policy | Information Security Policy <br>`POL-INFOSEC` | binds |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system subject to policy | Technology Change Management Policy <br>`POL-CHANGE` | binds |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system subject to policy | Records Retention & Disposition Policy <br>`POL-RECORDS` | binds |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system subject to policy | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | binds |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system subject to policy | Records Retention & Disposition Policy <br>`POL-RECORDS` | binds |
| Customer Identity Service <br>`SYS-IDENTITY-SVC` | system subject to policy | Information Security Policy <br>`POL-INFOSEC` | binds |
| Dynamics 365 Customer Service <br>`SYS-CRM` | system subject to policy | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | binds |
| Experian Credit Bureau <br>`SYS-CREDIT-BUREAU` | system subject to policy | Fair Lending & Credit Decision Policy <br>`POL-FAIR-LEND` | binds |
| Experian Credit Bureau <br>`SYS-CREDIT-BUREAU` | system subject to policy | Third-Party Risk Management Policy <br>`POL-TPRM` | binds |
| Identity Document Verification <br>`SYS-IDV-VENDOR` | system subject to policy | Third-Party Risk Management Policy <br>`POL-TPRM` | binds |
| Identity Document Verification <br>`SYS-IDV-VENDOR` | system subject to policy | BSA/AML & Sanctions Policy <br>`POL-BSA-AML` | binds |
| Installment Lending Integration Hub <br>`SYS-LENDING-HUB` | system subject to policy | Technology Change Management Policy <br>`POL-CHANGE` | binds |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | system subject to policy | Third-Party Risk Management Policy <br>`POL-TPRM` | binds |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | system subject to policy | BSA/AML & Sanctions Policy <br>`POL-BSA-AML` | binds |
| NICE Actimize Screening Identity Federation <br>`SYS-SCREENING-FEDERATION` | system subject to policy | Information Security Policy <br>`POL-INFOSEC` | binds |
| Open Banking Affordability <br>`SYS-OBAFF-VENDOR` | system subject to policy | Third-Party Risk Management Policy <br>`POL-TPRM` | binds |
| Open Banking Affordability <br>`SYS-OBAFF-VENDOR` | system subject to policy | Consumer Privacy & Data Handling Policy <br>`POL-PRIVACY` | binds |
| Open Banking Affordability <br>`SYS-OBAFF-VENDOR` | system subject to policy | Fair Lending & Credit Decision Policy <br>`POL-FAIR-LEND` | binds |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | system subject to policy | Third-Party Risk Management Policy <br>`POL-TPRM` | binds |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | system subject to policy | Error Resolution & Billing Dispute Policy <br>`POL-ERROR-RES` | binds |
| Security Monitoring <br>`SYS-SIEM` | system subject to policy | Information Security Policy <br>`POL-INFOSEC` | binds |
| Security Monitoring <br>`SYS-SIEM` | system subject to policy | Records Retention & Disposition Policy <br>`POL-RECORDS` | binds |

75 relationships across 70 entities. Generated from the model; this is a report rather than a diagram, so it is a table.
