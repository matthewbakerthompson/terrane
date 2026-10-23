# Identity verification — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Identity verification — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_02{{"Account Maintenance &<br/>Servicing Requests"}}
    CAP_RGOV_07{{"Financial Crimes & BSA/AML<br/>Compliance"}}
    CAP_ORIG_02{{"Identity Verification &<br/>KYC/CIP"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_SERVICING_012[\"Apply servicemember and<br/>military lending<br/>protections"/]
    P_COMPLIANCE_003[\"Screen for sanctions and<br/>watchlists"/]
    P_ORIG_002[\"Verify applicant identity<br/>and satisfy CIP"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_KYC["Identity verification"]
  end

  P_ORIG_002 -->|"Primary"| SYS_KYC
  P_COMPLIANCE_003 -->|"Supporting"| SYS_KYC
  P_SERVICING_012 -->|"Supporting"| SYS_KYC
  P_ORIG_002 -->|"supports"| CAP_ORIG_02
  P_ORIG_002 -->|"supports"| CAP_RGOV_07
  P_COMPLIANCE_003 -->|"supports"| CAP_RGOV_07
  P_SERVICING_012 -->|"supports"| CAP_SERV_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_ORIG_02,CAP_RGOV_07,CAP_SERV_02 s_capabilities__capabilities;
  class P_COMPLIANCE_003,P_ORIG_002,P_SERVICING_012 s_processes__processes;
  class SYS_KYC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Identity verification — Processes and Capabilities](../svg/system-processes--sys-kyc.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

7 entities, 7 relationships. Generated from the model; edit the model, not this file.
