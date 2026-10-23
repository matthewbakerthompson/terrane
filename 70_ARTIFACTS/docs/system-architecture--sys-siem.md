# Security Monitoring — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Security Monitoring — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_SCREENING_OUTCOMES[("NICE Actimize Screening<br/>outcomes")]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_IAM["Identity and access<br/>management"]
    SYS_ITSM["IT service management<br/>[SaaS]"]
    SYS_SCREENING_VENDOR["NICE Actimize Screening<br/>[NICE Actimize]"]
    SYS_SIEM["Security Monitoring<br/>[Microsoft Sentinel]"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
    TS_SERVICENOW[/"ServiceNow<br/>[Service management]"/]
  end

  SYS_IAM -->|"Syslog"| SYS_SIEM
  SYS_SIEM -->|"HTTPS"| SYS_ITSM
  SYS_SCREENING_VENDOR -->|"HTTPS"| SYS_SIEM
  SYS_ITSM -.->|"runs on"| TS_SERVICENOW
  SYS_IAM -.->|"runs on"| TS_ENTRA_ID
  SYS_SCREENING_VENDOR -->|"Write"| DA_SCREENING_OUTCOMES

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_SCREENING_OUTCOMES s_data_assets__data_assets;
  class SYS_IAM,SYS_ITSM,SYS_SCREENING_VENDOR,SYS_SIEM s_systems__systems;
  class TS_ENTRA_ID,TS_SERVICENOW s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Security Monitoring — Architecture](../svg/system-architecture--sys-siem.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#4338ca` | systems |
| `#c2410c` | tech services |

7 entities, 6 relationships. Generated from the model; edit the model, not this file.
