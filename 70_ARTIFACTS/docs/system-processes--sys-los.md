# Indirect loan origination system — Processes and Capabilities

One system, every process that uses it and in what role, and the capabilities those processes support. This shows the business impact of changing the system. A long list against a low criticality rating is worth a second look.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Indirect loan origination system — Processes and Capabilities
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_LEND_02_01{{"Dealer Application Intake"}}
    CAP_LEND_01{{"Dealer Network & Program<br/>Management"}}
    CAP_RGOV_09{{"Fair Lending Monitoring"}}
    CAP_LEND_02{{"Indirect Application &<br/>Underwriting"}}
    CAP_LEND_02_02{{"Indirect Credit Decision &<br/>Counteroffer"}}
    CAP_LEND_03{{"Loan Boarding & Dealer<br/>Funding"}}
  end

  subgraph grp_Process["Process"]
    direction LR
    P_LENDING_006[\"Board loan and fund dealer"/]
    P_LENDING_004[\"Decide indirect loan and<br/>return terms"/]
    P_LENDING_002[\"Monitor dealer performance<br/>and program compliance"/]
    P_LENDING_003[\"Receive and validate<br/>dealer-submitted<br/>application"/]
    P_LENDING_005[\"Review contract package<br/>and clear stipulations"/]
    P_COMPLIANCE_006[\"Test credit decisions and<br/>pricing for fair lending"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_LOS["Indirect loan origination<br/>system"]
  end

  P_LENDING_002 -->|"Supporting"| SYS_LOS
  P_LENDING_003 -->|"Primary"| SYS_LOS
  P_LENDING_004 -->|"Primary"| SYS_LOS
  P_LENDING_005 -->|"Primary"| SYS_LOS
  P_LENDING_006 -->|"Supporting"| SYS_LOS
  P_COMPLIANCE_006 -->|"Supporting"| SYS_LOS
  P_LENDING_002 -->|"supports"| CAP_LEND_01
  P_LENDING_003 -->|"supports"| CAP_LEND_02_01
  P_LENDING_004 -->|"supports"| CAP_LEND_02_02
  P_LENDING_005 -->|"supports"| CAP_LEND_03
  P_LENDING_006 -->|"supports"| CAP_LEND_03
  P_COMPLIANCE_006 -->|"supports"| CAP_RGOV_09
  P_LENDING_003 -->|"supports"| CAP_LEND_02
  P_LENDING_004 -->|"supports"| CAP_LEND_02

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_processes__processes fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class CAP_LEND_01,CAP_LEND_02,CAP_LEND_02_01,CAP_LEND_02_02,CAP_LEND_03,CAP_RGOV_09 s_capabilities__capabilities;
  class P_COMPLIANCE_006,P_LENDING_002,P_LENDING_003,P_LENDING_004,P_LENDING_005,P_LENDING_006 s_processes__processes;
  class SYS_LOS s_systems__systems;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Indirect loan origination system — Processes and Capabilities](../svg/system-processes--sys-los.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#0369a1` | processes |
| `#4338ca` | systems |

13 entities, 14 relationships. Generated from the model; edit the model, not this file.
