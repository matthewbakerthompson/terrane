# AAC-01 — Overview

## The problem this exists to solve

A drawn architecture diagram goes out of date when the estate changes, because the
diagram and the fact are separate artifacts. Someone draws the application landscape
for a board paper. Two products launch, one system is retired, a vendor is swapped.
The diagram is now wrong, and fixing it means a person remembering it exists, finding
the source file, and redrawing it. With fifteen diagrams in various decks, each has to
be found and redrawn separately. Each one shows the estate as it was on the day it
was drawn.

Terrane generates the diagrams from a model instead of drawing them.

## The shape of the fix

There is one model. It is a set of files under version control. Every diagram is
generated from it by a filter that names properties rather than systems. Adding an
application means adding a file; each diagram whose filter it matches then shows it.

```
                80_APP/  the browser app
                   |     map, inspector, editor
                   v
10_MODEL/          the facts            <- humans edit this
20_ARCHETYPES/     reusable shapes      <- humans edit this
30_VIEWS/          filters              <- humans edit this, rarely
     |
     |  terrane render
     v
70_ARTIFACTS/      diagrams and docs    <- generated, never edited
```

The app and the command line are two doors into the same files. The app writes the
same YAML a person would write by hand, and `terrane validate` is the gate either way.

Three consequences follow:

**A change has a diff.** "Who added this system, when, and what did the reviewer say"
is answered by `git log`.

**A change has a gate.** `terrane validate` runs on every change before it is merged
([AAC-05](AAC-05_CHANGE_FLOW.md#the-gate)). A system with no owner, an
interface pointing at something that does not exist, an id that breaks the convention —
these fail or warn at the point of change, where the person making it can correct them.

**A change is small.** The archetype mechanism exists so that the common case — a new
product that looks like the last four products — is a twenty-line file.

## The moving parts

| Part | Document | What it is |
|---|---|---|
| Model | [AAC-02](AAC-02_MODEL_CONVENTIONS.md) | Entities and relations as files. Identity, naming, layout, and what is required |
| Archetypes | [AAC-03](AAC-03_ARCHETYPES.md) | Reusable product and service shapes, with parameters, overrides and exclusions |
| Views | [AAC-04](AAC-04_VIEWS.md) | Declarative filters that resolve to diagrams |
| Change flow | [AAC-05](AAC-05_CHANGE_FLOW.md) | How a change gets in: intake, pull request, gate, render, publish |
| The app | [80_APP/README.md](../80_APP/README.md) | The browser app: map, inspector, editor, import |
| Impact | [AAC-08](AAC-08_IMPACT_ANALYSIS.md) | What breaks if this changes, and what this needs to work |
| Actors and flows | [AAC-09](AAC-09_ACTORS_AND_FLOWS.md) | Who is outside the estate, and what order a transaction moves in |
| Business layer | [AAC-10](AAC-10_BUSINESS_LAYER.md) | The capability map and value streams, imported rather than owned |
| Diagram kinds | [AAC-11](AAC-11_DIAGRAM_KINDS_AND_BUILDING_BLOCKS.md) | Diagrams, maps and reports, and the modular blocks below them |
| Frameworks | [AAC-12](AAC-12_FRAMEWORKS.md) | Which body of practice each capability domain answers to |
| Governance | [AAC-13](AAC-13_GOVERNANCE_LAYER.md) | The control register, imported, and where the estate enforces it |
| Diagram conventions | [AAC-14](AAC-14_DIAGRAM_CONVENTIONS.md) | What AWS, Azure and Google Cloud say a diagram owes its reader, what the generators do about it, and what is left |

Two more documents cover the edges: [AAC-06](AAC-06_CMDB_RECONCILIATION.md) on the
ServiceNow position, and [AAC-07](AAC-07_METAMODEL_CONTRACT.md) on how this stays
compatible with the canonical metamodel.

## What this is not

**It is not a replacement for a CMDB.** A CMDB records configuration items and their
runtime state, discovered automatically, at a finer granularity than this model records.
The two answer different questions and the long-term destination is that ServiceNow owns
the inventory and this model owns the intent and the structure around it. AAC-06 covers
how to get from here to there while the CMDB is not yet accurate enough to rely on.

**It is not a replacement for process modeling.** Value streams, processes and steps
belong in a business architecture capture effort. This model holds the application,
data and technology layers, and links to capabilities so the two meet.

**It is not a drawing tool.** If you need a diagram with a specific narrative layout
for a specific board paper, draw it; it is not the source, and it will not change when
the model does. What this replaces is the set of diagrams that are supposed to be
current.

## Where the effort goes

Standing this up is mostly not an engineering exercise: the engine is written, about
forty thousand lines of Python with no required dependencies. The effort is in three
places, in increasing order of difficulty:

1. **Getting the first model in.** An afternoon for a hundred systems if you have a
   usable spreadsheet — `terrane import csv` takes the metamodel v2 layout directly —
   and a month if you are starting from interviews.
2. **Getting the archetypes right.** These encode how your organization builds
   things. The first three drafts will need correcting. Expect to revise them after
   the first five real products go through.
3. **Getting change to flow through it.** This is the hardest of the three. A model
   updated by an architect who hears about changes second-hand is three months behind
   them. The model has to sit where the change already happens — in the design review,
   in the pull request, in the intake form — which is what AAC-05 is about.

The third is a governance question, which tooling does not settle.
