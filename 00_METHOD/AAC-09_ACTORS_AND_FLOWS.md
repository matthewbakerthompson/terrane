# AAC-09 — Actors and flows

This chapter covers two concepts in the model, actors and flows, and the
diagrams they draw: system context and transaction sequence diagrams. Neither
diagram could be drawn before the concepts existed in the model.

## Actors

A **system context diagram** shows who is outside the estate, what they touch,
and nothing else. It needs an entity for the people and organizations outside
the boundary; before actors existed, the model had fifteen views and none of
them was a context diagram.

```yaml
- actor_id: ACT-CARDHOLDER
  name: Cardholder
  actor_kind: Person        # Person, Role, Organization, External system, Regulator, Device
  internal: "No"
  volume: ~2.4M active accounts
```

`actor_uses_system` records only **entry points** — the systems an actor reaches
directly. Recording everything an actor transitively touches would turn a
context diagram into a landscape.

Keep the set small. If removing an actor would not change a design decision, it
does not belong on the diagram.

## Flows

A flowchart answers *what connects to what*. A sequence diagram answers *what
happens in what order* in a transaction: where the time goes, who is on the
critical path, what happens when step three is slow.

```yaml
- flow_id: FLOW-CARD-AUTH
  name: Card Authorization
  trigger: Cardholder presents a card at a merchant
  target_latency: under 500ms end to end
```

### A step is an interface, not a system

The first version made a step a *system visit* — a flow was an ordered list of
systems. That let a flow describe a hop that does not exist, and the first
diagram rendered showed it:

```
SYS_SCREENING_GATEWAY->>SYS_SCREENING_VENDOR: no interface recorded
Note over SYS_CORE_LEDGER: 2 hop(s) have no interface in the model
```

A step now names an **interface**, so an unrecorded hop cannot be written down.
The sequence diagram is consistent with the integration model by construction,
and the "no interface recorded" branch no longer exists because it cannot happen.

The diagram also takes `integration_style` from each interface: a
request-response hop draws a reply, an event or batch hop does not.

The limit: a flow is a **linear chain**. Branches, retries, and parallel calls
cannot be expressed, so a flow draws one path through a transaction, and one
whose branches matter needs a process model instead.

## Linkage in the app

The entity editor writes an entity's own fields; the linkage editor writes its
relations. Before the linkage editor, the app could create entities but not
connect them.

**Connect** on any entity opens the linkage editor. It offers only the relations
the metamodel allows for that entity type, on the correct end, with the valid
targets to choose from. Four guards keep what it writes valid:

- **Ends are type-checked.** `system_realizes_capability` will not accept a
  capability on the system end, and says so rather than writing it.
- **Duplicates are refused**, including when only the qualifier differs.
- **App-written links go to `10_MODEL/relations/app_edits.yaml`.** Hand-authored
  relation files are never rewritten by a form.
- **Hand-authored links cannot be removed by the app.** They show as
  `hand-authored` and the unlink button is not offered. The app does not edit a
  file it did not create.

Reference fields — `owner_org_id`, `source_of_truth`, and the rest — are now
pickers of valid targets rather than free text, so a dangling reference cannot
be typed in, instead of being caught by the validator afterward.

## The diagrams

| View | What it answers |
|---|---|
| `system-context` | Who is outside, what they touch. The first diagram to draw |
| `actor-channels` | Every way in, split internal from external |
| Flow sequence diagrams | What happens in what order, per transaction |

Flows render to `70_ARTIFACTS/flows/*.mmd` and are listed in the app under
**Flows**.
