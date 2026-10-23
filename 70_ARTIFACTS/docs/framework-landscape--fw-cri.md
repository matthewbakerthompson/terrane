# CRI Profile — Landscape

The capabilities placed in one framework, laid out in the framework's own terms: BIAN's business areas and domains, ITIL's groups of practices, the CRI Profile's functions. It is drawn for every framework something is placed in, including one an organization adds. A capability placed twice in one framework is drawn at its first placement, and its details list every one.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% CRI Profile — Landscape
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Detect["Detect"]
    direction TB
    subgraph grp_Detect__DE_CM_01["DE.CM-01"]
      direction TB
      CAP_SEC_02_01{{"Security Monitoring"}}
      CAP_SEC_02{{"Threat Detection &<br/>Response"}}
    end
  end

  subgraph grp_Extend["Extend"]
    direction TB
    subgraph grp_Extend__EX_CN_01["EX.CN-01"]
      direction TB
      CAP_TPRM_02{{"Contract & SLA Management"}}
    end
    subgraph grp_Extend__EX_DD_01["EX.DD-01"]
      direction TB
      CAP_TPRM_01{{"Vendor Sourcing & Due<br/>Diligence"}}
    end
    subgraph grp_Extend__EX_MM_01["EX.MM-01"]
      direction TB
      CAP_TPRM_03_01{{"Ongoing Third-Party<br/>Monitoring"}}
      CAP_TPRM_03{{"Ongoing Vendor Risk<br/>Monitoring"}}
    end
    subgraph grp_Extend__EX_MM_02["EX.MM-02"]
      direction TB
      CAP_TPRM_03_02{{"Third-Party Performance<br/>Review"}}
    end
    subgraph grp_Extend__EX_TR_01["EX.TR-01"]
      direction TB
      CAP_TPRM_04{{"Vendor Exit & Continuity<br/>Planning"}}
    end
  end

  subgraph grp_Govern["Govern"]
    direction TB
    subgraph grp_Govern__GV_OC_03["GV.OC-03"]
      direction TB
      CAP_DEP_05{{"Deposit Compliance &<br/>Insurance Administration"}}
    end
    subgraph grp_Govern__GV_PO_01["GV.PO-01"]
      direction TB
      CAP_SEC_05{{"Privacy Management"}}
    end
  end

  subgraph grp_Identify["Identify"]
    direction TB
    subgraph grp_Identify__ID_RA_01["ID.RA-01"]
      direction TB
      CAP_SEC_03{{"Vulnerability & Patch<br/>Management"}}
      CAP_SEC_03_01{{"Vulnerability<br/>Identification"}}
    end
  end

  subgraph grp_Protect["Protect"]
    direction TB
    subgraph grp_Protect__PR_AA_01["PR.AA-01"]
      direction TB
      CAP_SEC_01{{"Identity & Access<br/>Management"}}
    end
    subgraph grp_Protect__PR_DS_01["PR.DS-01"]
      direction TB
      CAP_SEC_04{{"Data Protection &<br/>Cryptography"}}
      CAP_SEC_04_01{{"Data-at-Rest Protection"}}
      CAP_PAY_07{{"Tokenization & Credential<br/>Management"}}
    end
    subgraph grp_Protect__PR_DS_02["PR.DS-02"]
      direction TB
      CAP_SEC_04_02{{"Data-in-Transit Protection"}}
    end
    subgraph grp_Protect__PR_PS_02["PR.PS-02"]
      direction TB
      CAP_SEC_03_02{{"Patch & Software<br/>Maintenance"}}
    end
    subgraph grp_Protect__PR_PS_06["PR.PS-06"]
      direction TB
      CAP_TECH_01_02{{"Secure Development"}}
      CAP_TECH_01{{"Solution Delivery &<br/>Engineering"}}
    end
  end

  subgraph grp_Recover["Recover"]
    direction TB
    subgraph grp_Recover__RC_RP_01["RC.RP-01"]
      direction TB
      CAP_TECH_05{{"Business Continuity &<br/>Disaster Recovery"}}
    end
  end

  subgraph grp_Respond["Respond"]
    direction TB
    subgraph grp_Respond__RS_MA_01["RS.MA-01"]
      direction TB
      CAP_SEC_02_02{{"Security Incident Response"}}
    end
  end


  classDef s_capabilities__core fill:#d5cafb,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_capabilities__enable fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.0px;
  class CAP_DEP_05,CAP_PAY_07 s_capabilities__core;
  class CAP_SEC_01,CAP_SEC_02,CAP_SEC_02_01,CAP_SEC_02_02,CAP_SEC_03,CAP_SEC_03_01,CAP_SEC_03_02,CAP_SEC_04,CAP_SEC_04_01,CAP_SEC_04_02,CAP_SEC_05,CAP_TECH_01,CAP_TECH_01_02,CAP_TECH_05,CAP_TPRM_01,CAP_TPRM_02,CAP_TPRM_03,CAP_TPRM_03_01,CAP_TPRM_03_02,CAP_TPRM_04 s_capabilities__enable;
  classDef boundary1 fill:#e7ebf6,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Detect__DE_CM_01,grp_Extend__EX_CN_01,grp_Extend__EX_DD_01,grp_Extend__EX_MM_01,grp_Extend__EX_MM_02,grp_Extend__EX_TR_01,grp_Govern__GV_OC_03,grp_Govern__GV_PO_01,grp_Identify__ID_RA_01,grp_Protect__PR_AA_01,grp_Protect__PR_DS_01,grp_Protect__PR_DS_02,grp_Protect__PR_PS_02,grp_Protect__PR_PS_06,grp_Recover__RC_RP_01,grp_Respond__RS_MA_01 boundary1;
  classDef boundary2 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Detect,grp_Extend,grp_Govern,grp_Identify,grp_Protect,grp_Recover,grp_Respond boundary2;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![CRI Profile — Landscape](../svg/framework-landscape--fw-cri.svg)

**capability tier** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 1.4px | Core |
| 1.0px | Enable |

22 entities, 0 relationships. Generated from the model; edit the model, not this file.

> No edges connected the selected entities.
