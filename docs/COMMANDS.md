# Commands

Everything Terrane does from a terminal, generated from the command line
itself; `terrane --help` and `terrane <command> --help` say the same. Each
command works on the estate in the current folder, or the one `--root`
names (in a clone of this repository, the sample estate). `terrane app`
opens the same estate in the browser.

| Option | What it is |
|---|---|
| `--root ROOT` | the estate to work on (default: the current folder; in a clone of the repository, the sample estate) |
| `--version` | print the version and stop |

## terrane validate

Run the model quality gates.

| Argument | What it is |
|---|---|
| `--strict` | treat warnings as failures |
| `--errors-only` | suppress warnings |

## terrane render

Generate diagrams from the views.

| Argument | What it is |
|---|---|
| `--view VIEW` | render only this view id |
| `--format FORMAT` | all writes everything under 70_ARTIFACTS; one format writes that format alone, the docs, the library pages and the index untouched; one of: all, mermaid, structurizr, svg |
| `--png` | also rasterize each SVG into png/, through a Chrome or Edge on the machine or resvg-py where it is installed |
| `--out OUT` | output directory (default 70_ARTIFACTS) |

## terrane export

Export the model to another format.

| Argument | What it is |
|---|---|
| `target` | one of: csv, backstage, json, archimate, drawio, plantuml, excel |
| `--out OUT` | output directory |

## terrane cmdb

ServiceNow CMDB reconciliation.

### terrane cmdb drift

Compare the model to a CI export.

| Argument | What it is |
|---|---|
| `--export EXPORT` | path to a cmdb_ci CSV export |
| `--field-sot FIELD_SOT` | path to field_sot.yaml |
| `--out OUT` | output directory |

## terrane connect

Clone an estate's repository and fetch the governance it pins; in a clone, the governance alone.

| Argument | What it is |
|---|---|
| `[url]` | the estate's repository, as git clones it (default: the clone you are in) |
| `--into FOLDER` | where to clone it (default: a folder named as git names it) |

## terrane init

Start an estate in a repository of its own, read with the installed terrane.

| Argument | What it is |
|---|---|
| `[folder]` | where to start it (default: the current folder) |
| `--name NAME` | the estate's name (default: the folder's) |
| `--governance URL` | the organization's governance repository |
| `--governance-ref REF` | the revision of it the estate is checked against |
| `--requires RANGE` | the terrane versions the estate is checked with (default: this minor release) |
| `--sample` | copy the sample estate, a card issuer, out of the package into the folder, to open in the app and change |

## terrane app

Open the app on an estate: its diagrams, its records and the library, in the browser, edited in place.

| Argument | What it is |
|---|---|
| `--port PORT` | the port it listens on (default: 8020) |
| `--host HOST` | the address it listens on (default: this machine only; the app has no sign-in) |
| `--no-browser` | start it without opening a browser |

## terrane new

Scaffold a new model entry.

| Argument | What it is |
|---|---|
| `entity_type` | one of: actors, architecture_change_requests, capabilities, controls, data_assets, flows, frameworks, interfaces, offered_interfaces, org_units, policies, processes, products, roadmaps, systems, tech_services, value_stream_stages, value_streams, work_packages |
| `id` | the identifier, e.g. SYS-CARDS-WEB |
| `--archetype ARCHETYPE` | build this instance from an archetype |
| `--set SET` | field=value, repeatable |
| `--force` | overwrite an existing file |

## terrane import

Import an existing inventory.

### terrane import csv

Import metamodel v2 CSVs, or an inventory through --map.

| Argument | What it is |
|---|---|
| `--from SOURCE` | directory of CSVs |
| `--overwrite` | replace records already in the model |
| `--only ONLY` | import only this entity type, repeatable |
| `--map MAP` | a mapping from the inventory's columns, values and codes to the model's (AAC-15) |

## terrane diff

What changed in the architecture between two revisions.

| Argument | What it is |
|---|---|
| `since` | a git revision, e.g. HEAD~5 or a tag |
| `[until]` | a later revision (default: the working tree) |
| `--out OUT` | write the Markdown here instead of printing it |
| `--picture PATH` | draw the change: what was added in full, what was removed dashed in red, what changed with a heavy border or a heavy line, and what is there unchanged one hop away, faded; an SVG, or a PNG by its suffix; the page is printed only with --out |
| `--view VIEW_ID` | with --picture: put the marks on this view of the whole estate (application-landscape, system-context) instead of the change-scoped drawing |
| `--date DATE` | with --picture: the date on the sheet; none by default |
| `--excel PATH` | write the change as a workbook: what was added, removed and changed field by field, the relation rows, the views, the shapes and the parts, a sheet each |

## terrane needs

What each diagram needs from the records, and how many lack it.

| Argument | What it is |
|---|---|
| `[view]` | one view; every view when left out |
| `--subject SUBJECT` | the system, product or other subject a subject view is drawn for |
| `--types` | what each record with no component_type probably is, by the library's words; writes nothing |

## terrane search

The records a query finds, best first, and by which words.

| Argument | What it is |
|---|---|
| `query` | words of a name, an id, a description or a tag |
| `--type TYPE` | only records of this type; one of: actors, architecture_change_requests, capabilities, controls, data_assets, flows, frameworks, interfaces, offered_interfaces, org_units, policies, processes, products, roadmaps, systems, tech_services, value_stream_stages, value_streams, work_packages |
| `--limit LIMIT` | how many to list (default 10; 0 for all) |

## terrane impact

What is affected if this changes.

| Argument | What it is |
|---|---|
| `id` | entity id, e.g. SYS-CORE-LEDGER |
| `--depth DEPTH` | how many hops out (default 3) |
| `--only ONLY` | report only this entity type, repeatable |

## terrane schema

Regenerate the JSON Schemas.

| Argument | What it is |
|---|---|
| `--out OUT` | output directory (default 40_SCHEMAS) |

## terrane stats

What the model currently holds.

## terrane clear

Take the sample estate out, keeping the library and the views.

| Argument | What it is |
|---|---|
| `--yes` | do it; without this it only says what it would do |
| `--keep TYPE` | entity types to leave in place, or `relations` |

## terrane draw

Draw one file: a sketch, or a diagram a reader reads, no repository.

| Argument | What it is |
|---|---|
| `[file]` | the sketch, a YAML file (see --example), or an ArchiMate, Structurizr, C4-PlantUML, draw.io, Visio, spreadsheet, Mermaid or Markdown file, read by its suffix |
| `--out OUT` | where the pictures go; beside the file by default |
| `--png` | a PNG beside each SVG, through a Chrome or Edge on the machine or resvg-py where installed |
| `--mermaid` | the Mermaid beside each SVG as well |
| `--pack DECK` | the pictures as a deck too, a slide each with a cover before them: at DECK, or <file>.pptx beside the pictures |
| `--date DATE` | a date for the title block and the timeline's current quarter |
| `--example NAME` | print an example sketch to start from: payments (the default), on-a-shape, from-parts |
| `--views` | list the shipped views a sketch may name |
| `--library` | list the shipped shapes, kits and parts a sketch may put a product on |
| `--drawio` | write a draw.io file beside the pictures as well, a page per diagram, each box where the engine put it, the styles the reader takes back to their types |
| `--excel` | write what the file said as an Excel workbook beside the pictures, a sheet per type of record and the relations, nothing filled in to draw it: a Visio drawing in, an inventory out |
| `--plantuml` | write a C4-PlantUML file beside each diagram as well, the macros the reader takes back |
| `--editable` | with --pack: every diagram goes on its slide as shapes a reviewer can move, glued by its connectors, rather than as a picture; no browser needed for those |
| `--from-mermaid` | the file is a Mermaid flowchart, C4 diagram or sequence diagram, or a Markdown file holding them: read it as a sketch, write the sketch beside it, draw that |
| `--from-structurizr` | the file is a Structurizr DSL workspace: read it as a sketch, write the sketch beside it, draw that |
| `--from-archimate` | the file is an ArchiMate model, as Archi saves it (.archimate) or in the Open Group's exchange format (.xml): read it as a sketch, its views as views, write the sketch beside it, draw that |
| `--from-plantuml` | the file is a C4-PlantUML diagram: read it as a sketch the way a Mermaid C4 diagram is read, write the sketch beside it, draw that |
| `--from-drawio` | the file is a draw.io diagram (.drawio, compressed or not): a box per thing by its shape, an arrow per connection, a container per domain, a page per view; read it as a sketch, write the sketch beside it, draw that |
| `--from-inventory` | the file is a spreadsheet of systems (.csv, .tsv or an Excel .xlsx, its inventory sheet found by its headers): a row per thing, read by its headers, the type and the connections off the columns; read it as a sketch, write the sketch beside it, draw that |
| `--from-visio` | the file is a Visio drawing (.vsdx): a shape per thing by the master it was dragged from, a connector per connection, a container per domain, a page per view; read it as a sketch, write the sketch beside it, draw that |
| `--sketch SKETCH` | with --from-mermaid, --from-structurizr, --from-archimate, --from-plantuml, --from-drawio, --from-inventory or --from-visio, where the sketch is written |

## terrane adopt

Write a sketch, or a diagram a reader reads, into this repository as its own records; nothing already here is touched unless --correct.

| Argument | What it is |
|---|---|
| `file` | a sketch, or an ArchiMate, Structurizr, C4-PlantUML, draw.io, Visio, spreadsheet, Mermaid or Markdown file, read by its suffix |
| `--owner OWNER` | the org unit of this estate that owns what the sketch left without an owner; else the sketch's placeholder is adopted too, and said |
| `--dry-run` | say what would be written and write nothing |
| `--same NEW=OLD` | the sketch's NEW is the estate's OLD: renamed throughout before it joins, repeatable |
| `--correct` | a record already here takes the file's differing cells, written into its own file with the file otherwise left as it is: a reviewer's workbook back in; a blank cell is left alone, and a correction to what a shape made goes under the product's overrides |
| `--picture PATH` | draw the change first: what the file adds, in full, and with --correct what it corrects, with a heavy border or, for a connection, a heavy line, among what is there one hop away, faded; an SVG, or a PNG by its suffix |

## terrane pack

The review pack: a slide per view, with the model's numbers on the cover.

| Argument | What it is |
|---|---|
| `[VIEW[:SUBJECT]]` | the views to pack, a subject view as VIEW:ID; none means every view of the whole estate, every product on the product architecture, and the flows |
| `--out OUT` | where the deck goes; 70_ARTIFACTS/review-pack.pptx by default, not committed |
| `--date DATE` | the date on the cover and in the title blocks; today by default |
| `--all-rows` | every page of every register, eight rows a slide; by default a register's first page, saying how many rows there are |
| `--editable` | every diagram goes on its slide as shapes a reviewer can move, glued by its connectors, rather than as a picture; maps, registers, timelines and flows keep theirs |
| `--since REV` | open the deck with what changed since this git revision, drawn: the slide a review starts from; nothing changed is said and the slide left out |
| `--excel` | write beside the deck the workbook of what the slides show: the records on the pictures, the connections among them and a page per slide; read back by terrane draw, the same pages |

## terrane refresh

Render, schema, the seven exports and the test seed, in one go.

| Argument | What it is |
|---|---|
| `--no-seed` | leave 90_EXAMPLE/csv as it is |
