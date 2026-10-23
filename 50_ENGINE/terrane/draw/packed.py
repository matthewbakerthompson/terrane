"""The app's packing layout, in Python: `layoutHierarchy(cy, dir, true, true)`.

A map is scanned, not read along its edges, so the app packs it at every
level: boundaries into rows whose shape is near the sheet's, nodes into
rows inside them. This is that code, line for line where it matters, so
that the Python drawing of a packed map lands every node where the app
does. `tests/test_draw_packed.py` holds the two equal against fixtures read
back from the running app; a change here that the app does not make, or
the other way round, fails there.

The faithful parts, in the order the app does them:

- a node's box from its label (`text_box`), the way `textBox()` sizes
  it: a calibrated glyph width, up to three lines, room for the mark in the
  corner and the technology line under the name; then made even, every box
  of one kind in the drawing as wide as the widest and as tall as the
  tallest name among them (`prepare`, `evenBoxes()`), and height added for
  a fan of edges past the third;
- a boundary's extent from the leaves inside it plus the compound padding
  and the room its own name needs, the way `extent()` does, not the way
  Cytoscape would report it, since the layout decided from this;
- bottom-left skyline packing of each level's items at a width tried
  against the sheet's shape (`pack_level`), tallest first or in the view's
  own order at the top level, whichever fits better; and a finished
  boundary moved as a unit.

The walk over the levels is the same one the layered drawings take, so it
lives once, in `layered.layout_hierarchy`, and `layout_packed` is its
grid-only call; the packing of one level is here. JavaScript's
`Math.round` rounds halves up and Python's rounds them to even, so the one
place the app rounds goes through `js_round`.
"""

from __future__ import annotations

import math
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from .shapes import (CHAR_W, CORNERED, FAN_PX, GLYPH_PATHS, LABEL_WIDTH, LAYOUT, LINE_H, PAD_X, PAD_Y,
                     PILL_PAD_X, PILL_PAD_Y, TECH_CHAR_W, TECH_H, TITLE_CHAR, TYPE_ICON_BODIES, shape_of)


def js_round(value: float) -> int:
    return int(math.floor(value + 0.5))


def title_width(label: str) -> float:
    return len(str(label or "")) * TITLE_CHAR


def title_room(label: str) -> int:
    return js_round(2 * title_width(label) + 4)


class Leaf(NamedTuple):
    id: str
    data: dict
    parent: Optional[str]
    shape: str
    #: "icon", "glyph", "ticon" or "": what sits in the top-right corner.
    corner: str
    degree: int
    w: int
    h: int


class Group(NamedTuple):
    id: str
    data: dict
    parent: Optional[str]
    depth: int


class Prepared(NamedTuple):
    """The payload as the app holds it once `drawGraph` has prepared it."""
    leaves: List[Leaf]
    groups: List[Group]
    edges: List[dict]
    by_id: Dict[str, object]


def label_box(label: str, corner: str, tech: str, degree: int) -> Tuple[int, int]:
    """A node's width and height from its own text and connections alone,
    as `labelBox()` sizes a box that has not been made even with the rest
    of its drawing."""
    w, h = text_box(label, corner, tech)
    return w, fanned(h, degree)


def fanned(h: int, degree: int) -> int:
    """`fanned()`: room on a side for a fan of edges, twelve pixels an
    edge past three."""
    return max(h, min(degree, 7) * FAN_PX) if degree > 3 else h


def text_box(label: str, corner: str, tech: str) -> Tuple[int, int]:
    """`textBox()`: what the name needs, the mark in the corner and the
    technology line under it."""
    text = str(label or "")
    one_line = len(text) * CHAR_W
    lines = min(3, max(1, math.ceil(one_line / LABEL_WIDTH)))
    w = LABEL_WIDTH if lines > 1 else max(64, one_line)
    if corner == "icon":
        w += 22
    elif corner in ("glyph", "ticon"):
        w += 10
    tech = str(tech or "")
    if tech:
        w = max(w, min(LABEL_WIDTH, len(tech) * TECH_CHAR_W))
    h = lines * LINE_H + PAD_Y + (TECH_H if tech else 0)
    return js_round(w + PAD_X), js_round(h)


def pill_box(label: str, tech: str) -> Tuple[int, int]:
    """`pillBox()`: what an offered interface's name and the protocol
    under it need, padded less than a system."""
    text = str(label or "")
    one_line = len(text) * CHAR_W
    lines = min(3, max(1, math.ceil(one_line / LABEL_WIDTH)))
    w = LABEL_WIDTH if lines > 1 else max(48, one_line)
    tech = str(tech or "")
    if tech:
        w = max(w, min(LABEL_WIDTH, len(tech) * TECH_CHAR_W))
    h = lines * LINE_H + PILL_PAD_Y + (TECH_H if tech else 0)
    return js_round(w + PILL_PAD_X), js_round(h)


def corner_of(data: dict) -> str:
    """What `drawGraph` puts in the corner: the provider's mark where one
    travels, else the component's glyph, else the type's own small mark on
    a shape with a corner to hold it."""
    if data.get("icon"):
        return "icon"
    if GLYPH_PATHS.get(str(data.get("componentCategory") or "")):
        return "glyph"
    entity_type = str(data.get("entityType") or "")
    if shape_of(entity_type) in CORNERED and entity_type in TYPE_ICON_BODIES:
        return "ticon"
    return ""


def prepare(payload: dict) -> Prepared:
    degree: Dict[str, int] = {}
    edges = []
    for element in payload.get("elements", []):
        data = element["data"]
        if data.get("source"):
            edges.append(data)
            degree[data["source"]] = degree.get(data["source"], 0) + 1
            degree[data["target"]] = degree.get(data["target"], 0) + 1
    leaves: List[Leaf] = []
    groups: List[Group] = []
    sized: List[Tuple[dict, Optional[str], str, str, int, int, int]] = []
    widest: Dict[str, int] = {}
    tallest: Dict[str, int] = {}
    for element in payload.get("elements", []):
        data = element["data"]
        if data.get("source"):
            continue
        parent = data.get("parent") or None
        if data.get("isGroup"):
            groups.append(Group(data["id"], data, parent, int(data.get("depth") or 1)))
            continue
        corner = corner_of(data)
        shape = shape_of(str(data.get("entityType") or ""))
        if shape == "pill":
            w, h = pill_box(data.get("label", ""), data.get("tech") or "")
        else:
            w, h = text_box(data.get("label", ""), corner, data.get("tech") or "")
        kind = str(data.get("entityType") or "")
        widest[kind] = max(widest.get(kind, 0), w)
        tallest[kind] = max(tallest.get(kind, 0), h)
        sized.append((data, parent, shape, corner, degree.get(data["id"], 0), w, h))
    # Even boxes, as `evenBoxes()` makes them: every box of one kind is as
    # wide as the widest of them and as tall as the tallest name among
    # them, and only a fan of connections makes one taller.
    for data, parent, shape, corner, deg, _w, _h in sized:
        kind = str(data.get("entityType") or "")
        leaves.append(Leaf(data["id"], data, parent, shape, corner, deg, widest[kind], fanned(tallest[kind], deg)))
    by_id: Dict[str, object] = {}
    for group in groups:
        by_id[group.id] = group
    for leaf in leaves:
        by_id[leaf.id] = leaf
    return Prepared(leaves, groups, edges, by_id)


class Layout(NamedTuple):
    #: Leaf id to its center and size: x, y, w, h.
    leaves: Dict[str, Tuple[float, float, int, int]]
    #: Boundary id to its extent: x1, y1, x2, y2, the box the app sized the
    #: layout with.
    groups: Dict[str, Tuple[float, float, float, float]]
    #: The sheet's width over its height, clamped the way the app clamps it.
    ratio: float


class _Item(NamedTuple):
    id: str
    is_group: bool
    w: float
    h: float
    box: Tuple[float, float, float, float]


def sheet_ratio(width: float, height: float) -> float:
    return max(0.6, min(2.4, width / height)) if height else 1.4


def pack_at(order: Sequence[_Item], width: float):
    """Bottom-left skyline packing: each item to the lowest spot it fits,
    leftmost among equals. Items of one size fill rows exactly as a row
    packer would, so a boundary's leaves keep their order; boundaries of
    unequal size slide under one another instead of leaving a hole beside
    every tall one."""
    gap_x, gap_y = LAYOUT["gapX"], LAYOUT["gapY"]
    sky = [(0.0, width, 0.0)]  # x, w, y
    at: Dict[str, Tuple[float, float]] = {}
    max_x = max_y = 0.0
    for it in order:
        w, h = it.w + gap_x, it.h + gap_y
        spot = None
        for i, (sx, _sw, _sy) in enumerate(sky):
            x = sx
            if x > 0 and x + it.w > width + 1:
                continue
            y = 0.0
            j = i
            while j < len(sky) and sky[j][0] < x + w:
                y = max(y, sky[j][2])
                j += 1
            if spot is None or y < spot[1] or (y == spot[1] and x < spot[0]):
                spot = (x, y)
        px, py = spot
        at[it.id] = (px + it.w / 2, py + it.h / 2)
        max_x = max(max_x, px + it.w)
        max_y = max(max_y, py + it.h)
        nxt = []
        for sx, sw, sy in sky:
            s1, s2 = sx, sx + sw
            if s2 <= px or s1 >= px + w:
                nxt.append((sx, sw, sy))
                continue
            if s1 < px:
                nxt.append((s1, px - s1, sy))
            if s2 > px + w:
                nxt.append((px + w, s2 - (px + w), sy))
        nxt.append((px, w, py + h))
        nxt.sort(key=lambda s: s[0])
        sky = nxt
    return at, max_x, max_y


def pack_level(items: Sequence[_Item], nested: bool, ratio: float,
               lane_at: Optional[Dict[str, int]]) -> Dict[str, Tuple[float, float]]:
    """One level packed into rows whose total shape is near the sheet's. At
    the top level the items are boundaries of unequal size, so the tallest
    go first and the row width is one of several tried, for the packing
    whose shape is nearest the sheet's with the least empty space; inside
    a boundary the order is the view's own and stays. The score is the fit
    itself: the sheet height a packing needs once its width is scaled to the
    sheet's."""
    area = widest = sum_w = 0.0
    for it in items:
        area += (it.w + LAYOUT["gapX"]) * (it.h + LAYOUT["gapY"])
        widest = max(widest, it.w)
        sum_w += it.w + LAYOUT["gapX"]
    wanted = 1.5 if nested else ratio
    if lane_at:
        orders = [sorted(items, key=lambda it: lane_at[it.id])]
    elif nested:
        orders = [list(items)]
    else:
        orders = [list(items), sorted(items, key=lambda it: (-it.h, -it.w))]
    base = max(widest, math.sqrt(area * wanted))
    tries = [1] if nested else [0.6, 0.75, 0.9, 1, 1.15, 1.3, 1.5, 1.75, 2]
    best = None
    for candidate in orders:
        for f in tries:
            at, w, h = pack_at(candidate, max(widest, min(sum_w, base * f)))
            score = max(w / wanted, h)
            if best is None or score < best[0]:
                best = (score, at)
    return best[1]


def layout_packed(payload: dict, sheet_width: float = 1240, sheet_height: float = 871.4375,
                  prepared: Optional[Prepared] = None) -> Layout:
    """Where the app puts everything on a packed map, for a sheet of this
    size. The default sheet is the app's at a 1600x1000 window with the rail
    folded, which is what the fixtures and the review pack use."""
    from .layered import layout_hierarchy
    lay = layout_hierarchy(payload, sheet_width, sheet_height, str(payload.get("layout") or "LR"), True, True,
                           prepared)
    return Layout(lay.leaves, lay.groups, lay.ratio)
