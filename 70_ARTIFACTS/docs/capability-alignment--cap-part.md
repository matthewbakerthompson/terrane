# Partner & Client Relationship Management — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Partner & Client Relationship Management — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PART_04{{"Client Service Level &<br/>Performance Management"}}
    CAP_PART_05{{"Co-Brand & Program Partner<br/>Management"}}
    CAP_PART_01{{"Issuing Bank & Sponsor<br/>Relationship"}}
    CAP_PART_02{{"Network & Scheme<br/>Relationship"}}
    CAP_PART{{"Partner & Client<br/>Relationship Management"}}
    CAP_PART_03{{"Servicing Client<br/>Origination & Contracting"}}
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_APQC["APQC Process<br/>Classification Framework"]
    FW_BIAN["BIAN"]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_PARTNERSHIPS_001[\"Fulfill issuing bank<br/>oversight obligations"/]
    P_PAYMENTS_005[\"Implement network mandate<br/>release"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
  end

  CAP_PART_01 -->|"part of"| CAP_PART
  CAP_PART_02 -->|"part of"| CAP_PART
  CAP_PART_03 -->|"part of"| CAP_PART
  CAP_PART_04 -->|"part of"| CAP_PART
  CAP_PART_05 -->|"part of"| CAP_PART
  CAP_PART_01 -->|"Reference Data #gt; Ext…"| FW_BIAN
  CAP_PART_02 -->|"Operations and Executio…"| FW_BIAN
  CAP_PART_03 -->|"11.0 Manage External Re…"| FW_APQC
  CAP_PART_04 -->|"11.0 Manage External Re…"| FW_APQC
  CAP_PART_05 -->|"11.0 Manage External Re…"| FW_APQC
  P_PAYMENTS_005 -->|"supported by"| CAP_PART_02
  P_PARTNERSHIPS_001 -->|"supported by"| CAP_PART_01
  SYS_CORE_LEDGER -->|"realizes"| CAP_PART_02
  SYS_GRC -->|"realizes"| CAP_PART_01

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PART,CAP_PART_01,CAP_PART_02,CAP_PART_03,CAP_PART_04,CAP_PART_05 s_capabilities__capabilities;
  class FW_APQC,FW_BIAN s_frameworks__frameworks;
  class P_PARTNERSHIPS_001,P_PAYMENTS_005 s_processes__processes;
  class SYS_CORE_LEDGER,SYS_GRC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Framework,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Partner & Client Relationship Management — Frameworks, Controls, Systems](../svg/capability-alignment--cap-part.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#4d7c0f` | frameworks |
| `#0369a1` | processes |
| `#4338ca` | systems |

12 entities, 14 relationships. Generated from the model; edit the model, not this file.
