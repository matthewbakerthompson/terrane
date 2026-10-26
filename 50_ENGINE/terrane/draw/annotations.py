"""The diagram's own shapes on the engine's picture, as the canvas draws
them: `canvas/engine.js`, from the same numbers.

A diagram drawn on the canvas lists what it draws of its own under
`annotations:` (`terrane.annotations`). The app draws them with maxGraph
around the estate's boundaries and boxes: a frame on the bare sheet or
around boundaries under all of the estate; a frame wholly inside a boundary
just above the innermost that holds it and under the boundaries inside it;
whatever sits in a frame with the frame; and every other shape, note, text
and line over everything. The
picture keeps the same order, the same paths for the same shapes, the same
six fills and their edges, and the words wrapped at the same widths, so what
was drawn on the sheet is what every export shows.

Places are measured from the sheet's corner, where the drawing's own
positions start: nought for an arranged drawing (`terrane.draw.arranged`
lays one from there, as `arrangeKept()` does), and for one the layout
placed the least corner of its boxes, as the canvas takes it.
"""

from __future__ import annotations

import math
from typing import Dict, List, Mapping, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from ..annotations import FILLS, TEXT_SIZES
from .metrics import Metrics

Box = Tuple[float, float, float, float]
Point = Tuple[float, float]

#: The shapes as fractions of their box, `OWN_PATHS` in engine.js: M and L
#: a point, Q a control and a point, C two controls and a point, Z the close.
K = 0.27614
PATHS: Dict[str, List[tuple]] = {
    "rectangle": [("M", 0, 0), ("L", 1, 0), ("L", 1, 1), ("L", 0, 1), ("Z",)],
    "ellipse": [("M", 0.5, 0), ("C", 0.5 + K, 0, 1, 0.5 - K, 1, 0.5), ("C", 1, 0.5 + K, 0.5 + K, 1, 0.5, 1),
                ("C", 0.5 - K, 1, 0, 0.5 + K, 0, 0.5), ("C", 0, 0.5 - K, 0.5 - K, 0, 0.5, 0), ("Z",)],
    "diamond": [("M", 0.5, 0), ("L", 1, 0.5), ("L", 0.5, 1), ("L", 0, 0.5), ("Z",)],
    "hexagon": [("M", 0, 0.5), ("L", 0.25, 0), ("L", 0.75, 0), ("L", 1, 0.5), ("L", 0.75, 1), ("L", 0.25, 1), ("Z",)],
    "cylinder": [("M", 0, 0.12), ("C", 0, -0.04, 1, -0.04, 1, 0.12), ("L", 1, 0.88), ("C", 1, 1.04, 0, 1.04, 0, 0.88),
                 ("Z",), ("M", 0, 0.12), ("C", 0, 0.28, 1, 0.28, 1, 0.12)],
    "cloud": [("M", 0.25, 0.25), ("C", 0.05, 0.25, 0, 0.5, 0.16, 0.55), ("C", 0, 0.66, 0.18, 0.9, 0.31, 0.8),
              ("C", 0.4, 1, 0.7, 1, 0.8, 0.8), ("C", 1, 0.8, 1, 0.6, 0.875, 0.5), ("C", 1, 0.3, 0.8, 0.1, 0.625, 0.2),
              ("C", 0.5, 0.05, 0.3, 0.05, 0.25, 0.25), ("Z",)],
    "document": [("M", 0, 0), ("L", 1, 0), ("L", 1, 0.85), ("Q", 0.75, 0.7, 0.5, 0.85), ("Q", 0.25, 1, 0, 0.85), ("Z",)],
    "person": [("M", 0.5, 0.02), ("C", 0.6, 0.02, 0.68, 0.1, 0.68, 0.2), ("C", 0.68, 0.3, 0.6, 0.38, 0.5, 0.38),
               ("C", 0.4, 0.38, 0.32, 0.3, 0.32, 0.2), ("C", 0.32, 0.1, 0.4, 0.02, 0.5, 0.02), ("Z",),
               ("M", 0.12, 1), ("L", 0.12, 0.72), ("C", 0.12, 0.52, 0.3, 0.44, 0.5, 0.44),
               ("C", 0.7, 0.44, 0.88, 0.52, 0.88, 0.72), ("L", 0.88, 1), ("Z",)],
    "callout": [("M", 0, 0), ("L", 1, 0), ("L", 1, 0.72), ("L", 0.42, 0.72), ("L", 0.22, 1), ("L", 0.26, 0.72),
                ("L", 0, 0.72), ("Z",)],
}

#: The fill each kind starts with; text has none.
ROLE_FILL = {"note": "yellow", "shape": "white", "frame": "white"}
INK = "#272b33"
TEXT_INK = "#3b4049"
LINE_INK = "#5b6577"
#: The leading the canvas sets its own words at.
LEADING = 1.32
#: Where a line of words has its baseline, as a share of its size: Geist's
#: ascent, the figure svg.py writes names with.
BASELINE = 0.855
#: How far in from a box's edge its words start, by kind, as maxGraph's
#: spacing puts them: a frame's name is twelve in and eight down.
PADDING = {"frame": (12, 8), "note": (10, 10), "text": (2, 2), "shape": (8, 8)}


def fmt(value: float) -> str:
    return ("%.2f" % value).rstrip("0").rstrip(".") if value != int(value) else str(int(value))


def path_data(shape: str, x: float, y: float, w: float, h: float) -> str:
    """A shape's outline as an SVG path, in the box at (x, y)."""
    parts = []
    for op in PATHS.get(shape) or PATHS["rectangle"]:
        if op[0] == "Z":
            parts.append("Z")
            continue
        nums = [fmt(x + v * w) if i % 2 == 0 else fmt(y + v * h) for i, v in enumerate(op[1:])]
        parts.append(op[0] + " ".join(nums))
    return " ".join(parts)


def layer_of(item: Mapping, boxes: Mapping[str, Box], bounds: Sequence[Box]):
    """Where the canvas stacks it: `"under"` the estate, `"over"`
    everything, or the index in `bounds` of the boundary it is drawn just
    above. A frame, and what sits in it, go by the outermost frame's place:
    inside a boundary's box, above the innermost holding it, which in a list
    of boundaries outermost first is the last that does; on the bare sheet
    or around boundaries, under them. A line is over."""
    if item.get("role") == "line":
        return "over"
    inside = list(item.get("in") or [])
    if item.get("role") != "frame" and not inside:
        return "over"
    top = str(inside[0]) if inside else str(item["key"])
    box = boxes.get(top)
    held = [i for i, b in enumerate(bounds)
            if box and box[0] >= b[0] and box[1] >= b[1] and box[2] <= b[2] and box[3] <= b[3]]
    return held[-1] if held else "under"


def sheet_origin(arranged: bool, leaves: Mapping[str, Tuple[float, float, float, float]]) -> Point:
    """Where the drawing's positions start. `leaves` is each box's center
    and size, as the layout gives them."""
    if arranged or not leaves:
        return (0.0, 0.0)
    return (min(round(x - w / 2) for x, _, w, _ in leaves.values()),
            min(round(y - h / 2) for _, y, _, h in leaves.values()))


def place(items: Sequence[Mapping], origin: Point) -> Dict[str, Box]:
    """Each box of the diagram's own where it is on the sheet: its corner in
    the innermost frame it sits in, that frame's corner added, and so out to
    the sheet's."""
    by_key = {str(a["key"]): a for a in items if a.get("role") != "line"}
    corners: Dict[str, Point] = {}

    def corner(a: Mapping, depth: int = 0) -> Point:
        key = str(a["key"])
        if key in corners:
            return corners[key]
        inside = list(a.get("in") or [])
        at = a.get("at") or (0, 0)
        if inside and inside[-1] in by_key and depth < 32:
            fx, fy = corner(by_key[inside[-1]], depth + 1)
            got = (fx + float(at[0]), fy + float(at[1]))
        else:
            got = (origin[0] + float(at[0]), origin[1] + float(at[1]))
        corners[key] = got
        return got

    out: Dict[str, Box] = {}
    for key, a in by_key.items():
        x, y = corner(a)
        w, h = a.get("size") or (120, 64)
        out[key] = (x, y, x + float(w), y + float(h))
    return out


def _look(item: Mapping) -> Tuple[str, str, str, float]:
    """Its fill, its edge, its dash and the size of its words."""
    role, look = item.get("role"), item.get("look") or {}
    name = None if role == "text" else (look.get("fill") if look.get("fill") in FILLS else ROLE_FILL.get(role, "white"))
    fill = FILLS[name][0] if name else "none"
    edge = "none" if role == "text" or look.get("line") == "none" else FILLS[name][1]
    dash = ' stroke-dasharray="6 4"' if look.get("line") == "dashed" else ""
    size = float(TEXT_SIZES.get(look.get("text"), 12 if role == "frame" else 13))
    return fill, edge, dash, size


def _words(item: Mapping, box: Box, m: Metrics, size: float) -> List[str]:
    role = item.get("role")
    label = str(item.get("label") or "")
    if not label:
        return []
    x1, y1, x2, y2 = box
    px, py = PADDING.get(str(role), (8, 8))
    weight = 600 if role == "frame" else 400
    # Wrapped two pixels wider than the room inside the padding: maxGraph
    # lays a wrapped label out that much wider than its cell, and a note's
    # "Guardrails: every account is", 164.3 at 13, kept its "is" there.
    lines = m.wrap(label, max(1.0, x2 - x1 - 2 * px + 2), "Geist", weight, size)
    step = size * LEADING
    first = size * (LEADING - 1) / 2 + BASELINE * size
    if role == "shape":
        x, anchor = (x1 + x2) / 2, ' text-anchor="middle"'
        top = (y1 + y2) / 2 - len(lines) * step / 2
    else:
        x, anchor = x1 + px, ""
        top = y1 + py
    fill = TEXT_INK if role == "text" else INK
    out = []
    for i, line in enumerate(lines):
        if top + i * step + step > y2 + 0.5 and role != "text" and i:
            break  # what does not fit is clipped on the canvas too
        out.append('<text x="%s" y="%s" font-size="%s" font-weight="%d" fill="%s"%s>%s</text>' % (
            fmt(x), fmt(top + first + i * step), fmt(size), weight, fill, anchor, escape(line)))
    return out


def _box(item: Mapping, box: Box, m: Metrics) -> str:
    role = item.get("role")
    fill, edge, dash, size = _look(item)
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    out = ['<g class="own" data-key="%s" data-role="%s">' % (escape(str(item["key"]), {'"': "&quot;"}), role)]
    paint = 'fill="%s" stroke="%s" stroke-width="1.25"%s' % (fill, edge, dash)
    if role == "frame" or (role == "shape" and item.get("shape") == "rounded"):
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" %s/>' % (
            fmt(x1), fmt(y1), fmt(w), fmt(h), "8" if role == "frame" else "10", paint))
    elif role == "shape":
        out.append('<path d="%s" %s/>' % (path_data(str(item.get("shape") or "rectangle"), x1, y1, w, h), paint))
    elif role == "note":
        out.append('<rect x="%s" y="%s" width="%s" height="%s" %s/>' % (fmt(x1), fmt(y1), fmt(w), fmt(h), paint))
    out.extend(_words(item, box, m, size))
    out.append("</g>")
    return "\n".join(out)


def _clip(box: Box, inner: Point, outer: Point, shape: str = "") -> Point:
    """Where the line from a box's middle toward a point leaves its outline,
    as maxGraph's perimeters put a joined line's end: an ellipse's and a
    diamond's own, every other shape's box."""
    x1, y1, x2, y2 = box
    dx, dy = outer[0] - inner[0], outer[1] - inner[1]
    if not dx and not dy:
        return inner
    hw, hh = (x2 - x1) / 2, (y2 - y1) / 2
    if shape == "ellipse":
        t = 1 / math.sqrt((dx / hw) ** 2 + (dy / hh) ** 2)
    elif shape == "diamond":
        t = 1 / (abs(dx) / hw + abs(dy) / hh)
    else:
        t = min(hw / abs(dx) if dx else math.inf, hh / abs(dy) if dy else math.inf)
    return (inner[0] + dx * t, inner[1] + dy * t)


def square(a: Box, b: Box) -> List[Point]:
    """The turns of a square line between two boxes (a point is a box of no
    size): across the middle of the gap between them, or down it, whichever
    gap is the wider, and none when they overlap both ways, which leaves the
    line straight. `squareTurns` in engine.js, the same arithmetic."""
    ca = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)
    cb = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    gx = b[0] - a[2] if b[0] >= a[2] else a[0] - b[2] if a[0] >= b[2] else -1.0
    gy = b[1] - a[3] if b[1] >= a[3] else a[1] - b[3] if a[1] >= b[3] else -1.0
    if gx < 0 and gy < 0:
        return []
    if gx >= gy:
        x = (a[2] + b[0]) / 2 if b[0] >= a[2] else (b[2] + a[0]) / 2
        return [(x, ca[1]), (x, cb[1])]
    y = (a[3] + b[1]) / 2 if b[1] >= a[3] else (b[3] + a[1]) / 2
    return [(ca[0], y), (cb[0], y)]


def _line(item: Mapping, ends: Tuple[object, object], m: Metrics,
          shapes: Tuple[str, str] = ("", "")) -> Tuple[str, List[Box]]:
    look = item.get("look") or {}

    def boxed(end: object) -> Box:
        if isinstance(end, tuple) and len(end) == 4:
            return end  # type: ignore[return-value]
        return (end[0], end[1], end[0], end[1])  # type: ignore[index]

    def middle(end: object) -> Point:
        b = boxed(end)
        return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)

    a, b = ends
    ca, cb = middle(a), middle(b)
    route = str(item.get("route") or "straight")
    turns = square(boxed(a), boxed(b)) if route in ("square", "curved") else []
    # Each end where the line toward its first turn leaves the outline, as
    # maxGraph's perimeters put it.
    first, last = (turns[0] if turns else cb), (turns[-1] if turns else ca)
    p1 = _clip(a, ca, first, shapes[0]) if isinstance(a, tuple) and len(a) == 4 else ca
    p2 = _clip(b, cb, last, shapes[1]) if isinstance(b, tuple) and len(b) == 4 else cb
    pts = [p1] + turns + [p2]
    dash = ' stroke-dasharray="6 4"' if look.get("line") == "dashed" else ""
    out = ['<g class="own" data-key="%s" data-role="line">' % escape(str(item["key"]), {'"': "&quot;"})]
    # Each head along the run it ends: the last piece, or the first.
    heads = {"end": [(p2, pts[-2])], "both": [(p2, pts[-2]), (p1, pts[1])], "none": []}[str(item.get("ends") or "end")]
    # The line stops where each head's base is, so its end does not show
    # past the point of the arrow.
    line = list(pts)
    for tip, toward in heads:
        ux, uy = toward[0] - tip[0], toward[1] - tip[1]
        n = math.hypot(ux, uy) or 1.0
        base = (tip[0] + ux / n * 7, tip[1] + uy / n * 7)
        line[-1 if tip == p2 else 0] = base
    if route == "curved" and len(line) > 2:
        # maxGraph's curved line: a quadratic through each turn to the
        # middle of the next piece, and the last to the end.
        d = ["M%s %s" % (fmt(line[0][0]), fmt(line[0][1]))]
        for i in range(1, len(line) - 2):
            mx, my = (line[i][0] + line[i + 1][0]) / 2, (line[i][1] + line[i + 1][1]) / 2
            d.append("Q%s %s %s %s" % (fmt(line[i][0]), fmt(line[i][1]), fmt(mx), fmt(my)))
        d.append("Q%s %s %s %s" % (fmt(line[-2][0]), fmt(line[-2][1]), fmt(line[-1][0]), fmt(line[-1][1])))
        path_d = " ".join(d)
    else:
        path_d = "M%s %s" % (fmt(line[0][0]), fmt(line[0][1])) + "".join(
            " L%s %s" % (fmt(x), fmt(y)) for x, y in line[1:])
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.5"%s/>' % (path_d, LINE_INK, dash))
    taken: List[Box] = [(min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))]
    for tip, toward in heads:
        ux, uy = toward[0] - tip[0], toward[1] - tip[1]
        n = math.hypot(ux, uy) or 1.0
        ux, uy = ux / n, uy / n
        bx, by = tip[0] + ux * 7, tip[1] + uy * 7
        out.append('<path d="M%s %s L%s %s L%s %s Z" fill="%s"/>' % (
            fmt(tip[0]), fmt(tip[1]), fmt(bx - uy * 3.5), fmt(by + ux * 3.5), fmt(bx + uy * 3.5), fmt(by - ux * 3.5),
            LINE_INK))
    label = str(item.get("label") or "")
    if label:
        size = float(TEXT_SIZES.get(look.get("text"), 11))
        tw = m.width(label, "Geist", 400, size)
        # At the middle of the run: of its middle piece when it turns, as
        # maxGraph puts an edge's label halfway along its length.
        cx, cy = _halfway(pts)
        w, h = tw + 6, size + 6
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="3" fill="#ffffff" stroke="#d8d2c6" stroke-width="1"/>'
                   % (fmt(cx - w / 2), fmt(cy - h / 2), fmt(w), fmt(h)))
        out.append('<text x="%s" y="%s" font-size="%s" font-weight="400" fill="%s" text-anchor="middle">%s</text>' % (
            fmt(cx), fmt(cy - size / 2 + BASELINE * size), fmt(size), INK, escape(label)))
        taken.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    out.append("</g>")
    return "\n".join(out), taken


def _halfway(pts: Sequence[Point]) -> Point:
    """The point halfway along a run of pieces."""
    lengths = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    half, walked = sum(lengths) / 2, 0.0
    for i, piece in enumerate(lengths):
        if walked + piece >= half and piece:
            t = (half - walked) / piece
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
        walked += piece
    return pts[0]


def paint(items: Sequence[Mapping], origin: Point, records: Mapping[str, Box], m: Metrics,
          layer: str, bounds: Sequence[Box] = ()) -> Tuple[str, List[Box]]:
    """The diagram's own of one layer, `"under"`, `"over"` or a boundary's
    index (`layer_of`), as SVG, and the boxes it takes up for the drawing's
    extent. `records` is each box of the estate on the drawing, by id, for a
    line that ends on one, and `bounds` each boundary's. A line whose record
    is not on the drawing is left off, as the canvas leaves it."""
    boxes = place(items, origin)
    shape_of = {str(a["key"]): str(a.get("shape") or "") for a in items if a.get("role") == "shape"}
    out: List[str] = []
    taken: List[Box] = []
    for item in items:
        if item.get("role") == "line":
            continue
        if layer_of(item, boxes, bounds) != layer:
            continue
        box = boxes[str(item["key"])]
        out.append(_box(item, box, m))
        taken.append(box)
    if layer == "over":
        for item in items:
            if item.get("role") != "line":
                continue
            ends = []
            for end in (item.get("from"), item.get("to")):
                if isinstance(end, (list, tuple)):
                    ends.append((origin[0] + float(end[0]), origin[1] + float(end[1])))
                elif str(end) in boxes:
                    ends.append(boxes[str(end)])
                elif str(end) in records:
                    ends.append(records[str(end)])
                else:
                    ends.append(None)
            if None in ends:
                continue
            svg, line_boxes = _line(item, (ends[0], ends[1]), m,
                                    (shape_of.get(str(item.get("from")), ""), shape_of.get(str(item.get("to")), "")))
            out.append(svg)
            taken.extend(line_boxes)
    return "\n".join(out), taken


def own_extent(items: Sequence[Mapping], origin: Point) -> Optional[Box]:
    """Everything the diagram's own boxes take up, or None."""
    boxes = list(place(items, origin).values())
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
