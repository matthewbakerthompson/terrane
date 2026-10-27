# Changelog

## 1.2.0 (2026-10-27)

- **The export and the overview draw what the canvas draws.** Export's PNG
  and the overview in the corner of the sheet were taken from Cytoscape's
  drawing under the canvas, which holds the estate alone, so a frame, a
  note or a line drawn on the diagram was in neither. Both are drawn from
  the canvas's own model now, marks and words included, on the canvas and
  on a diagram opened read only.
- **The deck and the draw.io export draw the diagram's own.** Frames,
  notes, text, shapes and lines drawn on the canvas are on the editable
  deck's slide and the draw.io page, stacked as the canvas stacks them; a
  draw.io page read back leaves them out, so a note is not read as a
  system. `terrane.diagrams(root).drawio(...)` on a repository's diagrams
  failed on a name `quick.py` never imported; it writes the file now.
- **Names on the canvas sit where the layout set them.** A box's name was
  up to a pixel and a half low, its last line most, and a wrapped name's
  first line about a pixel to the right. Each name is now set from the
  lines the layout broke it into, at the layout's own spacing and
  baseline.
- **A frame takes the records it is drawn round.** Carried, nudged or
  lined up, a frame on the canvas moves the records wholly inside it as
  far as it goes, where the diagram keeps them, and one Undo puts the
  frame and the records back. A frame still sets no field the way a
  boundary does.
- **Equal spacing, measured.** A box carried in its boundary is put
  where its gap to a box in line with it is the next gap along, or the
  same both sides, the gaps measured in red with their size as it is
  carried. A box let go by a guide's line is put on it, which the guide
  had said and never done. A shape, a note or a frame of the diagram's own
  finds the gap the same way, against every box on the sheet.
- **A status bar under the canvas, and Snap to grid.** Under the sheet:
  how the diagram is laid out, with Lay out again, what is on it, and
  Snap to grid, which puts a record let go, and the diagram's own when
  it is drawn, carried or resized, on a ten-unit grid. The setting is
  kept in the browser.
- **A key for every tool, and Boundary in Add.** R, T, N, F and L choose
  Shape, Text, Note, Frame and Line, beside V and H; A opens Add and B
  opens it on Boundaries, which is a tab of Add's now rather than a
  button of its own. "? for keys" in the status bar, or ?, shows every
  key the canvas takes, and Ctrl+K lists the canvas's tools and actions
  first, each with its key.
- **Copy and paste across diagrams.** Ctrl+C keeps what is picked in the
  browser: the diagram's own, with what sits in a frame that is picked
  and the lines among them, and the records. Ctrl+V on any canvas
  diagram places the records it does not draw and draws the rest with
  new keys, a step on from where it was on its own diagram or in the
  middle of the sheet on another; a line keeps its ends where both came
  or are there. One Undo takes the pasted shapes away.
- **Lock it here.** A record or a shape of the diagram's own can be
  locked on a diagram, with Ctrl+Shift+L or Lock it here in its panel:
  it is not carried, nudged, lined up or taken along by a frame until it
  is unlocked. The diagram's file lists what is locked under `locked:`,
  and the record itself is not changed.
- **Turned.** A shape, a note or text on the canvas turns about its
  middle, by the handle off its top right corner when it is picked or by
  Turned in its panel, in whole degrees; a frame does not, since what
  sits in it would turn too, and neither does what is locked. The
  diagram's file keeps `rotate:`, and the SVG, the editable deck and the
  draw.io page draw it turned as the canvas does.
- **Quick connect.** Hover a box on the canvas, a record or a shape,
  note or text of the diagram's own, and four arrows come off its sides.
  Press one and the next box is drawn that way, joined by a line: a copy
  of a shape, open to type in, or, from a record, Add asks which record
  comes next and the line asks whether it is a connection. Carry an
  arrow instead to draw a line to the box it is let go on, or the next
  box there.
- **Line jumps.** Where two lines cross on the canvas, the one drawn
  over the other hops it with a small half circle, round corners kept;
  the PNG export draws the hops too. Line jumps in the status bar turns
  them off and on, and the browser keeps the choice.
- **Bends.** A straight line on the canvas bends where it is dragged:
  pick it and carry the dot halfway along a stretch. Shift and a click
  on a bend take it out, and Remove the bends in its panel takes them
  all. The diagram's file keeps them under `via:`, and the SVG, the
  editable deck and the draw.io page draw the line through them. A
  square or curved line still turns by itself.
- **Around boxes.** A square or curved line of the diagram's own goes
  around the boxes in its way, the estate's and the diagram's own, when
  its plain turns would run through one, and is routed again when
  something moves. The SVG, the editable deck and the draw.io page route
  it the same way.
- **Ends held where they are put.** Carry a line's end over a box and
  the points it can be held at show; let go on one and the end is held
  there, and a square or curved line comes into it square. An end can
  also be carried to another box, or off one to a point of the sheet.
  The file keeps a held end as `from_at` or `to_at`, a share of the box,
  and the SVG, the deck and the draw.io page hold it there too.
- **A name matcher in the engine.** `terrane.match` says which records a
  name from somewhere else most likely means, with the words that made
  it think so: rare words count more, an abbreviation counts most of a
  word, word order does not matter, and two names with different
  numbers are never the same. The CMDB reconciliation's last pass uses
  it, and offers a CI only to a system that has no CMDB record yet.
- **What kind a record probably is.** Every component type in the
  library has `aliases:`, the generic words it is also called, and
  `terrane.match.suggest_types` offers the three kinds a record most
  likely is, with the words that matched. `terrane needs --types` prints
  them for every record with no `component_type`, grouped by the
  likeliest kind, and sets nothing.
- **What a drawing names that is probably already here.** `terrane adopt
  FILE --dry-run` lists, for each thing the drawing calls by an id the
  estate does not use, the estate's records of the same type its name
  reads like, with the score and the words they share, and `--same
  NEW=OLD` (repeatable) renames the drawing's id to the estate's before
  it joins, so a ledger drawn as `SYS-LEDGER` is the estate's
  `SYS-CORE-LEDGER` and not a second one. `terrane.adopt(..., same=...)`
  and `join_estate(..., same=...)` take the same.
- **Search reads more than names.** The search box and the command
  palette score a query against an index of every record's name, id,
  tags, kind, description and domain, each word weighed by how rare it is:
  a half-typed word finds the words it starts, a misspelled one the word
  it is near, and a library alias the kind it names ("rdbms" finds the
  relational databases). The record a query names outright comes first.
  The hosted copy searches the same way from a baked index.
  `terrane search QUERY` lists the same from a terminal, and
  `terrane.search` is the module.
- **A Style tab and an Arrange tab for the diagram's own.** A shape, a
  note, text or a frame picked on the canvas shows two tabs, as V16 draws
  them. Style holds the diagram's look, the words and their size, the
  shape, the fill and how much of it shows, the edge and how heavy it is,
  the corners' radius and the hard shadow; Arrange holds its size, how far
  it is turned, and Bring forward and Send back. Copy the look paints one
  shape's look onto each one clicked next until Esc, and Ctrl+Alt+C and
  Ctrl+Alt+V do it by keys. The picture, the deck and draw.io draw the new
  settings as the canvas does.
- **Icon tiles, and the cloud marks on a shape.** A diagram can draw its
  own shapes as the clouds draw reference architectures (`look: tiles`,
  under Look in the diagram's panel): each shape a tile with an icon, its
  name and caption under it. A tile carries its kind's icon, one of 24
  plain icons, or any of the 168 AWS, Azure, Google Cloud and vendor marks
  the app ships for records, picked by set or found by a word
  ("kubernetes" finds EKS, AKS and GKE). A line held at a point of a tile
  ends on the tile, and a line leaving it downward runs under its name.
- **The diagram's own shapes are drawn Illustrated.** Shapes, notes,
  frames and lines drawn on the canvas take the app's own picture
  language: ink edges, a hard ink shadow under a shape or a note, a
  shape's first line its name in the display face and the rest a caption,
  a frame's name on an ink tab, an `accent` fill for what the drawing is
  about. The canvas, the picture, the deck and draw.io draw it alike.
- **A command's name comes first in Ctrl+K.** Typing the start of an
  action's name puts the action ahead of the records the search finds, so
  "note" and Enter choose the Note tool again.
- **Words on several lines keep their breaks.** A label or a description
  written over lines was saved folded and came back as one line; it is
  written literal now and comes back as it was written.
- **The matcher says a word as the name writes it.** "HL7" shared by two
  names is "hl7" among the reasons, not "7" and "hl".

## 1.1.0 (2026-10-25)

The canvas draws from scratch, and the sample estate comes with a pip
install.

- **The canvas, drawn by maxGraph.** New diagram and Edit draw and handle
  the canvas with maxGraph 0.25 (Apache-2.0), vendored as one script and
  loaded the first time a canvas draws; the views written as queries stay
  on Cytoscape, which still lays the canvas out. `?canvas=cytoscape` in the
  address opens the canvas as it was.
- **Drawing from scratch.** Shapes (ten of them), Text, Note, Frame and
  Line, straight, square or curved, drawn on the sheet as the diagram's
  own: moved and resized with handles and guides, dropped into a frame,
  restyled from the panel, typed into where they are, with Undo, Redo and
  a key for each. They are saved under `annotations:` in the diagram's file,
  which the view schema admits and `terrane.annotations` reads, never in the
  model, and drawn on the diagram wherever it is shown and in its SVG.
  A diagram of its own shapes alone is a diagram too. The deck and the
  draw.io export leave them out for now.
- **Several at once.** A drag across the sheet picks what it goes around,
  records and shapes together, and Shift-click adds or takes one; the bar
  over them lines them up, spaces them evenly or frames them. The Hand, H
  or Space held moves the sheet, and a boundary is picked up by its edge or
  its name.
- **A line between two records asks what it is.** Drawn from one record to
  another, a line offers the connections the metamodel allows between them,
  saved with the records, or just a line on this diagram. The Connect tool
  it replaces is gone; dropping one box on another still connects them.
- **Add finds a part by what each cloud calls it.** EC2, Azure Virtual
  Machines and Compute Engine find the virtual machine, a former name finds
  the product it is now, and a part dropped into an account of a cloud is
  named and recorded as that cloud's product.
- **Down a level, and back up.** A box's panel lists the diagrams about it,
  about what holds it and about its domain, each counted, and a
  double-click goes down to the first; a diagram about one thing names the
  level above it (`up:` in its view), drawn as a crumb over it, each level a
  click. A parameter may take a value of a field rather than a record, so
  `domain-landscape` draws the landscape of every business domain the
  systems name; it replaces `domain-servicing`, which drew one.
- **A drawing dropped on the canvas.** A Visio, draw.io or ArchiMate file
  dropped on New diagram's sheet shows what adopting it would add, drawn
  against the estate, with a box to correct what it says differently; Adopt
  writes what `terrane adopt` writes, and each of its pages is a diagram on
  the canvas.
- **A report past its limit** is listed whole, with a note saying so, and
  `terrane validate` warns `view.past_limit` for it. `integration-architecture`
  and `lifecycle-portfolio` draw up to 80 and 120, so neither drops a
  product, and `terrane needs` says how many more a limit cut.
- **`terrane init --sample`.** Copies the sample estate, a card issuer,
  out of the package into a folder of your own: its records and the
  inventory and CMDB export its Sources and Drift pages read, with
  settings that read the shipped library and views from the installed
  Terrane, as an estate `terrane init` starts does. `terrane app` there
  opens it as the sample, and a first visit offers the tour. Until now the
  sample and the tour were on the demo and in a clone of the repository,
  and the package carried only the sample's landing zones and answers.
  The package's own copy is never opened in place.
- **`terrane --version`.** Prints the version; it printed the usage.

## 1.0.1 (2026-10-23)

What an installed Terrane tells its user now names only what an install
has.

- **An empty estate.** `terrane app` on an estate with no records said to
  import `../90_EXAMPLE/csv`, a folder only a clone of the repository has.
  It now names Import in the app, `terrane adopt` for a spreadsheet and
  `terrane import csv` for a folder of CSVs, and where the sample
  spreadsheet inside the package is. `terrane init` names that
  spreadsheet too.
- **Import in the app.** The folder of CSVs was filled in as
  `90_EXAMPLE/csv`; it starts empty.
- **Taking the sample out.** Settings said `terrane clear` takes the sample
  out on every estate; it says so on the sample alone, and `terrane clear`
  no longer sends a person to a folder of the repository's for the columns.
- **The tour.** The package's page said the sample estate offers a tour
  without saying where the sample is: it is on the demo, with nothing to
  install, and in a clone of the repository. The demo's own notes name
  `pip install terrane` rather than a script in the repository.

## 1.0.0 (2026-10-23)

The first release on PyPI.

- **The model and its views.** A model of systems, interfaces, data,
  technology services, capabilities, processes, controls, policies and
  change, kept as YAML files a person would write; 48 views over it, each a
  query, in six layers: business, application, data, technology, governance
  and change.
- **The library.** Building blocks, parts, kits, patterns and shapes a
  product is composed from, twelve connection kinds, and three landing
  zones, all inside the package.
- **The app.** `terrane app` opens an estate in the browser: every diagram,
  the records as tables, the library, the checks and the canvas, with edits
  written back to the model, and a tour of the sample estate on a first
  visit.
- **The command line.** `terrane init`, `connect`, `draw`, `adopt`,
  `validate`, `render`, `pack`, `export`, `diff`, `needs` and more; see
  docs/COMMANDS.md.
- **Readers and exports.** Mermaid, Structurizr DSL, C4-PlantUML,
  ArchiMate, draw.io, Visio and CSV or Excel inventories read in; ArchiMate,
  draw.io, C4-PlantUML, Excel, CSV, JSON and Backstage out, and editable
  PowerPoint review packs.
- **From Python.** `import terrane`: `terrane.diagrams`, `terrane.adopt`,
  `terrane.since` and the exports, the same as the command line.
- **The license.** PolyForm Shield 1.0.0: free for any use but offering it,
  or something built from it, as a competing product or hosted service.
