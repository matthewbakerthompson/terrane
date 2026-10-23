# Analyze complaint signal for conduct risk — Systems, Data and Controls

One process, the systems it uses and in what role, the data it touches, and the controls and policies that apply to it. The process comes from the business layer; everything around it comes from the technology estate.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Analyze complaint signal for conduct risk — Systems, Data and Controls
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_RGOV_06{{"Complaint Oversight &<br/>UDAAP Management"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_COMPLIANCE_005[\"Analyze complaint signal<br/>for conduct risk"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_CRM["Dynamics 365 Customer<br/>Service<br/>[Microsoft]"]
    SYS_DATA_INGEST["Enterprise Data Ingestion<br/>Hub<br/>[Service Bus · Snowflake Data Cloud]"]
    SYS_GRC["Governance, risk and<br/>compliance platform"]
  end

  P_COMPLIANCE_005 -->|"Primary"| SYS_GRC
  P_COMPLIANCE_005 -->|"Supporting"| SYS_CRM
  P_COMPLIANCE_005 -->|"Supporting"| SYS_DATA_INGEST
  P_COMPLIANCE_005 -->|"supports"| CAP_RGOV_06

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_RGOV_06 s_capabilities__capabilities;
  class P_COMPLIANCE_005 s_processes__processes;
  class SYS_CRM,SYS_DATA_INGEST,SYS_GRC s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Analyze complaint signal for conduct risk — Systems, Data and Controls](../svg/process-systems--p-compliance-005.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

5 entities, 4 relationships. Generated from the model; edit the model, not this file.
