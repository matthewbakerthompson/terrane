# Campaign management — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Campaign management — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_ACQ_03{{"Campaign Execution &<br/>Channel Management"}}
    CAP_ACQ_04{{"Marketing Compliance &<br/>Disclosure Review"}}
    CAP_ACQ_02{{"Offer & Pre-Screen<br/>Management"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_MARKETING_002[\"Construct and approve firm<br/>offer of credit"/]
    P_MARKETING_003[\"Execute acquisition<br/>campaign"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_MARKETING["Campaign management"]
  end

  P_MARKETING_002 -->|"Supporting"| SYS_MARKETING
  P_MARKETING_003 -->|"Primary"| SYS_MARKETING
  P_MARKETING_002 -->|"supports"| CAP_ACQ_02
  P_MARKETING_002 -->|"supports"| CAP_ACQ_04
  P_MARKETING_003 -->|"supports"| CAP_ACQ_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_ACQ_02,CAP_ACQ_03,CAP_ACQ_04 s_capabilities__capabilities;
  class P_MARKETING_002,P_MARKETING_003 s_processes__processes;
  class SYS_MARKETING s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Campaign management — Processes and Capabilities](../svg/system-processes--sys-marketing.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

6 entities, 5 relationships. Generated from the model; edit the model, not this file.
