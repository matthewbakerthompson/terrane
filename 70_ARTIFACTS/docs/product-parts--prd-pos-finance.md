# Point-of-Sale Finance — By part

One product drawn by the parts it was composed from: each boundary is a part of the library (the API, the web channel, the datastore, the event publisher), and what sits inside it is what that part made. A system in no boundary was written by hand or came from the landing zone. The same product as the architecture view, cut the other way: not where things run, but which decision in the library put them there.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Point-of-Sale Finance — By part
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_api_service["api-service"]
    direction LR
    OI_POSFIN_API("Point-of-Sale Finance API<br/>[HTTPS]")
    SYS_POSFIN_API["Point-of-Sale Finance<br/>Service<br/>[GKE · Point-of-Sale Finance Cache]"]
  end

  subgraph grp_event_publisher["event-publisher"]
    direction LR
    SYS_POSFIN_EVENTS["Point-of-Sale Finance<br/>Event Publisher<br/>[Pub/Sub]"]
  end

  subgraph grp_relational_datastore["relational-datastore"]
    direction LR
    SYS_POSFIN_DB["Point-of-Sale Finance<br/>Database<br/>[Cloud SQL]"]
    DA_POSFIN_OPERATIONAL[("Point-of-Sale Finance<br/>operational data")]
  end

  subgraph grp_web_channel["web-channel"]
    direction LR
    SYS_POSFIN_WEB["Point-of-Sale Finance Web<br/>[GKE]"]
  end

  TS_GCP_APIGEE[/"Apigee<br/>[API gateway]"/]
  TS_GCP_KMS[/"Cloud KMS<br/>[Key management]"/]
  TS_GCP_MONITORING[/"Cloud Monitoring<br/>[Observability]"/]
  TS_GCP_CLOUD_SQL[/"Cloud SQL for PostgreSQL<br/>[Relational database]"/]
  TS_GCP_GKE[/"Google Kubernetes Engine<br/>[Container platform]"/]
  TS_ENTRA_ID[/"Microsoft Entra ID<br/>[Identity provider]"/]
  TS_POSFIN_BACKUP[/"Point-of-Sale Finance<br/>Backup and recovery<br/>[Backup and DR Service]"/]
  TS_POSFIN_CACHE[/"Point-of-Sale Finance<br/>Cache<br/>[Memorystore]"/]
  TS_POSFIN_DNS[/"Point-of-Sale Finance DNS<br/>[Cloud DNS]"/]
  TS_POSFIN_WAF[/"Point-of-Sale Finance Web<br/>application firewall<br/>[Cloud Armor]"/]
  TS_GCP_PUBSUB[/"Pub/Sub<br/>[Message queue]"/]
  TS_GCP_SECRET_MANAGER[/"Secret Manager<br/>[Secrets manager]"/]

  SYS_POSFIN_WEB --> OI_POSFIN_API
  SYS_POSFIN_API -->|"PostgreSQL"| SYS_POSFIN_DB
  SYS_POSFIN_API -->|"AMQP"| SYS_POSFIN_EVENTS
  SYS_POSFIN_API -.->|"runs on"| TS_GCP_APIGEE
  SYS_POSFIN_API -.->|"runs on"| TS_GCP_GKE
  SYS_POSFIN_API -.->|"runs on"| TS_POSFIN_CACHE
  SYS_POSFIN_API -.->|"runs on"| TS_GCP_MONITORING
  SYS_POSFIN_API -.->|"runs on"| TS_GCP_SECRET_MANAGER
  SYS_POSFIN_WEB -.->|"runs on"| TS_POSFIN_DNS
  SYS_POSFIN_WEB -.->|"runs on"| TS_POSFIN_WAF
  SYS_POSFIN_WEB -.->|"runs on"| TS_GCP_GKE
  SYS_POSFIN_WEB -.->|"runs on"| TS_ENTRA_ID
  SYS_POSFIN_DB -.->|"runs on"| TS_GCP_CLOUD_SQL
  SYS_POSFIN_DB -.->|"runs on"| TS_POSFIN_BACKUP
  SYS_POSFIN_DB -.->|"runs on"| TS_GCP_KMS
  SYS_POSFIN_EVENTS -.->|"runs on"| TS_GCP_PUBSUB
  SYS_POSFIN_API -->|"ReadWrite"| DA_POSFIN_OPERATIONAL
  SYS_POSFIN_DB -->|"ReadWrite"| DA_POSFIN_OPERATIONAL
  OI_POSFIN_API --- SYS_POSFIN_API

  classDef s_data_assets__data_assets fill:#a7f3d0,stroke:#047857,color:#0f172a,stroke-width:1.4px;
  classDef s_offered_interfaces__offered_interfaces fill:#e6ecff,stroke:#6366f1,color:#0f172a,stroke-width:1.4px;
  classDef s_systems__systems fill:#c7d6ff,stroke:#4338ca,color:#0f172a,stroke-width:1.4px;
  classDef s_tech_services__tech_services fill:#fed7aa,stroke:#c2410c,color:#0f172a,stroke-width:1.4px;
  class DA_POSFIN_OPERATIONAL s_data_assets__data_assets;
  class OI_POSFIN_API s_offered_interfaces__offered_interfaces;
  class SYS_POSFIN_API,SYS_POSFIN_DB,SYS_POSFIN_EVENTS,SYS_POSFIN_WEB s_systems__systems;
  class TS_ENTRA_ID,TS_GCP_APIGEE,TS_GCP_CLOUD_SQL,TS_GCP_GKE,TS_GCP_KMS,TS_GCP_MONITORING,TS_GCP_PUBSUB,TS_GCP_SECRET_MANAGER,TS_POSFIN_BACKUP,TS_POSFIN_CACHE,TS_POSFIN_DNS,TS_POSFIN_WAF s_tech_services__tech_services;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_api_service,grp_event_publisher,grp_relational_datastore,grp_web_channel boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Point-of-Sale Finance — By part](../svg/product-parts--prd-pos-finance.svg)

**Hue is the entity type.**

| | Entity type |
|---|---|
| `#047857` | data assets |
| `#6366f1` | offered interfaces |
| `#4338ca` | systems |
| `#c2410c` | tech services |

18 entities, 19 relationships. Generated from the model; edit the model, not this file.
