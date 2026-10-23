# The app

A local web app for the architecture model. Standard library Python, binds to loopback,
makes no outbound calls.

```bash
python app/server.py
```

That is all the launchers do. It works from any shell and any folder, because the
server finds the model from its own path. The launchers only save typing: `run.cmd`
for `cmd` or a double-click in Explorer, where a Windows policy blocks PowerShell
scripts; `run.ps1` for PowerShell; `run.sh` for bash.

Then open http://127.0.0.1:8020. `--port`, `--host` and `--root` are accepted, by the
launchers too.

## Why this exists

The engine on its own is a command line tool, and a model that can only be changed from
a command line gets changed by one person. That person hears about changes second-hand,
weeks late, and within two quarters the model is stale. A stale model that people still
trust is worse than no model at all.

So the app is not a nicety. Editing the model and looking at the model have to be the
same activity, available to the team that owns the systems, or the change flow in
[AAC-05](../00_METHOD/AAC-05_CHANGE_FLOW.md) does not actually run.

## What it does

| | |
|---|---|
| **Map** | Every view, drawn with Cytoscape, edge to edge, the key and the controls floating in the bottom corners and the fit leaving them clear; a view morphs into the next, what both show gliding into place and what is new fading in. A layered drawing with few, unordered boundaries is laid out by ELK (vendored): boundaries as containers, every connection routed around nodes and boxes, labels placed by the layout; a drawing with ordered tiers or many nested boundaries keeps the lane-aware layout and router. Pan, zoom, fit, fit to width for a tall drawing, click through, switch layout, export PNG. A report is a table and a timeline a grid of quarters; a map with nothing connected (the capability map, the value streams, the process landscape, a framework's landscape) is a tile map, in HTML rather than on the canvas: a band per top-level boundary where the field has a reading order, a card per boundary otherwise, each thing a tile tinted by the view's dimension, every tile a button, the whole wrapped to the sheet and scrolled, and **Fit** shrinks it until the whole map is on the sheet; and exported as a picture through the same PNG button and review pack; the rest are drawn. Hue and shape are the entity type, and a node whose corner carries no provider mark or component glyph carries the type's own mark there, so a box reads without the legend; the view's dimension is a border weight and tint, a border style, or the boundary; line style is the relationship. On a layered drawing the edges are routed round the nodes, the boundaries' names and the boundaries that hold neither end: each leaves and arrives square at its own point on a node's side, and lines through one gap are spread apart; the committed SVG pictures are routed the same way, to the same points. A label sits on its own line, in a card, turned along the line where there is no room upright; past thirty-six labeled connections the labels are off until a node is hovered or **Labels** is pressed. Arrow keys walk the nodes, Enter opens one, Escape lets go, `/` opens the jump box. The sidebar folds away from its own corner and comes back from the strip over the sheet; the inspector folds from the strip; on a window narrower than 1240px the inspector is a sheet over the drawing that a selection opens and Escape closes. The strip names the view under a crumb back to its layer, tags its kind, and offers **Edit**, **Export** (the picture or the source) and a menu with **Sketch**; its description is one line there and whole in the inspector when nothing is selected. **Help** is a page that says the three things to do, how to read a drawing with the legend's own swatches, and the keys. A boundary is drawn the way its provider draws that kind of container and named by kind, with a legend row for the kinds on the sheet. Where a drawing carries a recorded flow's interfaces the inspector lists the flow, and a click walks it: the hops numbered on the picture, the rest dimmed, the steps not on this drawing said so. **PNG** exports a sheet with the view's title, description, date, counts and legend around the drawing at 2x. Under a system's name, smaller, the platform services it uses; under a technology service's, the kind of thing it is; *SaaS* under a bought one. The boundaries of a field with a reading order (tiers, lifecycle status, scales) are laid out in that order, whatever the edges between them say. A technology service carries its provider's own icon in the corner, a bought system its vendor's where the vendor lets the mark travel, and a system of ours the mark of the platform service its line names first (EKS, Azure SQL, Snowflake), so the logo and the words agree; `web/icons/CREDITS.md` says whose each is |
| **Inspector** | With nothing selected, the view: its description, its counts, the kinds of thing on it and the key to its dimension, each a filter. With something selected, the type of thing it is in the type's own color, its name in the heavy sans, its placement as chips, its description, and everything it connects to grouped by relationship in words. Click a relationship to walk the estate |
| **Editor** | Add or change an entity. Saves where the record lives: its own file rewritten, or its own lines in a file it shares with others, every other line left as it was and a field whose value did not change keeping its lines. A record a business-layer import harvested moves into a file of its own, which the import then leaves alone; one an import rewrites whole (a capability, a control) says so in the inspector instead of offering a form the next import would undo. A save the reload refuses is put back |
| **Assemble** | A project from parts, with four steps in the head read off the state (what it is, its parts, its details, review and save) and the one button that writes beside them. The first question is what kind of thing it is, asked as rows with a radio each: a build type from `29_TYPES/` locks the parts every build of its kind has, ticks the ones it usually has, offers the rest, folds the others away, and lists every deviation from the standard as it is made; the kinds of application (a web application, an internal tool, an event-driven service, an integration adapter and the rest) each require their standard kit, one tick that picks the parts the application is made of; the landing zone is a row of segments and its standard services are listed under it, so nobody chooses the load balancer. Then the parts of the library as cards with a thumbnail of what each makes; pick several, start from nothing or from a shape, answer the project's own questions, and watch its architecture drawing resolve over a scratch copy of the model. Rename, drop or set a field on anything the chunks make; each edit is an override or an exclusion on the project. Writes one product file whose `compose` block is the whole architecture, or that file and a new shape when the choice is worth keeping. Opens a project it made before, from its own list, from the product's inspector or by address (`#assemble&open=PRD-…`), with the chunks picked and the edits in place; Save rewrites the file and keeps the note above its data, and a changed id makes a new project beside it. A product on a shape opens too, in the shape's terms: its chunks and choices, the shape's own questions, Save writing what it drops, adds or chooses, or a compose block of its own when told to let go of the shape. List answers are rows, not JSON |
| **New** | Build a whole product from a shape: five answers, nine entities |
| **Settings** | Under the sidebar's foot. **Sources**: drop a CSV or Excel export and bring it in through three steps that write nothing until **Bring in**: which column is which field (filled in from the column names, to check), which of its words are the model's (a word left unmatched holds its rows back), and a review of every record it would add, what is left alone, the rows that wait, and what the checks would newly say. Kept, the export and its mapping go in `60_SOURCES` beside a note of the last run, and come in again with one click; a CMDB export is listed as a source that compares, counted and opened in Checks. **Project**: the estate's folder, repository, library and governance, and whether its ignore file keeps credentials out, with a button that adds the lines when it does not; and another estate, started (`terrane init`), joined (`terrane connect`) or opened, which the app switches to without a restart. The estate's name above the search opens the same three as a menu, with the estates this browser has opened. **Connections**: a live pull is not built yet, and the page says how its credentials will be held: never in the repository, read from an environment variable or a secrets manager when used. **Appearance**: Stone or Graphite |
| **Import** | Every Import in the app opens Settings, Sources. A folder of metamodel v2 CSVs is still brought in from there: existing records are reported, never silently replaced |
| **Changes** | What changed in the architecture between two revisions, in the model's own terms: entities added, removed and changed field by field, relationship rows, views and the library. Asks git locally; the hosted copy shows the change since the previous commit |
| **Drift** | The model against a ServiceNow CI export, read-only: coverage, findings by category with what each asks of a person, every mismatch with both values and the field's source of truth, each a click from its system. The sample export by default |
| **What the diagrams need** | A tab of Checks: every diagram's state (full, thin, nothing to draw yet, drawn for one thing at a time), the fields to fill with how many records lack each and which diagrams read them, the kinds of record the estate has none of, and the lines, all read off each view's own query (`terrane/needs.py`, `terrane needs`). A diagram that draws nothing says in place of the drawing what it draws and what the records lack; a thin one says it in a line over the drawing and in **What it needs** beside it. **Set on many** lists the records lacking a field with what a person decides by beside each name, narrows them, and sets one value on the ticked ones in one save, each record changed where it lives; **Undo** puts the files back as they were |
| **Library** | Six shelves as tabs, one on screen at a time. Patterns: a block plus the decision, with its status, the controls it satisfies, and which products apply it, read off the model. Parts: what a product is composed from, each with a thumbnail of what it makes. Blocks: the fourteen handfuls of components that arrive together; pick one, name what is being built, see exactly what it creates, add it. Component types: the hundred and nine underneath, the AI services, the security tooling and the enterprise applications among them. Landing zones: each provider a shape lands on, the shared service of each kind, who asks for it, and the kinds asked for that it does not have. Shapes and the estate: which products are on a shape and which a shape would reproduce |
| **Home** | The start page: what the tool is for in a line, **Import** and **New diagram**, the diagrams opened last in this browser (or the ones to start with), each layer with its sections and its count, and the model in a sentence. An empty estate opens on its first three steps instead: bring in the inventory (the drop zone is on the page), see what the diagrams need, draw; the sample says it is the sample, with a button to start your own and one to take the tour. A first visit to the sample is offered the tour once: seven steps, each with a pointer that travels to one control, a ring around it and a card saying what to press, with Show me to have it pressed. Help and the jump box start it again whenever |
| **Frameworks** | The capability map with a framework lens: choose BIAN, ITIL or any other above the whole map and the capabilities placed in it are marked, the rest faded. **Frameworks** is every framework against every domain in one grid, a ring for how firmly the domain follows it and a number for how many of its capabilities are placed in it; a column or a number opens that framework's landscape. **Map to a framework** in a capability's details writes where it sits, and for a domain how firmly it follows |
| **Diagrams** | Every diagram the model draws, as a picture, a tab per layer and one for the flows, with **Import** and **New diagram** beside the title; a layer's name in the sidebar opens its page, the diagrams under their section headings. The sidebar lists the layers, each opening on its sections (Capabilities, Frameworks, Landscape, Integration, …) and those on their diagrams. The six a newcomer should see lead; each card says what its boxes are ("22 capabilities", "14 systems, 8 actors") or that it is drawn for one subject at a time. The pictures are drawn, not shot: two inks and paper on a dotted plate, one accent where the eye should go, the same set in either tone (`web/app.js`, `ILLO`; designed in `design/architecture-model.pen`) |
| **Tones** | Stone or Graphite, under Settings, Appearance, kept per browser. Stone is warm grays with a teal accent and a light sidebar; Graphite neutral grays with an amber accent and a dark one. A tone is the chrome and the drawings together: the server styles every drawing in the tone the page asks for, from the engine's palette for it, which gives every entity type a hue of its own, and an estate can override any of it under `palette:` in `model.yaml` (`base:` picks the tone a page opens in) |
| **New** | One menu over the sidebar's foot for everything that can be made: a diagram, a system, a connection, a flow, a product from parts or a shape, or an import |
| **Jump** | One box for everything, from the sidebar, Ctrl+K or the slash: views, the things in the model and the actions the pages offer, ranked by how early the words match; with nothing typed, the views opened most recently. Resting on a view in the sidebar shows its miniature, its description and its size before it is opened |
| **Model** | The model as tables: every type and every relation in a list down the left, each entity type with its own swatch and every row with its count; the table beside it named with its records and fields, every field of every record, sortable, filterable, downloadable as CSV or JSON. Works on the hosted demo |
| **Coverage** | What the model does not say — capabilities nothing realizes, systems with no owner, data with more than one writer — and how much of each field is filled in |
| **Compose a shape** | Pick modules, blocks with what the landing zone provides, patterns, and the vocabulary an instance is asked for; the archetype file is written and opens in the editor for a preview |
| **Edit shape** / **Write a new archetype** | The archetype itself, with a preview of every entity one instance would create. Saving re-expands every instance of it |
| **Edit YAML** | The file behind an entity, comments and all, for the times a form cannot say it. Generated entities and shared files are read-only, and say why |
| **New diagram** | Opens a canvas, not a form: a sheet with **Add**, **Select**, **Connect** and **Boundary** over it, and the details of whatever is selected beside it. **Add** (or a drag from its list) places a library part as a new record, named where it is dropped and given the fields of every boundary it lands in; a system the estate has, drawn as it is; or a view, an account or a network zone as a boundary, which the diagram's file names (`places:`) rather than copies, so the diagram follows the view. The panel edits a record's name, owner, status and criticality, says what it still needs to pass the checks, and for a placed view, which of its accounts are left off this diagram. Written to `30_VIEWS/` as it is drawn; **Edit** opens it on the canvas again |
| **Edit view** | What a diagram shows and how it is laid out, in a panel beside the sheet, each part said as a sentence: show a type, only where a field has the values chosen (offered from the model), also bring in what is linked to it, what is pinned or hidden, which lines to draw (only those that can join what is shown), what to group into boxes and color by, its direction and size. Fields are named in words, not column names. Every change redraws the sheet; Save writes the file by value, so comments and hand-wrapped text survive. **Edit the file instead** is the same view as YAML, and **Back to the parts** returns. For a diagram written as a query; one drawn on the canvas opens there |
| **On this view** | Change one drawing without changing the model. Right-click a box, or select it and press Delete, to hide it from the drawing in view; **Add to this view** on the drawing's summary pins anything in the model to it. Each is the smallest change to the view's `scope.pin` or `scope.hide` that does it, comes with an Undo, and is listed on the summary with a button to take it back, so a pinned box is never mistaken for one the query found |
| **Source** | The generated Mermaid and Structurizr DSL for what is on screen, to copy |
| **Focus** | Draw the neighborhood of anything: that entity, N hops out, every kind of connection. A view nobody had to author |
| **Sketch** | Author a diagram by choosing. Pick things from any view, one at a time, a screenful, or everything connected to one; draw them together; then write the sketch back as a view file whose scope is the list itself, or as a module in the library with the entities rewritten as templates in the vocabulary of the shape that made them. *New…* creates a thing placed like the picked ones; *Connect…* creates an interface between two picked systems. When the picked things belong to a product made from an archetype, the new thing is offered to that product and written under its instance's `extra`. The drawing is never the artifact; the file is |
| **Connect** | Drop one box on another, or choose **Connect to** from a box's menu or the inspector and pick the other end. The chooser lists every way the metamodel joins those two kinds of thing, both ways round: a relation (asking for its qualifier with the words the model already uses), an interface between two systems (the form filled in), or one naming the other in a field such as its owner. What is recorded already is shown as recorded. A connection the drawing would not show says so and offers to draw that kind of line there. Relations land in `relations/app_edits.yaml`; **Every link of…** lists those and takes them back |
| **Move into a boundary** | Drag a box into another boundary on a drawing. A boundary is one value of the field the view groups by, so the drop sets that field on the record: the chooser names the field, the value from and to, and every other view grouped by it where the box moves, joins or comes off, a subject view once per subject. **Move it** is the one-field save (`/api/save` with `patch`), written where the record lives, and the toast's Undo is the same save with the old value. A record made by a shape, or imported, says where it is changed instead; a drop on empty sheet, into its own boundary, or into one that is a kind of thing does nothing. Where the box was dropped is not kept |
| **Flows** | A page, from the Flows row under the layers: what a flow is in a line and **New flow**; the flows down the left with their steps and criticality; the one chosen drawn as a sequence on the right, a column per participant in order of first appearance, a numbered arrow per hop with its protocol, dashed where the hop is an event or a batch; drawn from the steps the model records rather than from the Mermaid the renderer writes, so the two cannot disagree. Every participant is a way to the thing itself |
| **Impact** | What breaks if the selected thing changes, what it needs, graded by distance, blast radius lit on the map |
| **Checks** | One page with four tabs, each saying in a line what it answers. **Validate**: the totals as tiles, the rules on the left as a list that narrows the right, the findings grouped by rule with the file each came from; errors first, which block a merge. **Coverage**, **Drift** and **Changes** are the next three tabs; the Checks row in the sidebar carries the error count in red, and nothing when there are none |
| **Render** | Regenerate `70_ARTIFACTS/` — Mermaid, Markdown, Structurizr, CSV, Backstage, JSON |

Everything it does is also available as `python -m terrane ...`. The app is a second way in,
not a second source of truth: it writes the same YAML files you would write by hand, and
`terrane validate` is the gate in both cases.

## Layout

```
app/server.py       stdlib HTTP server, JSON API over the engine
web/index.html      the page: the sidebar, the strip over the sheet, the sheet, the inspector
web/app.js          map, inspector, pages, forms
web/styles.css      the tokens and every rule; the redesign's rules at the end, which win
web/fonts/          Geist, Libre Franklin and Geist Mono, self-hosted (fonts/README.md)
web/vendor/         Cytoscape, dagre and ELK, committed
design/             the pen.dev design the shell is built from, and a capture of each page as shipped
```

The design comes first and the code follows it: `design/architecture-model.pen` holds
the brand, the type, the node system and every page as drawn, with a capture of the
shipped page beside each, so the two can be compared on one canvas. `design/README.md`
says what is where and how to open it.

## Links are the state

The view and the selection live in the address bar
(`#view=onboarding&p_product=PRD-INSTALLMENT-LENDING&id=SYS-CORE-LEDGER`), so a link lands someone on the same
diagram with the same thing selected. A hosted map nobody can link into is a map
nobody sends to anyone, which is most of the value of hosting it.

## Two things to know

**It writes to your working tree.** Every save, delete and import changes files under
`10_MODEL/`. Run it in a git checkout and treat the diff as the record of what happened.
That is the point: the app produces reviewable commits, not database rows.

**It refuses some edits on purpose.** A generated entity cannot be edited or deleted
directly — the archetype instance owns it, and the next render would overwrite the
change. A record sharing a file with others cannot be deleted, because removing the file
would take the rest with it. Both refusals say what to do instead.

## Publishing a read-only copy

A view that takes a subject is baked once per subject, so the picker works on
the hosted copy exactly as it does locally; the 308 subject graphs add about
3 MB.

```bash
python 80_APP/tools/export_site.py --out site
```

That one run bakes the checkout's model into `site/` and every estate in the
exporter's `ESTATES` into a folder of it -- the second estate, Thurman Health,
into `site/thurman-health/` -- each by a process of its own, then writes an
`estates.json` beside every home page so each names the others and marks its
own. `--root` bakes one model alone, as `server.py --root` opens one:

```bash
python 80_APP/tools/export_site.py --root 90_EXAMPLE/thurman-health --out site/thurman-health
```

The README's pictures come from the running app the same way a reader's
would -- the PNG button's export of the whole drawing, with the rail folded
so the sheet is wide -- by a tool that drives the Chrome or Edge already on
the machine through the engine's own browser driver, nothing installed:

```bash
python 80_APP/tools/screenshots.py         # all seven; name some to re-take a subset
cd 50_ENGINE && python -m terrane pack         # review-pack.pptx: a slide per view, from the model
node 80_APP/tools/dev/shots.mjs card=view=product-architecture\&p_product=PRD-CARD-SERVICING
                                           # any drawing to a PNG; see tools/dev/README.md for the other probes
python 80_APP/tools/render_svg.py --embed-fonts application-landscape tiered-architecture
                                           # the same sheet as SVG, drawn in Python with no browser
```

Every map and the layered diagrams can also be drawn without a browser.
`50_ENGINE/terrane/draw/` lays the view out the way the app does -- the browser's
dagre ported beneath a layered diagram, the stylesheet's own arithmetic and
Chrome's line breaking for a tile map -- routes the edges the way the app
does and paints the sheet as SVG; `terrane render` writes one for every such view
under `70_ARTIFACTS/svg/`, linked from the index and from each view's page,
and CI holds them fresh with the Mermaid; `GET /api/svg?view=tiered-architecture`
serves the same picture from the running app, and tests hold every node,
every boundary, every turn of every edge and every tile to the app's own
coordinates. The payload both draw from is the engine's (`terrane.payload`), as
is the icon map (`terrane.icons`); the marks themselves stay in `web/icons/`. A
small unlaned diagram the app hands to ELK is laid out by ELK here too, the
app's own `elk.bundled.js` run in a browser on the machine; without one it is
drawn on the dagre path, which the sheet's `data-layout` attribute says and
the index marks. The hub view's wheel is Cytoscape's concentric layout,
ported; a flat drawing past what ELK takes that dagre ranks into a ribbon is
laid out by Cytoscape's own cose in the same browser, seeded as the app seeds
it, and held equal to the app by a fixture. `terrane render --png` rasterizes each SVG
through resvg-py where it is installed, into `70_ARTIFACTS/png/`, which is
not committed because CI has no rasterizer to hold it fresh.

The review pack is the engine's own: `terrane pack` draws every view with the
same code `terrane render` uses, ELK through the browser where the app would use
ELK, rasterizes each sheet through that browser, and writes the deck with the
standard library (`terrane/pptx.py`), so nothing is installed and the app need
not be listening. A cover with the model's numbers and what validate says, a
contents page by shelf numbered as the deck is, and a slide per view with its
picture, its own description and its counts. Every view without a subject is
in by default, then a slide per product drawn with the product architecture
view, then the flows; any other subject view is named as
`onboarding:PRD-REWARDS`. The deck is a picture of a commit and
is not committed; the Pages job builds it beside the hosted demo on every
push to `main`, so the deck at the demo's address is always the deck of the
commit shown, and the Diagrams page links it where it exists. The second estate gets its own, drawn by `terrane --root
90_EXAMPLE/thurman-health pack`, in its own folder, so the hospital's home page
offers the hospital's deck.

Calls every GET handler once, writes the answers under `site/api/`, copies the web
assets, and injects `static-shim.js` ahead of `app.js`. The shim rewrites
`fetch("/api/...")` onto those files, refuses anything that is not a GET, and
disables the controls that would need a server.

`app.js` is copied unmodified. That is the point: the hosted demo cannot drift away
from the local tool, because it is the same file reading pre-baked answers.

`.github/workflows/pages.yml` runs the same command on every push to `main`.

## Security

No authentication, no authorization, loopback by default. It is a local tool for whoever
owns the checkout. Do not put it on an interface anybody else can reach; `--host` exists
for container networking, not for sharing. That matters more now that the app can start an
estate in, clone into, or open any folder its user types, as `terrane init` and `terrane
connect` would from their terminal; a folder that already holds files is refused, and one
that holds no estate is not opened.

The page is served with a content security policy that allows nothing off-origin, and
the vendored libraries are committed so the app works with no internet at all.
