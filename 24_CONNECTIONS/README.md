# Connection kinds

The ways two systems are connected here: an API call, an event on the bus, a
scheduled file, a pipeline load. An interface is the most repeated thing in the
estate and, until this folder, the least reused: written field by field, its
style and protocol and authentication typed in each time. A kind is that
repetition said once.

## Why a kind is read off the estate

Each kind is a shape that already recurs in the model's interfaces, not a
category somebody hoped for. An interface is of a kind when its integration
style is the kind's and its protocol is one of the kind's, so the catalog
(`70_ARTIFACTS/library/connections.md`) can say which interfaces are of each
kind whether or not anyone chose it, and which are of none. That list is the
finding: a connection that matches no kind is either something new the library
should learn, or something built differently from everything around it.

No two kinds share a style and a protocol, which `terrane validate` holds
(`connection.overlap`), so an interface is of one kind at most and the catalog
never counts one twice.

## How it is used

Drop one system on another in the app and the chooser offers each kind by
name: "Card Servicing API calls Core Card Ledger by request on a queue". The
interface form arrives filled in with the kind's first protocol and
authentication, its frequency and direction, and the pattern it applies, all of
which stay editable. Nothing records which kind was chosen: the fields say it,
and the catalog reads them.

## The shape

```yaml
- connection_id: event
  name: Event on the bus
  description: >
    A system publishes what happened and never learns who consumed it.
  integration_style: Event          # Request-response, Event or Batch
  protocols: [AMQP]                 # an interface on any of these is of this kind
  auth_methods: [OAuth2, ManagedIdentity]   # the first is proposed
  frequency: Realtime
  direction: Outbound
  patterns: [event-fanout]          # from 27_PATTERNS; checked by the gate
  datastore: source                 # optional: target, source or both
```

`terrane validate` refuses a kind whose style is not one of the three, whose
pattern the library lacks (`connection.unknown_pattern`), or which shares a
style and a protocol with another. Like a block or a pattern, a kind names no
vendor: a protocol is a protocol, and the product that carries it is the
technology service's business.

## A database's ways in and out

A kind may say which end of it is a data store, a component type the library
draws as a cylinder: `target` for a way into one from something that is not
one, `source` for a way out of one, `both` for one store to another. A line
drawn into or out of a database then says what the estate already does with
that kind of store, and offers those kinds first, the library's ways in or out
after them: into a relational database, its own service's datastore, as the
estate's six are; out of one, a change data capture feed or a scheduled
extract, where the chooser used to propose an API call; between two, a
replica or a backup. A system of another product reaching into a database
another service already reads and writes as its own is said to be the shared
database the library deprecates, and is never the likeliest answer.

The four ways out (`change-data-capture`, `database-extract`,
`database-replica`, `database-backup`) are the one place this catalog is
ahead of the estate, at the owner's asking: no interface is of them yet, and
the catalog says "None yet" under each until one is.

## Adding one

Find the interfaces the catalog lists under "of no kind", and if several share
a shape, that shape is a kind: give it an id, a name, a sentence on what it is
for, the style and protocols that recognize it, and the pattern that says how it
is built here, if there is one. Run `terrane validate` and `terrane render`; the catalog
then counts what the new kind matches.
