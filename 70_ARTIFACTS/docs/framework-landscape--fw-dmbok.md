# DAMA-DMBOK — Landscape

The capabilities placed in one framework, laid out in the framework's own terms: BIAN's business areas and domains, ITIL's groups of practices, the CRI Profile's functions. It is drawn for every framework something is placed in, including one an organization adds. A capability placed twice in one framework is drawn at its first placement, and its details list every one.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% DAMA-DMBOK — Landscape
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Governance["Data Governance"]
    direction LR
    CAP_DATA_01{{"Data Governance &<br/>Stewardship"}}
  end

  subgraph grp_Data_Integration_and_Interoperability["Data Integration and Interoperability"]
    direction LR
    CAP_TPS_03{{"Client Reporting & Data<br/>Exchange"}}
    CAP_DATA_02{{"Data Sourcing &<br/>Integration"}}
  end

  subgraph grp_Data_Quality["Data Quality"]
    direction LR
    CAP_DATA_03{{"Data Quality Management"}}
  end

  subgraph grp_Data_Warehousing_and_Business_Intelligence["Data Warehousing and Business Intelligence"]
    direction LR
    CAP_DATA_04{{"Analytics, Reporting & BI"}}
  end

  subgraph grp_Document_and_Content_Management["Document and Content Management"]
    direction LR
    CAP_DATA_07{{"Records Retention &<br/>Disposition"}}
  end

  subgraph grp_Metadata_Management["Metadata Management"]
    direction LR
    CAP_DATA_05{{"Metadata, Lineage &<br/>Catalog"}}
  end


  classDef s_capabilities__core fill:#d5cafb,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_capabilities__enable fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.0px;
  class CAP_TPS_03 s_capabilities__core;
  class CAP_DATA_01,CAP_DATA_02,CAP_DATA_03,CAP_DATA_04,CAP_DATA_05,CAP_DATA_07 s_capabilities__enable;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Governance,grp_Data_Integration_and_Interoperability,grp_Data_Quality,grp_Data_Warehousing_and_Business_Intelligence,grp_Document_and_Content_Management,grp_Metadata_Management boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![DAMA-DMBOK — Landscape](../svg/framework-landscape--fw-dmbok.svg)

**capability tier** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 1.4px | Core |
| 1.0px | Enable |

7 entities, 0 relationships. Generated from the model; edit the model, not this file.

> No edges connected the selected entities.
