# Installment Lending Edge — Architecture

One system, the systems it talks to, and the technology it runs on. The most common whiteboard diagram, generated from the model for any system.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Installment Lending Edge — Architecture
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_System["System"]
    direction LR
    SYS_LENDING_EDGE["Installment Lending Edge"]
    SYS_LENDING_ALB["Installment Lending Load<br/>Balancer"]
  end

  subgraph grp_Technology_Service["Technology Service"]
    direction LR
    TS_AWS_CLOUDFRONT[/"Amazon CloudFront and WAF<br/>[Content delivery network]"/]
    TS_AWS_ALB[/"Application Load Balancer<br/>[Load balancer]"/]
    TS_LENDING_DNS[/"Installment Lending DNS<br/>[Amazon Route 53]"/]
    TS_LENDING_WAF[/"Installment Lending Web<br/>application firewall<br/>[AWS WAF]"/]
    TS_NET_SUB_LEND_PUB_A[/"Lending Public Subnet A<br/>[Subnet]"/]
    TS_NET_SUB_LEND_PUB_B[/"Lending Public Subnet B<br/>[Subnet]"/]
  end

  SYS_LENDING_EDGE -->|"HTTPS"| SYS_LENDING_ALB
  SYS_LENDING_EDGE -.->|"runs on"| TS_AWS_CLOUDFRONT
  SYS_LENDING_EDGE -.->|"runs on"| TS_LENDING_WAF
  SYS_LENDING_EDGE -.->|"runs on"| TS_LENDING_DNS
  SYS_LENDING_ALB -.->|"runs on"| TS_AWS_ALB
  SYS_LENDING_ALB -.->|"runs on"| TS_NET_SUB_LEND_PUB_A
  SYS_LENDING_ALB -.->|"runs on"| TS_NET_SUB_LEND_PUB_B

  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class SYS_LENDING_ALB,SYS_LENDING_EDGE s_systems__systems;
  class TS_AWS_ALB,TS_AWS_CLOUDFRONT,TS_LENDING_DNS,TS_LENDING_WAF,TS_NET_SUB_LEND_PUB_A,TS_NET_SUB_LEND_PUB_B s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_System,grp_Technology_Service boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Installment Lending Edge — Architecture](../svg/system-architecture--sys-lending-edge.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#4338ca` | systems |
| `#c2410c` | tech services |

## Flows across this diagram

Each flow is a recorded sequence of interfaces. The steps drawn on this diagram are numbered; a step whose interface is not on it is marked.

**Installment Loan Application**: An applicant applies for point-of-sale credit. Bureau search, affordability and a decision, with referral to an underwriter when the automated decision declines to take it.

1. Installment Lending Edge → Installment Lending Load Balancer (HTTPS)
2. Installment Lending Load Balancer → Installment Lending Web (HTTPS) — not on this diagram
3. Installment Lending Web → Installment Lending Service (HTTPS) — not on this diagram
4. Installment Lending Service → Customer Identity Service (HTTPS) — not on this diagram
5. Installment Lending Service → Experian Credit Bureau (HTTPS) — not on this diagram
6. Installment Lending Service → Installment Lending Database (PostgreSQL) — not on this diagram
7. Installment Lending Service → Core Card Ledger (MQ) — not on this diagram
8. Installment Lending Service → Installment Lending Async Worker (Kafka) — not on this diagram

8 entities, 7 relationships. Generated from the model; edit the model, not this file.
