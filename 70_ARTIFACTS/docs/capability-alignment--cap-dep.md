# Deposit Products & Funding — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Deposit Products & Funding — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_DEP_03{{"Brokered CD Program<br/>Management"}}
    CAP_DEP_02{{"Deposit Account Opening"}}
    CAP_DEP_05{{"Deposit Compliance &<br/>Insurance Administration"}}
    CAP_DEP_01{{"Deposit Product Management"}}
    CAP_DEP{{"Deposit Products & Funding"}}
    CAP_DEP_04{{"Deposit Servicing,<br/>Interest & Maturities"}}
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
    FW_CRI["CRI Profile"]
  end

  CAP_DEP_01 -->|"part of"| CAP_DEP
  CAP_DEP_02 -->|"part of"| CAP_DEP
  CAP_DEP_03 -->|"part of"| CAP_DEP
  CAP_DEP_04 -->|"part of"| CAP_DEP
  CAP_DEP_05 -->|"part of"| CAP_DEP
  CAP_DEP -->|"Aligned to"| FW_BIAN
  CAP_DEP_01 -->|"Operations and Executio…"| FW_BIAN
  CAP_DEP_02 -->|"Operations and Executio…"| FW_BIAN
  CAP_DEP_03 -->|"Operations and Executio…"| FW_BIAN
  CAP_DEP_04 -->|"Operations and Executio…"| FW_BIAN
  CAP_DEP_05 -->|"Govern #gt; GV.OC-03"| FW_CRI

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  class CAP_DEP,CAP_DEP_01,CAP_DEP_02,CAP_DEP_03,CAP_DEP_04,CAP_DEP_05 s_capabilities__capabilities;
  class FW_BIAN,FW_CRI s_frameworks__frameworks;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Framework boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Deposit Products & Funding — Frameworks, Controls, Systems](../svg/capability-alignment--cap-dep.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#4d7c0f` | frameworks |

8 entities, 11 relationships. Generated from the model; edit the model, not this file.
