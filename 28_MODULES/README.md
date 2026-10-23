# Modules

The plug-and-play parts.

A block (`26_BLOCKS/`) is infrastructure that arrives together. An archetype
(`20_ARCHETYPES/`) is a whole product. Between them sits the size most
architecture is actually done at: *a part of a product*. The identity
federation into a vendor. The private path out to it. The return feed that
lands in the warehouse. The callback listener for its webhooks. Each is a
handful of entities with the relations between them, and each turns up in
most onboardings and in none of them exactly.

A part may provide **any entity type**, not only the systems, interfaces and
data assets most of them happen to provide. `network-hub` creates a transit
gateway; `operator-role` creates the people. The composer walks `provides` by
name and the shape's `entity_defaults` fold under a template whatever the type
is, so an actor costs exactly what a system costs.

A module is that handful, with parameters. An archetype is composed from
modules -- and, where it varies, names a slot with the parts that can fill
it; an instance drops the ones that do not apply, adds the ones the shape did
not expect, and chooses in the slots. When a new vendor arrives, the diagram
is not drawn. It is chosen: which of these parts does this vendor need?

## The shape

```yaml
- module_id: sso-federation
  name: Single sign-on into the vendor
  category: Identity
  description: >
    What the form shows. One paragraph on what the part is and why it exists.
  optional: true                  # an instance may drop it with `without`
  requires: [vendor-tenancy]      # parts whose entities this one wires to
  parameters:
    - name: idp
      component: identity-provider  # a kind: the landing zone answers it
    - name: platform_org
      estate: true                  # the estate answers it, in model.yaml
    - name: access_controls
      estate: true
      default: []
  patterns: []                    # patterns a product with this part applies
  provides:
    systems:
      - system_id: "SYS-{slug|upper}-FEDERATION"
        name: "{product_name} Identity Federation"
        owner_org_id: "{platform_org}"
        uses: ["{idp}"]
        controls: "{access_controls}"   # governance arrives with the part
    interfaces:
      - interface_id: "INT-{slug|upper}-FEDERATION-VENDOR"
        source_system_id: "SYS-{slug|upper}-FEDERATION"
        target_system_id: "SYS-{slug|upper}-VENDOR"
  relations: {}
```

Templates see the archetype's bindings (`slug`, `product_name`, `owner_org`,
`domain`, `account` and the rest), the module's own parameters, and `alias`,
the name the module was composed under. The archetype's `entity_defaults`
fold under every template a module provides, so a module says only what
makes its entities different.

Three shorthands on a template do the wiring: `runs_on` and `uses` produce
`system_uses_tech_service` rows, and `controls` / `policies` produce the
governance rows for a system or a data asset. A part that brings its own
controls is a part an assessor does not have to ask about.

## Composing

In an archetype:

```yaml
modules:
  - module: vendor-tenancy
  - module: api-outbound
    with: { caller_system: "{caller_system}" }
  - module: private-egress
  - module: sso-federation
  - module: sftp-return-feed
```

In an instance, drop what does not apply and add what the shape did not
expect:

```yaml
archetype: saas-onboarding
without: [sftp-return-feed]
modules:
  - module: webhook-inbound
    with: { consumer_system: SYS-CORE-LEDGER }
  - module: sso-federation
    with: { idp: TS-OKTA }        # same alias as the shape's entry: overrides it
```

`requires` is enforced: dropping `api-outbound` while keeping
`private-egress` is refused, because the egress would wire to a gateway that
does not exist. A module marked `optional: false` cannot be dropped at all.

## Repeating over a list: hub and spoke

Most parts have a fixed shape. A hub does not: an integration hub, an event
bus, an identity provider or a transit hub is one thing in the middle and
however many spokes the product names. A template with `each` is produced
once per item of a list-valued parameter:

```yaml
parameters:
  - name: spokes
    required: true
provides:
  interfaces:
    - each: "{spokes}"
      interface_id: "INT-{slug|upper}-{item|stem}-HUB"
      source_system_id: "{item}"
      target_system_id: "SYS-{slug|upper}-HUB"
```

Each copy sees `{item}`, the list entry, `{item|stem}`, the entry without
its type prefix (`SYS-CRM` becomes `CRM`), and `{index}`, counting from one.
A list entry may be a mapping, in which case its keys are bound too.
`each` works on relation rows as well, which is how a network hub attaches
every named network. The instance supplies the list:

```yaml
modules:
  - module: integration-hub
    with:
      spokes: [SYS-CORE-LEDGER, SYS-CRM, SYS-STATEMENTS]
```

`28_MODULES/hub-and-spoke.yaml` has five: integration, event, data,
identity and network hubs. Every hub system carries the tag `hub`, and the
`hub-and-spoke` view draws one wheel per tagged system.

## Parts that create people

A diagram of a product nobody uses is half a diagram. Two parts put the people
on it, and the difference between them is a modeling judgment worth making
deliberately:

* **`operator-access`** names an actor the model already holds. An applicant,
  an underwriter and a servicing agent are not things a product invents, and
  creating a second one per product would turn eight actors into forty and a
  context diagram into a landscape with people drawn on it.
* **`operator-role`** creates one. A role that exists *because the product
  does* has nowhere else to come from: nobody was clearing sanctions alerts
  before the screening was bought, and hand-adding the actor first so a part
  can refer to it afterward is the manual step the library exists to remove.

`operator-role` takes a list of mappings and uses `each`, so the roles are
data on the instance rather than a parameter per role:

```yaml
modules:
  - module: operator-role
    with:
      system: SYS-SCREENING-VENDOR
      roles:
        - id: screening-analyst
          name: Screening Analyst
          description: Works the alert queue.
          interaction: Clears alerts
```

Two things follow from `each` that are worth knowing. A product that creates
no role passes an empty list and gets no actor, so the part needs no switch of
its own. And every key in a mapping is referenced by the template, so an entry
missing one fails by name and says which part and which product it was in,
rather than producing half an actor.

The created actor is a `Role`, not a `Person`. Who currently holds the job is
a staffing fact that goes stale; the job is what the architecture has to keep
working when the person changes.

The status comes from the shape, which means a role for a product that is not
live yet is `Planned`, and `system-context` -- which includes actors `where:
status: [Active]` -- leaves it out until the product ships. Nobody has to
remember to add it on launch day.

## What a part needs from the shape

Every template reads bindings the shape supplies -- `slug`, `product_name`,
`vendor`, `owner_org` -- without asking for them as parameters of its own.
`needs` is where a part says so:

```yaml
- module_id: private-egress
  needs: [product_name, slug, vendor]
```

It is checked twice. When the library loads, a template that reads a token
the part neither declares as a parameter nor lists under `needs` is refused
by name, so a typo in a template is a load error rather than a diagram with
a hole in it. And `terrane validate` checks every shape against every part it
composes or offers: a shape that binds no `vendor` and composes a part that
needs one fails then, with both named, rather than on the day a product is
expanded. Twenty-seven parts had this contract and none had written it down;
the library could not tell a shape it was missing something until now.

A template under `each` is exempt from the load-time check, because its
bindings include the keys of whatever mapping the list holds, which cannot
be known from the part alone. The composer still names the part and the
product if one of those turns out to be missing.

## A part names a kind; the shape binds it

Thirteen parts used to carry `default: TS-AWS-EKS` and the like. A part
that names a cloud is a part for one cloud, and a part chosen in a slot on
the Azure shape bound AWS services, because the shape had no way to reach
into an option it did not list. A parameter says what *kind* of shared
service it stands for instead, as a component type id:

```yaml
parameters:
  - name: platform
    component: container-platform
  - name: front_door
    component: api-gateway
  - name: idp
    component: identity-provider  # the same on every cloud: a neutral service answers
```

and the estate's landing zone says which service is that kind, by tagging
it `landing-zone` with its `component_type`. A shape can still say so by
hand, under `bind` -- the same word a block uses for the same fact, lifted
to the shape so it reaches every part the shape composes or offers -- for a
deliberate choice the tags would not make:

```yaml
bind:
  secrets-manager: TS-OUR-OTHER-VAULT
```

No shipped shape does: each names the services it lands on by kind, its
blocks bound `api-gateway: landing-zone` and its `uses` lists naming
`secrets-manager` where they named the sample's vault, so an estate's
services can be called whatever it calls them.

A parameter resolves in this order: what the entry's `with` says, then a
shape parameter of the same name, then what the shape binds the kind to --
on `bind` or on one of its blocks -- then the one shared service of that
kind tagged `landing-zone` on the shape's provider (a neutral one, like the
identity provider, where the provider has none; a service that is two kinds,
like Key Vault, says so under `answers_for`), then the part's own
default. A kind that resolves to nothing, or to two things, is refused by
kind at composition and by `terrane validate` before that
(`library.unbound_component`, `library.ambiguous_kind`), with the tag or the
`bind` line to add. Earlier still, before any shape composes the part, a kind
a part names that a provider's landing zone cannot answer is a warning
(`library.landing_zone_gap`) naming the parts that ask, so a queue no AWS
service answers for is found before the onboarding that wants it. The two
vendor shapes now differ in one line, `provider`;
the baseline kit carries nothing cloud-specific, and neither does any part in
the library. [AAC-03](../00_METHOD/AAC-03_ARCHETYPES.md) has the shape side.

## A part asks the estate

What a part needs from the estate around it that is not a kind of service --
who owns the shared network path, where a vendor's audit trail goes, which
controls govern a vendor tenancy -- is a parameter marked `estate: true`.
The estate answers it once, under `answers` in its `10_MODEL/model.yaml`,
for every product that composes the part:

```yaml
answers:
  platform_org: ORG-TECH          # owns the private egress and the federation
  siem_system: SYS-SIEM           # where audit-forwarding sends the trail
  vendor_controls: [CTL-TPRM-DD]  # every vendor tenancy is governed by these
```

The estate's answer comes after anything the product or the shape says and
before the part's own default. One with no default and no answer is refused
at composition, naming the parameter and where to answer it; a list with a
default of `[]` -- the controls and policies a part's records are governed
by -- is simply empty where the estate says nothing, which is the honest
state of an estate whose register does not cover it yet. The parts used to
name the sample's own records here, and the health system in
`90_EXAMPLE/thurman-health` held eighteen records under the card issuer's
ids to build on them; it answers with its own now, and gives the private
egress to its infrastructure team where the card issuer gives it to its
whole technology organization.

## Kits

A kit is a part made of parts:

```yaml
- module_id: vendor-baseline
  name: Vendor baseline
  optional: false
  parameters:
    - name: vendor
      required: true
    - name: caller_system
      required: true
  modules:
    - module: vendor-tenancy
      with: { vendor: "{vendor}" }
    - module: api-outbound
      with: { caller_system: "{caller_system}" }
    - module: secrets-management  # its vault is a kind; the landing zone answers
```

Both vendor shapes used to list the tenancy, the gateway and the vault
separately, and had drifted in a binding nobody meant. Both compose the
baseline now and differ only in `provider`: the vault is the landing zone's
secrets manager on whichever cloud the shape lands.

A kit is a name for a group, not a namespace. Its members land under their
own aliases, so `requires: [vendor-tenancy]` works whether the tenancy came
alone or inside the baseline; `without: [secrets-management]` drops one
member; and naming a member under an instance's `modules` re-binds it
without restating the kit. `without: [vendor-baseline]` drops every member,
and is refused for this kit because the tenancy cannot be dropped. A kit may
be made of kits; one that contains itself is refused when the library loads,
with the cycle named. In the New form a kit is a heading over its members,
each still a switch of its own.

## Slots: where a shape varies

The parts a shape always has go under `modules`. Where it *varies* -- one
need, and more than one part that can fill it -- is a slot on the shape:

```yaml
slots:
  - name: reach
    description: How our side gets to the vendor
    options: [private-egress, public-call]
    default: private-egress
  - name: return
    options: [sftp-return-feed, webhook-inbound]
    default: sftp-return-feed
    optional: true
```

and a choice on the instance:

```yaml
choose:
  reach: public-call
  return: none
```

A part is either always in the shape or an option in one of its slots,
never both. A slot's default has to be one of its options, and a required
slot with no default has to be chosen. What fills a slot is changed by
choosing, not by `without`: dropping the private path would leave a required
need silently unfilled, so the composer refuses and says which slot to choose
in instead. A chosen part is re-bound the way any part is, by naming it under
`modules`.

Where the shape can answer a chosen part's question itself, the slot says
so, keyed by option:

```yaml
  - name: return
    options: [sftp-return-feed, webhook-inbound]
    default: webhook-inbound
    with:
      webhook-inbound:
        consumer_system: "{upstream_system}"
```

The listener's consumer is the system that called the vendor, which the
shape already knows, so a product on the default says nothing about it. A
product that wants the result elsewhere answers the part under `modules`,
and its answer wins.

`vendor-saas-service` existed because it was `saas-onboarding` with the
public path in place of the private one, and the description of
`saas-onboarding` listed the variations as prose because there was nowhere
else to put them. The choice is one line on the instance now, and the second
shape keeps only what is genuinely different about it: the Azure bindings,
and the public path as its default.

## The catalog

`terrane render` writes the parts out beside the diagrams, as
`70_ARTIFACTS/library/modules.md`: every part with what it provides, what it
needs from the shape, the kinds it names, and -- the column no hand-kept
catalog has -- where it is used, by which shape, through which slot or kit.
A part nothing composes says so. The shapes get `library/shapes.md` the same
way: what each is composed from, its slots and defaults, the binds it keeps
as overrides, and which products sit on it. The landing zones get
`library/landing-zones.md`: for each provider a shape lands on, the shared
service of each kind, which parts ask for it, and the kinds asked for that
the zone does not have. And `library/adoption.md` measures the estate
against the shapes: how far each product on one has moved from it -- an
answer that is not the default, an override, a part added or dropped, a
slot chosen against its default -- and which hand-authored products have
the systems a shape's parts would make and are not on one
(`library.shape_candidate`).

## From a sketch

Most parts are not designed; they are noticed. The third vendor onboarding
has the same four boxes as the first two, and the architect who drew them
knows it. The app's sketch turns that into a module without retyping it:
pick the things on the map, choose *Save as module*, and the entities come
back as templates in the vocabulary of the shape that made them.

- Every value the shape bound becomes its token: `SYS-SCREENING-GATEWAY` is
  written `SYS-{slug|upper}-GATEWAY`, the product name `{product_name}`, the
  vendor `{vendor}`, the account `{account}`.
- Every field the shape's `entity_defaults` would supply is dropped, so the
  part says only what makes its entities different. A field the part itself
  overrides stays.
- Platform use and governance come back as the shorthands a person would
  have written: `uses`, `controls`, `policies`. Relations between the chosen
  things come back as rows.
- Tokens other than `slug` and `product_name` are listed as the module's
  parameters, so a shape that does not bind one is told, rather than
  expanding into a name with a hole in it.

The text is shown before it is written and can be edited in place; saving
parses it, reloads the library, and rolls back if either fails. A part
written from one product composes into the next, which is the claim the
library makes and the test suite checks.

## Assembling a project

A part is a diagram chunk: a handful of boxes with the lines between them,
named and parameterized. The app's **Assemble** panel is where chunks are
chosen for one project: pick several, watch the product's own architecture
drawing take shape, rename or drop what the chunks make or set a field on
it, and write one product file. The file says `compose:` where a product on
a shape says `archetype:`, and lists the parts, the provider and whatever
else a shape would carry; the loader builds the shape of one behind it. A
project that turns out to be the second of its kind is kept as a shape from
the same panel. [AAC-03](../00_METHOD/AAC-03_ARCHETYPES.md) has the file and
the rules.

A project the panel made opens again, from the panel's own *Open* list,
from the product's inspector, or by its address
(`#assemble&open=PRD-MERCHANT-PORTAL`): the chunks picked, the answers and
the edits as the file has them, and *Save* rewrites the file, keeping the
note a person wrote above its data. A product on a shape opens the same
way and is saved in the shape's terms: what it drops, what it adds, what it
chooses. A list answer, the roles a part creates or the spokes of a hub, is
a small table of rows rather than typed JSON.

## The standard components, and the standard applications

`application-parts.yaml` holds the components an application is built from
beyond the product parts: a mobile channel, an internal console, scheduled
jobs, an event consumer, a notification service, a search index, an
inference service, a reporting service, an adapter to a partner. Each wires
to the product service, a part that calls it going through the API the
service offers (`api-service` makes both: the service, named for itself,
and its API as an offered interface), and runs on a block or a kind the
landing zone answers for, so none names a cloud.

`applications.yaml` holds the standard applications as kits of those: a web
application, a mobile application, an internal tool, an event-driven
service, a batch application, an integration adapter, an AI inference
service, a reporting application. Picking a kit in the Assemble panel picks
its members under their own names, so a product can still do without one,
tell one something, or add a part the kit did not bring. The application
types in [`29_TYPES/`](../29_TYPES/README.md) require these kits and offer
the components each kind of application may add.

## What a module is not

**Not an archetype.** It has no `applies_to` and produces no product; it
produces parts of one.

**Not a block.** A block is technology services resolved per cloud. A module
is the application-level shape around them, and it can run on a block by
naming it in `runs_on`.

**Not a pattern.** A pattern is a decision. A module may declare the patterns
a product applies by having it, which is how adoption stays honest.
