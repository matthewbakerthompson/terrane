# Execute credit line decrease or account action — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Execute credit line decrease or account action — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_ORIG_05{{"Adverse Action & Notice<br/>Generation"}}
    CAP_CRED_03{{"Credit Line Assignment &<br/>Management"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_CREDIT_004[\"Execute credit line<br/>decrease or account action"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_DOC["Document management and<br/>archive"]
  end

  P_CREDIT_004 -->|"Primary"| SYS_CORE_LEDGER
  P_CREDIT_004 -->|"Supporting"| SYS_DOC
  P_CREDIT_004 -->|"supports"| CAP_CRED_03
  P_CREDIT_004 -->|"supports"| CAP_ORIG_05

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_CRED_03,CAP_ORIG_05 s_capabilities__capabilities;
  class P_CREDIT_004 s_processes__processes;
  class SYS_CORE_LEDGER,SYS_DOC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Execute credit line decrease or account action — Systems, Data and Controls](../svg/process-systems--p-credit-004.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
