"""The app's layered layout, in Python: `layoutHierarchy()` whole,
`bestDirection()` and `planPieces()`, the three pieces.

A diagram is read along its edges, so the app ranks it: at every boundary
level the children are a graph for dagre, boundaries first, with the edges
between what they hold drawn between them. A level of boundaries of a field
the view orders takes one rank each in that order instead. A level with no
edge between its children is packed the way a map is. The levels inside a
boundary run across the drawing's own direction, so each boundary is a lane
and the lanes stack; only the top level may turn, and only when the view's
own direction is clearly the worse fit for the sheet. This is that code,
line for line where it matters, and `tests/test_draw_layered.py` holds it
equal to the running app through fixtures read back from Cytoscape.

`layout_hierarchy` is the whole of the app's function, all three branches;
`packed.layout_packed` is its grid-only call. `best_direction` lays the
top level out both ways and keeps the one that fits the sheet at the
larger zoom, preferring the view's own unless the other is clearly better.
`route_layered` is the orthogonal router: every edge leaves a node along
the axis the layout made room in, turns once across the gap at the turn
that passes behind the fewest nodes, and comes in; a node's edges on one
side fan along it in the order of where they are going.
"""

from __future__ import annotations

import json
import math
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from . import dagre
from .labels import label_px
from .packed import (Group, Leaf, Prepared, _Item, js_round, pack_level, prepare, sheet_ratio, title_room,
                     title_width)
from .shapes import LAYOUT, shape_of

Box = Tuple[float, float, float, float]
Point = Tuple[float, float]

#: How many loose systems a lane puts in one row before starting another.
LANE_ROW = 6

#: The shares of its breadth the top level is tucked inside besides the
#: whole of it, for the one that fits the sheet best.
TUCK_BREADTHS = (0.9, 0.8, 0.7, 0.6, 0.5)

#: Shapes with a straight side for a fan of edges to leave from.
FANNED = {"round-rectangle", "rectangle", "cut-rectangle", "octagon", "round-octagon", "pill"}
FAN_STEP = 14
FAN_INSET = 8
FACE_GAP = 8
#: Middle pieces of different edges keep this far apart along the axis they
#: cross, so two edges through one corridor read as two.
TURN_APART = 28
#: A run across the gap closer than this to a boundary's border, along it,
#: reads as the border; one step of the turn ladder clears it.
BORDER_NEAR = 8
#: The fanned shapes whose sides are straight where the fan puts a line, so
#: a line's end is pinned to its place in the fan (`PORTED` in app.js).
PORTED = {"round-rectangle", "rectangle", "cut-rectangle", "pill"}
#: How far past the end of a boundary's name a port is moved to clear it.
NAME_CLEAR = 6.0


class LayeredLayout(NamedTuple):
    #: Leaf id to its center and size: x, y, w, h.
    leaves: Dict[str, Tuple[float, float, int, int]]
    #: Boundary id to its extent as the layout sized it: x1, y1, x2, y2.
    groups: Dict[str, Box]
    ratio: float
    #: The direction drawn, "TB" or "LR".
    direction: str
    #: Edge id to the axis the layout ranked it along, "x" or "y", for the
    #: edges that cross between children at some level.
    edge_axis: Dict[str, str]


#: The shapes Cytoscape draws as plain polygons, whose border meets itself in
#: a miter at every corner; a rectangle's miters add nothing, and the
#: rounded shapes have no corner to miter.
MITERED = {"diamond", "hexagon", "octagon", "pentagon", "rhomboid", "tag", "triangle"}


def miter_bounds(unit_points: Sequence[float], cx: float, cy: float, w: float, h: float, t: float) -> Box:
    """Where a polygon's border reaches: each edge moved out by `t`, and the
    corners where neighboring moved edges meet. Cytoscape's `miterBounds`,
    which is how a hexagon's tips push its box out sideways."""
    pts = [(cx + w / 2 * unit_points[i], cy + h / 2 * unit_points[i + 1]) for i in range(0, len(unit_points), 2)]
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area < 0:
        pts.reverse()
    n = len(pts)
    lines = []
    for i in range(n):
        (fx, fy), (px, py) = pts[i], pts[(i + 1) % n]
        gx, gy = px - fx, py - fy
        length = math.hypot(gy, gx)
        nx, ny = (gy / length, -gx / length) if length else (0.0, 0.0)
        lines.append(((fx + nx * t, fy + ny * t), (px + nx * t, py + ny * t)))
    corners = []
    for i in range(n):
        (ax, ay), (bx, by) = lines[(i - 1) % n]
        (cx2, cy2), (dx, dy) = lines[i]
        lx, ly = bx - ax, by - ay
        ux, uy = dx - cx2, dy - cy2
        cross = lx * uy - ly * ux
        if abs(cross) < 1e-9:
            corners.append((ax + lx * 0.5, ay + ly * 0.5))
            continue
        d = ((cx2 - ax) * uy - (cy2 - ay) * ux) / cross
        corners.append((ax + lx * d, ay + ly * d))
    return (min(c[0] for c in corners), min(c[1] for c in corners),
            max(c[0] for c in corners), max(c[1] for c in corners))


def leaf_box(leaf: Leaf, center: Tuple[float, float]) -> Box:
    """Cytoscape's bounding box of a leaf without its label, which is what
    the router and the sheet fit read: the body with its border, the border's
    miters where the shape has sharp corners, and a pixel more on each side
    for the antialiasing."""
    x, y = center
    border = float(leaf.data.get("strokeWidth") or 1)
    half = border / 2
    x1, y1, x2, y2 = x - leaf.w / 2 - half, y - leaf.h / 2 - half, x + leaf.w / 2 + half, y + leaf.h / 2 + half
    if leaf.shape in MITERED and border > 0:
        from .shapes import POLYGONS
        mx1, my1, mx2, my2 = miter_bounds(POLYGONS[leaf.shape], x, y, leaf.w, leaf.h, half)
        x1, y1, x2, y2 = min(x1, mx1), min(y1, my1), max(x2, mx2), max(y2, my2)
    return (x1 - 1, y1 - 1, x2 + 1, y2 + 1)


def layout_hierarchy(payload: dict, sheet_width: float, sheet_height: float, direction: str,
                     force_grid: bool, grid_root: bool, prepared: Optional[Prepared] = None,
                     tuck: bool = True) -> LayeredLayout:
    """`layoutHierarchy(cy, dir, forceGrid, gridRoot, untucked)` for a sheet
    of this size: where every leaf lands, and the axis each crossing edge
    was ranked along. `tuck=False` is dagre's own ranking at every level,
    which is what `best_direction` decides the direction by."""
    prep = prepared or prepare(payload)
    ratio = sheet_ratio(sheet_width, sheet_height)
    lanes: Dict[str, List[str]] = {k: list(v) for k, v in (payload.get("lanes") or {}).items()}
    edge_axis: Dict[str, str] = {}
    positions: Dict[str, Tuple[float, float]] = {}
    children: Dict[Optional[str], List[object]] = {}
    parent_of: Dict[str, Optional[str]] = {}
    # Cytoscape hands a parent its children in the order they were added:
    # the payload's, boundaries first and then leaves.
    for group in prep.groups:
        children.setdefault(group.parent, []).append(group)
        parent_of[group.id] = group.parent
    for leaf in prep.leaves:
        children.setdefault(leaf.parent, []).append(leaf)
        parent_of[leaf.id] = leaf.parent

    def extent(node) -> Box:
        if isinstance(node, Leaf):
            x, y = positions.get(node.id, (0.0, 0.0))
            return (x - node.w / 2, y - node.h / 2, x + node.w / 2, y + node.h / 2)
        box = None
        for child in children.get(node.id, []):
            e = extent(child)
            box = e if box is None else (min(box[0], e[0]), min(box[1], e[1]), max(box[2], e[2]), max(box[3], e[3]))
        if box is None:
            return (0.0, 0.0, 0.0, 0.0)
        pad = LAYOUT["boundaryPad"]
        extra = max(0, title_room(node.data.get("label", "")) + (28 if node.data.get("icon") else 0)
                    - (box[2] - box[0])) / 2
        return (box[0] - pad - extra, box[1] - pad - LAYOUT["boundaryLabel"], box[2] + pad + extra, box[3] + pad)

    def lane_order(items: Sequence[_Item]) -> Optional[Dict[str, int]]:
        if not items:
            return None
        first = prep.by_id[items[0].id]
        field = first.data.get("kind") if isinstance(first, Group) else None
        order = lanes.get(field) if field else None
        if not order:
            return None
        out: Dict[str, int] = {}
        for i, it in enumerate(items):
            node = prep.by_id[it.id]
            if not isinstance(node, Group) or node.data.get("kind") != field:
                return None
            value = str(node.data.get("value"))
            out[it.id] = order.index(value) if value in order else len(order) + i
        return out

    def leaves_under(group_id: str) -> List[Leaf]:
        out: List[Leaf] = []
        for child in children.get(group_id, []):
            if isinstance(child, Leaf):
                out.append(child)
            else:
                out.extend(leaves_under(child.id))
        return out

    def place(parent: Optional[Group]) -> None:
        kids = children.get(parent.id if parent else None, [])
        for kid in kids:
            if isinstance(kid, Group):
                place(kid)
        if not kids:
            return
        # A map's top level is a catalog of boundaries: pack them into rows
        # rather than chaining them by whatever edges cross between them.
        grid = force_grid or (grid_root and parent is None)
        by_id = {kid.id for kid in kids}
        items = []
        for kid in kids:
            e = extent(kid)
            items.append(_Item(kid.id, isinstance(kid, Group), e[2] - e[0], e[3] - e[1], e))

        # An edge between two descendants of different children is an edge
        # between those children, at this level.
        def within(node_id: str) -> Optional[str]:
            cur: Optional[str] = node_id
            while cur is not None and cur not in by_id:
                cur = parent_of.get(cur)
            return cur

        seen = set()
        among: List[Tuple[str, str]] = []
        level_dir = (("LR" if direction == "TB" else "TB") if parent else direction)
        level_axis = "y" if level_dir == "TB" else "x"
        # The gap between ranks makes room for the widest label that has to
        # sit in it; a boundary's padding on each side of the gap gives some.
        widest = 0.0
        if not grid:
            for e in prep.edges:
                if e["source"] not in parent_of or e["target"] not in parent_of:
                    continue
                a, b = within(e["source"]), within(e["target"])
                if not a or not b or a == b:
                    continue
                edge_axis[e["id"]] = level_axis
                widest = max(widest, label_px(str(e.get("label") or "")))
                key = a + ">" + b
                if key in seen:
                    continue
                seen.add(key)
                among.append((a, b))
        all_groups = all(it.is_group for it in items)
        ranksep = max(LAYOUT["ranksep"],
                      (widest + 24 - (2 * LAYOUT["boundaryPad"] if all_groups else 0)) if widest else 0)

        target: Dict[str, Tuple[float, float]] = {}
        lane = None if grid else lane_order(items)
        if lane:
            # A tier diagram reads edge to data whatever the edges say: the
            # boundaries of a laned field take one rank each in the field's
            # order, centered across the axis, and the edges go where they go.
            stacked = level_dir == "TB"
            cursor = 0.0
            for it in sorted(items, key=lambda it: lane[it.id]):
                size = it.h if stacked else it.w
                target[it.id] = (0.0, cursor + size / 2) if stacked else (cursor + size / 2, 0.0)
                cursor += size + ranksep
        elif among:
            # Inside a boundary the ranks run across the diagram's own
            # direction, so each boundary is a lane and the lanes stack.
            rankdir = level_dir

            def ranked(rd: str) -> Dict[str, Tuple[float, float]]:
                g = dagre.Graph()
                g.set_graph({"rankdir": rd, "nodesep": LAYOUT["nodesep"], "ranksep": ranksep,
                             "edgesep": LAYOUT["edgesep"], "marginx": 0, "marginy": 0})
                g.set_default_edge_label(lambda v, w, name: {})
                for it in items:
                    g.set_node(it.id, {"width": it.w, "height": it.h})
                for a, b in among:
                    g.set_edge(a, b)
                # Inside a lane, what nothing connects to runs along the band
                # in rows rather than stacking across it: chaining the loose
                # leaves with ranking-only edges, a row's worth at a time,
                # lays each chain out as a row under the connected ones.
                if parent and lanes.get(str(parent.data.get("kind") or "")):
                    touched = {a for a, _ in among} | {b for _, b in among}
                    loose = [it for it in items if it.id not in touched and not it.is_group]
                    for r in range(len(loose) - 1):
                        if (r + 1) % LANE_ROW != 0:
                            g.set_edge(loose[r].id, loose[r + 1].id)
                dagre.layout(g)
                return {it.id: (g.node(it.id)["x"], g.node(it.id)["y"]) for it in items}

            def extent_of(t: Dict[str, Tuple[float, float]]) -> Tuple[float, float]:
                x1 = y1 = math.inf
                x2 = y2 = -math.inf
                for it in items:
                    cx, cy = t[it.id]
                    x1, x2 = min(x1, cx - it.w / 2), max(x2, cx + it.w / 2)
                    y1, y2 = min(y1, cy - it.h / 2), max(y2, cy + it.h / 2)
                return x2 - x1, y2 - y1

            # The sheet height a placement needs once its width is scaled to
            # the sheet's: whichever of width and height overshoots more
            # decides.
            def sheet_score(t: Dict[str, Tuple[float, float]]) -> float:
                w, h = extent_of(t)
                return max(w / ratio, h)

            # A level that holds a boundary is tucked as soon as it is ranked.
            holds_group = any(it.is_group for it in items)
            preds: Dict[str, List[str]] = {}
            for a, b in among:
                preds.setdefault(b, []).append(a)

            def arranged(rd: str, breadth: float = 1.0):
                """Dagre's ranking of the level, and what is drawn of it:
                tucked, or as it was drawn before tucking."""
                raw = ranked(rd)
                plain = dict(raw)
                if all_groups:
                    compact_ranks(items, plain, rd == "TB", ranksep)
                    center_columns(items, plain, rd == "TB")
                if not (tuck and holds_group and len(items) > 1):
                    return raw, plain
                tucked = dict(raw)
                tuck_ranks(items, tucked, rd == "TB", ranksep, preds, breadth)
                # Tucked, everything hangs from the start across; each
                # column then sits centered across the drawing where it can,
                # as a level of boundaries always did.
                center_columns(items, tucked, rd == "TB")
                # A row of leaves that a hung boundary stands in front of
                # goes after it, and the level can come out longer than it
                # was; and a level tucked into no less room is only moved
                # about. Either way it is drawn as it was.
                if breadth == 1.0:
                    (tw, th), (pw, ph) = extent_of(tucked), extent_of(plain)
                    if tw > pw + 1e-9 or th > ph + 1e-9 or (tw > pw - 1 and th > ph - 1):
                        return raw, plain
                return raw, tucked

            raw, target = arranged(rankdir)
            # Only the outermost arrangement turns, and only when the view's
            # own direction is clearly the worse fit, so a drawing an author
            # read top to bottom stays that way unless the sheet cannot
            # show it. Weighed as dagre ranks it, as it always was: tucking
            # takes space out and does not turn a drawing (`tuckRanks`).
            if parent is None and len(items) > 1:
                other = "LR" if rankdir == "TB" else "TB"
                raw_turned, turned = arranged(other)
                if sheet_score(raw_turned) < sheet_score(raw) / 1.25:
                    target = turned
                    rankdir = other
                    turned_axis = "y" if rankdir == "TB" else "x"
                    for e in prep.edges:
                        if e["source"] not in parent_of or e["target"] not in parent_of:
                            continue
                        a, b = within(e["source"]), within(e["target"])
                        if a and b and a != b:
                            edge_axis[e["id"]] = turned_axis
            # The top level tucked inside the breadth dagre gave it can come
            # out long and thin with the sheet no better filled, so narrower
            # breadths are tried too and the one that fits the sheet best is
            # kept, the direction already settled.
            if tuck and parent is None and holds_group and len(items) > 1:
                best = sheet_score(target)
                for breadth in TUCK_BREADTHS:
                    tried = arranged(rankdir, breadth)[1]
                    score = sheet_score(tried)
                    if score < best - 1e-9:
                        best, target = score, tried
        else:
            target = pack_level(items, parent is not None, ratio, lane_order(items))

        for it in items:
            to = target[it.id]
            if not it.is_group:
                positions[it.id] = to
                continue
            # A finished boundary moves as a unit: shift every leaf inside it.
            dx = to[0] - (it.box[0] + it.box[2]) / 2
            dy = to[1] - (it.box[1] + it.box[3]) / 2
            for leaf in leaves_under(it.id):
                x, y = positions[leaf.id]
                positions[leaf.id] = (x + dx, y + dy)

    place(None)
    leaves_out = {leaf.id: (positions[leaf.id][0], positions[leaf.id][1], leaf.w, leaf.h) for leaf in prep.leaves}
    groups_out = {group.id: extent(group) for group in prep.groups}
    return LayeredLayout(leaves_out, groups_out, ratio, direction, edge_axis)


def compact_ranks(items: Sequence[_Item], target: Dict[str, Tuple[float, float]], vertical: bool,
                  ranksep: float) -> None:
    """Dagre leaves a hole wherever a column's first ranks are empty. In rank
    order, each boundary slides toward the start of the rank axis until it
    would come within a rank gap of something it overlaps across that axis,
    so nothing changes its place relative to what is beside or before it,
    and nothing ever moves the other way. How a level of boundaries was
    drawn before tucking, and still is where tucking takes no space out."""
    def pos(it: _Item) -> float:
        t = target[it.id]
        return t[1] if vertical else t[0]

    def half(it: _Item) -> float:
        return (it.h if vertical else it.w) / 2

    def span(it: _Item) -> Tuple[float, float]:
        t = target[it.id]
        return (t[0] - it.w / 2, t[0] + it.w / 2) if vertical else (t[1] - it.h / 2, t[1] + it.h / 2)

    origin = min(pos(it) - half(it) for it in items)
    done: List[Tuple[float, float, float]] = []
    for it in sorted(items, key=pos):
        s = span(it)
        floor = origin
        for lo, hi, end in done:
            if lo < s[1] + 8 and hi > s[0] - 8:
                floor = max(floor, end + ranksep)
        moved = min(pos(it), floor + half(it))
        x, y = target[it.id]
        target[it.id] = (x, moved) if vertical else (moved, y)
        done.append((s[0], s[1], moved + half(it)))


def tuck_ranks(items: Sequence[_Item], target: Dict[str, Tuple[float, float]], vertical: bool,
               ranksep: float, preds: Dict[str, List[str]], breadth: float = 1.0) -> None:
    """Dagre ranks a boundary as one node and centers each rank across the
    axis, so a level that holds boundaries came out as columns of very
    different sizes with the space between them blank. Rank by rank: each
    boundary goes to the earliest place along the rank axis that is clear
    of what is already placed, inside the breadth the level already has,
    nearest the start across it; then the rank's leaves move as one row,
    keeping their places across and their alignment, to the first place
    clear of what they would sit beside. What an edge leaves a leaf for
    stays a rank gap after that leaf; what an edge leaves a boundary for may
    sit beside the boundary, never before its start. `breadth` narrows the
    level's breadth to that share of it, never below its widest boundary.
    `tuckRanks()` in the app, which says what each rule was for."""
    gap = LAYOUT["nodesep"]

    def along(it: _Item) -> float:
        x, y = target[it.id]
        return y - it.h / 2 if vertical else x - it.w / 2

    def across(it: _Item) -> float:
        x, y = target[it.id]
        return x - it.w / 2 if vertical else y - it.h / 2

    def size_a(it: _Item) -> float:
        return it.h if vertical else it.w

    def size_c(it: _Item) -> float:
        return it.w if vertical else it.h

    lo, hi, origin = math.inf, -math.inf, math.inf
    ranks: Dict[int, List[_Item]] = {}
    by_id: Dict[str, _Item] = {}
    for it in items:
        lo = min(lo, across(it))
        hi = max(hi, across(it) + size_c(it))
        origin = min(origin, along(it))
        # Dagre puts every node of a rank on one center line.
        x, y = target[it.id]
        ranks.setdefault(js_round(y if vertical else x), []).append(it)
        by_id[it.id] = it
    widest = max((size_c(it) for it in items if it.is_group), default=0.0)
    hi = max(lo + widest, lo + (hi - lo) * breadth)
    # Id to (along start, along end, across start, across end).
    placed: Dict[str, Tuple[float, float, float, float]] = {}

    def floor_of(it: _Item) -> float:
        f = origin
        for pid in preds.get(it.id, []):
            p = placed.get(pid)
            if p is not None:
                f = max(f, p[0] if by_id[pid].is_group else p[1] + ranksep)
        return f

    def put(it: _Item, a: float, c: float) -> None:
        big_a, big_c = size_a(it), size_c(it)
        placed[it.id] = (a, a + big_a, c, c + big_c)
        target[it.id] = (c + big_c / 2, a + big_a / 2) if vertical else (a + big_a / 2, c + big_c / 2)

    def clear(a: float, c: float, big_a: float, big_c: float) -> bool:
        for p in placed.values():
            if a < p[1] + ranksep and a + big_a > p[0] - ranksep and c < p[3] + gap and c + big_c > p[2] - gap:
                return False
        return True

    for key in sorted(ranks):
        rank = sorted(ranks[key], key=across)
        for it in rank:
            if not it.is_group:
                continue
            big_a, big_c, floor = size_a(it), size_c(it), floor_of(it)
            ends = list(placed.values())
            alongs = sorted(a for a in [origin, along(it)] + [p[1] + ranksep for p in ends] if a >= floor - 1e-9)
            acrosses = sorted(c for c in [lo, across(it)] + [p[3] + gap for p in ends]
                              if c >= lo - 1e-9 and c + big_c <= hi + 1e-9)
            spot = None
            for a in alongs:
                for c in acrosses:
                    if clear(a, c, big_a, big_c):
                        spot = (a, c)
                        break
                if spot:
                    break
            # Nothing fits inside the breadth: after everything, where it was.
            if spot is None:
                last = floor
                for p in ends:
                    last = max(last, p[1] + ranksep)
                spot = (last, across(it))
            put(it, spot[0], spot[1])
        row = [it for it in rank if not it.is_group]
        if not row:
            continue
        top, floor = math.inf, -math.inf
        for it in row:
            top = min(top, along(it))
            floor = max(floor, floor_of(it))
        for it in row:
            c1, c2 = across(it), across(it) + size_c(it)
            for p in placed.values():
                if p[2] < c2 + 8 and p[3] > c1 - 8:
                    floor = max(floor, p[1] + ranksep)
        offs = [along(it) - top for it in row]
        for i, it in enumerate(row):
            put(it, floor + offs[i], across(it))


def _js_key_order(keys: Sequence[int]) -> List[int]:
    """`Object.keys` on an object keyed by integers: the non-negative ones
    first in numeric order, then the rest as they were added."""
    return sorted((k for k in keys if k >= 0)) + [k for k in keys if k < 0]


def center_columns(items: Sequence[_Item], target: Dict[str, Tuple[float, float]], vertical: bool) -> None:
    """Boundaries that start at the same place along the rank axis are a
    column, and each column sits centered across the drawing, where the
    move overlaps nothing in another column."""
    def start(it: _Item) -> float:
        t = target[it.id]
        return t[1] - it.h / 2 if vertical else t[0] - it.w / 2

    def span(it: _Item) -> Tuple[float, float]:
        t = target[it.id]
        return (t[0] - it.w / 2, t[0] + it.w / 2) if vertical else (t[1] - it.h / 2, t[1] + it.h / 2)

    def rank_span(it: _Item) -> Tuple[float, float]:
        t = target[it.id]
        return (t[1] - it.h / 2, t[1] + it.h / 2) if vertical else (t[0] - it.w / 2, t[0] + it.w / 2)

    lo, hi = math.inf, -math.inf
    columns: Dict[int, List[_Item]] = {}
    for it in items:
        s = span(it)
        lo, hi = min(lo, s[0]), max(hi, s[1])
        columns.setdefault(js_round(start(it) / 8), []).append(it)
    middle = (lo + hi) / 2
    for key in _js_key_order(list(columns)):
        column = columns[key]
        c_lo, c_hi = math.inf, -math.inf
        for it in column:
            s = span(it)
            c_lo, c_hi = min(c_lo, s[0]), max(c_hi, s[1])
        shift = middle - (c_lo + c_hi) / 2
        if abs(shift) < 1:
            continue
        # Nothing in another column may end up under a moved boundary.
        clear = True
        for it in column:
            r, s = rank_span(it), span(it)
            for other in items:
                if other in column:
                    continue
                orr, os_ = rank_span(other), span(other)
                along = r[0] < orr[1] + 8 and r[1] > orr[0] - 8
                across = s[0] + shift < os_[1] + 8 and s[1] + shift > os_[0] - 8
                if along and across:
                    clear = False
        if not clear:
            continue
        for it in column:
            x, y = target[it.id]
            target[it.id] = (x + shift, y) if vertical else (x, y + shift)


def elements_box(prep: Prepared, lay: LayeredLayout, metrics) -> Box:
    """What `cy.elements().boundingBox()` spans once the layout has run and
    before the labels are placed: every leaf with its border, every
    boundary with its padding and border, and every edge's label in its
    card at the chord's midpoint, which is where a straight edge carries
    it. `metrics` measures the faces."""
    boxes: List[Box] = []
    centers: Dict[str, Tuple[float, float]] = {}
    for leaf in prep.leaves:
        x, y, _, _ = lay.leaves[leaf.id]
        centers[leaf.id] = (x, y)
        boxes.append(leaf_box(leaf, (x, y)))
    memo: Dict[str, Box] = {}
    for group in prep.groups:
        boxes.append(group_box(prep, lay, group, memo))
    for e in prep.edges:
        text = str(e.get("label") or "")
        if not text or e["source"] not in centers or e["target"] not in centers:
            continue
        sx, sy = centers[e["source"]]
        tx, ty = centers[e["target"]]
        mx, my = (sx + tx) / 2, (sy + ty) / 2
        # Text, three of padding each side and the hairline border.
        hw, hh = (metrics.width(text, "Geist", 500, 10) + 6 + 1) / 2, (10 + 6 + 1) / 2
        boxes.append((mx - hw, my - hh, mx + hw, my + hh))
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


#: A boundary's name: 11px Geist 600 on one line, set `text-valign: top`
#: and brought down nineteen pixels into the box's own padding.
BOUNDARY_FONT = 11
BOUNDARY_LABEL_DOWN = 19


def boundary_lines(group: Group) -> List[str]:
    """The lines a boundary's name is drawn on: one. Wrapped at the width
    every node label wraps at, "account prod-riskops" broke in two, and
    with the margin set for one line the first sat on the border; the box
    is already at least twice the name's width, so the line has its room."""
    return [str(group.data.get("label") or "")]


def boundary_name(box: Box, group: Group) -> Box:
    """The corner a boundary's name holds, inside the box Cytoscape draws
    for it: the padding's depth, and the name's nominal width with the
    padding before and after. What the label placer keeps clear, and what
    the router keeps its runs off."""
    return (box[0], box[1], min(box[2], box[0] + 24 + title_width(str(group.data.get("label") or ""))),
            min(box[3], box[1] + 30))


def _name_advance() -> Dict[str, float]:
    from .metrics import _PATH
    data = json.loads(_PATH.read_text(encoding="utf-8"))
    advance = data["faces"]["Geist/600"]["advance"]
    size = float(data.get("size") or 100)
    return {chr(i): round(advance[chr(i)] * BOUNDARY_FONT / size, 2) for i in range(32, 127) if chr(i) in advance}


#: Geist 600 at 11px, each printable glyph's advance rounded to the
#: hundredth: `NAME_ADVANCE` in app.js, which a test holds equal to this.
NAME_ADVANCE: Dict[str, float] = _name_advance()


def name_width(label: str) -> float:
    """`nameWidth()`: a boundary's name as wide as Chrome draws it, summed
    the way the app sums it, without the kerning: a pixel or two wide where
    a pair kerns, the safe side for a box a line keeps out of."""
    w = 0.0
    for ch in str(label or ""):
        w += NAME_ADVANCE.get(ch, NAME_ADVANCE["n"])
    return w


def boundary_word(box: Box, group: Group) -> Box:
    """The name itself, in Cytoscape's box for its boundary: centered half
    its nominal width past twelve in, as wide as it is drawn, with four
    pixels of air; seven down, eleven high. What the three-piece router
    keeps its runs off: the padding beside the word is open ground
    (`planPieces()` says what counting it cost)."""
    label = str(group.data.get("label") or "")
    mid, hw = box[0] + 13 + title_width(label) / 2, name_width(label) / 2 + 4
    return (max(box[0], mid - hw), box[1] + 4, min(box[2], mid + hw), min(box[3], box[1] + 22))


def group_body(prep: Prepared, lay: LayeredLayout, group: Group,
               memo: Optional[Dict[str, Box]] = None) -> Box:
    """The box Cytoscape draws for a compound, inside its border: its
    children's boxes and borders, plus the padding, widened for its own
    name."""
    memo = memo if memo is not None else {}
    if group.id in memo:
        return memo[group.id]
    box = None
    for child in _children_of(prep, group.id):
        if isinstance(child, Leaf):
            e = leaf_box(child, lay.leaves[child.id][:2])
        else:
            e = group_box(prep, lay, child, memo)
        box = e if box is None else (min(box[0], e[0]), min(box[1], e[1]), max(box[2], e[2]), max(box[3], e[3]))
    if box is None:
        x1, y1, x2, y2 = lay.groups[group.id]
        box = (x1 + 24, y1 + 24, x2 - 24, y2 - 24)
    room = title_room(group.data.get("label", "")) + (28 if group.data.get("icon") else 0) - (box[2] - box[0])
    extra = max(0.0, room) / 2
    out = (box[0] - 24 - extra, box[1] - 24, box[2] + 24 + extra, box[3] + 24)
    memo[group.id] = out
    return out


def group_border(group: Group) -> float:
    return 1.4 if group.data.get("bkey") else 1.0


def group_box(prep: Prepared, lay: LayeredLayout, group: Group,
              memo: Optional[Dict[str, Box]] = None) -> Box:
    """Cytoscape's bounding box of a compound: its body, its border and a
    pixel of antialiasing. Its name is on one line inside its padding, so
    it reaches nothing the box does not."""
    x1, y1, x2, y2 = group_body(prep, lay, group, memo)
    grow = (group_border(group) + 2) / 2
    return (x1 - grow, y1 - grow, x2 + grow, y2 + grow)


def _children_of(prep: Prepared, group_id: str) -> List[object]:
    kids: List[object] = [g for g in prep.groups if g.parent == group_id]
    kids.extend(leaf for leaf in prep.leaves if leaf.parent == group_id)
    return kids


def best_direction(payload: dict, sheet_width: float, sheet_height: float, preferred: str, metrics,
                   prepared: Optional[Prepared] = None) -> LayeredLayout:
    """`bestDirection()`: lay the drawing out both ways as dagre ranks it
    and keep the direction that fits the sheet at the larger zoom, the
    view's own unless the other is clearly better; then lay it out tucked."""
    prep = prepared or prepare(payload)

    def zoom_for(direction: str) -> float:
        lay = layout_hierarchy(payload, sheet_width, sheet_height, direction, False, False, prep, False)
        x1, y1, x2, y2 = elements_box(prep, lay, metrics)
        return min(sheet_width / max(x2 - x1, 1), sheet_height / max(y2 - y1, 1))

    other = "LR" if preferred == "TB" else "TB"
    own = zoom_for(preferred)
    alt = zoom_for(other)
    return layout_hierarchy(payload, sheet_width, sheet_height, other if alt > own * 1.3 else preferred,
                            False, False, prep)


#: Past this, a diagram with no boundaries is a ribbon and the app lays it
#: out organically instead, which has no Python answer.
RIBBON_RATIO = 6


def is_ribbon(prep: Prepared, lay: LayeredLayout, metrics) -> bool:
    """`unribbon()`'s test: a drawing with no boundaries whose extent is
    wider or taller than six to one."""
    if prep.groups:
        return False
    x1, y1, x2, y2 = elements_box(prep, lay, metrics)
    ratio = (x2 - x1) / max(y2 - y1, 1)
    return ratio > RIBBON_RATIO or ratio < 1 / RIBBON_RATIO


def layout_layered(payload: dict, sheet_width: float = 1240, sheet_height: float = 871.4375,
                   prepared: Optional[Prepared] = None, metrics=None) -> LayeredLayout:
    """Where the app puts everything on a layered diagram drawn on its dagre
    path, in the direction it would choose for a sheet of this size."""
    from .metrics import default_metrics
    return best_direction(payload, sheet_width, sheet_height, str(payload.get("layout") or "LR"),
                          metrics or default_metrics(), prepared)


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------

class Route(NamedTuple):
    edge_id: str
    #: The axis the edge leaves its source along, "x" or "y", and which way.
    axis: str
    direction: int
    #: The segment points: the turn's two corners, or one when the pieces
    #: are in line.
    points: List[Point]
    #: Where the line leaves its source and reaches its target when that is
    #: pinned to the fan rather than found on the ray from the center.
    start: Optional[Point] = None
    end: Optional[Point] = None


def route_layered(prep: Prepared, lay: LayeredLayout, down: bool) -> Dict[str, Optional[Route]]:
    """`planPieces(cy, down)`: for every edge between two leaves, the
    three-piece route, or None for an edge left free, which the app draws as
    a curve: one with no face toward the other across a gap."""
    primary = "y" if down else "x"
    centers = {leaf.id: (lay.leaves[leaf.id][0], lay.leaves[leaf.id][1]) for leaf in prep.leaves}
    leaves = {leaf.id: leaf for leaf in prep.leaves}

    def coord(point: Tuple[float, float], axis: str) -> float:
        return point[0] if axis == "x" else point[1]

    def half(leaf: Leaf, axis: str) -> float:
        return (leaf.w if axis == "x" else leaf.h) / 2

    def other(axis: str) -> str:
        return "y" if axis == "x" else "x"

    # Every leaf, for keeping runs out from behind nodes they do not touch.
    boxes = [(leaf.id, leaf_box(leaf, centers[leaf.id])) for leaf in prep.leaves]
    # And every boundary's name, kept off after the nodes: a run through a
    # name strikes the word out (`planPieces()` says where that was found
    # and why the nodes come first). The id is no node's, so no edge is
    # exempt.
    named = len(boxes)
    memo: Dict[str, Box] = {}
    # Its four borders too, after the names: the axis a border lies across,
    # where, and its span along the other; and the box itself, for the
    # borders a route crosses.
    borders: List[Tuple[str, float, float, float]] = []
    bounds: List[Box] = []
    for group in prep.groups:
        gb = group_box(prep, lay, group, memo)
        bounds.append(gb)
        boxes.append(("", boundary_word(gb, group)))
        borders.extend((("y", gb[1], gb[0], gb[2]), ("y", gb[3], gb[0], gb[2]),
                        ("x", gb[0], gb[1], gb[3]), ("x", gb[2], gb[1], gb[3])))

    def hits(b: Box, a: str, u1: float, u2: float, v: float) -> bool:
        lo, hi = min(u1, u2), max(u1, u2)
        bl, bh = (b[0], b[2]) if a == "x" else (b[1], b[3])
        cl, ch = (b[1], b[3]) if a == "x" else (b[0], b[2])
        return hi >= bl - 2 and lo <= bh + 2 and cl - 2 <= v <= ch + 2

    def crossings(b: Box, a: str, u1: float, u2: float, v: float) -> int:
        """How many of a boundary's borders a straight piece along `a`
        goes through; one on a border counts as through it."""
        cl, ch = (b[1], b[3]) if a == "x" else (b[0], b[2])
        if v < cl or v > ch:
            return 0
        lo, hi = min(u1, u2), max(u1, u2)
        bl, bh = (b[0], b[2]) if a == "x" else (b[1], b[3])
        return int(lo <= bl <= hi) + int(lo <= bh <= hi)

    # Middle pieces already laid, so a later edge through the same corridor
    # takes its own line.
    laid: List[Tuple[str, float, float, float]] = []

    def plan(s: Leaf, t: Leaf, a: str, c1: float, c2: float, label_w: float) -> dict:
        """The best three-piece route from s to t leaving along `a`: the
        turn is halfway unless another turn passes behind fewer nodes."""
        sp, tp = centers[s.id], centers[t.id]
        c = other(a)
        direction = 1 if coord(tp, a) >= coord(sp, a) else -1
        from_ = coord(sp, a) + direction * half(s, a)
        to = coord(tp, a) - direction * half(t, a)
        mid = (from_ + to) / 2

        def in_range(v: float) -> bool:
            return (v - from_) * direction > 6 and (to - v) * direction > 6

        cands = [mid]
        for d in (12, 24, 36, 48):
            if in_range(mid + d):
                cands.append(mid + d)
            if in_range(mid - d):
                cands.append(mid - d)
        for bid, b in boxes:
            if bid == s.id or bid == t.id:
                continue
            bl, bh = (b[0], b[2]) if a == "x" else (b[1], b[3])
            for v in (bl - 10, bh + 10):
                if in_range(v):
                    cands.append(v)
        # And a step either side of every boundary's border, for a turn in
        # the open ground between two boundaries.
        for b in bounds:
            bl, bh = (b[0], b[2]) if a == "x" else (b[1], b[3])
            for v in (bl - 12, bl + 12, bh - 12, bh + 12):
                if in_range(v):
                    cands.append(v)
        # A labeled edge also tries the turns that leave one piece long
        # enough to carry the label upright, with a little to spare.
        if label_w:
            for v in (from_ + direction * (label_w + 4), to - direction * (label_w + 4)):
                if in_range(v):
                    cands.append(v)
        lo, hi = min(c1, c2) - 4, max(c1, c2) + 4

        def score(turn: float) -> dict:
            n = m = 0
            for i, (bid, b) in enumerate(boxes):
                if bid == s.id or bid == t.id:
                    continue
                k = int(hits(b, a, from_, turn, c1)) + int(hits(b, c, c1, c2, turn)) + int(hits(b, a, turn, to, c2))
                if i >= named:
                    m += k
                else:
                    n += k
            x = sum(crossings(b, a, from_, turn, c1) + crossings(b, c, c1, c2, turn) + crossings(b, a, turn, to, c2)
                    for b in bounds)
            r = sum(1 for ba, at, blo, bhi in borders
                    if ba == a and abs(at - turn) < BORDER_NEAR and min(max(c1, c2), bhi) - max(min(c1, c2), blo) >= 12)
            crowd = 0
            for la, lturn, llo, lhi in laid:
                if la == a and abs(lturn - turn) < TURN_APART and llo < hi and lhi > lo:
                    crowd += 1
            fits = (not label_w or abs(turn - from_) >= label_w - 2 or abs(to - turn) >= label_w - 2
                    or abs(c2 - c1) >= label_w - 24)
            return {"turn": turn, "n": n, "m": m, "x": x, "r": r, "crowd": crowd, "fits": fits, "d": abs(turn - mid)}

        best = None
        for turn in cands:
            got = score(turn)
            # Nodes, names, borders crossed, borders run along: in that order.
            rank = (got["n"], got["m"], got["x"], got["r"])
            held = None if best is None else (best["n"], best["m"], best["x"], best["r"])
            even = rank == held
            if (best is None or rank < held
                    or (even and got["crowd"] < best["crowd"])
                    or (even and got["crowd"] == best["crowd"] and got["fits"] and not best["fits"])
                    or (even and got["crowd"] == best["crowd"] and got["fits"] == best["fits"]
                        and got["d"] < best["d"])):
                best = got
        best["dir"] = direction
        best["lo"] = lo
        best["hi"] = hi
        return best

    def port_at(leaf: Leaf, a: str, sign: int, off: float) -> Optional[Point]:
        """`portAt()`: on the side, at its place in the fan, for a shape
        whose side is straight there; None leaves the end to the ray."""
        if shape_of(str(leaf.data.get("entityType") or "")) not in PORTED:
            return None
        cx, cy = centers[leaf.id]
        out = sign * (half(leaf, a) + float(leaf.data.get("strokeWidth") or 1) / 2)
        return (cx + out, cy + off) if a == "x" else (cx + off, cy + out)

    plans: List[dict] = []
    sides: Dict[str, List[dict]] = {}
    routes: Dict[str, Optional[Route]] = {}
    for e in prep.edges:
        s = leaves.get(e["source"])
        t = leaves.get(e["target"])
        if s is None or t is None or s.id == t.id:
            routes[e["id"]] = None
            continue
        sp, tp = centers[s.id], centers[t.id]
        # Which axis to leave along: whichever has room, and of those the
        # one whose route passes behind fewer nodes, then through fewer
        # names; on a tie the axis the layout ranked this edge along, or
        # the drawing's own direction.
        preferred = lay.edge_axis.get(e["id"]) or primary
        choice = None
        for a in (preferred, other(preferred)):
            gap = abs(coord(tp, a) - coord(sp, a)) - half(s, a) - half(t, a)
            if gap < FACE_GAP:
                continue
            c = other(a)
            got = plan(s, t, a, coord(sp, c), coord(tp, c), label_px(str(e.get("label") or "")))
            if choice is None or got["n"] < choice["n"] or (got["n"] == choice["n"] and got["m"] < choice["m"]):
                choice = {"axis": a, "n": got["n"], "m": got["m"], "dir": got["dir"]}
        if choice is None:
            routes[e["id"]] = None
            continue
        axis, cross, direction = choice["axis"], other(choice["axis"]), choice["dir"]
        item = {"e": e, "s": s, "t": t, "axis": axis, "cross": cross, "dir": direction, "offS": 0.0, "offT": 0.0}
        plans.append(item)
        key_s = "%s|%s%d" % (s.id, axis, direction)
        key_t = "%s|%s%d" % (t.id, axis, -direction)
        sides.setdefault(key_s, []).append({"plan": item, "role": "offS", "node": s, "at": coord(tp, cross)})
        sides.setdefault(key_t, []).append({"plan": item, "role": "offT", "node": t, "at": coord(sp, cross)})
    # The edges on each side of a node fan along that side, in the order of
    # where they are going so the fan does not cross itself, fourteen
    # pixels apart or as close as the side allows.
    for key, lst in sides.items():
        if len(lst) < 2:
            continue
        node: Leaf = lst[0]["node"]
        cross = lst[0]["plan"]["cross"]
        if shape_of(str(node.data.get("entityType") or "")) not in FANNED:
            continue
        room = half(node, cross) - FAN_INSET
        if room <= 0:
            continue
        lst.sort(key=lambda item: item["at"])
        step = min(FAN_STEP, (2 * room) / (len(lst) - 1))
        for i, item in enumerate(lst):
            item["plan"][item["role"]] = (i - (len(lst) - 1) / 2) * step
    def name_on(a: str, u1: float, u2: float, v: float) -> Optional[Box]:
        """The name a straight piece along `a` runs through, if any."""
        for i, (_, b) in enumerate(boxes):
            if i >= named and hits(b, a, u1, u2, v):
                return b
        return None

    def rank(got: dict) -> Tuple[int, int, int, int]:
        return (got["n"], got["m"], got["x"], got["r"])

    for item in plans:
        s, t = item["s"], item["t"]
        sp, tp = centers[s.id], centers[t.id]
        a, c = item["axis"], item["cross"]
        c1 = coord(sp, c) + item["offS"]
        c2 = coord(tp, c) + item["offT"]
        label_w = label_px(str(item["e"].get("label") or ""))
        got = plan(s, t, a, c1, c2, label_w)
        # A port under a name moves along its side past the word, and keeps
        # the place if the route is better for it (`planPieces()`).
        from_ = coord(sp, a) + item["dir"] * half(s, a)
        to = coord(tp, a) - item["dir"] * half(t, a)
        for role, leaf, p, first in (("offS", s, sp, True), ("offT", t, tp, False)):
            if not got["m"] or shape_of(str(leaf.data.get("entityType") or "")) not in PORTED:
                continue
            word = name_on(a, from_, got["turn"], c1) if first else name_on(a, got["turn"], to, c2)
            if word is None:
                continue
            room = half(leaf, c) - FAN_INSET
            wl, wh = (word[0], word[2]) if c == "x" else (word[1], word[3])
            key = "%s|%s%d" % (leaf.id, a, item["dir"] if first else -item["dir"])
            others = [coord(p, c) + en["plan"][en["role"]] for en in sides.get(key, []) if en["plan"] is not item]
            moved = None
            for v in (c2 if first else c1, wh + NAME_CLEAR, wl - NAME_CLEAR):
                if abs(v - coord(p, c)) > room:
                    continue
                if any(abs(o - v) < FAN_STEP / 2 for o in others):
                    continue
                tried = plan(s, t, a, v if first else c1, c2 if first else v, label_w)
                if rank(tried) < rank(got):
                    got, moved = tried, v
            if moved is None:
                continue
            if first:
                c1 = moved
            else:
                c2 = moved
            item[role] = moved - coord(p, c)
        turn = got["turn"]
        laid.append((a, turn, got["lo"], got["hi"]))
        p1 = (turn, c1) if a == "x" else (c1, turn)
        p2 = (turn, c2) if a == "x" else (c2, turn)
        points = [p1] if abs(c1 - c2) < 0.5 else [p1, p2]
        routes[item["e"]["id"]] = Route(item["e"]["id"], a, item["dir"], points,
                                        port_at(s, a, item["dir"], item["offS"]),
                                        port_at(t, a, -item["dir"], item["offT"]))
    return routes
