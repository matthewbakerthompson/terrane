# People, Legal & Corporate Services — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% People, Legal & Corporate Services — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_CORP_05{{"Corporate Communications"}}
    CAP_CORP_04{{"Facilities & Workplace<br/>Operations"}}
    CAP_CORP_02{{"Learning, Licensing &<br/>Certification"}}
    CAP_CORP_03{{"Legal & Contract Counsel"}}
    CAP_CORP{{"People, Legal & Corporate<br/>Services"}}
    CAP_CORP_01{{"Workforce Management & HR"}}
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_APQC["APQC Process<br/>Classification Framework"]
  end

  CAP_CORP_01 -->|"part of"| CAP_CORP
  CAP_CORP_02 -->|"part of"| CAP_CORP
  CAP_CORP_03 -->|"part of"| CAP_CORP
  CAP_CORP_04 -->|"part of"| CAP_CORP
  CAP_CORP_05 -->|"part of"| CAP_CORP
  CAP_CORP -->|"Aligned to"| FW_APQC
  CAP_CORP_01 -->|"6.0 Develop and Manage…"| FW_APQC
  CAP_CORP_02 -->|"6.0 Develop and Manage…"| FW_APQC
  CAP_CORP_03 -->|"11.0 Manage External Re…"| FW_APQC
  CAP_CORP_04 -->|"9.0 Acquire, Construct…"| FW_APQC
  CAP_CORP_05 -->|"11.0 Manage External Re…"| FW_APQC

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  class CAP_CORP,CAP_CORP_01,CAP_CORP_02,CAP_CORP_03,CAP_CORP_04,CAP_CORP_05 s_capabilities__capabilities;
  class FW_APQC s_frameworks__frameworks;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Framework boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![People, Legal & Corporate Services — Frameworks, Controls, Systems](../svg/capability-alignment--cap-corp.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#4d7c0f` | frameworks |

7 entities, 11 relationships. Generated from the model; edit the model, not this file.
