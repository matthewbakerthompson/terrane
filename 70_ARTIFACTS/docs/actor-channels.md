# Channels by Actor

Every actor and the systems they use, split into external parties (customers, partners, regulators) and internal staff. Use it to see which systems are customer-facing and which are internal tooling.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Channels by Actor
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_No["No"]
    direction LR
    ACT_CARD_SCHEME(["Card Scheme"])
    ACT_CARDHOLDER(["Cardholder"])
    ACT_APPLICANT(["Loan Applicant"])
    ACT_MERCHANT(["Merchant"])
    ACT_REGULATOR(["Regulator"])
  end

  subgraph grp_Yes["Yes"]
    direction LR
    ACT_COLLECTIONS_AGENT(["Collections Agent"])
    ACT_UNDERWRITER(["Credit Underwriter"])
    ACT_SERVICING_AGENT(["Servicing Agent"])
  end

  SYS_AUTH_SWITCH["Authorization Switch"]
  SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
  SYS_MOBILE["Cardholder mobile<br/>application"]
  SYS_COLLECT_WEB["Collections Workspace Web<br/>[AKS]"]
  SYS_CONTACT["Contact center platform"]
  SYS_CREDIT_DATA["Credit data and<br/>decisioning environment<br/>[Snowflake Data Cloud]"]
  SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
  SYS_LENDING_WEB["Installment Lending Web<br/>[EKS]"]
  SYS_IVR["IVR and self-service voice"]
  SYS_ORIG_DECISION["Originations decision<br/>engine"]
  SYS_DIALER["Outbound contact platform"]
  SYS_DISPUTES_SAAS["Pega Smart Dispute<br/>[Pegasystems]"]
  SYS_REG_REPORTING["Regulatory Reporting<br/>Engine<br/>[AKS · Snowflake Data Cloud]"]
  SYS_STATEMENTS["Statement Generation"]

  ACT_APPLICANT -->|"Applies"| SYS_LENDING_WEB
  ACT_UNDERWRITER -->|"Reviews referrals"| SYS_LENDING_WEB
  ACT_CARDHOLDER -->|"Self-service"| SYS_CARDSVC_WEB
  ACT_CARDHOLDER -->|"Receives statements"| SYS_STATEMENTS
  ACT_SERVICING_AGENT -->|"Handles cases"| SYS_CRM
  ACT_SERVICING_AGENT -->|"Raises disputes"| SYS_DISPUTES_SAAS
  ACT_COLLECTIONS_AGENT -->|"Works arrears"| SYS_COLLECT_WEB
  ACT_MERCHANT -->|"Presents transactions"| SYS_AUTH_SWITCH
  ACT_CARD_SCHEME -->|"Carries authorization"| SYS_AUTH_SWITCH
  ACT_REGULATOR -->|"Receives returns"| SYS_REG_REPORTING
  ACT_CARDHOLDER -->|"Mobile self-service"| SYS_MOBILE
  ACT_CARDHOLDER -->|"Voice self-service"| SYS_IVR
  ACT_SERVICING_AGENT -->|"Agent desktop"| SYS_CONTACT
  ACT_COLLECTIONS_AGENT -->|"Outbound campaigns"| SYS_DIALER
  ACT_UNDERWRITER -->|"Manual review queue"| SYS_ORIG_DECISION
  ACT_UNDERWRITER -->|"Strategy analysis"| SYS_CREDIT_DATA

  classDef s_actors__default fill:#fde68a,stroke:#b45309,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__high fill:#9aa0ed,stroke:#4338ca,color:#0f172a,stroke-width:2.6px;
  classDef s_systems__medium fill:#becbfb,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class ACT_APPLICANT,ACT_CARD_SCHEME,ACT_CARDHOLDER,ACT_COLLECTIONS_AGENT,ACT_MERCHANT,ACT_REGULATOR,ACT_SERVICING_AGENT,ACT_UNDERWRITER s_actors__default;
  class SYS_AUTH_SWITCH,SYS_CARDSVC_WEB,SYS_LENDING_WEB,SYS_REG_REPORTING s_systems__high;
  class SYS_COLLECT_WEB,SYS_CONTACT,SYS_CREDIT_DATA,SYS_CRM,SYS_DIALER,SYS_DISPUTES_SAAS,SYS_IVR,SYS_MOBILE,SYS_ORIG_DECISION,SYS_STATEMENTS s_systems__medium;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_No,grp_Yes boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Channels by Actor](../svg/actor-channels.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#b45309` | actors |
| `#4338ca` | systems |

**criticality** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | High |
| 1.4px | Medium |
| 1.1px | default |

22 entities, 16 relationships. Generated from the model; edit the model, not this file.
