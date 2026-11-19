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

They are drawn Illustrated, in the app's own picture language: a paper
fill, an ink edge and a hard ink shadow under each shape and note; a
shape's first line of words its name, in the display face, and the rest a
caption under it; a frame's name on an ink tab across its top edge; and
the lines in the pictures' line color, their words on paper tags.

Places are measured from the sheet's corner, where the drawing's own
positions start: nought for an arranged drawing (`terrane.draw.arranged`
lays one from there, as `arrangeKept()` does), and for one the layout
placed the least corner of its boxes, as the canvas takes it.
"""

from __future__ import annotations

import functools
import json
import math
from typing import Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from ..annotations import (CONTAINERS, DEFAULT_LOOK, FILLS, KIND_ICONS, LINE_WEIGHTS, TEXT_SIZES, WEIGHTS, WORDS_ON,
                           heads_of)
from ..icons import mark_file
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
    # The lid drawn right to left, wound as the body is: the other way it
    # was a hole in the fill, and the ink shadow showed through it.
    "cylinder": [("M", 0, 0.12), ("C", 0, -0.04, 1, -0.04, 1, 0.12), ("L", 1, 0.88), ("C", 1, 1.04, 0, 1.04, 0, 0.88),
                 ("Z",), ("M", 1, 0.12), ("C", 1, 0.28, 0, 0.28, 0, 0.12)],
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

#: The fill each kind starts with: a shape on paper, a note on cream; a
#: frame and text have none.
ROLE_FILL = {"note": "yellow", "shape": "white"}
INK = "#2e2a25"
TEXT_INK = INK
LINE_INK = "#6e655a"
CAPTION_INK = "#6e655a"
PAPER = "#fffdf8"
#: How far down and right the hard shadow under a shape or a note falls,
#: as the app's pictures cast theirs.
SHADOW = 4.0
#: The face a shape's name is set in: the display face, as the app sets the
#: name of a thing; and the faces after it where a viewer has not got it,
#: the picture's own.
NAME_FACE = ("Libre Franklin", 700)
NAME_FAMILIES = "Libre Franklin, Geist, system-ui, sans-serif"
#: A rounded box's corner radius, and a frame's.
ROUND = 6.0
#: How far a rounded turn of a line starts before its corner, as maxGraph
#: rounds one (half its LINE_ARCSIZE).
ROUND_TURN = 10.0
#: Where a line's words at its start and its end sit: this share of its
#: length in from each end (END_LABEL_AT in engine.js is one less twice it).
END_LABELS_AT = 0.15
#: The dashes of a dashed outline and a dotted one.
DASHES = {"dashed": "6 4", "dotted": "2 3"}
#: Each head an end of a line may have (V16), as the picture and the canvas
#: draw it, in the drawing's units back from its tip along the line (`a`)
#: and across it (`b`): `stop`, how far back the line itself stops, and its
#: parts, each "fill" (a shape filled with the line's ink), "hollow" (a
#: shape drawn round), "line" (strokes), "dot" (a filled circle at `a`, of
#: radius `r`) or "ring" (one drawn round), points as [a, b, a, b, ...].
#: HEAD_GLYPHS in the canvas's engine.js is held equal to it.
HEAD_GLYPHS: Dict[str, Dict[str, object]] = {
    "none": {"stop": 0, "parts": []},
    "arrow": {"stop": 7, "parts": [["fill", [0, 0, 7, 3.5, 7, -3.5]]]},
    "open-arrow": {"stop": 0, "parts": [["line", [7, 4, 0, 0, 7, -4]]]},
    "dot": {"stop": 6, "parts": [["dot", [3, 3]]]},
    "inherits": {"stop": 9, "parts": [["hollow", [0, 0, 9, 4.5, 9, -4.5]]]},
    "made-of": {"stop": 12, "parts": [["fill", [0, 0, 6, 3.5, 12, 0, 6, -3.5]]]},
    "has": {"stop": 12, "parts": [["hollow", [0, 0, 6, 3.5, 12, 0, 6, -3.5]]]},
    "depends-on": {"stop": 0, "parts": [["line", [7, 4, 0, 0, 7, -4]]]},
    "one": {"stop": 0, "parts": [["line", [4, 4.5, 4, -4.5]], ["line", [8, 4.5, 8, -4.5]]]},
    "many": {"stop": 0, "parts": [["line", [0, 4.5, 8, 0, 0, -4.5]]]},
    "one-or-many": {"stop": 0, "parts": [["line", [11, 4.5, 11, -4.5]], ["line", [0, 4.5, 8, 0, 0, -4.5]]]},
    "none-or-one": {"stop": 15, "parts": [["line", [10, 0, 0, 0]], ["line", [5, 4.5, 5, -4.5]], ["ring", [12.5, 2.5]]]},
    "none-or-many": {"stop": 17, "parts": [["line", [12, 0, 0, 0]], ["line", [0, 4.5, 8, 0, 0, -4.5]],
                                           ["ring", [14.5, 2.5]]]},
    "serving": {"stop": 0, "parts": [["line", [7, 4, 0, 0, 7, -4]]]},
    "triggering": {"stop": 7, "parts": [["fill", [0, 0, 7, 3.5, 7, -3.5]]]},
    "flow": {"stop": 7, "parts": [["fill", [0, 0, 7, 3.5, 7, -3.5]]]},
    "realization": {"stop": 9, "parts": [["hollow", [0, 0, 9, 4.5, 9, -4.5]]]},
    "assignment": {"stop": 7, "parts": [["fill", [0, 0, 7, 3.5, 7, -3.5]]]},
    "access": {"stop": 0, "parts": [["line", [5, 3, 0, 0, 5, -3]]]},
}


def head_parts(tip: Point, toward: Point, head: str) -> Tuple[Point, List[Tuple[str, Tuple[Point, ...], float]]]:
    """A head at `tip`, pointing away from `toward`, in the sheet's units:
    where the line itself stops, and its parts, each its kind, its points (a
    circle's middle alone) and a circle's radius, as HEAD_GLYPHS says."""
    glyph = HEAD_GLYPHS[head]
    ux, uy = toward[0] - tip[0], toward[1] - tip[1]
    n = math.hypot(ux, uy) or 1.0
    ux, uy = ux / n, uy / n

    def at(a: float, b: float) -> Point:
        return (tip[0] + ux * a - uy * b, tip[1] + uy * a + ux * b)

    stop = float(glyph["stop"])  # type: ignore[arg-type]
    parts: List[Tuple[str, Tuple[Point, ...], float]] = []
    for kind, v in glyph["parts"]:  # type: ignore[attr-defined]
        if kind in ("dot", "ring"):
            parts.append((kind, (at(v[0], 0),), float(v[1])))
        else:
            parts.append((kind, tuple(at(v[i], v[i + 1]) for i in range(0, len(v), 2)), 0.0))
    return (at(stop, 0) if stop else tip), parts


def dash_of(line: object) -> str:
    """An outline's dashes as the picture's attribute, or nothing."""
    pattern = DASHES.get(str(line or ""))
    return ' stroke-dasharray="%s"' % pattern if pattern else ""


def along(pts: Sequence[Point], share: float) -> Point:
    """The point a share of the way along a run of pieces."""
    lengths = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    goal, walked = sum(lengths) * share, 0.0
    for i, piece in enumerate(lengths):
        if walked + piece >= goal and piece:
            t = (goal - walked) / piece
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
        walked += piece
    return pts[-1]


def rounded(pts: Sequence[Point], radius: float = ROUND_TURN) -> List[tuple]:
    """A run of pieces with each turn rounded as maxGraph rounds one: the
    line stops `radius` short of the corner, or half the shorter piece, and
    a quadratic through the corner carries it on. `("M", p)`, then `("L",
    p)` and `("Q", corner, p)`."""
    out: List[tuple] = [("M", pts[0])]
    for i in range(1, len(pts) - 1):
        (ax, ay), (cx, cy), (bx, by) = pts[i - 1], pts[i], pts[i + 1]
        la, lb = math.hypot(cx - ax, cy - ay), math.hypot(bx - cx, by - cy)
        r = min(radius, la / 2, lb / 2)
        if not la or not lb or not r:
            out.append(("L", pts[i]))
            continue
        out.append(("L", (cx - (cx - ax) / la * r, cy - (cy - ay) / la * r)))
        out.append(("Q", (cx, cy), (cx + (bx - cx) / lb * r, cy + (by - cy) / lb * r)))
    out.append(("L", pts[-1]))
    return out
#: A swimlane (V16): the band its pool's name sits in across its top, the
#: column at a lane's left or the band at its top that the lane's name sits
#: in, and their paint. engine.js paints the same, by the same names.
POOL_TITLE = 34.0
LANE_COLUMN = 130.0
LANE_BAND = 40.0
BAND = "#f3eee5"
#: How much smaller a caption is than the name over it.
CAPTION_STEP = 2.0

#: Icon tiles, a diagram's other look (V16): every shape a square tile in
#: the middle of its box, light at the top and deep at the foot, a soft glow
#: under it and its icon in white; its words under the box, wider than it;
#: a note flat, a frame a pale panel with its name inside, lines gray.
TILE = 48.0
TILE_ROUND = 12.0
TILE_GLOW = 4.0
TILE_ICON = 22.0
TILE_GAP = 6.0
TILE_WORDS_OVER = 16.0
TILE_FILLS = {
    "yellow": ("#f2c94c", "#c9a227"), "mint": ("#36b096", "#1f7a68"), "lavender": ("#8a84e6", "#5b54c6"),
    "rose": ("#e27b6e", "#b54a3f"), "white": ("#6e7683", "#3b4049"), "stone": ("#a1937f", "#6e655a"),
    "accent": ("#5c8fd6", "#3a62a8"),
}
TILE_INK = "#1e2230"
TILE_CAPTION = "#6b7489"
TILE_LINE = "#8a92a0"
TILE_FRAME = "#f4f5f7"
TILE_FRAME_INK = "#5b6170"
TILE_NAME_FACE = ("Geist", 600)
#: The sheet Icon tiles draw on, and how far a tile's words' patch reaches
#: past the widest of them either side.
TILE_SHEET = "#ffffff"
TILE_GROUND_PAD = 3


@functools.lru_cache(maxsize=1)
def own_icons() -> Dict[str, str]:
    """The icons a tile can carry, by name: `canvas/own-icons.js`, the
    canvas's own file, read as the JSON it holds."""
    from ..shipped import shipped_web

    web = shipped_web()
    path = web / "canvas" / "own-icons.js" if web else None
    if path is None or not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def icon_of(item: Mapping) -> str:
    """The icon a shape carries as a tile: its own, a provider's mark the
    app ships or one of the plain icons, or its kind's."""
    named = (item.get("look") or {}).get("icon")
    if named and (named in own_icons() or mark_file(named) is not None):
        return str(named)
    return KIND_ICONS.get(str(item.get("shape") or "rectangle"), "box")


def tile_box(box: Box) -> Box:
    """The tile in the middle of a shape's box: a square, no wider than the
    box, no taller, and no more than TILE."""
    x1, y1, x2, y2 = box
    side = min(x2 - x1, y2 - y1, TILE)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
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
    # What is on a drawing layer under the estate's records goes under
    # them, as a frame does (`by_layer` marks it).
    if item.get("role") not in CONTAINERS and not inside and not item.get("_under"):
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


def _look(item: Mapping) -> Tuple[str, str, str, float, str]:
    """Its fill, its edge, its dash, the size of its words and their ink."""
    role, look = item.get("role"), item.get("look") or {}
    name = (look.get("fill") if look.get("fill") in FILLS else ROLE_FILL.get(str(role))) if role != "text" else None
    fill = FILLS[name] if name else "none"
    edge = "none" if role == "text" or look.get("line") == "none" else INK
    dash = dash_of(look.get("line"))
    size = float(TEXT_SIZES.get(look.get("text"), 12 if role == "frame" else 13))
    return fill, edge, dash, size, WORDS_ON.get(name or "", INK)


def _baseline(m: Metrics, face: Tuple[str, int], size: float) -> float:
    """Where a line of words has its baseline, down from the top of its
    line box: half the leading the face leaves, then its ascent, as the
    browser sets a line at the canvas's leading."""
    ascent, descent = m.ascent(face[0], face[1], size), m.descent(face[0], face[1], size)
    return (LEADING * size - ascent - descent) / 2 + ascent


def named_rows(label: str, room: float, m: Metrics, size: float, face: Tuple[str, int] = NAME_FACE,
               caption_weight: int = 400) -> List[Tuple[str, Tuple[str, int], float]]:
    """A shape's words as the lines it draws, each with its face and size:
    the first line of the words its name in the display face, wrapped to the
    room; every later line a caption two sizes down. A blank line is no line:
    the canvas's blocks have no height without words in them."""
    lines = [p for p in str(label or "").split("\n")]
    rows: List[Tuple[str, Tuple[str, int], float]] = []
    if lines and lines[0].strip():
        rows += [(t, face, size) for t in m.wrap(lines[0], room, face[0], face[1], size)]
    small = size - CAPTION_STEP
    for p in lines[1:]:
        if p.strip():
            rows += [(t, ("Geist", caption_weight), small) for t in m.wrap(p, room, "Geist", caption_weight, small)]
    return rows


def _named(item: Mapping, box: Box, m: Metrics, size: float, ink: str) -> List[str]:
    """A shape's name and caption, the block of them in its middle."""
    x1, y1, x2, y2 = box
    px, _py = PADDING["shape"]
    words = words_of(item)
    rows = named_rows(str(item.get("label") or ""), max(1.0, x2 - x1 - 2 * px + 2), m, size,
                      caption_weight=600 if words["bold"] else 400)
    top = (y1 + y2) / 2 - sum(s * LEADING for _t, _f, s in rows) / 2
    x, anchor = {"left": (x1 + px, ""), "right": (x2 - px, ' text-anchor="end"')}.get(
        str(words["align"]), ((x1 + x2) / 2, ' text-anchor="middle"'))
    dress = _dress(words)
    caption = 'fill="%s" fill-opacity="0.75"' % ink if ink != INK else 'fill="%s"' % CAPTION_INK
    out = []
    for i, (line, face, s) in enumerate(rows):
        if top + s * LEADING > y2 + 0.5 and i:
            break  # what does not fit is clipped on the canvas too
        named = face == NAME_FACE
        out.append('<text x="%s" y="%s" font-size="%s" font-weight="%d" %s%s%s%s>%s</text>' % (
            fmt(x), fmt(top + _baseline(m, face, s)), fmt(s), face[1],
            'fill="%s"' % ink if named else caption, anchor, ' font-family="%s"' % NAME_FAMILIES if named else "",
            dress, escape(line)))
        top += s * LEADING
    return out


def _tab(item: Mapping, box: Box, m: Metrics, size: float) -> List[str]:
    """A frame's name on an ink tab across its top edge, twelve in, on one
    line and cut short with an ellipsis where it would run past the frame."""
    label = str(item.get("label") or "").split("\n")[0]
    if not label.strip():
        return []
    x1, y1, x2, _y2 = box
    name = m.fit(label, max(1.0, x2 - x1 - 24 - 2 * TAB_PAD), "Geist", 600, size)
    w, h = m.width(name, "Geist", 600, size) + 2 * TAB_PAD, size * LEADING + 4
    top = y1 - h / 2
    return ['<rect x="%s" y="%s" width="%s" height="%s" rx="3" fill="%s"/>' % (
                fmt(x1 + 12), fmt(top), fmt(w), fmt(h), INK),
            '<text x="%s" y="%s" font-size="%s" font-weight="600" fill="%s"%s>%s</text>' % (
                fmt(x1 + 12 + TAB_PAD), fmt(top + 2 + _baseline(m, ("Geist", 600), size)), fmt(size), PAPER,
                _dress(words_of(item)), escape(name))]


#: The room either side of a frame's name on its tab.
TAB_PAD = 8.0


def _words(item: Mapping, box: Box, m: Metrics, size: float, ink: str = INK) -> List[str]:
    role = item.get("role")
    label = str(item.get("label") or "")
    if not label:
        return []
    x1, y1, x2, y2 = box
    px, py = PADDING.get(str(role), (8, 8))
    words = words_of(item)
    weight = 600 if role == "frame" or words["bold"] else 400
    # A list's lines each start past a bullet, a font size in, and wrap to
    # the room left after it.
    indent = size if words["listed"] else 0.0
    # Wrapped two pixels wider than the room inside the padding: maxGraph
    # lays a wrapped label out that much wider than its cell, and a note's
    # "Guardrails: every account is", 164.3 at 13, kept its "is" there.
    room = max(1.0, x2 - x1 - 2 * px + 2 - indent)
    rows = []
    for para in label.split("\n"):
        rows += [(t, words["listed"] and i == 0 and bool(para.strip()))
                 for i, t in enumerate(m.wrap(para, room, "Geist", weight, size))]
    step = size * LEADING
    first = size * (LEADING - 1) / 2 + BASELINE * size
    align = "left" if words["listed"] else words["align"] or ("center" if role == "shape" else "left")
    x, anchor = {"left": (x1 + px, ""), "center": ((x1 + x2) / 2, ' text-anchor="middle"'),
                 "right": (x2 - px, ' text-anchor="end"')}[str(align)]
    top = (y1 + y2) / 2 - len(rows) * step / 2 if role == "shape" else y1 + py
    fill = TEXT_INK if role == "text" else ink
    dress = _dress(words)
    out = []
    for i, (line, bullet) in enumerate(rows):
        if top + i * step + step > y2 + 0.5 and role != "text" and i:
            break  # what does not fit is clipped on the canvas too
        y = top + first + i * step
        if bullet:
            out.append('<text x="%s" y="%s" font-size="%s" font-weight="%d" fill="%s">•</text>' % (
                fmt(x), fmt(y), fmt(size), weight, fill))
        out.append('<text x="%s" y="%s" font-size="%s" font-weight="%d" fill="%s"%s%s>%s</text>' % (
            fmt(x + indent), fmt(y), fmt(size), weight, fill, anchor, dress, escape(line)))
    return out


def casts_shadow(item: Mapping, look: str = DEFAULT_LOOK) -> bool:
    """Whether it stands on the sheet with a hard shadow under it, drawn
    Illustrated: a shape or a note with an edge, unless its look says
    `shadow: none`; text, a frame and what has no edge lie flat, as
    everything does as tiles. A see-through fill casts none either: the
    ink under it showed through as a muddy patch."""
    mine = item.get("look") or {}
    return (look != "tiles" and item.get("role") in ("shape", "note")
            and mine.get("line") != "none" and mine.get("shadow") != "none" and (mine.get("opacity") or 100) >= 100)


def corners_of(item: Mapping, look: str = DEFAULT_LOOK) -> Optional[float]:
    """The radius its corners are rounded by: its look's own, else its
    kind's (Illustrated rounds a rounded box and a frame by ROUND; as tiles a
    shape's tile by TILE_ROUND, a frame by 16, a note by 4); 0 for square,
    and None for what has no corners to round, a line, text, or an ellipse
    or a cylinder drawn Illustrated."""
    role, kind = item.get("role"), str(item.get("shape") or "rectangle")
    if role not in ("shape", "note", "frame") or (role == "shape" and look != "tiles"
                                                  and kind not in ("rectangle", "rounded")):
        return None
    mine = (item.get("look") or {}).get("corners")
    if mine is not None:
        return float(mine)
    if look == "tiles":
        return {"shape": TILE_ROUND, "frame": 16.0, "note": 4.0}[str(role)]
    return ROUND if role == "frame" or kind == "rounded" else 0.0


def words_of(item: Mapping) -> Dict[str, object]:
    """How its words are set (V16's words toolbar), each false or blank
    when its look says nothing."""
    look = item.get("look") or {}
    return {"bold": look.get("bold") is True, "italic": look.get("italic") is True,
            "underline": look.get("underline") is True, "strike": look.get("strike") is True,
            "align": str(look.get("align") or ""), "listed": look.get("list") is True}


def _dress(words: Mapping) -> str:
    """Italic, underlined and struck through, as a text's attributes; the
    face has no italic of its own, and the browser slants the upright one,
    on the canvas as here, so a line measures the same either way."""
    deco = " ".join(n for n, on in (("underline", words["underline"]), ("line-through", words["strike"])) if on)
    return (' font-style="italic"' if words["italic"] else "") + (' text-decoration="%s"' % deco if deco else "")


def opacity_of(item: Mapping) -> float:
    """How much of its fill shows, from 0.1 to 1."""
    return float((item.get("look") or {}).get("opacity") or 100) / 100


def weight_of(item: Mapping) -> float:
    """How heavy its edge is drawn, in pixels."""
    return WEIGHTS.get(str((item.get("look") or {}).get("weight") or "m"), WEIGHTS["m"])


def _faded(opacity: float) -> str:
    return ' fill-opacity="%s"' % fmt(opacity) if opacity < 1 else ""


def tile_rows(item: Mapping, box: Box, m: Metrics) -> List[Tuple[str, Tuple[str, int], float]]:
    """A tile's words, under its box: the name and the caption, wrapped a
    little wider than the box."""
    size = float(TEXT_SIZES.get((item.get("look") or {}).get("text"), 13))
    room = box[2] - box[0] + 2 * TILE_WORDS_OVER
    return named_rows(str(item.get("label") or ""), room, m, size, TILE_NAME_FACE,
                      600 if words_of(item)["bold"] else 400)


def tile_ground(item: Mapping, by_key: Mapping[str, Mapping]) -> str:
    """What lies under a tile's words: the frame it sits in, the
    innermost, as Icon tiles fill one, else the sheet."""
    for key in reversed(list(item.get("in") or [])):
        frame = by_key.get(str(key))
        # A swimlane's lane lies on its pool's paper.
        if frame is not None and frame.get("role") in ("pool", "lane"):
            return PAPER
        if frame is not None and frame.get("role") == "frame":
            name = (frame.get("look") or {}).get("fill")
            return FILLS[name] if name in FILLS else TILE_FRAME
    return TILE_SHEET


def tile_words(item: Mapping, box: Box, m: Metrics, ground: str = TILE_SHEET) -> List[str]:
    """A tile's name and caption under its box, on a patch of what lies
    under them: a line leaving the tile downward runs under its words, and
    not through them."""
    rows = tile_rows(item, box, m)
    if not rows:
        return []
    x1, _y1, x2, y2 = box
    cx, top_of_words = (x1 + x2) / 2, y2 + TILE_GAP
    wide = max(m.width(line, face[0], face[1], s) for line, face, s in rows)
    out = ['<rect x="%s" y="%s" width="%s" height="%s" fill="%s" class="ground"/>' % (
        fmt(cx - wide / 2 - TILE_GROUND_PAD), fmt(top_of_words), fmt(wide + 2 * TILE_GROUND_PAD),
        fmt(sum(s * LEADING for _line, _face, s in rows)), ground)]
    for line, face, s in rows:
        named = face == TILE_NAME_FACE
        out.append('<text x="%s" y="%s" font-size="%s" font-weight="%d" fill="%s" text-anchor="middle"%s>%s</text>' % (
            fmt(cx), fmt(top_of_words + _baseline(m, face, s)), fmt(s), face[1],
            TILE_INK if named else TILE_CAPTION, _dress(words_of(item)), escape(line)))
        top_of_words += s * LEADING
    return out


def _tiled(item: Mapping, box: Box, m: Metrics, ground: str = TILE_SHEET) -> List[str]:
    """One of the diagram's own as Icon tiles draws it."""
    role, look = item.get("role"), item.get("look") or {}
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    name = look.get("fill") if look.get("fill") in FILLS else ROLE_FILL.get(str(role))
    dash = dash_of(look.get("line"))
    size = float(TEXT_SIZES.get(look.get("text"), 12 if role == "frame" else 13))
    if role == "shape":
        top, foot = TILE_FILLS[name or "white"]
        tx1, ty1, tx2, _ty2 = tile_box(box)
        side = tx2 - tx1
        gid = "tile-%s" % "".join(c if c.isalnum() or c in "-_" else "_" for c in str(item["key"]))
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        radius, faded = min(corners_of(item, "tiles") or 0.0, side / 2), opacity_of(item)
        mark = mark_file(look.get("icon"))
        if mark is not None:
            # A provider's or vendor's own mark stands in the tile's place
            # as its owner publishes it: no tile behind it, no glow, nothing
            # recolored (icons/CREDITS.md).
            from .svg import image

            out = [image(mark.read_bytes(), tx1, ty1, side, side)]
        else:
            out = ['<defs><linearGradient id="%s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/>'
                   '<stop offset="1" stop-color="%s"/></linearGradient></defs>' % (gid, top, foot),
                   '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" fill-opacity="%s" class="glow"/>' % (
                       fmt(tx1), fmt(ty1 + TILE_GLOW), fmt(side), fmt(side), fmt(radius), foot, fmt(0.25 * faded)),
                   '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="url(#%s)"%s/>' % (
                       fmt(tx1), fmt(ty1), fmt(side), fmt(side), fmt(radius), gid, _faded(faded))]
        icon = own_icons().get(icon_of(item)) if mark is None else None
        if icon:
            out.append('<g transform="translate(%s %s) scale(%s)" fill="none" stroke="#ffffff" stroke-width="2" '
                       'stroke-linecap="round" stroke-linejoin="round" class="icon">%s</g>' % (
                           fmt(cx - TILE_ICON / 2), fmt(cy - TILE_ICON / 2), fmt(TILE_ICON / 24), icon))
        return out + tile_words(item, box, m, ground)
    if role == "frame":
        fill = FILLS[name] if name else TILE_FRAME
        edge = 'stroke="%s" stroke-width="%s"%s' % (TILE_FRAME_INK, fmt(weight_of(item)), dash) if dash else 'stroke="none"'
        out = ['<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"%s %s/>' % (
            fmt(x1), fmt(y1), fmt(w), fmt(h), fmt(min(corners_of(item, "tiles") or 0.0, w / 2, h / 2)), fill,
            _faded(opacity_of(item)), edge)]
        label = str(item.get("label") or "").split("\n")[0]
        if label.strip():
            words = m.fit(label, max(1.0, w - 28), "Geist", 600, size)
            out.append('<text x="%s" y="%s" font-size="%s" font-weight="600" fill="%s">%s</text>' % (
                fmt(x1 + 14), fmt(y1 + 10 + _baseline(m, ("Geist", 600), size)), fmt(size), TILE_FRAME_INK,
                escape(words)))
        return out
    out = []
    if role == "note":
        edge = 'stroke="%s" stroke-width="%s"%s' % (TILE_FRAME_INK, fmt(weight_of(item)), dash) if dash else 'stroke="none"'
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"%s %s/>' % (
            fmt(x1), fmt(y1), fmt(w), fmt(h), fmt(min(corners_of(item, "tiles") or 0.0, w / 2, h / 2)),
            FILLS[name or "yellow"], _faded(opacity_of(item)), edge))
    return out + _words(item, box, m, size, WORDS_ON.get(name or "", INK))


def _tiled_paint(item: Mapping) -> Tuple[str, str, str]:
    """The fill, edge and words' ink of one of the diagram's own as tiles,
    for a painter that draws it as a slide shape or a draw.io cell: a
    shape's tile at its deeper color, a frame's pale panel, a note flat."""
    role, look = item.get("role"), item.get("look") or {}
    name = look.get("fill") if look.get("fill") in FILLS else ROLE_FILL.get(str(role))
    dashed = look.get("line") == "dashed"
    if role == "shape":
        return TILE_FILLS[name or "white"][1], "none", TILE_INK
    if role == "frame":
        return FILLS[name] if name else TILE_FRAME, TILE_FRAME_INK if dashed else "none", TILE_FRAME_INK
    if role == "note":
        return FILLS[name or "yellow"], TILE_FRAME_INK if dashed else "none", WORDS_ON.get(name or "", INK)
    return "none", "none", INK


def names_of(item: Mapping, by_key: Mapping[str, Mapping]) -> str:
    """Where a lane's name sits, as its swimlane says: at its left unless
    the swimlane says top."""
    inside = list(item.get("in") or [])
    pool = by_key.get(str(inside[-1])) if inside else None
    return "top" if pool is not None and pool.get("names") == "top" else "left"


def swim_parts(item: Mapping, box: Box, names: str, m: Metrics) -> List[Tuple[str, Box, str, str, float, bool]]:
    """What a swimlane's pool or lane is drawn as, the same for every
    painter: rectangles, each `("rect", box, fill, "", size, False)`, and
    words, each `("words", box, fill, label, size, bold)` set from the box's
    corner. A pool is its ground and the band its name sits in; a lane its
    outline, the column or band its name sits in, its name, and the id of
    the record it stands for under it."""
    x1, y1, x2, y2 = box
    size = float(TEXT_SIZES.get((item.get("look") or {}).get("text"), 13))
    label = str(item.get("label") or "")
    if item.get("role") == "pool":
        out = [("rect", box, PAPER, "", size, False), ("rect", (x1, y1, x2, min(y2, y1 + POOL_TITLE)), BAND, "", size,
                                                       False)]
        title = label.split("\n")[0]
        if title.strip():
            name = m.fit(title, max(1.0, x2 - x1 - 24), "Geist", 600, size)
            top = y1 + (POOL_TITLE - size * LEADING) / 2
            out.append(("words", (x1 + 12, top, x2 - 12, top + size * LEADING), INK, name, size, True))
        return out
    out = [("rect", box, "none", "", size, False)]
    caption = str(item.get("stands_for") or "")
    if names == "top":
        out.append(("rect", (x1, y1, x2, min(y2, y1 + LANE_BAND)), BAND, "", size, False))
        rows = [m.fit(label.split("\n")[0], max(1.0, x2 - x1 - 24), "Geist", 600, size)] if label.strip() else []
        top = y1 + 5
    else:
        right = min(x2, x1 + LANE_COLUMN)
        out.append(("rect", (x1, y1, right, y2), BAND, "", size, False))
        rows = m.wrap(label.split("\n")[0], max(1.0, right - x1 - 24), "Geist", 600, size) if label.strip() else []
        top = y1 + 10
    room = (x2 if names == "top" else min(x2, x1 + LANE_COLUMN)) - 12
    if rows:
        out.append(("words", (x1 + 12, top, room, top + len(rows) * size * LEADING), INK, "\n".join(rows), size, True))
        top += len(rows) * size * LEADING + (1 if names == "top" else 4)
    if caption:
        small = size - CAPTION_STEP
        out.append(("words", (x1 + 12, top, room, top + small * LEADING), CAPTION_INK, caption, small, False))
    return out


def _swim(item: Mapping, box: Box, m: Metrics, names: str) -> str:
    """A swimlane's pool or lane, as `swim_parts` makes it, whatever the
    diagram's look: a swimlane is drawn one way."""
    out = ['<g class="own" data-key="%s" data-role="%s">' % (escape(str(item["key"]), {'"': "&quot;"}), item["role"])]
    for kind, (x1, y1, x2, y2), fill, label, size, bold in swim_parts(item, box, names, m):
        if kind == "rect":
            out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                fmt(x1), fmt(y1), fmt(x2 - x1), fmt(y2 - y1), fill, INK, fmt(WEIGHTS["m"])))
            continue
        weight = 600 if bold else 400
        for i, row in enumerate(label.split("\n")):
            out.append('<text x="%s" y="%s" font-size="%s" font-weight="%d" fill="%s">%s</text>' % (
                fmt(x1), fmt(y1 + size * (LEADING - 1) / 2 + BASELINE * size + i * size * LEADING), fmt(size), weight,
                fill, escape(row)))
    out.append("</g>")
    return "\n".join(out)


def _box(item: Mapping, box: Box, m: Metrics, look: str = DEFAULT_LOOK, ground: str = TILE_SHEET,
         names: str = "left") -> str:
    role = item.get("role")
    if role in ("pool", "lane"):
        return _swim(item, box, m, names)
    if look == "tiles":
        x1, y1, x2, y2 = box
        turn = float(item.get("rotate") or 0)
        spin = ' transform="rotate(%s %s %s)"' % (fmt(turn), fmt((x1 + x2) / 2), fmt((y1 + y2) / 2)) if turn else ""
        return _linked("\n".join(['<g class="own" data-key="%s" data-role="%s"%s>' % (
            escape(str(item["key"]), {'"': "&quot;"}), role, spin)] + _tiled(item, box, m, ground) + ["</g>"]), item)
    fill, edge, dash, size, words = _look(item)
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    turn = float(item.get("rotate") or 0)
    # Turned about its middle, words, shadow and all, as maxGraph turns it.
    spin = ' transform="rotate(%s %s %s)"' % (fmt(turn), fmt(x1 + w / 2), fmt(y1 + h / 2)) if turn else ""
    out = ['<g class="own" data-key="%s" data-role="%s"%s>' % (escape(str(item["key"]), {'"': "&quot;"}), role, spin)]
    radius, kind = corners_of(item), str(item.get("shape") or "rectangle")

    def outline(dx: float, dy: float, paint: str) -> str:
        if radius:
            return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" %s/>' % (
                fmt(x1 + dx), fmt(y1 + dy), fmt(w), fmt(h), fmt(min(radius, w / 2, h / 2)), paint)
        if role == "shape" and kind != "rounded":
            return '<path d="%s" %s/>' % (path_data(str(item.get("shape") or "rectangle"), x1 + dx, y1 + dy, w, h),
                                          paint)
        return '<rect x="%s" y="%s" width="%s" height="%s" %s/>' % (fmt(x1 + dx), fmt(y1 + dy), fmt(w), fmt(h), paint)

    if casts_shadow(item):
        out.append(outline(SHADOW, SHADOW, 'fill="%s" class="shadow"' % INK))
    if role != "text":
        out.append(outline(0.0, 0.0, 'fill="%s"%s stroke="%s" stroke-width="%s"%s' % (
            fill, _faded(opacity_of(item)), edge, fmt(weight_of(item)), dash)))
    if role == "frame":
        out.extend(_tab(item, box, m, size))
    elif role == "shape":
        out.extend(_named(item, box, m, size, words))
    else:
        out.extend(_words(item, box, m, size, words))
    out.append("</g>")
    return _linked("\n".join(out), item)


def _linked(svg: str, item: Mapping) -> str:
    """One of its own that links somewhere (`link:`), as a link of the
    picture's: the shape opens it in a browser, and says where on hover. No
    mark is drawn: the canvas's is over the drawing for the person, as its
    handles are, and its export leaves it out too."""
    link = str(item.get("link") or "")
    if not link:
        return svg
    return '<a href="%s" target="_blank" rel="noopener"><title>%s</title>\n%s\n</a>' % (
        escape(link, {'"': "&quot;"}), escape(link), svg)


def _clip(box: Box, inner: Point, outer: Point, shape: str = "") -> Point:
    if shape == "tile":
        return _clip(tile_box(box), inner, outer, "rectangle")
    return _clip_outline(box, inner, outer, shape)


def _clip_outline(box: Box, inner: Point, outer: Point, shape: str = "") -> Point:
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


#: A square or curved line goes around the boxes in its way: the corridors
#: run this far out from every box, and a bend costs this much of the length
#: it is traded against, the grid router's numbers (`terrane.draw.router`).
DETOUR_MARGIN = 10.0
DETOUR_BEND = 36.0
#: Right, down, left, up: the four ways along the grid, in the order tried.
_STEPS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def _snap(v: float) -> float:
    # To a 1024th, half up: Python's round() goes half to even and
    # JavaScript's Math.round half up, and the canvas routes from the same
    # numbers this does.
    return math.floor(v * 1024 + 0.5) / 1024


def _cuts(p: Point, q: Point, o: Box) -> bool:
    """Whether the piece from p to q, across or down, runs through o's inside."""
    if p[0] == q[0]:
        return o[0] < p[0] < o[2] and max(min(p[1], q[1]), o[1]) < min(max(p[1], q[1]), o[3])
    return o[1] < p[1] < o[3] and max(min(p[0], q[0]), o[0]) < min(max(p[0], q[0]), o[2])


def detour(a: Box, b: Box, obstacles: Sequence[Box], plain: Sequence[Point]) -> List[Point]:
    """A square line's turns from box `a` to box `b` (a point is a box of no
    size) around the boxes in `obstacles`. `plain`, the turns `square` gives,
    when the line through them runs through none of them, or when the boxes
    overlap and the line has no turns; else the cheapest way over a grid of
    corridors a margin out from every box, where a bend costs DETOUR_BEND,
    leaving `a` and coming into `b` square from the middle of a side, a
    margin's run first and last; and `plain` again when the boxes leave no
    way. The turns are where it turns, its runs straight between them.
    `detour` in engine.js, step for step: the inputs are snapped to a 1024th,
    so every sum after is exact, and the queue breaks ties on the order
    things went into it."""
    import heapq

    if not plain:
        return list(plain)
    m, bend = DETOUR_MARGIN, DETOUR_BEND
    sa = (_snap(a[0]), _snap(a[1]), _snap(a[2]), _snap(a[3]))
    sb = (_snap(b[0]), _snap(b[1]), _snap(b[2]), _snap(b[3]))
    walls = sorted({(_snap(o[0]), _snap(o[1]), _snap(o[2]), _snap(o[3])) for o in obstacles} - {sa, sb})
    ca = ((sa[0] + sa[2]) / 2, (sa[1] + sa[3]) / 2)
    cb = ((sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2)
    run = [ca] + [(float(p[0]), float(p[1])) for p in plain] + [cb]
    if not any(_cuts(run[i], run[i + 1], o) for i in range(len(run) - 1) for o in walls):
        return list(plain)
    # The ends' own boxes are walls too, so the line does not cut through
    # where it starts or ends; a point is no wall.
    blocks = walls + [w for w in (sa, sb) if w[0] < w[2] and w[1] < w[3]]

    def free(p: Point) -> bool:
        return not any(o[0] < p[0] < o[2] and o[1] < p[1] < o[3] for o in blocks)

    def ports(box: Box, c: Point) -> List[Tuple[Point, int, Point]]:
        # Where a line leaves a box, a margin out from each side's middle,
        # the way it leaves, and the side's middle; a point leaves any way.
        if box[0] == box[2] and box[1] == box[3]:
            return [(c, -1, c)]
        out = [((box[2] + m, c[1]), 0, (box[2], c[1])), ((c[0], box[3] + m), 1, (c[0], box[3])),
               ((box[0] - m, c[1]), 2, (box[0], c[1])), ((c[0], box[1] - m), 3, (c[0], box[1]))]
        return [(p, d, side) for p, d, side in out if free(p) and not any(_cuts(side, p, o) for o in walls)]

    xs = sorted({sa[0] - m, sa[2] + m, ca[0], sb[0] - m, sb[2] + m, cb[0]}
                | {o[0] - m for o in walls} | {o[2] + m for o in walls})
    ys = sorted({sa[1] - m, sa[3] + m, ca[1], sb[1] - m, sb[3] + m, cb[1]}
                | {o[1] - m for o in walls} | {o[3] + m for o in walls})
    xi = {x: i for i, x in enumerate(xs)}
    yi = {y: j for j, y in enumerate(ys)}
    goals: Dict[Tuple[int, int], Tuple[int, float]] = {}
    for p, d, _side in ports(sb, cb):
        goals[(xi[p[0]], yi[p[1]])] = (-1 if d < 0 else (d + 2) % 4, 0.0 if d < 0 else m)
    if not goals:
        return list(plain)
    targets = [(xs[i], ys[j]) for i, j in goals]

    def near(i: int, j: int) -> float:
        return min(abs(xs[i] - tx) + abs(ys[j] - ty) for tx, ty in targets)

    def turn(d1: int, d2: int) -> float:
        if d1 < 0 or d2 < 0 or d1 == d2:
            return 0.0
        return 2 * bend if (d1 + 2) % 4 == d2 else bend

    heap: List[tuple] = []
    best: Dict[Tuple[int, int, int], float] = {}
    parent: Dict[Tuple[int, int, int], Optional[Tuple[int, int, int]]] = {}
    count = 0
    for p, d, _side in ports(sa, ca):
        s = (xi[p[0]], yi[p[1]], d)
        g = 0.0 if d < 0 else m
        if g < best.get(s, math.inf):
            best[s], parent[s] = g, None
            heapq.heappush(heap, (g + near(s[0], s[1]), count, 0, s, g))
            count += 1
    end = None
    while heap:
        _f, _n, kind, s, g = heapq.heappop(heap)
        if kind:
            end = s
            break
        if g > best.get(s, math.inf):
            continue
        i, j, d = s
        goal = goals.get((i, j))
        if goal is not None:
            total = g + turn(d, goal[0]) + goal[1]
            heapq.heappush(heap, (total, count, 1, s, total))
            count += 1
        for k, (dx, dy) in enumerate(_STEPS):
            if d >= 0 and k == (d + 2) % 4:
                continue
            ni, nj = i + dx, j + dy
            if not (0 <= ni < len(xs) and 0 <= nj < len(ys)):
                continue
            p, q = (xs[i], ys[j]), (xs[ni], ys[nj])
            if not free(q) or any(_cuts(p, q, o) for o in blocks):
                continue
            ng = g + abs(q[0] - p[0]) + abs(q[1] - p[1]) + (bend if d >= 0 and k != d else 0.0)
            t = (ni, nj, k)
            if ng < best.get(t, math.inf):
                best[t], parent[t] = ng, s
                heapq.heappush(heap, (ng + near(ni, nj), count, 0, t, ng))
                count += 1
    if end is None:
        return list(plain)
    nodes: List[Point] = []
    at: Optional[Tuple[int, int, int]] = end
    while at is not None:
        nodes.append((xs[at[0]], ys[at[1]]))
        at = parent[at]
    pts = [ca] + nodes[::-1] + [cb]
    kept = [pts[0]]
    for k in range(1, len(pts) - 1):
        p, q, r = kept[-1], pts[k], pts[k + 1]
        if p[0] == q[0] == r[0] or p[1] == q[1] == r[1]:
            continue
        kept.append(q)
    kept.append(pts[-1])
    return kept[1:-1]


def kept_turns(a: Box, b: Box, kept: Sequence[Point]) -> List[Point]:
    """A square or curved line's turns where its stretches were moved by
    hand (V16), from its `via`: through them, each end leaving its box
    square toward the first or the last, with a turn of its own where the
    box faces neither across nor down to it. keptTurns in engine.js."""
    turns = [tuple(p) for p in kept]
    f, last = turns[0], turns[-1]
    if not a[0] <= f[0] <= a[2] and not a[1] <= f[1] <= a[3]:
        turns.insert(0, (f[0], (a[1] + a[3]) / 2))
    if not b[0] <= last[0] <= b[2] and not b[1] <= last[1] <= b[3]:
        turns.append((last[0], (b[1] + b[3]) / 2))
    return turns  # type: ignore[return-value]


def line_route(item: Mapping, ends: Tuple[object, object], shapes: Tuple[str, str] = ("", ""),
               origin: Point = (0.0, 0.0),
               obstacles: Sequence[Box] = ()) -> Tuple[List[Point], List[Tuple[Point, Point, str]]]:
    """A line's points from end to end, each end where the line leaves its
    box's outline, and its heads, each a tip, the point it points away from
    and which head it is (`heads_of`), its end's before its start's. An end is a box, or a point of the sheet; a straight line's bends
    (`via`) are points of the sheet from `origin`, as a point end is; and a
    square or curved line goes around the boxes in `obstacles` (`detour`)."""

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
    # An end held at a side of its box leaves it square, a margin out
    # first, and is routed on from there as a point (`_stub`).
    sa, sb = _stub(a), _stub(b)
    ra = (sa[0], sa[1], sa[0], sa[1]) if sa else boxed(a)
    rb = (sb[0], sb[1], sb[0], sb[1]) if sb else boxed(b)
    # Its stretches moved by hand, a square or curved line keeps its turns
    # and goes around nothing: where it runs is the person's.
    kept = route in ("square", "curved") and bool(item.get("via"))
    if kept:
        turns = kept_turns(ra, rb, [(origin[0] + float(p[0]), origin[1] + float(p[1])) for p in item["via"]])
    else:
        turns = square(ra, rb) if route in ("square", "curved") else []
        if turns and obstacles:
            turns = detour(ra, rb, obstacles, turns)
    if route in ("square", "curved"):
        turns = ([sa] if sa else []) + turns + ([sb] if sb else [])
    if route == "straight" and item.get("via"):
        turns = [(origin[0] + float(p[0]), origin[1] + float(p[1])) for p in item["via"]]
    first, last = (turns[0] if turns else cb), (turns[-1] if turns else ca)

    def square_from(end: object, c: Point, toward: Point) -> Point:
        # A kept turn need not face a box's middle: the line leaves square,
        # from under or beside the turn, as maxGraph's orthogonal outline
        # point puts it.
        if kept and isinstance(end, tuple) and len(end) == 4:
            if end[0] <= toward[0] <= end[2]:
                return (toward[0], c[1])
            if end[1] <= toward[1] <= end[3]:
                return (c[0], toward[1])
        return c

    p1 = _clip(a, square_from(a, ca, first), first, shapes[0]) if isinstance(a, tuple) and len(a) == 4 else ca
    p2 = _clip(b, square_from(b, cb, last), last, shapes[1]) if isinstance(b, tuple) and len(b) == 4 else cb
    pts = [p1] + turns + [p2]
    start, end = heads_of(item)
    heads = [(tip, toward, head) for tip, toward, head in ((p2, pts[-2], end), (p1, pts[1], start)) if head != "none"]
    return pts, heads


def _line(item: Mapping, ends: Tuple[object, object], m: Metrics, shapes: Tuple[str, str] = ("", ""),
          origin: Point = (0.0, 0.0), obstacles: Sequence[Box] = (), drawn: str = DEFAULT_LOOK) -> Tuple[str, List[Box]]:
    look = item.get("look") or {}
    tiles = drawn == "tiles"
    route = str(item.get("route") or "straight")
    # Each end where the line toward its first turn leaves the outline, as
    # maxGraph's perimeters put it, and each head along the run it ends.
    pts, heads = line_route(item, ends, shapes, origin, obstacles)
    p2 = pts[-1]
    dash = dash_of(look.get("line"))
    heavy = LINE_WEIGHTS.get(str(look.get("weight") or "m"), LINE_WEIGHTS["m"])
    out = ['<g class="own" data-key="%s" data-role="line">' % escape(str(item["key"]), {'"': "&quot;"})]
    # The line stops where each head's base is, so its end does not show
    # past the point of the arrow or through a hollow head.
    line = list(pts)
    for tip, toward, head in heads:
        line[-1 if tip == p2 else 0] = head_parts(tip, toward, head)[0]
    if route == "curved" and len(line) > 2:
        # maxGraph's curved line: a quadratic through each turn to the
        # middle of the next piece, and the last to the end.
        d = ["M%s %s" % (fmt(line[0][0]), fmt(line[0][1]))]
        for i in range(1, len(line) - 2):
            mx, my = (line[i][0] + line[i + 1][0]) / 2, (line[i][1] + line[i + 1][1]) / 2
            d.append("Q%s %s %s %s" % (fmt(line[i][0]), fmt(line[i][1]), fmt(mx), fmt(my)))
        d.append("Q%s %s %s %s" % (fmt(line[-2][0]), fmt(line[-2][1]), fmt(line[-1][0]), fmt(line[-1][1])))
        path_d = " ".join(d)
    elif item.get("turns") == "rounded" and len(line) > 2:
        path_d = " ".join(("%s%s %s" % (op[0], fmt(op[1][0]), fmt(op[1][1]))) if op[0] != "Q" else
                          "Q%s %s %s %s" % (fmt(op[1][0]), fmt(op[1][1]), fmt(op[2][0]), fmt(op[2][1]))
                          for op in rounded(line))
    else:
        path_d = "M%s %s" % (fmt(line[0][0]), fmt(line[0][1])) + "".join(
            " L%s %s" % (fmt(x), fmt(y)) for x, y in line[1:])
    ink = TILE_LINE if tiles else LINE_INK
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s"%s/>' % (path_d, ink, fmt(heavy), dash))
    taken: List[Box] = [(min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))]
    # Each head's parts, its strokes as heavy as the line and never dashed.
    for tip, toward, head in heads:
        for kind, at, r in head_parts(tip, toward, head)[1]:
            if kind in ("dot", "ring"):
                out.append('<circle cx="%s" cy="%s" r="%s" %s/>' % (
                    fmt(at[0][0]), fmt(at[0][1]), fmt(r), 'fill="%s"' % ink if kind == "dot" else
                    'fill="none" stroke="%s" stroke-width="%s"' % (ink, fmt(heavy))))
                continue
            d = "M%s %s" % (fmt(at[0][0]), fmt(at[0][1])) + "".join(" L%s %s" % (fmt(x), fmt(y)) for x, y in at[1:])
            if kind == "fill":
                out.append('<path d="%s Z" fill="%s"/>' % (d, ink))
            else:
                out.append('<path d="%s%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" '
                           'stroke-linecap="round"/>' % (d, " Z" if kind == "hollow" else "", ink, fmt(heavy)))
    size = float(TEXT_SIZES.get(look.get("text"), 11))
    # Its middle's words at the middle of the run, as maxGraph puts an
    # edge's label halfway along its length; its start's and its end's a
    # share in from each end (V16); each on a paper tag edged in ink, as the
    # app's pictures label a joint.
    words = [(str(item.get("label") or ""), _halfway(pts))] + [
        (str((item.get("labels") or {}).get(place) or ""), along(pts, share))
        for place, share in (("start", END_LABELS_AT), ("end", 1 - END_LABELS_AT))]
    for label, (cx, cy) in words:
        if not label:
            continue
        tw = m.width(label, "Geist", 400, size)
        w, h = tw + 6, size + 6
        if tiles:
            out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="3" fill="#ffffff"/>'
                       % (fmt(cx - w / 2), fmt(cy - h / 2), fmt(w), fmt(h)))
        else:
            out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="2" fill="%s" stroke="%s" stroke-width="1"/>'
                       % (fmt(cx - w / 2), fmt(cy - h / 2), fmt(w), fmt(h), PAPER, INK))
        out.append('<text x="%s" y="%s" font-size="%s" font-weight="400" fill="%s" text-anchor="middle">%s</text>' % (
            fmt(cx), fmt(cy - size / 2 + BASELINE * size), fmt(size), TILE_CAPTION if tiles else INK, escape(label)))
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
          layer: str, bounds: Sequence[Box] = (), look: str = DEFAULT_LOOK) -> Tuple[str, List[Box]]:
    """The diagram's own of one layer, `"under"`, `"over"` or a boundary's
    index (`layer_of`), as SVG, and the boxes it takes up for the drawing's
    extent. `records` is each box of the estate on the drawing, by id, for a
    line that ends on one, and `bounds` each boundary's. A line whose record
    is not on the drawing is left off, as the canvas leaves it."""
    boxes = place(items, origin)
    shape_of = _outlines(items, look)
    by_key = {str(i.get("key")): i for i in items}
    out: List[str] = []
    taken: List[Box] = []
    for item in items:
        if item.get("role") == "line":
            continue
        if layer_of(item, boxes, bounds) != layer:
            continue
        box = boxes[str(item["key"])]
        taken.append(_reach(item, box, m, look))
        # As tiles, a tile is drawn last, over the lines (below).
        if look != "tiles" or item.get("role") != "shape":
            out.append(_box(item, box, m, look, names=names_of(item, by_key)))
    drawn = len(out)
    if layer == "over":
        walls = _walls(items, boxes, records)
        tiled = _tiles(items, look)
        for item in items:
            if item.get("role") != "line":
                continue
            ends = _ends(item, origin, boxes, records, tiled)
            if ends is None:
                continue
            svg, line_boxes = _line(item, ends, m,
                                    (shape_of.get(str(item.get("from")), ""), shape_of.get(str(item.get("to")), "")),
                                    origin, walls, look)
            out.append(svg)
            taken.extend(line_boxes)
        if look == "tiles":
            # As tiles, the lines go under what this layer holds, and every
            # tile, words and all, over the lines, whichever layer its place
            # puts it in: a shape in a frame sits in the layer under them, and
            # a line leaving a tile downward ran through its name. The canvas
            # draws its tiles in maxGraph's foreground the same way.
            out = out[drawn:] + out[:drawn]
            for item in items:
                if item.get("role") == "shape":
                    out.append(_box(item, boxes[str(item["key"])], m, look, tile_ground(item, by_key)))
    return "\n".join(out), taken


def _reach(item: Mapping, box: Box, m: Optional[Metrics] = None, look: str = DEFAULT_LOOK) -> Box:
    """What it takes up on the sheet, past its box: a frame's tab, half
    above its top edge; a shape's or a note's shadow, down and right; a
    tile's words, under its box and wider. The drawing's extent holds them,
    as the canvas's export does."""
    x1, y1, x2, y2 = box
    if look == "tiles":
        if item.get("role") == "shape" and m is not None:
            rows = tile_rows(item, box, m)
            wide = max([m.width(t, f[0], f[1], s) for t, f, s in rows] or [0.0])
            cx = (x1 + x2) / 2
            x1, x2 = min(x1, cx - wide / 2), max(x2, cx + wide / 2)
            y2 = max(y2, tile_box(box)[3] + TILE_GLOW) + (TILE_GAP + sum(s * LEADING for _t, _f, s in rows) if rows else 0)
        return (x1, y1, x2, y2)
    if item.get("role") == "frame" and str(item.get("label") or "").strip():
        size = float(TEXT_SIZES.get((item.get("look") or {}).get("text"), 12))
        y1 -= (size * LEADING + 4) / 2
    if casts_shadow(item):
        x2, y2 = x2 + SHADOW, y2 + SHADOW
    return (x1, y1, x2, y2)


def _outlines(items: Sequence[Mapping], look: str) -> Dict[str, str]:
    """Each shape's outline, which a line joined to it ends on: its own, or
    as tiles the tile in the middle of its box."""
    return {str(a["key"]): "tile" if look == "tiles" else str(a.get("shape") or "")
            for a in items if a.get("role") == "shape"}


def _walls(items: Sequence[Mapping], boxes: Mapping[str, Box], records: Mapping[str, Box]) -> List[Box]:
    """What a square or curved line goes around: every box of the estate
    and every shape, note and text of the diagram's own, not a frame, which
    holds things rather than standing in the way. `walls` in engine.js."""
    own = [boxes[str(a["key"])] for a in items if a.get("role") in ("shape", "note", "text")]
    return own + list(records.values())


def _pinned(box: Box, held: Sequence[float]) -> Tuple[float, float, int]:
    """An end held at a point of its box (`from_at`, `to_at`): the point,
    and the side it leaves by, as `_STEPS` counts them, right, down, left,
    up, or -1 inside the box. A corner leaves across first."""
    fx, fy = float(held[0]), float(held[1])
    side = 0 if fx == 1 else 1 if fy == 1 else 2 if fx == 0 else 3 if fy == 0 else -1
    return (box[0] + fx * (box[2] - box[0]), box[1] + fy * (box[3] - box[1]), side)


def _stub(end: object) -> Optional[Point]:
    """Where a square or curved line held at a side of a box turns from
    first: a margin out from the side, square to it."""
    if isinstance(end, tuple) and len(end) == 3 and end[2] >= 0:
        dx, dy = _STEPS[end[2]]
        return (end[0] + dx * DETOUR_MARGIN, end[1] + dy * DETOUR_MARGIN)
    return None


def _tiles(items: Sequence[Mapping], look: str) -> frozenset:
    """The keys of the shapes drawn as tiles: every shape, as Icon tiles."""
    if look != "tiles":
        return frozenset()
    return frozenset(str(i["key"]) for i in items if i.get("role") == "shape")


def _ends(item: Mapping, origin: Point, boxes: Mapping[str, Box],
          records: Mapping[str, Box], tiled: frozenset = frozenset()) -> Optional[Tuple[object, object]]:
    """What a line's two ends are on the sheet: a box of the diagram's own,
    a record's box, a point of the sheet, or a point a box holds it at
    (`_pinned`), of a shape's tile as Icon tiles; None when one is a record
    not drawn."""
    ends: List[object] = []
    for end, held in ((item.get("from"), item.get("from_at")), (item.get("to"), item.get("to_at"))):
        if isinstance(end, (list, tuple)):
            ends.append((origin[0] + float(end[0]), origin[1] + float(end[1])))
            continue
        box = boxes.get(str(end)) or records.get(str(end))
        if box is None:
            return None
        ends.append(_pinned(tile_box(box) if str(end) in tiled else box, held) if held else box)
    return ends[0], ends[1]


def own_extent(items: Sequence[Mapping], origin: Point) -> Optional[Box]:
    """Everything the diagram's own boxes take up, or None."""
    boxes = list(place(items, origin).values())
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


class Own(NamedTuple):
    """One of the diagram's own as the picture placed it, for a painter that
    is not this one: the deck draws it as a slide shape, the draw.io page as
    a cell. `layer` is where it is stacked, as `layer_of` says: "under" the
    estate, "over" it, or the index of the boundary it sits just above. A
    line's `points` run from end to end, each end on its box's outline, and
    `source` and `target` are what it is joined to, a key of the diagram's
    own or a record's id, blank for a point of the sheet."""
    key: str
    role: str
    box: Box
    layer: object
    shape: str
    fill: str
    edge: str
    dashed: bool
    size: float
    label: str
    within: str = ""
    points: Tuple[Point, ...] = ()
    ends: str = "end"
    route: str = "straight"
    source: str = ""
    target: str = ""
    #: Degrees clockwise about its middle.
    rotate: float = 0.0
    #: Where on its box each end of a line is held, or nothing.
    from_at: Tuple[float, ...] = ()
    to_at: Tuple[float, ...] = ()
    #: The ink its words are set in, and whether a hard shadow falls under it.
    words: str = INK
    shadow: bool = False
    #: How its diagram draws it, and as tiles its tile's two colors and icon.
    look: str = DEFAULT_LOOK
    tint: Tuple[str, ...] = ()
    icon: str = ""
    #: How much of its fill shows, how heavy its edge is, and the radius its
    #: corners are rounded by: 0 square, None no corners to round.
    opacity: float = 1.0
    weight: float = 1.25
    corners: Optional[float] = None
    #: How its words are set: bold, italic, underlined, struck through,
    #: where they sit (blank for its kind's place) and a note's as a list.
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    align: str = ""
    listed: bool = False
    #: Where it links to, blank for nowhere.
    link: str = ""
    #: An outline drawn dotted rather than dashed; a line's words at its
    #: start and its end, `(("start", words), ("end", words))`; and its
    #: turns, rounded or not.
    dotted: bool = False
    labels: Tuple[Tuple[str, str], ...] = ()
    turns: str = ""
    #: A line's heads at its start and its end (V16), as `heads_of` says.
    heads: Tuple[str, str] = ("none", "arrow")


def _swim_own(item: Mapping, box: Box, layer: object, names: str) -> List["Own"]:
    """A swimlane's pool or lane for another painter, from the parts the
    picture draws: itself a flat frame with no name, holding what sits in
    it, then its band and its words, each a part of it. The words go as a
    note with no fill or edge, whose ten in from its box the box gives
    back, so they sit where the picture sets them."""
    from .metrics import default_metrics
    key = str(item["key"])
    inside = list(item.get("in") or [])
    out: List[Own] = []
    for i, (kind, b, fill, label, size, bold) in enumerate(swim_parts(item, box, names, default_metrics())):
        if kind == "rect":
            out.append(Own(key if i == 0 else "%s~%d" % (key, i), "frame", b, layer, "", fill, INK, False, size, "",
                           (str(inside[-1]) if inside else "") if i == 0 else key, weight=WEIGHTS["m"], corners=0.0))
        else:
            pad = PADDING["note"]
            out.append(Own("%s~%d" % (key, i), "note", (b[0] - pad[0], b[1] - pad[1], b[2] + pad[0], b[3] + pad[1]),
                           layer, "", "none", "none", False, size, label, key, words=fill, bold=bold))
    return out


def scene(items: Sequence[Mapping], origin: Point, records: Mapping[str, Box],
          bounds: Sequence[Box] = (), look: str = DEFAULT_LOOK) -> List[Own]:
    """The diagram's own as records, in the order the list draws them: the
    same places, layers, looks and line points `paint` draws, so another
    painter cannot drift from this one. A line whose record is not on the
    drawing is left off, as the picture leaves it."""
    boxes = place(items, origin)
    shape_of = _outlines(items, look)
    walls = _walls(items, boxes, records)
    tiled = _tiles(items, look)
    by_key = {str(i.get("key")): i for i in items}
    out: List[Own] = []
    for item in items:
        key, role = str(item["key"]), str(item.get("role") or "")
        if role in ("pool", "lane"):
            out.extend(_swim_own(item, boxes[key], layer_of(item, boxes, bounds), names_of(item, by_key)))
            continue
        fill, edge, dash, size, words = _look(item)
        if role == "line":
            ends = _ends(item, origin, boxes, records, tiled)
            if ends is None:
                continue
            frm, to = item.get("from"), item.get("to")
            pts, _heads = line_route(item, ends, (shape_of.get(str(frm), ""), shape_of.get(str(to), "")), origin,
                                     walls)
            mine = item.get("look") or {}
            out.append(Own(key, role, (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts),
                                       max(p[1] for p in pts)), "over", "", "none",
                           TILE_LINE if look == "tiles" else LINE_INK,
                           mine.get("line") in DASHES, float(TEXT_SIZES.get(mine.get("text"), 11)),
                           str(item.get("label") or ""), "", tuple(pts), str(item.get("ends") or "end"),
                           str(item.get("route") or "straight"),
                           "" if isinstance(frm, (list, tuple)) else str(frm),
                           "" if isinstance(to, (list, tuple)) else str(to),
                           from_at=tuple(float(v) for v in item.get("from_at") or ()),
                           to_at=tuple(float(v) for v in item.get("to_at") or ()),
                           weight=LINE_WEIGHTS.get(str(mine.get("weight") or "m"), LINE_WEIGHTS["m"]),
                           dotted=mine.get("line") == "dotted",
                           labels=tuple((place, str(words)) for place, words in sorted((item.get("labels") or {}).items())
                                        if words),
                           turns=str(item.get("turns") or ""), heads=heads_of(item)))
            continue
        inside = list(item.get("in") or [])
        if look == "tiles":
            fill, edge, words = _tiled_paint(item)
        out.append(Own(key, role, boxes[key], layer_of(item, boxes, bounds),
                       str(item.get("shape") or ("rectangle" if role == "shape" else "")), fill, edge, bool(dash),
                       size, str(item.get("label") or ""), str(inside[-1]) if inside else "",
                       rotate=float(item.get("rotate") or 0), words=words, shadow=casts_shadow(item, look),
                       dotted=(item.get("look") or {}).get("line") == "dotted",
                       look=look, opacity=opacity_of(item), weight=weight_of(item), corners=corners_of(item, look),
                       **words_of(item), link=str(item.get("link") or ""),
                       tint=TILE_FILLS[str((item.get("look") or {}).get("fill") or "white")]
                       if look == "tiles" and role == "shape" and (item.get("look") or {}).get("fill", "white") in TILE_FILLS
                       else (),
                       icon=icon_of(item) if look == "tiles" and role == "shape" else ""))
    if look == "tiles":
        # Every tile over the lines, as the picture and the canvas draw them.
        out = [o for o in out if o.role != "shape"] + [o._replace(layer="over") for o in out if o.role == "shape"]
    return out
