# AAC-08 — Impact analysis

`terrane impact` lists what a change to one record affects, for questions like
these:

- We are retiring the mainframe. What breaks?
- This vendor is going away. What stops working?
- We need a four-hour outage on that database. Who do I have to tell?
- This capability is degraded. What could be causing it?

```bash
cd 50_ENGINE && python -m terrane impact SYS-CORE-LEDGER
```

In the app, select anything and press **Impact**. The map highlights everything
affected, across every hop, rather than one hop at a time.

## What it answers

Two questions, kept apart:

**Affected if this changes** — the downstream set. Everything that needs this
thing, directly or transitively. This is the notification list and the
regression scope.

**This depends on** — the upstream set. Everything this thing needs to work.
This is the prerequisite list: what has to be up before it can start, and what
to check first when it is misbehaving.

They are reported separately, because one merged count would mix the two.

## Direction

Depending on something is not the same as being depended on by it, and the
model does not record which way round each relation runs. It has to be stated,
and a direction stated wrong gives a result that points the wrong way.

The rules live in `DEPENDENCY_DIRECTION` and `STYLE_DIRECTION` in
`50_ENGINE/terrane/impact.py`, listed rather than inferred:

| Relation | Which way | Why |
|---|---|---|
| `system_uses_tech_service` | system → service | A system needs what it runs on |
| `product_includes_system` | product → systems | A product is its parts |
| `system_realizes_capability` | capability → system | **Reversed.** A capability is realized by what implements it. The ledger going away degrades Card Issuing; Card Issuing going away does nothing to the ledger |
| `system_reads_writes` | depends on `operation` | A reader needs the data. A writer is what the data needs. `ReadWrite` is both |
| `source_of_truth` | data → system | Data needs whatever masters it |

## Interface direction

An interface has a direction, but **data flow direction is not dependency
direction**:

- **Request-response** — the caller depends on the callee. The card servicing
  API calls the ledger, so the API is downstream of the ledger.
- **Event and Batch** — the *consumer* depends on the *producer*, which is the
  opposite way round. The ledger pushes a nightly extract to the ingestion hub,
  so the hub is downstream of the ledger even though it is the target of the
  interface rather than the source.

That distinction is why `integration_style` is a field on every interface
rather than something guessed from the protocol. Protocol is a bad proxy: MQ
carries both request-response and fire-and-forget, and Kafka is realtime but
still a feed. A guess from the protocol would be wrong for about a quarter of
the estate, with nothing to show which quarter.

Backfilling it from protocol and frequency was a one-time migration. From here
it is explicit in the model, visible in review, and corrected by whoever knows
the interface.

## Distance, and saying how sure you are

In a connected estate most records reach most others at enough hops, so each
result is graded by its distance:

| Distance | Reported as | Read it as |
|---|---|---|
| 1 hop | `direct` | This breaks. Tell them |
| 2 hops | `likely` | This probably degrades. Check |
| 3+ hops | `possible` | Worth a look, not worth a page |

Default depth is 3. `--depth` raises or lowers it, and `--only` restricts what
gets *reported* without restricting what gets *traversed* — a dependency that
runs through a subnet still reaches the system beyond it, so filtering the
subnet out of the report does not hide what is past it.

## What it does not do

**It does not know about redundancy.** Two paths to the same dependency count
as one dependency, not as resilience. A system with a failover it never lists
as a dependency will look more fragile than it is, and one whose failover is
modeled as an ordinary dependency will look the same as one with no failover at
all. Reading this against `resilience` and the DR view is the manual step.

**It does not weight by criticality**, beyond calling out High-criticality
systems in the notes. A hundred `possible` hops on a Tier 3 reporting tool and
one `direct` hop on the authorization switch are not the same finding, and the
tool does not rank them.

**It reports only what the model records.** An integration the model does not
hold is missing from the result, with everything reached through it. The
`graph.orphan` warnings and the CMDB drift report are the two places that gap
shows up; read both before quoting an impact result.
