# Card Servicing Web — Governance

One system and everything that governs it: the controls it enforces, the policies it is subject to, and the controls that apply through the capabilities it realizes. A control reached only through a capability means either the system enforces it and nobody recorded that, or it is enforced somewhere else.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Card Servicing Web — Governance
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SERV{{"Customer Servicing & Care"}}
    CAP_SERV_03{{"Digital Self-Service"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_COMPLAINT_REG[["Complaint regulatory<br/>routing"]]
    CTL_REGE_DETERM[["Dispute determination<br/>timeliness and notice"]]
    CTL_NOTICE_CONTENT[["Notice content and<br/>delivery evidence"]]
    CTL_SCRA_MLA[["Servicemember protections<br/>screening"]]
  end

  subgraph grp_Policy["Policy"]
    direction LR
    POL_ERROR_RES[/"Error Resolution & Billing<br/>Dispute Policy"\]
    POL_FAIR_LEND[/"Fair Lending & Credit<br/>Decision Policy"\]
    POL_MKT_UDAAP[/"Marketing Review & UDAAP<br/>Policy"\]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CARDSVC_WEB["Card Servicing Web<br/>[AKS]"]
  end

  SYS_CARDSVC_WEB -->|"realizes"| CAP_SERV
  SYS_CARDSVC_WEB -->|"realizes"| CAP_SERV_03
  CAP_SERV -->|"governed by"| CTL_COMPLAINT_REG
  CAP_SERV -->|"governed by"| CTL_NOTICE_CONTENT
  CAP_SERV -->|"governed by"| CTL_REGE_DETERM
  CAP_SERV -->|"governed by"| CTL_SCRA_MLA
  CTL_COMPLAINT_REG -->|"gives effect to"| POL_MKT_UDAAP
  CTL_NOTICE_CONTENT -->|"gives effect to"| POL_ERROR_RES
  CTL_REGE_DETERM -->|"gives effect to"| POL_ERROR_RES
  CTL_SCRA_MLA -->|"gives effect to"| POL_FAIR_LEND

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_policies__policies fill:#fecaca,stroke:#dc2626,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SERV,CAP_SERV_03 s_capabilities__capabilities;
  class CTL_COMPLAINT_REG,CTL_NOTICE_CONTENT,CTL_REGE_DETERM,CTL_SCRA_MLA s_controls__controls;
  class POL_ERROR_RES,POL_FAIR_LEND,POL_MKT_UDAAP s_policies__policies;
  class SYS_CARDSVC_WEB s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Policy,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Card Servicing Web — Governance](../svg/system-governance--sys-cardsvc-web.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#dc2626` | policies |
| `#4338ca` | systems |

10 entities, 10 relationships. Generated from the model; edit the model, not this file.
