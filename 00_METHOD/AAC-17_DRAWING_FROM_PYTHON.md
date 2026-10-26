# AAC-17: Drawing from Python

Every picture in this method is a query over the model, and the engine draws
the answer itself: the same layouts the app has, held equal to it by
fixtures, painted as SVG with nothing a browser has to compute, except where
a browser on the machine runs ELK and Cytoscape for the drawings the app
hands to them. This chapter is the manual for that engine as a diagramming
tool on its own: one file drawn with no repository, what a team already has
read in, the presets drawn from a notebook, a sketch adopted into the
estate, the estate written out for the tools other teams use, the review
pack, and what a commit changed, as a picture. The commands are run from
`50_ENGINE/`; from Python it is `import terrane` after `pip install .`
in the repository's root, which works from any folder.

## One file, drawn

A sketch is a YAML file holding a small model in the method's own
vocabulary and the views it wants:

```yaml
model: {name: Payments}
systems:
  - {system_id: SYS-WEB, name: Web portal, company_domain: Channels}
  - {system_id: SYS-API, name: Account API, company_domain: Core banking}
interfaces:
  - {interface_id: INT-1, source_system_id: SYS-WEB, target_system_id: SYS-API, protocol: HTTPS}
views: [system-context, application-landscape]
```

`terrane draw payments.yaml` lays it out as a repository in a scratch folder
and draws every view it names, and every flow it holds, as
`payments--<view>.svg` beside the file; `--png` rasterizes each through the
browser on the machine or resvg-py; `--mermaid` writes the Mermaid beside
each; `--pack` puts the pictures in a deck; `--drawio` and `--plantuml`
write the pictures as draw.io pages and C4-PlantUML files. A view may be a
shipped view's id (`terrane draw --views` lists them), a subject view with its
subject (`{use: product-architecture, with: {product: PRD-X}}`), or a view
written out in full with a `view_id`, `scope` and `edges`, drawn as written.
A sketch that names no views gets the context and the landscape. What was
filled in with a default, what a shape was answered for with a placeholder,
and what could not be drawn and why, are the notes the command prints and
the Python result carries; so is what validate says of the model behind the
pictures, every error by name and the warnings counted by code.

From Python:

```python
import terrane
pictures = terrane.diagrams(sketch)                   # a dict, YAML text, or a path
pictures["system-context"]                        # shows itself in a notebook
pictures["system-context"].save("context.png")    # or .svg
pictures.notes
pictures.pack("deck.pptx", editable=True)
pictures.drawio("sketch.drawio")
```

`terrane.diagrams` also takes the folder of a repository and the views to draw,
including a view written out as a dict and drawn over the estate without a
file, or, with no views named, every view of the estate with the reports as
tables.

## What a team already has, read in

Every reader produces a sketch: the records of their types, the connections
the method has between them, the views the file held as views of the sketch. The
reader is chosen by the file's suffix, at `terrane draw`, `terrane adopt` and
`terrane.diagrams` alike; `terrane draw --from-<reader>` reads the file and writes
the sketch beside it to correct and keep.

| File | Reader | What becomes what |
|---|---|---|
| `.mmd`, `.mermaid` | Mermaid | A flowchart's box is a system unless its shape says otherwise (a cylinder a data asset, a stadium an actor, a hexagon a capability); a subgraph is the domain; an arrow is the connection, its label the name or the protocol. A C4 diagram's elements are what C4 says. A sequence diagram is a flow, its messages the steps. |
| `.md`, `.markdown` | Markdown | Every Mermaid block in the file, read together: records merged by id across the blocks, a view per block named after the heading above it, each block's view scoped to what the block drew. |
| `.dsl` | Structurizr | A workspace's people, software systems and containers, its relationships, its views; a relationship tagged with a connection kind is of that kind, as the engine's own workspace writes it. |
| `.puml`, `.plantuml` | C4-PlantUML | Brought to the form the C4 reader takes: includes, layout macros, legends and named arguments taken care of; a `$tags` naming one of the method's types is the element's type. |
| `.drawio`, `.dio` | draw.io | Compressed or not; a box by its shape style, a container by its label as the domain, an arrow with its own label or the label riding it, a page per view. |
| `.vsdx`, `.vsdm` | Visio | A shape by the master it was dragged from, never by its text; a container, swimlane or group as the domain of what sits in it; a connector by the shapes its `Connect` rows glue it to; a page per view. |
| `.csv`, `.tsv`, `.xlsx` | A spreadsheet of systems | A row per thing, read by its headers spelled loosely; the type off a type column's words; the connections off the columns that name other rows. An Excel workbook is read with the standard library: the first sheet whose header row the reader knows, the rows above the header skipped, the other sheets said and left alone, a date Excel kept as a serial number read as the date it shows; a workbook in the method's own vocabulary, a sheet per type headed by its id column, a relations sheet and a views sheet, the one `terrane draw --excel` and `terrane export excel` write, reads back as the records and the pages it holds. |
| `.archimate`, `.xml` | ArchiMate | Archi's own file or the exchange format: elements of the ArchiMate types mapped back, relationships as the method's connections, every view of the model written out as a view. |

`terrane draw file --excel`, and `pictures.excel(path)` from Python, write what
a file said as a workbook beside the pictures: a sheet per type of record
and the relations, nothing filled in by default to draw it, so a Visio
drawing can be written out as an inventory. The workbook reads back as the
same records, its pages on a `views` sheet, so drawing the workbook gives the
same pictures as drawing the original file. A product on
a shape or assembled from parts is a row like any other, its answers in
`parameters.<name>` columns, what it is assembled on in `compose.provider`,
its parts in one cell (`web-app-baseline;async-worker`), and a view on a
subject a row of the views sheet saying what it uses and with what; what is
not a cell is said and left out rather than flattened.

Three rules hold across the readers. A thing drawn in two places in one file
is one record, its type settled across the file first, so a cylinder on one
page and a plain box with the same name on another are one data asset. A
page, a block or a view is a view of what it draws, not of every record of
its types. What the method has no connection for is said and left out,
never silently dropped or silently invented.

## The presets, from a notebook

A product in a sketch may sit on a shipped shape (`archetype:
azure-digital-product`) or be assembled from the library's kits and parts
(`compose:` with a provider and the parts), as in a repository: the
shape or the parts make the systems, the lines between them, the platform
services they run on and the data they master, and the shipped landing
zones stand in for the shared services a shape binds when the file names
none of its own. `terrane draw --library` lists the shapes, the kits, the parts
and the landing zone kinds; `terrane draw --example on-a-shape` and `--example
from-parts` are the two sketches. From Python the same without a file:

```python
terrane.presets()                                                   # shapes, kits, parts, landing zones, as data
terrane.diagrams(terrane.on_shape("azure-digital-product", "Rewards", answers={"account": "azure-cards-prod"}))
terrane.diagrams(terrane.from_parts("AWS", "Merchant portal", parts=["web-app-baseline", "async-worker"]))
terrane.diagrams(terrane.part("mobile-channel"))                        # one part, with the parts it requires
terrane.connect("SYS-A", "SYS-B", "API call")                       # an interface as the connection kind proposes it
terrane.made_by(terrane.from_parts("AWS", "Portal", parts=["web-app-baseline"]))  # what the parts make, by id, before drawing
```

What a shape or the parts make is knowable before the drawing:
`terrane.made_by(sketch)` lays the sketch out in a scratch folder the way `terrane
draw` does and says, by product, each record the shape made, its type, id,
name and the part that made it, so a sketch connects a part's system to the
rest of the estate by id (`terrane.connect(made_id, "SYS-CORE-LEDGER",
"queued-request")`) and the product architecture view draws the line; once
drawn, `pictures.made` says the same.

The connection kinds of `24_CONNECTIONS/` are presets too: `terrane.presets()`
lists them under `connections`, each with what a new interface of the kind
is proposed with; `terrane.connect(source, target, kind)` is that interface as
a record a sketch takes, the kind by its id or its name, a field of one's
own over the proposal; and in any drawing read, an arrow whose words name a
kind is of that kind, its style, protocol and authentication the proposal,
while an arrow that says a protocol one kind alone carries (`MQ`) takes
that kind's style and keeps its protocol; a protocol several kinds carry
(`HTTPS`) says nothing about the kind. Words that name no kind stay what
the reader made of them before. A hop of a sequence diagram whose words
name a kind is of that kind too, the arrow's own style yielding to the
kind's, and `terrane draw --library` lists the kinds beside the shapes, the
kits and the parts, with what each proposes. A drawing read for an estate,
by `terrane adopt` or `terrane.adopt(source, root)`, is read with the estate's own
connection kinds after the shipped ones, so a health system's HL7 feed is
its own kind there; drawn alone, a drawing goes by the shipped kinds. The
listings follow: `terrane draw --library --root estate` and `terrane.presets(root)`
list the estate's library after the shipped one, its own kinds and parts
included, and `terrane draw --views --root estate` and `terrane.views(root)` its
own views.

The library's own pages carry the same pictures: every shape as the product
it makes, every kit on each landing zone, every part with what it requires,
every block as the small diagram it is, and the library mapped twice, kits
to parts and parts to blocks. The estate's side of that linkage is the
Parts in Use view: every system a part made, grouped by the part, across
the products.

## Into the estate, and the change before it lands

`terrane adopt file` writes a sketch, or what a reader read, into the repository
as its own records: each its own file under `10_MODEL/` with a header that
says where it came from, the relation rows into `relations/adopted.yaml`,
the views the sketch wrote out into `30_VIEWS/`; nothing already there is
touched unless `--correct`, when a record already there takes the file's
differing cells, and a relation row its differing qualifier, written into
its own file with the file otherwise left as it is, comments and all, so
the workbook a reviewer corrected comes back as corrections (`terrane adopt
deck.xlsx --correct`); a cell left blank is left alone, since a workbook
cannot say "clear this", and a correction to what a shape made goes under
the product's overrides, where the method keeps what reality says
differently from the shape. What was already there is said, the estate is
validated after and the change in the count reported. `--owner ORG-X`
names who owns what the sketch left without an owner; `--dry-run` says
what would be written;
`--picture change.svg` draws the change first: what the file adds, in full,
and what a new product's shape or parts make, new too, and with `--correct`
what it corrects, with a heavy border, a corrected
connection as a heavy line, among what is there one hop away, faded, so a
reviewer sees it against the estate before anything is written; an estate in
a subfolder of its repository is copied for the drawing with the library it
names and its own. From Python, `terrane.adopt(source, root)` and
`terrane.change(source, root)`.

A page the file drew is written as the diagram of the things on it, pinned
to it, which is what a diagram drawn on the canvas is: the one page of a
file, which every reader calls `imported`, is named for the file, so a
second drawing adopted keeps its page beside the first; a type a reader
names bare (`- type: systems`) is the file's own records of it, never every
system the estate holds; and the page is filed under the layer most of its
things belong to. The app adopts a file the same way. A drawing dropped on
New diagram's sheet, on Settings > Sources or on an empty estate's first
page is staged outside the repository and read with the estate's own
connection kinds; its page shows the change picture without its title
block, what it would add, who owns what it names no owner for, and what the
estate has and the drawing says differently, with a box to correct it; and
Adopt writes what `terrane adopt FILE --owner ORG-X`, with `--correct` when
ticked, writes. The first page then opens on the canvas, its boxes the
records.

A diagram drawn on the canvas may also hold things of its own: shapes,
text, notes, frames and free lines, drawn with the canvas's tools, none of
them records. Its file lists them under `annotations:`, each with a key that
never changes, the frames it sits in by key, its corner in the innermost of
them or on the sheet, and its size, or a line's two ends, each a record by
id, a key of the list or a point, and its route, straight, square or
curved; `terrane.annotations` reads the list and
says what is wrong with it. Every picture of the diagram draws them as the
canvas does, from the same paths, fills and sizes: the frames, and what sits
in them, under the boundaries, and the rest over the boxes. A diagram of
them alone, nothing of the estate on it yet, draws them and nothing of the
model.

## Out again

Five formats take the estate to the tools other teams use, each rebuilt by
`terrane refresh` with the rest of the generated output
([AAC-05](AAC-05_CHANGE_FLOW.md#ci) says how a stale one is caught):

- `terrane export archimate` writes `70_ARTIFACTS/export/archimate.xml` in the
  Open Group's exchange format: elements of the ArchiMate types the reader
  maps back, relationships of the kinds it expects, every picture view
  placed by the engine's own layout. Archi imports it.
- `terrane export archimate` also writes a flow's protocol and its connection
  kind as properties on the relationship, with their definitions, so Archi
  shows them in its properties panel and the reader takes the flow back as
  the connection it was, protocol and kind and all, rather than as a name
  with the protocol in brackets. Every element carries its record's domain,
  hosting and kind as properties the same way, a flow its id and what its
  kind proposes as the record has it, a relationship the row it is with
  its qualifier or the field it draws, so the estate's own export reads
  back as the estate, with nothing to add or correct.
- `terrane export drawio` writes `70_ARTIFACTS/export/estate.drawio`, a page
  per picture view: each box where the engine's layout put it, in its shape
  and colors, each boundary a container holding what sits in it, each line
  through the bends the router laid down with its label where the engine
  placed it, in the styles the reader takes back, a line of a connection
  kind carrying the kind as an attribute of the object wrapping it, as a
  box's technology rides as its tooltip, so a page exported and read again
  is the sketch it came from, kinds included. Every box and line carries
  its record's type, id and the fields the picture cannot say as `aac_`
  attributes of that object, which diagrams.net shows as the shape's data
  and keeps through an edit, so the estate's own export reads back as the
  estate, with nothing to add or correct, and a box drawn by hand
  beside the export's reads by its label, shape and container as before.
- `terrane export plantuml` writes a `.puml` per picture view under
  `70_ARTIFACTS/export/plantuml/`: a `Person` per actor, a `System` per
  system, a `SystemDb` per data asset, a `Deployment_Node` per technology
  service, a `Boundary` per boundary, a `Rel` per line, and what C4 has no
  word for a `System` tagged with its type, the method's colors as the
  element tags, so the public PlantUML server draws it in the estate's own
  colors and the reader takes it back, types included; a `Rel` of a
  connection kind carries the kind's id as its tag, with an `AddRelTag`
  so the legend names it, and the reader takes the tag back as the kind,
  style and all. A `'` comment under each element carries the record's
  own domain, hosting and kind, which the picture cannot (a boundary is
  the view's grouping, and `System_Ext` says External of every SaaS
  system), so the estate's own page reads back as the estate, with nothing
  to add or correct.
- `terrane render` writes `70_ARTIFACTS/structurizr/workspace.dsl` beside the
  pictures, a Structurizr DSL workspace of every view that names the
  renderer: every element and relationship carries its record in a
  `properties` block, which Structurizr shows and keeps through an edit,
  so the estate's own workspace reads back as the estate; before, every
  element read back as a software system, told apart only by tags the
  reader ignored.
- `terrane export excel` writes `70_ARTIFACTS/export/estate.xlsx`: a
  contents sheet, a sheet per
  entity type with the CSV export's columns, the systems first so the
  spreadsheet reader takes the workbook back as the inventory it is, and
  every relation row on a sheet of its own. The interfaces sheet carries a
  `kind` column, each connection's kind read off its style and protocol
  against the estate's own kinds after the shipped ones; read back, a kind
  word fills an interface that has neither as the kind proposes, and
  changes the style and protocol of one that said another kind.

From Python, `terrane.export_archimate(root, out)`, `terrane.export_drawio(root,
out, views=[...])`, `terrane.export_plantuml(root, out, views=[...])`,
`terrane.export_excel(root, out)`, and for a sketch's pictures
`pictures.drawio(path)` and `pictures["view"].plantuml`.

## The review pack

`terrane pack` builds a review deck from the model, so it cannot disagree
with it: a cover with the model's
numbers and what validate says, a contents page by shelf, one slide per
view with its picture and its own account of what it is, one per product
drawn with the product architecture view, one per flow; `terrane pack
system-context product-architecture:PRD-X` the slides named. A register
goes on one slide, its first page of rows; `--all-rows` every page. The
Pages workflow builds it with no Node. Three flags change what a slide
holds, or what goes beside the deck:

- `--editable` puts every diagram on its slide as PowerPoint's own shapes
  rather than a picture: each box the shape the engine drew, in its fill
  and ink, each line a connector glued to the boxes it joins and bent where
  the engine bent it, each label its card, so a reviewer moves a box and
  the lines follow. The marks in a box's corner, the legend and the fan of
  a bundle on a map stay on the picture, and a deck of nothing but diagrams
  needs no browser.
- `--excel` writes beside the deck the workbook of what the slides show:
  the records on the pictures, the connections the model has among them
  and a page per slide saying what it shows and which lines, so a reviewer
  corrects a name or an owner in Excel and `terrane draw deck.xlsx` draws the
  same pages again. A register is a table, not a page of records, and is
  said and left out. From Python, `terrane.diagrams(repo, views=[...]).excel(path)`.
- `--since REV` opens the deck with a slide of what changed since that git
  revision, drawn.

From Python, `pictures.pack(path, title=..., editable=True)`.

## What changed, as a picture

`terrane diff SINCE [UNTIL]` says what moved between two revisions in the
model's own terms; `--picture change.svg` draws it: what was added in full,
what was removed dashed in red (put back into a scratch copy of the later
model for the drawing, since a picture of what is gone has to hold it),
what changed with a heavy border, and what is there unchanged one hop away,
faded; a line added in full, a line removed dashed, a line that changed
heavy, a line that did not move faded. The change-scoped drawing reaches
one hop along the structural relations only, counted off the rows from what
was added or removed, so a new line to the ledger brings the ledger and not
the estate; `--view application-landscape` puts the same marks on a
view of the whole estate. From Python, `terrane.since(root, "HEAD~5", view=...)`.

The same change is a workbook: `terrane diff SINCE --excel change.xlsx` writes
what was added, what was removed, each field that changed with its value
before and after, the relation rows added and removed, the views, the shapes
and the parts, a sheet each and only where there is something to say, the
change log a governance board is sent in the model's own terms; from Python
`terrane.export_changes(root, since, out)`. A connection whose fields moved it
into another kind is said as the kind first, `kind: queued-request ->
scheduled-pull` above the protocol and the style, the one word the reviewer
used; a connection the library moved under, its own fields unchanged, is a
change of that one line. An estate kept in a subfolder of its repository
diffs the same way: the export of a revision carries the library its
`shipped_library` names, from that revision, at the place the name reaches.

## A review, end to end

The pieces above make one loop, which is how an estate is reviewed with
this tool and nothing else installed:

1. `terrane pack --since HEAD~5 --excel` writes the deck, opening with what
   moved since the last review, and beside it `review-pack.xlsx`, the
   workbook of what the slides show: a sheet per type of record, the
   relations, the pages, a `kind` column on the interfaces sheet.
2. The reviewer reads the deck and corrects the workbook in Excel: a name,
   an owner, a date, a connection's kind by one word, a row added for what
   is missing. What Excel does to a typed date on the way is undone when
   the workbook is read.
3. `terrane adopt review-pack.xlsx --correct --dry-run --picture change.svg`
   lists every change the workbook would make, cell by cell and row by
   row, and draws what it would add in full and correct with a heavy
   border, a corrected connection as a heavy line, among what is there
   one hop from what it adds; nothing is written.
4. `terrane adopt review-pack.xlsx --correct` writes the corrections into the
   records' own files and the additions as records of their own, the
   files otherwise left as they are, comments and all; `terrane validate` says
   what the estate now says, and `terrane refresh` redraws every picture and
   export from it.
5. `terrane diff HEAD~1 --excel change.xlsx` is the change log the board is
   sent, and `terrane diff HEAD~1 --picture change.svg` the same change
   drawn.

From Python the same loop is `terrane.diagrams(repo, views=[...]).excel(path)`,
`terrane.change(path, repo, correct=True)`, `terrane.adopt(path, repo, correct=True)`
and `terrane.export_changes(repo, "HEAD~1", out)`; an estate with a library of
its own goes by its own connection kinds at every step.

## The package

The engine has no dependencies: a bundled reader covers the YAML the model
uses, the painter is pure Python, and the browser on the machine is used
only for ELK, Cytoscape and PNGs. The package is `terrane`, since
the repository's own name was taken on PyPI, and it is run and imported
as `terrane`: `pip install terrane`
once a release is up, or `pip install .` in the root of a clone; the
wheel carries the shipped views, library, marks, faces, ELK, Cytoscape,
examples and landing zones under `terrane/shipped/`, and the LICENSE with its
notice, so `terrane draw` and `import terrane` work from any folder, and `terrane
init` starts an estate in a repository of its own that reads the library
and the views from the package and pins the release it is checked with
([AAC-15](AAC-15_ADOPTING.md#the-first-day-an-empty-model-that-passes)). `python
tools/wheel_check.py` builds the sdist and the wheel from it, installs
the wheel into a fresh environment and checks it from an empty folder, and
`python tools/release.py --upload` runs it, with the gates, and publishes
the two it checked. The project is the repository, so the sdist carries
the views and the library beside the engine, and a wheel built from it
alone is whole.

## Where it is thin

- ELK and Cytoscape run in a browser on the machine; without one, the small
  unlaned diagrams the app hands to ELK are placed by dagre and say so, and
  a flat drawing past what ELK takes is refused with the reason.
- The editable deck keeps the marks in a box's corner, the legend and the
  rounding of a line's turns on the picture; PowerPoint takes a connector
  only as one of its presets.
- A nominal field a view colors by changes nothing, by the palette's own
  rule, so the product on the Parts in Use view is read off the names.
- A diagram's own shapes are in its SVG and the PNG made from it; the deck
  and the draw.io export leave them out for now.
- The draw.io and C4-PlantUML exports carry a tile map as boxes in bands
  and a system's technology line as a tooltip or a sentence; the ArchiMate
  export leaves roadmaps out, which have no counterpart.
