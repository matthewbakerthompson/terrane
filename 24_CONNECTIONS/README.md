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
```

`terrane validate` refuses a kind whose style is not one of the three, whose
pattern the library lacks (`connection.unknown_pattern`), or which shares a
style and a protocol with another. Like a block or a pattern, a kind names no
vendor: a protocol is a protocol, and the product that carries it is the
technology service's business.

## Adding one

Find the interfaces the catalog lists under "of no kind", and if several share
a shape, that shape is a kind: give it an id, a name, a sentence on what it is
for, the style and protocols that recognize it, and the pattern that says how it
is built here, if there is one. Run `terrane validate` and `terrane render`; the catalog
then counts what the new kind matches.
