# Authorization Switch — Governance

One system and everything that governs it: the controls it enforces, the policies it is subject to, and the controls that apply through the capabilities it realizes. A control reached only through a capability means either the system enforces it and nobody recorded that, or it is enforced somewhere else.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Authorization Switch — Governance
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_PAY{{"Payments & Transaction<br/>Processing"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_AUTH_AVAIL[["Authorization availability<br/>and stand-in"]]
    CTL_PCI_EVIDENCE[["Cardholder data scope and<br/>evidence maintenance"]]
    CTL_DAILY_RECON[["Daily settlement and<br/>clearing reconciliation"]]
    CTL_PMT_POSTING[["Payment posting timeliness"]]
  end

  subgraph grp_Policy["Policy"]
    direction LR
    POL_ERROR_RES[/"Error Resolution & Billing<br/>Dispute Policy"\]
    POL_INFOSEC[/"Information Security<br/>Policy"\]
    POL_RECORDS[/"Records Retention &<br/>Disposition Policy"\]
    POL_CHANGE[/"Technology Change<br/>Management Policy"\]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_AUTH_SWITCH["Authorization Switch"]
  end

  SYS_AUTH_SWITCH -->|"enforces"| CTL_AUTH_AVAIL
  SYS_AUTH_SWITCH -->|"enforces"| CTL_PCI_EVIDENCE
  SYS_AUTH_SWITCH -->|"realizes"| CAP_PAY
  CAP_PAY -->|"governed by"| CTL_AUTH_AVAIL
  CAP_PAY -->|"governed by"| CTL_DAILY_RECON
  CAP_PAY -->|"governed by"| CTL_PMT_POSTING
  SYS_AUTH_SWITCH -->|"subject to"| POL_INFOSEC
  SYS_AUTH_SWITCH -->|"subject to"| POL_CHANGE
  CTL_AUTH_AVAIL -->|"gives effect to"| POL_CHANGE
  CTL_DAILY_RECON -->|"gives effect to"| POL_RECORDS
  CTL_PCI_EVIDENCE -->|"gives effect to"| POL_INFOSEC
  CTL_PMT_POSTING -->|"gives effect to"| POL_ERROR_RES

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_policies__policies fill:#fecaca,stroke:#dc2626,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_PAY s_capabilities__capabilities;
  class CTL_AUTH_AVAIL,CTL_DAILY_RECON,CTL_PCI_EVIDENCE,CTL_PMT_POSTING s_controls__controls;
  class POL_CHANGE,POL_ERROR_RES,POL_INFOSEC,POL_RECORDS s_policies__policies;
  class SYS_AUTH_SWITCH s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Policy,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Authorization Switch — Governance](../svg/system-governance--sys-auth-switch.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#dc2626` | policies |
| `#4338ca` | systems |

10 entities, 12 relationships. Generated from the model; edit the model, not this file.
