# Changelog

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
