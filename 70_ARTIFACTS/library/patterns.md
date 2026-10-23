# Patterns

A building block plus the decision: what it is for, what it costs, and when not to use it. Generated from `27_PATTERNS/` by `terrane render`; edit the pattern files, not this. Who owns each one here, the decision that approved it and the controls it satisfies are the estate's, under `patterns` in `10_MODEL/model.yaml`.

The last column is the adoption report. It is read off the `patterns` field of every product and every interface in the model, so it is current whether or not anybody remembered to update a register. Where a pattern implements one of the method's reference patterns, the **Method** line names it.

| Pattern | Status | Category | Made of | Satisfies | Applied by |
|---|---|---|---|---|---|
| [Hybrid return path](#hybrid-return-path) | Candidate | Landing zone | `hybrid-connectivity` | `CTL-DR-TEST` | — |
| [Analytics landing zone](#analytics-landing-zone) | Approved | Data | `analytics-platform`, `data-governance` | `CTL-DQ-GATE`, `CTL-MASK-NONPROD`, `CTL-RETENTION` | Customer 360, Lending Portfolio Performance, 3 interfaces |
| [API front door](#api-front-door) | Approved | Edge | `public-api-tier` | `CTL-AUTH-POLICY` | Card Servicing, Collections Workspace, Customer Identity Service, Point-of-Sale Finance, Rewards Redemption, 6 interfaces |
| [Change evidence read off the systems](#change-evidence-chain) | Approved | Governance | `change-evidence` | `CTL-CHG-APPROVAL`, `CTL-REGCHANGE-TRACK` | Installment Lending, 6 interfaces |
| [Contact center through the servicing gateway](#contact-center-integration) | Approved | Communications | `contact-channel` | `CTL-CONTACT-LIM`, `CTL-COMPLAINT-REG`, `CTL-AUTH-POLICY` | Collections Workspace, 5 interfaces |
| [Customer communications through one archive](#customer-communication-archive) | Approved | Communications | `document-services` | `CTL-NOTICE-CONTENT`, `CTL-FDCPA-NOTICE`, `CTL-RETENTION` | Collections Workspace, Dispute Management, 4 interfaces |
| [Event fan-out](#event-fanout) | Approved | Integration | `event-tier` | — | Card Servicing, Installment Lending, Merchant Portal, Point-of-Sale Finance, Rewards Redemption, 4 interfaces |
| [Governed model lifecycle](#governed-model-lifecycle) | Approved | Decisioning | `model-platform`, `data-governance` | `CTL-ADVERSE-ACT`, `CTL-TREATMENT-APPR`, `CTL-DQ-GATE` | 3 interfaces |
| [Inline risk decision in the transaction path](#inline-risk-decision) | Approved | Decisioning | `realtime-decision` | `CTL-FRAUD-SLA`, `CTL-AUTH-AVAIL` | 2 interfaces |
| [Observed service](#observed-service) | Approved | Operations | `observability-stack` | `CTL-IR-PLAYBOOK`, `CTL-AUTH-AVAIL`, `CTL-DR-TEST` | Card Servicing, Customer Identity Service, 3 interfaces |
| [Partner file exchange](#partner-file-exchange) | Approved | Integration | `file-exchange` | `CTL-CLIENT-SLA` | Dispute Management, NICE Actimize Screening, 1 interface |
| [Payment capture and same-day posting](#payment-capture-and-posting) | Approved | Payments | `payment-capture`, `transactional-store` | `CTL-PMT-POSTING`, `CTL-FUNDING-CONF`, `CTL-DAILY-RECON` | 2 interfaces |
| [Private egress to a bought service](#private-egress-to-saas) | Approved | Integration | `private-egress-to-saas` | `CTL-TPRM-DD`, `CTL-SANCTIONS` | Identity Document Verification, NICE Actimize Screening, Open Banking Affordability, 1 interface |
| [Public web entry](#public-web-entry) | Approved | Edge | `public-web-tier` | `CTL-PCI-EVIDENCE` | Installment Lending |
| [Regulatory file furnishing with reconciliation](#regulatory-file-furnishing) | Approved | Integration | `file-exchange`, `batch-tier` | `CTL-METRO2-RECON`, `CTL-BUREAU-ACC`, `CTL-REGE-ACK` | 3 interfaces |
| [Secrets and keys from the baseline](#secrets-and-keys) | Approved | Security | `security-baseline` | `CTL-PCI-EVIDENCE` | Customer Identity Service |
| [Stateless request service](#stateless-request-service) | Approved | Compute | `stateless-service`, `transactional-store` | — | Card Servicing, Collections Workspace, Installment Lending, Merchant Portal, Point-of-Sale Finance, Rewards Redemption |
| [Strangler facade over a system being replaced](#strangler-facade) | Approved | Compute | `public-api-tier`, `stateless-service` | `CTL-CHG-APPROVAL`, `CTL-CONV-VERIFY` | Card Servicing |
| [Tokenized card data](#tokenized-card-data) | Approved | Security | `token-vault` | `CTL-PCI-EVIDENCE`, `CTL-AUTH-AVAIL` | 2 interfaces |
| [Windowed batch](#windowed-batch) | Approved | Compute | `batch-tier` | `CTL-DAILY-RECON` | Customer 360, Lending Portfolio Performance, 8 interfaces |
| [Workforce identity from the people system](#workforce-identity-lifecycle) | Approved | Security | `identity-governance` | `CTL-ACCESS-CERT`, `CTL-IR-PLAYBOOK` | 4 interfaces |
| [Workload account baseline](#workload-account-baseline) | Approved | Landing zone | `account-baseline`, `security-baseline`, `delivery-pipeline` | `CTL-CHG-APPROVAL`, `CTL-ACCESS-CERT`, `CTL-VULN-SLA` | Installment Lending |
| [Shared database integration](#shared-database-integration) | Deprecated | Integration | `transactional-store` | — | Collections Workspace |

<a id="hybrid-return-path"></a>
## Hybrid return path

**Id:** `hybrid-return-path` · **Status:** Candidate · **Category:** Landing zone · **Owner:** Technology · **Decision:** ADR-0011 · **Method:** PAT-008

**Intent.** Two independent paths from the cloud estate back to the data center, with failover between them, so that the mainframe stays reachable when one carrier does not.

**What it costs.** Two circuits, two carriers, two contracts, and a failover that is a claim until it has been exercised. The pattern is a candidate rather than approved for exactly that reason: the recovery test has not been run against it, and a resilience pattern that has not been tested is a diagram.

**When not to use it.** A workload with no dependency on anything in the data center, which should not be given a path to it. Every hybrid path is an attack surface as well as a resilience measure.

**Made of.** Hybrid connectivity (`hybrid-connectivity`): Hybrid link, DNS.

![Hybrid connectivity, as the block is drawn](svg/block--hybrid-connectivity.svg)

*Hybrid connectivity: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Recovery test against committed objectives (`CTL-DR-TEST`).

**Applied by.** Nothing in the model yet.

<a id="analytics-landing-zone"></a>
## Analytics landing zone

**Id:** `analytics-landing-zone` · **Status:** Approved · **Category:** Data · **Owner:** Data Governance · **Decision:** ADR-0010 · **Method:** PAT-005

**Intent.** Data lands once, in object storage, and everything analytical is built from that landing: pipelines into a warehouse, reporting on top, and a catalog that records what each dataset is and where it came from. The boundary between landing and warehouse is where lineage is either recorded or lost, so the pattern makes it a step rather than a leap.

**What it costs.** A second copy of every operational dataset, with its own classification, retention and masking obligations, and its own owner who is usually not the operational one. The catalog is only worth having if registration is part of landing rather than a task for later, which means the pipeline has to refuse a dataset nobody has described.

**When not to use it.** A single operational report from a single system, which is a query, not a platform. Data that must not leave its source system's classification boundary, where landing it elsewhere is the control failure.

**Made of.** Analytics platform (`analytics-platform`): Object store, Data pipeline, Data warehouse, Business intelligence; Data governance (`data-governance`): Data catalog, Key management.

![Analytics platform, as the block is drawn](svg/block--analytics-platform.svg)

*Analytics platform: the block's components with the category glyph and the services each resolves to, and the connections between them.*

![Data governance, as the block is drawn](svg/block--data-governance.svg)

*Data governance: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Ingestion data quality gate (`CTL-DQ-GATE`), Masked data outside production (`CTL-MASK-NONPROD`), Retention schedule enforcement (`CTL-RETENTION`).

**Applied by.** Customer 360 (`PRD-CUSTOMER-360`), Lending Portfolio Performance (`PRD-LENDING-PERFORMANCE`).

**On interfaces.** Enterprise Data Platform to Credit Data Environment (`INT-INGEST-CREDIT-DATA`), Enterprise Data Platform to Governance Catalog (`INT-INGEST-CATALOG`), Enterprise Data Platform to Model Platform (`INT-INGEST-MODEL`).

<a id="api-front-door"></a>
## API front door

**Id:** `api-front-door` · **Status:** Approved · **Category:** Edge · **Owner:** Technology · **Decision:** ADR-0004 · **Method:** PAT-001

**Intent.** Every programmatic entry point sits behind one gateway that authenticates, throttles and versions on behalf of the services behind it. Consumers are coupled to a contract at the gateway rather than to a service, which is what makes the service replaceable.

**What it costs.** The gateway is on the critical path of everything, so it needs the resilience posture of the most critical thing behind it. Teams will route around it when it is slow or its change process is heavier than theirs; the pattern only holds while going through it is the easy option.

**When not to use it.** Service-to-service calls inside one workload account do not need a public front door and should not pay its latency. A single internal consumer of a single service is a private endpoint, not a platform.

**Made of.** Public API tier (`public-api-tier`): DNS, Web application firewall, API gateway.

![Public API tier, as the block is drawn](svg/block--public-api-tier.svg)

*Public API tier: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Cardholder authentication to policy (`CTL-AUTH-POLICY`).

**Applied by.** Card Servicing (`PRD-CARD-SERVICING`), Collections Workspace (`PRD-COLLECTIONS-WORKSPACE`), Customer Identity Service (`PRD-IDENTITY`), Point-of-Sale Finance (`PRD-POS-FINANCE`), Rewards Redemption (`PRD-REWARDS`).

**On interfaces.** Cardholder Mobile to Card Servicing API (`INT-MOBILE-CARDSVC`), Cardholder Mobile to Tokenization Service (`INT-MOBILE-TOKEN`), Document Management to Servicing Client Portal (`INT-DOC-CLIENT-PORTAL`), IVR to Card Servicing API (`INT-IVR-CARDSVC`), Originations Decision Engine to Credit Data Environment (`INT-ORIG-CREDIT-DATA`), Originations Decision Engine to Identity Verification (`INT-ORIG-KYC`).

<a id="change-evidence-chain"></a>
## Change evidence read off the systems

**Id:** `change-evidence-chain` · **Status:** Approved · **Category:** Governance · **Owner:** Enterprise Architecture · **Decision:** ADR-0016 · **Method:** PAT-012

**Intent.** What reached production is proven by a chain of systems writing to each other: the pipeline records the change it deployed, service management records the approval it was deployed under, and the risk register reads both. A regulatory change is a work item whose closure is evidenced by the deployment that implemented it. Nobody compiles the audit; the audit is a query.

**What it costs.** Every deployment path has to go through the pipeline, including the emergency one, or the chain has a gap exactly where an auditor will look. The service management tool becomes a dependency of releasing software, which teams resent until the first audit they do not have to prepare for. Linking work items, approvals and deployments is a data discipline, and a change raised under the wrong work item is a false statement the chain faithfully preserves.

**When not to use it.** Changes to things outside the estate's control, such as a vendor's release of their own service, where the evidence is their notice and our assessment of it, not a deployment of ours. Prototypes with no path to production data, where the ceremony buys nothing, provided the no-path claim is checked and the prototype is actually retired.

**Made of.** Change evidence (`change-evidence`): Source control, Delivery pipeline, Artifact registry, Service management.

![Change evidence, as the block is drawn](svg/block--change-evidence.svg)

*Change evidence: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Production change approval (`CTL-CHG-APPROVAL`), Regulatory change implementation tracking (`CTL-REGCHANGE-TRACK`).

**Applied by.** Installment Lending (`PRD-INSTALLMENT-LENDING`).

**On interfaces.** Architecture Repository to Governance, Risk and Compliance (`INT-ARCHREPO-GRC`), IT Service Management to Architecture Repository (`INT-ITSM-ARCHREPO`), IT Service Management to Governance, Risk and Compliance (`INT-ITSM-GRC`), Source Control and Pipeline to IT Service Management (`INT-SCM-ITSM`), Source Control and Pipeline to Test Management (`INT-SCM-TESTMGMT`), Work Tracking to Governance, Risk and Compliance (`INT-WORKTRACK-GRC`).

<a id="contact-center-integration"></a>
## Contact center through the servicing gateway

**Id:** `contact-center-integration` · **Status:** Approved · **Category:** Communications · **Owner:** Customer Servicing · **Decision:** ADR-0020 · **Method:** PAT-018

**Intent.** The voice self-service and the agent desktop reach customer and account data through the same gateway the digital channels use, with the same authentication policy, so a cardholder is verified once and the context follows the call from the voice menu to the agent. Contact outcomes, complaints among them, are written back as events the servicing systems consume, which is how a complaint reaches the regulatory register without a person re-keying it.

**What it costs.** The gateway's latency is now audible: a screen that takes two seconds to populate is two seconds of silence on a call. Call context has to be carried across a transfer, which means a session the telephony and the servicing systems both understand, and nobody's telephony came with one. Every outcome written back is a classification decision made by an agent under time pressure, and the register inherits its quality.

**When not to use it.** An outsourced contact center that works inside its own desktop with our data exported to it, where the integration is a vendor file exchange and pretending it is this pattern hides where the data went. Outbound campaigns with no servicing component, which are a marketing channel and belong to the marketing platform's rules.

**Made of.** Contact channel (`contact-channel`): Conversational AI, API gateway, Event bus.

![Contact channel, as the block is drawn](svg/block--contact-channel.svg)

*Contact channel: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Collections contact limits (`CTL-CONTACT-LIM`), Complaint regulatory routing (`CTL-COMPLAINT-REG`), Cardholder authentication to policy (`CTL-AUTH-POLICY`).

**Applied by.** Collections Workspace (`PRD-COLLECTIONS-WORKSPACE`).

**On interfaces.** Collections Platform to Outbound Contact Platform (`INT-COLLECT-DIALER`), Contact Center Platform to CRM (`INT-CONTACT-CRM`), IVR to Card Servicing API (`INT-IVR-CARDSVC`), IVR to Contact Center Platform (`INT-IVR-CONTACT`), Outbound Contact Platform to Collections Platform (`INT-DIALER-COLLECT`).

<a id="customer-communication-archive"></a>
## Customer communications through one archive

**Id:** `customer-communication-archive` · **Status:** Approved · **Category:** Communications · **Owner:** Customer Servicing · **Decision:** ADR-0017 · **Method:** PAT-016

**Intent.** Every statement, notice and letter is generated from a reviewed template by one service, delivered through it, and archived by it with the evidence of delivery beside the document. The systems that decide a communication is due say so and hand over the facts; they never render or send. The question an examiner asks, "show me what this customer was told and when", has one place to be answered from.

**What it costs.** One service is on the path of every regulated communication and on the schedule of every cycle, so its backlog is everyone's backlog and its outage is a notice-timing finding for every product at once. Templates are governed artifacts with a review process, which is slower than a developer editing a string, and that is the point. The archive grows forever at the pace of the retention schedule and is the single largest store in the estate within a few years.

**When not to use it.** Operational messages with no regulatory content and no retention requirement, such as a one-time passcode or a delivery notification, which the archive would keep for seven years for no reason anyone can name. Communications a vendor is contracted to produce and archive, where the pattern applies to the evidence we receive back and not to the production.

**Made of.** Document services (`document-services`): Workflow orchestration, Container platform, Object store, Archive storage.

![Document services, as the block is drawn](svg/block--document-services.svg)

*Document services: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Notice content and delivery evidence (`CTL-NOTICE-CONTENT`), Statutory collections notices (`CTL-FDCPA-NOTICE`), Retention schedule enforcement (`CTL-RETENTION`).

**Applied by.** Collections Workspace (`PRD-COLLECTIONS-WORKSPACE`), Dispute Management (`PRD-DISPUTES`).

**On interfaces.** Collections Platform to Document Management (`INT-COLLECT-DOC`), Core Card Ledger to Document Management (`INT-LEDGER-DOC`), Originations Decision Engine to Document Management (`INT-ORIG-DOC`), Statement Generation to Document Management (`INT-STATEMENTS-DOC`).

<a id="event-fanout"></a>
## Event fan-out

**Id:** `event-fanout` · **Status:** Approved · **Category:** Integration · **Owner:** Application Development · **Decision:** ADR-0008 · **Method:** PAT-002

**Intent.** A producer publishes domain events to a stream and never learns who consumed them. Consumers arrive and leave without the producer changing, which is the decoupling every integration architecture claims and this is the shape that actually delivers it.

**What it costs.** Once a consumer reads the stream the producer no longer controls who depends on it, so the event schema is a public contract with all the versioning discipline that implies. Ordering, replay and duplicate delivery each have to be decided rather than hoped for, and every consumer is on the impact list of a schema change whether or not anybody can name it.

**When not to use it.** A caller that needs an answer before it can continue. Wrapping a request-response conversation in events produces a distributed transaction with extra steps.

**Made of.** Event tier (`event-tier`): Event stream, Event bus, Function.

![Event tier, as the block is drawn](svg/block--event-tier.svg)

*Event tier: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Applied by.** Card Servicing (`PRD-CARD-SERVICING`), Installment Lending (`PRD-INSTALLMENT-LENDING`), Merchant Portal (`PRD-MERCHANT-PORTAL`), Point-of-Sale Finance (`PRD-POS-FINANCE`), Rewards Redemption (`PRD-REWARDS`).

**On interfaces.** Campaign Management to CRM (`INT-MARKETING-CRM`), Identity Verification to Financial Crimes Platform (`INT-KYC-AML`), Outbound Contact Platform to Collections Platform (`INT-DIALER-COLLECT`), Transaction Fraud Detection to CRM (`INT-FRAUD-CRM`).

<a id="governed-model-lifecycle"></a>
## Governed model lifecycle

**Id:** `governed-model-lifecycle` · **Status:** Approved · **Category:** Decisioning · **Owner:** Credit Risk · **Decision:** ADR-0018 · **Method:** PAT-017

**Intent.** Every model that affects a customer is trained on data the catalog describes, registered with its version, its training set and its intended use, served from the registry rather than from a laptop, and monitored for drift against the population it was built on. A decision the model made can be explained after the fact from what the registry holds, which is what an adverse action notice and a model risk review both need and neither can reconstruct.

**What it costs.** Registration is a gate and gates slow things: a model that cannot say what it was trained on does not get served, and the data scientist who built it finds that out at the gate. Monitoring produces findings that somebody has to own, and a model with drift nobody acts on is a model with a documented defect. The feature store is a second copy of operational data, with the classification, masking and retention obligations a second copy always has.

**When not to use it.** Analytics that inform a person rather than decide for one, where a dashboard is a dashboard and the registry adds ceremony with no decision to explain. Rules that are rules, written and reviewed as such; dressing a lookup table as a model gives it a lifecycle it does not need and hides the fact that somebody could just read it.

**Made of.** Model platform (`model-platform`): Machine learning platform, Object store, Data catalog, Observability; Data governance (`data-governance`): Data catalog, Key management.

![Model platform, as the block is drawn](svg/block--model-platform.svg)

*Model platform: the block's components with the category glyph and the services each resolves to, and the connections between them.*

![Data governance, as the block is drawn](svg/block--data-governance.svg)

*Data governance: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Adverse action notice completeness (`CTL-ADVERSE-ACT`), Treatment strategy approval (`CTL-TREATMENT-APPR`), Ingestion data quality gate (`CTL-DQ-GATE`).

**On interfaces.** Enterprise Data Platform to Model Platform (`INT-INGEST-MODEL`), Originations Decision Engine to Model Platform (`INT-ORIG-MODEL`), Transaction Fraud Detection to Model Platform (`INT-FRAUD-MODEL`).

<a id="inline-risk-decision"></a>
## Inline risk decision in the transaction path

**Id:** `inline-risk-decision` · **Status:** Approved · **Category:** Decisioning · **Owner:** Fraud Operations · **Decision:** ADR-0014 · **Method:** PAT-013

**Intent.** A fraud or risk score is produced inside the authorization flow, against a time budget the switch enforces, from features that were computed before the transaction arrived. The scorer answers or it does not; when it does not, the switch applies a stated default and the transaction completes. A decision the business can tune in minutes, on a path whose latency the business cannot see, is what the pattern buys.

**What it costs.** A time budget is a contract and every feature, model and network hop in the path spends it; the features that would make the model better are usually the ones that cannot be computed in time. The fail-open or fail-closed default is a business decision with a loss attached either way, and has to be written down, owned and revisited, because the scorer's availability sets how often it is taken. Every model change is a change to the authorization path and goes through that change process, not the analytics one.

**When not to use it.** Decisions with no time budget: an application that takes a day to underwrite does not need a scorer that answers in forty milliseconds, and should use the model platform directly. Decisions whose default is unacceptable in either direction, which means the scorer must never be unavailable, which means the pattern is being asked for a guarantee it cannot give and the switch's own rules should carry the decision.

**Made of.** Real-time decision (`realtime-decision`): Stream processing, Cache, Machine learning platform, Observability.

![Real-time decision, as the block is drawn](svg/block--realtime-decision.svg)

*Real-time decision: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Fraud alert handling service level (`CTL-FRAUD-SLA`), Authorization availability and stand-in (`CTL-AUTH-AVAIL`).

**On interfaces.** Authorization Switch to Transaction Fraud Detection (`INT-AUTH-FRAUD`), Originations Decision Engine to Application Fraud Screening (`INT-ORIG-APPFRAUD`).

<a id="observed-service"></a>
## Observed service

**Id:** `observed-service` · **Status:** Approved · **Category:** Operations · **Owner:** Technology · **Decision:** ADR-0015 · **Method:** PAT-008

**Intent.** A service in production emits logs, metrics and traces with a shared correlation id, declares the handful of signals that mean it is healthy, and is paged on them through the same on-call that security monitoring pages. The incident that follows is recorded in service management, reviewed, and closed with what changed. A service whose health cannot be read off a dashboard is not in production yet, whatever the release note says.

**What it costs.** Telemetry has a bill, and verbose logging of a busy service is a real line in the cloud invoice; the pattern expects the signals to be chosen, not everything kept. A page is a promise that somebody answers, so on-call has to be staffed before the alert exists. Security monitoring reading application logs means application logs are now in scope for what must not be logged, and a card number in a debug line is a breach.

**When not to use it.** A batch job that runs once a day and is checked once a day, where a failed-run alert is the whole of what is needed and a dashboard is decoration. A vendor's service, whose observability is theirs; what we observe is our side of the integration and the vendor's status page, and the pattern applies to the first.

**Made of.** Observability stack (`observability-stack`): Observability, Security monitoring, On-call and incident response, Service management.

![Observability stack, as the block is drawn](svg/block--observability-stack.svg)

*Observability stack: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Security incident response execution (`CTL-IR-PLAYBOOK`), Authorization availability and stand-in (`CTL-AUTH-AVAIL`), Recovery test against committed objectives (`CTL-DR-TEST`).

**Applied by.** Card Servicing (`PRD-CARD-SERVICING`), Customer Identity Service (`PRD-IDENTITY`).

**On interfaces.** Identity and Access Management to Security Monitoring (`INT-IAM-SIEM`), Observability Platform to IT Service Management (`INT-OBSERV-ITSM`), Security Monitoring to IT Service Management (`INT-SIEM-ITSM`).

<a id="partner-file-exchange"></a>
## Partner file exchange

**Id:** `partner-file-exchange` · **Status:** Approved · **Category:** Integration · **Owner:** Third-Party Servicing · **Decision:** ADR-0009 · **Method:** PAT-003

**Intent.** Scheduled files with a party who was never going to build an API, landed in object storage under orchestration that knows when a file is late. Older than every other pattern here and still how most inter-company data actually moves, so it is worth doing deliberately.

**What it costs.** File formats drift silently on the other side, so validation on arrival is part of the pattern and not an optional extra. The schedule is an agreement with a partner and changes at the speed of contracts. Monitoring for a file that did not arrive is harder than monitoring for one that did, and is the part most implementations skip.

**When not to use it.** A partner who does offer an API, where a file exchange adds a day of latency to an integration that could take a second. Data that is personal and leaves the estate, unless the transfer control has been designed first.

**Made of.** File exchange (`file-exchange`): Managed file transfer, Object store, Workflow orchestration.

![File exchange, as the block is drawn](svg/block--file-exchange.svg)

*File exchange: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Client reporting and feed monitoring (`CTL-CLIENT-SLA`).

**Applied by.** Dispute Management (`PRD-DISPUTES`), NICE Actimize Screening (`PRD-SCREENING`).

**On interfaces.** Core Card Ledger to Card Production (`INT-LEDGER-CARD-FULFILL`).

<a id="payment-capture-and-posting"></a>
## Payment capture and same-day posting

**Id:** `payment-capture-and-posting` · **Status:** Approved · **Category:** Payments · **Owner:** Payments Operations · **Decision:** ADR-0021 · **Method:** PAT-015

**Intent.** Every channel a payment can arrive through -- the app, a debit at a terminal, a lockbox file, a wallet push -- lands in one capture service that assigns each instruction a sequence, stores it, and posts it to the ledger in order, once. Returns and reversals come back through the same service and reverse the instruction they refer to. Settlement totals go to the general ledger from the same store the postings came from, so the daily reconciliation compares two reports of one fact.

**What it costs.** The capture service is a system of record for payment instructions, with the tiering, recovery and retention that implies, where before the instructions lived in four channels' logs. Posting in order means a slow channel can hold up a fast one, and the ordering guarantee has to be designed rather than assumed from a queue's documentation. Every new payment channel is an integration into this service first and a product feature second, which product teams find slower than calling the ledger.

**When not to use it.** Card transactions, which arrive through the authorization switch and the clearing files and have their own posting path; a payment is money the customer sends us, and conflating the two paths loses the distinction the reconciliation depends on. Internal transfers between the bank's own accounts, which are journal entries and belong to the general ledger's rules.

**Made of.** Payment capture (`payment-capture`): API gateway, Managed file transfer, Message queue, Relational database; Transactional store (`transactional-store`): Relational database, Backup and recovery, Key management.

![Payment capture, as the block is drawn](svg/block--payment-capture.svg)

*Payment capture: the block's components with the category glyph and the services each resolves to, and the connections between them.*

![Transactional store, as the block is drawn](svg/block--transactional-store.svg)

*Transactional store: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Payment posting timeliness (`CTL-PMT-POSTING`), Settlement funding confirmation (`CTL-FUNDING-CONF`), Daily settlement and clearing reconciliation (`CTL-DAILY-RECON`).

**On interfaces.** Payment Capture Gateway to Core Card Ledger (`INT-PAYMENT-GW-LEDGER`), Payment Capture Gateway to General Ledger (`INT-PAYMENT-GW-GL`).

<a id="private-egress-to-saas"></a>
## Private egress to a bought service

**Id:** `private-egress-to-saas` · **Status:** Approved · **Category:** Integration · **Owner:** Vendor Management · **Decision:** ADR-0007 · **Method:** PAT-011

**Intent.** Reach a vendor's service without the traffic touching the internet and without the vendor holding a credential of ours: a gateway we own, a private path out, and federated identity. This is the whole of what we build when we buy something. The vendor runs the software; we run the boundary.

**What it costs.** A private endpoint per vendor per region, and a vendor that offers one, which not all do. The gateway is a system with an owner, a change process and a service tier, and it is easy to forget that a bought capability still leaves something to operate.

**When not to use it.** A vendor with no private connectivity offer, where the pattern degrades to a gateway and a public path and should be modeled honestly as that. A service exchanging only Public data, where the boundary is the cost of a control the data does not need.

**Made of.** Private egress to SaaS (`private-egress-to-saas`): API gateway, Private egress, Identity provider.

![Private egress to SaaS, as the block is drawn](svg/block--private-egress-to-saas.svg)

*Private egress to SaaS: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Third-party due diligence before onboarding (`CTL-TPRM-DD`), Sanctions and watchlist screening (`CTL-SANCTIONS`).

**Applied by.** Identity Document Verification (`PRD-IDV`), NICE Actimize Screening (`PRD-SCREENING`), Open Banking Affordability (`PRD-OB-AFFORDABILITY`).

**On interfaces.** CRM to Dispute Gateway (`INT-CRM-DISPUTES`).

<a id="public-web-entry"></a>
## Public web entry

**Id:** `public-web-entry` · **Status:** Approved · **Category:** Edge · **Owner:** Information Security · **Decision:** ADR-0003

**Intent.** The only way from the internet to a browser-facing application is through a CDN and a WAF, in that order, and nothing behind them is reachable any other way. The point is not caching. It is that the origin has exactly one front door, and that the door has rules.

**What it costs.** Every hostname is a CDN distribution somebody has to own, the WAF ruleset becomes a change-managed artifact with false positives to triage, and a surprising amount of routing logic migrates to the edge where it is harder to test. Budget for the ruleset review as an ongoing cost, not a setup one.

**When not to use it.** An application with no internet exposure gains nothing but a bill. An API consumed only by other systems wants the API front door pattern, which puts authentication and throttling where a browser never goes.

**Made of.** Public web tier (`public-web-tier`): Content delivery network, Web application firewall, Load balancer, DNS.

![Public web tier, as the block is drawn](svg/block--public-web-tier.svg)

*Public web tier: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Cardholder data scope and evidence maintenance (`CTL-PCI-EVIDENCE`).

**Applied by.** Installment Lending (`PRD-INSTALLMENT-LENDING`).

<a id="regulatory-file-furnishing"></a>
## Regulatory file furnishing with reconciliation

**Id:** `regulatory-file-furnishing` · **Status:** Approved · **Category:** Integration · **Owner:** Collections · **Decision:** ADR-0022 · **Method:** PAT-014

**Intent.** A file the regulation prescribes -- the monthly furnishing to the credit bureaus is the one every card business has -- is produced from the ledger by one gateway, validated against the format before it leaves, sent on the schedule, and reconciled against what the recipient acknowledged. The disputes the recipient sends back come in through the same gateway and are cases from the moment they land. The gateway exists so the ledger never speaks to a bureau and the bureau never speaks to the ledger.

**What it costs.** A reconciliation that finds a difference is a finding, and the pattern produces one every month there is a difference; teams used to a file that was simply sent find this unwelcome. Format changes arrive from the regulator or the recipient on their schedule, and the validation step is the thing that breaks first, deliberately. A dispute returned in a file has a statutory clock running from the day it landed, not the day somebody opened the file, so the landing has to create the case.

**When not to use it.** Files exchanged with a commercial partner under a contract rather than a regulation, which is the partner file exchange pattern, where the schedule and format are negotiated rather than prescribed and a missed file is a service-level matter rather than a furnishing failure. Regulatory reports that are forms rather than files, which go through the reporting platform and its certification control.

**Made of.** File exchange (`file-exchange`): Managed file transfer, Object store, Workflow orchestration; Batch tier (`batch-tier`): Batch compute, Object store, Workflow orchestration.

![File exchange, as the block is drawn](svg/block--file-exchange.svg)

*File exchange: the block's components with the category glyph and the services each resolves to, and the connections between them.*

![Batch tier, as the block is drawn](svg/block--batch-tier.svg)

*Batch tier: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Furnishing and bucketing reconciliation (`CTL-METRO2-RECON`), Bureau furnishing accuracy (`CTL-BUREAU-ACC`), Dispute acknowledgment timeliness (`CTL-REGE-ACK`).

**On interfaces.** Core Card Ledger to Credit Bureau Gateway (`INT-LEDGER-BUREAU-GW`), Credit Bureau Gateway to Credit Bureau (`INT-BUREAU-GW-BUREAU`), Credit Bureau Gateway to CRM (`INT-BUREAU-GW-CRM`).

<a id="secrets-and-keys"></a>
## Secrets and keys from the baseline

**Id:** `secrets-and-keys` · **Status:** Approved · **Category:** Security · **Owner:** Information Security · **Decision:** ADR-0013 · **Method:** PAT-010

**Intent.** No credential lives in code, configuration or a person's head. Secrets are issued by the landing zone's secrets manager and rotated by it; keys are generated inside the key management service and never leave it; certificates come from one authority and expire on a schedule something watches. A product inherits all three from the account it is built in, which is why they are in the baseline block and not a block of their own.

**What it costs.** Every workload has a startup dependency on the secrets manager, so the secrets manager has the resilience posture of the most critical thing that reads it. Rotation breaks anything that cached a secret, which is the intended way to find out what cached a secret. Keys that cannot leave the service cannot be used by a vendor's software that wants to hold them, and that constraint has ended more than one procurement late.

**When not to use it.** A bought service that manages its own secrets inside its own boundary, where the pattern applies to the credential we hold for it and nothing else. Development environments with no path to production data, where the cost of the pattern buys nothing, provided the no-path claim has been checked rather than assumed.

**Made of.** Security baseline (`security-baseline`): Identity provider, Secrets manager, Key management, Security monitoring.

![Security baseline, as the block is drawn](svg/block--security-baseline.svg)

*Security baseline: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Cardholder data scope and evidence maintenance (`CTL-PCI-EVIDENCE`).

**Applied by.** Customer Identity Service (`PRD-IDENTITY`).

<a id="stateless-request-service"></a>
## Stateless request service

**Id:** `stateless-request-service` · **Status:** Approved · **Category:** Compute · **Owner:** Application Development · **Decision:** ADR-0005 · **Method:** PAT-004

**Intent.** A request-response service that keeps no state of its own, with the state it needs in a transactional store beside it. Any instance can answer any request, which is the property that makes scaling and recovery mechanical rather than heroic.

**What it costs.** The cache is where the stateless claim usually turns out to be false, and it should be treated as a store with a recovery objective rather than an optimization. The database becomes the constraint on scale and on recovery time, and the pattern pushes every difficult question there.

**When not to use it.** Long-running work does not fit a request that has to wait for an answer; that is the event tier or the batch tier. A workload whose state genuinely must live in the process, such as a session-bound protocol, is a different shape and should be modeled as one rather than forced into this.

**Made of.** Stateless service (`stateless-service`): Container platform, Cache, Observability; Transactional store (`transactional-store`): Relational database, Backup and recovery, Key management.

![Stateless service, as the block is drawn](svg/block--stateless-service.svg)

*Stateless service: the block's components with the category glyph and the services each resolves to, and the connections between them.*

![Transactional store, as the block is drawn](svg/block--transactional-store.svg)

*Transactional store: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Applied by.** Card Servicing (`PRD-CARD-SERVICING`), Collections Workspace (`PRD-COLLECTIONS-WORKSPACE`), Installment Lending (`PRD-INSTALLMENT-LENDING`), Merchant Portal (`PRD-MERCHANT-PORTAL`), Point-of-Sale Finance (`PRD-POS-FINANCE`), Rewards Redemption (`PRD-REWARDS`).

<a id="strangler-facade"></a>
## Strangler facade over a system being replaced

**Id:** `strangler-facade` · **Status:** Approved · **Category:** Compute · **Owner:** Application Development · **Decision:** ADR-0023 · **Method:** PAT-009

**Intent.** Every consumer of a system being replaced is moved behind one facade that speaks the new contract and, behind it, still calls the old system. Capabilities are then moved one at a time from the old system to services behind the facade, and no consumer notices which side of the line a capability is on today. The old system is retired when the facade's last route to it is removed, and not before. This is how the card platform is being modernized, and it is the only way a Tier 1 system of record ever has been.

**What it costs.** The facade is a Tier 1 system from the day it fronts one: it has the old system's availability obligation and the new estate's change cadence. Two implementations of a capability exist during every move, and the data between them has to be reconciled until the old one is retired, which is longer than any plan says. Programs stall with the facade carrying half the routes, and a half-strangled system is more complex than either end state; the pattern needs an owner for the retirement, not just for the facade.

**When not to use it.** A system with one consumer, which should just be replaced; the facade is decoupling for the sake of many consumers and costs a hop when there is one. A system whose data model is the thing being replaced, where routing by capability does not divide the problem and the move is a migration with a cutover, however much everyone would prefer otherwise.

**Made of.** Public API tier (`public-api-tier`): DNS, Web application firewall, API gateway; Stateless service (`stateless-service`): Container platform, Cache, Observability.

![Public API tier, as the block is drawn](svg/block--public-api-tier.svg)

*Public API tier: the block's components with the category glyph and the services each resolves to, and the connections between them.*

![Stateless service, as the block is drawn](svg/block--stateless-service.svg)

*Stateless service: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Production change approval (`CTL-CHG-APPROVAL`), Conversion balance and record verification (`CTL-CONV-VERIFY`).

**Applied by.** Card Servicing (`PRD-CARD-SERVICING`).

<a id="tokenized-card-data"></a>
## Tokenized card data

**Id:** `tokenized-card-data` · **Status:** Approved · **Category:** Security · **Owner:** Information Security · **Decision:** ADR-0019 · **Method:** PAT-019

**Intent.** A card number is exchanged for a token at the edge of the estate and nothing inside the estate but the vault ever sees the number again. The authorization switch detokenizes on the way to the schemes; a wallet provisioning request is answered with a token the device holds; every other system, including the ledger, carries the token. Cardholder-data scope shrinks from the estate to one service, and the evidence a control demands is about one service.

**What it costs.** The vault is on the critical path of every authorization and has to answer inside the switch's time budget, which makes it the most availability-sensitive thing in the estate after the switch itself. A token is only useful to systems that agree on it, so re-tokenizing a portfolio is a migration touching everything. Reports and investigations that genuinely need the number need a controlled path to the vault, and the path is the first thing an auditor asks about.

**When not to use it.** Data that is not a card number: a tokenization service is not a general encryption service and treating it as one puts customer data in the highest-scope component for no reduction in scope. A system that receives card numbers from a scheme or a processor and can only forward them, where tokenizing in the middle adds a hop and removes nothing.

**Made of.** Token vault (`token-vault`): Container platform, Relational database, Key management, Certificate management.

![Token vault, as the block is drawn](svg/block--token-vault.svg)

*Token vault: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Cardholder data scope and evidence maintenance (`CTL-PCI-EVIDENCE`), Authorization availability and stand-in (`CTL-AUTH-AVAIL`).

**On interfaces.** Authorization Switch to Tokenization Service (`INT-AUTH-TOKEN`), Cardholder Mobile to Tokenization Service (`INT-MOBILE-TOKEN`).

<a id="windowed-batch"></a>
## Windowed batch

**Id:** `windowed-batch` · **Status:** Approved · **Category:** Compute · **Owner:** Data Engineering · **Decision:** ADR-0006

**Intent.** Scheduled work with a deadline: orchestration that knows the window, compute that fits inside it, and object staging for what goes in and comes out. Lateness is a business event here, so the window is modeled rather than assumed.

**What it costs.** The window is usually set by somebody outside the organization, and it does not move when volume grows. Capacity has to be planned against the worst night of the year, and the orchestration becomes the place where every dependency between jobs is either recorded or discovered at three in the morning.

**When not to use it.** Anything a consumer needs within seconds of it happening. A batch that is run every five minutes to fake real time has all the costs of both shapes.

**Made of.** Batch tier (`batch-tier`): Batch compute, Object store, Workflow orchestration.

![Batch tier, as the block is drawn](svg/block--batch-tier.svg)

*Batch tier: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Daily settlement and clearing reconciliation (`CTL-DAILY-RECON`).

**Applied by.** Customer 360 (`PRD-CUSTOMER-360`), Lending Portfolio Performance (`PRD-LENDING-PERFORMANCE`).

**On interfaces.** Core Card Ledger to Financial Crimes Platform (`INT-LEDGER-AML`), Core Card Ledger to General Ledger (`INT-LEDGER-GL`), Core Card Ledger to Reconciliation Platform (`INT-LEDGER-RECON`), Core Card Ledger to Servicing Client Portal (`INT-LEDGER-CLIENT-PORTAL`), General Ledger to Reconciliation Platform (`INT-GL-RECON`), General Ledger to Treasury Management (`INT-GL-TREASURY`), Originations Decision Engine to Core Card Ledger (`INT-ORIG-LEDGER-BOARD`), Prospect Data Services to Campaign Management (`INT-PROSPECT-MARKETING`).

<a id="workforce-identity-lifecycle"></a>
## Workforce identity from the people system

**Id:** `workforce-identity-lifecycle` · **Status:** Approved · **Category:** Security · **Owner:** Information Security · **Decision:** ADR-0012 · **Method:** PAT-007

**Intent.** Every workforce account exists because the people system says a person does, with the access their role implies, and stops existing the day the people system says they left. Applications federate to the one identity provider rather than keeping users of their own; privileged accounts are checked out of a vault rather than owned; and every authentication is read by security monitoring. The access certification a control demands becomes a report rather than a campaign.

**What it costs.** The people system becomes a Tier 1 dependency of everything, and its data quality becomes a security property: a mover whose record is a week late keeps a week of access nobody meant. Applications that cannot federate have to be fronted or replaced, which is a program, not a configuration. The vault adds a step to every privileged action, and the step is the point, so it cannot be optimized away when an incident is in progress.

**When not to use it.** Customer identity, which is a different pattern with a different threat model: a cardholder is not provisioned from a people system and is not certified quarterly. Service and workload identities, which are issued by the platform rather than a person, and should not be given a joiner-mover-leaver process they will never follow.

**Made of.** Identity governance (`identity-governance`): Identity provider, Identity governance, Privileged access management, Security monitoring.

![Identity governance, as the block is drawn](svg/block--identity-governance.svg)

*Identity governance: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Periodic access certification (`CTL-ACCESS-CERT`), Security incident response execution (`CTL-IR-PLAYBOOK`).

**On interfaces.** Contact Center Platform to Identity and Access Management (`INT-CONTACT-IAM`), CRM to Identity and Access Management (`INT-CRM-IAM`), HR Information System to Identity and Access Management (`INT-HRIS-IAM`), Identity and Access Management to Security Monitoring (`INT-IAM-SIEM`).

<a id="workload-account-baseline"></a>
## Workload account baseline

**Id:** `workload-account-baseline` · **Status:** Approved · **Category:** Landing zone · **Owner:** Technology · **Decision:** ADR-0001 · **Method:** PAT-004

**Intent.** Every workload account arrives with the same network tiers, the same identity, secrets, keys and detection, and the same route to production, before a line of application code lands. Onboarding creates this; the product team never has to think about it, which is the point.

**What it costs.** The baseline is a product with a release cadence, and a change to it reaches every account at once. That is the feature, and it means the baseline needs a change process stricter than any single workload's. The unglamorous half of a cloud footprint, and the half a security review is actually about.

**When not to use it.** A sandbox or a proof of concept that will be deleted in a month, which should be a sandbox account with a deletion date rather than a workload account with a baseline it will never use.

**Made of.** Account baseline (`account-baseline`): Virtual network, Subnet, DNS, Observability, Infrastructure as code; Security baseline (`security-baseline`): Identity provider, Secrets manager, Key management, Security monitoring; Delivery pipeline (`delivery-pipeline`): Delivery pipeline, Infrastructure as code, Service management.

![Account baseline, as the block is drawn](svg/block--account-baseline.svg)

*Account baseline: the block's components with the category glyph and the services each resolves to, and the connections between them.*

![Security baseline, as the block is drawn](svg/block--security-baseline.svg)

*Security baseline: the block's components with the category glyph and the services each resolves to, and the connections between them.*

![Delivery pipeline, as the block is drawn](svg/block--delivery-pipeline.svg)

*Delivery pipeline: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Satisfies.** Production change approval (`CTL-CHG-APPROVAL`), Periodic access certification (`CTL-ACCESS-CERT`), Vulnerability remediation service level (`CTL-VULN-SLA`).

**Applied by.** Installment Lending (`PRD-INSTALLMENT-LENDING`).

<a id="shared-database-integration"></a>
## Shared database integration

**Id:** `shared-database-integration` · **Status:** Deprecated · **Category:** Integration · **Owner:** Application Development · **Decision:** ADR-0002

**Intent.** Two systems integrate by reading and writing one database. It was the default for twenty years and it still turns up wherever a deadline met a schema somebody already had access to.

**What it costs.** Neither system can change its schema without the other, neither owns the data, and the database becomes the integration contract with no version, no owner and no test. Every reconciliation problem in the estate can be traced to one of these eventually.

**When not to use it.** Always, for new work. Where one already exists, model it honestly as two writers to one asset so the data lineage view shows it, and replace it with the event fan-out or a service interface when the next change to either side is planned.

**Made of.** Transactional store (`transactional-store`): Relational database, Backup and recovery, Key management.

![Transactional store, as the block is drawn](svg/block--transactional-store.svg)

*Transactional store: the block's components with the category glyph and the services each resolves to, and the connections between them.*

**Applied by.** Collections Workspace (`PRD-COLLECTIONS-WORKSPACE`).
