# Controls and Where They Are Enforced

Every control in the register and where it is enforced: the systems and data assets it governs directly, and the capabilities it governs through recorded processes. A row with a capability but no system means the model does not say which system enforces that control.

![Controls and Where They Are Enforced](../svg/control-coverage.svg)

| From | | To | Detail |
|---|---|---|---|
| Account Establishment & Card Issuance <br>`CAP-ORIG-06` | capability governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | Process |
| Account Maintenance & Servicing Requests <br>`CAP-SERV-02` | capability governed by control | Servicemember protections screening <br>`CTL-SCRA-MLA` | Process |
| Adverse Action & Notice Generation <br>`CAP-ORIG-05` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Process |
| Ancillary Product & Dealer Reserve Administration <br>`CAP-LEND-07` | capability governed by control | Ancillary product refund on early termination <br>`CTL-ANCILLARY-REFUND` | Process |
| Ancillary Product & Dealer Reserve Administration <br>`CAP-LEND-07` | capability governed by control | Dealer program and markup monitoring <br>`CTL-DEALER-MON` | Process |
| Application Capture <br>`CAP-ORIG-01` | capability governed by control | Application completeness and disclosure <br>`CTL-APP-INTAKE` | Process |
| Application Capture <br>`CAP-ORIG-01` | capability governed by control | Servicemember protections screening <br>`CTL-SCRA-MLA` | Process |
| Application Fraud Screening <br>`CAP-ORIG-03` | capability governed by control | Application completeness and disclosure <br>`CTL-APP-INTAKE` | Process |
| Authorization Fraud Screening <br>`CAP-PAY-01-02` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Process |
| Authorization Fraud Screening <br>`CAP-PAY-01-02` | capability governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | Process |
| Authorization Processing <br>`CAP-PAY-01` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Process |
| Authorization Processing <br>`CAP-PAY-01` | capability governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | Process |
| Authorization Processing <br>`CAP-PAY-01` | capability governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | Descendant |
| Authorization Strategy Management <br>`CAP-CRED-06` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Process |
| Authorization Strategy Management <br>`CAP-CRED-06` | capability governed by control | Treatment strategy approval <br>`CTL-TREATMENT-APPR` | Process |
| Bankruptcy Processing <br>`CAP-COLL-06-01` | capability governed by control | Statutory collections notices <br>`CTL-FDCPA-NOTICE` | Process |
| Bankruptcy, Deceased & Legal Account Handling <br>`CAP-COLL-06` | capability governed by control | Statutory collections notices <br>`CTL-FDCPA-NOTICE` | Process |
| Billing, Statements & Rewards <br>`CAP-BILL` | capability governed by control | Credit balance refund and escheatment <br>`CTL-CREDIT-BAL` | Descendant |
| Billing, Statements & Rewards <br>`CAP-BILL` | capability governed by control | Cycle assessment validation <br>`CTL-CYCLE-VALID` | Descendant |
| Broker Network & Issuance <br>`CAP-DEP-03-01` | capability governed by control | Brokered deposit position reconciliation <br>`CTL-BROKERED-RECON` | Process |
| Brokered CD Program Management <br>`CAP-DEP-03` | capability governed by control | Brokered deposit position reconciliation <br>`CTL-BROKERED-RECON` | Process |
| Brokered CD Settlement & Record Keeping <br>`CAP-DEP-03-02` | capability governed by control | Brokered deposit position reconciliation <br>`CTL-BROKERED-RECON` | Process |
| Business Continuity & Disaster Recovery <br>`CAP-TECH-05` | capability governed by control | Recovery test against committed objectives <br>`CTL-DR-TEST` | Process |
| Charge-off Processing <br>`CAP-COLL-04` | capability governed by control | Charge-off timing to policy <br>`CTL-CHARGEOFF-TIME` | Process |
| Chargeback & Representment Processing <br>`CAP-FRAUD-04` | capability governed by control | Dispute determination timeliness and notice <br>`CTL-REGE-DETERM` | Process |
| Chargeback Processing <br>`CAP-FRAUD-04-01` | capability governed by control | Dispute determination timeliness and notice <br>`CTL-REGE-DETERM` | Process |
| Clearing & Transaction Posting <br>`CAP-PAY-02` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Process |
| Client Program Configuration & Setup <br>`CAP-TPS-01` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Process |
| Client Reporting & Data Exchange <br>`CAP-TPS-03` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Process |
| Client Service Level & Performance Management <br>`CAP-PART-04` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Process |
| Co-Brand & Program Partner Management <br>`CAP-PART-05` | capability governed by control | Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | Process |
| Co-Brand & Program Partner Management <br>`CAP-PART-05` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Process |
| Collateral Remarketing & Deficiency Recovery <br>`CAP-LEND-06-02` | capability governed by control | Repossession and disposition notices <br>`CTL-REPO-NOTICE` | Process |
| Collateral, Title & Lien Management <br>`CAP-LEND-04` | capability governed by control | Lien perfection within policy window <br>`CTL-LIEN-PERFECT` | Process |
| Collateral, Title & Lien Management <br>`CAP-LEND-04` | capability governed by control | Title release within statutory deadline <br>`CTL-LIEN-RELEASE` | Process |
| Collections & Recovery <br>`CAP-COLL` | capability governed by control | Bureau furnishing accuracy <br>`CTL-BUREAU-ACC` | Descendant |
| Collections & Recovery <br>`CAP-COLL` | capability governed by control | Charge-off timing to policy <br>`CTL-CHARGEOFF-TIME` | Descendant |
| Collections & Recovery <br>`CAP-COLL` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Descendant |
| Collections & Recovery <br>`CAP-COLL` | capability governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | Descendant |
| Collections & Recovery <br>`CAP-COLL` | capability governed by control | Statutory collections notices <br>`CTL-FDCPA-NOTICE` | Descendant |
| Collections & Recovery <br>`CAP-COLL` | capability governed by control | Furnishing and bucketing reconciliation <br>`CTL-METRO2-RECON` | Descendant |
| Collections & Recovery <br>`CAP-COLL` | capability governed by control | Treatment strategy approval <br>`CTL-TREATMENT-APPR` | Descendant |
| Collections Compliance Oversight <br>`CAP-COLL-07` | capability governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | Process |
| Collections Compliance Oversight <br>`CAP-COLL-07` | capability governed by control | Statutory collections notices <br>`CTL-FDCPA-NOTICE` | Process |
| Complaint Capture & Resolution <br>`CAP-SERV-05` | capability governed by control | Complaint regulatory routing <br>`CTL-COMPLAINT-REG` | Process |
| Complaint Oversight & UDAAP Management <br>`CAP-RGOV-06` | capability governed by control | Complaint regulatory routing <br>`CTL-COMPLAINT-REG` | Process |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Ancillary product refund on early termination <br>`CTL-ANCILLARY-REFUND` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Application completeness and disclosure <br>`CTL-APP-INTAKE` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Dealer program and markup monitoring <br>`CTL-DEALER-MON` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Stipulations cleared before funding <br>`CTL-FUND-STIPS` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Settlement funding confirmation <br>`CTL-FUNDING-CONF` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Lien perfection within policy window <br>`CTL-LIEN-PERFECT` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Title release within statutory deadline <br>`CTL-LIEN-RELEASE` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Payment posting timeliness <br>`CTL-PMT-POSTING` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Repossession and disposition notices <br>`CTL-REPO-NOTICE` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Descendant |
| Consumer & Recreation Lending <br>`CAP-LEND` | capability governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | Descendant |
| Contract & SLA Management <br>`CAP-TPRM-02` | capability governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | Process |
| Correspondence & Notification Management <br>`CAP-SERV-04` | capability governed by control | Notice content and delivery evidence <br>`CTL-NOTICE-CONTENT` | Process |
| Correspondence & Notification Management <br>`CAP-SERV-04` | capability governed by control | Dispute determination timeliness and notice <br>`CTL-REGE-DETERM` | Process |
| Credential Authentication <br>`CAP-PAY-01-01` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Process |
| Credit & Limit Check <br>`CAP-PAY-01-03` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Process |
| Credit Balance Refund & Unclaimed Property <br>`CAP-BILL-06` | capability governed by control | Credit balance refund and escheatment <br>`CTL-CREDIT-BAL` | Process |
| Credit Bureau Reporting & Dispute Handling <br>`CAP-COLL-08` | capability governed by control | Bureau furnishing accuracy <br>`CTL-BUREAU-ACC` | Process |
| Credit Bureau Reporting & Dispute Handling <br>`CAP-COLL-08` | capability governed by control | Furnishing and bucketing reconciliation <br>`CTL-METRO2-RECON` | Process |
| Credit Decisioning & Portfolio Management <br>`CAP-CRED` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Descendant |
| Credit Decisioning & Portfolio Management <br>`CAP-CRED` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Descendant |
| Credit Decisioning & Portfolio Management <br>`CAP-CRED` | capability governed by control | Treatment strategy approval <br>`CTL-TREATMENT-APPR` | Descendant |
| Credit Line Assignment & Management <br>`CAP-CRED-03` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Process |
| Credit Strategy & Scorecard Management <br>`CAP-CRED-01` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Process |
| Customer Acquisition & Marketing <br>`CAP-ACQ` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Descendant |
| Customer Servicing & Care <br>`CAP-SERV` | capability governed by control | Bureau furnishing accuracy <br>`CTL-BUREAU-ACC` | Descendant |
| Customer Servicing & Care <br>`CAP-SERV` | capability governed by control | Complaint regulatory routing <br>`CTL-COMPLAINT-REG` | Descendant |
| Customer Servicing & Care <br>`CAP-SERV` | capability governed by control | Notice content and delivery evidence <br>`CTL-NOTICE-CONTENT` | Descendant |
| Customer Servicing & Care <br>`CAP-SERV` | capability governed by control | Dispute determination timeliness and notice <br>`CTL-REGE-DETERM` | Descendant |
| Customer Servicing & Care <br>`CAP-SERV` | capability governed by control | Servicemember protections screening <br>`CTL-SCRA-MLA` | Descendant |
| Cycle & Statement Generation <br>`CAP-BILL-02` | capability governed by control | Cycle assessment validation <br>`CTL-CYCLE-VALID` | Process |
| Data & Analytics Management <br>`CAP-DATA` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Descendant |
| Data & Analytics Management <br>`CAP-DATA` | capability governed by control | Conversion balance and record verification <br>`CTL-CONV-VERIFY` | Descendant |
| Data & Analytics Management <br>`CAP-DATA` | capability governed by control | Ingestion data quality gate <br>`CTL-DQ-GATE` | Descendant |
| Data & Analytics Management <br>`CAP-DATA` | capability governed by control | Regulatory report certification <br>`CTL-REGRPT-CERT` | Descendant |
| Data & Analytics Management <br>`CAP-DATA` | capability governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | Descendant |
| Data Protection & Cryptography <br>`CAP-SEC-04` | capability governed by control | Masked data outside production <br>`CTL-MASK-NONPROD` | Process |
| Data Protection & Cryptography <br>`CAP-SEC-04` | capability governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | Process |
| Data Quality Management <br>`CAP-DATA-03` | capability governed by control | Ingestion data quality gate <br>`CTL-DQ-GATE` | Process |
| Data Quality Management <br>`CAP-DATA-03` | capability governed by control | Regulatory report certification <br>`CTL-REGRPT-CERT` | Process |
| Data Sourcing & Integration <br>`CAP-DATA-02` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Process |
| Data Sourcing & Integration <br>`CAP-DATA-02` | capability governed by control | Conversion balance and record verification <br>`CTL-CONV-VERIFY` | Process |
| Data Sourcing & Integration <br>`CAP-DATA-02` | capability governed by control | Ingestion data quality gate <br>`CTL-DQ-GATE` | Process |
| Dealer Application Intake <br>`CAP-LEND-02-01` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Process |
| Dealer Application Intake <br>`CAP-LEND-02-01` | capability governed by control | Application completeness and disclosure <br>`CTL-APP-INTAKE` | Process |
| Dealer Application Intake <br>`CAP-LEND-02-01` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Process |
| Dealer Network & Program Management <br>`CAP-LEND-01` | capability governed by control | Dealer program and markup monitoring <br>`CTL-DEALER-MON` | Process |
| Dealer Network & Program Management <br>`CAP-LEND-01` | capability governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | Process |
| Delinquency Segmentation & Treatment Strategy <br>`CAP-COLL-01` | capability governed by control | Furnishing and bucketing reconciliation <br>`CTL-METRO2-RECON` | Process |
| Delinquency Segmentation & Treatment Strategy <br>`CAP-COLL-01` | capability governed by control | Treatment strategy approval <br>`CTL-TREATMENT-APPR` | Process |
| Deposit Account Opening <br>`CAP-DEP-02` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Process |
| Deposit Compliance & Insurance Administration <br>`CAP-DEP-05` | capability governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | Process |
| Deposit Product Management <br>`CAP-DEP-01` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Process |
| Deposit Products & Funding <br>`CAP-DEP` | capability governed by control | Brokered deposit position reconciliation <br>`CTL-BROKERED-RECON` | Descendant |
| Deposit Products & Funding <br>`CAP-DEP` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Descendant |
| Deposit Products & Funding <br>`CAP-DEP` | capability governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | Descendant |
| Deposit Products & Funding <br>`CAP-DEP` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Descendant |
| Deposit Products & Funding <br>`CAP-DEP` | capability governed by control | Deposit interest tax reporting <br>`CTL-TAX-REPORT` | Descendant |
| Deposit Servicing, Interest & Maturities <br>`CAP-DEP-04` | capability governed by control | Deposit interest tax reporting <br>`CTL-TAX-REPORT` | Process |
| Dispute Intake & Provisional Credit <br>`CAP-FRAUD-03` | capability governed by control | Dispute acknowledgment timeliness <br>`CTL-REGE-ACK` | Process |
| Dispute Intake & Provisional Credit <br>`CAP-FRAUD-03` | capability governed by control | Dispute determination timeliness and notice <br>`CTL-REGE-DETERM` | Process |
| Dispute Intake & Provisional Credit <br>`CAP-FRAUD-03` | capability governed by control | Provisional credit within regulatory window <br>`CTL-REGE-PROVCR` | Process |
| Fair Lending Monitoring <br>`CAP-RGOV-09` | capability governed by control | Fair lending testing <br>`CTL-FAIR-LEND-TEST` | Process |
| Finance, Treasury & Settlement Accounting <br>`CAP-FIN` | capability governed by control | Charge-off timing to policy <br>`CTL-CHARGEOFF-TIME` | Descendant |
| Finance, Treasury & Settlement Accounting <br>`CAP-FIN` | capability governed by control | Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | Descendant |
| Finance, Treasury & Settlement Accounting <br>`CAP-FIN` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Descendant |
| Finance, Treasury & Settlement Accounting <br>`CAP-FIN` | capability governed by control | Ingestion data quality gate <br>`CTL-DQ-GATE` | Descendant |
| Finance, Treasury & Settlement Accounting <br>`CAP-FIN` | capability governed by control | Settlement funding confirmation <br>`CTL-FUNDING-CONF` | Descendant |
| Finance, Treasury & Settlement Accounting <br>`CAP-FIN` | capability governed by control | Regulatory report certification <br>`CTL-REGRPT-CERT` | Descendant |
| Financial Crimes & BSA/AML Compliance <br>`CAP-RGOV-07` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Process |
| Financial Crimes & BSA/AML Compliance <br>`CAP-RGOV-07` | capability governed by control | Suspicious activity investigation and filing <br>`CTL-SAR-FILING` | Process |
| First-Party Fraud & Bust-Out Management <br>`CAP-FRAUD-08` | capability governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | Process |
| Fraud Case Investigation <br>`CAP-FRAUD-02` | capability governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | Process |
| Fraud, Disputes & Chargeback Management <br>`CAP-FRAUD` | capability governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | Descendant |
| Fraud, Disputes & Chargeback Management <br>`CAP-FRAUD` | capability governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | Descendant |
| Fraud, Disputes & Chargeback Management <br>`CAP-FRAUD` | capability governed by control | Security incident response execution <br>`CTL-IR-PLAYBOOK` | Descendant |
| Fraud, Disputes & Chargeback Management <br>`CAP-FRAUD` | capability governed by control | Dispute acknowledgment timeliness <br>`CTL-REGE-ACK` | Descendant |
| Fraud, Disputes & Chargeback Management <br>`CAP-FRAUD` | capability governed by control | Dispute determination timeliness and notice <br>`CTL-REGE-DETERM` | Descendant |
| Fraud, Disputes & Chargeback Management <br>`CAP-FRAUD` | capability governed by control | Provisional credit within regulatory window <br>`CTL-REGE-PROVCR` | Descendant |
| Funding & Liquidity Management <br>`CAP-FIN-03` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Process |
| Funding & Liquidity Management <br>`CAP-FIN-03` | capability governed by control | Settlement funding confirmation <br>`CTL-FUNDING-CONF` | Process |
| General Ledger & Financial Close <br>`CAP-FIN-01` | capability governed by control | Charge-off timing to policy <br>`CTL-CHARGEOFF-TIME` | Process |
| General Ledger & Financial Close <br>`CAP-FIN-01` | capability governed by control | Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | Process |
| Identity & Access Management <br>`CAP-SEC-01` | capability governed by control | Periodic access certification <br>`CTL-ACCESS-CERT` | Process |
| Identity & Access Management <br>`CAP-SEC-01` | capability governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | Process |
| Identity Theft & Account Takeover Response <br>`CAP-FRAUD-06` | capability governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | Process |
| Identity Theft & Account Takeover Response <br>`CAP-FRAUD-06` | capability governed by control | Security incident response execution <br>`CTL-IR-PLAYBOOK` | Process |
| Identity Verification & KYC/CIP <br>`CAP-ORIG-02` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Process |
| Indirect Application & Underwriting <br>`CAP-LEND-02` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Process |
| Indirect Application & Underwriting <br>`CAP-LEND-02` | capability governed by control | Application completeness and disclosure <br>`CTL-APP-INTAKE` | Process |
| Indirect Application & Underwriting <br>`CAP-LEND-02` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Process |
| Indirect Credit Decision & Counteroffer <br>`CAP-LEND-02-02` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Process |
| Information Security & Privacy <br>`CAP-SEC` | capability governed by control | Periodic access certification <br>`CTL-ACCESS-CERT` | Descendant |
| Information Security & Privacy <br>`CAP-SEC` | capability governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | Descendant |
| Information Security & Privacy <br>`CAP-SEC` | capability governed by control | Security incident response execution <br>`CTL-IR-PLAYBOOK` | Descendant |
| Information Security & Privacy <br>`CAP-SEC` | capability governed by control | Masked data outside production <br>`CTL-MASK-NONPROD` | Descendant |
| Information Security & Privacy <br>`CAP-SEC` | capability governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | Descendant |
| Information Security & Privacy <br>`CAP-SEC` | capability governed by control | Consumer privacy request fulfillment <br>`CTL-PRIV-REQ` | Descendant |
| Information Security & Privacy <br>`CAP-SEC` | capability governed by control | Vulnerability remediation service level <br>`CTL-VULN-SLA` | Descendant |
| Installment Loan Servicing <br>`CAP-LEND-05` | capability governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | Process |
| Installment Loan Servicing <br>`CAP-LEND-05` | capability governed by control | Payment posting timeliness <br>`CTL-PMT-POSTING` | Process |
| Interchange & Revenue Accounting <br>`CAP-FIN-02` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Process |
| Interest & Fee Assessment <br>`CAP-BILL-01` | capability governed by control | Cycle assessment validation <br>`CTL-CYCLE-VALID` | Process |
| Interest Accrual & Tax Reporting <br>`CAP-DEP-04-01` | capability governed by control | Deposit interest tax reporting <br>`CTL-TAX-REPORT` | Process |
| Internal Audit & Examination Management <br>`CAP-RGOV-05` | capability governed by control | Regulatory report certification <br>`CTL-REGRPT-CERT` | Process |
| ISO & Agent Program Management <br>`CAP-MERCH-01` | capability governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | Process |
| Legal Placement & Litigation <br>`CAP-COLL-06-03` | capability governed by control | Statutory collections notices <br>`CTL-FDCPA-NOTICE` | Process |
| Lien Perfection & Title Custody <br>`CAP-LEND-04-01` | capability governed by control | Lien perfection within policy window <br>`CTL-LIEN-PERFECT` | Process |
| Loan Boarding & Dealer Funding <br>`CAP-LEND-03` | capability governed by control | Stipulations cleared before funding <br>`CTL-FUND-STIPS` | Process |
| Loan Boarding & Dealer Funding <br>`CAP-LEND-03` | capability governed by control | Settlement funding confirmation <br>`CTL-FUNDING-CONF` | Process |
| Marketing Compliance & Disclosure Review <br>`CAP-ACQ-04` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Process |
| Merchant Acquiring & Sponsorship <br>`CAP-MERCH` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Descendant |
| Merchant Acquiring & Sponsorship <br>`CAP-MERCH` | capability governed by control | Settlement funding confirmation <br>`CTL-FUNDING-CONF` | Descendant |
| Merchant Acquiring & Sponsorship <br>`CAP-MERCH` | capability governed by control | Merchant exposure limit monitoring <br>`CTL-MERCH-EXPOSURE` | Descendant |
| Merchant Acquiring & Sponsorship <br>`CAP-MERCH` | capability governed by control | Merchant screening before boarding <br>`CTL-MERCH-SCREEN` | Descendant |
| Merchant Acquiring & Sponsorship <br>`CAP-MERCH` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Descendant |
| Merchant Acquiring & Sponsorship <br>`CAP-MERCH` | capability governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | Descendant |
| Merchant Boarding & Network Sponsorship <br>`CAP-MERCH-03` | capability governed by control | Merchant screening before boarding <br>`CTL-MERCH-SCREEN` | Process |
| Merchant Credit Underwriting <br>`CAP-MERCH-02-01` | capability governed by control | Merchant exposure limit monitoring <br>`CTL-MERCH-EXPOSURE` | Process |
| Merchant Funding <br>`CAP-MERCH-04-01` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Process |
| Merchant Funding <br>`CAP-MERCH-04-01` | capability governed by control | Settlement funding confirmation <br>`CTL-FUNDING-CONF` | Process |
| Merchant Monitoring & Exposure Management <br>`CAP-MERCH-06` | capability governed by control | Merchant exposure limit monitoring <br>`CTL-MERCH-EXPOSURE` | Process |
| Merchant Reserve Management <br>`CAP-MERCH-04-02` | capability governed by control | Merchant exposure limit monitoring <br>`CTL-MERCH-EXPOSURE` | Process |
| Merchant Screening & Brand Risk <br>`CAP-MERCH-02-02` | capability governed by control | Merchant screening before boarding <br>`CTL-MERCH-SCREEN` | Process |
| Merchant Screening & Brand Risk <br>`CAP-MERCH-02-02` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Process |
| Merchant Settlement & Funding <br>`CAP-MERCH-04` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Process |
| Merchant Settlement & Funding <br>`CAP-MERCH-04` | capability governed by control | Settlement funding confirmation <br>`CTL-FUNDING-CONF` | Process |
| Merchant Settlement & Funding <br>`CAP-MERCH-04` | capability governed by control | Merchant exposure limit monitoring <br>`CTL-MERCH-EXPOSURE` | Process |
| Merchant Underwriting & Risk Vetting <br>`CAP-MERCH-02` | capability governed by control | Merchant exposure limit monitoring <br>`CTL-MERCH-EXPOSURE` | Process |
| Merchant Underwriting & Risk Vetting <br>`CAP-MERCH-02` | capability governed by control | Merchant screening before boarding <br>`CTL-MERCH-SCREEN` | Process |
| Merchant Underwriting & Risk Vetting <br>`CAP-MERCH-02` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Process |
| Network & Merchant Reconciliation <br>`CAP-PAY-06` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Process |
| Network Settlement & Interchange <br>`CAP-PAY-05` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Process |
| Originations & Account Opening <br>`CAP-ORIG` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Descendant |
| Originations & Account Opening <br>`CAP-ORIG` | capability governed by control | Application completeness and disclosure <br>`CTL-APP-INTAKE` | Descendant |
| Originations & Account Opening <br>`CAP-ORIG` | capability governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | Descendant |
| Originations & Account Opening <br>`CAP-ORIG` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Descendant |
| Originations & Account Opening <br>`CAP-ORIG` | capability governed by control | Servicemember protections screening <br>`CTL-SCRA-MLA` | Descendant |
| Outbound Contact Operations <br>`CAP-COLL-02` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Process |
| Outbound Contact Operations <br>`CAP-COLL-02` | capability governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | Process |
| Outbound Contact Operations <br>`CAP-COLL-02` | capability governed by control | Statutory collections notices <br>`CTL-FDCPA-NOTICE` | Process |
| Owned-Portfolio Collections Contact <br>`CAP-COLL-02-01` | capability governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | Process |
| Partner & Client Relationship Management <br>`CAP-PART` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Descendant |
| Partner & Client Relationship Management <br>`CAP-PART` | capability governed by control | Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | Descendant |
| Partner & Client Relationship Management <br>`CAP-PART` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Descendant |
| Partner Agreement & Program Governance <br>`CAP-PART-05-01` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Process |
| Partner Revenue Share Settlement <br>`CAP-PART-05-02` | capability governed by control | Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | Process |
| Payment Allocation & Posting <br>`CAP-PAY-03-02` | capability governed by control | Payment allocation to rule <br>`CTL-PMT-ALLOC` | Process |
| Payment Arrangement & Settlement Offers <br>`CAP-COLL-03` | capability governed by control | Treatment strategy approval <br>`CTL-TREATMENT-APPR` | Process |
| Payment Capture & Application <br>`CAP-PAY-03` | capability governed by control | Payment allocation to rule <br>`CTL-PMT-ALLOC` | Process |
| Payment Capture & Application <br>`CAP-PAY-03` | capability governed by control | Payment posting timeliness <br>`CTL-PMT-POSTING` | Process |
| Payment Channel Capture <br>`CAP-PAY-03-01` | capability governed by control | Payment posting timeliness <br>`CTL-PMT-POSTING` | Process |
| Payments & Transaction Processing <br>`CAP-PAY` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Descendant |
| Payments & Transaction Processing <br>`CAP-PAY` | capability governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | Descendant |
| Payments & Transaction Processing <br>`CAP-PAY` | capability governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | Descendant |
| Payments & Transaction Processing <br>`CAP-PAY` | capability governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | Descendant |
| Payments & Transaction Processing <br>`CAP-PAY` | capability governed by control | Payment allocation to rule <br>`CTL-PMT-ALLOC` | Descendant |
| Payments & Transaction Processing <br>`CAP-PAY` | capability governed by control | Payment posting timeliness <br>`CTL-PMT-POSTING` | Descendant |
| Payoff & Lien Release <br>`CAP-LEND-04-02` | capability governed by control | Title release within statutory deadline <br>`CTL-LIEN-RELEASE` | Process |
| Platform & Infrastructure Operations <br>`CAP-TECH-02` | capability governed by control | Masked data outside production <br>`CTL-MASK-NONPROD` | Process |
| Portfolio Conversion & Deconversion <br>`CAP-TPS-02` | capability governed by control | Conversion balance and record verification <br>`CTL-CONV-VERIFY` | Process |
| Privacy Management <br>`CAP-SEC-05` | capability governed by control | Consumer privacy request fulfillment <br>`CTL-PRIV-REQ` | Process |
| Product Management & Pricing <br>`CAP-PROD` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Descendant |
| Product Management & Pricing <br>`CAP-PROD` | capability governed by control | Notice content and delivery evidence <br>`CTL-NOTICE-CONTENT` | Descendant |
| Quality Engineering & Testing <br>`CAP-TECH-08` | capability governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | Process |
| Quality Engineering & Testing <br>`CAP-TECH-08` | capability governed by control | Masked data outside production <br>`CTL-MASK-NONPROD` | Process |
| Records Retention & Disposition <br>`CAP-DATA-07` | capability governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | Process |
| Regulatory & Financial Reporting <br>`CAP-FIN-04` | capability governed by control | Ingestion data quality gate <br>`CTL-DQ-GATE` | Process |
| Regulatory & Financial Reporting <br>`CAP-FIN-04` | capability governed by control | Regulatory report certification <br>`CTL-REGRPT-CERT` | Process |
| Regulatory Change Management <br>`CAP-RGOV-02` | capability governed by control | Regulatory change implementation tracking <br>`CTL-REGCHANGE-TRACK` | Process |
| Release & Change Management <br>`CAP-TECH-04` | capability governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | Process |
| Repossession & Asset Remarketing <br>`CAP-LEND-06` | capability governed by control | Repossession and disposition notices <br>`CTL-REPO-NOTICE` | Process |
| Repossession & Redemption Notices <br>`CAP-LEND-06-01` | capability governed by control | Repossession and disposition notices <br>`CTL-REPO-NOTICE` | Process |
| Retention, Product Change & Account Closure <br>`CAP-SERV-09` | capability governed by control | Bureau furnishing accuracy <br>`CTL-BUREAU-ACC` | Process |
| Retention, Product Change & Account Closure <br>`CAP-SERV-09` | capability governed by control | Notice content and delivery evidence <br>`CTL-NOTICE-CONTENT` | Process |
| Rewards Earn, Accrual & Redemption <br>`CAP-BILL-04` | capability governed by control | Cycle assessment validation <br>`CTL-CYCLE-VALID` | Process |
| Rewards Program Design <br>`CAP-PROD-04` | capability governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | Process |
| Risk Governance & Compliance Management <br>`CAP-RGOV` | capability governed by control | Complaint regulatory routing <br>`CTL-COMPLAINT-REG` | Descendant |
| Risk Governance & Compliance Management <br>`CAP-RGOV` | capability governed by control | Fair lending testing <br>`CTL-FAIR-LEND-TEST` | Descendant |
| Risk Governance & Compliance Management <br>`CAP-RGOV` | capability governed by control | Regulatory change implementation tracking <br>`CTL-REGCHANGE-TRACK` | Descendant |
| Risk Governance & Compliance Management <br>`CAP-RGOV` | capability governed by control | Regulatory report certification <br>`CTL-REGRPT-CERT` | Descendant |
| Risk Governance & Compliance Management <br>`CAP-RGOV` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Descendant |
| Risk Governance & Compliance Management <br>`CAP-RGOV` | capability governed by control | Suspicious activity investigation and filing <br>`CTL-SAR-FILING` | Descendant |
| Sanctions Screening <br>`CAP-RGOV-07-01` | capability governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | Process |
| Service Management & Incident Response <br>`CAP-TECH-03` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Process |
| Serviced-Portfolio Collections Contact <br>`CAP-COLL-02-02` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Process |
| Serviced-Portfolio Collections Contact <br>`CAP-COLL-02-02` | capability governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | Process |
| Serviced-Portfolio Collections Contact <br>`CAP-COLL-02-02` | capability governed by control | Statutory collections notices <br>`CTL-FDCPA-NOTICE` | Process |
| Servicemember Protections <br>`CAP-SERV-02-02` | capability governed by control | Servicemember protections screening <br>`CTL-SCRA-MLA` | Process |
| Settlement Offers <br>`CAP-COLL-03-02` | capability governed by control | Treatment strategy approval <br>`CTL-TREATMENT-APPR` | Process |
| Solution Delivery & Engineering <br>`CAP-TECH-01` | capability governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | Process |
| Solution Delivery & Engineering <br>`CAP-TECH-01` | capability governed by control | Vulnerability remediation service level <br>`CTL-VULN-SLA` | Process |
| Stand-In Processing <br>`CAP-PAY-01-04` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Process |
| Technology & Platform Operations <br>`CAP-TECH` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Descendant |
| Technology & Platform Operations <br>`CAP-TECH` | capability governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | Descendant |
| Technology & Platform Operations <br>`CAP-TECH` | capability governed by control | Recovery test against committed objectives <br>`CTL-DR-TEST` | Descendant |
| Technology & Platform Operations <br>`CAP-TECH` | capability governed by control | Masked data outside production <br>`CTL-MASK-NONPROD` | Descendant |
| Technology & Platform Operations <br>`CAP-TECH` | capability governed by control | Vulnerability remediation service level <br>`CTL-VULN-SLA` | Descendant |
| Terms & Disclosure Management <br>`CAP-PROD-03` | capability governed by control | Notice content and delivery evidence <br>`CTL-NOTICE-CONTENT` | Process |
| Third-Party & Vendor Management <br>`CAP-TPRM` | capability governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | Descendant |
| Third-Party Servicing Delivery <br>`CAP-TPS` | capability governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | Descendant |
| Third-Party Servicing Delivery <br>`CAP-TPS` | capability governed by control | Conversion balance and record verification <br>`CTL-CONV-VERIFY` | Descendant |
| Threat Detection & Response <br>`CAP-SEC-02` | capability governed by control | Security incident response execution <br>`CTL-IR-PLAYBOOK` | Process |
| Transaction Fraud Detection & Strategy <br>`CAP-FRAUD-01` | capability governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | Process |
| Transaction Monitoring & Suspicious Activity Reporting <br>`CAP-RGOV-07-02` | capability governed by control | Suspicious activity investigation and filing <br>`CTL-SAR-FILING` | Process |
| Transaction Switching <br>`CAP-PAY-01-05` | capability governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | Process |
| Transaction Switching <br>`CAP-PAY-01-05` | capability governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | Process |
| Underwriting & Credit Decisioning Execution <br>`CAP-ORIG-04` | capability governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | Process |
| Vendor Sourcing & Due Diligence <br>`CAP-TPRM-01` | capability governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | Process |
| Vulnerability & Patch Management <br>`CAP-SEC-03` | capability governed by control | Vulnerability remediation service level <br>`CTL-VULN-SLA` | Process |
| Card account master <br>`DA-CARD-ACCOUNT` | data governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | enforced on |
| Card account master <br>`DA-CARD-ACCOUNT` | data governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | enforced on |
| Card transaction history <br>`DA-TRANSACTION` | data governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | enforced on |
| Card transaction history <br>`DA-TRANSACTION` | data governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | enforced on |
| Customer 360 curated dataset <br>`DA-CUST360-CURATED` | data governed by control | Masked data outside production <br>`CTL-MASK-NONPROD` | enforced on |
| Customer 360 curated dataset <br>`DA-CUST360-CURATED` | data governed by control | Ingestion data quality gate <br>`CTL-DQ-GATE` | enforced on |
| Customer profile <br>`DA-CUSTOMER-PROFILE` | data governed by control | Consumer privacy request fulfillment <br>`CTL-PRIV-REQ` | enforced on |
| Dispute Management Platform vendor feed <br>`DA-DISPUTES-VENDOR-FEED` | data governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | enforced on |
| NICE Actimize Screening outcomes <br>`DA-SCREENING-OUTCOMES` | data governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | enforced on |
| Application fraud screening <br>`SYS-APPFRAUD` | system governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | enforced by |
| Authorization Switch <br>`SYS-AUTH-SWITCH` | system governed by control | Authorization availability and stand-in <br>`CTL-AUTH-AVAIL` | enforced by |
| Authorization Switch <br>`SYS-AUTH-SWITCH` | system governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | enforced by |
| Brokered deposit settlement gateway <br>`SYS-BROKER-GW` | system governed by control | Brokered deposit position reconciliation <br>`CTL-BROKERED-RECON` | enforced by |
| Campaign management <br>`SYS-MARKETING` | system governed by control | Marketing material compliance review <br>`CTL-MKT-REVIEW` | enforced by |
| Card production and fulfillment <br>`SYS-CARD-FULFILL` | system governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | enforced by |
| Cardholder mobile application <br>`SYS-MOBILE` | system governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | enforced by |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | enforced by |
| Collections Workspace Service <br>`SYS-COLLECT-API` | system governed by control | Statutory collections notices <br>`CTL-FDCPA-NOTICE` | enforced by |
| Collections Workspace Web <br>`SYS-COLLECT-WEB` | system governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | enforced by |
| Contact center platform <br>`SYS-CONTACT` | system governed by control | Complaint regulatory routing <br>`CTL-COMPLAINT-REG` | enforced by |
| Contact center platform <br>`SYS-CONTACT` | system governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | enforced by |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | enforced by |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system governed by control | Payment posting timeliness <br>`CTL-PMT-POSTING` | enforced by |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system governed by control | Cycle assessment validation <br>`CTL-CYCLE-VALID` | enforced by |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | enforced by |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | enforced by |
| Core Card Ledger <br>`SYS-CORE-LEDGER` | system governed by control | Recovery test against committed objectives <br>`CTL-DR-TEST` | enforced by |
| Credit bureau gateway <br>`SYS-BUREAU-GW` | system governed by control | Furnishing and bucketing reconciliation <br>`CTL-METRO2-RECON` | enforced by |
| Credit bureau gateway <br>`SYS-BUREAU-GW` | system governed by control | Bureau furnishing accuracy <br>`CTL-BUREAU-ACC` | enforced by |
| Credit bureau gateway <br>`SYS-BUREAU-GW` | system governed by control | Dispute acknowledgment timeliness <br>`CTL-REGE-ACK` | enforced by |
| Credit data and decisioning environment <br>`SYS-CREDIT-DATA` | system governed by control | Ingestion data quality gate <br>`CTL-DQ-GATE` | enforced by |
| Credit data and decisioning environment <br>`SYS-CREDIT-DATA` | system governed by control | Fair lending testing <br>`CTL-FAIR-LEND-TEST` | enforced by |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system governed by control | Ingestion data quality gate <br>`CTL-DQ-GATE` | enforced by |
| Customer 360 Pipeline <br>`SYS-CUST360-PIPELINE` | system governed by control | Masked data outside production <br>`CTL-MASK-NONPROD` | enforced by |
| Customer Identity Service <br>`SYS-IDENTITY-SVC` | system governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | enforced by |
| Customer Identity Service <br>`SYS-IDENTITY-SVC` | system governed by control | Periodic access certification <br>`CTL-ACCESS-CERT` | enforced by |
| Dealer portal <br>`SYS-DEALER-PORTAL` | system governed by control | Dealer program and markup monitoring <br>`CTL-DEALER-MON` | enforced by |
| Deposit platform <br>`SYS-DEPOSIT` | system governed by control | Deposit interest tax reporting <br>`CTL-TAX-REPORT` | enforced by |
| Deposit platform <br>`SYS-DEPOSIT` | system governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | enforced by |
| Dispute Management Platform Integration Gateway <br>`SYS-DISPUTES-GATEWAY` | system governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | enforced by |
| Document management and archive <br>`SYS-DOC` | system governed by control | Notice content and delivery evidence <br>`CTL-NOTICE-CONTENT` | enforced by |
| Document management and archive <br>`SYS-DOC` | system governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | enforced by |
| Dynamics 365 Customer Service <br>`SYS-CRM` | system governed by control | Consumer privacy request fulfillment <br>`CTL-PRIV-REQ` | enforced by |
| Dynamics 365 Customer Service <br>`SYS-CRM` | system governed by control | Complaint regulatory routing <br>`CTL-COMPLAINT-REG` | enforced by |
| Experian Credit Bureau <br>`SYS-CREDIT-BUREAU` | system governed by control | Bureau furnishing accuracy <br>`CTL-BUREAU-ACC` | enforced by |
| Experian Credit Bureau <br>`SYS-CREDIT-BUREAU` | system governed by control | Furnishing and bucketing reconciliation <br>`CTL-METRO2-RECON` | enforced by |
| Experian Credit Bureau <br>`SYS-CREDIT-BUREAU` | system governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | enforced by |
| Financial crimes platform <br>`SYS-AML` | system governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | enforced by |
| Financial crimes platform <br>`SYS-AML` | system governed by control | Suspicious activity investigation and filing <br>`CTL-SAR-FILING` | enforced by |
| General ledger <br>`SYS-GL` | system governed by control | Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | enforced by |
| General ledger <br>`SYS-GL` | system governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | enforced by |
| Governance catalog <br>`SYS-CATALOG` | system governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | enforced by |
| Governance, risk and compliance platform <br>`SYS-GRC` | system governed by control | Regulatory change implementation tracking <br>`CTL-REGCHANGE-TRACK` | enforced by |
| Identity and access management <br>`SYS-IAM` | system governed by control | Periodic access certification <br>`CTL-ACCESS-CERT` | enforced by |
| Identity Document Verification <br>`SYS-IDV-VENDOR` | system governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | enforced by |
| Identity verification <br>`SYS-KYC` | system governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | enforced by |
| Identity verification <br>`SYS-KYC` | system governed by control | Servicemember protections screening <br>`CTL-SCRA-MLA` | enforced by |
| Indirect loan origination system <br>`SYS-LOS` | system governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | enforced by |
| Indirect loan origination system <br>`SYS-LOS` | system governed by control | Application completeness and disclosure <br>`CTL-APP-INTAKE` | enforced by |
| Indirect loan origination system <br>`SYS-LOS` | system governed by control | Stipulations cleared before funding <br>`CTL-FUND-STIPS` | enforced by |
| Installment Lending Integration Hub <br>`SYS-LENDING-HUB` | system governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | enforced by |
| Installment loan servicing platform <br>`SYS-LOAN-SVC` | system governed by control | Payment posting timeliness <br>`CTL-PMT-POSTING` | enforced by |
| Installment loan servicing platform <br>`SYS-LOAN-SVC` | system governed by control | Ancillary product refund on early termination <br>`CTL-ANCILLARY-REFUND` | enforced by |
| IT service management <br>`SYS-ITSM` | system governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | enforced by |
| IVR and self-service voice <br>`SYS-IVR` | system governed by control | Cardholder authentication to policy <br>`CTL-AUTH-POLICY` | enforced by |
| Merchant acquiring platform <br>`SYS-MERCH-ACQ` | system governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | enforced by |
| Merchant acquiring platform <br>`SYS-MERCH-ACQ` | system governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | enforced by |
| Merchant risk monitoring <br>`SYS-MERCH-RISK` | system governed by control | Merchant screening before boarding <br>`CTL-MERCH-SCREEN` | enforced by |
| Merchant risk monitoring <br>`SYS-MERCH-RISK` | system governed by control | Merchant exposure limit monitoring <br>`CTL-MERCH-EXPOSURE` | enforced by |
| Model platform <br>`SYS-MODEL` | system governed by control | Treatment strategy approval <br>`CTL-TREATMENT-APPR` | enforced by |
| Model platform <br>`SYS-MODEL` | system governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | enforced by |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | system governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | enforced by |
| NICE Actimize Screening <br>`SYS-SCREENING-VENDOR` | system governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | enforced by |
| NICE Actimize Screening Identity Federation <br>`SYS-SCREENING-FEDERATION` | system governed by control | Periodic access certification <br>`CTL-ACCESS-CERT` | enforced by |
| NICE Actimize Screening Integration Gateway <br>`SYS-SCREENING-GATEWAY` | system governed by control | Sanctions and watchlist screening <br>`CTL-SANCTIONS` | enforced by |
| Observability platform <br>`SYS-OBSERV` | system governed by control | Security incident response execution <br>`CTL-IR-PLAYBOOK` | enforced by |
| Open Banking Affordability <br>`SYS-OBAFF-VENDOR` | system governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | enforced by |
| Open Banking Affordability Integration Gateway <br>`SYS-OBAFF-GATEWAY` | system governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | enforced by |
| Open Banking Affordability Integration Gateway <br>`SYS-OBAFF-GATEWAY` | system governed by control | Consumer privacy request fulfillment <br>`CTL-PRIV-REQ` | enforced by |
| Open Banking Affordability Private Egress <br>`SYS-OBAFF-EGRESS` | system governed by control | Periodic access certification <br>`CTL-ACCESS-CERT` | enforced by |
| Open Banking Affordability Webhook Listener <br>`SYS-OBAFF-WEBHOOKS` | system governed by control | Security incident response execution <br>`CTL-IR-PLAYBOOK` | enforced by |
| Originations decision engine <br>`SYS-ORIG-DECISION` | system governed by control | Adverse action notice completeness <br>`CTL-ADVERSE-ACT` | enforced by |
| Originations decision engine <br>`SYS-ORIG-DECISION` | system governed by control | Application completeness and disclosure <br>`CTL-APP-INTAKE` | enforced by |
| Outbound contact platform <br>`SYS-DIALER` | system governed by control | Collections contact limits <br>`CTL-CONTACT-LIM` | enforced by |
| Payment capture gateway <br>`SYS-PAYMENT-GW` | system governed by control | Payment posting timeliness <br>`CTL-PMT-POSTING` | enforced by |
| Payment capture gateway <br>`SYS-PAYMENT-GW` | system governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | enforced by |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | system governed by control | Third-party due diligence before onboarding <br>`CTL-TPRM-DD` | enforced by |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | system governed by control | Dispute acknowledgment timeliness <br>`CTL-REGE-ACK` | enforced by |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | system governed by control | Provisional credit within regulatory window <br>`CTL-REGE-PROVCR` | enforced by |
| Pega Smart Dispute <br>`SYS-DISPUTES-SAAS` | system governed by control | Dispute determination timeliness and notice <br>`CTL-REGE-DETERM` | enforced by |
| Prospect and marketing data services <br>`SYS-PROSPECT-DATA` | system governed by control | Consumer privacy request fulfillment <br>`CTL-PRIV-REQ` | enforced by |
| Reconciliation platform <br>`SYS-RECON` | system governed by control | Daily settlement and clearing reconciliation <br>`CTL-DAILY-RECON` | enforced by |
| Reconciliation platform <br>`SYS-RECON` | system governed by control | Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | enforced by |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system governed by control | Regulatory report certification <br>`CTL-REGRPT-CERT` | enforced by |
| Regulatory Reporting Engine <br>`SYS-REG-REPORTING` | system governed by control | Close reconciliation sign-off <br>`CTL-CLOSE-SIGNOFF` | enforced by |
| Repossession and remarketing management <br>`SYS-REMARKET` | system governed by control | Repossession and disposition notices <br>`CTL-REPO-NOTICE` | enforced by |
| Security Monitoring <br>`SYS-SIEM` | system governed by control | Security incident response execution <br>`CTL-IR-PLAYBOOK` | enforced by |
| Security Monitoring <br>`SYS-SIEM` | system governed by control | Periodic access certification <br>`CTL-ACCESS-CERT` | enforced by |
| Security Monitoring <br>`SYS-SIEM` | system governed by control | Retention schedule enforcement <br>`CTL-RETENTION` | enforced by |
| Servicing client portal <br>`SYS-CLIENT-PORTAL` | system governed by control | Client reporting and feed monitoring <br>`CTL-CLIENT-SLA` | enforced by |
| Source control and CI/CD pipeline <br>`SYS-SCM` | system governed by control | Production change approval <br>`CTL-CHG-APPROVAL` | enforced by |
| Statement Generation <br>`SYS-STATEMENTS` | system governed by control | Notice content and delivery evidence <br>`CTL-NOTICE-CONTENT` | enforced by |
| Statement Generation <br>`SYS-STATEMENTS` | system governed by control | Cycle assessment validation <br>`CTL-CYCLE-VALID` | enforced by |
| Test management and automation <br>`SYS-TESTMGMT` | system governed by control | Masked data outside production <br>`CTL-MASK-NONPROD` | enforced by |
| Title and lien management <br>`SYS-TITLE` | system governed by control | Lien perfection within policy window <br>`CTL-LIEN-PERFECT` | enforced by |
| Title and lien management <br>`SYS-TITLE` | system governed by control | Title release within statutory deadline <br>`CTL-LIEN-RELEASE` | enforced by |
| Tokenization and credential management <br>`SYS-TOKEN` | system governed by control | Cardholder data scope and evidence maintenance <br>`CTL-PCI-EVIDENCE` | enforced by |
| Transaction fraud detection <br>`SYS-FRAUD-DETECT` | system governed by control | Fraud alert handling service level <br>`CTL-FRAUD-SLA` | enforced by |
| Treasury management <br>`SYS-TREASURY` | system governed by control | Settlement funding confirmation <br>`CTL-FUNDING-CONF` | enforced by |
| Work and change tracking <br>`SYS-WORKTRACK` | system governed by control | Regulatory change implementation tracking <br>`CTL-REGCHANGE-TRACK` | enforced by |

368 relationships across 256 entities. Generated from the model; this is a report rather than a diagram, so it is a table.
