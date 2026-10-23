# AAC-14 — Diagram conventions, and what the cloud providers do

## Why this exists

The drawings this repository generates are held to the published diagram
conventions of the AWS Architecture Center, the Azure Architecture Center and
Google Cloud's Architecture Center. This note records what each says, what
the generators here already do, what they do differently on purpose, and
what is left.

It was written from the sources below in October 2026. The conventions move
slowly; the icon sets move several times a year.

## What the three providers say

### Microsoft

The clearest statement is the Well-Architected Framework page on
[architecture design diagrams](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/design-diagrams).
Its practices, compressed:

- **Use standard notations** and official icons with the product name near
  the icon; never use a vendor logo for a conceptual block.
- **Directional arrows, never bidirectional.** Two flows are two arrows, from
  the initiating side to the dependency.
- **Label everything**: icons, containers and lines "when relationships
  aren't immediately obvious from context."
- **Consistency**: the same colors, casing, icon sizes, line weights, line
  types, arrow heads and border styles for similar things, across the whole
  set of diagrams.
- **Accuracy over simplicity**: "don't depict a PaaS service inside a subnet
  if it's actually accessed over a private endpoint." Retire a diagram that
  no longer answers a live question.
- **Metadata on every diagram**: title, description, last updated date,
  author, version, external references; a change log once it is shared.
- **A legend** whenever border or line semantics are introduced.
- **Accessibility**: contrast, and never color alone; pair color with a
  pattern.
- **Layer, don't overload**: context, then container, then a focused
  component or sequence diagram for a critical use case.
- **Version control** the source files with the workload's other assets.

The same page names the diagram types a workload needs: context, high-level
system, block, component, deployment, data-flow (and its STRIDE variant),
sequence, user journey, entity-relationship, network, state, flowchart, and
three specialized maps: availability and resilience, data residency,
identity and access flow.

The [Azure architecture icons](https://learn.microsoft.com/en-us/azure/architecture/icons/)
page adds the rules for the icons themselves: use them as they appear in
Azure, with the product name close by; do not crop, flip, rotate or distort;
do not use a Microsoft icon for your own product. Permitted use is
"architectural diagrams, training materials, or documentation." The
reference architectures on the Architecture Center follow one structure: a
diagram, a numbered **workflow** whose steps are the callouts on the
diagram, the **components**, alternatives, and considerations by pillar; the
network diagrams carry two numbered flows, inbound and outbound.

### AWS

The [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/)
package is the notation: service icons, resource icons, and **group**
shapes for the containers an AWS diagram nests: AWS Cloud, Account, Region,
Availability Zone, VPC, public and private subnet, security group, auto
scaling group, server contents. Each group has its own line style and
color, and the guidance is not to recolor icons or groups. AWS permits
customers and partners to use the package "to create architecture
diagrams."

The community conventions kept with the
[AWS networking best practices](https://aws.github.io/aws-networking-best-practices/community/conventions/)
are the house rules in one place: the latest icon set only, and only for
what the icon represents; icon colors unchanged; a label centered under
each icon in a regular weight; lines at least 1pt, solid for primary
connections and containers, dashed for secondary ones; open arrowheads over
closed; a white or transparent background; a minimum font size of 12px;
callouts rather than text embedded in the picture. AWS Prescriptive
Guidance asks for the same: PNG on a light neutral background, the current
icons, standard notation, color to differentiate.

The AWS reference architecture diagrams and the Prescriptive Guidance
patterns all read the same way: numbered steps on the diagram and a
numbered narrative beside it, left to right or top to bottom.

### Google Cloud

Google publishes its [icons](https://cloud.google.com/icons) and an
architecture diagramming tool built on them. Its diagrams are a house style:
white rounded **product cards** carrying the icon, the product name and a
one-line description; dashed **zones** for project, VPC network, region and
zone, nested, each named in its top-left corner; user cards at the left
edge; numbered user paths; a title bar and a footer. The
[deployment archetypes](https://docs.cloud.google.com/architecture/deployment-archetypes)
are the idea closest to this repository: zonal, regional,
multi-regional, global, hybrid and multicloud are **reusable topologies**,
each a diagram, and an application is described as a composition of them.
That is a diagram chunk with a name, and it is what the parts in
`28_MODULES/` are at the application layer.

### The C4 model

Not a provider: a notation for software architecture independent of any
cloud. Its [review checklist](https://c4model.com/diagrams/checklist)
lists what a diagram should give its reader: a title, a
type and scope the reader understands, a key; every element with a name,
a type, a purpose and, where it applies, a technology; every arrow with a
descriptive label that matches its direction; every acronym, color, shape,
icon, border style and line style explained. A diagram should be "mostly
understood without a narrative."

## What the generators here do, against that list

| Convention | Here | Where |
|---|---|---|
| Directional arrows only | Every edge is a relation with a direction; a two-way exchange is two rows | `query.py`, `render_mermaid.py` |
| Labels on lines where the relationship is not obvious | Edge labels carry the protocol, operation, interaction or role; the app places each on its own line, in a card | `placeEdgeLabels()` in `app.js` |
| One meaning per channel, consistent across the set | Hue and shape are the entity type everywhere; the view's dimension is a border weight and tint, a border style, or the boundary; line style is the kind of relationship | `palette.py`, `graphStyle()` |
| A legend whenever semantics are introduced | Four legend rows: types, the dimension's values, the kinds of boundary drawn, the line styles; the inspector's brief repeats them in words and the PNG export carries them | `renderLegend()`, `renderBrief()`, `legendLines()` |
| Nested containers with the provider's hierarchy | `group_by` draws provider, account, region, availability zone and network tier as nested boundaries, each in the convention of the provider it belongs to: a solid pink AWS account, a dashed teal region, a dashed blue zone, a green public and a blue private subnet, a dashed blue Azure subscription, a dashed GCP project. Each is named by kind in its corner: `region eu-west-2`, `subscription azure-cards-prod` | `boundary_style()` in `palette.py`, `group_kinds()` in `query.py`; `onboarding`, `network-topology`, `multi-az-deployment` |
| A title, a description and a date on the diagram itself | The PNG export is a sheet: the view's title and description, the model's name and the date, the counts, the drawing at 2x, the legend, and a footer naming the view and the generator | `exportPng()` in `app.js` |
| Accuracy over simplicity | A diagram is a query over the model; nothing is drawn that is not recorded, and a recorded fact cannot be left off a view that asks for it | the premise of [AAC-01](AAC-01_OVERVIEW.md) |
| Layer, don't overload | Context, landscape, product, system, governance, network and flow are separate views; a report is a table | [AAC-11](AAC-11_DIAGRAM_KINDS_AND_BUILDING_BLOCKS.md) |
| Version control the source | The model, the views and the generated output are all in the repository; CI fails on stale output | `.github/workflows/validate.yml` |
| Numbered flows with a narrative | Flows are sequence diagrams with one numbered hop per interface, and any drawing that carries a flow's interfaces can walk it: the hops numbered on the picture, the rest dimmed, the narrative beside it with the steps not on this drawing said so. The Markdown beside each rendered view lists the same walks | `render_sequence.py`, `flows_across()` in `render_mermaid.py`, `walkFlow()` in `app.js` |
| Reusable topologies as named chunks | Blocks, parts, kits and shapes; a project assembled from parts in the app | [AAC-03](AAC-03_ARCHETYPES.md), `28_MODULES/README.md` |
| Light background, legible type | White sheet, 12px node labels, 9.5px edge labels in cards, PNG export at 2x | `graphStyle()`, the PNG button |
| Every container says its technology | A second, smaller line under a node's name, read from the model: the platform services a system uses, compute first and the rest counted, or data first for a pipeline, an analytics layer or a datastore; the product behind a technology service or the kind of thing it is; *SaaS* for a bought system. Painted on a layer over the drawing in the document's own type, and onto the export | `techline.py`, `attachTechLayer()` in `app.js` |
| Tiers drawn in a fixed order, traffic crossing one at a time | The boundaries of a grouped field are laid out in the field's own order (`lanes` on the view, else the field's reading order where it has one): edge to data, proposed to retired, whatever the edges between them say | `lanes` in `query.py`, `laneOrder()` in `layoutHierarchy()` |
| Provider icons on the services that are a named product | A curated subset of the AWS, Azure and Google Cloud icon sets, and the vendor marks the Simple Icons collection carries, mapped from a service's name or its kind of component and from a bought system's vendor; drawn in the node's corner and on the export, credited with each set's terms | `80_APP/web/icons/`, `terrane/icons.py` |
| A checklist the drawings are held to | A test resolves every view and checks it: a title and a description, a legend that explains every channel drawn, boundaries named by kind and in the legend, no edge drawn twice, a kind of edge labeled throughout or not at all, a technology line that says what the name does not, the Markdown and Mermaid beside the drawing carrying the same | `tests/test_checklist.py` |
| Color never alone | Entity type is a shape as well as a hue; status is a border style; the legend names each | `palette.py` |
| An interface is a point of access on its component, as ArchiMate draws one | What a system offers (an API, a topic, a file drop) is drawn on a diagram as a pill in its owner's hue, a step lighter, inside its owner's boundaries, joined to it by a short line with no head laid the way the traffic runs (caller, API, service; publisher, topic, consumer); every connection through it ends at it, and the protocol it says once is not repeated on the lines. A map, and the hub view's wheel, keep their lines on the boxes; a diagram counts the pill as part of its owner's box | `_offered_on_owners()` in `query.py`, `pillBox()` in `app.js`, `pill_box()` in `terrane/draw/packed.py` |

## Where this repository differs, on purpose

**Generic shapes, with the mark in the corner.** A node here is an entity
in the model: a system, a data asset, a technology service. Hue and shape
stay the entity type, so a system is never drawn as a product. The
provider's or vendor's own mark sits in the top-right corner instead, and
only where it is true: on a technology service, the mark of the service it
is (EKS, Key Vault, Cloud SQL); on a bought system, its vendor's mark where
the vendor lets the mark travel. A system of ours carries no vendor's mark
whatever its name says, and anything without a mark keeps the monochrome
glyph for its kind of component. The shipped subset and whose each mark is
are in `80_APP/web/icons/CREDITS.md`.

**Filled arrowheads.** The AWS community prefers open arrowheads; Azure's
and Google's diagrams use filled ones. A filled head stays legible at 50%
zoom, where an open one does not, and the app is read at that zoom more
often than at 100%.

**Edge labels under 12px.** AWS's floor is 12px for text in a diagram. A
protocol name at 12px beside a 12px node label reads as a second node. The
label is 9.5px in its own card, and the PNG export is taken at 2x, where it
is 19px.

**A boundary's color is a second channel.** Hue on a
node means entity type and nothing else. A boundary is not a node, so its
stroke can carry a second meaning without breaking the one-meaning-per-
channel rule: the provider's own color and line for that kind of container,
which a reader of AWS or Azure diagrams knows before reading the name. The
fills stay near white so the node hues still read, a boundary that is not a
cloud container keeps a plain tint that deepens with nesting, and the legend
names every kind on the sheet. The stroke colors are the providers'
documented ones rather than this palette's, on purpose: the convention is
theirs. A boundary's kind is learned from the things inside it, not from
how deep it sits, because a record with no account or region collapses its
empty levels and its network tier lands at depth two.

## What landed, and what did not

All six items landed: boundary kinds styled the provider's way with a
legend row (`boundary_style()`, `boundary_legend()`), flows walked on any
drawing that carries their hops (`flows_across()`, the inspector's *Flows
across this drawing*), the title block on the PNG export (`exportPng()`),
the technology line under a node's name (`techline.py`, painted by
`attachTechLayer()` because Cytoscape draws one label per node and a second
line at the name's size would read as a second node), the checklist test
(`tests/test_checklist.py`), and the marks (`80_APP/web/icons/`, matched by
`terrane/icons.py`). A boundary carries the mark of the kind of container it is
where the provider publishes one: the AWS group icons for a cloud, an
account, a region and a public or private subnet, Microsoft's for a
subscription, AWS's corporate data center for the on-premises boundary;
Google draws its containers as labeled boxes, and so do we. The Mermaid
output carries the technology line as a second line in brackets, the way a
C4 container names its own technology, at the name's size, since Mermaid
cannot size one line of a label differently from the next; it carries no
marks, because an image in a committed `.mmd` would be a path to a file the
reader of the Markdown may not have.

**Marks and their terms.** The AWS Architecture Icons, the Azure Public
Service Icons and the Google Cloud icons are published for architecture
diagrams and shipped here unmodified as a curated subset, 143 files for the
kinds of service the component library knows and the kinds of container the
providers draw, under the terms quoted in
`CREDITS.md`. Vendor marks come from the Simple Icons collection, whose
files are CC0 while the marks stay their owners'; 25 are shipped, each with
the brand color the collection records for it. Fourteen more (Microsoft and
Azure, Salesforce, Oracle, Adobe, Slack, Tableau, Twilio, AWS, DocuSign,
Informatica, MuleSoft, Alteryx, Power BI) the collection has withdrawn at
their owners' request, so they are not shipped whatever its file server
still serves; ServiceNow, Workday, Collibra, Pegasystems, Experian, Onfido
and NICE never let theirs travel. A bought system from any of them names
its vendor in the technology line instead, which says the same thing in
words. That is the limit the convention sets: a diagram may use a vendor's
mark to name the vendor's product, and nothing more.

## Sources

- Microsoft, *Create architecture design diagrams*, Azure Well-Architected Framework: https://learn.microsoft.com/en-us/azure/well-architected/architect-role/design-diagrams
- Microsoft, *Azure architecture icons*: https://learn.microsoft.com/en-us/azure/architecture/icons/
- Microsoft, *Baseline highly available zone-redundant web application* (an example of the reference architecture structure): https://learn.microsoft.com/en-us/azure/architecture/web-apps/app-service/architectures/baseline-zone-redundant
- AWS, *AWS Architecture Icons*: https://aws.amazon.com/architecture/icons/
- AWS, *Diagramming conventions*, AWS Networking Best Practices (community): https://aws.github.io/aws-networking-best-practices/community/conventions/
- AWS, *Prescriptive Guidance patterns*: https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/welcome.html
- Google Cloud, *Icons*: https://cloud.google.com/icons
- Google Cloud, *Deployment archetypes*: https://docs.cloud.google.com/architecture/deployment-archetypes
- Simon Brown, *C4 model: diagram review checklist*: https://c4model.com/diagrams/checklist
