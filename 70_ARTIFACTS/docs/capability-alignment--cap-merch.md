# Merchant Acquiring & Sponsorship — Frameworks, Controls, Systems

One capability domain and everything connected to it: its level-1 capabilities, the frameworks it aligns to, the controls that govern it, and the systems that realize it. Click any capability to continue from there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Merchant Acquiring & Sponsorship — Frameworks, Controls, Systems
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Capability["Capability"]
    direction LR
    CAP_MERCH_05{{"Acquiring Chargeback<br/>Processing"}}
    CAP_MERCH_01{{"ISO & Agent Program<br/>Management"}}
    CAP_MERCH{{"Merchant Acquiring &<br/>Sponsorship"}}
    CAP_MERCH_03{{"Merchant Boarding &<br/>Network Sponsorship"}}
    CAP_MERCH_06{{"Merchant Monitoring &<br/>Exposure Management"}}
    CAP_MERCH_04{{"Merchant Settlement &<br/>Funding"}}
    CAP_MERCH_02{{"Merchant Underwriting &<br/>Risk Vetting"}}
  end

  subgraph grp_Framework["Framework"]
    direction LR
    FW_BIAN["BIAN"]
    FW_PCI_DSS["PCI DSS"]
  end

  CAP_MERCH_01 -->|"part of"| CAP_MERCH
  CAP_MERCH_02 -->|"part of"| CAP_MERCH
  CAP_MERCH_03 -->|"part of"| CAP_MERCH
  CAP_MERCH_04 -->|"part of"| CAP_MERCH
  CAP_MERCH_05 -->|"part of"| CAP_MERCH
  CAP_MERCH_06 -->|"part of"| CAP_MERCH
  CAP_MERCH -->|"Aligned to"| FW_BIAN
  CAP_MERCH -->|"Governed by"| FW_PCI_DSS
  CAP_MERCH_01 -->|"Reference Data #gt; Ext…"| FW_BIAN
  CAP_MERCH_02 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_MERCH_03 -->|"Operations and Executio…"| FW_BIAN
  CAP_MERCH_04 -->|"Operations and Executio…"| FW_BIAN
  CAP_MERCH_05 -->|"Sales and Service #gt;…"| FW_BIAN
  CAP_MERCH_06 -->|"Operations and Executio…"| FW_BIAN

  classDef s_capabilities__capabilities fill:#ddd6fe,stroke:#6d28d9,color:#0f172a,stroke-width:1.4px;
  classDef s_frameworks__frameworks fill:#d9f99d,stroke:#4d7c0f,color:#0f172a,stroke-width:1.4px;
  class CAP_MERCH,CAP_MERCH_01,CAP_MERCH_02,CAP_MERCH_03,CAP_MERCH_04,CAP_MERCH_05,CAP_MERCH_06 s_capabilities__capabilities;
  class FW_BIAN,FW_PCI_DSS s_frameworks__frameworks;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Capability,grp_Framework boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Merchant Acquiring & Sponsorship — Frameworks, Controls, Systems](../svg/capability-alignment--cap-merch.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#6d28d9` | capabilities |
| `#4d7c0f` | frameworks |

9 entities, 14 relationships. Generated from the model; edit the model, not this file.
