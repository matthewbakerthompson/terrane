# Customer Identity Service — Governance

One system and everything that governs it: the controls it enforces, the policies it is subject to, and the controls that apply through the capabilities it realizes. A control reached only through a capability means either the system enforces it and nobody recorded that, or it is enforced somewhere else.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Customer Identity Service — Governance
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_SEC_01{{"Identity & Access<br/>Management"}}
  end

  subgraph grp_Control["Control"]
    direction LR
    CTL_AUTH_POLICY[["Cardholder authentication<br/>to policy"]]
    CTL_ACCESS_CERT[["Periodic access<br/>certification"]]
  end

  subgraph grp_Policy["Policy"]
    direction LR
    POL_INFOSEC[/"Information Security<br/>Policy"\]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
  end

  SYS_IDENTITY_SVC -->|"enforces"| CTL_AUTH_POLICY
  SYS_IDENTITY_SVC -->|"enforces"| CTL_ACCESS_CERT
  SYS_IDENTITY_SVC -->|"realizes"| CAP_SEC_01
  CAP_SEC_01 -->|"governed by"| CTL_ACCESS_CERT
  CAP_SEC_01 -->|"governed by"| CTL_AUTH_POLICY
  SYS_IDENTITY_SVC -->|"subject to"| POL_INFOSEC
  CTL_ACCESS_CERT -->|"gives effect to"| POL_INFOSEC
  CTL_AUTH_POLICY -->|"gives effect to"| POL_INFOSEC

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_controls__controls fill:#fca5a5,stroke:#b91c1c,color:#0f172a,stroke-width:1.4px;
  classDef s_policies__policies fill:#fecaca,stroke:#dc2626,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_SEC_01 s_capabilities__capabilities;
  class CTL_ACCESS_CERT,CTL_AUTH_POLICY s_controls__controls;
  class POL_INFOSEC s_policies__policies;
  class SYS_IDENTITY_SVC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Control,grp_Policy,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Customer Identity Service — Governance](../svg/system-governance--sys-identity-svc.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#b91c1c` | controls |
| `#dc2626` | policies |
| `#4338ca` | systems |

5 entities, 8 relationships. Generated from the model; edit the model, not this file.
