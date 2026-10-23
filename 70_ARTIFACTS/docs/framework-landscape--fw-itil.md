# ITIL 4 — Landscape

The capabilities placed in one framework, laid out in the framework's own terms: BIAN's business areas and domains, ITIL's groups of practices, the CRI Profile's functions. It is drawn for every framework something is placed in, including one an organization adds. A capability placed twice in one framework is drawn at its first placement, and its details list every one.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% ITIL 4 — Landscape
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_General_management["General management"]
    direction TB
    subgraph grp_General_management__Architecture_Management["Architecture Management"]
      direction TB
      CAP_STRAT_04{{"Enterprise Architecture &<br/>Change Portfolio"}}
    end
  end

  subgraph grp_Service_management["Service management"]
    direction TB
    subgraph grp_Service_management__Capacity_and_Performance_Management["Capacity and Performance Management"]
      direction TB
      CAP_TECH_02_02{{"Capacity & Performance<br/>Management"}}
      CAP_TECH_02{{"Platform & Infrastructure<br/>Operations"}}
    end
    subgraph grp_Service_management__Change_Enablement["Change Enablement"]
      direction TB
      CAP_TECH_04_01{{"Change Enablement"}}
      CAP_TPS_06{{"Client-Directed Change<br/>Management"}}
      CAP_TECH_04{{"Release & Change<br/>Management"}}
    end
    subgraph grp_Service_management__IT_Asset_Management["IT Asset Management"]
      direction TB
      CAP_TECH_07{{"End-User Computing &<br/>Workplace Technology"}}
      CAP_TECH_07_01{{"IT Asset Management"}}
    end
    subgraph grp_Service_management__Incident_Management["Incident Management"]
      direction TB
      CAP_TECH_03_02{{"Incident Management"}}
      CAP_TECH_03{{"Service Management &<br/>Incident Response"}}
    end
    subgraph grp_Service_management__Problem_Management["Problem Management"]
      direction TB
      CAP_TECH_03_03{{"Problem Management"}}
    end
    subgraph grp_Service_management__Release_Management["Release Management"]
      direction TB
      CAP_TECH_04_02{{"Release Management"}}
    end
    subgraph grp_Service_management__Service_Continuity_Management["Service Continuity Management"]
      direction TB
      CAP_TECH_05{{"Business Continuity &<br/>Disaster Recovery"}}
    end
    subgraph grp_Service_management__Service_Desk["Service Desk"]
      direction TB
      CAP_TECH_03_01{{"Service Desk"}}
    end
    subgraph grp_Service_management__Service_Request_Management["Service Request Management"]
      direction TB
      CAP_TECH_07_02{{"Service Request Management"}}
    end
    subgraph grp_Service_management__Service_Validation_and_Testing["Service Validation and Testing"]
      direction TB
      CAP_TECH_08{{"Quality Engineering &<br/>Testing"}}
    end
  end

  subgraph grp_Technical_management["Technical management"]
    direction TB
    subgraph grp_Technical_management__Deployment_Management["Deployment Management"]
      direction TB
      CAP_TECH_04_03{{"Deployment Management"}}
    end
    subgraph grp_Technical_management__Infrastructure_and_Platform_Management["Infrastructure and Platform Management"]
      direction TB
      CAP_TECH_06{{"Enterprise Integration &<br/>API Management"}}
      CAP_TECH_02_01{{"Infrastructure & Platform<br/>Management"}}
    end
    subgraph grp_Technical_management__Software_Development_and_Management["Software Development and Management"]
      direction TB
      CAP_TECH_01_01{{"Software Development &<br/>Management"}}
      CAP_TECH_01{{"Solution Delivery &<br/>Engineering"}}
    end
  end


  classDef s_capabilities__core fill:#d5cafb,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_capabilities__direct fill:#b79bf1,stroke:#6d28d9,color:#0f172a,stroke-width:2.6px;
  classDef s_capabilities__enable fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.0px;
  class CAP_TPS_06 s_capabilities__core;
  class CAP_STRAT_04 s_capabilities__direct;
  class CAP_TECH_01,CAP_TECH_01_01,CAP_TECH_02,CAP_TECH_02_01,CAP_TECH_02_02,CAP_TECH_03,CAP_TECH_03_01,CAP_TECH_03_02,CAP_TECH_03_03,CAP_TECH_04,CAP_TECH_04_01,CAP_TECH_04_02,CAP_TECH_04_03,CAP_TECH_05,CAP_TECH_06,CAP_TECH_07,CAP_TECH_07_01,CAP_TECH_07_02,CAP_TECH_08 s_capabilities__enable;
  classDef boundary1 fill:#e7ebf6,stroke:#8f9bb5,color:#3b4a6b;
  class grp_General_management__Architecture_Management,grp_Service_management__Capacity_and_Performance_Management,grp_Service_management__Change_Enablement,grp_Service_management__IT_Asset_Management,grp_Service_management__Incident_Management,grp_Service_management__Problem_Management,grp_Service_management__Release_Management,grp_Service_management__Service_Continuity_Management,grp_Service_management__Service_Desk,grp_Service_management__Service_Request_Management,grp_Service_management__Service_Validation_and_Testing,grp_Technical_management__Deployment_Management,grp_Technical_management__Infrastructure_and_Platform_Management,grp_Technical_management__Software_Development_and_Management boundary1;
  classDef boundary2 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_General_management,grp_Service_management,grp_Technical_management boundary2;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![ITIL 4 — Landscape](../svg/framework-landscape--fw-itil.svg)

**capability tier** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | Direct |
| 1.4px | Core |
| 1.0px | Enable |

21 entities, 0 relationships. Generated from the model; edit the model, not this file.

> No edges connected the selected entities.
