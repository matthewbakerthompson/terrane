# Changelog

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
