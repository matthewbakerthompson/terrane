# Terrane

Enterprise architecture diagrams from a model. Every diagram is a query over
the model rather than a drawing of it: add a system, and it appears on every
view whose filter it matches. Terrane draws the diagrams in Python, opens the
model in an app in your browser, and carries the preset views (context,
landscape, product, deployment, network, governance, lifecycle, roadmap,
flows), a library of building blocks and parts a product is composed from,
and the provider marks the pictures use. It runs on a bare interpreter, with
nothing else required.

## Install

```bash
pip install terrane
```

Python 3.10 to 3.12. Two extras are optional: `terrane[yaml]` reads the model
with PyYAML instead of the bundled reader, and `terrane[png]` writes PNGs
through `resvg-py` where no Chrome or Edge is on the machine.

## A first drawing

```bash
terrane draw --example > sketch.yaml
terrane draw sketch.yaml
```

A sketch holds a small model and the views it wants; one SVG per view lands
beside it. `--png` adds PNGs and `--mermaid` the Mermaid source.
`terrane draw --views` lists the views a sketch may name, and
`terrane draw --library` the shapes, kits and parts a product can be built
from.

A diagram you already have reads as a sketch by its suffix: Mermaid
(flowcharts, C4 and sequence diagrams), Structurizr DSL, C4-PlantUML,
ArchiMate, draw.io, Visio, and a CSV or Excel inventory of systems.

```bash
terrane draw architecture.drawio
terrane draw inventory.xlsx --pack
```

## An estate of your own, and the app

An estate is a folder, usually a repository of its own, holding your model
and any views of your own. The shipped library and views are read from the
installed package, so nothing of Terrane's is copied into it.

```bash
terrane init my-estate
cd my-estate
terrane app
```

`terrane app` opens the estate at http://127.0.0.1:8020: every diagram, the
records as tables, the library, and the checks. Edits made there are written
back as YAML files that read as if a person wrote them. A first visit to the
sample estate offers a two-minute tour.

`terrane init` pins the Terrane releases the estate is checked with, so
everyone on it draws the same thing, and can name the organization's
governance repository. A colleague joins with `terrane connect <url>`, which
clones the estate and fetches the governance it pins; git signs in, and
Terrane holds no password or token.

## The commands

| Command | What it does |
|---|---|
| `terrane app` | open the estate in the browser |
| `terrane init` | start an estate |
| `terrane draw` | draw one file: a sketch, or a diagram a reader reads |
| `terrane adopt` | write a sketch, or what a reader read, into the estate as its own records |
| `terrane validate` | run the model's quality gates |
| `terrane render` | draw every view into `70_ARTIFACTS/` |
| `terrane pack` | the review pack: a PowerPoint slide per view |
| `terrane export` | the estate as ArchiMate, draw.io, C4-PlantUML, Excel, CSV, JSON or Backstage |
| `terrane diff` | what changed between two revisions, drawn |
| `terrane needs` | what each diagram needs from the records, and how many lack it |

[The command reference](https://github.com/matthewbakerthompson/terrane/blob/main/docs/COMMANDS.md) lists
every command and argument.

## From Python

The same door, for a notebook or a script:

```python
import terrane

pictures = terrane.diagrams({
    "systems": ["SYS-WEB", "SYS-API", "SYS-LEDGER"],
    "interfaces": [
        {"interface_id": "INT-1", "source_system_id": "SYS-WEB", "target_system_id": "SYS-API", "protocol": "HTTPS"},
        {"interface_id": "INT-2", "source_system_id": "SYS-API", "target_system_id": "SYS-LEDGER", "protocol": "MQ"},
    ],
    "views": ["application-landscape"],
})
pictures["application-landscape"]                  # shows itself in a notebook
pictures["application-landscape"].save("landscape.svg")   # or .png
pictures.notes                                     # what was filled in, what was not drawn
pictures.pack("deck.pptx", title="Payments")       # a slide per picture, a cover before them
pictures.pack("deck.pptx", editable=True)          # every diagram as shapes a reviewer can move, lines glued
pictures.drawio("sketch.drawio")                   # a draw.io file, a page per diagram, boxes where the engine put them
pictures.excel("sketch.xlsx")                      # what the sketch, the file read or the estate's pictures show, as a workbook
pictures                                           # a notebook shows every picture, by name
terrane.views()                                        # the shipped views, as records
terrane.presets()                                      # the shapes, kits, parts, landing zones and connection kinds, as data
terrane.presets("path/to/estate")                      # an estate's own library after the shipped one; terrane.views(root) its views
terrane.example("on-a-shape")                          # a sketch to start from; terrane.examples() names them
terrane.diagrams(terrane.on_shape("azure-digital-product", "Rewards Redemption",
                          answers={"account": "azure-cards-prod"}, modules=["async-worker"]))
terrane.diagrams(terrane.from_parts("AWS", "Merchant portal", parts=["web-app-baseline", "async-worker"]))
terrane.diagrams(terrane.part("mobile-channel"))           # one part with what it requires, the parts page's own picture
terrane.connect("SYS-A", "SYS-B", "API call")          # an interface as the connection kind proposes it, for a sketch or terrane.adopt
terrane.made_by(terrane.from_parts("AWS", "Portal", parts=["web-app-baseline"]))  # what the parts make, by id, before drawing
terrane.change("model.archimate", "path/to/repo")      # what it would add, drawn among the estate, faded
terrane.since("path/to/repo", "HEAD~5")                 # what changed since a commit, drawn: added, removed, changed, the rest faded
terrane.since("path/to/repo", "v1", view="application-landscape")   # the same marks on a view of the whole estate
terrane.adopt("model.archimate", "path/to/repo")       # what a reader read, into the estate
terrane.adopt("deck.xlsx", "path/to/repo", correct=True)  # the reviewer's workbook back in: differing cells, in place
terrane.export_archimate("path/to/repo", "estate.xml") # the estate for Archi
terrane.export_drawio("path/to/repo", "estate.drawio")  # every picture view as a draw.io page
terrane.export_plantuml("path/to/repo", "puml/")         # every picture view as C4-PlantUML, the reader takes it back
terrane.export_excel("path/to/repo", "estate.xlsx")      # the estate as one workbook, a sheet per type
pictures["application-landscape"].plantuml         # one picture as C4-PlantUML
```

`terrane.diagrams` takes a sketch as a dict, as YAML text or as a path; the
file of any reader above; or the folder of an estate and the views to draw.
The pictures carry their own faces, so they look the same wherever they are
opened.

## How the diagrams are drawn

A small diagram is laid out by ELK, the same build the app uses, run in a
Chrome or Edge found on the machine, so the picture matches the app's. With
no browser, it is laid out by dagre, and the sheet says so. A whole estate
renders with `terrane render`, and the review pack with `terrane pack`
(`--editable` puts each diagram on as shapes a reviewer can move, and needs
no browser).

## License

Free to use, change and share, at work or at home, for any purpose but one:
offering it, or something built from it, as a product or hosted service that
competes with Terrane, whether for a charge or not. The terms are the
PolyForm Shield License 1.0.0. The package also bundles Cytoscape, dagre and
elkjs, the Geist and Libre Franklin faces, and provider icons, each under
its own license; the texts travel inside the package, listed in
THIRD_PARTY_NOTICES.md.

## Links

- [The repository](https://github.com/matthewbakerthompson/terrane)
- [The method](https://github.com/matthewbakerthompson/terrane/tree/main/00_METHOD), chapter by chapter
- [The changelog](https://github.com/matthewbakerthompson/terrane/blob/main/CHANGELOG.md)
- [Issues](https://github.com/matthewbakerthompson/terrane/issues)
