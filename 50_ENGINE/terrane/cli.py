"""Command line entry point.

    terrane connect [URL]            clone an estate and fetch the governance it pins
    terrane init [FOLDER]            start an estate in a repository of its own, on the installed terrane
    terrane init --sample [FOLDER]   copy the sample estate out of the package, to open and change
    terrane --version
    terrane validate                 quality gates, exit 1 on any error
    terrane render                   Mermaid, SVG and Structurizr output for every view
    terrane export csv|backstage|json
    terrane impact ID                what is affected if this changes
    terrane cmdb drift --export FILE
    terrane new system|product ...
    terrane stats
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from . import cmdb as cmdb_module
from . import exports, impact as impact_module, importer, jsonschema, scaffold, validate
from .archetype import ArchetypeError, landing_providers
from .blocks import LibraryError, load_blocks, load_components, load_patterns
from .modules import load_modules
from .adoption import candidates as shape_candidates, drifts as shape_drifts
from .build_types import load_build_types
from .connections import load_connections
from .answers import ANSWERS_KEY, PATTERNS_KEY
from .draw import Undrawable, drawing_mode, render_sequence_svg, render_svg, render_timeline_svg
from .draw.table import render_table_svg
from .pictures import render_pictures
from .icons import IconMap, web_dir
from .payload import graph_payload
from .render_library import (
    render_connections,
    render_adoption,
    render_blocks,
    render_build_types,
    render_landing_zones,
    render_modules,
    render_patterns,
    render_shapes,
)
from .importer import ImportError_
from .inventory import MappingError
from .library import summary as library_summary
from .loader import PARSER, ModelFileError, read_data_file
from .model import ModelError, load
from .palette import Palette
from .query import View, ViewError, bind, load_views, render_targets, resolve, subject_slug
from .render_mermaid import render as render_mermaid
from .render_mermaid import render_table, render_timeline, render_timeline_markdown
from .render_mermaid import render_markdown
from .render_sequence import all_flows
from .render_sequence import render as render_sequence
from .render_sequence import render_markdown as render_flow_markdown
from .render_structurizr import render_workspace
from .schema import ENTITY_TYPES
from .shipped import HOME, default_root, sample_inventory, shipped_app
from .estate import InitError, init_estate, init_sample, pins as estate_pins, problems as estate_problems, views_of


def _root(args: argparse.Namespace) -> Path:
    """The model to work on: `--root`, else the repository the engine sits
    in, else the current folder, which is where an installed `terrane` runs."""
    return Path(args.root).resolve() if args.root else default_root()


def _load(args: argparse.Namespace):
    root = _root(args)
    model = load(root)
    views = views_of(root)
    # Validate says it as an error; every other command still runs, and says
    # once that what it writes is another release's picture of the estate.
    if getattr(args, "func", None) is not cmd_validate:
        for code, message in estate_problems(root):
            if code == "estate.requires":
                print("warning: " + message, file=sys.stderr)
    return root, model, views


def _select_views(views: Sequence[View], wanted: Optional[Sequence[str]]) -> List[View]:
    if not wanted:
        return list(views)
    known = {v.view_id: v for v in views}
    missing = [w for w in wanted if w not in known]
    if missing:
        raise ViewError(
            "unknown view(s): %s (available: %s)"
            % (", ".join(missing), ", ".join(sorted(known)))
        )
    return [known[w] for w in wanted]


def cmd_validate(args: argparse.Namespace) -> int:
    root, model, views = _load(args)
    report = validate.run(model, views)
    for finding in report.findings:
        if finding.severity == "error" or not args.errors_only:
            print(finding.format())
    print("")
    print(
        "%d entities, %d relationships, %d views"
        % (
            sum(len(v) for v in model.entities.values()),
            sum(len(v) for v in model.relations.values()),
            len(views),
        )
    )
    print("%d error(s), %d warning(s)" % (len(report.errors), len(report.warnings)))
    if args.strict and report.warnings:
        return 1
    return 0 if report.ok else 1


def cmd_render(args: argparse.Namespace) -> int:
    root, model, views = _load(args)
    selected = _select_views(views, args.view)
    palette = Palette(model.config.get("palette"))
    out_dir = Path(args.out) if args.out else root / "70_ARTIFACTS"
    mermaid_dir = out_dir / "mermaid"
    # A run for one format writes that format and nothing else. The docs,
    # the library pages and the index carry a picture line only when the
    # SVG is drawn in the same run, so `--format structurizr` rewrote the
    # committed docs without theirs; those go to a scratch folder now.
    want_docs = args.format == "all"
    docs_dir = out_dir / "docs" if want_docs else Path(tempfile.mkdtemp(prefix="aac-docs-"))
    svg_dir = out_dir / "svg"
    png_dir = out_dir / "png"
    mermaid_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    # The picture the app draws, as SVG, for every view the engine can lay
    # out the way the app does; the marks come from the app's folder and
    # the faces are named, not embedded, so the file is the drawing and
    # nothing else. A PNG is a rasterizer's job, and the engine ships none:
    # `--png` goes through a browser on the machine, or resvg-py where it
    # is installed, and says so where there is neither.
    want_svg = args.format in ("all", "svg")
    web = web_dir(root)
    icons = IconMap(web if web else root / "80_APP" / "web")
    if want_svg:
        svg_dir.mkdir(parents=True, exist_ok=True)
        if web is None:
            print("no marks on the SVG: the icons were found neither beside the estate nor in this terrane; "
                  "reinstalling terrane puts them back")
    rasterize = _rasterizer() if getattr(args, "png", False) else None
    if rasterize:
        png_dir.mkdir(parents=True, exist_ok=True)
    elk = _elk_runner(web if web else root / "80_APP" / "web") if want_svg else None
    # The library's component types, for the category glyph and the
    # technology line on the drawing, and the catalog pages further down.
    components = load_components(root)
    model_name = str(model.config.get("name") or "Architecture Model")
    #: view id -> the SVG's path relative to the index, where one was drawn.
    pictures: Dict[str, str] = {}
    #: view id -> the layout the app gives it instead, in a word.
    left_to_app: Dict[str, str] = {}
    #: the views drawn on the dagre path where the app itself would use ELK.
    stood_in: Set[str] = set()

    graphs = []
    written: List[Path] = []
    # A parameterized view is not one diagram, it is one per subject. The
    # subjects come from `render_for`, which is a query rather than a list
    # somebody has to keep up to date.
    expanded = []
    stale: List[Path] = []
    for view in selected:
        if not view.parameters:
            expanded.append(view)
            continue
        targets = render_targets(model, view)
        bound_ids = set()
        for parameter, value in targets:
            bound = bind(view, {parameter: value}, model)
            bound_id = "%s--%s" % (view.view_id, subject_slug(value))
            bound_ids.add(bound_id)
            expanded.append(bound._replace(view_id=bound_id, parameters=()))
        # A subject that no longer qualifies leaves a diagram behind that
        # nothing regenerates, and CI cannot tell, because an untouched file
        # is not a stale one. A committed diagram nobody regenerates is the
        # exact thing this repository exists to get rid of, so it goes.
        for folder, suffix in ((mermaid_dir, ".mmd"), (docs_dir, ".md"), (svg_dir, ".svg"), (png_dir, ".png")):
            for path in sorted(folder.glob("%s--*%s" % (view.view_id, suffix))):
                if path.stem not in bound_ids:
                    stale.append(path)
        if not targets:
            print(
                "%-34s skipped -- takes %s and render_for selected nothing"
                % (view.view_id, ", ".join(p.name for p in view.parameters))
            )
    for path in stale:
        path.unlink()
    if stale:
        print("%d file(s) removed for subjects that no longer qualify" % len(stale))
    selected = expanded

    for view in selected:
        try:
            graph = resolve(model, view)
        except ViewError as exc:
            # An empty model, or a filter that nothing matches yet, should not
            # stop the other views from rendering.
            print("%-34s skipped -- %s" % (view.view_id, exc))
            continue
        graphs.append(graph)
        if view.kind == "report":
            # A report answers a question with a set. Its honest output is a
            # table, and a graph of it only suggests the lines mean something;
            # the table is drawn as one, on the sheet, so the pack and the
            # Python door have the registers too.
            picture = ""
            if want_svg:
                svg_path = svg_dir / ("%s.svg" % view.view_id)
                svg_path.write_text(render_table_svg(graph, model_name=model_name), encoding="utf-8")
                written.append(svg_path)
                picture = "svg/%s" % svg_path.name
                pictures[view.view_id] = picture
                if rasterize:
                    (png_dir / ("%s.png" % view.view_id)).write_bytes(rasterize(svg_path.read_text(encoding="utf-8")))
            md = docs_dir / ("%s.md" % view.view_id)
            md.write_text(render_table(graph, picture="../" + picture if picture else ""), encoding="utf-8")
            written.append(md)
            stale = mermaid_dir / ("%s.mmd" % view.view_id)
            if stale.exists():
                stale.unlink()
        elif view.kind == "timeline":
            # A bar per dated thing on a calendar of quarters: a Mermaid gantt
            # in the artifacts, a grid in the app, and the same grid drawn
            # as SVG. Time is the one axis a layout must not choose.
            picture = ""
            if want_svg:
                payload = graph_payload(model, view, palette, icons, components, graph=graph)
                svg_path = svg_dir / ("%s.svg" % view.view_id)
                svg_path.write_text(render_timeline_svg(payload, model_name=model_name), encoding="utf-8")
                written.append(svg_path)
                picture = "svg/%s" % svg_path.name
                pictures[view.view_id] = picture
                if rasterize:
                    (png_dir / ("%s.png" % view.view_id)).write_bytes(rasterize(svg_path.read_text(encoding="utf-8")))
            mmd = mermaid_dir / ("%s.mmd" % view.view_id)
            mmd.write_text(render_timeline(graph), encoding="utf-8")
            md = docs_dir / ("%s.md" % view.view_id)
            md.write_text(render_timeline_markdown(graph, picture="../" + picture if picture else ""),
                          encoding="utf-8")
            written.extend([mmd, md])
        else:
            picture = ""
            if want_svg:
                drawn = _draw_svg(graph, view, model, palette, icons, components, svg_dir, model_name, rasterize,
                                  png_dir, elk=elk)
                if isinstance(drawn, Undrawable):
                    left_to_app[view.view_id] = drawn.layout or "another"
                else:
                    path, fallback = drawn
                    written.append(path)
                    picture = "svg/%s" % path.name
                    pictures[view.view_id] = picture
                    if fallback:
                        stood_in.add(view.view_id)
            if "mermaid" in view.renderers or args.format == "mermaid":
                mmd = mermaid_dir / ("%s.mmd" % view.view_id)
                mmd.write_text(render_mermaid(graph, palette, model), encoding="utf-8")
                md = docs_dir / ("%s.md" % view.view_id)
                md.write_text(render_markdown(graph, palette, model, picture="../" + picture if picture else ""),
                              encoding="utf-8")
                written.extend([mmd, md])
        print(
            "%-34s %-8s %3d nodes  %3d edges%s%s"
            % (
                view.view_id,
                view.kind,
                len(graph.nodes),
                len(graph.edges),
                "  svg" if view.view_id in pictures else "",
                "  [%s]" % "; ".join(graph.notes) if graph.notes else "",
            )
        )
    if want_svg:
        print("")
        print("%d view(s) drawn as SVG under svg/%s" % (
            len(pictures), ", %d of them on the dagre path where the app uses ELK" % len(stood_in) if stood_in else ""))
        for view_id, layout in sorted(left_to_app.items()):
            print("%-34s left to the app, which draws it as %s" % (view_id, layout))

    structurizr_graphs = [
        g for g in graphs
        if "structurizr" in g.view.renderers and g.view.kind not in ("report", "timeline")
    ]
    if structurizr_graphs or args.format == "structurizr":
        dsl_dir = out_dir / "structurizr"
        dsl_dir.mkdir(parents=True, exist_ok=True)
        dsl = dsl_dir / "workspace.dsl"
        dsl.write_text(
            render_workspace(model, structurizr_graphs or graphs, palette), encoding="utf-8"
        )
        written.append(dsl)

    if not graphs:
        print("")
        print("No view matched anything. The model is empty or the filters are wrong.")
        print("Populate it with `terrane import csv --from <dir>`, or open it in the app: `terrane app`.")
    # Flows render as sequence diagrams, which answer a question a flowchart
    # cannot: what happens in what order.
    flow_ids = all_flows(model)
    if flow_ids:
        flow_dir = out_dir / "flows"
        flow_dir.mkdir(parents=True, exist_ok=True)
        for flow_id in flow_ids:
            mmd = flow_dir / ("%s.mmd" % flow_id)
            mmd.write_text(render_sequence(model, flow_id), encoding="utf-8")
            picture = ""
            if want_svg:
                # The same flow drawn: the sequence diagram the Mermaid says,
                # as a sheet beside the views'.
                svg_path = svg_dir / ("%s.svg" % flow_id)
                svg_path.write_text(render_sequence_svg(model, flow_id, palette, model_name=model_name),
                                    encoding="utf-8")
                written.append(svg_path)
                picture = "svg/%s" % svg_path.name
                pictures[flow_id] = picture
                if rasterize:
                    (png_dir / ("%s.png" % flow_id)).write_bytes(rasterize(svg_path.read_text(encoding="utf-8")))
            md = docs_dir / ("%s.md" % flow_id)
            md.write_text(render_flow_markdown(model, flow_id, picture="../" + picture if picture else ""),
                          encoding="utf-8")
            written.extend([mmd, md])
        print("")
        print("%d flow(s) rendered as sequence diagrams" % len(flow_ids))

    # The library renders too. The pattern catalog is what a review board
    # reads, and one that lives only in YAML is one nobody reads; rendering it
    # here is also what gives it the adoption column, read off the model.
    blocks = load_blocks(root, components)
    patterns = load_patterns(root, blocks)
    library_dir = out_dir / "library"
    pages_dir = library_dir if want_docs else docs_dir
    library_dir.mkdir(parents=True, exist_ok=True)
    # The parts and the shapes: the modular layer, which lived in the library
    # and the app and nowhere a reader of the artifacts could see it.
    modules = load_modules(root)
    shapes = list(model.archetypes.values())
    types = load_build_types(root)
    # Every shape as the product it would make, every kit assembled on each
    # landing zone, every block as the small diagram it is, and the library
    # as a map, drawn by the same painter a real product gets, so the
    # catalog shows a preset rather than listing its parts.
    presets = None
    if want_svg:
        presets = render_pictures(model, views, shapes, modules, palette, icons, components, blocks,
                                  library_dir / "svg", model_name, root, elk=elk)
        written.extend(presets.written)
    patterns_md = pages_dir / "patterns.md"
    patterns_md.write_text(
        render_patterns(patterns, blocks, components, model, presets), encoding="utf-8"
    )
    blocks_md = pages_dir / "blocks.md"
    blocks_md.write_text(render_blocks(blocks, components, patterns, presets), encoding="utf-8")
    modules_md = pages_dir / "modules.md"
    modules_md.write_text(render_modules(modules, shapes, model, types, presets), encoding="utf-8")
    shapes_md = pages_dir / "shapes.md"
    shapes_md.write_text(render_shapes(shapes, modules, model, presets), encoding="utf-8")
    # The landing zones: what each provider answers for by kind, and the
    # kinds the parts name that it does not -- the page that says where the
    # next onboarding would stop.
    zones = landing_providers(shapes)
    zones_md = pages_dir / "landing-zones.md"
    zones_md.write_text(render_landing_zones(modules, shapes, model), encoding="utf-8")
    # Shapes and the estate: who is on a shape and how far they have moved,
    # and who could be. Pattern adoption's counterpart for the modular layer.
    adoption = (len(shape_drifts(model, shapes, modules)), len(shape_candidates(model, shapes, modules)))
    adoption_md = pages_dir / "adoption.md"
    adoption_md.write_text(render_adoption(modules, shapes, model), encoding="utf-8")
    # The build types: the kinds of thing the organization builds, and which
    # product departs from its standard, read off the model.
    types_md = pages_dir / "build-types.md"
    types_md.write_text(render_build_types(types, modules, shapes, model), encoding="utf-8")
    # The connection kinds, and which interfaces are of each, read off their
    # fields: the library layer that reaches the connections between systems.
    kinds = load_connections(root)
    connections_md = pages_dir / "connections.md"
    connections_md.write_text(render_connections(kinds, patterns, model), encoding="utf-8")
    written.extend([patterns_md, blocks_md, modules_md, shapes_md, zones_md, adoption_md, types_md, connections_md])
    print("")
    print(
        "%d pattern(s), %d block(s), %d part(s), %d shape(s), %d build type(s) and %d landing zone(s) "
        "cataloged under library/; %d product(s) on a shape, %d candidate(s)"
        % (len(patterns), len(blocks), len(modules), len(shapes), len(types), len(zones),
           adoption[0], adoption[1])
    )
    if presets is not None:
        kits_drawn = sum(1 for paths in presets.kits.values() if paths)
        print("%d shape(s), %d kit(s) and %d block(s) pictured under library/svg/%s%s" % (
            len(presets.shapes), kits_drawn, len(presets.blocks),
            ", and the library mapped" if presets.maps else "",
            "; without a picture: %s" % ", ".join(sorted(presets.notes)) if presets.notes else ""))

    # The CMDB drift report is generated output too, and was not regenerated
    # here: it said thirty systems in the model when the model had
    # seventy-four, and CI had no way to tell. The sample export is in the
    # repository; when it is, the report renders with everything else and
    # the staleness check covers it.
    drift_summary = None
    sample = root / "60_SOURCES" / "servicenow" / "sample_cmdb_ci_export.csv"
    if sample.exists():
        sot_file = root / "60_SOURCES" / "servicenow" / "field_sot.yaml"
        drift = cmdb_module.reconcile(
            model,
            cmdb_module.read_ci_export(sample),
            field_sot=cmdb_module.load_field_sot(sot_file) if sot_file.exists() else {},
            export_path="60_SOURCES/servicenow/sample_cmdb_ci_export.csv",
        )
        cmdb_dir = out_dir / "cmdb"
        written.append(cmdb_module.write_drift_markdown(drift, cmdb_dir / "drift_report.md", model))
        written.append(cmdb_module.write_drift_csv(drift, cmdb_dir / "drift.csv"))
        linked = drift.counts.get("LINKED_OK", 0) + drift.counts.get("ATTR_MISMATCH", 0)
        drift_summary = (linked, len(model.all_of("systems")))

    # The organization's libraries, by what each adds and replaces: the
    # catalogs mark each record, and the index says what came from where.
    libraries = library_summary(root, {
        "shape": model.archetypes, "connection kind": kinds, "component type": components,
        "building block": blocks, "pattern": patterns, "part": modules, "build type": types,
    })
    index = (out_dir if want_docs else docs_dir) / "INDEX.md"
    index.write_text(
        _render_index(
            model, graphs, flow_ids, (patterns, blocks, modules, zones, adoption, types, kinds), drift=drift_summary,
            libraries=libraries, pictures=pictures, left_to_app=left_to_app, stood_in=stood_in,
        ),
        encoding="utf-8",
    )
    written.append(index)

    print("")
    kept = [p for p in written if out_dir.resolve() in Path(p).resolve().parents]
    print("%d file(s) written under %s" % (len(kept), out_dir))
    return 0


def _draw_svg(graph, view, model, palette, icons, components, svg_dir: Path, model_name: str, rasterize,
              png_dir: Path, elk=None):
    """The view as the app draws it, written as `svg/<view>.svg` on the
    default sheet, with no date, the faces named and the marks inside; the
    path and whether the app itself would have used ELK, or the
    `Undrawable` that says why it is left to the app. A picture an earlier
    render wrote for a view that no longer draws goes, the way a stale
    subject diagram goes, since an untouched file is not a stale one to CI."""
    svg_path = svg_dir / ("%s.svg" % view.view_id)
    png_path = png_dir / ("%s.png" % view.view_id)
    payload = graph_payload(model, view, palette, icons, components, graph=graph)
    try:
        mode = drawing_mode(payload)
        text = render_svg(payload, icon_loader=icons.read, model_name=model_name, elk=elk)
    except Undrawable as exc:
        for stale in (svg_path, png_path):
            if stale.exists():
                stale.unlink()
        return exc
    svg_path.write_text(text, encoding="utf-8")
    if rasterize:
        png_path.write_bytes(rasterize(text))
    # With ELK at hand the small diagrams are the app's own picture, not
    # the dagre stand-in the index marks.
    return svg_path, mode.fallback and elk is None


def _elk_runner(web):
    """The ELK runner for a command, or None, said either way: the app's
    `elk.bundled.js` in a headless Chrome or Edge (`terrane.draw.elk`), so the
    small diagrams the app hands to ELK are laid out by ELK here too. Opened
    on the first such diagram and closed when the interpreter ends."""
    import atexit

    from .draw.elk import open_runner

    runner = open_runner(web)
    if runner is None:
        print("no browser or no elk.bundled.js: the small diagrams are drawn on the dagre path and the sheet says "
              "dagre-for-elk")
        return None
    atexit.register(runner.close)
    print("ELK through %s for the small diagrams" % runner.means)
    return runner


def _rasterizer():
    """The PNG maker for a command, or None, said either way: a Chrome or an
    Edge on the machine, driven headless, else resvg-py where it is
    installed (`terrane.draw.raster`). The engine runs on a bare interpreter and
    CI holds it to that, so a PNG is the one thing a command asks the
    machine for, and only when asked with `--png`. The sheet is drawn at
    twice its size, the way the app's export is. The browser is opened on
    the first picture and closed when the interpreter ends, which for a
    command is the same moment."""
    import atexit

    from .draw.raster import NoRasterizer, open_rasterizer

    try:
        shoot = open_rasterizer()
    except NoRasterizer as exc:
        print("--png asked for, but %s; the SVGs are written and no PNG is" % exc)
        return None
    atexit.register(shoot.close)
    print("PNG through %s" % shoot.means)
    return shoot


def _counted(counts) -> str:
    """"1 pattern and 2 parts", from (noun, n) pairs."""
    said = ["%d %s%s" % (n, noun, "" if n == 1 else "s") for noun, n in counts if n]
    if not said:
        # A library that adds and replaces nothing -- or, the case that
        # found this, adds two connection kinds and replaces none -- has
        # nothing to say on that side; the caller words the sentence.
        return ""
    return said[0] if len(said) == 1 else ", ".join(said[:-1]) + " and " + said[-1]


def _libraries_paragraph(libraries) -> str:
    """What each of the organization's libraries adds and replaces, after
    the shipped one. Nothing at all while the model names none, so the
    method's own repository renders as it always did."""
    said = []
    for name, counts in libraries:
        adds = _counted((noun, added) for noun, (added, _r) in counts.items())
        replaces = _counted((noun, replaced) for noun, (_a, replaced) in counts.items())
        if adds and replaces:
            what = "adds %s, and replaces %s" % (adds, replaces)
        elif adds or replaces:
            what = ("adds %s" % adds) if adds else ("replaces %s" % replaces)
        else:
            what = "adds and replaces nothing yet"
        said.append("`%s/` %s" % (name, what))
    return (
        "The shipped library is read first and then the organization's own, in the order "
        "`library_paths` names them: %s. A record stands in for one read before it only "
        "where it says `replaces:`, and each catalog marks what came from where."
        % "; ".join(said)
    )


def _render_index(model, graphs, flow_ids=(), library=None, drift=None, libraries=(), pictures=None,
                  left_to_app=None, stood_in=()) -> str:
    pictures = pictures or {}
    left_to_app = left_to_app or {}
    lines = ["# Generated architecture views", ""]
    lines.append(
        "Every file in this folder is produced by `terrane render` from the model in "
        "`10_MODEL/`. Editing them is pointless; the next render overwrites them."
    )
    lines.append("")
    lines.append(
        "Four kinds of thing live here. A **diagram** has a subject and is read "
        "closely. A **map** has no subject and is scanned. A **report** answers a "
        "question with a set, so it is a table, drawn as one. A **timeline** "
        "puts dated things on a calendar of quarters."
    )
    lines.append("")
    if pictures or left_to_app:
        lines.append(
            "A diagram or a map the engine lays out the way the app does is also drawn as the "
            "app draws it, as SVG under `svg/`, the provider's marks inside the file and the faces "
            "named rather than embedded; the **Drawing** column links it, and each view's page "
            "carries it under the Mermaid; a map with no connections is the tiles the app shows. A "
            "drawing the app lays out in its browser, by ELK or organically, is drawn the same way here through a "
            "browser on the machine; where there was none, the column says which layout the picture needed. A "
            "drawing marked \u2020 is laid out by dagre where the app would use ELK: the app's own fallback, not "
            "its first choice."
        )
        lines.append("")
    for kind, heading in (
        ("diagram", "Architecture diagrams"),
        ("map", "Landscape maps"),
        ("report", "Reports"),
        ("timeline", "Timelines"),
    ):
        of_kind = [g for g in graphs if g.view.kind == kind]
        if not of_kind:
            continue
        lines.append("## %s" % heading)
        lines.append("")
        drawn = kind in ("diagram", "map", "timeline", "report") and (pictures or left_to_app)
        lines.append("| View | %sNodes | Edges | Description |" % ("Drawing | " if drawn else ""))
        lines.append("|---|%s---:|---:|---|" % ("---|" if drawn else ""))
        for graph in sorted(of_kind, key=lambda g: g.view.view_id):
            view_id = graph.view.view_id
            if not drawn:
                drawing = ""
            elif view_id in pictures:
                drawing = "[SVG](%s)%s | " % (pictures[view_id], " \u2020" if view_id in stood_in else "")
            else:
                drawing = "%s, app only | " % left_to_app.get(view_id, "not drawn")
            lines.append(
                "| [%s](docs/%s.md) | %s%d | %d | %s |"
                % (
                    graph.view.title,
                    view_id,
                    drawing,
                    len(graph.nodes),
                    len(graph.edges),
                    graph.view.description.replace("\n", " ").strip(),
                )
            )
        lines.append("")
    if flow_ids:
        lines.append("## Flows")
        lines.append("")
        lines.append(
            "Rendered as sequence diagrams: what happens in what order, which is "
            "the question a flowchart cannot answer."
        )
        lines.append("")
        drawn_flows = any(flow_id in pictures for flow_id in flow_ids)
        lines.append("| Flow | %sSteps | Target |" % ("Drawing | " if drawn_flows else ""))
        lines.append("|---|%s---:|---|" % ("---|" if drawn_flows else ""))
        from .render_sequence import steps_for
        for flow_id in flow_ids:
            record = model.get("flows", flow_id) or {}
            drawing = ("[SVG](%s) | " % pictures[flow_id] if flow_id in pictures else "not drawn | ") if drawn_flows else ""
            lines.append(
                "| [%s](docs/%s.md) | %s%d | %s |"
                % (record.get("name") or flow_id, flow_id, drawing, len(steps_for(model, flow_id)),
                   record.get("target_latency") or "")
            )
        lines.append("")
    if library:
        patterns, blocks = library[0], library[1]
        modules = library[2] if len(library) > 2 else {}
        zones = library[3] if len(library) > 3 else ()
        lines.append("## Library")
        lines.append("")
        lines.append(
            "What the estate is built from, and the decisions about how. Generated "
            "from `26_BLOCKS/`, `27_PATTERNS/`, `28_MODULES/`, `20_ARCHETYPES/` and the "
            "services tagged `landing-zone`."
        )
        lines.append("")
        if libraries:
            lines.append(_libraries_paragraph(libraries))
            lines.append("")
        lines.append("| | |")
        lines.append("|---|---|")
        lines.append(
            "| [Patterns](library/patterns.md) | %d. A building block plus the decision, "
            "with which products apply each one |" % len(patterns)
        )
        lines.append(
            "| [Building blocks](library/blocks.md) | %d. The handfuls of components "
            "that arrive together, resolved per provider |" % len(blocks)
        )
        lines.append(
            "| [Parts](library/modules.md) | %d. What a shape is composed from: what each "
            "provides, needs and runs on, and where it is used; every kit drawn, assembled on each "
            "landing zone |" % len(modules)
        )
        lines.append(
            "| [Shapes](library/shapes.md) | %d. A provider, the parts, the slots where it "
            "varies, and which products sit on each; every shape drawn as the product it makes |"
            % len(model.archetypes)
        )
        if zones:
            lines.append(
                "| [Landing zones](library/landing-zones.md) | %d. What each provider answers "
                "for by kind, and the kinds the parts name that it does not |" % len(zones)
            )
        types = library[5] if len(library) > 5 else {}
        if types:
            lines.append(
                "| [Build types](library/build-types.md) | %d. The kinds of thing the organization "
                "builds, the standard parts of each, and the products on each with their "
                "deviations |" % len(types)
            )
        kinds = library[6] if len(library) > 6 else {}
        if kinds:
            lines.append(
                "| [Connection kinds](library/connections.md) | %d. The ways two systems are "
                "connected here, and which interfaces are of each |" % len(kinds)
            )
        adoption = library[4] if len(library) > 4 else None
        if adoption:
            lines.append(
                "| [Shapes and the estate](library/adoption.md) | %d product(s) on a shape "
                "and how far each has moved; %d hand-authored product(s) a shape would "
                "reproduce |" % (adoption[0], adoption[1])
            )
        lines.append("")
    if drift:
        lines.append("## Reconciliation")
        lines.append("")
        lines.append(
            "| [ServiceNow drift report](cmdb/drift_report.md) | %d of %d systems reconciled to a "
            "CI in the sample export; read-only, regenerated with the rest |" % drift
        )
        lines.append("")
    lines.append("## Model contents")
    lines.append("")
    lines.append("| Collection | Count |")
    lines.append("|---|---:|")
    for name, count in sorted(model.counts().items()):
        lines.append("| `%s` | %d |" % (name, count))
    lines.append("")
    return "\n".join(lines)


def cmd_export(args: argparse.Namespace) -> int:
    root, model, views = _load(args)
    out_dir = Path(args.out) if args.out else root / "70_ARTIFACTS" / "export"
    if args.target == "csv":
        written = exports.export_csv(model, out_dir / "csv")
    elif args.target == "backstage":
        written = exports.export_backstage(model, out_dir / "backstage")
    elif args.target == "archimate":
        # The way out to Archi: elements, relationships and every view that
        # is a picture, placed by the engine's own layout.
        from .render_archimate import export_archimate

        web = web_dir(root)
        path, notes = export_archimate(model, views, out_dir / "archimate.xml", Palette(model.config.get("palette")),
                                       IconMap(web) if web else None, load_components(root))
        for note in notes:
            print("note: %s" % note)
        written = [path]
    elif args.target == "drawio":
        # The way out to the whiteboard: every picture view as a page,
        # each box where the engine put it, in the styles the reader takes
        # back to their types.
        from .render_drawio import export_drawio
        from .shipped import shipped_root

        web = web_dir(root) or web_dir(shipped_root()) or shipped_root() / "web"
        path, notes = export_drawio(model, views, out_dir / "estate.drawio", Palette(model.config.get("palette")),
                                    IconMap(web), load_components(root), web)
        for note in notes:
            print("note: %s" % note)
        written = [path]
    elif args.target == "excel":
        # The workbook that gets sent to a person: a sheet per type, the
        # systems first so the spreadsheet reader takes it back.
        from .render_excel import export_excel

        written = [export_excel(model, out_dir / "estate.xlsx")]
    elif args.target == "plantuml":
        # The way out to C4-PlantUML: every picture view as a .puml the
        # reader takes back, the method's colors as element tags.
        from .render_plantuml import export_plantuml

        written, notes = export_plantuml(model, views, out_dir / "plantuml", Palette(model.config.get("palette")))
        for note in notes:
            print("note: %s" % note)
    else:
        written = [exports.export_json(model, out_dir / "model.json")]
    for path in written:
        print(path)
    print("")
    print("%d file(s) written" % len(written))
    return 0


def cmd_cmdb(args: argparse.Namespace) -> int:
    root, model, _views = _load(args)
    export_path = Path(args.export)
    if not export_path.exists():
        print("CI export not found: %s" % export_path, file=sys.stderr)
        return 2
    rows = cmdb_module.read_ci_export(export_path)
    sot_path = Path(args.field_sot) if args.field_sot else root / "60_SOURCES" / "servicenow" / "field_sot.yaml"
    field_sot = cmdb_module.load_field_sot(sot_path)
    result = cmdb_module.reconcile(
        model, rows, field_sot=field_sot, export_path=str(export_path)
    )
    out_dir = Path(args.out) if args.out else root / "70_ARTIFACTS" / "cmdb"
    md = cmdb_module.write_drift_markdown(result, out_dir / "drift_report.md", model)
    csv_path = cmdb_module.write_drift_csv(result, out_dir / "drift.csv")

    print("Read %d CI record(s) from %s" % (len(rows), export_path))
    for category in sorted(result.counts):
        print("  %-16s %d" % (category, result.counts[category]))
    print("")
    print(md)
    print(csv_path)
    print("")
    print("Read-only. Nothing was written to ServiceNow or to the model.")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    root, model, _views = _load(args)
    values = {}
    for pair in args.set or []:
        if "=" not in pair:
            print("--set expects field=value, got %r" % pair, file=sys.stderr)
            return 2
        key, _, value = pair.partition("=")
        values[key.strip()] = value.strip()

    if args.archetype:
        archetype = model.archetypes.get(args.archetype)
        if archetype is None:
            print(
                "unknown archetype %r (available: %s)"
                % (args.archetype, ", ".join(sorted(model.archetypes)) or "none"),
                file=sys.stderr,
            )
            return 2
        if archetype.applies_to != args.entity_type:
            print(
                "archetype %s applies to %s, not %s"
                % (args.archetype, archetype.applies_to, args.entity_type),
                file=sys.stderr,
            )
            return 2
        content = scaffold.scaffold_instance(archetype, args.id, values)
    else:
        content = scaffold.scaffold_entity(args.entity_type, args.id, values, model)

    path = scaffold.target_path(root, args.entity_type, args.id)
    if path.exists() and not args.force:
        print("%s already exists; pass --force to overwrite" % path, file=sys.stderr)
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(path)
    print("")
    print("Next: fill in the blanks, then run `terrane validate` and `terrane render`.")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    root, model, _views = _load(args)
    outcome = importer.import_csv(
        root,
        Path(args.source),
        model,
        overwrite=args.overwrite,
        only=args.only,
        mapping=Path(args.map) if args.map else None,
    )
    for name, count in sorted(outcome.imported.items()):
        print("  %-32s %d" % (name, count))

    def listed(header: str, lines: List[str]) -> None:
        print("")
        print(header)
        for line in lines[:20]:
            print("  %s" % line)
        if len(lines) > 20:
            print("  ... and %d more" % (len(lines) - 20))

    if outcome.held:
        listed("Held back; nothing of these rows is written:", outcome.held)
        print("")
        print("Say what each is in the mapping and run it again; nothing already written is written twice.")
    if outcome.conflicts:
        listed("%d record(s) left alone:" % len(outcome.conflicts), outcome.conflicts)
        if any("already in the model" in line for line in outcome.conflicts):
            print("")
            print("Pass --overwrite to replace a record already in the model.")
    if outcome.skipped:
        listed("Left out:", outcome.skipped)
    print("")
    print("%d file(s) written under %s" % (len(outcome.written), root / "10_MODEL"))
    if outcome.written:
        print("Next: `terrane validate`, then `terrane render`.")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """What changed between two revisions, in the model's own terms."""
    from . import diff as diff_module

    root = _root(args)
    if args.picture:
        # The change drawn: added in full, removed dashed, changed with a
        # heavy border, the rest faded; with --view, on that view.
        from .diff_picture import changes_since

        try:
            drawing = changes_since(root, args.since, args.until, view_id=args.view, date=args.date or "")
        except diff_module.DiffError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
        target = Path(args.picture)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() == ".png":
            from .draw.raster import NoRasterizer, open_rasterizer

            try:
                with open_rasterizer() as shoot:
                    target.write_bytes(shoot(drawing.svg))
            except NoRasterizer as exc:
                print("error: a PNG needs a browser or resvg-py, and %s" % exc, file=sys.stderr)
                return 2
        else:
            target.write_text(drawing.svg, encoding="utf-8")
        print("%s: %s" % (target, drawing.title))
        if not args.out:
            return 0
    try:
        result = diff_module.between(root, args.since, args.until)
    except diff_module.DiffError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if args.excel:
        # The change as the workbook a board is sent: a sheet per kind of change.
        from .render_excel import export_changes

        written = export_changes(result, Path(args.excel))
        print("%s: what changed from %s to %s" % (written, result.since, result.until))
        if not args.out and not args.picture:
            return 0
    text = diff_module.format_markdown(result)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print("written to %s" % args.out)
    else:
        # The page has arrows and dashes in it, and a Windows console may
        # not: say it in UTF-8 rather than fail on the first "→".
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
        print(text, end="")
    return 0


def cmd_needs(args: argparse.Namespace) -> int:
    """What each diagram needs from the records, and how many records lack
    it: the fields its query, boxes, lines and shade read (terrane/needs.py)."""
    from . import needs as needs_module

    root, model, views = _load(args)
    name = (model.config or {}).get("name") or root.name
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if args.view:
        known = {v.view_id: v for v in views}
        view = known.get(args.view)
        if view is None:
            print("error: no view %r here" % args.view, file=sys.stderr)
            return 2
        subject = args.subject or ""
        if view.parameters:
            supplied = {view.parameters[0].name: subject} if subject else dict(render_targets(model, view))
            subject = subject or next(iter(supplied.values()), "")
            try:
                view = bind(view, supplied, model)
            except ViewError as exc:
                print("error: %s" % exc, file=sys.stderr)
                return 2
        result = needs_module.needs_of(model, view, subject=subject)
        print("%s: %s, %d drawn%s%s" % (result.title, result.state, result.drawn,
                                         ", %d more past limits.max_nodes" % result.cut if result.cut else "",
                                         ", %d left off for want of a field" % len(result.kept_off)
                                         if result.kept_off else ""))
        if result.problem:
            print("  " + result.problem)
        for need in result.needs:
            # What lacking it does here, by the strongest thing the view does with it.
            said = next((needs_module.ROLE_WORDS[r] for r in needs_module.ROLES if dict(need.by_role).get(r)), "")
            print("  %-36s %-22s %s" % (
                "%s.%s" % (need.type, need.field), ", ".join(need.roles),
                "none of the type here" if not need.asked else "%d of %d lack it%s" % (
                    len(need.lacking), need.asked, " (%s)" % said if said else "")))
        return 0
    results = needs_module.estate_needs(model, views)
    count = needs_module.states(results)
    print("%s: %d views. %d draw in full, %d thin, %d with nothing to draw, %d drawn for one thing at a time."
          % (name, len(results), count["full"], count["thin"], count["empty"], count["subject"]))
    listed = needs_module.by_field(model, results, views)
    sections = (
        ("Fields to fill", [n for n in listed if n.kind in ("field", "tag") and n.lacking]),
        ("Kinds of record the estate has none of", []),
        ("Lines", [n for n in listed if n.kind == "relation" and n.lacking]),
    )
    missing: Dict[str, List[str]] = {}
    for need in listed:
        if not need.asked and not model.all_of(need.type):
            for view_id, _title, _roles, _n in need.views:
                if view_id not in missing.setdefault(need.type, []):
                    missing[need.type].append(view_id)
    for title, rows in sections:
        print("")
        print(title)
        if title.startswith("Kinds"):
            for type_name, view_ids in sorted(missing.items(), key=lambda kv: (-len(kv[1]), kv[0])):
                print("  %-36s %s" % (type_name, ", ".join(view_ids)))
            if not missing:
                print("  none")
            continue
        for need in rows:
            print("  %-36s %5d of %-5d %s" % ("%s.%s" % (need.type, need.field), len(need.lacking), need.asked,
                                              ", ".join(v[0] for v in need.views)))
        if not rows:
            print("  none")
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    _root, model, _views = _load(args)
    try:
        result = impact_module.analyze(
            model, args.id, max_distance=args.depth, include_types=args.only
        )
    except KeyError as exc:
        print("error: %s" % exc.args[0], file=sys.stderr)
        return 2
    print(impact_module.format_text(result))
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    root = _root(args)
    out_dir = Path(args.out) if args.out else root / "40_SCHEMAS"
    written = jsonschema.write_all(out_dir)
    for path in written:
        print(path)
    print("")
    print("%d schema(s) written. Point your editor at them for completion." % len(written))
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    """Everything CI's freshness check regenerates, in the order it runs
    it, and the test seed after: render (the Mermaid, the SVG and the
    Structurizr workspace), schema, the seven exports, then the CSVs copied
    into 90_EXAMPLE/csv, relations included, where that folder exists. One
    command, so a round cannot forget one of the nine;
    a round that ran render and the CSV export alone failed CI on the
    Backstage catalog and the JSON."""
    root_args = ["--root", args.root] if args.root else []
    for step in (["render"], ["schema"], ["export", "csv"], ["export", "backstage"], ["export", "json"],
                 ["export", "archimate"], ["export", "drawio"], ["export", "plantuml"], ["export", "excel"]):
        print("== terrane %s" % " ".join(step))
        code = main(root_args + step)
        if code:
            return code
    root = _root(args)
    src = root / "70_ARTIFACTS" / "export" / "csv"
    dst = root / "90_EXAMPLE" / "csv"
    if args.no_seed or not dst.is_dir():
        print("== seed: left alone%s" % ("" if args.no_seed else " (no 90_EXAMPLE/csv here)"))
        return 0
    if not is_sample_estate(root):
        # The engine's tests are seeded from the sample, whatever the model
        # holds; an organization's first refresh would otherwise make its own
        # estate the fixture, and every test that names a sample id would fail.
        print("== seed: left alone (this model is not the sample estate; the engine's tests keep theirs)")
        return 0
    copied = 0
    for path in sorted(src.glob("*.csv")):
        shutil.copy2(path, dst / path.name)
        copied += 1
    (dst / "relations").mkdir(exist_ok=True)
    for path in sorted((src / "relations").glob("*.csv")):
        shutil.copy2(path, dst / "relations" / path.name)
        copied += 1
    print("== seed: %d CSV(s) copied into %s" % (copied, dst))
    return 0


def is_sample_estate(root: Path) -> bool:
    """Whether 10_MODEL is the sample estate the repository ships with, as
    `model.yaml` says. `terrane clear` takes the line out with the estate."""
    path = Path(root) / "10_MODEL" / "model.yaml"
    try:
        data = read_data_file(path) if path.exists() else {}
    except ModelFileError:
        return False
    return bool(isinstance(data, dict) and data.get("sample_estate"))


def cmd_draw(args: argparse.Namespace) -> int:
    """One file, drawn: a sketch holding a small model and the views it
    wants, laid out as a repository in a scratch folder and drawn by the
    same code as the estate (`terrane.quick`). `--example` prints the sketch
    beside the engine to start from."""
    from .mermaid_import import ReadError
    from .pack import PackError
    from .quick import (QuickError, draw_sketch, example_text, shipped_library_text, shipped_views_text,
                        sketch_from_archimate_file, sketch_from_drawio_file, sketch_from_inventory_file,
                        sketch_from_mermaid_file, sketch_from_plantuml_file, sketch_from_structurizr_file,
                        sketch_from_visio_file)

    if args.example:
        try:
            print(example_text(args.example), end="")
        except QuickError as exc:
            print("terrane draw: %s" % exc)
            return 1
        return 0
    if args.views:
        # With --root, the estate's own views and library, after the shipped ones.
        print(shipped_views_text(Path(args.root).resolve() if args.root else None), end="")
        return 0
    if args.library:
        print(shipped_library_text(Path(args.root).resolve() if args.root else None), end="")
        return 0
    if not args.file:
        print("terrane draw: a sketch file to draw, --example for one to start from, --views for the shipped views, "
              "--library for the shapes, kits, parts and connection kinds")
        return 2
    if (args.from_mermaid or args.from_structurizr or args.from_archimate or args.from_plantuml or args.from_drawio
            or args.from_inventory or args.from_visio):
        # A diagram someone already has arrives as a sketch first, so the
        # person has a model to correct and keep; the drawing is the sketch's.
        reader = (sketch_from_archimate_file if args.from_archimate
                  else sketch_from_plantuml_file if args.from_plantuml
                  else sketch_from_drawio_file if args.from_drawio
                  else sketch_from_inventory_file if args.from_inventory
                  else sketch_from_visio_file if args.from_visio
                  else sketch_from_structurizr_file if args.from_structurizr else sketch_from_mermaid_file)
        try:
            sketch, notes = reader(Path(args.file), Path(args.sketch) if args.sketch else None)
        except ReadError as exc:
            print("terrane draw: %s" % exc)
            return 1
        print(sketch)
        for note in notes:
            print("note: %s" % note)
        args.file = str(sketch)
    rasterize = _rasterizer() if args.png else None
    pack = None
    if args.pack is not None:
        pack = Path(args.pack) if args.pack else (Path(args.out) if args.out else Path(args.file).parent) / (
            Path(args.file).stem + ".pptx")
    try:
        written, notes = draw_sketch(Path(args.file), Path(args.out) if args.out else None, mermaid=args.mermaid,
                                     rasterize=rasterize, date=args.date or "", pack=pack, editable=args.editable,
                                     drawio=args.drawio, plantuml=args.plantuml, excel=args.excel)
    except (QuickError, ReadError) as exc:
        print("terrane draw: %s" % exc)
        return 1
    except PackError as exc:
        print("terrane draw: the deck needs a picture, and %s" % exc)
        return 1
    for path in written:
        print(path)
    for note in notes:
        print("note: %s" % note)
    print("%d file(s) drawn from %s" % (len(written), args.file))
    return 0 if written else 1


def cmd_pack(args: argparse.Namespace) -> int:
    """The review pack as a deck: a cover with the model's numbers and what
    validate says, a contents page, one slide per view with its picture.
    Node, puppeteer and pptxgenjs did this against the running app; the
    engine does it from its own drawings, so the Pages workflow and a
    laptop with nothing installed get the same file."""
    from .pack import PackError, build_pack

    root = _root(args)
    out = Path(args.out) if args.out else root / "70_ARTIFACTS" / "review-pack.pptx"
    try:
        path, slides = build_pack(root, out, args.view or (), date=args.date or "", all_rows=args.all_rows,
                                  editable=args.editable, since=args.since,
                                  excel=out.with_suffix(".xlsx") if args.excel else None)
    except PackError as exc:
        print("terrane pack: %s" % exc)
        return 1
    print("%s: %d slides" % (path, slides))
    return 0


def cmd_adopt(args: argparse.Namespace) -> int:
    """A sketch, or what a reader read, written into this repository as
    its own records (`terrane.join`): the point of reading a diagram was to
    arrive at a model, and this is where it arrives."""
    from .join import AdoptError, change_picture, describe, join_estate
    from .mermaid_import import ReadError
    from .quick import QuickError, read_any

    root = _root(args)
    path = Path(args.file)
    try:
        doc, notes = read_any(path, root)
        picture = None
        if args.picture:
            # The change against what is there, before anything is written.
            picture = change_picture(doc, root, owner=args.owner, source_name=path.name, correct=args.correct)
        result = join_estate(doc, root, owner=args.owner, source_name=path.name, dry_run=args.dry_run,
                             correct=args.correct)
    except (ReadError, QuickError, AdoptError) as exc:
        print("terrane adopt: %s" % exc)
        return 1
    for note in notes + result.notes:
        print("note: %s" % note)
    if picture is not None:
        target = Path(args.picture)
        if target.suffix.lower() == ".png":
            from .draw.raster import NoRasterizer, open_rasterizer

            try:
                with open_rasterizer() as shoot:
                    target.write_bytes(shoot(picture.svg))
            except NoRasterizer as exc:
                print("terrane adopt: the picture needs a PNG, and %s" % exc)
                return 1
        else:
            picture.save(target)
        print("%s: what %s adds, drawn against what is there" % (target, path.name))
    for line in describe(result, args.dry_run):
        print(line)
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    """Take the sample estate out, for an organization starting its own.

    The library, the views, the method and the engine stay. What goes is every
    record under 10_MODEL but the model's own settings, and the line in
    model.yaml that says this model is the sample -- which `refresh` reads
    before copying the export into the engine's test seed, and the spelling
    test reads before checking the model's prose. `--keep` names entity types
    to leave in place, the org units or the capability map as a starting
    shape to correct; `relations` keeps the relation files. Nothing is
    removed without `--yes`; without it the command says what it would do.
    """
    root = _root(args)
    model_dir = root / "10_MODEL"
    keep = set(args.keep or [])
    unknown = sorted(k for k in keep if k not in ENTITY_TYPES and k != "relations")
    if unknown:
        print("error: not an entity type: %s" % ", ".join(unknown), file=sys.stderr)
        return 2
    folders = sorted({ENTITY_TYPES[t].folder for t in ENTITY_TYPES if t not in keep}
                     | ({"relations"} if "relations" not in keep else set()))
    plan = []
    for folder in folders:
        base = model_dir / folder
        files = sorted(p for p in base.rglob("*") if p.is_file()) if base.is_dir() else []
        if files:
            plan.append((folder, files))
    total = sum(len(files) for _folder, files in plan)
    sample = is_sample_estate(root)
    config = model_dir / "model.yaml"
    # What the estate answered the library and how it adopted the patterns
    # name its own records, so they go with them: left behind, the next
    # estate's first product would land its private egress on an org unit
    # that is not there (terrane/answers.py).
    settings = dict(read_data_file(config) or {}) if config.exists() else {}
    answered = [key for key in (ANSWERS_KEY, PATTERNS_KEY) if settings.get(key)]
    if not args.yes:
        print("This would remove %d file(s) from %s:" % (total, model_dir))
        for folder, files in plan:
            print("  %-30s %d" % (folder, len(files)))
        if keep:
            print("and keep %s." % ", ".join(sorted(keep)))
        if sample:
            print("model.yaml would stop saying this is the sample estate.")
        if answered:
            print("model.yaml would drop %s, which name the estate's records."
                  % " and ".join("`%s`" % key for key in answered))
        print("")
        print("Nothing has been changed. Run it again with --yes to do it.")
        return 0
    for _folder, files in plan:
        for path in files:
            path.unlink()
    if sample or answered:
        from . import records

        before = config.read_text(encoding="utf-8-sig")
        data = dict(read_data_file(config))
        data.pop("sample_estate", None)
        for key in answered:
            data.pop(key, None)
        config.write_text(records.rewrite(before, data), encoding="utf-8", newline="\n")
    print("Removed %d file(s) from %s%s." % (
        total, model_dir, "; kept %s" % ", ".join(sorted(keep)) if keep else ""))
    print("")
    # Run from 50_ENGINE as often as from the root, so a folder of the
    # repository's named here was the wrong path half the time, and no
    # path at all once installed: the columns are said, not pointed at.
    print("Next:")
    print("  terrane adopt <a spreadsheet>                (an inventory as exported, read by its column names)")
    print("  terrane import csv --from <a folder>         (metamodel v2 CSVs, as terrane export csv writes them)")
    print("  terrane validate                             (warnings are the list of what the inventory lacks)")
    print("  terrane refresh                              (the drawings, the schemas and the exports)")
    print("")
    print("The rest of the first week: %s/blob/main/00_METHOD/AAC-15_ADOPTING.md" % HOME)
    return 0


def cmd_connect(args: argparse.Namespace) -> int:
    """Clone an estate's repository and fetch the governance it pins, at the
    pinned revision, into `.terrane/governance/`; in a clone made some other
    way, fetch the governance alone. git signs in, not terrane."""
    from .workspace import WorkspaceError, connect, governance_pin

    here = Path(args.root).resolve() if args.root else None
    try:
        done = connect(args.url or "", into=Path(args.into).resolve() if args.into else None, here=here)
    except WorkspaceError as exc:
        print("terrane connect: %s" % exc, file=sys.stderr)
        return 2
    print("%s %s" % ("cloned " if done.cloned else "estate ", done.root))
    if done.governance is not None:
        print("governance %s at %s (%s), read-only in %s" % (
            governance_pin(done.root)["repository"], done.governance_ref, done.governance_commit[:10],
            done.governance.relative_to(done.root).as_posix()))
    for note in done.notes:
        print("note: " + note)
    for code, message in estate_problems(done.root):
        if code == "estate.requires":
            print("warning: " + message, file=sys.stderr)
    print("")
    print("Next: work in %s; terrane validate is the gate." % done.root)
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Start an estate in a repository of its own: the settings that read the
    shipped library and views from the installed terrane and pin its release,
    a README, a .gitignore that keeps generated pictures out, and nothing of
    terrane's own. A folder holding an estate is refused, not mixed into.
    With `--sample`, the sample estate instead, copied out of the package."""
    from . import __version__

    folder = Path(args.folder).resolve()
    if args.sample and (args.name or args.governance or args.governance_ref):
        # The sample is a card issuer's, named and governed as it ships.
        print("terrane init: --sample copies the sample estate as it is; --name and --governance "
              "are for an estate of your own", file=sys.stderr)
        return 2
    try:
        if args.sample:
            written, kept = init_sample(folder, __version__, requirement=args.requires or "")
        else:
            written, kept = init_estate(folder, args.name or folder.name, __version__,
                                        repository=args.governance or "", ref=args.governance_ref or "",
                                        requirement=args.requires or "")
    except InitError as exc:
        print("terrane init: %s" % exc, file=sys.stderr)
        return 2
    for path in written:
        if path.is_dir():
            print("wrote  %s/ (%d files)" % (path.relative_to(folder).as_posix(),
                                            sum(1 for p in path.rglob("*") if p.is_file())))
        else:
            print("wrote  %s" % path.relative_to(folder).as_posix())
    for path in kept:
        print("kept   %s (already there)" % path.relative_to(folder).as_posix())
    model = load(folder)
    report = validate.run(model, views_of(folder))
    errors = sum(1 for f in report.findings if f.severity == "error")
    print("")
    if args.sample:
        print("%s: the sample estate on terrane %s, %d records, %d views, %d error(s)"
              % (folder.name, __version__, sum(len(v) for v in model.entities.values()), len(views_of(folder)),
                 errors))
        # Typed as given, so the line runs from where the person is; the
        # option goes before the command, which is where argparse reads it.
        print("Open it in the browser, where a first visit offers a two-minute tour:")
        print("  terrane%s app" % ("" if folder == Path.cwd().resolve() else " --root %s" % _shell_word(args.folder)))
        print("An estate of your own starts empty, with terrane init.")
        return 1 if errors else 0
    print("%s: an empty estate on terrane %s, %d views, %d error(s)"
          % (folder.name, __version__, len(views_of(folder)), errors))
    print("Next: add records (terrane new system SYS-..., terrane import csv, terrane adopt FILE),")
    print("then terrane validate and terrane render, from inside the folder or with --root;")
    print("terrane app opens it in the browser. A spreadsheet to try terrane adopt on:")
    print("  %s" % sample_inventory())
    return 1 if errors else 0


def _shell_word(text: str) -> str:
    return '"%s"' % text if any(c.isspace() for c in text) else text


def cmd_stats(args: argparse.Namespace) -> int:
    root, model, views = _load(args)
    print("root:   %s" % root)
    print("parser: %s" % PARSER)
    # What the estate is read with, when it says: the people on one estate
    # compare these before they compare anything else.
    for label, value in estate_pins(root).items():
        print("%s: %s" % (label, value))
    print("")
    for name, count in sorted(model.counts().items()):
        print("  %-32s %d" % (name, count))
    print("")
    print("archetypes:")
    for archetype_id, archetype in sorted(model.archetypes.items()):
        provided = sum(len(v) for v in archetype.provides.values())
        instances = [
            r
            for r in model.all_of(archetype.applies_to)
            if r.get("archetype") == archetype_id
        ]
        print(
            "  %-28s provides %2d entities, %d instance(s)"
            % (archetype_id, provided, len(instances))
        )
    print("")
    print("views:")
    for view in views:
        print("  %-32s %s" % (view.view_id, view.title))
    components = load_components(root)
    blocks = load_blocks(root, components)
    patterns = load_patterns(root, blocks)
    print("")
    modules = load_modules(root)
    print(
        "library: %d component type(s), %d block(s), %d pattern(s), %d part(s), %d connection kind(s)"
        % (len(components), len(blocks), len(patterns), len(modules), len(load_connections(root)))
    )
    libraries = library_summary(root, {
        "shape": model.archetypes, "connection kind": load_connections(root),
        "component type": components, "building block": blocks, "pattern": patterns,
        "part": modules, "build type": load_build_types(root),
    })
    if libraries:
        print(_libraries_paragraph(libraries).replace("`", ""))
    return 0


def cmd_app(args: argparse.Namespace) -> int:
    """The app on an estate, in the browser: the repository's server in a
    clone, the copy inside the package once installed. It reads and writes
    the estate `--root` names, else the one the command is run in (in a
    clone, the sample). The browser opens once the server answers, so a
    model that does not load opens no empty page."""
    import importlib.util
    import socket
    import threading
    import time
    import webbrowser

    server_file = shipped_app()
    if server_file is None:
        print("error: this terrane has no app in it; install it with pip (pip install terrane)", file=sys.stderr)
        return 1
    root = _root(args)
    if not (root / "10_MODEL").is_dir():
        print("error: %s holds no estate (no 10_MODEL folder). Start one here with `terrane init`, copy "
              "the sample here with `terrane init --sample`, or name one with --root." % root, file=sys.stderr)
        return 1
    spec = importlib.util.spec_from_file_location("terrane_app_server", server_file)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    url = "http://%s:%d" % (args.host, args.port)

    def open_when_up() -> None:
        for _ in range(100):
            try:
                with socket.create_connection((args.host, args.port), timeout=0.2):
                    webbrowser.open(url)
                    return
            except OSError:
                time.sleep(0.1)

    if not args.no_browser:
        threading.Thread(target=open_when_up, daemon=True).start()
    return server.main(["--root", str(root), "--port", str(args.port), "--host", args.host])


def build_parser() -> argparse.ArgumentParser:
    from . import __version__

    # `terrane` however it was started: run as `python -m terrane`, the
    # usage line would otherwise name `__main__.py`.
    parser = argparse.ArgumentParser(
        prog="terrane", description="Architecture as code: model in, diagrams out."
    )
    parser.add_argument("--root", help="the estate to work on (default: the current folder; in a clone of the repository, the sample estate)")
    # Until 1.1.0 `terrane --version` printed the usage: it was no option,
    # and argparse said the command was missing.
    parser.add_argument("--version", action="version", version="terrane %s" % __version__,
                        help="print the version and stop")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="run the model quality gates")
    p_validate.add_argument("--strict", action="store_true", help="treat warnings as failures")
    p_validate.add_argument("--errors-only", action="store_true", help="suppress warnings")
    p_validate.set_defaults(func=cmd_validate)

    p_render = sub.add_parser("render", help="generate diagrams from the views")
    p_render.add_argument("--view", action="append", help="render only this view id")
    p_render.add_argument("--format", choices=("all", "mermaid", "structurizr", "svg"), default="all",
                          help="all writes everything under 70_ARTIFACTS; one format writes that format alone, the docs, "
                               "the library pages and the index untouched")
    p_render.add_argument("--png", action="store_true",
                          help="also rasterize each SVG into png/, through a Chrome or Edge on the machine or "
                               "resvg-py where it is installed")
    p_render.add_argument("--out", help="output directory (default 70_ARTIFACTS)")
    p_render.set_defaults(func=cmd_render)

    p_export = sub.add_parser("export", help="export the model to another format")
    p_export.add_argument("target", choices=("csv", "backstage", "json", "archimate", "drawio", "plantuml", "excel"))
    p_export.add_argument("--out", help="output directory")
    p_export.set_defaults(func=cmd_export)

    p_cmdb = sub.add_parser("cmdb", help="ServiceNow CMDB reconciliation")
    cmdb_sub = p_cmdb.add_subparsers(dest="cmdb_command", required=True)
    p_drift = cmdb_sub.add_parser("drift", help="compare the model to a CI export")
    p_drift.add_argument("--export", required=True, help="path to a cmdb_ci CSV export")
    p_drift.add_argument("--field-sot", help="path to field_sot.yaml")
    p_drift.add_argument("--out", help="output directory")
    p_drift.set_defaults(func=cmd_cmdb)

    p_connect = sub.add_parser(
        "connect", help="clone an estate's repository and fetch the governance it pins; in a clone, the governance alone")
    p_connect.add_argument("url", nargs="?", help="the estate's repository, as git clones it (default: the clone you are in)")
    p_connect.add_argument("--into", metavar="FOLDER", help="where to clone it (default: a folder named as git names it)")
    p_connect.set_defaults(func=cmd_connect)

    p_init = sub.add_parser("init", help="start an estate in a repository of its own, read with the installed terrane")
    p_init.add_argument("folder", nargs="?", default=".", help="where to start it (default: the current folder)")
    p_init.add_argument("--name", help="the estate's name (default: the folder's)")
    p_init.add_argument("--governance", metavar="URL", help="the organization's governance repository")
    p_init.add_argument("--governance-ref", metavar="REF", help="the revision of it the estate is checked against")
    p_init.add_argument("--requires", metavar="RANGE",
                        help="the terrane versions the estate is checked with (default: this minor release)")
    p_init.add_argument("--sample", action="store_true",
                        help="copy the sample estate, a card issuer, out of the package into the folder, "
                             "to open in the app and change")
    p_init.set_defaults(func=cmd_init)

    p_app = sub.add_parser("app", help="open the app on an estate: its diagrams, its records and the library, "
                                       "in the browser, edited in place")
    p_app.add_argument("--port", type=int, default=8020, help="the port it listens on (default: 8020)")
    p_app.add_argument("--host", default="127.0.0.1",
                       help="the address it listens on (default: this machine only; the app has no sign-in)")
    p_app.add_argument("--no-browser", action="store_true", help="start it without opening a browser")
    p_app.set_defaults(func=cmd_app)

    p_new = sub.add_parser("new", help="scaffold a new model entry")
    p_new.add_argument("entity_type", choices=sorted(ENTITY_TYPES))
    p_new.add_argument("id", help="the identifier, e.g. SYS-CARDS-WEB")
    p_new.add_argument("--archetype", help="build this instance from an archetype")
    p_new.add_argument("--set", action="append", help="field=value, repeatable")
    p_new.add_argument("--force", action="store_true", help="overwrite an existing file")
    p_new.set_defaults(func=cmd_new)

    p_import = sub.add_parser("import", help="import an existing inventory")
    import_sub = p_import.add_subparsers(dest="import_command", required=True)
    p_import_csv = import_sub.add_parser("csv", help="import metamodel v2 CSVs, or an inventory through --map")
    p_import_csv.add_argument("--from", dest="source", required=True, help="directory of CSVs")
    p_import_csv.add_argument(
        "--overwrite", action="store_true", help="replace records already in the model"
    )
    p_import_csv.add_argument(
        "--only", action="append", help="import only this entity type, repeatable"
    )
    p_import_csv.add_argument(
        "--map", help="a mapping from the inventory's columns, values and codes to the model's (AAC-15)"
    )
    p_import_csv.set_defaults(func=cmd_import)

    p_diff = sub.add_parser("diff", help="what changed in the architecture between two revisions")
    p_diff.add_argument("since", help="a git revision, e.g. HEAD~5 or a tag")
    p_diff.add_argument("until", nargs="?", help="a later revision (default: the working tree)")
    p_diff.add_argument("--out", help="write the Markdown here instead of printing it")
    p_diff.add_argument("--picture", metavar="PATH",
                        help="draw the change: what was added in full, what was removed dashed in red, what changed "
                             "with a heavy border or a heavy line, and what is there unchanged one hop away, faded; "
                             "an SVG, or a "
                             "PNG by its suffix; the page is printed only with --out")
    p_diff.add_argument("--view", metavar="VIEW_ID",
                        help="with --picture: put the marks on this view of the whole estate (application-landscape, "
                             "system-context) instead of the change-scoped drawing")
    p_diff.add_argument("--date", help="with --picture: the date on the sheet; none by default")
    p_diff.add_argument("--excel", metavar="PATH",
                        help="write the change as a workbook: what was added, removed and changed field by field, the "
                             "relation rows, the views, the shapes and the parts, a sheet each")
    p_diff.set_defaults(func=cmd_diff)

    p_needs = sub.add_parser("needs", help="what each diagram needs from the records, and how many lack it")
    p_needs.add_argument("view", nargs="?", help="one view; every view when left out")
    p_needs.add_argument("--subject", help="the system, product or other subject a subject view is drawn for")
    p_needs.set_defaults(func=cmd_needs)

    p_impact = sub.add_parser("impact", help="what is affected if this changes")
    p_impact.add_argument("id", help="entity id, e.g. SYS-CORE-LEDGER")
    p_impact.add_argument("--depth", type=int, default=3, help="how many hops out (default 3)")
    p_impact.add_argument(
        "--only", action="append", help="report only this entity type, repeatable"
    )
    p_impact.set_defaults(func=cmd_impact)

    p_schema = sub.add_parser("schema", help="regenerate the JSON Schemas")
    p_schema.add_argument("--out", help="output directory (default 40_SCHEMAS)")
    p_schema.set_defaults(func=cmd_schema)

    p_stats = sub.add_parser("stats", help="what the model currently holds")
    p_stats.set_defaults(func=cmd_stats)

    p_clear = sub.add_parser("clear", help="take the sample estate out, keeping the library and the views")
    p_clear.add_argument("--yes", action="store_true", help="do it; without this it only says what it would do")
    p_clear.add_argument("--keep", nargs="*", metavar="TYPE",
                         help="entity types to leave in place, or `relations`")
    p_clear.set_defaults(func=cmd_clear)

    p_draw = sub.add_parser("draw", help="draw one file: a sketch, or a diagram a reader reads, no repository")
    p_draw.add_argument("file", nargs="?", help="the sketch, a YAML file (see --example), or an ArchiMate, "
                                                "Structurizr, C4-PlantUML, draw.io, Visio, spreadsheet, Mermaid or "
                                                "Markdown file, read by its suffix")
    p_draw.add_argument("--out", help="where the pictures go; beside the file by default")
    p_draw.add_argument("--png", action="store_true",
                        help="a PNG beside each SVG, through a Chrome or Edge on the machine or resvg-py where installed")
    p_draw.add_argument("--mermaid", action="store_true", help="the Mermaid beside each SVG as well")
    p_draw.add_argument("--pack", nargs="?", const="", metavar="DECK",
                        help="the pictures as a deck too, a slide each with a cover before them: at DECK, or "
                             "<file>.pptx beside the pictures")
    p_draw.add_argument("--date", help="a date for the title block and the timeline's current quarter")
    p_draw.add_argument("--example", nargs="?", const="payments", metavar="NAME",
                        help="print an example sketch to start from: payments (the default), on-a-shape, from-parts")
    p_draw.add_argument("--views", action="store_true", help="list the shipped views a sketch may name")
    p_draw.add_argument("--library", action="store_true",
                        help="list the shipped shapes, kits and parts a sketch may put a product on")
    p_draw.add_argument("--drawio", action="store_true",
                        help="write a draw.io file beside the pictures as well, a page per diagram, each box where "
                             "the engine put it, the styles the reader takes back to their types")
    p_draw.add_argument("--excel", action="store_true",
                        help="write what the file said as an Excel workbook beside the pictures, a sheet per type of "
                             "record and the relations, nothing filled in to draw it: a Visio drawing in, an "
                             "inventory out")
    p_draw.add_argument("--plantuml", action="store_true",
                        help="write a C4-PlantUML file beside each diagram as well, the macros the reader takes back")
    p_draw.add_argument("--editable", action="store_true",
                        help="with --pack: every diagram goes on its slide as shapes a reviewer can move, glued by "
                             "its connectors, rather than as a picture; no browser needed for those")
    p_draw.add_argument("--from-mermaid", action="store_true",
                        help="the file is a Mermaid flowchart, C4 diagram or sequence diagram, or a Markdown file "
                             "holding them: read it as a sketch, write the sketch beside it, draw that")
    p_draw.add_argument("--from-structurizr", action="store_true",
                        help="the file is a Structurizr DSL workspace: read it as a sketch, write the sketch beside "
                             "it, draw that")
    p_draw.add_argument("--from-archimate", action="store_true",
                        help="the file is an ArchiMate model, as Archi saves it (.archimate) or in the Open Group's "
                             "exchange format (.xml): read it as a sketch, its views as views, write the sketch "
                             "beside it, draw that")
    p_draw.add_argument("--from-plantuml", action="store_true",
                        help="the file is a C4-PlantUML diagram: read it as a sketch the way a Mermaid C4 diagram "
                             "is read, write the sketch beside it, draw that")
    p_draw.add_argument("--from-drawio", action="store_true",
                        help="the file is a draw.io diagram (.drawio, compressed or not): a box per thing by its "
                             "shape, an arrow per connection, a container per domain, a page per view; read it as "
                             "a sketch, write the sketch beside it, draw that")
    p_draw.add_argument("--from-inventory", action="store_true",
                        help="the file is a spreadsheet of systems (.csv, .tsv or an Excel .xlsx, its inventory "
                             "sheet found by its headers): a row per thing, read by its headers, the type and the "
                             "connections off the columns; read it as a sketch, write the sketch beside it, draw that")
    p_draw.add_argument("--from-visio", action="store_true",
                        help="the file is a Visio drawing (.vsdx): a shape per thing by the master it was dragged "
                             "from, a connector per connection, a container per domain, a page per view; read it as "
                             "a sketch, write the sketch beside it, draw that")
    p_draw.add_argument("--sketch", help="with --from-mermaid, --from-structurizr, --from-archimate, --from-plantuml, "
                                         "--from-drawio, --from-inventory or --from-visio, where the sketch is written")
    p_draw.set_defaults(func=cmd_draw)

    p_adopt = sub.add_parser("adopt", help="write a sketch, or a diagram a reader reads, into this repository as "
                                            "its own records; nothing already here is touched unless --correct")
    p_adopt.add_argument("file", help="a sketch, or an ArchiMate, Structurizr, C4-PlantUML, draw.io, Visio, "
                                      "spreadsheet, Mermaid or Markdown file, read by its suffix")
    p_adopt.add_argument("--owner", help="the org unit of this estate that owns what the sketch left without an "
                                         "owner; else the sketch's placeholder is adopted too, and said")
    p_adopt.add_argument("--dry-run", action="store_true", help="say what would be written and write nothing")
    p_adopt.add_argument("--correct", action="store_true",
                         help="a record already here takes the file's differing cells, written into its own file "
                              "with the file otherwise left as it is: a reviewer's workbook back in; a blank cell "
                              "is left alone, and a correction to what a shape made goes under the product's "
                              "overrides")
    p_adopt.add_argument("--picture", metavar="PATH",
                         help="draw the change first: what the file adds, in full, and with --correct what it "
                              "corrects, with a heavy border or, for a connection, a heavy line, among what is there "
                              "one hop away, faded; an SVG, or a PNG by its suffix")
    p_adopt.set_defaults(func=cmd_adopt)

    p_pack = sub.add_parser("pack", help="the review pack: a slide per view, with the model's numbers on the cover")
    p_pack.add_argument("view", nargs="*", metavar="VIEW[:SUBJECT]",
                        help="the views to pack, a subject view as VIEW:ID; none means every view of the whole "
                             "estate, every product on the product architecture, and the flows")
    p_pack.add_argument("--out", help="where the deck goes; 70_ARTIFACTS/review-pack.pptx by default, not committed")
    p_pack.add_argument("--date", help="the date on the cover and in the title blocks; today by default")
    p_pack.add_argument("--all-rows", action="store_true",
                        help="every page of every register, eight rows a slide; by default a register's first "
                             "page, saying how many rows there are")
    p_pack.add_argument("--editable", action="store_true",
                        help="every diagram goes on its slide as shapes a reviewer can move, glued by its "
                             "connectors, rather than as a picture; maps, registers, timelines and flows keep theirs")
    p_pack.add_argument("--since", metavar="REV",
                        help="open the deck with what changed since this git revision, drawn: the slide a review "
                             "starts from; nothing changed is said and the slide left out")
    p_pack.add_argument("--excel", action="store_true",
                        help="write beside the deck the workbook of what the slides show: the records on the pictures, "
                             "the connections among them and a page per slide; read back by terrane draw, the same pages")
    p_pack.set_defaults(func=cmd_pack)

    p_refresh = sub.add_parser("refresh", help="render, schema, the seven exports and the test seed, in one go")
    p_refresh.add_argument("--no-seed", action="store_true", help="leave 90_EXAMPLE/csv as it is")
    p_refresh.set_defaults(func=cmd_refresh)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (
        ModelError,
        ModelFileError,
        ArchetypeError,
        ViewError,
        ImportError_,
        MappingError,
        LibraryError,
        scaffold.ScaffoldError,
    ) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
