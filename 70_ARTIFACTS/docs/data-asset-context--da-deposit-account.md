# Deposit account and CD record — Where It Lives and Who Uses It

One data asset in full: the system that masters it, the systems that read or write it, the processes that use it, the controls that govern it and the policies it is subject to. The page a privacy or audit question starts from.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Deposit account and CD record — Where It Lives and Who Uses It
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Data_Asset["Data Asset"]
    direction LR
    DA_DEPOSIT_ACCOUNT[("Deposit account and CD<br/>record")]
  end

  subgraph grp_Process["Process"]
    direction LR
    P_DEPOSITS_005[\"Accrue and pay deposit<br/>interest"/]
    P_DEPOSITS_008[\"Administer deposit<br/>insurance records and<br/>escheatment"/]
    P_DEPOSITS_003[\"Issue brokered CDs through<br/>the broker network"/]
    P_COMPLIANCE_007[\"Monitor transactions for<br/>suspicious activity"/]
    P_DEPOSITS_002[\"Open and fund direct<br/>deposit account"/]
    P_DEPOSITS_007[\"Process CD maturity,<br/>renewal, and early<br/>withdrawal"/]
    P_DEPOSITS_006[\"Produce deposit tax<br/>reporting"/]
    P_DEPOSITS_001[\"Set deposit rates and<br/>product terms"/]
    P_DEPOSITS_004[\"Settle brokered CDs and<br/>keep the position"/]
  end

  subgraph grp_System["System"]
    direction LR
    SYS_BROKER_GW["Brokered deposit<br/>settlement gateway"]
    SYS_DEPOSIT["Deposit platform"]
    SYS_AML["Financial crimes platform"]
    SYS_KYC["Identity verification"]
    SYS_TREASURY["Treasury management"]
  end

  SYS_DEPOSIT -.->|"masters"| DA_DEPOSIT_ACCOUNT
  SYS_DEPOSIT -->|"ReadWrite"| DA_DEPOSIT_ACCOUNT
  SYS_BROKER_GW -->|"Write"| DA_DEPOSIT_ACCOUNT
  SYS_TREASURY -->|"Read"| DA_DEPOSIT_ACCOUNT
  SYS_KYC -->|"Read"| DA_DEPOSIT_ACCOUNT
  SYS_AML -->|"Read"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_001 -->|"Read"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_002 -->|"Write"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_003 -->|"Write"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_004 -->|"Both"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_005 -->|"Both"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_006 -->|"Read"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_007 -->|"Both"| DA_DEPOSIT_ACCOUNT
  P_DEPOSITS_008 -->|"Read"| DA_DEPOSIT_ACCOUNT
  P_COMPLIANCE_007 -->|"Read"| DA_DEPOSIT_ACCOUNT

  classDef s_data_assets__restricted fill:#70c9a7,stroke:#047857,color:#0f172a,stroke-width:2.6px;
  classDef s_processes__default fill:#bae6fd,stroke:#0369a1,color:#0f172a,stroke-width:1.1px;
  classDef s_systems__default fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.1px;
  class DA_DEPOSIT_ACCOUNT s_data_assets__restricted;
  class P_COMPLIANCE_007,P_DEPOSITS_001,P_DEPOSITS_002,P_DEPOSITS_003,P_DEPOSITS_004,P_DEPOSITS_005,P_DEPOSITS_006,P_DEPOSITS_007,P_DEPOSITS_008 s_processes__default;
  class SYS_AML,SYS_BROKER_GW,SYS_DEPOSIT,SYS_KYC,SYS_TREASURY s_systems__default;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Data_Asset,grp_Process,grp_System boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Deposit account and CD record — Where It Lives and Who Uses It](../svg/data-asset-context--da-deposit-account.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#0369a1` | processes |
| `#4338ca` | systems |

**classification** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | Restricted |
| 1.1px | default |

15 entities, 15 relationships. Generated from the model; edit the model, not this file.
