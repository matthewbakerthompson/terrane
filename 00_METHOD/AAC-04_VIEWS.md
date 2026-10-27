# AAC-04 — Views

A view is a query over the model rather than a drawing. It names properties and never
names a system, so an application added to the model appears in every view whose
filter it matches, with no view edited.

## Anatomy

```yaml
view_id: application-landscape
title: Application Landscape
description: >
  Every live and planned system, grouped by business domain.
layout: LR                       # LR, RL, TB, BT
group_by: company_domain         # any field, or `type`
node_label: name
renderers: [mermaid, structurizr]

scope:
  include:
    - type: systems
      where:
        status: [Active, Planned]
  expand:
    - relation: interfaces
      depth: 1
      types: [systems]
  exclude:
    - type: systems
      where:
        tags_any: [hide-from-landscape]

edges:
  - via: interfaces
    label: protocol

style:
  color_by: criticality

limits:
  max_nodes: 60
```

## Boundaries

`group_by` takes one field, or a list of them for nested containers:

```yaml
group_by: company_domain                                       # one level
group_by: [cloud_provider, cloud_account, region, network_zone] # nested
```

Nested boundaries are how an infrastructure view gets drawn: provider, then
account, then region, then network tier, each derived from a field rather than
placed by hand. A system added with those fields set lands inside the right
four boxes with no change to the view.

A boundary can also come from a relation rather than a field, written
`relation@target`: the qualifier values of the record's rows in that relation
whose other end is `target`. This is how a capability is placed on a
framework's landscape: where it sits is a row in
`capability_references_framework`, with the place written in the row's `ref`
as a path ([AAC-12](AAC-12_FRAMEWORKS.md)). `#n` takes one level of the path,
so a landscape nests as the framework does, and a view about one framework
names it with a token the subject fills in:

```yaml
group_by:
  - "capability_references_framework@{framework}#1"
  - "capability_references_framework@{framework}#2"
scope:
  include:
    - type: capabilities
      where:
        "capability_references_framework@{framework}": {exists: true}
```

A record with several rows for the target is drawn at the first, in
alphabetical order, when a level is asked for; without one it sits in a group
named for all of them, joined with `; `. The same key works in `where`, with
`exists`, `not` or a list of values. A key that names no relation, or a relation that carries no
value to group by, is refused when the view resolves.

Two collapses keep a partially populated model drawing a smaller diagram rather
than a broken one:

* **A level that is blank is dropped**, wherever it appears in the path. A SaaS
  system with no account of ours nests under its provider and region directly,
  instead of sitting inside two boxes labeled `Unassigned`.
* **Consecutive identical levels collapse to one.** An on-premise system whose
  provider and network zone are both `On-prem` gets a single boundary, not a box
  inside an identical box.

Boundary identity is the whole path, not the leaf, so `Private-App` in two
different accounts stays two different boxes.

**Lanes.** The boundaries of one field are laid out in the field's own
order, not in the order the edges between them happen to suggest: a tier
diagram reads edge to data whatever the traffic does, and a lifecycle view
reads proposed to retired. A grouped field with a reading order takes it by
default: the network tiers, a lifecycle `status`, and the ordinal scales the
legend lists in order (`criticality`, `service_tier`, `classification`,
`capability_tier` and the rest). A field that is merely enumerated, a
provider or a kind of actor, has no reading order and its boundaries follow
the edges, which put what talks most next to each other. A view can give
its own order with `lanes`, a list for the innermost `group_by` field or a
mapping of field to values, or turn the ordering off with `lanes: false`:

```yaml
group_by: network_zone
lanes: [Edge, Public, Private-App, Private-Data, Shared-Services, On-prem]
```

A value the lanes do not name follows the named ones. The order is honored
by the committed Mermaid, which declares the boundaries in it, and by the
app, which gives each laned boundary one rank in that order and routes the
edges around it. Inside a lane, what nothing connects to runs along the
band in rows rather than stacking across it, so a tier reads as a band and
not a tower.

## Filters

Inside a `where` clause:

| Form | Meaning |
|---|---|
| `status: Active` | Equals |
| `status: [Active, Planned]` | Is one of |
| `status: {not: [Retired]}` | Is not one of |
| `provider: {exists: true}` | Field is present and non-empty |
| `tags_any: [vendor, legacy]` | Has at least one of these tags |
| `tags_all: [vendor, critical]` | Has all of these tags |
| `tags_none: [network-fabric]` | Has none of these tags |
| `id_in: [SYS-A, SYS-B]` | Explicit ids |
| `id_prefix: [SYS-CARDSVC]` | Id starts with |
| `has_any: [system_governed_by_control]` | At least one of these relations exists |
| `has_all: [interfaces, system_reads_writes]` | All of these relations exist |
| `has_none: [system_governed_by_control]` | None of these relations exists |

The `has_` forms take relation names rather than fields, and ask whether the
relation exists at all — which nothing on the record itself can answer. They
accept anything `expand` accepts: a relation table, a reference field such as
`policy_id`, the pseudo-relations `interfaces`, `owner` and `source_of_truth`,
or `any` for a neighbor of any kind. Resolution runs through the same function
`expand` uses, so a filter and the expansion it guards cannot drift apart, and
a misspelled relation fails loudly in both places instead of matching nothing.

`system-governance` uses `has_any` to leave out systems with nothing to draw. It
renders one diagram per system an auditor would ask about, and a datastore with
no control of its own and no capability to inherit one through rendered as a
single box beside neighbors that rendered fully. Dropping the diagram does not
hide the gap — `governance.no_control` still fires on that system and the
coverage report still counts it.

`has_none` is the same test pointed the other way, and is how a gap report says
"every Restricted system with no control on it" without a curated list.

A view built on `id_in` lists its members, so it does not pick up the next system
that would match. It suits a fixed set, such as a specific migration wave or a named
remediation program; anything that should grow is scoped with a filter instead.

`archetype_instance` scopes to a product without listing its parts.
`product-card-servicing` uses it, and stays correct when the product gains or
loses a component.

## Expansion

`expand` pulls in neighbors of whatever `include` selected.

```yaml
expand:
  - relation: interfaces      # or any relation name, or `any`
    depth: 1
    types: [systems]          # restrict what gets pulled in
```

`relation: any` follows every relation and both interface directions. `depth` above 1
grows fast — in a connected estate, depth 3 from anything is usually most of it — so
pair it with `types` and a `max_nodes` limit.

Order is fixed and matters: include, then expand, then exclude. Exclusion runs last, so
you can exclude something that expansion would otherwise have dragged in.

## Edges

```yaml
edges:
  - via: interfaces           # system to system through an interface entity
    label: protocol           # label from a field on the interface
  - via: system_uses_tech_service
  - via: source_of_truth      # data asset to its system of record
    text: system of record    # fixed label
```

`via` takes any relation name, plus two pseudo-relations: `interfaces` and
`source_of_truth`, which are modeled as fields rather than relation rows.

An edge is only drawn when both endpoints are in scope. That is why a view can render
nodes and no edges — the `view.no_edges` warning — and it usually means the `edges`
clause names a relation none of the selected entities participate in.

A view that takes a subject and whose `render_for` selects nothing is reported as
`view.no_subjects`, a warning: an onboarding view in a model with no product on a
shape yet has nothing to draw and nothing wrong with it. It is not bound to nothing
and called unresolvable.

## Limits, and why Mermaid has them

`limits.max_nodes` cuts a diagram, a map or a timeline deterministically and says so,
both in the render output and as a note in the generated Markdown: pins first, then
what the scope names, then the rest by id.

A report is never cut. It is a table and has no page to fit, and a table cut at its
limit lies: the capability realization report, cut at sixty, listed five of its 67 rows.
Past its limit a report is listed whole and says so, in the same note and as the
`view.past_limit` warning, because a table that has grown that far may have a scope
that stopped filtering.

Mermaid's layout degrades noticeably past roughly forty nodes: edges cross, subgraphs
stretch, and the result is correct but hard to read. There are two responses, used
together:

- **Slice.** A landscape view that needs a hundred nodes is usually three views that
  each need thirty. `group_by` plus a domain filter is normally the cut.
- **Use Structurizr for the big one.** Any view listing `structurizr` in `renderers`
  is also emitted into `70_ARTIFACTS/structurizr/workspace.dsl`, which handles large
  landscapes properly.

Hitting the limit is a warning rather than an error, so a view that grows past it keeps
rendering — truncated and labeled — rather than breaking the build on the day someone
adds a system.

## Labels that do not collide

Two things in the app keep labels from overlapping. Boundary names are placed inside
their own box, top-left, by arithmetic on the box and the text, so a
boundary never names itself on top of its neighbor. Edge labels are placed
after every layout by a pass that tries a ladder of positions around each
edge's midpoint and keeps the first that overlaps no node and no label
already placed; an edge with no clear spot shows its label on hover and
selection only. Mermaid has no such pass; the committed artifacts are the
record, and the app is where a diagram is read.

## Sketching a view

A query answers a standing question. A sketch in the app is for a chosen set
instead, *these nine things, drawn together*, such as the picture wanted for
one review. A sketch is never the artifact: it is a set of ids kept in the
browser, and it can only be written back in the two forms the repository has.

**As a view.** The sketch becomes a file in `30_VIEWS/` whose scope is the
explicit list, one `id_in` clause per entity type, with every edge between the
things in it, and whatever `group_by`, `color_by` and layout the form was
given:

```yaml
scope:
  include:
    - type: systems
      where:
        id_in: [SYS-SCREENING-EGRESS, SYS-SCREENING-GATEWAY, SYS-SCREENING-VENDOR]
    - type: interfaces
      where:
        id_in: [INT-SCREENING-EGRESS-VENDOR, INT-SCREENING-GATEWAY-EGRESS]
```

It renders with every other view from then on, and it is saved through the
same door as a typed view, so it is validated the same way. The scope is a
list on purpose: a choice written as a list is one a reviewer can read
without running anything. It is widened into a predicate in the editor when
the picture turns out to answer a standing question.

**As a module.** The same sketch can go the other way, into `28_MODULES/`,
which is how the library grows from work already done. See
[AAC-03](AAC-03_ARCHETYPES.md) and the module README for what that writes.

A sketch grows from the map: the Sketch button on anything in the inspector,
*Add all on screen* for a screenful, *Add connected* for everything one hop
from the selected thing, by relation, with the ones the sketch does not need
unticked. What is already picked wears a halo on every view. A sketch can
also create: *New…* opens the entity editor with the placement of the picked
things filled in, and *Connect…* creates the interface between the selected
system and another picked one. Both go through the same form, validation and
file as anything made by hand; the sketch only fills in what it knows.

## The shipped views

| View | What it answers |
|---|---|
| `application-landscape` | What do we run, grouped by domain, colored by criticality |
| `product-card-servicing` | What is this product, and what does it touch |
| `product-architecture` | One product drawn whole: every system its shape produced, what each runs on, and everything one hop away. Takes a subject |
| `product-parts` | The same product cut by the part each thing came from: a boundary per part of the library, what sits outside it written by hand or shared. Takes a subject |
| `parts-in-use` | Every system a part of the library made, grouped by the part: which parts the estate leans on, and which products share them |
| `capability-realization` | Which systems realize which capabilities. Thin coverage is the finding |
| `pii-data-flow` | What holds personal data, who masters it, who reads it. The privacy assessment view |
| `platform-dependencies` | What breaks if we touch this platform service |
| `target-state-change` | What is planned, what it connects to today, and the work package delivering it |
| `onboarding` | One product on a shape, drawn as what its onboarding creates: account, region, network tier; for a bought one, the boundary and the controls on it. Takes a subject, one per product on a shape |
| `hosting-estate` | The estate cut by where it runs |
| `domain-landscape` | One business domain plus one hop, drawn for every domain the systems name: the level between the landscape and a system |
| `vendor-exposure` | Third-party systems by tag, and what they are wired into |
| `network-topology` | The fabric: VPCs, subnets, gateways, and both paths back to the data center |
| `tiered-architecture` | The estate as tiers — the classic layered picture, with the tiers read off a field |
| `multi-az-deployment` | One account by region and zone. A tier in only one zone is the finding |
| `dr-topology` | Primary and recovery regions, and the replication between them |
| `integration-architecture` | Systems by the role they play, with the protocol on every edge |
| `harvested-estate` | The systems the business layer harvested, with the connections drafted from the process map, Proposed until an owner confirms or strikes them |
| `capability-map` | The whole capability map on one page: every level-1 capability in its domain, the domains banded Direct / Core / Enable, and a framework's placements marked on it when one is chosen |
| `value-streams` | The value streams and their stages, in order, with exit criteria |
| `value-stream-capabilities` | One stream, its stages, and what each stage depends on |
| `system-context` | Who is outside the estate and what they touch. The first diagram to draw |
| `actor-channels` | Every way in, internal parties separated from external |
| `ownership` | Every system under the org unit accountable for it |
| `technology-stack` | What we run on, by the job each service does |
| `lifecycle-portfolio` | The estate by where each system is in its life |
| `data-lineage` | Where each asset is mastered, and who else reads or writes it |
| `data-landscape` | Every data asset by business domain, shaded by classification |
| `data-dissemination` | Each data asset and the one system that masters it. An asset with no line has no system of record |
| `data-and-processes` | Every process that reads or changes a Restricted data asset, with the kind of access on the line |
| `restricted-data-governance` | The Restricted data assets, the system that masters each, and the controls and policies over them |
| `data-asset-context` | One data asset: the system that masters it, who reads or writes it, and the processes, controls and policies on it. Takes a subject |
| `frameworks` | Every framework against every capability domain, in one grid: how firmly the domain follows it, and how many of its capabilities are placed in it |
| `framework-landscape` | One framework's own shape, with the capabilities placed in it. Takes a subject, one per framework something is placed in |
| `capability-alignment` | One domain: its children, frameworks and references, controls, processes, and the systems that realize it. Takes a subject |
| `process-landscape` | Every process under the value stream it serves, tinted by criticality |
| `process-systems` | One process: the systems it uses and in what role, the data, the controls. Takes a subject |
| `system-processes` | One system: every process that uses it and the capabilities they support. Its reach. Takes a subject |
| `hub-and-spoke` | One hub and its spokes, drawn as a wheel. Takes a subject |
| `system-architecture` | One system, what it talks to, and what it runs on. Takes a subject |
| `control-coverage` | Every control, and what the estate says enforces it |
| `policy-landscape` | Every policy, the controls under it, and what it binds |
| `system-governance` | One system and everything that obliges it, including controls reached through the capabilities it realizes. Takes a subject |
| `change-evidence-chain` | The systems that record what changed and who knew: the pipeline, service management, work tracking, the risk register, the people system and monitoring |
| `change-roadmap` | Every work package under way, inside its roadmap and ordered by start quarter, with what it builds and what it changes |
| `change-register` | Which package sits on which roadmap, on whose decision, and which decisions reach the estate with no delivery behind them |
| `change-footprint` | One work package: the systems it builds or changes, and the data, capabilities and processes that depend on them. Takes a subject |

Each is a filter. `change-evidence-chain` names the ten systems of the evidence
chain by id, and `harvested-estate` leaves the same ten out; no other view names
a system.

## Drawing infrastructure

The infrastructure diagrams use the nested boundaries above rather than a
separate mechanism. Three things make them work:

**Placement is a field, not a position.** `cloud_provider`, `cloud_account`,
`region`, `availability_zone` and `network_zone` on each entity give the
boundaries, and the fields decide where a box goes.

**Zones live on subnets, not on systems.** A load-balanced service spans both
zones and so has no zone of its own. Putting the zone on the subnet and
attaching systems to subnets means a multi-AZ diagram draws without cloning
every system once per zone — and a system pinned to one zone
stands out, because it is the only kind that carries the field.

**Fabric is tagged, not inferred.** `network-topology` scopes on
`tags_any: [network-fabric]` rather than `service_category: Network`, because
that category also holds managed services like the load balancer and the CDN.
Those have no account of their own and rendered as loose boxes with nothing
connected to them.

## A view can take a subject

`parameters` lets a view be about one subject, such as *the architecture of the
authorization switch*, rather than the whole estate:

```yaml
parameters:
  - name: system
    type: systems
    required: true

scope:
  include:
    - type: systems
      where:
        id_in: ["{system}"]

render_for:
  parameter: system
  type: systems
  where:
    criticality: [High]
```

The scope binds to the id, because that is what it matches on. The title and
description bind to the **name**, so the diagram is titled with the system's
name rather than `SYS-AUTH-SWITCH`.

`render_for` turns one view into a set of committed artifacts: one per
high-criticality system, regenerated on every render, named
`system-architecture--sys-auth-switch`. The selection is a query rather than a
list, so a high-criticality system added to the model gets its architecture
diagram on the next render. Those generated names resolve back to the view in
the app.

Resolving a parameterized view unbound is refused rather than returning
nothing: an unreplaced `{system}` would match no entities and look like an
empty model instead of a missing argument.

A subject need not be a record. A business domain is a word on the systems,
`Servicing` on eight of them, with no record of its own, so the domain's
landscape takes a value of the field instead of an id:

```yaml
parameters:
  - name: domain
    field: company_domain

render_for:
  parameter: domain
  type: systems
  field: company_domain
  where:
    status: [Active, Planned]
```

It is drawn once for each value the selected systems carry, so a ninth domain
gets its landscape the day a system names it, and an estate whose domains are
Claims and Underwriting gets theirs rather than a Servicing view it cannot
draw. A value no record carries is refused. Each subject's committed file is
named by a slug of it: `domain-landscape--risk-and-compliance`.

## From one level to the next

A large estate is read at levels: the application landscape, a domain, a
system, and where the system runs. Each is a view about one thing, and a view
says the level above it:

```yaml
view_id: system-architecture
up: domain-landscape
```

`up` names a view; what that view is drawn for is read off the subject. A
system's architecture goes up to the landscape of the domain the system
carries in `company_domain`, and `domain-landscape` says `up:
application-landscape`. A level the subject has no value for (a system no
domain names) is passed over and the chain goes on above it. In the app the
chain is the crumb over the title: *Diagrams / Application Landscape /
Servicing*, each level a click.

Down goes the other way and needs no key. Every box lists, under
**Diagrams**, the views about it (each view with a parameter of its type),
about what contains it (the product whose `product_includes_system` names
it, a capability's parent, a data asset's source of truth), and about a value
it carries that a view is drawn for (its domain's landscape). Each is bound
and counted, so a view that would draw the box alone says *Only itself*
rather than opening empty. A double-click on a box opens the first view
about it, and a right-click lists them. A boundary that is one value of a
field (Servicing on the landscape) lists the views about that value and
opens the first on a double-click. Beside a subject's picker, the other views
about the same subject sit as tabs: a system's Architecture, Hub and Spokes,
Processes and Capabilities and Governance. Where a system runs, its account,
region and network zone, is its product's Onboarding drawing.

An `up` naming no view is `view.up`, an error in a view the estate holds. A
shipped view's level is the shipped set's to keep, and a sketch drawn from the
quick door, which copies only the views it draws, is not held to it.

## Four kinds, and why it matters

`kind` says what a view is, and it decides how the view is rendered.
Full reasoning in [AAC-11](AAC-11_DIAGRAM_KINDS_AND_BUILDING_BLOCKS.md).

| | What it is | How it renders | Size |
|---|---|---|---|
| `diagram` | A subject, at a level. Read closely by someone about to change something | Layered, shapes carry meaning | Warns past 40 nodes |
| `map` | No subject: everything, cut one way. Scanned rather than read | Packed, color carries the cut | Any |
| `report` | A question, answered with a set | A table | Any |
| `timeline` | Dated things on a calendar of quarters | A bar per thing with a `start_date` and `end_date`, sectioned by what the view groups by; a Mermaid `gantt` in the artifacts, a grid in the app | Any |

A timeline is the one kind where the layout chooses nothing: time is the
axis. What a bar's edges reach that carries no quarter -- the systems a work
package delivers -- is listed under the bar rather than drawn, and the only
timeline so far is `change-roadmap`, which is what the change layer's
quarters were for.

Reports were drawn as graphs until the kinds were split. The first six were
each grouped by entity type or carried a single edge kind, which shows
membership rather than structure. A report renders as a table: sortable,
filterable, downloadable, with the ids clickable.

For diagrams, the split carries the size warning. An architecture diagram past
about forty boxes is treated as a modeling finding rather than a layout
problem, so the engine reports it rather than the renderer working around it.

Leave `kind` off and it is guessed: grouped by entity type means report, no
edges means map, otherwise diagram. It is guessed rather than defaulted to
`diagram` because defaulting is how the first six reports ended up as graphs.

## Views have a layer and a section

`category` puts a view in a layer: Business, Application, Data, Technology,
Governance, Change. `section` puts it under a heading within the layer:
Capabilities, Frameworks, Integration, Hosting, Plans. Eighteen views had sat in
one flat list under Business; the sidebar now lists the layers, each opens on its
sections, and a layer's name opens a page of its diagrams as pictures. The
layers are also the order they are shown in, the business layer first because
that is what the estate exists for, change last.

A view with no category lands on **Other** until it is given one. One with no
section is listed after the sections of its layer.

## Writing one in the app

**Edit** on a drawing written as a query opens the view in parts, each
said as a sentence: what it shows (a type, and conditions on its fields, the
values offered from what the model holds), what else it brings in, what is
pinned or hidden, which lines it draws (only the kinds that can join what is
shown are listed), what it groups into boxes and colors by, and its direction
and size. Fields are named in words, the business domain rather than
`company_domain`. The panel sits beside the sheet and every change redraws it, so the
query is edited by watching the picture. **Save** writes the file by value:
a key whose value did not change keeps every line it had, so the comment beside
an expansion rule and a description wrapped by hand survive a change to the
filter. What the parts have no words for -- a filter on what a relation says,
`lanes`, a parameter -- is kept as written and shown as written.

**Edit the file instead** opens the same view as YAML in a text box, with
**Preview** drawing it on the canvas without writing anything, and **Back to
the parts** returns with whatever the text now says. Either way, the result is
an ordinary view file, the same as one written by hand.

The parts are not a canvas to draw on, and the canvas below draws only what
the model holds, so the diagram and the model cannot drift apart.

## Drawing one on the canvas

**New > Diagram** opens a sheet to draw on rather than a form, with whatever
is selected in the panel beside it. **Add**, or a drag from its list, places
one of three things, and each is something the model keeps:

* **A library part** becomes a new record where it was dropped. Its name is
  asked there, since the id is made from it; the part's defaults are its
  fields, with the fields of every boundary it landed in (a web application
  dropped in zone eu-west-2a of the lending account is a system in that
  cloud, account, region and zone), and what the record must have and the
  drop did not say, an owner or a criticality, is left for the panel to ask,
  not guessed. A name the estate already has offers the existing one first.
* **A system the estate has** is pinned to the diagram, drawn as it is.
  Dropped into a boundary it does not sit in, the move is asked the way a drag
  between boundaries is (below).
* **A view, an account or a network zone** is placed as a boundary. The
  diagram's file names the view; it does not copy what the view draws:

```yaml
view_id: lending-onboarding
title: Lending onboarding
kind: diagram
places:
  - view: network-topology
    leave_out:
      cloud_account: [prod-riskops]   # on the view, off this diagram
scope:
  pin: [SYS-LENDING-PORTAL, SYS-LENDING-EVENTS]
edges:
  - via: interfaces
```

Each time views are loaded the placed view is read as it is then: its scope,
its lines and, unless the diagram groups by something of its own, its
boundaries, direction and the order its values are laid out in. Change the
network on Network Topology and every diagram it is placed on follows, so
the network is drawn once rather than on every diagram that stands on it. A
place may say `leave_out` (a field and the values left off this diagram; they
stay in the view), `only` (the values kept), or
`parts: false` (the boundaries without the view's own boxes, so only what
was placed inside them is drawn). An account placed from the list is the
view kept `only` to that account. What the placed view expands, pins and
hides is its own, and is not carried over. `terrane validate` reports a
place naming a view that is not there, or one that itself places others, as
`view.place`, an error: the diagram would otherwise be drawn without it, with
nothing on the drawing to say so.

The drawing is the same as every other's, laid out from the model, so a box
lands where the layout puts it inside the boundary it was dropped into, and
the sheet moves to it. Connect, or a drop of one box on another, joins two
things the ways the metamodel allows, and a kind of line the diagram did not
draw yet is added to it. The file is written as it is drawn, the first time
something is on the sheet; **Edit** on a diagram drawn this way opens it on
the canvas again.

## Pinning and hiding on one drawing

Two keys in `scope` record two gestures on one drawing: *this box does not
belong here*, *that one should be*. The app writes them, so neither needs the
YAML opened:

```yaml
scope:
  include:
    - type: actors
  pin: [SYS-SIEM]          # on this drawing, whatever the query finds
  hide: [SYS-IVR]          # never on this drawing
```

A pin is one thing, not a seed: pinning the SIEM on a context drawing does not
bring every system that sends it logs. A pinned thing is kept first when the
drawing is cut to `max_nodes`. A hide is applied last and beats a pin. A view
may be pins alone, which is what a saved sketch is.

In the app, right-click a box (or select it and press Delete) to hide it from
the drawing in view; **Add to this view…** on the drawing's summary pins
anything in the model to it. Either is the smallest change that does what was
asked: showing a thing takes it off the hidden list and pins it only if the
query still does not draw it, and hiding a pinned thing unpins it before it
writes a hide. Every one comes with an Undo, and an undone change leaves the
file byte for byte as it was.

`pin` works like `id_in` and has the same limit: a pinned box will not be
joined by the next thing like it. So every pin and every hide is listed on the
drawing's summary with a button to undo it, rather than only in the file.
`terrane validate` reports a pin or a hide on something the model no longer
holds as `view.stale_pin`.

On a view written as a query, where a box sits is not saved. Position is the
layout's to decide, from the model, every time. A diagram drawn on the canvas
is the exception: once a box is moved by hand, every box's place is kept in
the view's `positions`, the layout places only what is new, and **Lay out
again** hands the whole drawing back to it. A box, or a shape of the
diagram's own, can also be locked on such a diagram: it is listed under the
view's `locked`, by id or by key, and is not carried, nudged or lined up
there until it is unlocked. A lock is the drawing's, not the record's; the
same box on another diagram moves freely.

## Moving a box into another boundary

Two more gestures change the model rather than the drawing. Dropping one box
on another asks how the two connect, from the ways the metamodel allows, and
records the one chosen. Dropping a box into a different boundary moves it there -- and
since a boundary is one value of a field the view groups by, that is a change
to the record, not to the drawing. Dragging a system from *Servicing* into
*Card Issuing* sets its `company_domain`, and it moves on every view grouped
by `company_domain`, not only this one.

So the app says so before it writes. The chooser names the field, the value
it has and the one it will get, and every other view grouped by that field
the box moves on, a subject view once per subject it is drawn for. A view
whose scope selects by the same field may take the box off or bring it on,
and the chooser says which: moving a system out of the servicing domain takes
it off the Servicing landscape, `domain-landscape` drawn for Servicing, whose
scope is that domain, and puts it on the landscape of the domain it goes to. **Move it** is
the same one-field save the inspector's form makes, written where the record
lives, and the toast's Undo is that save with the old value.

What a drop can mean is decided by the model, not the picture:

* **Only a field's boundary takes a box.** A boundary that is a type
  (`group_by: type`) or a framework's relation (`relation@target`) has no
  field to set, and a drop there says so and does nothing. So does a drop on empty sheet
  or into the boundary the box is already in.
* **A reference field stores the id.** A boundary is labeled with an org
  unit's or a parent capability's name; the drop writes the id the records
  inside it hold. A label two different values share is not offered.
* **Only the levels that differ change.** Dropping into an account in the
  same cloud sets the account; dropping into one in another cloud sets both.
* **A record made by a shape, or brought in by an import, is not moved
  here.** The chooser says where it is changed instead: under `overrides` on
  the product's instance, or in the source the import reads. A record
  harvested from the business layer can be moved, and saving it moves it into
  a file of its own, which the chooser says first.

An edgeless map drawn as tiles has no drag: choose **Packed** under Layout,
in the drawing's **⋯** menu, to move things on it.

The reference panel beside the editor lists the entity types, edge kinds,
groupable fields and `where` operators **read out of the model at that moment**,
so a field that appears in the model appears in the list.

Four guards, all for the same reason the entity editor has its own:

- **The text must parse and resolve** before anything is written. The parser's
  complaint is shown with the source name and caret diagram stripped out, since
  in a text box the line number is the useful part.
- **Two files can never claim one view id.** Saving a new view whose id already
  exists is refused, and so is renaming a view in place — that is a save-as, and
  the message says so.
- **The model is loaded again from disk after the write.** If the reload fails
  the previous contents go back, so a file that parses only in memory cannot
  break the next start.
- **A view that draws nothing is still saved**, and reported as drawing nothing,
  so half-finished work is not lost.

**Source** on any diagram — authored or focus — gives the generated Mermaid and
Structurizr DSL to copy. That is the same renderer `terrane render` uses, so what is
copied is byte-for-byte what would be committed.

## Focus

Each authored view answers a question decided in advance.
Focus answers the one asked while looking at a single entity, *what is around
this thing*, without a view file per entity.

**Focus** on any entity builds a view on the fly: that entity, everything within
N relationship hops of it, and every kind of connection between them. It is the
same query engine, given a scope of one id and an unrestricted `expand`.

Two decisions:

- **Every edge kind is drawn.** An authored view chooses the edges its question
  needs. A focus view is for exploring, so it hides no connection.
- **Four hops is the ceiling.** Past that the picture approaches the whole
  landscape, which the authored views cover.

Focus is not saved and is not an artifact. A neighborhood worth keeping is
written down as a view file.

## Hue is the entity type

A system is indigo on every diagram, a data asset green, a capability violet,
a control red, an actor amber. Shape follows the type the same way. The rule
holds in the app and in every committed artifact, because both draw from
`50_ENGINE/terrane/palette.py`.

`style.color_by` still names the dimension a view is about, but it gets a
**second channel** rather than a second hue:

| Dimension | How it is drawn |
|---|---|
| Ordered — `criticality`, `classification`, `service_tier`, `resilience`, `capability_level`, `capability_tier`, `strategic_importance` | Border weight and a tint of the type's own hue, strongest first. The legend lists the values in their order, not alphabetically |
| `status` | Border style: solid for Active, dashed for Planned, dotted for Proposed, faded for Deprecated and Retired |
| Anything nominal the view also groups by — `network_zone`, `actor_kind`, `capability_tier` on the map | Nothing extra. The boundary already says it, and the legend says that the boundary says it |
| `type` | Nothing extra; hue and shape already are the type |

The first version of this palette handed one nine-hue ramp to every
dimension, and the same green came to mean Low criticality, Active status and
data asset depending on which view was open. A reader who learned the legend
on one diagram was misled by the next. Ordered data drawn as unrelated hues
had to be read from the legend rather than seen. Both made the maps hard to
read, and neither could be fixed by choosing different colors.

Override a type's swatch under `palette:` in `10_MODEL/model.yaml`.

### Three palettes, one rule

The palette above is **classic**, and every committed artifact is drawn in
it unless the estate says otherwise. The app has two tones, **Stone** and
**Graphite**, chosen per person in the sidebar, and each is a whole palette
of its own rather than classic recolored: a hue for every entity type, the
ramp for free-text values, the tints of a plain boundary, the ink. The rule
holds in all three, and so does every channel in the table: a system is
teal in Stone and amber in Graphite, the tone's own accent, so the commonest
box on a drawing is the color the page around it already uses. A boundary a
cloud provider draws is the provider's convention in every palette.

An organization picks the palette its exports are drawn in, and the tone
its people's app opens in, with `base:`; any bucket at the top replaces the
base's in every palette; a section named for a tone replaces it in that tone
alone:

```yaml
palette:
  base: graphite            # classic, stone or graphite
  systems:                  # every palette: our systems are our blue
    fill: "#dbe7f6"
    stroke: "#1f4e8c"
  stone:                    # Stone only: a lighter blue beside its warm grays
    systems:
      fill: "#e3ecf7"
      stroke: "#2b5d9c"
```

A tone's palette is held by `50_ENGINE/tests/test_tones.py` to give every entity type
a stroke of its own and to keep a box's name readable, at 4.5 to 1, at the
deepest tint an ordered value gives it.

## Flows are not views

A view is a filter over entities and renders as a flowchart. A **flow** is an
ordered chain of interfaces and renders as a sequence diagram, because "what
happens in what order" is a different question from "what connects to what".

Flows live in `10_MODEL/flows/`, their steps in `relations/`, and they render to
`70_ARTIFACTS/flows/`. See [AAC-09](AAC-09_ACTORS_AND_FLOWS.md).

## Adding one

Before adding a view, check whether an existing view with a different `group_by`
answers the question: regrouping costs nothing, and each view is one more to maintain.

When you do add one, `terrane validate` checks it resolves, is non-empty, and produces
edges, so a view that matches nothing is reported at review.
