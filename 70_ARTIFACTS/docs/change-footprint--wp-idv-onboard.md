# Onboard the identity verification vendor — Footprint

One work package and its footprint: the systems it builds or changes, the data those systems read and write, the capabilities they realize, and the processes that depend on them. The footprint is derived from the model, so it includes indirect effects.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Onboard the identity verification vendor — Footprint
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SEC_01{{"Identity & Access<br/>Management"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_005[\"Authenticate cardholder"/]
    P_INFOSEC_001[\"Provision and certify<br/>access"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
    SYS_IDV_VENDOR["Identity Document<br/>Verification<br/>[Onfido]"]
    SYS_IDV_GATEWAY["Identity Document<br/>Verification Integration<br/>Gateway<br/>[AKS]"]
    SYS_IDV_EGRESS["Identity Document<br/>Verification Private<br/>Egress"]
    SYS_IDV_WEBHOOKS["Identity Document<br/>Verification Webhook<br/>Listener<br/>[AKS]"]
  end

  subgraph grp_Work_Package["Work Package"]
    direction LR
    WP_IDV_ONBOARD["Onboard the identity<br/>verification vendor"]
  end

  WP_IDV_ONBOARD -->|"Builds"| SYS_IDV_VENDOR
  WP_IDV_ONBOARD -->|"Builds"| SYS_IDV_GATEWAY
  WP_IDV_ONBOARD -->|"Builds"| SYS_IDV_EGRESS
  WP_IDV_ONBOARD -->|"Builds"| SYS_IDV_WEBHOOKS
  WP_IDV_ONBOARD -->|"Changes"| SYS_IDENTITY_SVC
  SYS_IDENTITY_SVC -->|"realizes"| CAP_SEC_01
  P_SERVICING_005 -->|"supports"| CAP_SEC_01
  P_INFOSEC_001 -->|"supports"| CAP_SEC_01

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_work_packages__work_packages fill:#ccfbf1,stroke:#0d9488,color:#0f172a,stroke-width:1.4px;
  class CAP_SEC_01 s_capabilities__capabilities;
  class P_INFOSEC_001,P_SERVICING_005 s_processes__processes;
  class SYS_IDENTITY_SVC,SYS_IDV_EGRESS,SYS_IDV_GATEWAY,SYS_IDV_VENDOR,SYS_IDV_WEBHOOKS s_systems__systems;
  class WP_IDV_ONBOARD s_work_packages__work_packages;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System,grp_Work_Package boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Onboard the identity verification vendor — Footprint](../svg/change-footprint--wp-idv-onboard.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |
| `#0d9488` | work packages |

9 entities, 8 relationships. Generated from the model; edit the model, not this file.
