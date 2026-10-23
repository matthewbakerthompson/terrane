# Security Monitoring — Governance

One system and everything that governs it: the controls it enforces, the policies it is subject to, and the controls that apply through the capabilities it realizes. A control reached only through a capability means either the system enforces it and nobody recorded that, or it is enforced somewhere else.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Security Monitoring — Governance
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SEC_02_02{{"Security Incident Response"}}
    CAP_SEC_02_01{{"Security Monitoring"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_ACCESS_CERT[["Periodic access<br/>certification"]]
    CTL_RETENTION[["Retention schedule<br/>enforcement"]]
    CTL_IR_PLAYBOOK[["Security incident response<br/>execution"]]
  end

  subgraph grp_Policy["Policy"]
    direction LR
    POL_INFOSEC[/"Information Security<br/>Policy"\]
    POL_RECORDS[/"Records Retention &<br/>Disposition Policy"\]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_SIEM["Security Monitoring<br/>[Microsoft Sentinel]"]
  end

  SYS_SIEM -->|"enforces"| CTL_IR_PLAYBOOK
  SYS_SIEM -->|"enforces"| CTL_ACCESS_CERT
  SYS_SIEM -->|"enforces"| CTL_RETENTION
  SYS_SIEM -->|"realizes"| CAP_SEC_02_01
  SYS_SIEM -->|"realizes"| CAP_SEC_02_02
  SYS_SIEM -->|"subject to"| POL_INFOSEC
  SYS_SIEM -->|"subject to"| POL_RECORDS
  CTL_ACCESS_CERT -->|"gives effect to"| POL_INFOSEC
  CTL_IR_PLAYBOOK -->|"gives effect to"| POL_INFOSEC
  CTL_RETENTION -->|"gives effect to"| POL_RECORDS

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_policies__policies fill:#fecaca,stroke:#dc2626,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SEC_02_01,CAP_SEC_02_02 s_capabilities__capabilities;
  class CTL_ACCESS_CERT,CTL_IR_PLAYBOOK,CTL_RETENTION s_controls__controls;
  class POL_INFOSEC,POL_RECORDS s_policies__policies;
  class SYS_SIEM s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Policy,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Security Monitoring — Governance](../svg/system-governance--sys-siem.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#dc2626` | policies |
| `#4338ca` | systems |

8 entities, 10 relationships. Generated from the model; edit the model, not this file.
