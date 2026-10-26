"""The picture the app draws, painted as SVG.

The app paints a drawing with Cytoscape and a canvas over it, and exports
it as a sheet: a title block, the drawing at 2x, the legend, a footer. This
paints the same sheet as one SVG, in the same encoding (`shapes.py`), the
same faces (`metrics.py`) and the same geometry (`packed.py` for a packed
map, `layered.py` for a layered diagram, `tiles.py` for a map with nothing
connected, which the app draws as HTML), with nothing in it a browser has
to compute. The differences are the ones vector gives for free: crisp at
any zoom, every label real text, every mark the provider's own file, and a
hover on a line that still says what it is.

What Cytoscape does that this reproduces on purpose, because the pictures
are compared side by side: a compound's box is sized from its children's
boxes *including their borders*, and the layout's extent is not; a
round rectangle's corner is a quarter of its shorter side capped at eight;
on a packed map a lone edge between two nodes is straight and a bundle
fans out forty pixels a step; on a layered diagram an edge is the three
pieces the router laid down, its corners rounded to ten, leaving and
arriving where the line from its first turn to the node's center meets the
node's outer border; the line stops short of the arrow's tip by twice its
width, and the arrow is a filled triangle sized from the line's width.
A tile map is painted as the browser paints the app's HTML: a card's
border inside its box, a tile's border at the whole pixel Chrome snaps it
to, every line of text on the baseline its line box gives it.
"""

from __future__ import annotations

import base64
import math
from typing import Callable, Dict, List, NamedTuple, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from . import annotations as own_module
from . import labels as labels_module
from .arranged import arrange
from .elk import ElkLayout, ElkRoute, layout_elk
from .layered import (BOUNDARY_FONT, BOUNDARY_LABEL_DOWN, LayeredLayout, Route, boundary_lines, group_body,
                      group_border, is_ribbon, layout_layered, leaf_box, route_layered)
from .router import route_grid
from .metrics import Metrics, default_metrics
from .mode import Mode, Undrawable, drawing_mode, is_tile_map
from .packed import Group, Layout, Leaf, Prepared, layout_packed, prepare, title_room, title_width
from .organic import layout_organic
from .wheel import layout_wheel
from .shapes import (BOUNDARY_FILL, GLYPH_PATHS, HEADLESS, PILL_RADIUS, POLYGONS, SHAPE_KEYS, TECH_FONT,
                     TYPE_ICON_BODIES, edge_word, key_label)
from .tiles import (CARD_BORDER, CARD_RADIUS, INK, INK_2, INK_3, PANEL, RULE, RULE_2, TILE_RADIUS, Cards, Grid,
                    TileLayout, baseline, layout_tiles, line_height, tile_meta)
from .tiles import Text as TileText

SANS = "Geist, system-ui, sans-serif"
MONO = "Geist Mono, ui-monospace, monospace"
INK_SOFT = "#5b6577"
EDGE = "#7b8798"
#: The fonts the sheet sets type in, by family and weight, from the app's
#: own files when embedding is asked for.
FONT_FILES = {
    ("Geist", 400): "geist-latin-400-normal.woff2",
    ("Geist", 500): "geist-latin-500-normal.woff2",
    ("Geist", 600): "geist-latin-600-normal.woff2",
    ("Geist", 700): "geist-latin-700-normal.woff2",
    ("Geist Mono", 400): "geist-mono-latin-400-normal.woff2",
    ("Geist Mono", 500): "geist-mono-latin-500-normal.woff2",
}
#: Where a line box puts the baseline, as a share of the font size, for a
#: face whose ascent is 1.01em and descent 0.30em set at line-height 1.
BASELINE = 0.855
#: The line on a packed map steps back; on a layered diagram it is the
#: reading order and stands at full weight.
LINE_PACKED = 1.3
LINE_LAYERED = 1.6
ARROW_SCALE = 1.1
#: The corner radius of a routed edge's turns.
SEGMENT_RADIUS = 10

Box = Tuple[float, float, float, float]
Point = Tuple[float, float]
IconLoader = Callable[[str], Optional[bytes]]


class SceneNode(NamedTuple):
    """A node as placed: its shape, its center and size, its colors, the
    name and the technology line, in sheet pixels."""
    id: str
    shape: str
    x: float
    y: float
    w: float
    h: float
    fill: str
    stroke: str
    width: float
    dash: str
    label: str
    ink: str
    tech: str
    faded: bool
    type: str
    #: The boundary it sits in, by id; None at the top.
    parent: Optional[str] = None


class SceneBoundary(NamedTuple):
    id: str
    box: Box
    fill: str
    stroke: str
    width: float
    dash: str
    lines: List[str]
    ink: str
    depth: int
    parent: Optional[str] = None


class SceneEdge(NamedTuple):
    """An edge as drawn: the points it passes from where it leaves its
    source to the arrow's tip, three with `curved` and the middle one the
    control point of the curve; the label and where it sits, if placed."""
    id: str
    source: str
    target: str
    points: List[Point]
    curved: bool
    style: str
    label: str
    label_at: Optional[Point]
    label_box: Optional[Box]
    #: The interface the edge draws, when it draws one, so a page written
    #: for another tool can say the connection's kind; blank otherwise.
    ref: str = ""
    #: The relation the edge draws (`system_reads_writes`, `interfaces`, a
    #: field's name), so a page written for another tool can mark a row
    #: as the row it is and a derived line as derived.
    kind: str = ""


class Scene(NamedTuple):
    """The drawing as the things it is made of, for a painter that is not
    this one: the editable deck draws each as a PowerPoint shape glued to
    its connectors, from the same geometry the SVG was painted from."""
    extent: Box
    boundaries: List[SceneBoundary]
    edges: List[SceneEdge]
    nodes: List[SceneNode]
    layered: bool
    drawn_by: str

#: The unit circle at ten-degree steps through the first half quadrant, as
#: the cosine and sine of 0, 10, 20, 30 and 40 degrees written out; the
#: other thirty-one points of the ellipse's outline are these reflected.
#: Written out because the C library's cos and sin are not the same number
#: on every platform in the last bit, and the committed SVG is compared
#: byte for byte by a Linux runner against what Windows rendered.
_ARC = ((1.0, 0.0), (0.984807753012208, 0.17364817766693033), (0.9396926207859084, 0.3420201433256687),
        (0.8660254037844387, 0.5), (0.766044443118978, 0.6427876096865393))
_QUARTER = list(_ARC) + [(s, c) for c, s in reversed(_ARC[1:])]  # 0 to 80 degrees, nine points
#: The full circle from (1, 0), 36 points. `0.0 - x` rather than `-x` so a
#: zero stays a plain zero rather than a minus zero.
ELLIPSE = tuple([(c, s) for c, s in _QUARTER] + [(0.0 - s, c) for c, s in _QUARTER]
                + [(0.0 - c, 0.0 - s) for c, s in _QUARTER] + [(s, 0.0 - c) for c, s in _QUARTER])


def fmt(value: float) -> str:
    text = "%.2f" % value
    text = text.rstrip("0").rstrip(".") if "." in text else text
    return "0" if text in ("-0", "") else text


def attr(value: str) -> str:
    return escape(str(value), {'"': "&quot;"})


def round_rect_radius(w: float, h: float) -> float:
    return min(w / 4, h / 4, 8)


def round_polygon_radius(w: float, h: float) -> float:
    return min(w / 10, h / 10, 8)


def polygon_points(shape: str, cx: float, cy: float, w: float, h: float) -> List[Point]:
    """The shape's outline as a polygon in sheet coordinates."""
    if shape == "ellipse":
        return [(cx + w / 2 * c, cy + h / 2 * s) for c, s in ELLIPSE]
    if shape == "cut-rectangle":
        c = min(8, w / 2, h / 2)
        x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        return [(x1 + c, y1), (x2 - c, y1), (x2, y1 + c), (x2, y2 - c), (x2 - c, y2), (x1 + c, y2), (x1, y2 - c),
                (x1, y1 + c)]
    pts = POLYGONS.get(shape) or POLYGONS["rectangle"]
    return [(cx + w / 2 * pts[i], cy + h / 2 * pts[i + 1]) for i in range(0, len(pts), 2)]


def rounded_polygon_path(points: Sequence[Point], radius: float) -> str:
    """A polygon with each corner rounded by `radius`, the way Cytoscape
    draws its round-* shapes: the corner cut back along both edges and
    joined by a curve."""
    n = len(points)
    parts = []
    for i in range(n):
        p0, p1, p2 = points[i - 1], points[i], points[(i + 1) % n]
        d1 = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1
        d2 = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) or 1
        r = min(radius, d1 / 2, d2 / 2)
        a = (p1[0] - (p1[0] - p0[0]) / d1 * r, p1[1] - (p1[1] - p0[1]) / d1 * r)
        b = (p1[0] + (p2[0] - p1[0]) / d2 * r, p1[1] + (p2[1] - p1[1]) / d2 * r)
        parts.append(("M" if i == 0 else "L") + "%s %s" % (fmt(a[0]), fmt(a[1])))
        parts.append("Q%s %s %s %s" % (fmt(p1[0]), fmt(p1[1]), fmt(b[0]), fmt(b[1])))
    return " ".join(parts) + " Z"


def barrel_path(cx: float, cy: float, w: float, h: float) -> str:
    """Cytoscape's barrel: a box whose top and bottom edges curve down into
    the sides, `generateBarrelBezierPts` with its constants."""
    a, i = h / 2, w / 2
    o, s, l, u = cx - i, cx + i, cy - a, cy + a
    h_off, w_off, f = min(15, 0.05 * h), min(100, 0.25 * w), 0.05 * w
    return ("M%s %s Q%s %s %s %s L%s %s Q%s %s %s %s L%s %s Q%s %s %s %s L%s %s Q%s %s %s %s Z" % tuple(
        fmt(v) for v in (
            o, l + h_off, o + f, l, o + w_off, l,
            s - w_off, l, s - f, l, s, l + h_off,
            s, u - h_off, s - f, u, s - w_off, u,
            o + w_off, u, o + f, u, o, u - h_off)))


def shape_path(shape: str, cx: float, cy: float, w: float, h: float) -> str:
    """The element that draws a node body, without fill or stroke."""
    if shape == "pill":
        # Cytoscape's round rectangle with the app's corner radius, which it
        # holds to half the box.
        r = min(PILL_RADIUS, w / 2, h / 2)
        return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s"' % (
            fmt(cx - w / 2), fmt(cy - h / 2), fmt(w), fmt(h), fmt(r))
    if shape == "round-rectangle":
        r = round_rect_radius(w, h)
        return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s"' % (
            fmt(cx - w / 2), fmt(cy - h / 2), fmt(w), fmt(h), fmt(r))
    if shape == "rectangle":
        return '<rect x="%s" y="%s" width="%s" height="%s"' % (fmt(cx - w / 2), fmt(cy - h / 2), fmt(w), fmt(h))
    if shape == "ellipse":
        return '<ellipse cx="%s" cy="%s" rx="%s" ry="%s"' % (fmt(cx), fmt(cy), fmt(w / 2), fmt(h / 2))
    if shape == "barrel":
        return '<path d="%s"' % barrel_path(cx, cy, w, h)
    pts = polygon_points(shape, cx, cy, w, h)
    if shape.startswith("round-"):
        return '<path d="%s"' % rounded_polygon_path(pts, round_polygon_radius(w, h))
    return '<path d="%s"' % (" ".join(("M" if i == 0 else "L") + "%s %s" % (fmt(x), fmt(y))
                                      for i, (x, y) in enumerate(pts)) + " Z")


def intersect(center: Point, outside: Point, polygon: Sequence[Point]) -> Point:
    """Where the line from the center toward an outside point leaves the
    shape: the crossing nearest the outside point."""
    cx, cy = center
    ox, oy = outside
    best, best_d = None, math.inf
    n = len(polygon)
    for i in range(n):
        (x1, y1), (x2, y2) = polygon[i], polygon[(i + 1) % n]
        den = (x2 - x1) * (oy - cy) - (y2 - y1) * (ox - cx)
        if abs(den) < 1e-9:
            continue
        t = ((cx - x1) * (oy - cy) - (cy - y1) * (ox - cx)) / den
        u = ((cx - x1) * (y2 - y1) - (cy - y1) * (x2 - x1)) / den
        if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            px, py = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            d = math.hypot(ox - px, oy - py)
            if d < best_d:
                best, best_d = (px, py), d
    return best or center


def arrow_width(line_width: float, scale: float) -> float:
    """Cytoscape's arrow size for a line of this width: the width times
    13.37 to the power 0.9, with a floor of 29. The floor wins for every
    width up to 3.15, and the painter draws lines of 1.3 and 1.6, so the
    power -- the C library's, and not the same number everywhere -- is
    never taken; a wider line is refused rather than sized differently on
    different platforms."""
    if line_width > 3.15:
        raise ValueError("a line wider than 3.15 wants an arrow the painter cannot size the same everywhere")
    return 29.0 * scale


def _head(edge: "_Edge", tip: Point, toward: Point, line_width: float) -> Tuple[List[Point], Point]:
    """The edge's arrow and where its line stops: short of the tip under
    the head, or at the tip itself for a line drawn with none."""
    if str(edge.data.get("kind") or "") in HEADLESS:
        return [], tip
    return arrow_head(tip, toward, line_width)


def arrow_head(tip: Point, toward: Point, line_width: float) -> Tuple[List[Point], Point]:
    """The filled triangle at `tip`, pointing the way the line arrives from
    `toward`, and where the line itself stops: Cytoscape ends it short of
    the tip by twice the line's width, scaled, under the head."""
    size = arrow_width(line_width, ARROW_SCALE)
    d = math.hypot(tip[0] - toward[0], tip[1] - toward[1]) or 1
    ux, uy = (tip[0] - toward[0]) / d, (tip[1] - toward[1]) / d
    length, half = 0.3 * size, 0.15 * size
    base = (tip[0] - ux * length, tip[1] - uy * length)
    gap = 2 * line_width * ARROW_SCALE
    return ([tip, (base[0] - uy * half, base[1] + ux * half), (base[0] + uy * half, base[1] - ux * half)],
            (tip[0] - ux * gap, tip[1] - uy * gap))


def dash(style: str, line: bool) -> str:
    if style == "dashed":
        return ' stroke-dasharray="%s"' % ("6 3" if line else "4 2")
    if style == "dotted":
        return ' stroke-dasharray="1 1"'
    return ""


def text_el(x: float, y: float, content: str, size: float, weight: int, fill: str, family: str = SANS,
            anchor: str = "start", extra: str = "") -> str:
    """One line of text with its baseline at `y`."""
    return '<text x="%s" y="%s" font-size="%s" font-weight="%d" fill="%s"%s%s%s>%s</text>' % (
        fmt(x), fmt(y), fmt(size), weight, fill,
        ' font-family="%s"' % attr(family) if family != SANS else "",
        ' text-anchor="%s"' % anchor if anchor != "start" else "", extra, escape(content))


class _Corner:
    """A routed edge's turn, rounded: where the line leaves the straight
    piece before, where it rejoins the one after, and the arc between."""
    __slots__ = ("at", "radius", "tin", "tout", "center", "sweep")

    def __init__(self, at: Point, radius: float, tin: Point, tout: Point, center: Point, sweep: int) -> None:
        self.at, self.radius, self.tin, self.tout, self.center, self.sweep = at, radius, tin, tout, center, sweep


def round_corner(prev: Point, cur: Point, nxt: Point, radius: float) -> Optional[_Corner]:
    """Cytoscape's arc at a segment point: of the asked radius, tangent to
    both pieces, pulled in where a piece is too short to hold it; none
    where the pieces run straight through."""
    v1 = (prev[0] - cur[0], prev[1] - cur[1])
    v2 = (nxt[0] - cur[0], nxt[1] - cur[1])
    len1, len2 = math.hypot(*v1), math.hypot(*v2)
    if len1 < 1e-9 or len2 < 1e-9 or radius <= 0:
        return None
    u1, u2 = (v1[0] / len1, v1[1] / len1), (v2[0] / len2, v2[1] / len2)
    cos_angle = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
    # Straight through, or doubling back: an angle under a millionth of a
    # radian either side, said in its cosine.
    if 1 - cos_angle < 5e-13 or 1 + cos_angle < 5e-13:
        return None
    # The arc meets each piece at radius / tan(half) from the corner, half
    # being half the angle between the pieces. Its sine and cosine come
    # from the cosine of the whole by the half-angle identities, through
    # sqrt alone: the C library's sin and cos of 45 degrees differ in the
    # last bit between Windows and Linux, and for a right-angle turn pulled
    # in to a piece 6.53 wide that bit decided whether the radius 3.265
    # printed as 3.26 or 3.27, which is what made four committed SVGs stale
    # on the Linux runner. Here a right angle gives exactly 1.
    sin_half = math.sqrt((1 - cos_angle) / 2)
    cos_half = math.sqrt((1 + cos_angle) / 2)
    # The ratio first, so that a right angle's 1 leaves the length as it
    # is: (a * s) / c is not a for the same s and c in floating point.
    tan_half = sin_half / cos_half
    len_out = radius / tan_half
    if len_out > min(len1, len2) / 2:
        len_out = min(len1, len2) / 2
        radius = len_out * tan_half
    tin = (cur[0] + u1[0] * len_out, cur[1] + u1[1] * len_out)
    tout = (cur[0] + u2[0] * len_out, cur[1] + u2[1] * len_out)
    bx, by = u1[0] + u2[0], u1[1] + u2[1]
    bl = math.hypot(bx, by) or 1
    reach = radius / sin_half
    center = (cur[0] + bx / bl * reach, cur[1] + by / bl * reach)
    cross = (tin[0] - center[0]) * (tout[1] - center[1]) - (tin[1] - center[1]) * (tout[0] - center[0])
    return _Corner(cur, radius, tin, tout, center, 1 if cross > 0 else 0)


class _Edge:
    __slots__ = ("data", "path", "pieces", "mid", "arrow", "points")

    def __init__(self, data: dict) -> None:
        self.data = data
        self.path = ""
        self.pieces: List[labels_module.Piece] = []
        self.mid: Point = (0.0, 0.0)
        self.arrow: List[Point] = []
        #: Every point the line passes, for the drawing's extent.
        self.points: List[Point] = []


def _packed_edges(prep: Prepared, centers: Dict[str, Point], polygons: Dict[str, List[Point]],
                  line_width: float) -> List[_Edge]:
    """Cytoscape's bezier bundles: a lone edge between two nodes is
    straight; a bundle fans out about the chord, forty pixels a step,
    mirrored for the edge that runs the other way so two directions never
    share a curve."""
    edges = [_Edge(e) for e in prep.edges if e["source"] in centers and e["target"] in centers]
    bundles: Dict[Tuple[str, str], List[_Edge]] = {}
    for edge in edges:
        key = tuple(sorted((edge.data["source"], edge.data["target"])))
        bundles.setdefault(key, []).append(edge)
    for key, bundle in bundles.items():
        n = len(bundle)
        for i, edge in enumerate(bundle):
            _bezier(edge, key, i, n, centers, polygons, line_width)
    return edges


def _bezier(edge: _Edge, key: Tuple[str, str], i: int, n: int, centers: Dict[str, Point],
            polygons: Dict[str, List[Point]], line_width: float) -> None:
    sx, sy = centers[edge.data["source"]]
    tx, ty = centers[edge.data["target"]]
    dist = 40 * (i - (n - 1) / 2)
    if edge.data["source"] != key[0]:
        dist = -dist
    chord = math.hypot(tx - sx, ty - sy) or 1
    nx, ny = -(ty - sy) / chord, (tx - sx) / chord
    ctrl = ((sx + tx) / 2 + nx * dist, (sy + ty) / 2 + ny * dist)
    start = intersect((sx, sy), ctrl if dist else (tx, ty), polygons[edge.data["source"]])
    tip = intersect((tx, ty), ctrl if dist else (sx, sy), polygons[edge.data["target"]])
    edge.arrow, end = _head(edge, tip, ctrl if dist else start, line_width)
    if dist:
        edge.path = "M%s %s Q%s %s %s %s" % tuple(fmt(v) for v in (*start, *ctrl, *end))
        edge.mid = (0.25 * start[0] + 0.5 * ctrl[0] + 0.25 * end[0], 0.25 * start[1] + 0.5 * ctrl[1] + 0.25 * end[1])
        legs = [labels_module.piece(*start, *ctrl), labels_module.piece(*ctrl, *end)]
        edge.points = [start, ctrl, end]
    else:
        edge.path = "M%s %s L%s %s" % tuple(fmt(v) for v in (*start, *end))
        edge.mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        legs = [labels_module.piece(*start, *end)]
        edge.points = [start, end]
    edge.pieces = [p for p in legs if p]


def _layered_edges(prep: Prepared, lay: LayeredLayout, centers: Dict[str, Point],
                   polygons: Dict[str, List[Point]], line_width: float, routing: str = "grid") -> List[_Edge]:
    """The routed edges as drawn: around the other nodes and boundaries on
    the grid router (`routing="grid"`, the default), or the app's own three
    pieces -- out of the node, across the turn, in -- with `routing="pieces"`;
    a free edge, with no face toward the other across a gap, is a bezier
    bundle like a packed map's."""
    if routing == "pieces":
        routes = route_layered(prep, lay, lay.direction == "TB")
    else:
        routes = route_grid(prep, lay, lay.direction == "TB")
    edges = [_Edge(e) for e in prep.edges if e["source"] in centers and e["target"] in centers]
    free: Dict[Tuple[str, str], List[_Edge]] = {}
    for edge in edges:
        route = routes.get(edge.data["id"])
        if route is None:
            key = tuple(sorted((edge.data["source"], edge.data["target"])))
            free.setdefault(key, []).append(edge)
            continue
        _orthogonal(edge, route, centers, polygons, line_width)
    for key, bundle in free.items():
        for i, edge in enumerate(bundle):
            _bezier(edge, key, i, len(bundle), centers, polygons, line_width)
    return edges


def _orthogonal(edge: _Edge, route: Route, centers: Dict[str, Point], polygons: Dict[str, List[Point]],
                line_width: float) -> None:
    pts = route.points
    start = route.start or intersect(centers[edge.data["source"]], pts[0], polygons[edge.data["source"]])
    tip = route.end or intersect(centers[edge.data["target"]], pts[-1], polygons[edge.data["target"]])
    edge.arrow, end = _head(edge, tip, pts[-1], line_width)
    parts = ["M%s %s" % (fmt(start[0]), fmt(start[1]))]
    corners: List[Optional[_Corner]] = []
    prev = start
    for i, p in enumerate(pts):
        nxt = pts[i + 1] if i + 1 < len(pts) else end
        corner = round_corner(prev, p, nxt, SEGMENT_RADIUS)
        corners.append(corner)
        if corner is None:
            parts.append("L%s %s" % (fmt(p[0]), fmt(p[1])))
        else:
            parts.append("L%s %s" % (fmt(corner.tin[0]), fmt(corner.tin[1])))
            parts.append("A%s %s 0 0 %d %s %s" % (fmt(corner.radius), fmt(corner.radius), corner.sweep,
                                                  fmt(corner.tout[0]), fmt(corner.tout[1])))
        prev = p
    parts.append("L%s %s" % (fmt(end[0]), fmt(end[1])))
    edge.path = " ".join(parts)
    chain = [start] + list(pts) + [end]
    edge.pieces = [p for p in (labels_module.piece(*chain[i], *chain[i + 1]) for i in range(len(chain) - 1)) if p]
    edge.points = chain
    # Cytoscape's midpoint of a segment edge: between the middle two
    # points when there is an even number of them, else on the middle
    # point's arc, the spot of it nearest the corner.
    if len(pts) % 2 == 0:
        a, b = pts[len(pts) // 2 - 1], pts[len(pts) // 2]
        edge.mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    else:
        corner = corners[len(pts) // 2]
        if corner is None or corner.radius <= 0:
            edge.mid = pts[len(pts) // 2]
        else:
            vx, vy = corner.at[0] - corner.center[0], corner.at[1] - corner.center[1]
            vl = math.hypot(vx, vy) or 1
            edge.mid = (corner.center[0] + vx / vl * corner.radius, corner.center[1] + vy / vl * corner.radius)


def render_svg(payload: dict, layout: Optional[object] = None, *, sheet_width: float = 1240,
               sheet_height: float = 871.4375, metrics: Optional[Metrics] = None,
               icon_loader: Optional[IconLoader] = None, font_loader: Optional[IconLoader] = None,
               font_url_prefix: str = "", sheet: bool = True, model_name: str = "", date: str = "",
               labels: Optional[bool] = None, routing: str = "grid", elk=None,
               scene_out: Optional[list] = None) -> str:
    """The view as one SVG document.

    `payload` is what `/api/graph` returns. `layout` is the layout to
    paint, a packed `Layout`, a `LayeredLayout` or a `TileLayout`, or the
    one the app would compute for a sheet of the given size (a tile map
    wraps to the sheet's width and is as tall as it needs to be); a view
    the Python drawing does not cover raises `Undrawable` with the reason. `icon_loader` returns
    the bytes of a served icon path (`icons/aws/...svg`) or None;
    `font_loader` returns a font file's bytes by name and, when given, the
    faces are embedded so the picture is set in Geist wherever it is opened;
    `font_url_prefix` names them by URL instead, for a picture served beside
    the app's own font files.
    `sheet` adds the title block, legend and footer the app's export has.
    `date` is written on the sheet only when given, since a generated file
    that carried the day it was made would never be idempotent. `elk` is
    an ELK runner (`terrane.draw.elk.open_runner`): with one, a small unlaned
    diagram the app hands to ELK is laid out by ELK here too and the sheet
    says `elk`; without one it is drawn on the dagre path and says so.
    `scene_out`, a list, receives the drawing as a `Scene` beside the SVG:
    the same geometry for a painter that is not this one, with nothing laid
    out twice. A tile map has no scene; it is the app's HTML, not shapes."""
    m = metrics or default_metrics()
    if is_tile_map(payload) and (layout is None or isinstance(layout, TileLayout)):
        lay = layout if isinstance(layout, TileLayout) else layout_tiles(payload, sheet_width, m)
        # The export is the host as the PNG button clones it, padding and
        # all; on a sheet the host's own padding gives way to the sheet's.
        extent = lay.content if sheet else (0.0, 0.0, lay.width, lay.height)
        return _frame(payload, m, paint_tiles(lay, m), extent, "tiles", tile_meta(payload), sheet=sheet,
                      pad=28 if sheet else 0, font_loader=font_loader, font_url_prefix=font_url_prefix,
                      model_name=model_name, date=date)
    own = list(payload.get("annotations") or [])
    if own and not any(not (e.get("data") or {}).get("source") for e in payload.get("elements") or []):
        # A diagram with nothing from the estate on it yet, only shapes of
        # its own: those, on the sheet, and nothing laid out.
        under_svg, under_boxes = own_module.paint(own, (0.0, 0.0), {}, m, "under")
        over_svg, over_boxes = own_module.paint(own, (0.0, 0.0), {}, m, "over")
        taken = under_boxes + over_boxes or [(0.0, 0.0, 200.0, 80.0)]
        extent = (min(b[0] for b in taken), min(b[1] for b in taken), max(b[2] for b in taken), max(b[3] for b in taken))
        return frame_sheet(payload, m, "\n".join(s for s in (under_svg, over_svg) if s), extent, "own", "", sheet=sheet,
                           pad=28, font_loader=font_loader, font_url_prefix=font_url_prefix, model_name=model_name,
                           date=date)
    prep = prepare(payload)
    mode: Mode = drawing_mode(payload, prep)
    organic = False
    # Arranged by hand on the canvas: the dagre layout proposes and what
    # was kept overrides it, whatever the view would otherwise be given, as
    # `drawGraph()` does on Auto. ELK's routes would be for boxes that are
    # no longer where it put them.
    kept = payload.get("positions") or {}
    arranged = bool(kept) and layout is None and mode.kind in ("packed", "layered")
    if layout is not None:
        lay = layout
        layered = isinstance(layout, LayeredLayout)
    elif arranged:
        lay = arrange(prep, layout_layered(payload, sheet_width, sheet_height, prep, m), kept)
        layered = True
    elif mode.kind == "packed":
        lay = layout_packed(payload, sheet_width, sheet_height, prep)
        layered = False
    elif mode.kind == "wheel":
        # The hub in the middle and its spokes on a ring, the lines straight
        # between them as Cytoscape's beziers are for lone edges.
        lay = layout_wheel(payload, sheet_width, sheet_height, prep)
        layered = False
    else:
        lay = layout_layered(payload, sheet_width, sheet_height, prep, m)
        layered = True
        # A drawing with no boundaries that dagre ranks into one long line.
        # The app never shows that line: a small one it hands to ELK, which
        # does not ribbon, and a large one it lays out organically after
        # dagre, cose seeded from where dagre left things. Both run in the
        # browser here, so the check waits on the runner; without one
        # neither is drawn, and the refusal says what is missing.
        if is_ribbon(prep, lay, m) and not (mode.fallback and elk is not None):
            view = payload.get("viewId") or "the view"
            if mode.fallback:
                raise Undrawable("%s has no boundaries and comes out as a ribbon on the dagre path; the app hands "
                                 "it to ELK, which needs a browser on this machine" % view, "elk")
            if elk is None or not elk.has_cose:
                raise Undrawable("%s has no boundaries and comes out as a ribbon, which the app lays out "
                                 "organically; that layout needs a browser on this machine" % view, "organic")
            lay = layout_organic(prep, lay, elk, sheet_width, sheet_height)
            layered = False
            organic = True
    # The app hands a small, unlaned diagram to ELK; with a runner, so does
    # this, and the picture is the app's rather than the dagre fallback.
    elk_result: Optional[ElkLayout] = None
    if layered and layout is None and mode.fallback and elk is not None and not arranged:
        elk_result = layout_elk(payload, prep, elk, sheet_width, sheet_height)
        lay = elk_result.layout
    leaf_by_id: Dict[str, Leaf] = {leaf.id: leaf for leaf in prep.leaves}

    # ---- geometry -------------------------------------------------------
    def leaf_bb(leaf: Leaf) -> Box:
        """Cytoscape's bounding box of a leaf: body, border, miters, one."""
        x, y, _, _ = lay.leaves[leaf.id]
        return leaf_box(leaf, (x, y))

    # The box Cytoscape draws for each compound: its children's boxes,
    # borders and names included, plus the padding, widened for its own
    # name.
    body: Dict[str, Box] = {}
    for group in prep.groups:
        group_body(prep, lay, group, body)

    centers = {leaf.id: (lay.leaves[leaf.id][0], lay.leaves[leaf.id][1]) for leaf in prep.leaves}
    # The line leaves and arrives on the node's outer border.
    polygons: Dict[str, List[Point]] = {}
    for leaf in prep.leaves:
        x, y, w, h = lay.leaves[leaf.id]
        border = float(leaf.data.get("strokeWidth") or 1)
        polygons[leaf.id] = polygon_points(leaf.shape, x, y, w + border, h + border)
    line_width = LINE_LAYERED if layered else LINE_PACKED
    if elk_result is not None:
        edges = _elk_edges(prep, elk_result, centers, polygons, line_width)
    elif layered:
        edges = _layered_edges(prep, lay, centers, polygons, line_width, routing)
    else:
        edges = _packed_edges(prep, centers, polygons, line_width)

    if elk_result is not None:
        placed = _elk_labels(edges, elk_result, m, labels)
    else:
        placed = labels_module.place_labels(
            [e.data for e in edges], {e.data["id"]: e.pieces for e in edges}, {e.data["id"]: e.mid for e in edges},
            [leaf_bb(leaf) for leaf in prep.leaves],
            [(body[g.id], str(g.data.get("label") or "")) for g in prep.groups], show=labels)

    # What the diagram draws of its own on the canvas, measured from where
    # its positions start, and its lines joined to the boxes they end on.
    own_under, own_over, own_boxes = "", "", []
    own_on: Dict[int, str] = {}
    if own:
        origin = own_module.sheet_origin(arranged, {leaf.id: lay.leaves[leaf.id] for leaf in prep.leaves})
        records = {}
        for leaf in prep.leaves:
            x, y, w, h = lay.leaves[leaf.id]
            records[leaf.id] = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        bounds = [body[g.id] for g in prep.groups]
        own_under, taken = own_module.paint(own, origin, records, m, "under", bounds)
        own_boxes += taken
        own_over, taken = own_module.paint(own, origin, records, m, "over", bounds)
        own_boxes += taken
        for i in range(len(bounds)):
            svg_on, taken = own_module.paint(own, origin, records, m, i, bounds)
            own_boxes += taken
            if svg_on:
                own_on[i] = svg_on

    # ---- the drawing's own extent ---------------------------------------
    boxes: List[Box] = [leaf_bb(leaf) for leaf in prep.leaves] + own_boxes
    for group in prep.groups:
        b = body[group.id]
        grow = (group_border(group) + 2) / 2
        boxes.append((b[0] - grow, b[1] - grow, b[2] + grow, b[3] + grow))
    for p in placed:
        boxes.append(p.box)
    for edge in edges:
        for x, y in edge.arrow + edge.points:
            boxes.append((x, y, x, y))
    if not boxes:
        boxes.append((0.0, 0.0, 200.0, 80.0))
    dx1 = min(b[0] for b in boxes)
    dy1 = min(b[1] for b in boxes)
    dx2 = max(b[2] for b in boxes)
    dy2 = max(b[3] for b in boxes)
    draw_w, draw_h = dx2 - dx1, dy2 - dy1

    # ---- the drawing ----------------------------------------------------
    out: List[str] = []

    text = text_el

    # The diagram's own frames on the bare sheet, and what is drawn in
    # them, under everything of the estate's, as the canvas stacks them.
    if own_under:
        out.append(own_under)

    # Boundaries, parents before children: the payload's order, each with
    # the diagram's own frames it holds drawn on it, before its children.
    for index, group in enumerate(prep.groups):
        d = group.data
        x1, y1, x2, y2 = body[group.id]
        fill = d.get("bfill") or BOUNDARY_FILL[min(group.depth - 1, len(BOUNDARY_FILL) - 1)]
        stroke = d.get("bstroke") or "#8f9bb5"
        out.append('<g class="boundary" data-id="%s">' % attr(group.id))
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"%s/>' % (
            fmt(x1), fmt(y1), fmt(x2 - x1), fmt(y2 - y1), fmt(round_rect_radius(x2 - x1, y2 - y1)), fill, stroke,
            fmt(group_border(group)), dash(str(d.get("bdash") or "solid"), False)))
        # The name, on its one line, centered where the stylesheet's
        # margin puts it: twelve in from the outer left edge plus half the
        # name's nominal width.
        label = str(d.get("label") or "")
        lines = boundary_lines(group)
        center_x = x1 - group_border(group) / 2 + 12 + title_width(label) / 2
        top = y1 + BOUNDARY_LABEL_DOWN - BOUNDARY_FONT * len(lines)
        for i, line in enumerate(lines):
            out.append(text(center_x, top + i * BOUNDARY_FONT + BASELINE * BOUNDARY_FONT, line, BOUNDARY_FONT, 600,
                            d.get("bink") or "#3b4a6b", anchor="middle"))
        icon = d.get("icon")
        if icon and icon_loader:
            data = icon_loader(str(icon))
            if data:
                out.append(image(data, x2 - 20 - 7, y1 + 6, 20, 20))
        out.append("</g>")
        if index in own_on:
            out.append(own_on[index])

    # Edges under the nodes, each with its label card, the way Cytoscape
    # draws a label with its edge. On a packed map the lines are context
    # and step back; on a layered diagram they are the reading order.
    placed_by_edge = {p.edge_id: p for p in placed}
    for edge in edges:
        d = edge.data
        style = str(d.get("lineStyle") or "solid")
        # A line steps back on a packed map, and on any drawing when the
        # payload says it is faded: the change picture fades the lines that
        # did not move so the ones that did stand out.
        out.append('<g class="edge" data-id="%s"%s>' % (attr(d["id"]),
                                                       ' opacity="0.45"' if not layered or d.get("faded") else ""))
        if d.get("label"):
            out.append("<title>%s</title>" % escape(str(d["label"])))
        # A line the payload marks heavy, a connection that changed or that
        # a review corrects, is drawn at that width and never thinner than
        # the sheet's lines.
        width = max(line_width, float(d.get("strokeWidth") or 0))
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s"%s/>' % (edge.path, EDGE, fmt(width),
                                                                                 dash(style, True)))
        if edge.arrow:
            out.append('<path d="M%s %s L%s %s L%s %s Z" fill="%s"/>' % (
                *(fmt(v) for pt in edge.arrow for v in pt), EDGE))
        out.append("</g>")
        p = placed_by_edge.get(d["id"])
        if p:
            tw = m.width(p.text, "Geist", 500, 10)
            cw, ch = tw + 6, 16
            # Turned along its run: the rotation about (x, y) as the matrix
            # the run's direction gives outright, since an angle would come
            # from the C library's atan2.
            transform = ' transform="matrix(%s %s %s %s %s %s)"' % (
                fmt(p.ux), fmt(p.uy), fmt(0.0 - p.uy), fmt(p.ux),
                fmt(p.x - p.x * p.ux + p.y * p.uy), fmt(p.y - p.x * p.uy - p.y * p.ux)) if p.turned else ""
            out.append('<g class="edge-label" data-edge="%s"%s>' % (attr(d["id"]), transform))
            out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="3" fill="#ffffff" fill-opacity="0.96" '
                       'stroke="#cdd5e1" stroke-width="1"/>' % (fmt(p.x - cw / 2), fmt(p.y - ch / 2), fmt(cw), fmt(ch)))
            out.append(text(p.x, p.y - ch / 2 + BASELINE * 10 + 3, p.text, 10, 500, "#3f4a5c", anchor="middle"))
            out.append("</g>")

    # Nodes.
    for leaf in prep.leaves:
        d = leaf.data
        x, y, w, h = lay.leaves[leaf.id]
        faded = ' opacity="0.55"' if d.get("faded") else ""
        out.append('<g class="node" data-id="%s" data-type="%s"%s>' % (attr(leaf.id), attr(d.get("entityType") or ""),
                                                                        faded))
        out.append("<title>%s</title>" % escape(str(d.get("label") or "")))
        out.append('%s fill="%s" stroke="%s" stroke-width="%s"%s/>' % (
            shape_path(leaf.shape, x, y, w, h), d.get("fill") or "#ffffff", d.get("stroke") or "#8f9bb5",
            fmt(float(d.get("strokeWidth") or 1)), dash(str(d.get("dash") or "solid"), False)))
        # The name, wrapped the way Cytoscape wraps it, moved up for the
        # technology line and left for the mark.
        tech = str(d.get("tech") or "")
        margin_y = -(11 / 2) if tech else 0
        margin_x = -10 if leaf.corner == "icon" else -4 if leaf.corner in ("glyph", "ticon") else 0
        max_w = 132 - (20 if leaf.corner == "icon" else 8 if leaf.corner in ("glyph", "ticon") else 0)
        lines = m.wrap(str(d.get("label") or ""), max_w, "Geist", 600, 12)
        top = y + margin_y - len(lines) * 12 / 2
        for i, line in enumerate(lines):
            out.append(text(x + margin_x, top + i * 12 + BASELINE * 12, line, 12, 600, d.get("ink") or "#0f172a",
                            anchor="middle"))
        if tech:
            shown = m.fit(tech, w - 10, "Geist", 500, TECH_FONT)
            out.append(text(x, y + h / 2 - 5.5, shown, TECH_FONT, 500, INK_SOFT, anchor="middle"))
        # The corner: the provider's mark, the component's glyph, or the
        # type's own small mark.
        x2, y1 = x + w / 2, y - h / 2
        rhomboid = leaf.shape == "rhomboid"
        if leaf.corner == "icon" and icon_loader:
            data = icon_loader(str(d.get("icon") or ""))
            if data:
                out.append(image(data, x2 - 18 + (-16 if rhomboid else -4), y1 + 4, 18, 18))
        elif leaf.corner == "glyph":
            path = GLYPH_PATHS[str(d.get("componentCategory") or "")]
            gx, gy = x2 - 13 + (-16 if rhomboid else -5), y1 + 5
            out.append('<svg x="%s" y="%s" width="13" height="13" viewBox="0 0 16 16" opacity="0.9">'
                       '<path d="%s" fill="none" stroke="#3f4a5c" stroke-width="1.5" stroke-linecap="round" '
                       'stroke-linejoin="round"/></svg>' % (fmt(gx), fmt(gy), path))
        elif leaf.corner == "ticon":
            body_svg = TYPE_ICON_BODIES[str(d.get("entityType") or "")]
            gx, gy = x2 - 12 - 6, y1 + 5
            out.append('<svg x="%s" y="%s" width="12" height="12" viewBox="0 0 24 24" opacity="0.85" fill="none" '
                       'stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">%s</svg>' % (
                           fmt(gx), fmt(gy), d.get("stroke") or "#8f9bb5", body_svg))
        out.append("</g>")

    # And the rest of its own, over the boxes.
    if own_over:
        out.append(own_over)

    drawing = "\n".join(out)
    # The sheet says which path drew it: arranged by hand, packed,
    # concentric, cose, elk, dagre, or dagre standing in for the ELK the app
    # would have used.
    drawn_by = ("arranged" if arranged else "cose" if organic
                else "concentric" if not layered and mode.kind == "wheel"
                else "packed" if not layered else "elk" if elk_result is not None
                else "dagre-for-elk" if mode.fallback else "dagre")
    counts = payload.get("counts") or {}
    facts = "%d nodes · %d edges" % (counts.get("nodes", 0), counts.get("edges", 0)) if counts else ""
    if scene_out is not None:
        scene_out.append(_scene(prep, lay, body, edges, placed, (dx1, dy1, dx2, dy2), layered, drawn_by, m))
    return frame_sheet(payload, m, drawing, (dx1, dy1, dx2, dy2), drawn_by, facts, sheet=sheet, pad=28,
                       font_loader=font_loader, font_url_prefix=font_url_prefix, model_name=model_name, date=date)


def _scene(prep: Prepared, lay, body: Dict[str, Box], edges: List["_Edge"], placed: List[labels_module.Placed],
           extent: Box, layered: bool, drawn_by: str, m: Metrics) -> Scene:
    """What the painter just drew, as records: the same boxes, colors,
    points and labels the SVG got, so another painter cannot drift from
    this one."""
    boundaries = []
    for group in prep.groups:
        d = group.data
        boundaries.append(SceneBoundary(
            group.id, body[group.id], d.get("bfill") or BOUNDARY_FILL[min(group.depth - 1, len(BOUNDARY_FILL) - 1)],
            d.get("bstroke") or "#8f9bb5", float(group_border(group)), str(d.get("bdash") or "solid"),
            boundary_lines(group), d.get("bink") or "#3b4a6b", group.depth, group.parent))
    placed_by_edge = {p.edge_id: p for p in placed}
    scene_edges = []
    for edge in edges:
        d = edge.data
        p = placed_by_edge.get(d["id"])
        # The line as drawn stops short of the tip under the arrow head; a
        # connector draws its own head, so it runs to the tip itself.
        points = list(edge.points[:-1]) + [edge.arrow[0]] if edge.arrow and edge.points else list(edge.points)
        scene_edges.append(SceneEdge(str(d["id"]), str(d["source"]), str(d["target"]), points, "Q" in edge.path,
                                     str(d.get("lineStyle") or "solid"), p.text if p else "",
                                     (p.x, p.y) if p else None, p.box if p else None, str(d.get("ref") or ""),
                                     str(d.get("kind") or "")))
    nodes = []
    for leaf in prep.leaves:
        d = leaf.data
        x, y, w, h = lay.leaves[leaf.id]
        nodes.append(SceneNode(leaf.id, leaf.shape, x, y, w, h, d.get("fill") or "#ffffff",
                               d.get("stroke") or "#8f9bb5", float(d.get("strokeWidth") or 1),
                               str(d.get("dash") or "solid"), str(d.get("label") or ""), d.get("ink") or "#0f172a",
                               str(d.get("tech") or ""), bool(d.get("faded")), str(d.get("entityType") or ""),
                               leaf.parent))
    return Scene(extent, boundaries, scene_edges, nodes, layered, drawn_by)


def _elk_edges(prep: Prepared, result: ElkLayout, centers: Dict[str, Point], polygons: Dict[str, List[Point]],
               line_width: float) -> List[_Edge]:
    """The edges as ELK routed them; one ELK gave no section to is drawn as
    a bezier bundle, the way a free edge is on the dagre path."""
    edges = [_Edge(e) for e in prep.edges if e["source"] in centers and e["target"] in centers]
    free: Dict[Tuple[str, str], List[_Edge]] = {}
    for edge in edges:
        route = result.routes.get(edge.data["id"])
        if route is None:
            key = tuple(sorted((edge.data["source"], edge.data["target"])))
            free.setdefault(key, []).append(edge)
            continue
        _orthogonal_fixed(edge, route, line_width)
    for key, bundle in free.items():
        for i, edge in enumerate(bundle):
            _bezier(edge, key, i, len(bundle), centers, polygons, line_width)
    return edges


def _orthogonal_fixed(edge: _Edge, route: ElkRoute, line_width: float) -> None:
    """An edge drawn where ELK put it: from the point it leaves its source,
    through its bends, to the point it arrives, the corners rounded as the
    router's are and the arrow head on the last piece. The ports are ELK's,
    which is the half of its placement dagre never had."""
    pts = list(route.bends)
    start = route.start
    edge.arrow, end = _head(edge, route.end, pts[-1] if pts else start, line_width)
    parts = ["M%s %s" % (fmt(start[0]), fmt(start[1]))]
    prev = start
    for i, p in enumerate(pts):
        nxt = pts[i + 1] if i + 1 < len(pts) else end
        corner = round_corner(prev, p, nxt, SEGMENT_RADIUS)
        if corner is None:
            parts.append("L%s %s" % (fmt(p[0]), fmt(p[1])))
        else:
            parts.append("L%s %s" % (fmt(corner.tin[0]), fmt(corner.tin[1])))
            parts.append("A%s %s 0 0 %d %s %s" % (fmt(corner.radius), fmt(corner.radius), corner.sweep,
                                                  fmt(corner.tout[0]), fmt(corner.tout[1])))
        prev = p
    parts.append("L%s %s" % (fmt(end[0]), fmt(end[1])))
    edge.path = " ".join(parts)
    chain = [start] + pts + [end]
    edge.pieces = [p for p in (labels_module.piece(*chain[i], *chain[i + 1]) for i in range(len(chain) - 1)) if p]
    edge.points = chain
    # The midpoint, halfway along the line as drawn.
    lengths = [math.hypot(chain[i + 1][0] - chain[i][0], chain[i + 1][1] - chain[i][1]) for i in range(len(chain) - 1)]
    half = sum(lengths) / 2
    edge.mid = chain[0]
    for i, length in enumerate(lengths):
        if half <= length or i == len(lengths) - 1:
            t = half / length if length else 0
            edge.mid = (chain[i][0] + (chain[i + 1][0] - chain[i][0]) * t, chain[i][1] + (chain[i + 1][1] - chain[i][1]) * t)
            break
        half -= length


def _elk_labels(edges: List[_Edge], result: ElkLayout, m: Metrics, show: Optional[bool]) -> List[labels_module.Placed]:
    """The labels where ELK placed them, upright, each on the edge it was
    given for; all of them under the app's budget and none above it, as
    `showElkLabels` does."""
    labeled = [e for e in edges if e.data["id"] in result.labels]
    if show is None:
        show = len(labeled) <= labels_module.LABEL_BUDGET
    if not show:
        return []
    placed = []
    for edge in labeled:
        text = str(edge.data.get("label") or "")
        x, y = result.labels[edge.data["id"]]
        cw, ch = m.width(text, "Geist", 500, 10) + 6, 16
        placed.append(labels_module.Placed(edge.data["id"], text, x, y, False, 1.0, 0.0,
                                           (x - cw / 2, y - ch / 2, x + cw / 2, y + ch / 2)))
    return placed


def frame_sheet(payload: dict, m: Metrics, drawing: str, extent: Box, drawn_by: str, facts: str, *, sheet: bool,
                pad: float, font_loader: Optional[IconLoader], font_url_prefix: str, model_name: str, date: str,
                legend: Optional[List[dict]] = None) -> str:
    """The drawing on its sheet, or alone with `pad` around it: the title
    block above, the legend and the footer below, the faces named or
    embedded, and `data-layout` saying which path drew it. `legend` is the
    rows to show; left out, they are read off the payload's legend the way
    a view's are. The timeline and sequence painters bring their own."""
    dx1, dy1, dx2, dy2 = extent
    draw_w, draw_h = dx2 - dx1, dy2 - dy1
    text = text_el
    if not sheet:
        width, height = draw_w + 2 * pad, draw_h + 2 * pad
        head = ""
        foot = ""
        offset = (pad - dx1, pad - dy1)
    else:
        width = max(draw_w + 2 * pad, 1100)
        title = str(payload.get("title") or "Architecture")
        desc_lines = m.wrap(str(payload.get("description") or "").strip(), width - 2 * pad, "Geist", 400, 14)[:4]
        if desc_lines == [""]:
            desc_lines = []
        head_h = pad + 30 + (len(desc_lines) * 20 + 6 if desc_lines else 0) + 18
        rows = legend if legend is not None else legend_rows(payload)
        foot_h = (len(rows) * 22 + 14 if rows else 0) + 30 + pad
        height = head_h + draw_h + foot_h
        parts = [text(pad, pad + 24, title, 24, 600, "#101828")]
        said = "   ·   ".join(f for f in (model_name, date, facts) if f)
        if said:
            parts.append(text(width - pad, pad + 22, said, 12, 400, "#495366", MONO, anchor="end"))
        for i, line in enumerate(desc_lines):
            parts.append(text(pad, pad + 30 + 20 * (i + 1), line, 14, 400, "#343d50"))
        parts.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#d2dae5" stroke-width="1"/>' % (
            fmt(pad), fmt(head_h - 10), fmt(width - pad), fmt(head_h - 10)))
        head = "\n".join(parts)
        y = head_h + draw_h + 14
        parts = ['<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#d2dae5" stroke-width="1"/>' % (
            fmt(pad), fmt(y), fmt(width - pad), fmt(y))]
        y += 10
        for row in rows:
            x = pad
            cap = row["cap"].upper()
            parts.append(text(x, y + 14, cap, 10.5, 500, "#2841b9", MONO))
            x += m.width(cap, "Geist Mono", 500, 10.5) + 14
            for key in row["keys"]:
                parts.append(legend_key(key, x, y + 3))
                x += 26
                parts.append(text(x, y + 14, key["text"], 12, 400, "#343d50"))
                x += m.width(key["text"], "Geist", 400, 12) + 18
            y += 22
        parts.append(text(pad, height - pad + 6,
                          "Generated from the model by architecture-as-code · %s · edit the model, not the picture"
                          % str(payload.get("viewId") or ""), 11, 400, "#495366", MONO))
        foot = "\n".join(parts)
        offset = ((width - draw_w) / 2 - dx1, head_h - dy1)

    style = font_face_css(font_loader) if font_loader else font_face_urls(font_url_prefix) if font_url_prefix else ""
    doc = [
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="%s" height="%s" '
        'viewBox="0 0 %s %s" font-family="%s" data-layout="%s">' % (
            fmt(width), fmt(height), fmt(width), fmt(height), attr(SANS), drawn_by),
        "<title>%s</title>" % escape(str(payload.get("title") or "")),
    ]
    if style:
        doc.append("<style>%s</style>" % style)
    # The sheet's backing, white: without it a viewer that shows transparency
    # as black (resvg's PNG, a dark image pane) showed black, and this line
    # had doubled its percent signs as if it went through `%` formatting.
    doc.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    if head:
        doc.append('<g class="head">%s</g>' % head)
    doc.append('<g class="drawing" transform="translate(%s %s)">\n%s\n</g>' % (fmt(offset[0]), fmt(offset[1]), drawing))
    if foot:
        doc.append('<g class="foot">%s</g>' % foot)
    doc.append("</svg>")
    return "\n".join(doc) + "\n"


#: The frame under its older name, for the callers in this module.
_frame = frame_sheet


def paint_tiles(lay: TileLayout, m: Metrics) -> str:
    """The tile map in host coordinates, the way the browser paints the
    app's HTML: a band's rule, its name, gloss and count; a card's border
    inside its box with the name beside the count; a tile's border at the
    pixel Chrome snaps it to, the name on at most two lines, the technology
    line under it; each run of text on the baseline its line box gives it.
    Grouped the way the DOM is, each tile and card carrying its id."""
    out: List[str] = []

    def run(t: TileText, fill: str, anchor: str = "start") -> None:
        lh = line_height(t.face)
        base = baseline(m, t.face)
        x = t.x if anchor == "start" else t.x + t.w
        spacing = ' letter-spacing="%s"' % fmt(t.face.spacing) if t.face.spacing else ""
        for i, line in enumerate(t.lines):
            out.append(text_el(x, t.y + i * lh + base, line, t.face.size, t.face.weight, fill, anchor=anchor,
                               extra=spacing))

    def grid(g: Grid) -> None:
        for tl in g.tiles:
            d = tl.data
            b = tl.border
            out.append('<g class="tile" data-id="%s" data-type="%s"%s>' % (
                attr(tl.id), attr(d.get("entityType") or ""), ' opacity="0.6"' if d.get("faded") else ""))
            key = str(d.get("styleKey") or "")
            out.append("<title>%s</title>" % escape(str(d.get("label") or "") + (" · " + key if key and key != "default"
                                                                                else "")))
            # CSS draws the border inside the box: the stroke's centerline
            # sits half a border in, and the corner's radius shrinks with it.
            out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                fmt(tl.x + b / 2), fmt(tl.y + b / 2), fmt(tl.w - b), fmt(tl.h - b), fmt(max(0.0, TILE_RADIUS - b / 2)),
                d.get("fill") or PANEL, d.get("stroke") or "#9aa3b5", fmt(b)))
            run(tl.name, INK)
            if tl.tech:
                run(tl.tech, INK_3)
            out.append("</g>")

    def cards(cs: Cards) -> None:
        for c in cs.cards:
            out.append('<g class="card" data-id="%s">' % attr(c.id))
            out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                fmt(c.x + CARD_BORDER / 2), fmt(c.y + CARD_BORDER / 2), fmt(c.w - CARD_BORDER), fmt(c.h - CARD_BORDER),
                fmt(CARD_RADIUS - CARD_BORDER / 2), PANEL, RULE_2, fmt(CARD_BORDER)))
            run(c.name, INK)
            run(c.count, INK_3, anchor="end")
            if c.grid:
                grid(c.grid)
            if c.cards:
                cards(c.cards)
            out.append("</g>")

    for band in lay.bands:
        out.append('<g class="band" data-id="%s">' % attr(band.id))
        if not band.first:
            out.append('<rect x="%s" y="%s" width="%s" height="1" fill="%s"/>' % (fmt(band.x), fmt(band.y), fmt(band.w),
                                                                                RULE))
        run(band.name, INK)
        if band.gloss:
            run(band.gloss, INK_2)
        run(band.count, INK_3)
        if band.cards:
            cards(band.cards)
        if band.grid:
            grid(band.grid)
        out.append("</g>")
    if lay.cards:
        cards(lay.cards)
    if lay.loose:
        grid(lay.loose)
    return "\n".join(out)


def image(data: bytes, x: float, y: float, w: float, h: float) -> str:
    """A mark as its own document inside the picture, so an icon set's
    gradient ids cannot collide with another's."""
    head = data.lstrip()[:5]
    mime = "image/svg+xml" if head.startswith((b"<svg", b"<?xml", b"<!--")) else "image/png"
    return '<image x="%s" y="%s" width="%s" height="%s" href="data:%s;base64,%s"/>' % (
        fmt(x), fmt(y), fmt(w), fmt(h), mime, base64.b64encode(data).decode("ascii"))


def font_face_css(loader: IconLoader) -> str:
    rules = []
    for (family, weight), name in FONT_FILES.items():
        data = loader(name)
        if not data:
            continue
        rules.append('@font-face{font-family:"%s";font-weight:%d;src:url(data:font/woff2;base64,%s) format("woff2")}'
                     % (family, weight, base64.b64encode(data).decode("ascii")))
    return "".join(rules)


def font_face_urls(prefix: str) -> str:
    return "".join('@font-face{font-family:"%s";font-weight:%d;src:url(%s%s) format("woff2")}'
                   % (family, weight, prefix, name) for (family, weight), name in FONT_FILES.items())


def legend_rows(payload: dict) -> List[dict]:
    """The export's legend: type, the dimension, boundaries, lines."""
    legend = payload.get("legend") or {}
    rows = []
    types = legend.get("types") or []
    if types:
        rows.append({"cap": "type", "keys": [
            {"kind": "shape", "type": t["key"], "fill": t["fill"], "stroke": t["stroke"], "dash": "solid",
             "width": 1.4, "text": "%s · %d" % (t["label"], t["count"])} for t in types]})
    dim = legend.get("dimension") or {}
    keys = dim.get("keys") or []
    if dim.get("name") and len(keys) > 1 and dim.get("role") in ("ordinal", "status"):
        sample = types[0]["key"] if types else "systems"
        rows.append({"cap": str(dim["name"]).replace("_", " "), "keys": [
            {"kind": "shape", "type": sample, "fill": k["fill"], "stroke": k["stroke"], "dash": k.get("dash") or "solid",
             "width": k.get("width") or 1.4, "text": "%s · %d" % (key_label(k["value"]), k["count"])}
            for k in keys]})
    bounds = legend.get("boundaries") or []
    if bounds:
        rows.append({"cap": "boundaries", "keys": [
            {"kind": "box", "fill": b["fill"], "stroke": b["stroke"], "dash": b.get("dash") or "solid", "text": b["key"]}
            for b in bounds]})
    said = set()
    line_keys = []
    for e in legend.get("edges") or []:
        word = edge_word(e["kind"])
        if (e["style"], word) in said:
            continue
        said.add((e["style"], word))
        line_keys.append({"kind": "line", "dash": e["style"], "text": word, "bare": e["kind"] in HEADLESS})
    if line_keys:
        rows.append({"cap": "lines", "keys": line_keys})
    return rows


def legend_key(key: dict, x: float, y: float) -> str:
    """One key on the sheet, 20 wide: the entity's own shape for a type, a
    box for a boundary, a line with its arrow for a relation."""
    if key["kind"] == "line":
        head = ('<path d="M16 4l5 3-5 3" fill="none" stroke="%s" stroke-width="1.6"/>' % EDGE if key.get("open")
                else "" if key.get("bare") else '<path d="M16 4l5 3-5 3z" fill="%s"/>' % EDGE)
        return ('<g transform="translate(%s %s)"><path d="M0 7h20" fill="none" stroke="%s" stroke-width="1.6"%s/>'
                '%s</g>' % (fmt(x), fmt(y), EDGE, dash(key["dash"], True), head))
    if key["kind"] == "dot":
        return ('<g transform="translate(%s %s)"><circle cx="10" cy="7" r="4" fill="%s" stroke="%s" '
                'stroke-width="1.5"/></g>' % (fmt(x), fmt(y), key["fill"], key["stroke"]))
    if key["kind"] == "box":
        return ('<g transform="translate(%s %s)"><rect x="1" y="1" width="18" height="12" rx="2" fill="%s" '
                'stroke="%s" stroke-width="1.4"%s/></g>' % (fmt(x), fmt(y), key["fill"], key["stroke"],
                                                            dash(key["dash"], False)))
    from .shapes import shape_of
    shape = SHAPE_KEYS.get(shape_of(key["type"])) or SHAPE_KEYS["round-rectangle"]
    return '<g transform="translate(%s %s)" fill="%s" stroke="%s" stroke-width="%s"%s>%s</g>' % (
        fmt(x), fmt(y), key["fill"], key["stroke"], fmt(float(key.get("width") or 1.4)), dash(key["dash"], False),
        shape)
