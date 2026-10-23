# Maintain authorization strategy — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Maintain authorization strategy — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_CRED_06{{"Authorization Strategy<br/>Management"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_TREATMENT_APPR[["Treatment strategy<br/>approval"]]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_CREDIT_007[\"Maintain authorization<br/>strategy"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_FRAUD_DETECT["Transaction fraud<br/>detection"]
  end

  P_CREDIT_007 -->|"Primary"| SYS_CORE_LEDGER
  P_CREDIT_007 -->|"Supporting"| SYS_FRAUD_DETECT
  P_CREDIT_007 -->|"governed by"| CTL_TREATMENT_APPR
  P_CREDIT_007 -->|"supports"| CAP_CRED_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_CRED_06 s_capabilities__capabilities;
  class CTL_TREATMENT_APPR s_controls__controls;
  class P_CREDIT_007 s_processes__processes;
  class SYS_CORE_LEDGER,SYS_FRAUD_DETECT s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Maintain authorization strategy — Systems, Data and Controls](../svg/process-systems--p-credit-007.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
