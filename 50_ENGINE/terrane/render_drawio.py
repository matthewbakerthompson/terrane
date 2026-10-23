"""The drawing as a draw.io file, the whiteboard most teams keep.

The reader (`drawio_import`) brings a draw.io file in; this is the way
back out: every picture of the estate, or of a sketch, as a page of one
`.drawio` file, each box where the engine's own layout put it, in the
shape and the colors the SVG has, each boundary a container holding what
sits in it, each line an orthogonal edge through the bends the router laid
down with its label on it, so a team opens the estate in diagrams.net,
moves what the meeting needs moved, and keeps the file beside the model.
The styles are the ones the reader takes back to their types (a cylinder
a data asset, an ellipse an actor, a hexagon a capability, a parallelogram
a technology service, a document a policy, a card a product, an octagon a
control, a process a process), so a page exported and read again is the
sketch it came from, domains included.

The file is written uncompressed, each page's `mxGraphModel` inline, with
no timestamp, so the same estate is the same bytes and the file diffs in
git. What the page does not carry: the mark in a box's corner (a mark is
the app's icon file), the legend and the title block (a page has a name),
and a map with nothing connected (a tile map is the app's HTML and has no
scene). The technology line under a name rides as the box's tooltip, so
the name reads back as the name.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import quoteattr

from .draw.shapes import HEADLESS
from .draw.svg import EDGE, Scene, SceneBoundary, SceneEdge, SceneNode
from .schema import ENTITY_TYPES, RELATION_TYPES

MARGIN = 20
#: draw.io styles by the method's type, the ones the reader takes back to
#: the type; a type not here is drawn by its shape.
TYPE_STYLES: Dict[str, str] = {
    "data_assets": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=8;",
    "actors": "ellipse;",
    "capabilities": "shape=hexagon;perimeter=hexagonPerimeter2;spacingLeft=14;spacingRight=14;",
    "processes": "shape=process;",
    "tech_services": "shape=parallelogram;perimeter=parallelogramPerimeter;",
    "policies": "shape=document;",
    "products": "shape=card;",
    "controls": "shape=mxgraph.basic.octagon2;",
}
SHAPE_STYLES: Dict[str, str] = {
    "round-rectangle": "rounded=1;",
    "pill": "rounded=1;arcSize=50;",
    "rectangle": "rounded=0;",
    "ellipse": "ellipse;",
    "barrel": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=8;",
    "hexagon": "shape=hexagon;perimeter=hexagonPerimeter2;spacingLeft=14;spacingRight=14;",
    "round-hexagon": "shape=hexagon;perimeter=hexagonPerimeter2;spacingLeft=14;spacingRight=14;rounded=1;",
    "rhomboid": "shape=parallelogram;perimeter=parallelogramPerimeter;",
    "tag": "shape=step;perimeter=stepPerimeter;",
    "round-tag": "shape=card;",
    "octagon": "shape=mxgraph.basic.octagon2;",
    "round-octagon": "shape=mxgraph.basic.octagon2;rounded=1;",
    "cut-rectangle": "shape=document;",
    "pentagon": "shape=process;",
    "diamond": "rhombus;",
    "round-diamond": "rhombus;rounded=1;",
}
COMMON = "whiteSpace=wrap;html=1;fontSize=12;fontStyle=1;"
BOUNDARY = ("rounded=1;whiteSpace=wrap;html=1;container=1;collapsible=0;verticalAlign=top;align=left;"
            "spacingLeft=8;spacingTop=2;fontSize=11;fontStyle=1;")
LABEL_INK = "#3f4a5c"


def _f(value: float) -> str:
    text = "%.1f" % value
    return text[:-2] if text.endswith(".0") else text


def _color(value: str, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text.startswith("#") and len(text) in (4, 7) else fallback


def _dash(style: str) -> str:
    if style == "dashed":
        return "dashed=1;"
    if style == "dotted":
        return "dashed=1;dashPattern=1 2;"
    return ""


def node_style(node: SceneNode) -> str:
    """The box's style: its shape by type where the reader knows the type,
    else by the painter's shape, in its own fill, stroke and ink."""
    shape = TYPE_STYLES.get(node.type) or SHAPE_STYLES.get(node.shape) or "rounded=1;"
    return "".join([shape, COMMON, "fillColor=%s;strokeColor=%s;fontColor=%s;strokeWidth=%s;" % (
        _color(node.fill, "#ffffff"), _color(node.stroke, "#8f9bb5"), _color(node.ink, "#0f172a"), _f(node.width)),
        _dash(node.dash), "opacity=55;" if node.faded else ""])


def boundary_style(b: SceneBoundary) -> str:
    return "".join([BOUNDARY, "fillColor=%s;strokeColor=%s;fontColor=%s;strokeWidth=%s;" % (
        _color(b.fill, "#f3f5fb"), _color(b.stroke, "#8f9bb5"), _color(b.ink, "#3b4a6b"), _f(b.width)), _dash(b.dash)])


def edge_style(e: SceneEdge, layered: bool) -> str:
    """A routed line follows its bends as an orthogonal edge; a lone line
    runs straight; a curve is draw.io's curve through its control point."""
    if e.curved:
        route = "curved=1;"
    elif len(e.points) > 2:
        route = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;"
    else:
        route = ""
    head = "endArrow=none;" if e.kind in HEADLESS else "endArrow=blockThin;endFill=1;"
    return "".join([route, "html=1;strokeColor=%s;strokeWidth=%s;%s" % (
        EDGE, "1.6" if layered else "1.3", head), _dash(e.style), "" if layered else "opacity=45;",
        "fontColor=%s;fontSize=10;labelBackgroundColor=#ffffff;" % LABEL_INK])


def _along(points: Sequence[Tuple[float, float]], at: Tuple[float, float]) -> Tuple[float, Tuple[float, float]]:
    """The share of the line's length at the point of it nearest `at`,
    and that point."""
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])]
    total = sum(lengths) or 1.0
    best = (float("inf"), 0.0, points[0])
    walked = 0.0
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if length:
            u = ((at[0] - a[0]) * (b[0] - a[0]) + (at[1] - a[1]) * (b[1] - a[1])) / (length * length)
            u = min(1.0, max(0.0, u))
        else:
            u = 0.0
        p = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
        d = math.hypot(at[0] - p[0], at[1] - p[1])
        if d < best[0]:
            best = (d, (walked + u * length) / total, p)
        walked += length
    return best[1], best[2]


def kinds_by_interface(records, root: Optional[Path] = None) -> Dict[str, str]:
    """Each interface's connection kind by its id, read off its style and
    protocol against the kinds at `root` (the estate's own after the
    shipped ones; the shipped ones alone when no root is given); an
    interface of no kind is left out."""
    from .connections import kind_of, load_connections
    from .library import LibraryError
    from .shipped import shipped_root

    try:
        catalog = load_connections(root if root is not None else shipped_root())
    except LibraryError:
        return {}
    out: Dict[str, str] = {}
    for record in records:
        if isinstance(record, dict) and record.get("interface_id"):
            found = kind_of(record, catalog)
            if found:
                out[str(record["interface_id"])] = found
    return out


def marks_for(records_by_type: Dict[str, Sequence[dict]], kinds: Optional[Dict[str, str]] = None,
              rows: Optional[Dict[str, Sequence[dict]]] = None) -> Dict[str, Dict[str, str]]:
    """What each box and line carries as the attributes of the object
    wrapping it, by record id: a thing's type, id and the fields the picture
    cannot say (its domain, since a band or a provider grouping is not a
    domain; its hosting; an actor's kind), and a connection's id, kind,
    name, protocol and what its kind proposes, as the record has them. The
    reader takes these over the labels, shapes and containers it reads a
    hand-drawn page by: the estate's own export read back would have added
    168 systems, their ids made from the labels."""
    from .render_plantuml import MARK_FIELDS, REL_MARK_FIELDS

    marks: Dict[str, Dict[str, str]] = {}
    for type_name, records in records_by_type.items():
        if type_name not in ENTITY_TYPES:
            continue
        pk = ENTITY_TYPES[type_name].pk
        for record in records:
            if not isinstance(record, dict):
                continue
            entity_id = str(record.get(pk) or "")
            if not entity_id:
                continue
            if type_name == "interfaces":
                mark = {"interface_id": entity_id}
                if (kinds or {}).get(entity_id):
                    mark["kind"] = kinds[entity_id]
                keys: Sequence[str] = ("name", "protocol") + tuple(REL_MARK_FIELDS)
            else:
                mark = {"type": type_name, "id": entity_id}
                keys = MARK_FIELDS
            for key in keys:
                value = record.get(key)
                if value not in (None, "", []):
                    mark[key] = ";".join(str(v) for v in value) if isinstance(value, list) else str(value)
            marks[entity_id] = mark
    # The rows, by relation and both ends, so a line that draws one carries
    # the row and its qualifier, and a line that draws none is derived: the
    # framework landscapes draw a parent capability to the framework its
    # children reference, and read back that was a new row; a line with no
    # label read as ReadWrite over a Read row.
    for relation, relation_rows in (rows or {}).items():
        spec = RELATION_TYPES.get(relation)
        if spec is None:
            continue
        for row in relation_rows:
            if not isinstance(row, dict):
                continue
            left, right = str(row.get(spec.left_column) or ""), str(row.get(spec.right_column) or "")
            mark = {"relation": relation}
            if spec.qualifier and row.get(spec.qualifier) not in (None, "", []):
                value = row[spec.qualifier]
                mark[spec.qualifier] = ";".join(str(v) for v in value) if isinstance(value, list) else str(value)
            marks.setdefault("%s::%s::%s" % (relation, left, right), mark)
    return marks


def _line_mark(e: SceneEdge, marks: Optional[Dict[str, Dict[str, str]]]) -> Optional[Dict[str, str]]:
    """What a line carries: its interface's mark, the row it draws, or
    that it was derived, when the page is written with marks at all."""
    if marks is None:
        return None
    if e.ref:
        return marks.get(e.ref)
    if e.kind == "sot":
        return {"field": "source_of_truth"}  # the line a view draws for a data asset's source of truth
    if e.kind == "offers":
        return {"field": "system_id"}  # an offered interface joined to the system offering it
    if e.kind in RELATION_TYPES:
        return (marks.get("%s::%s::%s" % (e.kind, e.source, e.target))
                or marks.get("%s::%s::%s" % (e.kind, e.target, e.source)) or {"derived": "1"})
    return None


def _attributes(mark: Optional[Dict[str, str]]) -> str:
    return "".join(" aac_%s=%s" % (key, quoteattr(value)) for key, value in (mark or {}).items())


def diagram_xml(scene: Scene, kinds: Optional[Dict[str, str]] = None,
                marks: Optional[Dict[str, Dict[str, str]]] = None) -> str:
    """One page's `mxGraphModel`: the drawing moved so its corner sits a
    margin in from the page's, boundaries first and nested, every box in
    its boundary's own coordinates as draw.io keeps a container's
    children, then the lines through their bends."""
    dx1, dy1, dx2, dy2 = scene.extent
    ox, oy = MARGIN - dx1, MARGIN - dy1
    width, height = int(math.ceil(dx2 - dx1 + 2 * MARGIN)), int(math.ceil(dy2 - dy1 + 2 * MARGIN))
    boundaries = {b.id: b for b in scene.boundaries}

    def origin(parent: Optional[str]) -> Tuple[float, float]:
        """Where a cell's coordinates start on the page: its boundary's
        corner, or the page's own, which is nought. The first cut took the
        drawing's offset for the page's corner and moved every top-level
        box by the margin twice."""
        b = boundaries.get(parent or "")
        if b is None:
            return 0.0, 0.0
        return ox + b.box[0], oy + b.box[1]

    def parent_of(parent: Optional[str]) -> str:
        return parent if parent in boundaries else "1"

    out: List[str] = ['<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
                      'arrows="1" fold="1" page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0">'
                      % (width, height), "  <root>", '    <mxCell id="0"/>', '    <mxCell id="1" parent="0"/>']
    for b in scene.boundaries:
        px, py = origin(b.parent)
        x1, y1, x2, y2 = b.box
        out.append('    <mxCell id=%s value=%s style=%s vertex="1" parent=%s>' % (
            quoteattr(b.id), quoteattr(" ".join(b.lines)), quoteattr(boundary_style(b)), quoteattr(parent_of(b.parent))))
        out.append('      <mxGeometry x="%s" y="%s" width="%s" height="%s" as="geometry"/>' % (
            _f(ox + x1 - px), _f(oy + y1 - py), _f(x2 - x1), _f(y2 - y1)))
        out.append("    </mxCell>")
    for n in scene.nodes:
        px, py = origin(n.parent)
        geometry = '      <mxGeometry x="%s" y="%s" width="%s" height="%s" as="geometry"/>' % (
            _f(ox + n.x - n.w / 2 - px), _f(oy + n.y - n.h / 2 - py), _f(n.w), _f(n.h))
        mark = (marks or {}).get(n.id)
        if n.tech or mark:
            # The technology line rides as the tooltip, so the name reads
            # back as the name and not as the name with the platform after
            # it; the record's type, id and fields ride as attributes, so
            # the box reads back as the record and not as what its label,
            # shape and container suggest.
            out.append('    <UserObject id=%s label=%s%s%s>' % (
                quoteattr(n.id), quoteattr(n.label), " tooltip=%s" % quoteattr(n.tech) if n.tech else "",
                _attributes(mark)))
            out.append('      <mxCell style=%s vertex="1" parent=%s>' % (quoteattr(node_style(n)),
                                                                          quoteattr(parent_of(n.parent))))
            out.append("  " + geometry)
            out.append("      </mxCell>")
            out.append("    </UserObject>")
        else:
            out.append('    <mxCell id=%s value=%s style=%s vertex="1" parent=%s>' % (
                quoteattr(n.id), quoteattr(n.label), quoteattr(node_style(n)), quoteattr(parent_of(n.parent))))
            out.append(geometry)
            out.append("    </mxCell>")
    ids = {n.id for n in scene.nodes}
    for e in scene.edges:
        if e.source not in ids or e.target not in ids:
            continue
        kind = (kinds or {}).get(e.ref, "") if e.ref else ""
        mark = _line_mark(e, marks)
        if kind or mark:
            # The connection's kind rides as an attribute of the object
            # wrapping the line, as a box's technology rides as its tooltip,
            # so the reader takes the line back as a connection of that
            # kind; its id and its record's own values ride the same way.
            out.append('    <UserObject id=%s label=%s%s%s>' % (
                quoteattr(e.id), quoteattr(e.label), " kind=%s" % quoteattr(kind) if kind else "", _attributes(mark)))
            out.append('      <mxCell style=%s edge="1" parent="1" source=%s target=%s>' % (
                quoteattr(edge_style(e, scene.layered)), quoteattr(e.source), quoteattr(e.target)))
        else:
            out.append('    <mxCell id=%s value=%s style=%s edge="1" parent="1" source=%s target=%s>' % (
                quoteattr(e.id), quoteattr(e.label), quoteattr(edge_style(e, scene.layered)), quoteattr(e.source),
                quoteattr(e.target)))
        bends = e.points[1:-1]
        # draw.io sets a label at the middle of its line; the engine put it
        # where it would not sit on a box, so the label goes there: the
        # position along the line nearest the spot, and the rest as offset.
        label_geometry = ' x="0"'
        offset = ""
        if e.label and e.label_at is not None and len(e.points) >= 2:
            t, (px, py) = _along(e.points, e.label_at)
            label_geometry = ' x="%s" y="0"' % ("%.3f" % (2 * t - 1)).rstrip("0").rstrip(".")
            offset = '        <mxPoint x="%s" y="%s" as="offset"/>' % (_f(e.label_at[0] - px), _f(e.label_at[1] - py))
        if bends or offset:
            out.append('      <mxGeometry%s relative="1" as="geometry">' % (label_geometry if offset else ""))
            if bends:
                out.append('        <Array as="points">')
                for x, y in bends:
                    out.append('          <mxPoint x="%s" y="%s"/>' % (_f(ox + x), _f(oy + y)))
                out.append("        </Array>")
            if offset:
                out.append(offset)
            out.append("      </mxGeometry>")
        else:
            out.append('      <mxGeometry relative="1" as="geometry"/>')
        out.append("    </mxCell>")
        if kind or mark:
            out.append("    </UserObject>")
    out.append("  </root>")
    out.append("</mxGraphModel>")
    return "\n".join(out)


def render_drawio(pages: Sequence[Tuple[str, str, Scene]], kinds: Optional[Dict[str, str]] = None,
                  marks: Optional[Dict[str, Dict[str, str]]] = None) -> str:
    """The file: a `diagram` per (page id, name, scene), uncompressed;
    `kinds` is each interface's connection kind by id, which a line of
    one carries."""
    out = ['<mxfile host="architecture-as-code" version="24.0.0" type="device">']
    for page_id, name, scene in pages:
        out.append('  <diagram id=%s name=%s>' % (quoteattr(page_id), quoteattr(name)))
        out.extend("    " + line for line in diagram_xml(scene, kinds, marks).splitlines())
        out.append("  </diagram>")
    out.append("</mxfile>")
    return "\n".join(out) + "\n"


def tile_scene(payload: dict, lay) -> Scene:
    """A map with nothing connected as a scene: the bands and cards the
    tile layout stacks as boundaries, the tiles as boxes where it put
    them, no lines. The painter has no scene for one, since the app draws
    it as HTML; the page draws the same boxes."""
    boundaries: List[SceneBoundary] = []
    for band in lay.bands:
        d = band.data
        boundaries.append(SceneBoundary(band.id, (band.x, band.y, band.x + band.w, band.y + band.h),
                                        d.get("bfill") or "#f3f5fb", d.get("bstroke") or "#8f9bb5", 1.0, "solid",
                                        [str(d.get("label") or "")], d.get("bink") or "#3b4a6b", 1, d.get("parent")))
    for card in lay.all_cards():
        d = card.data
        boundaries.append(SceneBoundary(card.id, (card.x, card.y, card.x + card.w, card.y + card.h),
                                        d.get("bfill") or "#ffffff", d.get("bstroke") or "#cdd5e1", 1.0, "solid",
                                        [str(d.get("label") or "")], d.get("bink") or "#3b4a6b", 2, d.get("parent")))
    nodes: List[SceneNode] = []
    for tile in lay.all_tiles():
        d = tile.data
        nodes.append(SceneNode(tile.id, "round-rectangle", tile.x + tile.w / 2, tile.y + tile.h / 2, tile.w, tile.h,
                               d.get("fill") or "#ffffff", d.get("stroke") or "#8f9bb5", float(tile.border or 1),
                               "solid", str(d.get("label") or ""), d.get("ink") or "#0f172a",
                               " ".join(tile.tech.lines) if tile.tech else "", False,
                               str(d.get("entityType") or ""), d.get("parent")))
    x1, y1, x2, y2 = lay.content
    return Scene((x1, y1, x2, y2), boundaries, [], nodes, True, "tiles")


def gather_scenes(model, views, palette, icons, components, web=None) -> Tuple[List[Tuple[str, str, Scene]], List[str]]:
    """Every picture view of the estate as a scene, bound once per subject
    where the view takes one, laid out as the pictures are (ELK through
    the browser on the machine where the app would use ELK); what could
    not be drawn, and why, in the notes."""
    from .draw import Undrawable, drawing_mode, render_svg
    from .draw.elk import open_runner
    from .draw.metrics import default_metrics
    from .draw.mode import is_tile_map
    from .draw.tiles import layout_tiles
    from .payload import graph_payload
    from .query import ViewError, bind, render_targets, resolve

    pages: List[Tuple[str, str, Scene]] = []
    notes: List[str] = []
    elk = open_runner(web) if web is not None else None
    try:
        for view in views:
            if view.kind in ("report", "timeline"):
                continue
            bound_views = []
            if view.parameters:
                for parameter, value in render_targets(model, view):
                    try:
                        bound_views.append((bind(view, {parameter: value}, model),
                                            "%s--%s" % (view.view_id, str(value))))
                    except ViewError as exc:
                        notes.append("%s: %s" % (view.view_id, exc))
            else:
                bound_views.append((view, view.view_id))
            for bound, page_id in bound_views:
                collected: list = []
                try:
                    graph = resolve(model, bound)
                    payload = graph_payload(model, bound, palette, icons, components, graph=graph)
                    drawing_mode(payload)
                    render_svg(payload, icon_loader=icons.read if icons is not None else None, elk=elk,
                               scene_out=collected)
                except (ViewError, Undrawable) as exc:
                    notes.append("%s: %s; left out" % (page_id, exc))
                    continue
                if not collected and is_tile_map(payload):
                    collected.append(tile_scene(payload, layout_tiles(payload, 1240, default_metrics())))
                if not collected:
                    notes.append("%s: nothing to draw; left out" % page_id)
                    continue
                pages.append((page_id, bound.title, collected[0]))
    finally:
        if elk is not None:
            elk.close()
    return pages, notes


def export_drawio(model, views, out_path: Path, palette, icons, components, web=None) -> Tuple[Path, List[str]]:
    """Write every picture view of the estate as a page of one draw.io
    file at `out_path`; the path and the notes."""
    pages, notes = gather_scenes(model, views, palette, icons, components, web)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kinds = kinds_by_interface(model.all_of("interfaces"), model.root)
    marks = marks_for({t: model.all_of(t) for t in ENTITY_TYPES}, kinds, {r: model.relation_rows(r) for r in RELATION_TYPES})
    out_path.write_text(render_drawio(pages, kinds, marks), encoding="utf-8", newline="\n")
    return out_path, notes
