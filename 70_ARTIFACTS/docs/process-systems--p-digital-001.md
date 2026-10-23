# Enroll cardholder in digital servicing — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Enroll cardholder in digital servicing — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV_03{{"Digital Self-Service"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DIGITAL_001[\"Enroll cardholder in<br/>digital servicing"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
    SYS_MOBILE["Cardholder mobile<br/>application"]
    SYS_IAM["Identity and access<br/>management"]
  end

  P_DIGITAL_001 -->|"Primary"| SYS_CARDSVC_WEB
  P_DIGITAL_001 -->|"Supporting"| SYS_MOBILE
  P_DIGITAL_001 -->|"Supporting"| SYS_IAM
  P_DIGITAL_001 -->|"supports"| CAP_SERV_03

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SERV_03 s_capabilities__capabilities;
  class P_DIGITAL_001 s_processes__processes;
  class SYS_CARDSVC_WEB,SYS_IAM,SYS_MOBILE s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Enroll cardholder in digital servicing — Systems, Data and Controls](../svg/process-systems--p-digital-001.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
