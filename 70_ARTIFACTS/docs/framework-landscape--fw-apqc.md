# APQC Process Classification Framework — Landscape

The capabilities placed in one framework, laid out in the framework's own terms: BIAN's business areas and domains, ITIL's groups of practices, the CRI Profile's functions. It is drawn for every framework something is placed in, including one an organization adds. A capability placed twice in one framework is drawn at its first placement, and its details list every one.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% APQC Process Classification Framework — Landscape
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_1_0_Develop_Vision_and_Strategy["1.0 Develop Vision and Strategy"]
    direction TB
    CAP_STRAT_03{{"Business Performance<br/>Management"}}
    CAP_STRAT_05{{"Merger, Acquisition &<br/>Portfolio Transaction"}}
  end

  subgraph grp_11_0_Manage_External_Relationships["11.0 Manage External Relationships"]
    direction TB
    CAP_PART_04{{"Client Service Level &<br/>Performance Management"}}
    CAP_PART_05{{"Co-Brand & Program Partner<br/>Management"}}
    CAP_CORP_05{{"Corporate Communications"}}
    CAP_CORP_03{{"Legal & Contract Counsel"}}
    CAP_PART_03{{"Servicing Client<br/>Origination & Contracting"}}
  end

  subgraph grp_12_0_Develop_and_Manage_Business_Capabilities["12.0 Develop and Manage Business Capabilities"]
    direction TB
    CAP_STRAT_04{{"Enterprise Architecture &<br/>Change Portfolio"}}
  end

  subgraph grp_6_0_Develop_and_Manage_Human_Capital["6.0 Develop and Manage Human Capital"]
    direction TB
    CAP_CORP_02{{"Learning, Licensing &<br/>Certification"}}
    CAP_CORP_01{{"Workforce Management & HR"}}
  end

  subgraph grp_8_0_Manage_Financial_Resources["8.0 Manage Financial Resources"]
    direction TB
    CAP_FIN_05{{"Accounts Payable &<br/>Procurement Finance"}}
  end

  subgraph grp_9_0_Acquire__Construct_and_Manage_Assets["9.0 Acquire, Construct and Manage Assets"]
    direction TB
    CAP_CORP_04{{"Facilities & Workplace<br/>Operations"}}
  end


  classDef s_capabilities__direct fill:#b79bf1,stroke:#6d28d9,color:#0f172a,stroke-width:2.6px;
  classDef s_capabilities__enable fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.0px;
  class CAP_PART_03,CAP_PART_04,CAP_PART_05,CAP_STRAT_03,CAP_STRAT_04,CAP_STRAT_05 s_capabilities__direct;
  class CAP_CORP_01,CAP_CORP_02,CAP_CORP_03,CAP_CORP_04,CAP_CORP_05,CAP_FIN_05 s_capabilities__enable;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_1_0_Develop_Vision_and_Strategy,grp_11_0_Manage_External_Relationships,grp_12_0_Develop_and_Manage_Business_Capabilities,grp_6_0_Develop_and_Manage_Human_Capital,grp_8_0_Manage_Financial_Resources,grp_9_0_Acquire__Construct_and_Manage_Assets boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![APQC Process Classification Framework — Landscape](../svg/framework-landscape--fw-apqc.svg)

**capability tier** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | Direct |
| 1.0px | Enable |

12 entities, 0 relationships. Generated from the model; edit the model, not this file.

> No edges connected the selected entities.
