# AAC-12 — Frameworks

The model holds more than one framework, because each covers part of an
enterprise: a capability map shaped entirely like BIAN has no corporate
functions in it, and one shaped entirely like APQC has nothing specific to the
business.

Different domains answer to different bodies of practice. The model records
which, so a review knows which standard a domain is held to and a reader of the
map can tell a choice from an obligation.

The capability map is the organization's own; a framework says where a piece
of it sits in somebody else's vocabulary. The ten below ship as examples of
common ones, records in `10_MODEL/frameworks/frameworks.yaml` that an
organization edits, adds to or deletes like any other.

## Two questions, two links

| Question | Link | Said by | What it carries |
|---|---|---|---|
| Does this part of the business follow the framework, and how firmly? | `capability_aligns_to_framework`, read "follows" | A level-0 domain | `alignment`: Governed by, Aligned to or Informed by |
| Where in the framework does this capability sit? | `capability_references_framework`, read "is placed in" | Any capability, usually level 1 | `ref`: a path in the framework's own terms |

Payments follows PCI DSS, and Clearing & Transaction Posting, inside it, is
placed in BIAN at Operations and Execution > Payments > Card Clearing. The
first is an obligation or a choice made for a whole domain; the second is a
location at the level the work is done. They are two links rather than one with two
qualifiers because every import and export format writes a link's one
qualifier, and the two would otherwise travel as one ambiguous column. In the
app one form writes both: a capability's **Map to a framework** writes the
placement, and for a domain the following too.

## The frameworks held

| | Type | What it is for |
|---|---|---|
| BIAN | Reference model | Banking business capabilities and service domains |
| APQC PCF | Reference model | Cross-industry operating and management processes |
| ITIL 4 | Practice framework | IT service management |
| DAMA-DMBOK | Body of knowledge | Data management and governance |
| COBIT 2019 | Governance framework | Governance and management of enterprise IT |
| NIST CSF | Practice framework | Cybersecurity risk management |
| ISO/IEC 27001 | Standard | Information security management systems |
| PCI DSS | Standard | Cardholder data security |
| BIZBOK | Body of knowledge | Business architecture practice |
| TOGAF | Method | Enterprise architecture method and content |

`scope` is the field that stops a mapping claiming coverage the framework does
not give. ITIL has nothing to say about credit decisioning; DMBOK has nothing to
say about merchant sponsorship. Recording what each is for makes that legible
rather than something a reader has to already know.

## How firmly a domain follows

`capability_aligns_to_framework` carries an `alignment` qualifier, one of three:

| | |
|---|---|
| **Governed by** | A fact about the organization. An auditor turns up. |
| **Aligned to** | A choice somebody made, and can revisit. |
| **Informed by** | A borrowing. Useful vocabulary, no obligation. |

Payments is *governed by* PCI DSS, an obligation, and *aligned to* BIAN
because somebody chose that shape. One relationship for both would not say
which of the two is the obligation.

## Following is said at level 0

A level-1 capability inside Payments follows PCI DSS because Payments does.
Repeating the link on all 136 level-1 capabilities would make a copy on each
to keep in step, and a child updated without the rest would disagree with its
domain.

## A placement is a path

`ref` is written outermost first, joined with ` > `, in the framework's own
terms:

| Framework | A placement |
|---|---|
| BIAN | `Sales and Service > Sales > Customer Offer`: business area, business domain, service domain |
| ITIL 4 | `Service management > Incident Management`: group of practices, practice |
| CRI Profile | `Protect > PR.DS-01`: function, diagnostic statement |
| APQC PCF | `8.0 Manage Financial Resources`: one level |
| DAMA-DMBOK | `Data Governance`: one level |

A framework's landscape nests by the first two levels, so BIAN opens on its
five business areas and ITIL on its three groups of practices. A capability
placed twice in one framework is drawn at its first placement and lists every
one in its details. The business-layer import writes BIAN's paths from that
repository's own record of where each service domain sits, never from a copy
of BIAN's classification, which this repository has no license to hold; where
the records disagree, the place most of them give wins.

## Where each framework lands

| View | What it answers |
|---|---|
| `capability-map` | The whole map on one page: the 136 level-1 capabilities in their 22 domains and three tiers. Choose a framework above it and the capabilities placed in it are marked |
| `frameworks` | Every framework against every domain, in one grid: a ring for how firmly the domain follows it, a number for how many of its capabilities are placed in it |
| `framework-landscape` | One framework's own shape, with the capabilities placed in it. Drawn for every framework something is placed in, an organization's own included |
| `capability-alignment` | One domain: what it follows, where its capabilities are placed, and the controls, processes and systems around it |

The first three replace nine: a landscape per framework, five of them; a
domains map beside the top-level map; and three views that each showed part
of the grid.

## Mapping your own

From the app: open a capability, and **Map to a framework** in its details
asks which framework, where in it (the paths the model already uses are
offered), and for a domain how firmly it follows it. For many capabilities: a folder
holding `relations/capability_references_framework.csv`, with the columns
`capability_id`, `framework_id` and `ref`, brought in with **New > Import**.
A framework of your own is a record in `10_MODEL/frameworks/`; its landscape
appears as soon as something is placed in it.

## A domain with no framework

Twenty-one of the twenty-two domains follow at least one framework, and
Partner & Client Relationship Management follows none: no external body of
practice has much to say about it as this enterprise does it. A link for it
would record governance that does not exist.

The `frameworks` view is a **report** drawn as a grid rather than a diagram:
it answers a question with a set, and drawing it as a graph would only
suggest the lines mean something structural.
