# AAC-11 — Diagram kinds, and the modular blocks below them

*Written as a proposal on 2026-09-01, and all three parts were built the same
day. A count from that day says so; [AAC-04](AAC-04_VIEWS.md#the-shipped-views)
lists the views as they are, and `terrane stats` ends with the library's counts.*

On 2026-09-01 twenty-six things were called views, and they were not the same
kind of thing. Some were architecture diagrams. Some were portfolio maps.
Several were reports that had been drawn as graphs because a graph was the only
renderer available. Drawing them all one way was why some of them looked wrong
however the layout was tuned.

Below that sat a second problem: the modular unit was missing. There were
component types (too small to assemble anything from) and archetypes (a whole
product), and nothing in between to design with.

## Part one: three kinds, not one

### Architecture diagram

Has a **subject** and a **level**. Shows what the subject is composed of, what
it connects to, and where it runs. Read closely, by someone who is about to
change something.

Properties that follow: shapes carry meaning, boundaries are containment and
not grouping, every edge is a real relationship, and the thing should fit on a
page because it is being reasoned about rather than scanned.

Among the shipped views: `system-context`, `system-architecture`,
`product-architecture`, `onboarding`, `network-topology`,
`multi-az-deployment`, `dr-topology`, `tiered-architecture`,
`integration-architecture`.

### Landscape map

No subject: it shows the whole estate, cut one way. Read by scanning, to
find something or to see how it is distributed.

Properties that follow: packing rather than ranking, color carries the cut,
counts matter more than edges, and it can be large because it is scanned
rather than read in order.

Among the shipped views: `application-landscape`, `hosting-estate`,
`lifecycle-portfolio`, `technology-stack`, `capability-map`,
`framework-landscape`, `value-streams`, `vendor-exposure`.

### Report

Answers a question with a set. It is a query whose output is a table, and
drawn as a graph its lines can be read as relationships they are not.

On 2026-09-01: `capability-realization` ("which capabilities have a system"),
`platform-dependencies` ("what is attached to each platform service"),
`data-lineage`, `pii-data-flow`, `target-state-change` and
`value-stream-capabilities` were all this. Six of twenty-six. Every one had
`group_by: type` or a single edge kind, so it showed membership and no
structure. `ownership`, a map then, has become a report since, and
`frameworks`, `control-coverage`, `policy-landscape` and `change-register` were
written as reports.

The Data browser and the Coverage report already show sets as tables. A report
should render as a table by default and offer the graph.

### What it changes

`kind: diagram | map | report` on a view, driving:

| | Diagram | Map | Report |
|---|---|---|---|
| Default layout | layered | packed | table |
| Node shape | by component type | by entity type | n/a |
| Boundaries | containment | grouping | column |
| Size warning at | 40 nodes | none | none |
| Mermaid artifact | yes | yes | markdown table |

A fourth kind, `timeline`, came later, for the change layer's quarters
([AAC-04](AAC-04_VIEWS.md#four-kinds-and-why-it-matters)).

For diagrams the split brings a size warning: an architecture diagram past
about forty boxes no longer fits on a page, and the model should say so rather
than drawing it anyway.

## Part two: the missing layer

### What there was

**Component type** — *a load balancer.* The vocabulary. About fifty of them then,
with a category, a shape, defaults, and what each cloud calls it. Too small to
assemble from one at a time.

**Archetype** — *an AWS product onboarding.* Fourteen entities and twenty-one
relations from six answers. The right size for onboarding a product and too big
to reuse in a design conversation.

There was nothing between those two.

### Building blocks

A **building block** is a handful of component types that always arrive
together, with the relations between them:

```yaml
building_block_id: public-web-tier
name: Public web tier
category: Network
description: >
  Everything between the internet and an application. The point of naming it is
  that it is never one thing: a load balancer with no WAF in front of it is a
  different risk posture, and that difference should be visible.
provides:
  - component_type: cdn
  - component_type: waf
  - component_type: load-balancer
  - component_type: dns
relations:
  - from: cdn
    to: waf
  - from: waf
    to: load-balancer
constraints:
  network_zone: Edge
```

Five or six blocks compose a workload. The same block appears in the AWS
archetype, the Azure one, and by hand in a design review — and when the WAF
requirement changes, it changes in one place.

This is TOGAF's Architecture Building Block, named for TOGAF's distinction
between the two: an **ABB** says *a public web tier*, an **SBB** says
*CloudFront, AWS WAF, and an ALB*. The block holds the ABB; the `providers` map
on each component type already holds the SBB. So a cloud migration is a
re-parameterization: it changes the resolution and leaves the blocks as they are.

### Patterns

A **pattern** is a building block plus the decision: what it is for, what it
costs, when not to use it. `private-egress-to-saas` is three components and one
paragraph that records the decision.

An architecture review board governs patterns. With them modeled, "did this
design use the approved pattern" is a query over the model.

**Built.** Twenty-three patterns in [`27_PATTERNS/`](../27_PATTERNS/README.md),
each with a status (candidate, approved, deprecated, retired), the blocks it
is made of, the controls it is designed to satisfy, and three paragraphs:
intent, what it costs, and when not to use it. Twenty name the reference
pattern in the method repository they implement (`method_ref`), so each house
decision links to the method's standards traceability. An archetype declares
the patterns its shape applies and every instance inherits them onto the
product's `patterns` field; an interface carries `patterns` too, because
three of the method's reference patterns are about how two systems talk, and
the interface is the record of that. The adoption report in
`70_ARTIFACTS/library/patterns.md` is read off both. `terrane validate` refuses a
product or an interface naming a pattern the library does not hold, and
fails on a library that does not load. The parts and the shapes have the
same treatment in `library/modules.md` and `library/shapes.md`: where each part
is used and which products sit on each shape, read off the library and the
model, so the modular layer is readable in the repository without running
anything.

### The chain

```
component type  →  building block  →  pattern  →  module  →  archetype
   a queue          an event tier      outbox      an event    a product
                                                   publisher
```

Each level is the one below plus something the one below cannot say. Blocks
say what a product runs on; modules say what a product is made of, one part
at a time, with parameters. An archetype is composed from modules on blocks,
not written as forty individual entities, and a product keeps the parts it
needs. So a new vendor's diagram is made by choosing parts:
`28_MODULES/` holds the parts of a vendor onboarding and the parts of a built
product, and [AAC-03](AAC-03_ARCHETYPES.md) says how a shape and an instance
pick from them.

Two more things the top of the chain can say, both found by noticing what the
shapes were doing by hand. A module can be a **kit** -- a part made of parts,
so the tenancy, the gateway and the vault every vendor onboarding starts with
have one name, and the two vendor shapes compose it by reference instead of
by copy. And a shape has **slots**: where it varies, the need is named with
the parts that can fill it and a default, and an instance chooses. One shape
had listed its variations in its description as prose, and a second shape
existed to express one of them; a slot holds those variations as parts, with
a default.
Under both, every part declares what it **needs** from the shape, checked
when the library loads and again by `terrane validate` against every shape that
composes or offers it. And a part parameter names the **kind** of shared
service it stands for rather than a service: the block's ABB/SBB split,
applied to parts. The shape's `bind` -- the block's word, lifted to the shape
-- says which service is that kind on its landing zone, so the same part
binds Secrets Manager on the AWS shape and Key Vault on the Azure one, and a
part chosen in a slot binds the right cloud's services without the shape
having listed it. See the [module README](../28_MODULES/README.md).

## Part three: the diagram that is missing

Every architecture diagram in the set is either the whole estate or a product.
A request such as *show me the architecture of the authorization switch* has
no answer here. Focus mode approximates it, but focus is an exploration tool:
it draws a neighborhood, not a designed picture.

In C4 terms the set has **Context** and something like **Deployment**, and no
**Container** level: one system, its internal parts, its dependencies, and
nothing else. The set cannot produce that diagram.

It needs a parameter — *which system* — and views had no parameters then.
`value-stream-capabilities` needs the same mechanism, and works around its
absence by hard-coding one value stream id in its scope.

## What this would take

| | |
|---|---|
| `kind` on views, and reports rendering as tables | Small. Mostly routing. |
| Size warning on diagrams | Small. |
| Building blocks: schema, library, expansion | Medium. The expander already exists for archetypes. |
| Archetypes expressed as blocks | Medium, and it rewrites the six archetype files. **Done**, as version 2 of every shape; see [AAC-03](AAC-03_ARCHETYPES.md#built-on-blocks). |
| Patterns | Small once blocks exist. Mostly prose. **Done.** |
| Parameterized views, and a container diagram | Medium. Views gain parameters; the app gains a picker. |

## Three decisions

1. ~~**Split the kinds, and let reports be tables.**~~ **Done**, into ten
   diagrams, ten maps and six reports that day; reports render as tables in
   the artifacts and in the app, diagrams warn past forty nodes, and the
   generated index is grouped by kind.
2. ~~**Building blocks as the composition unit.**~~ **Done**, including the
   archetypes rewritten on top of them as version 2 of every shape, and the
   patterns above them. That day: forty-eight component types across eight
   categories, fourteen blocks made of them, expansion that resolves the same
   block to different products per cloud, a palette in the app, and every one
   of the estate's thirty-seven technology services typed so shapes and counts
   mean something.
3. ~~**Parameterized views.**~~ **Done.** `parameters` and `render_for` on a
   view; `system-architecture` takes a system and renders one committed diagram
   per high-criticality system, seventeen of them that day. The app gained a
   subject picker, and the generated ids resolve back to the view.

They are independent. Any one is worth doing alone; 1 is the cheapest and 2 is
the one that changes how the repository is used.
