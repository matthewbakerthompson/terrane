# AAC-03 — Archetypes

An archetype is a reusable shape: the systems, interfaces, data assets and relations
that a particular kind of product or service always brings with it. Adding a product
on an archetype means naming it and answering its parameters, and the archetypes are
the part of this repository to fit to your own organization first.

## Why this and not templates

The alternative is a file template you copy and edit. A copied template is a fork.
When the standard shape changes — the platform adds a mandatory sidecar, the event bus
moves, the data landing pattern is revised — every copy has to be found and edited
individually, and the copies have drifted apart. Within two years they no longer match
the standard.

An archetype is a live reference. Instances name it; they do not copy it. Change the
archetype and every instance changes on the next render. What an instance holds is only
what makes it different.

## Anatomy

```yaml
archetype_id: azure-digital-product
applies_to: products
patterns: [api-front-door, stateless-request-service]   # every instance applies these
parameters:
  - name: slug
    required: true
  - name: criticality
    default: Medium
defaults:                      # applied to the instance entity itself
  architecture_domain: Business
provides:                      # the entities this shape creates
  systems:
    - system_id: "SYS-{slug|upper}-WEB"
      name: "{product_name} Web"
      criticality: "{criticality}"
  interfaces: [...]
  data_assets: [...]
relations:                     # the edges between them
  system_uses_tech_service:
    - system_id: "SYS-{slug|upper}-WEB"
      tech_service_id: TS-AZURE-AKS
```

Templating is `{parameter}`, with optional filters `|upper`, `|lower`, `|slug` and
`|title`. `{product_id}` and `{instance_id}` are bound automatically from the instance.
A value that is exactly one token keeps the bound value's type, so numbers and lists
survive substitution rather than becoming strings.

## Instances

```yaml
product_id: PRD-CARD-SERVICING
name: Card Servicing
status: Active
owner_org_id: ORG-DIGITAL

archetype: azure-digital-product
parameters:
  slug: cardsvc
  product_name: Card Servicing
  owner_org: ORG-DIGITAL
  domain: Servicing
  account: azure-cards-prod
  criticality: High
  classification: Restricted

overrides:
  SYS-CARDSVC-WEB:
    service_tier: Tier 1
    cmdb_ci_sys_id: e5f6071829304050
```

Generated entities have the same fields as hand-written ones, plus `archetype` and
`archetype_instance`. Those two fields are what let a view
scope itself to a product without listing its parts — see the
`product-card-servicing` view.

This is, less a few more overrides, the file `PRD-CARD-SERVICING.yaml` is.
Card servicing was imported as plain rows and moved onto the shape without a
rename: the slug `cardsvc` makes the ids the estate already had, so
every relation, control and process that pointed at them is untouched, and
the move is the product file rewritten as answers plus `overrides` for what
the shape's defaults got wrong about a live product.

## The four escape hatches

An instance can depart from its shape in four ways, and each one is written in the
instance file.

**`overrides`** changes fields on a generated entity. Use it where the instance
differs: a higher tier, a real CMDB id, a different classification.

**`exclude`** drops a generated entity entirely, by id, where a shape's own
`provides` made it; a part is dropped whole with `without`. The Collections
Workspace has no event publisher because it is an internal agent tool, so it does
without that part.

Exclusion cascades. Anything pointing at an excluded entity goes with it — an interface
to a system that does not exist is worse than a missing edge — and so does anything
pointing at what went, until nothing more does: excluding a product's datastore takes
the data asset mastered in it, and the API's read-write row to that asset with it.
Each entity that goes is reported:

```
warn  model.load  PRD-EXAMPLE: INT-EXAMPLE-API-EVENTS
                  dropped because it referenced excluded SYS-EXAMPLE-EVENTS
```

One that pointed only at something else that went says which exclusion it went with.
The warning is there so that a cascade never removes entities without saying so.

**`ids`** keeps the estate's names where the shape was written after the product
and named things otherwise. It maps an id the shape makes to the id the estate
already uses for it, and every record and relation the shape makes follows:
`PRD-DISPUTES` keeps `SYS-DISPUTES-SAAS` where the vendor shape says
`SYS-DISPUTES-VENDOR`, so the processes, capability realizations, controls and
the flow that point at it did not change when the product moved. Overrides and
exclusions may be written against the kept names.

**`extra`** adds entities and relations inline for one-off components, and
for the governance rows only this product can know: the screening product records
the sanctions control on its vendor and gateway under `extra.relations`, so
everything about the product is in its file. The app writes here too: a thing
created beside generated things is offered to their product, and lands under
`extra` rather than in a file of its own, so it is included in the product and
survives a re-expansion. Use it
sparingly. Three instances of the same archetype all adding the same `extra` is a
sign that the archetype is missing a part.

Both `overrides` and `exclude` fail with an error if they name something the archetype does not
produce, which catches the case where the archetype was refactored and an instance still
refers to the old shape.

## Built on blocks

The anatomy above lists every entity longhand, and the first version of every
shipped shape did that: seven systems at twenty fields each, and a
relation list saying which shared service each one runs on. That was hard to
review, and a change to what a public web tier is had to be made
in every archetype separately.

Version 2 of the shapes says three things instead.

**What every entity has in common.** `entity_defaults` carries the fields a
template would otherwise repeat, by entity type, with `all` for the ones every
type shares. A template then says only what makes it different, and `null`
takes a default away where one part of the shape differs:

```yaml
entity_defaults:
  all:
    status: Planned
    company_domain: "{domain}"
  systems:
    owner_org_id: "{owner_org}"
    cloud_account: "{account}"
    deployment_unit: helm
provides:
  systems:
    - system_id: "SYS-{slug|upper}-VENDOR"
      hosting: SaaS
      deployment_unit: null        # nothing of ours deploys it
```

**What it is built on.** `blocks` names building blocks from `26_BLOCKS/`, and
`bind` says which of their components the landing zone already provides. A
bound component creates nothing; it is what the systems run on --
`landing-zone`, the one service of that kind the estate tags `landing-zone`
on the shape's provider. Every other component is created for the product,
named from the slug, and resolved to the `provider`'s product where the
component knows one:

```yaml
provider: AWS
blocks:
  - block: public-web-tier
    bind:
      cdn: landing-zone
      load-balancer: landing-zone
    # waf and dns: created per product, as TS-{SLUG}-WAF and TS-{SLUG}-DNS
```

The shapes bound the sample's services by id here until the health system in
`90_EXAMPLE/thurman-health` built on them and had to hold its Azure services
under the card issuer's ids to do it. A shape names a kind; the estate's
landing zone says which of its services that is.

The AWS shape's first version listed a CDN and a load balancer and left out
the WAF ruleset and the DNS record. Version 2 names the block, and both arrive
because the block includes them. Change the block and every shape built on it
changes on the next render; hand-listed entities have to be changed in each
shape.

**What runs on what.** A system template names what it runs on with
`runs_on` (a block, for every part of it, or `block.component`) and `uses`
(shared services, by kind or by id). Both produce `system_uses_tech_service`
rows, so the relation list shrinks to the few rows nothing else implies. A
kind in `uses` -- lower case, a component type -- is the landing zone's
service of that kind, as a bind is; an id is taken as written. Every
provided system is included in the product unless `include_systems: false`.

```yaml
    - system_id: "SYS-{slug|upper}-API"
      runs_on: [stateless-service]
      uses: [secrets-manager]
```

**What the estate answers.** A shape parameter marked `estate: true` is one
the estate answers once, under `answers` in its `model.yaml`, rather than
every product: where landed data comes in, who stewards what a data product
makes. A product can still say otherwise under `parameters`; one left
unanswered is refused at expansion with where to answer it. Parts ask the same
way ([`28_MODULES/README.md`](../28_MODULES/README.md#a-part-asks-the-estate)).

Two rules follow. A connection between two bound services is a fact
about the landing zone, not about this product, so it is not written once per
instance. And a block whose every component is bound creates nothing at all,
which is the case for `saas-onboarding`: buying creates controls on things the
landing zone already runs, so the shape creates no infrastructure of its own.

Not every shape is built on blocks. `batch-data-product` runs on the shared
analytics platform and creates no infrastructure of its own; it applies the
analytics landing zone *pattern* as a tenant of it rather than instantiating
the blocks. The shape says so in its description, which is where that kind of
decision belongs. A shape built on no parts still has a footprint -- the
systems its own `provides` makes -- so `library.shape_candidate` can find the
products such shapes were written from. Customer 360 and the identity
service were those products -- `batch-data-product` and
`core-platform-service` are their records with the name made a parameter --
and both are on their shapes now: the slugs `cust360` and `identity` make
the ids the estate had, and what the shapes' defaults get wrong about them
is a few `overrides`.

## Composed from modules

Blocks say what a product runs on. They do not say what a product *is*: the
gateway on our side of a vendor, the return feed that comes back, the identity
federation, the webhook receiver. Those are the parts an architect
chooses when a new vendor arrives, and until version 3 every shape listed
them longhand, so a vendor that sent webhooks instead of a file was a
different archetype.

A **module** is one such part, with parameters: a handful of entities that
arrive together, the relations between them, the controls and policies they
carry, and the pattern they apply. A part may provide any entity type -- most
provide systems, interfaces and data assets, `api-service` provides the
product's service and the API it offers as an offered interface (every part
that calls the service goes through it), `network-hub` provides a transit
gateway and `operator-role` provides the people who work in the thing. They
live in `28_MODULES/`, and a shape is composed from them:

```yaml
modules:
  - module: vendor-baseline         # a kit: tenancy, gateway, vault; `optional: false`
    with:
      vendor: "{vendor}"
      caller_system: "{caller_system}"
  - module: sso-federation
  - module: audit-forwarding

slots:                              # where the shape varies
  - name: reach
    options: [private-egress, public-call]
    default: private-egress
  - name: return
    options: [sftp-return-feed, webhook-inbound]
    default: sftp-return-feed
    optional: true
```

A **kit** is a module made of modules: `vendor-baseline` is the three parts
every vendor onboarding starts with, under one name, so the two vendor shapes
compose it by reference rather than by copy. What its members run on is not
passed to it at all: a part parameter names a *kind* -- `component:
api-gateway` -- and the shape's `bind` says which service is that kind on its
landing zone, the same `bind` a block entry uses, lifted to the shape so it
reaches every part composed or offered. The two vendor shapes differ in
nothing but that map now. A **slot** is one need with more than one part that can fill it; the
shape names the default and the instance chooses. A part is either always in
the shape or an option in one of its slots, never both. Where the shape can
answer a chosen part's question from its own parameters, the slot says so
under `with`, keyed by option -- the webhook listener's `consumer_system` is
the shape's `upstream_system` -- so a product on the default says nothing it
need not; the product's own `with` for the part wins.

A module template uses the shape's parameters as well as its own, and inherits
the shape's `entity_defaults`, so it says only what makes its entities
different. Everything it creates is stamped with `module: <alias>`, which is how
the whole-product view and the inspector know which part a system belongs to.

**What the instance says.** A product keeps the parts it needs and chooses
in the slots. `choose` picks an option, or `none` where the slot allows it;
what fills a slot is changed by choosing, never by `without`, because
dropping the private path would leave a required need silently unfilled.
`without` drops a listed part and everything that pointed at it, reported as
dropped dependents the way an exclusion is; a part another kept part
requires cannot be dropped, and neither can one the shape marks as always
present. `modules` on the instance adds a part the shape did not include, or
re-binds one it did -- a kit's member included, without restating the kit:

```yaml
archetype: saas-onboarding
choose:
  return: webhook-inbound            # this vendor calls us rather than sending a file
modules:
  - module: webhook-inbound          # and this is who listens
    with:
      consumer_system: SYS-CRM
  - module: secrets-management       # the vault is Key Vault here
    with:
      vault: TS-AZURE-KEYVAULT
```

Onboarding a vendor is choosing in two slots, switching off the parts it
does not need, and answering their parameters; the systems, interfaces,
data, controls and the diagram follow. The New form in the app shows the
same: the slots as
choices, the parts as switches with a kit as a heading over its members, and
the parameters each one still needs.

**Two shorthands for governance.** A template may say `controls:` and
`policies:`. They become rows in the enforcement relations, so the
third-party due diligence control lands on every vendor tenancy without a
hand-written row. Which controls those are is
the estate's register, not the library's: the vendor tenancy says
`controls: "{vendor_controls}"`, and the estate answers `vendor_controls`
once in its `model.yaml` -- `[CTL-TPRM-DD]` in the sample, its business
associate review in the health system.

The module library is documented in [28_MODULES/README.md](../28_MODULES/README.md).
The rule for what belongs there: a module is a *part of a product*, not an
infrastructure tier. A queue is a component, an event tier is a block, an
event publisher that a product owns is a module.

## Writing one for your organization

Do not start from a whiteboard. Start from three real things you have already built,
write out their systems and edges longhand, and find what is identical. That is the
archetype. What differs becomes parameters, and what differs in only one of the three
is probably not a parameter — it is an override.

Some heuristics:

**Parameterize identity and ownership, not structure.** `slug`, `name`, `owner_org`,
`domain`, `criticality` are good parameters. A parameter that adds or removes a system
means you have two archetypes under one name.

**Reference shared systems, through the estate.** The batch data product points at
the estate's ingestion system rather than generating a per-product ingestion path,
so every data product shares that one system. It
asks for it (`ingest_system`, marked `estate: true`) rather than naming the sample's
`SYS-DATA-INGEST`, so another estate answers with its own once, in `model.yaml`.

**Five parts is about right.** An archetype that produces fifteen entities is modeling
an implementation rather than a shape, and every instance will need overrides.

**Version them.** `version` is recorded on the archetype and carried into the diff when
it changes. Changing an archetype changes every instance, so it should be a reviewed
change whose effect on the instances is visible. `terrane render` before and after
shows how much changed.

## The instance's status flows through

```yaml
entity_defaults:
  all:
    status: "{status}"
```

`status` is bound from the instance, like `name`, so a shape says the parts
are whatever the product is. Every shipped shape does. Two used to hardcode
it -- one `Planned`, one `Active` -- and the first planned product on the
second came out with four live systems, which the target-state view then
left out and the governance view drew.

## The landing zone resolves itself

```yaml
provider: Azure
```

That line is the landing zone. A part parameter names a kind --
`component: api-gateway` -- and resolves to the one shared technology
service of that kind tagged `landing-zone` on the shape's provider: APIM
here, the API Gateway on the AWS shapes. A neutral service, tagged with no
provider -- Entra, the identity provider on every cloud -- answers for any
shape whose provider has none of that kind. Nothing about the landing zone
is written on the shape, and the two vendor shapes differ in that one line.
A block bound to `landing-zone` and a kind in `uses` resolve the same way.

The tag is opt-in because the estate has services of the same kinds that
are not the landing zone: a NAT gateway is a `private-egress` as much as
PrivateLink is, a subnet a `vpc` as much as the shared VPC. Thirty-two shared
services carry the tag; the per-product network primitives do not. Two
tagged services of one kind on one provider is an ambiguity, refused by name
at composition and by `terrane validate` (`library.ambiguous_kind`); none is
refused with the tag to add (`library.unbound_component`).

That refusal comes when a shape already composes the part. The same fact
one step earlier is a warning: for each provider a shape lands on, every kind
a part names that no tagged service there answers for
(`library.landing_zone_gap`), with the parts that ask and any shape that
binds it by hand. It is measured against the providers the shapes land on,
not against every provider with a tagged service -- the on-prem data center
is one tagged `vpc`, and nothing lands there -- and only where the provider
has a landing zone at all. A provider with none reports no gaps, only
`library.no_landing_zone`, once per shape: the health system, all Azure,
used to get twenty-two gaps about AWS and Google Cloud on top of it. A
neutral service is no landing zone on any cloud, so an estate that tags its
identity provider still has no AWS landing zone. `terrane render` writes the same
picture out as `70_ARTIFACTS/library/landing-zones.md`: what each zone has,
by kind, and what is asked of it that it lacks, which is where the next
onboarding would stop.

A service that is two kinds says so. Key Vault holds the keys as well as the
secrets, and `component_type` is one value -- the kind it is drawn as -- so
`answers_for: [kms]` on the record lists the further kinds it answers for on
its landing zone, and the index lists it under each. A kind on either field
has to be a component type (`library.unknown_kind`, an error): a misspelled
one on the single tagged service would otherwise go unreported.

A service id under `bind` is the override, for the cases resolution cannot
decide:

```yaml
bind:
  kms: TS-OUR-HSM-VAULT     # this shape's keys live somewhere the zone's do not
```

A shape-level `bind` maps a kind to a service and wins over resolution; a
block entry's `bind` says the same about the block's components and counts
for the parts too, so nothing is repeated. Two blocks binding one kind two
ways is a contradiction (`library.bind_conflict`), and every bound service
has to exist (`library.bind_unknown`). Whether a bound service is
of the kind it is bound as is still the author's claim, and is not checked.
No shipped shape binds by id: the Azure shape's key used to be Key Vault by
hand, and is the landing zone's `kms` now, which Key Vault answers for by
saying so on its own record.

## Multi-cloud

`provider` on the shape is the cloud every block resolves against by default.
A block entry can name its own: `- block: public-api-tier` with
`provider: Azure` under an AWS shape gives an AWS workload an Azure front
door, and every shipped shape already federates identity to Entra ID from
AWS. Multi-cloud is one product whose blocks resolve against different
providers, not two products; the whole-product view groups by
`cloud_provider`, so the two clouds are two boundaries on one sheet. The
composer offers the choice per block.

## Hubs and spokes

A part whose shape depends on the instance, an integration hub with however
many spokes the product names, uses `each` on a template: one copy per item
of a list-valued parameter, with `{item}`, `{item|stem}` and `{index}` bound.
The five hub-and-spoke modules in `28_MODULES/` are built on it, and the
`hub-and-spoke` view draws any system tagged `hub` as a wheel. See the module
README for the template form.

## Assembling a project without a shape

A shape is worth naming when the second product like it arrives. The first
one is assembled from the same parts, with no shape, and says so in its own
file:

```yaml
product_id: PRD-MERCHANT-PORTAL
name: Merchant Portal
status: Planned
owner_org_id: ORG-MERCHANT
compose:
  provider: Azure
  modules:
    - module: api-service
      with: { runs_on: [public-api-tier.api-gateway, stateless-service] }
    - module: web-channel
    - module: relational-datastore
    - module: event-publisher
    - module: operator-role
      with: { system: SYS-MERCHANT-API, roles: [...] }
parameters:
  slug: merchant
  product_name: Merchant Portal
  owner_org: ORG-MERCHANT
  domain: Payments
  account: azure-payments-prod
overrides:
  SYS-MERCHANT-API: { description: ... }
```

`compose` is the shape part of an instance: the provider, the parts, and
optionally the `blocks`, `bind`, `patterns` and `relations` a shape would
carry. The loader builds the shape of one behind it, `compose:<product id>`,
and expands it like any other, so `parameters`, `overrides`, `exclude` and
`extra` mean what they mean on a product on a shape. What the file
does not say is derived the way the composer derives it: the vocabulary is
what the product answered plus whatever its parts need; the blocks are the
ones the parts run on, each bound the way the provider's shipped shape binds
it, so a project assembled on Azure lands on the same cluster and gateway
as a product on the Azure shape and gets its own hostname and firewall
policy for the same reasons; the entity defaults are the ones every composed
shape carries. A part without what it requires, a kind the landing zone
cannot answer, or a product that says both `archetype` and `compose` fails
at load, by file and by name.

Every entity an assembled product makes carries `archetype:
compose:PRD-MERCHANT-PORTAL`, so a reader can tell it from one on a shared
shape. The shape of one is not in `20_ARCHETYPES/` and the New form does not
offer it; the parts catalog counts the product among a part's users, and
`library/adoption.md` lists it under *Assembled from parts* rather than as a
hand-authored candidate for a shape it happens to match. When a second
product wants the same parts, the `compose` block is the shape: the app's
Assemble panel writes it to `20_ARCHETYPES/` on request, and the product
file gains `archetype:` in its place.

## Assembling one in the app

**Assemble a project from chunks**, on the home page, in the New picker and
on the Library's parts shelf, is the panel for that file. The parts of the
library are shown as chunks, each with a thumbnail of what it makes; picking
one brings what it requires, and a chunk another picked chunk requires
cannot be dropped. The project's own answers sit beside them: a name, from
which the id and the slug follow until changed, the landing zone, the
account and region, the owner and domain, criticality and classification.
Start from nothing or from a shape, whose chunks and bindings come across.
The drawing on the right is the product's own architecture view, resolved
over a scratch copy of the model with the assembly in it, so it is the
diagram the file will have; under it, every entity the chunks make can be
renamed, dropped or given a field, and each edit is written as an override
or an exclusion on the project. Anything already in the model under one of
the ids the slug would make is named, and nothing is written until it is
changed. *Create project* writes the one file; *also keep this choice of
chunks as a shape* writes the shape too and puts the product on it.

A product the panel made opens again in it: from the panel's *Open* list,
from *Open in Assemble* on the product (and *Open assembly* on anything it
made), or by address, `#assemble&open=PRD-MERCHANT-PORTAL`. The file is
read as written: the chunks with their answers, the project's fields, the
overrides and exclusions, the comment above the data. *Save project*
rewrites that file, keeping the comment, after the product and everything
it generated have been taken out of the reckoning, so the re-assembly is
judged against the rest of the estate; a changed slug retires what the old
one made, and the reply names it. Change the id instead and *Create
project* writes a new product beside the old. If the model will not load
with the new text, the old text goes back. A list answer -- the roles a
part creates, the spokes of a hub -- is a table of rows in the panel, and
the bindings a chunk carries from a shape (`runs_on`, `uses`) are shown on
its card. A save keeps what a person wrote in the file: a key whose data
did not change keeps its lines as they were, comments inside them included;
one whose data changed keeps the remark above it and takes the new lines;
mappings merge key by key however deep, so the note above one override
survives a change to another. The preview is that text, so what *Save*
will write is on the page before it is written.

A product on a shape opens in the same panel, from its inspector or the
panel's *Open* list, and is held in the shape's terms. Its chunks are the
shape's, each with what the shape binds for it; a slot is a select under
*Choices*, and the part it chose cannot be dropped from its card, only
chosen away; a question the shape answers for a chosen part from its own
parameters arrives answered, and the field is for saying otherwise; the
shape's own questions (`vendor`, `upstream_system`) are asked beside the
project's. A kit's members are rows on its card: untick one and *Save*
writes the member's alias under `without`; a member nothing may drop, or
one another kept part requires, is shown with the reason and not offered.
The names a product keeps from before its shape (`ids`) travel with the
file and are not edited here. Drop a chunk and *Save* writes it as `without`;
pick another and *Save* adds it under `modules`; tell a kept part something
the shape did not and the difference goes under `modules` too; a choice
equal to the shape's default is not written. The file stays the shape's
answers and the differences, which is what an instance on a shape is. One
checkbox lets go of the shape: *Save* then writes the product as its own
`compose` block, with the shape's blocks, binds and patterns copied in so it
keeps drawing as it did, for the product that has grown away from the shape
it started on. A product on a shape has no second shape to keep. A product
on a shape built on no parts -- the batch data product, the core platform
service -- opens too: there is nothing to pick, the shape draws what it
makes, and the file is its answers and overrides.

## Composing one in the app

The New form chooses parts for a product; the composer chooses parts for a
shape. *Compose a shape from parts* in the archetype picker asks four things:
which of the shape vocabulary the instance will be asked for (`slug`,
`product_name`, `owner_org`, `domain`, `account` and the rest), which modules
with what the shape binds, which blocks with what the landing zone already
provides, and which patterns every instance applies. The archetype is written
in the form the shipped shapes have, `entity_defaults` derived from the
provider and the vocabulary, and a required parameter added for anything a
chosen part still needs. It opens in the editor below for a preview before it
is saved, and it is the file: edit it like any other.

## Editing one in the app

**New** lists the archetypes, and each one has **Edit shape** beside it. That
opens the archetype file itself with a **Preview** that expands it against a
stand-in instance and lists every entity and relation one instantiation would
create, which is hard to work out by reading the placeholders.

Two guards, each against losing work without a message:

- **Saving re-expands every instance.** If the result will not load, the file
  goes back as it was, since an archetype that parses but breaks the model would
  stop the model loading at all.
- **An archetype in use cannot be deleted.** Removing it would delete every
  entity it generates, and nothing would say so. The refusal names the
  instances.

Entities the shape generated are read-only wherever they appear, and say why:
the next expansion would overwrite an edit to them. Edit the instance or the
shape.

## The shipped archetypes

| Archetype | Shape |
|---|---|
| `azure-digital-product` | Web front end, product API, datastore, event publisher, operational data asset. The in-house digital product. Composed from four modules on three blocks, resolved against Azure |
| `gcp-digital-product` | The same four modules on the same three blocks, resolved against the Google Cloud landing zone: GKE, Apigee, Cloud SQL, Pub/Sub. The first product on it is Point-of-Sale Finance, which lands beside the dealer platforms that already integrate through Apigee |
| `vendor-saas-service` | Vendor system, integration gateway on our side over the public path, return feed, landed dataset. The same modules as `saas-onboarding` with Azure bindings and no private egress |
| `vendor-saas-service-gcp` | The vendor shape with a Google Cloud binding: Private Service Connect for the private path, webhooks for the return by default, the gateway and listener in the caller's workload project. The first product on it buys affordability data for point-of-sale finance |
| `batch-data-product` | Ingestion and curation pipeline, semantic layer, curated dataset, Collibra registration |
| `batch-data-product-gcp` | The batch shape with a Google Cloud binding: Pub/Sub in from a source system the shape asks for, Dataflow on a Composer schedule, the dataset in BigQuery served through Looker, Collibra either way; built on no blocks like the shape it mirrors. The first product on it curates lending performance in an analytics project of its own |
| `core-platform-service` | A single shared service behind the API gateway |
| `aws-product-onboarding` | What landing-zone onboarding creates: edge, public, application and data tiers in a vended account, with the platform services each consumes. Six modules on three blocks, with the WAF ruleset, DNS record, cache and backup plan created per product |
| `saas-onboarding` | What buying creates: a vendor tenancy outside our accounts, plus the gateway, private egress, identity federation, return feed, audit trail and monitoring that make up the boundary we own. Eight modules and no infrastructure of its own; drop the parts a vendor does not need, add webhooks, SCIM, BYOK or an embedded UI for one that does |

The last two describe the same event — a new product arriving — and produce
almost nothing in common, because building creates components and buying creates
controls.

These are starting shapes drafted against a placeholder estate, not a
recommendation. Expect to rewrite them once five real products have gone through:
they encode how an organization builds things, and yours will differ.
