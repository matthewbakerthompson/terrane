# Experian Credit Bureau — Governance

One system and everything that governs it: the controls it enforces, the policies it is subject to, and the controls that apply through the capabilities it realizes. A control reached only through a capability means either the system enforces it and nobody recorded that, or it is enforced somewhere else.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Experian Credit Bureau — Governance
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Control["Control"]
    direction LR
    CTL_BUREAU_ACC[["Bureau furnishing accuracy"]]
    CTL_METRO2_RECON[["Furnishing and bucketing<br/>reconciliation"]]
    CTL_TPRM_DD[["Third-party due diligence<br/>before onboarding"]]
  end

  subgraph grp_Policy["Policy"]
    direction LR
    POL_FAIR_LEND[/"Fair Lending & Credit<br/>Decision Policy"\]
    POL_TPRM[/"Third-Party Risk<br/>Management Policy"\]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CREDIT_BUREAU["Experian Credit Bureau<br/>[Experian]"]
  end

  SYS_CREDIT_BUREAU -->|"enforces"| CTL_BUREAU_ACC
  SYS_CREDIT_BUREAU -->|"enforces"| CTL_METRO2_RECON
  SYS_CREDIT_BUREAU -->|"enforces"| CTL_TPRM_DD
  SYS_CREDIT_BUREAU -->|"subject to"| POL_FAIR_LEND
  SYS_CREDIT_BUREAU -->|"subject to"| POL_TPRM
  CTL_BUREAU_ACC -->|"gives effect to"| POL_FAIR_LEND
  CTL_METRO2_RECON -->|"gives effect to"| POL_FAIR_LEND
  CTL_TPRM_DD -->|"gives effect to"| POL_TPRM

  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_policies__policies fill:#fecaca,stroke:#dc2626,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CTL_BUREAU_ACC,CTL_METRO2_RECON,CTL_TPRM_DD s_controls__controls;
  class POL_FAIR_LEND,POL_TPRM s_policies__policies;
  class SYS_CREDIT_BUREAU s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Control,grp_Policy,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Experian Credit Bureau — Governance](../svg/system-governance--sys-credit-bureau.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#b91c1c` | controls |
| `#dc2626` | policies |
| `#4338ca` | systems |

6 entities, 8 relationships. Generated from the model; edit the model, not this file.
