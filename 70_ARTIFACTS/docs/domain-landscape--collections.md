# Collections — Landscape

One business domain and its immediate neighbors: every system in the domain plus everything one interface away. Smaller and easier to read than the full landscape, and drawn for every domain the systems name.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Collections — Landscape
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Card_Issuing["Card Issuing"]
    direction LR
    SYS_CORE_LEDGER["Core Card Ledger"]
    OI_LEDGER_QUEUE("Core Ledger request queue<br/>[MQ]")
  end

  subgraph grp_Collections["Collections"]
    direction LR
    OI_COLLECT_API("Collections Workspace API<br/>[HTTPS]")
    SYS_COLLECT_STORE["Collections Workspace<br/>Datastore<br/>[Azure SQL]"]
    SYS_COLLECT_API["Collections Workspace<br/>Service<br/>[AKS · Collections Workspace Cache]"]
    SYS_COLLECT_WEB["Collections Workspace Web<br/>[AKS]"]
  end

  subgraph grp_Enterprise_Platform["Enterprise Platform"]
    direction LR
    OI_IDENTITY_API("Customer Identity API<br/>[HTTPS]")
    SYS_IDENTITY_SVC["Customer Identity Service<br/>[AKS]"]
  end

  SYS_DOC["Document management and<br/>archive"]
  SYS_DIALER["Outbound contact platform"]

  SYS_COLLECT_API -->|"FileTransfer"| SYS_DIALER
  SYS_DIALER -->|"AMQP"| SYS_COLLECT_API
  SYS_COLLECT_API -->|"AMQP"| SYS_DOC
  SYS_CORE_LEDGER -->|"FileTransfer"| SYS_DOC
  SYS_COLLECT_API --> OI_IDENTITY_API
  SYS_COLLECT_API --> OI_LEDGER_QUEUE
  SYS_COLLECT_WEB --> OI_COLLECT_API
  SYS_COLLECT_API -->|"TDS"| SYS_COLLECT_STORE
  OI_COLLECT_API --- SYS_COLLECT_API
  OI_IDENTITY_API --- SYS_IDENTITY_SVC
  OI_LEDGER_QUEUE --- SYS_CORE_LEDGER

  classDef s_offered_interfaces__high fill:#b9befa,stroke:#6366f1,color:#0f172a,stroke-width:2.6px;
  classDef s_offered_interfaces__medium fill:#dde3fe,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__high fill:#9aa0ed,stroke:#4338ca,color:#0f172a,stroke-width:2.6px;
  classDef s_systems__medium fill:#becbfb,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  class OI_IDENTITY_API,OI_LEDGER_QUEUE s_offered_interfaces__high;
  class OI_COLLECT_API s_offered_interfaces__medium;
  class SYS_CORE_LEDGER,SYS_IDENTITY_SVC s_systems__high;
  class SYS_COLLECT_API,SYS_COLLECT_STORE,SYS_COLLECT_WEB,SYS_DIALER,SYS_DOC s_systems__medium;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Card_Issuing,grp_Collections,grp_Enterprise_Platform boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Collections — Landscape](../svg/domain-landscape--collections.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |

**criticality** is drawn as border weight and tint, strongest first.

| Border | Value |
|---|---|
| 2.6px | High |
| 1.4px | Medium |

10 entities, 11 relationships. Generated from the model; edit the model, not this file.
