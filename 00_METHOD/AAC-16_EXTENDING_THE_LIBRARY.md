# AAC-16: Extending the Library

The library is the vocabulary a product is assembled from. This document is
the map of it as it stands, the places it is thin, and the order to extend it
in, so that each addition lets more of the estate be assembled from the
library rather than drawn by hand. Every count below was read off the
library and the model on the day it was written; `terrane stats` and the catalogs under
`70_ARTIFACTS/library/` say what they are now.

## The layers, and what each one refers to

```
25_COMPONENTS   a kind of thing: a load balancer, a vault       109 kinds
      | provides
26_BLOCKS       the kinds that always arrive together           23 blocks
      | built on
27_PATTERNS     a block plus the decision and its cost          23 patterns
      | applied by
28_MODULES      a part of a product, with parameters            45 parts, 9 of them kits
      | composed into
29_TYPES        the kinds of thing the organization builds      13 types
      | shaped on each provider by
20_ARCHETYPES   a product shape, parts on blocks, bound to      9 shapes
                a landing zone
      | instantiated as
10_MODEL/products   the products themselves

24_CONNECTIONS  the ways two systems are connected, read off    12 kinds
                the interfaces; each names its pattern

library_paths   the organization's own folders of the same      read after
                layers, in 10_MODEL/model.yaml                  the shipped
```

Each layer refers only to the ones above it, by id, and `terrane validate` holds
every reference: a block naming a kind that is not a component type, a
pattern naming a block the library lacks, a part needing a parameter its
shape does not bind, a shape binding a service the model does not hold. The
connections between systems were the one part of the estate the layers did
not reach until this round: an interface was written field by field, its
protocol and style and authentication typed in each time.

No layer refers to the model below it. What a shape or a part needs of an
estate it names by kind, for the landing zone to answer, or asks for, for
the estate to answer in its `model.yaml`; "the sample out of the library",
below, says how.

## Where it is thin

**Parts make systems and interfaces, and little else.** Across the 45
modules there are 34 interface templates and 26 system templates, three data
assets, one technology service and one actor. No part makes a capability
link, a value-stream stage, a data asset's lineage or a flow, though the
engine would expand any of them: a part can provide any entity type and any
relation. The relations parts write are the ones a product needs to run --
reads and writes, runs on, uses -- and none of the ones that say why it
exists, so a product assembled from parts realizes nothing until somebody
adds it by hand.

**Most blocks reach no product.** All 23 blocks are used by a pattern, and
four reach a shape: the public web tier, the public API tier, the stateless
service and the transactional store. The other nineteen -- the inline risk
decision, the observed service, payment capture and posting among them --
are decisions written down that no product can yet be assembled from.

**Nineteen component types are for systems, and no system uses one.** The
application kinds (an ERP, a CRM, a web application) are refused by blocks,
which hold infrastructure, and parts classify a system with a free-text
`system_category` instead. Twenty-nine of the 109 kinds are instantiated in
the model at all.

**The providers are uneven.** Twelve kinds have no Azure name, twenty-eight
no Google Cloud name and twenty-nine no AWS name. Some are SaaS by nature --
an ITSM tool, a source host -- and the gap says nothing; the rest are kinds a
landing zone on that cloud cannot yet be asked for by name.

**The library was one folder per layer, in one repository.** Ids were global
and a duplicate stopped the load, so an organization adding its own patterns
edited the shipped files or forked them. That is what the second section
below closed: there is a place for "ours" beside "the method's" now.

## What was added this round: connection kinds

An interface is the most repeated thing in the estate -- 115 of them -- and
each was written field by field, its protocol, style, authentication and
frequency typed in each time. Read across the model, 113 of
the 115 fall into twelve shapes, and most shapes already had the library
pattern that says how it is built here. `24_CONNECTIONS/` is those shapes as
a layer: an API call, a request on a queue, a service and its own datastore,
an event on the bus, an event over HTTPS, a log stream, a scheduled file, a
partner file, a pipeline load, a scheduled API pull, a private path to a
vendor and sign-on federation, each with the style and protocols that
recognize it, the authentication and frequency a new one is proposed with,
and the pattern it applies. The two of no kind are a card-network message and
a voice call. Connecting
two systems on the drawing asks which kind and fills the form from it.
`terrane validate` holds each kind's style to the vocabulary, its pattern to the
library and its protocols apart from every other kind's, and the catalog
lists the interfaces of each kind whether or not they were made from it, so
the kinds also describe the interfaces already in the estate.

## What was added next: a library of your own

An organization keeps the method's library as it came and writes its own
beside it. `library_paths` in `10_MODEL/model.yaml` names one or more folders
in the repository, each holding any of the same layer folders:

```yaml
library_paths: [our-library]
```

```
our-library/
  25_COMPONENTS/integration.yaml   a kind of its own: the mainframe gateway
  26_BLOCKS/integration.yaml       a block made of it and the shipped API gateway
  27_PATTERNS/ours.yaml            a pattern of its own, and its own API front door
  28_MODULES/integration.yaml      a part of its own
```

Every layer -- shapes, connection kinds, component types, blocks, patterns,
parts and build types -- is read from the shipped folders first, then from
each named folder in the order listed, and a record of the organization's may
use anything in either: its block is made of a shipped component type and
one of its own. An id already taken stays the error it always was, naming
both files. A record stands in for an earlier one only when it says so, with
its own id:

```yaml
- pattern_id: api-front-door
  replaces: api-front-door
  name: API front door, partner edition
  ...
```

The replacement keeps the id, so every product, shape, part and connection
kind that names it gets the organization's version without being edited, and
it keeps its place in the catalog's order. Three ways of saying it wrongly are
refused rather than guessed at: `replaces` naming another id (a replacement is
not a rename), naming nothing read before it, or two records of one id in one
library. A folder `library_paths` names that is not there, lies outside the
repository, or holds a folder no layer is called is refused too, because each
of those would leave the organization's library quietly unread and a typo would
look like an empty library.

Additions and replacements are reported. Each catalog under
`70_ARTIFACTS/library/` names the organization's folders beside the shipped ones, marks a record of
its own with the library's name, and says of a replacement which file it
stands in for; `INDEX.md` and `terrane stats` say what each library adds and
replaces. The app's Library says the same on the cards. A part saved from a
sketch, a shape written in the editor and a shape kept from an assembly go to
the first library `library_paths` names, never into the shipped files, and
saving over a shipped part or shape asks for the `replaces:` line rather than
editing it in place. Without
`library_paths` the repository reads, renders and saves as it did.

## What was added after that: the sample out of the library

The library was written beside one estate, and named it. The vendor parts
gave the private egress and the identity federation to the card issuer's
technology org, sent the audit trail to its security monitoring and landed
files in its ingestion hub; the shapes bound its Azure, AWS and Google
services by id; the batch data product ran on its warehouse and defaulted
its owner to its data engineering team; every pattern named an owner, a
decision record and the controls it met, all in the card issuer's terms. A
second estate built on the shipped shapes -- the health system in
`90_EXAMPLE/thurman-health` -- had to hold eighteen records under the
sample's ids to build at all, and raised fifty-one warnings about patterns
owned by org units it does not have and meeting controls it never wrote.

Three things replace the names, and one rule says when each applies.

- **A technology service is a kind, and the landing zone answers.** A block
  says `bind: {api-gateway: landing-zone}`, a system template says
  `uses: [secrets-manager]`, and the estate's service of that kind tagged
  `landing-zone` on the shape's provider is the one -- the same resolution a
  part's `component` parameter already had. In the sample every one resolves
  to the service the shape used to name, so nothing it draws moved.
- **Anything else the estate answers once.** A shape or part parameter
  marked `estate: true` -- `platform_org`, `siem_system`, `ingest_system`,
  `data_org`, `vendor_controls` -- takes the value under `answers` in the
  estate's `model.yaml`, ahead of its default; a product still says
  otherwise for itself. A question with no default and no answer is refused
  at expansion, naming it.
- **A pattern's owner, decision and controls are the estate's.** Under
  `patterns` in `model.yaml`, per pattern id. They sit there rather than on
  the control records because the sample's register is imported and a
  re-import rewrites it whole; `model.yaml` is the estate's own and is never
  generated.

`terrane clear` takes `answers` and `patterns` out with the records they name.
`test_answers.py` scans every value the engine reads in the shipped layers for
an id the sample holds, and finds none; it found 134 before.

Measured on the health system, the eighteen became its own choices: eleven
kept as they were, seven renamed to what a hospital calls them (Information
Services rather than `ORG-TECH`, business associates rather than `TPRM`),
and the private egress given to its infrastructure team where the card
issuer gives it to its whole technology org -- an answer the parts could not
have taken before. Its warnings fell from 112 to 38: the fifty-one about the
patterns went, and so did twenty-three landing-zone gaps -- twenty-two
because a provider with no landing zone at all now has a wait and no gaps,
and one because its identity platform is tagged as the landing zone's.

## What was added next: the words a kind is also called

None of the card issuer's 88 systems carried a `component_type`, and no
reader or panel offered one. A kind now lists what else people call it under
`aliases`, in generic words: a relational database is also an RDBMS, an SQL
database, OLTP; a message queue a message broker, MQ. A product is not an
alias. What each provider sells is under `providers` already, and an alias
that named a vendor would make the library's choice of words a choice of
vendor.

`terrane.match.suggest_types` reads a record against every kind, through
each kind's name, id, category, description, providers and aliases, every
word weighed by how few kinds use it, a word a kind is called by (its name,
id or an alias) and a word of the record's own name counted double, and
gives the three likeliest with the words that matched. Every kind, not only
those that apply to the record's type: a system is often a database or an
integration engine, and Thurman Health's systems are typed so; a kind that
applies goes first on a tie. Nothing is learned and nothing is stored: a
kind added to the library, or an alias added to a kind, is in the next
suggestion. Hiding each typed technology service's kind and asking for it
back, the card issuer's 106 come back first 84% of the time and in the
first three 92%, Thurman Health's 22 at 91% and 91%. `terrane needs --types` prints them for the records that
have no `component_type`, grouped by the likeliest kind, and writes
nothing; a person sets the field.

## The order to extend it in

1. **A library of your own, beside the shipped one.** Built; the section
   above.
2. **Parts that say why.** A `realizes:` shorthand on a part, like `uses:`
   and `controls:`, writing `system_realizes_capability` for what it makes;
   then a product assembled from parts appears on the capability map and in
   the coverage report as soon as it is assembled.
3. **Shapes from the unused blocks.** The inline risk decision and the
   observed service are each one part away from being something a product
   can be assembled with; the patterns behind them are approved and the
   blocks are written.
4. **Connection kinds that require.** A kind that names the technology
   service it runs through -- an event needs the bus, a file transfer the
   managed transfer service -- so connecting two systems by event also
   records the bus, the way a part's `runs_on` records its platform.
5. **Qualifiers with a vocabulary.** A relation's qualifier is free text
   today; `system_reads_writes` says Read, Write or ReadWrite and
   `process_uses_data_asset` says Reads, Writes or Both. One list per
   qualifier, held by the gate the way an enum is, and the importer mapping
   the other spellings on the way in.
6. **Application kinds a system can carry.** Let a part's system template
   name a `component_type` from the nineteen application kinds, so an ERP
   bought as SaaS groups, shapes and defaults like one.

Each of these is library data and a check, not an engine rewrite; the engine
already expands any entity type and any relation a part names. That is the
test for whether an extension belongs here: if it needs the engine to learn
a new idea, it is a method change and starts in `00_METHOD/`; if it is the
existing idea applied to more of the estate, it is a file in a numbered
folder and a line in `terrane validate`.
