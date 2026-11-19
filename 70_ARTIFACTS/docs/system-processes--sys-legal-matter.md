# Legal matter management — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Legal matter management — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_COLL_06{{"Bankruptcy, Deceased &<br/>Legal Account Handling"}}
    CAP_COLL_06_03{{"Legal Placement &<br/>Litigation"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_RECOVERY_006[\"Refer account to legal and<br/>manage litigation"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_LEGAL_MATTER["Legal matter management<br/>[SaaS]"]
  end

  P_RECOVERY_006 -->|"Primary"| SYS_LEGAL_MATTER
  P_RECOVERY_006 -->|"supports"| CAP_COLL_06_03
  P_RECOVERY_006 -->|"supports"| CAP_COLL_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_COLL_06,CAP_COLL_06_03 s_capabilities__capabilities;
  class P_RECOVERY_006 s_processes__processes;
  class SYS_LEGAL_MATTER s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Legal matter management — Processes and Capabilities](../svg/system-processes--sys-legal-matter.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

4 entities, 3 relationships. Generated from the model; edit the model, not this file.
