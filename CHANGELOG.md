# Changelog

## 1.3.0 (not yet released)

- **The rest of the estate on Add.** Four shelves more: the library's
  Building blocks, and the estate's Data (by classification), Actors and
  Teams. A data asset, an actor or a team placed is drawn with the lines
  that join it to what is on the diagram: the systems that read and write
  the data and the one that keeps its master, the systems the actor uses,
  what the team owns. A building block dropped into an account asks its
  name and who owns it (the owner most of the account's services have),
  and writes its services there, each the cloud's usual product, with
  their lines. A block's product is the provider's first choice, not the
  whole answer ("Amazon Kinesis", not "Amazon Kinesis or MSK").

- **Add on shelves.** The canvas's Add keeps what can be placed on
  shelves, each counted: Whole applications (the kits), Parts of an
  application, Business systems and Cloud services from the library,
  Systems and Boundaries from the estate. A shelf lists everything it
  holds under its headings (a kind's group, or its category), two to a
  row, each kind with an icon of its own; the one pointed at is described
  under the list with the kits that make one. Typing searches every
  shelf at once, listed by shelf and heading, the arrow keys moving
  through it and Enter placing it. It opens on the shelf picked last.
- **A list of products is split at its commas.** A provider's answer of
  "ADP, Workday Payroll or UKG Pro" offered two products; it is three.

- **Fifty more kinds in the library, each under a group.** The parts a
  system we build is made of (an admin console, a desktop application, a
  chat interface, a device application, a background worker, an event
  processor, a workflow, decision, notification, reporting and inference
  service, an integration adapter, an AI agent) and the business systems
  an organization runs (billing, payments, payroll, recruiting, marketing,
  e-commerce, the website's content, a support desk, order management, a
  warehouse, contract management, privacy and consent, fraud detection,
  identity verification, a health record and thirty more). A component
  type may say the heading it is listed under, `group`. The library's parts
  say these kinds of the systems they make, and two kits more: a customer
  portal and an API offered to partners.

- **A kit placed whole on the canvas.** The canvas's Add offers the
  library's kits beside its parts, so an AI assistant dropped on a diagram
  is six systems with their lines rather than one box. Dropped into an
  account, a kit asks its name, who owns it and what its parameters ask,
  says what each system runs on in that account's landing zone, and is
  written as one product assembled from it. A kit's parameter may say how
  it is asked (`ask`) and what kind of record its value names (`names`).

- **What organizations build again and again.** An AI agent kit that acts
  through the APIs it is given, every action logged; customer sign-in on
  each cloud's customer identity service; a feed of a product's data to
  analytics by change data capture; a partner API through the gateway; and
  document intake read by each cloud's document processing. A kind a part
  uses by default is now checked against every landing zone too.

- **An AI assistant kit.** A chat behind workforce sign-on, the API, the
  inference service calling the landing zone's model through its AI
  gateway, a retrieval index the named systems' documents are embedded
  into, and the conversation history, resolved on AWS, Azure and Google
  Cloud; and an AI assistant application type that requires it.

- **A network made once per account.** A network is made from a shape on
  each cloud, the VPC or virtual network with its subnets, NAT gateways,
  hub attachment and resolver link, three tiers by default; every system
  in the account lands in its subnets by network zone, with nothing
  written, and a kind that sits in no subnet says so (`subnet: false`).

- **A database's ways in and out.** A line drawn into or out of a database
  says what the estate does with that kind of store and offers its ways in
  or out first: its own service reading and writing it, and out of it a
  change data capture feed, a scheduled extract, a replica or a backup,
  four new connection kinds. A system of another product reaching into a
  database another service owns is said to be the shared database the
  library deprecates. A connection kind may say `datastore:`, which end is
  a data store.

- **Names the model does not hold, on Sources.** A column that names
  records, an owner most often, has its names on the Words step: each with
  its rows, the record it already is, or a choice of the kind's records,
  with one offered where it reads like the name, and the words they share.
  Nothing is chosen for you, and a name left holds its rows back.
- **Names that read alike, on Checks.** Beside the rules, the records of
  one type whose names read alike, grouped by why each pair is probably
  two things: a letter or a DR copy, another cloud, an interface's two
  ends, another place on the map. Not a finding, counted in neither box.

- **What is this line?, ranked.** A line drawn between two records, or a
  connection asked for, lists its answers in the order the estate makes
  them, each with why in the estate's numbers: a call the way the two
  systems lean, the likeliest marked and its likeliest kinds offered as
  chips that fill the form at once. Nothing is chosen for you.
- **Probably here already, on the adopt page.** A drawing dropped lists
  what it adds that reads like a record the estate has, with the estate's
  record, the score and the words they share, and a Same record box,
  ticked where one stands alone; the counts and the picture follow the
  boxes, and Adopt joins the drawing's records to the estate's, their lines
  with them, writing no second one. A record joined so is never corrected
  to the drawing's name, from the app or from `terrane adopt --same`.
- **What kind each record probably is.** Checks, under What the
  diagrams need, groups each record with no component type by the kind it
  most likely is, with the words that matched and the next kinds; a sure
  match is ticked, and Set gives the kind to what is ticked, each in its
  own file, with Undo.
- **Parts say the kind of what they make.** The library's parts and
  shapes give each system they make its `component_type` where a kind
  plainly is it, a web channel's front end a web application, a datastore
  a relational database, so a product built from parts comes out typed.
  A part with no such kind says none.

- **Heads from four notations.** A line picked names each end, At
  Customer, with a picker of the heads it may have: plain ones, UML's,
  crow's foot's and ArchiMate's. A UML or ArchiMate head draws its line
  as its notation does, and Assignment puts a dot at the other end. The
  picture, the deck and draw.io draw them all, PowerPoint its own where
  it has one.
- **Bends on a square or curved line.** A square or curved line picked
  has a handle on each stretch; carried across it, the stretch moves and
  the line keeps the bends it then has, still square, as things move.
  Remove the bends lets it find its own way around the boxes again. The
  picture, the deck and draw.io draw it through the same bends.
- **A line's words at three places, dotted, heavy, rounded.** A line
  picked lists its words by where they sit, its start, its middle and its
  end, with + Add a label for the next; its look is solid, dashed or
  dotted and S, M or L heavy; a square line's turns can be rounded. The
  picture, the deck and draw.io draw them all.
- **Styles for every diagram.** A style saved from the Style tab can be
  kept for every diagram, in the estate's model.yaml, rather than in one
  diagram's file; every diagram offers it, marked, and it can be removed
  from any of them. `terrane validate` checks them.
- **A group turned, and a place typed.** A group's panel turns it as one
  about its middle, left or right by the degrees said. The Arrange tab
  says where a shape sits and takes a place typed, from the corner of what
  it sits in or of the sheet.
- **Pages.** A diagram can have more than one page, as tabs at the foot
  of the canvas's sheet: each one more sheet in the diagram's file, with
  its own shapes and its own records placed, under the diagram's name and
  look. A click opens a page and a double-click renames it; + adds one;
  a page's menu opens, renames, duplicates, moves it left or right, or
  deletes it after asking. Each page is drawn as a picture of its own, and
  the review pack has a slide for each.
- **Drawing layers.** The canvas's toolbar opens Drawing layers: the
  diagram's layers top first, with the estate's records among them. A
  layer is shown or hidden, locked or not, renamed with a double-click,
  carried by its grip to another place, or deleted, what was on it going to
  the layer under it; what is drawn goes on the layer marked. A layer under
  the records draws under them, and a hidden one is left out of the
  picture, the export and the review pack. Ctrl+Alt+] and Ctrl+Alt+[ take
  what is picked to the layer above or below, as does Drawing layer in
  Arrange.
- **Swimlanes.** Swimlane, the last of Shapes, draws a pool of three
  lanes, stacked across it or side by side down it, each lane's name in a
  column at its left or a band at its top. What is drawn in a lane moves
  with it, and a box carried into another lane changes lanes. A lane can
  stand for an actor or an org unit: it is named as the record is, and the
  record's page lists the diagram. Lanes are added, reordered by their
  grips in the panel, made deeper by their handles, and deleted keeping what
  they held in the lane above. The picture, the deck and draw.io draw a
  swimlane as the canvas does.
- **Groups.** Several of a diagram's own shapes, picked, are grouped from
  the bar or the panel (Ctrl+Shift+G), and are then picked, moved, copied,
  pasted and painted as one; a double-click goes inside to pick one of
  them, Esc comes back out, and Ctrl+Shift+U ungroups. A group has a name
  and may hold groups. It has no box: its outline and name show while it
  is picked, and the picture, the deck and draw.io draw its shapes as
  before.
- **A double-click opens a shape's words.** maxGraph's own double-click
  stopped the event at the shape, so it opened the words only on an empty
  spot of the sheet, where there were none.
- **Ctrl+D on several keeps the diagram saving.** Every copy took the
  same key, and the diagram's file was refused from then on.
- **A link on a shape.** The words' toolbar's last button links a shape,
  a note, text or a frame to an address on the web or for email. A mark at
  its corner on the canvas opens it in a new tab; the picture, the deck
  and draw.io make the shape itself open it. An address of any other kind
  is refused.
- **Styles, and how the words are set.** The Style tab offers five styles
  to start from, Service, Data, Outside, Risk and Quiet, and a diagram's
  own, saved by name in its file with "Save this as a style": choosing one
  copies its look onto what is picked, and its chip is ticked while the
  look matches. A toolbar over the words sets them bold, italic,
  underlined or struck through, places them left, in the middle or right,
  and makes a note's or text's lines a bulleted list. The picture, the
  deck and draw.io set the words as the canvas does.

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
