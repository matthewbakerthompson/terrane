"""Edges that go around things: an orthogonal router for the layered drawings.

The three pieces (`layered.route_layered`) lay every edge down out of the
node, across the gap, in, and let the middle piece pass behind whatever
sits in the way, because dagre leaves no corridors. ELK, which the app uses
where it can, routes around nodes and boundaries, and that is what makes
its drawings read as architecture diagrams rather than as graphs. This is
the answer to ELK's routing on top of the dagre placement: the kind of
router the orthogonal-connector literature describes (Wybrow, Marriott and
Stuckey; libavoid), kept to what a diagram of a few dozen nodes needs. It
was the Python drawing's alone until the app took it over (`planGrid` in
app.js); the layered fixtures hold the two to the same points.

The corridors are a grid: one line along each side of every node a margin
out, one along each side of every boundary half a margin out, and one
through each port, so a route can hug anything and leave or arrive
squarely. A segment of the grid that runs through a node is closed. Every
edge is then a shortest path over that grid by A*, where the length is the
cost plus a turn's worth for every bend, a boundary's worth for every
boundary border crossed that holds neither end of the edge, and a share's
worth for every piece of corridor an earlier edge already took, so two
edges through one gap take two lines rather than one. An edge leaves its
node along the axis the layout ranked it on, from a port fanned along that
side in the order of where it is going, and comes in squarely on the
facing side; the painter rounds the corners and finds the border.

Deterministic by construction: the grid is sorted coordinates, the edges
are routed in the payload's order, and ties in the queue break on the
order of insertion. Every arithmetic step is addition and comparison on
coordinates the layout produced, so the same bytes come out on every
platform.
"""

from __future__ import annotations

import bisect
import heapq
import math
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .layered import (FACE_GAP, FAN_INSET, FAN_STEP, FANNED, NAME_CLEAR, PORTED, LayeredLayout, Route, boundary_word,
                      group_box, leaf_box, route_layered)
from .packed import Group, Leaf, Prepared
from .shapes import shape_of

Point = Tuple[float, float]
Box = Tuple[float, float, float, float]

#: Clearance kept around a node: the corridor beside it runs this far out.
MARGIN = 10.0
#: What a bend costs, in the length it is traded against.
BEND = 36.0
#: What crossing a boundary's border costs, when the boundary holds neither
#: end of the edge: a line through a box it has no business in.
CROSS_BOUNDARY = 48.0
#: What running through a boundary's name costs: a line through a name is a
#: line through a word, so the name is dear, twice a bend, and a line jogs
#: around it wherever the grid offers a way. It cannot be a wall: a port
#: moved along its side to clear the name (`_off_the_name`) still sits in
#: the band where the whole side is under the name.
NAME = 80.0
#: What running through a node's clearance costs, per pixel of the run: a
#: line goes round where there is room, and through where a packed row
#: leaves a gap too narrow for two margins.
NEAR = 2.0
#: What a piece of corridor costs once another edge runs along it: enough
#: that an edge with a free corridor of its own takes it, not so much that
#: edges through one gap scatter across the sheet rather than bundle.
SHARED = 14.0
#: A run along a boundary's border closer than this reads as the border:
#: the corridor at the top edge of a name's box is four pixels inside its
#: boundary, and Tiered Architecture had twelve runs along borders there.
HUG_NEAR = 6.0
#: What such a run costs, per pixel of it: like a node's clearance, enough
#: that a line takes the corridor a margin out where there is one.
HUG = 1.0
#: How much the search trusts its estimate of what is left. At 1 the route
#: found is the cheapest there is; above it the search runs straighter at
#: the goal and finds a route a little dearer, a few times sooner. The
#: drawings are the same to the eye at this weight and the full render is
#: back under a minute.
EPSILON = 1.3
#: How far apart the runs of a bundle are nudged, and the most they move.
NUDGE = 7.0
NUDGE_MAX = MARGIN - 3

#: The four ways to move on the grid, as index steps: right, down, left, up.
_STEPS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def _dedupe(values: Sequence[float]) -> List[float]:
    """The grid's lines, sorted, one of any within a hundredth of a pixel,
    each snapped to the nearest 1024th: the app's `gridDedupe`, and why."""
    out: List[float] = []
    for v in sorted(values):
        if not out or v - out[-1] > 0.01:
            out.append(v)
    return [math.floor(v * 1024 + 0.5) / 1024 for v in out]


def _index(values: List[float], v: float) -> int:
    """The index of a coordinate the grid was built from."""
    lo, hi = 0, len(values) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if abs(values[mid] - v) <= 0.011:
            return mid
        if values[mid] < v:
            lo = mid + 1
        else:
            hi = mid - 1
    raise KeyError(v)


def _pieces_in(xs: List[float], ys: List[float], box: Box):
    """The horizontal and vertical pieces whose inside crosses the box's
    inside: a horizontal piece (i, j) runs from xs[i] to xs[i + 1] at ys[j],
    a vertical one (i, j) from ys[j] to ys[j + 1] at xs[i]. Found by the
    index ranges the box spans, not by testing every piece."""
    x1, y1, x2, y2 = box
    lo_j = bisect.bisect_right(ys, y1 + 0.011)
    hi_j = bisect.bisect_left(ys, y2 - 0.011)
    lo_i = max(0, bisect.bisect_right(xs, x1 + 0.011) - 1)
    hi_i = min(len(xs) - 1, bisect.bisect_left(xs, x2 - 0.011))
    horizontal = [(i, j) for j in range(lo_j, hi_j) for i in range(lo_i, hi_i)]
    lo_i2 = bisect.bisect_right(xs, x1 + 0.011)
    hi_i2 = bisect.bisect_left(xs, x2 - 0.011)
    lo_j2 = max(0, bisect.bisect_right(ys, y1 + 0.011) - 1)
    hi_j2 = min(len(ys) - 1, bisect.bisect_left(ys, y2 - 0.011))
    vertical = [(i, j) for i in range(lo_i2, hi_i2) for j in range(lo_j2, hi_j2)]
    return horizontal, vertical


class _Grid:
    def __init__(self, xs: List[float], ys: List[float], bodies: Sequence[Box], clearances: Sequence[Box],
                 borders: Sequence[Tuple[str, Box]], soft: Sequence[Box] = ()) -> None:
        self.xs, self.ys = xs, ys
        nx, ny = len(xs), len(ys)
        self.nx, self.ny = nx, ny
        # A piece through a node's body is closed. A piece through the
        # clearance around it is dear, by how much of it runs there, so a
        # line goes round where there is room and squeezes through where a
        # packed row leaves none. A piece across a boundary's border
        # remembers whose; a piece through a boundary's name is dear.
        self.closed_h: Set[Tuple[int, int]] = set()
        self.closed_v: Set[Tuple[int, int]] = set()
        self.near_h: Dict[Tuple[int, int], int] = {}
        self.near_v: Dict[Tuple[int, int], int] = {}
        for body in bodies:
            h, v = _pieces_in(xs, ys, body)
            self.closed_h.update(h)
            self.closed_v.update(v)
        for clear in clearances:
            h, v = _pieces_in(xs, ys, clear)
            for piece in h:
                self.near_h[piece] = self.near_h.get(piece, 0) + 1
            for piece in v:
                self.near_v[piece] = self.near_v.get(piece, 0) + 1
        self.cross_h: Dict[Tuple[int, int], Tuple[str, ...]] = {}
        self.cross_v: Dict[Tuple[int, int], Tuple[str, ...]] = {}
        for gid, (x1, y1, x2, y2) in borders:
            js = [j for j, y in enumerate(ys) if y1 - 0.011 <= y <= y2 + 0.011]
            is_ = [i for i, x in enumerate(xs) if x1 - 0.011 <= x <= x2 + 0.011]
            for x in (x1, x2):
                i = _between(xs, x)
                if i is None:
                    continue
                for j in js:
                    self.cross_h[(i, j)] = self.cross_h.get((i, j), ()) + (gid,)
            for y in (y1, y2):
                j = _between(ys, y)
                if j is None:
                    continue
                for i in is_:
                    self.cross_v[(i, j)] = self.cross_v.get((i, j), ()) + (gid,)
        self.soft_h: Dict[Tuple[int, int], int] = {}
        self.soft_v: Dict[Tuple[int, int], int] = {}
        for box in soft:
            h, v = _pieces_in(xs, ys, box)
            for piece in h:
                self.soft_h[piece] = self.soft_h.get(piece, 0) + 1
            for piece in v:
                self.soft_v[piece] = self.soft_v.get(piece, 0) + 1
        # A piece along a boundary's border, nearer it than HUG_NEAR, over
        # the border's own span.
        self.hug_h: Dict[Tuple[int, int], int] = {}
        self.hug_v: Dict[Tuple[int, int], int] = {}
        for _gid, (x1, y1, x2, y2) in borders:
            for y in (y1, y2):
                for j, gy in enumerate(ys):
                    if abs(gy - y) >= HUG_NEAR:
                        continue
                    for i in range(nx - 1):
                        if xs[i + 1] > x1 + 0.011 and xs[i] < x2 - 0.011:
                            self.hug_h[(i, j)] = self.hug_h.get((i, j), 0) + 1
            for x in (x1, x2):
                for i, gx in enumerate(xs):
                    if abs(gx - x) >= HUG_NEAR:
                        continue
                    for j in range(ny - 1):
                        if ys[j + 1] > y1 + 0.011 and ys[j] < y2 - 0.011:
                            self.hug_v[(i, j)] = self.hug_v.get((i, j), 0) + 1
        self.used_h: Dict[Tuple[int, int], int] = {}
        self.used_v: Dict[Tuple[int, int], int] = {}
        self.best: List[float] = [float("inf")] * (nx * ny * 4)
        self.came: List[int] = [-1] * (nx * ny * 4)


def _span(values: List[float], lo: float, hi: float) -> Tuple[int, int]:
    """The grid indices of a box's two sides, which are grid lines."""
    return _index(values, lo), _index(values, hi)


def _between(values: List[float], v: float) -> Optional[int]:
    """The index of the grid line just below `v`, when `v` is strictly
    between two lines; None when it is a line itself."""
    for i in range(len(values) - 1):
        if values[i] + 0.011 < v < values[i + 1] - 0.011:
            return i
    return None


def _piece_closed(grid: _Grid, cell: Tuple[int, int], direction: int) -> bool:
    """Whether the piece out of `cell` in `direction` is a wall or the edge
    of the grid."""
    i, j = cell
    di, dj = _STEPS[direction]
    ni, nj = i + di, j + dj
    if not (0 <= ni < grid.nx and 0 <= nj < grid.ny):
        return True
    if di:
        return (min(i, ni), j) in grid.closed_h
    return (i, min(j, nj)) in grid.closed_v


def _astar(grid: _Grid, start: Tuple[int, int], out_dir: int, goal: Tuple[int, int], in_dir: int,
           outside: Set[str], window: Optional[Tuple[int, int, int, int]] = None) -> Optional[List[Tuple[int, int]]]:
    """The cheapest route from `start`, leaving in `out_dir`, to `goal`,
    arriving in `in_dir`, over the open pieces of the grid; None when the
    goal cannot be reached. `outside` names the boundaries the edge is
    allowed across for free, since one of its ends is inside them.
    `window` is the index box the search may use, so a route between two
    neighbors does not consider the far side of the sheet; the caller
    widens it when nothing is found."""
    xs, ys = grid.xs, grid.ys
    nx, ny = grid.nx, grid.ny
    gx, gy = xs[goal[0]], ys[goal[1]]
    lo_i, lo_j, hi_i, hi_j = window if window else (0, 0, nx - 1, ny - 1)
    closed_h, closed_v = grid.closed_h, grid.closed_v
    near_h, near_v = grid.near_h, grid.near_v
    cross_h, cross_v = grid.cross_h, grid.cross_v
    used_h, used_v = grid.used_h, grid.used_v
    soft_h, soft_v = grid.soft_h, grid.soft_v
    hug_h, hug_v = grid.hug_h, grid.hug_v
    inf = float("inf")

    def h(x: float, y: float, d: int) -> float:
        """What is left at least: the distance, and the turns a route
        moving in `d` must still make to arrive in `in_dir`. Counting the
        turns is what keeps the search from walking every equal-length
        staircase between two points."""
        dx, dy = gx - x, gy - y
        bends = 0
        if abs(dx) > 0.01 and abs(dy) > 0.01:
            bends = 1
            # Moving away from the goal along the axis of travel: turn back.
            if (d == 0 and dx < 0) or (d == 2 and dx > 0) or (d == 1 and dy < 0) or (d == 3 and dy > 0):
                bends = 2
        elif abs(dx) > 0.01:
            toward = 0 if dx > 0 else 2
            bends = 0 if d == toward else 2 if d == (toward + 2) % 4 else 1
        elif abs(dy) > 0.01:
            toward = 1 if dy > 0 else 3
            bends = 0 if d == toward else 2 if d == (toward + 2) % 4 else 1
        # Arriving means moving in `in_dir`; a route not headed that way
        # when it gets there turns at least once more.
        if bends == 0 and d != in_dir:
            bends = 2
        return (abs(dx) + abs(dy) + BEND * bends) * EPSILON

    # Costs and parents in the grid's flat arrays, state (i, j, d) at
    # (i * ny + j) * 4 + d, allocated once for the drawing and reset after
    # each search by the entries it touched.
    best, came, touched = grid.best, grid.came, []
    # A port whose straight stub is a wall -- a node stacked closer than a
    # margin from the one above it -- is left and reached along the gap
    # instead, from whichever way is open; squarely where it can be.
    out_dirs = [out_dir] if not _piece_closed(grid, start, out_dir) else [d for d in range(4)]
    goal_keys = {(goal[0] * ny + goal[1]) * 4 + in_dir}
    if _piece_closed(grid, goal, (in_dir + 2) % 4):
        goal_keys = {(goal[0] * ny + goal[1]) * 4 + d for d in range(4)}
    heap = []
    counter = 0
    for d in out_dirs:
        first = (start[0] * ny + start[1]) * 4 + d
        best[first] = 0.0
        touched.append(first)
        counter += 1
        heap.append((h(xs[start[0]], ys[start[1]], d), 0.0, counter, first))
    heapq.heapify(heap)
    while heap:
        _f, g, _c, key = heapq.heappop(heap)
        if g > best[key]:
            continue
        if key in goal_keys:
            path = []
            cur = key
            while cur != -1:
                cell = cur // 4
                path.append((cell // ny, cell % ny))
                cur = came[cur]
            path.reverse()
            for k in touched:
                best[k] = inf
                came[k] = -1
            return path
        cell, d = key // 4, key % 4
        i, j = cell // ny, cell % ny
        for nd, (di, dj) in enumerate(_STEPS):
            ni, nj = i + di, j + dj
            if ni < lo_i or ni > hi_i or nj < lo_j or nj > hi_j:
                continue
            if di:
                piece = (i if di > 0 else ni, j)
                if piece in closed_h:
                    continue
                length = abs(xs[ni] - xs[i])
                cost = g + length
                near = near_h.get(piece)
                crossed = cross_h.get(piece)
                shared = used_h.get(piece)
                soft = soft_h.get(piece)
                hug = hug_h.get(piece)
            else:
                piece = (i, j if dj > 0 else nj)
                if piece in closed_v:
                    continue
                length = abs(ys[nj] - ys[j])
                cost = g + length
                near = near_v.get(piece)
                crossed = cross_v.get(piece)
                shared = used_v.get(piece)
                soft = soft_v.get(piece)
                hug = hug_v.get(piece)
            if nd != d:
                cost += BEND
            if near:
                cost += NEAR * length * near
            if crossed:
                for gid in crossed:
                    if gid not in outside:
                        cost += CROSS_BOUNDARY
            if shared:
                cost += SHARED * shared
            if soft:
                cost += NAME * soft
            if hug:
                cost += HUG * length * hug
            nkey = (ni * ny + nj) * 4 + nd
            if cost < best[nkey]:
                if best[nkey] == inf:
                    touched.append(nkey)
                best[nkey] = cost
                came[nkey] = key
                counter += 1
                heapq.heappush(heap, (cost + h(xs[ni], ys[nj], nd), cost, counter, nkey))
    for k in touched:
        best[k] = inf
        came[k] = -1
    return None


def _window(grid: _Grid, a: Tuple[int, int], b: Tuple[int, int], reach: float) -> Tuple[int, int, int, int]:
    """The index box around two grid points, `reach` pixels wider each way."""
    xs, ys = grid.xs, grid.ys
    x_lo, x_hi = min(xs[a[0]], xs[b[0]]) - reach, max(xs[a[0]], xs[b[0]]) + reach
    y_lo, y_hi = min(ys[a[1]], ys[b[1]]) - reach, max(ys[a[1]], ys[b[1]]) + reach
    lo_i = max(0, max((i for i, x in enumerate(xs) if x <= x_lo), default=0))
    hi_i = min(len(xs) - 1, min((i for i, x in enumerate(xs) if x >= x_hi), default=len(xs) - 1))
    lo_j = max(0, max((j for j, y in enumerate(ys) if y <= y_lo), default=0))
    hi_j = min(len(ys) - 1, min((j for j, y in enumerate(ys) if y >= y_hi), default=len(ys) - 1))
    return lo_i, lo_j, hi_i, hi_j


def _corners(points: Sequence[Point]) -> List[Point]:
    """The polyline with its straight runs joined: the points where it turns,
    the two ends kept."""
    out: List[Point] = []
    for p in points:
        if out and abs(out[-1][0] - p[0]) < 0.01 and abs(out[-1][1] - p[1]) < 0.01:
            continue
        if len(out) >= 2:
            a, b = out[-2], out[-1]
            if (abs(a[0] - b[0]) < 0.01 and abs(b[0] - p[0]) < 0.01) or \
                    (abs(a[1] - b[1]) < 0.01 and abs(b[1] - p[1]) < 0.01):
                out[-1] = p
                continue
        out.append(p)
    return out


def _off_the_name(port: Point, axis: str, names: Sequence[Box], box: Box) -> Point:
    """A port inside a boundary's name band, moved along its side to clear
    the name. A node at the top-left corner of its boundary has its top
    port under the name, and every line arriving from above ran through
    the word, whatever the name cost, since the last piece into the port
    had nowhere else to be. Moved past the far end of the name first, back
    past the near end if the side is too short, left where the whole side
    is under the name."""
    for name in names:
        if not (name[0] < port[0] < name[2] and name[1] < port[1] < name[3]):
            continue
        if axis == "y":
            lo, hi = box[0] + FAN_INSET, box[2] - FAN_INSET
            for x in (name[2] + NAME_CLEAR, name[0] - NAME_CLEAR):
                if lo <= x <= hi:
                    return (x, port[1])
        else:
            lo, hi = box[1] + FAN_INSET, box[3] - FAN_INSET
            for y in (name[3] + NAME_CLEAR, name[1] - NAME_CLEAR):
                if lo <= y <= hi:
                    return (port[0], y)
    return port


def route_grid(prep: Prepared, lay: LayeredLayout, down: bool) -> Dict[str, Optional[Route]]:
    """Every edge between two leaves routed around the others; None for an
    edge with no two leaves to join. An edge the grid cannot carry (a port
    boxed in on every side) takes the app's three-piece route instead, so
    the drawing is never missing a line."""
    primary = "y" if down else "x"
    leaves: Dict[str, Leaf] = {leaf.id: leaf for leaf in prep.leaves}
    centers: Dict[str, Point] = {leaf.id: (lay.leaves[leaf.id][0], lay.leaves[leaf.id][1]) for leaf in prep.leaves}
    boxes: Dict[str, Box] = {leaf.id: leaf_box(leaf, centers[leaf.id]) for leaf in prep.leaves}
    clearance: Dict[str, Box] = {
        lid: (b[0] - MARGIN, b[1] - MARGIN, b[2] + MARGIN, b[3] + MARGIN) for lid, b in boxes.items()}

    # Which boundaries hold each leaf, so an edge is free to cross those.
    parent_of: Dict[str, Optional[str]] = {g.id: g.parent for g in prep.groups}
    enclosing: Dict[str, Set[str]] = {}
    for leaf in prep.leaves:
        chain: Set[str] = set()
        cur = leaf.parent
        while cur:
            chain.add(cur)
            cur = parent_of.get(cur)
        enclosing[leaf.id] = chain

    def coord(p: Point, axis: str) -> float:
        return p[0] if axis == "x" else p[1]

    def half(leaf: Leaf, axis: str) -> float:
        b = boxes[leaf.id]
        return ((b[2] - b[0]) if axis == "x" else (b[3] - b[1])) / 2

    def other(axis: str) -> str:
        return "y" if axis == "x" else "x"

    # Which side each end uses: along the axis the layout ranked the edge
    # on where there is room between the two, toward the other end; else
    # the other axis; and never a side whose port would sit inside a third
    # node's clearance, which is a gap in a stack that no line can enter.
    # The two ends choose on their own, so a node in a tight stack is
    # reached from its free side while its partner leaves squarely.
    def boxed(leaf: Leaf, point: Point, partner: Leaf) -> bool:
        for lid, b in clearance.items():
            if lid in (leaf.id, partner.id):
                continue
            if b[0] < point[0] < b[2] and b[1] < point[1] < b[3]:
                return True
        return False

    def port_of(leaf: Leaf, axis: str, sign: int, partner: Leaf) -> Point:
        c = centers[leaf.id]
        gap = abs(coord(centers[partner.id], axis) - coord(c, axis)) - half(leaf, axis) - half(partner, axis)
        # Two nodes closer than two margins apart along the axis would put
        # each one's port inside the other's clearance; the stubs meet in
        # the middle of the gap instead, and the line between is straight.
        stub = MARGIN if gap >= 2 * MARGIN else max(1.0, gap / 2)
        out = coord(c, axis) + sign * (half(leaf, axis) + stub)
        return (out, c[1]) if axis == "x" else (c[0], out)

    def choose(leaf: Leaf, partner: Leaf, preferred: str) -> Tuple[str, int]:
        """The side of `leaf` that faces `partner`: its axis and the sign
        out of the node along it."""
        here, there = centers[leaf.id], centers[partner.id]
        options = []
        for a in (preferred, other(preferred)):
            gap = abs(coord(there, a) - coord(here, a)) - half(leaf, a) - half(partner, a)
            sign = 1 if coord(there, a) >= coord(here, a) else -1
            options.append((a, sign, gap))
        # Room between the two along the axis first; then the side whose
        # port is not inside someone else's clearance; the preferred axis
        # breaks the tie.
        usable = [(a, s) for a, s, gap in options if gap >= FACE_GAP]
        if not usable:
            usable = [(a, s) for a, s, gap in sorted(options, key=lambda o: -o[2])]
        for a, s in usable:
            if not boxed(leaf, port_of(leaf, a, s, partner), partner):
                return a, s
        return usable[0]

    plans: List[dict] = []
    routes: Dict[str, Optional[Route]] = {}
    for e in prep.edges:
        s, t = leaves.get(e["source"]), leaves.get(e["target"])
        if s is None or t is None or s.id == t.id:
            routes[e["id"]] = None
            continue
        preferred = lay.edge_axis.get(e["id"]) or primary
        s_axis, s_sign = choose(s, t, preferred)
        t_axis, t_sign = choose(t, s, preferred)
        plans.append({"e": e, "s": s, "t": t, "axis": s_axis, "dir": s_sign, "t_axis": t_axis, "t_sign": t_sign,
                      "offS": 0.0, "offT": 0.0})

    # Fan the ports along each side, in the order of where they go.
    sides: Dict[str, List[dict]] = {}
    for plan in plans:
        s, t = plan["s"], plan["t"]
        sides.setdefault("%s|%s%d" % (s.id, plan["axis"], plan["dir"]), []).append(
            {"plan": plan, "role": "offS", "node": s, "axis": plan["axis"],
             "at": coord(centers[t.id], other(plan["axis"]))})
        sides.setdefault("%s|%s%d" % (t.id, plan["t_axis"], plan["t_sign"]), []).append(
            {"plan": plan, "role": "offT", "node": t, "axis": plan["t_axis"],
             "at": coord(centers[s.id], other(plan["t_axis"]))})
    for lst in sides.values():
        if len(lst) < 2:
            continue
        node: Leaf = lst[0]["node"]
        cross = other(lst[0]["axis"])
        if shape_of(str(node.data.get("entityType") or "")) not in FANNED:
            continue
        room = half(node, cross) - FAN_INSET
        if room <= 0:
            continue
        lst.sort(key=lambda item: (item["at"], item["plan"]["e"]["id"]))
        step = min(FAN_STEP, (2 * room) / (len(lst) - 1))
        for i, item in enumerate(lst):
            item["plan"][item["role"]] = (i - (len(lst) - 1) / 2) * step

    # The ports, a margin out from the border, and the grid through them.
    xs: List[float] = []
    ys: List[float] = []
    for b in clearance.values():
        xs.extend((b[0], b[2]))
        ys.extend((b[1], b[3]))
    borders: List[Tuple[str, Box]] = []
    # A boundary's name sits in its top-left corner, and a line through a
    # name is a line through a word: the word is dear to cross, so a line
    # jogs round it where it can; it cannot be closed, since a node at that
    # corner has its top port beside it. The boundary is the box Cytoscape
    # draws (`group_box`), which is the one the app has to hand, and the
    # name the word as drawn (`boundary_word`), not the corner.
    names: List[Box] = []
    memo: Dict[str, Box] = {}
    for group in prep.groups:
        gb = group_box(prep, lay, group, memo)
        borders.append((group.id, gb))
        # A line five pixels from a border reads as the border; a margin
        # out it reads as a line beside it.
        xs.extend((gb[0] - MARGIN, gb[0] + MARGIN, gb[2] - MARGIN, gb[2] + MARGIN))
        ys.extend((gb[1] - MARGIN, gb[1] + MARGIN, gb[3] - MARGIN, gb[3] + MARGIN))
        name = boundary_word(gb, group)
        names.append(name)
        xs.extend((name[0], name[2]))
        ys.extend((name[1], name[3]))
    for plan in plans:
        for leaf, partner, role, axis, sign in ((plan["s"], plan["t"], "offS", plan["axis"], plan["dir"]),
                                                (plan["t"], plan["s"], "offT", plan["t_axis"], plan["t_sign"])):
            port = port_of(leaf, axis, sign, partner)
            if axis == "x":
                port = (port[0], port[1] + plan[role])
            else:
                port = (port[0] + plan[role], port[1])
            moved = _off_the_name(port, axis, names, boxes[leaf.id])
            if moved != port:
                port = moved
                plan[role] = (port[1] - centers[leaf.id][1]) if axis == "x" else (port[0] - centers[leaf.id][0])
            plan[role + "_port"] = port
            xs.append(port[0])
            ys.append(port[1])
    if xs and ys:
        xs.extend((min(xs) - 2 * MARGIN, max(xs) + 2 * MARGIN))
        ys.extend((min(ys) - 2 * MARGIN, max(ys) + 2 * MARGIN))
    grid = _Grid(_dedupe(xs), _dedupe(ys), [boxes[lid] for lid in clearance], [clearance[lid] for lid in clearance],
                 borders, names)

    fallback = None
    gridded: List[dict] = []
    for plan in plans:
        e, s, t = plan["e"], plan["s"], plan["t"]
        axis, direction = plan["axis"], plan["dir"]
        start, goal = plan["offS_port"], plan["offT_port"]
        si, sj = _index(grid.xs, start[0]), _index(grid.ys, start[1])
        gi, gj = _index(grid.xs, goal[0]), _index(grid.ys, goal[1])
        if axis == "x":
            out_dir = 0 if direction > 0 else 2
        else:
            out_dir = 1 if direction > 0 else 3
        # Arriving squarely means moving into the target's side: the way
        # opposite to the sign out of it.
        if plan["t_axis"] == "x":
            in_dir = 2 if plan["t_sign"] > 0 else 0
        else:
            in_dir = 3 if plan["t_sign"] > 0 else 1
        outside = enclosing[s.id] | enclosing[t.id]
        # Near first: a route between neighbors has no business on the far
        # side of the sheet, and a search that never looks there is quick.
        # Widened when nothing is found, and only then the whole grid.
        path = None
        for reach in (240, None):
            window = _window(grid, (si, sj), (gi, gj), reach) if reach is not None else None
            path = _astar(grid, (si, sj), out_dir, (gi, gj), in_dir, outside, window)
            if path is not None:
                break
        if path is None:
            if fallback is None:
                fallback = route_layered(prep, lay, down)
            routes[e["id"]] = fallback.get(e["id"])
            continue
        for (i, j), (ni, nj) in zip(path, path[1:]):
            if i != ni:
                piece = (min(i, ni), j)
                grid.used_h[piece] = grid.used_h.get(piece, 0) + 1
            else:
                piece = (i, min(j, nj))
                grid.used_v[piece] = grid.used_v.get(piece, 0) + 1
        points = _corners([(grid.xs[i], grid.ys[j]) for i, j in path])
        routes[e["id"]] = Route(e["id"], axis, direction, points)
        gridded.append(plan)
    nudge(routes, names)

    def pinned(leaf: Leaf, axis: str, sign: int, port: Point) -> Optional[Point]:
        """The end on the node's side at the port's place, for a side that is
        straight there; None leaves it to the ray from the center."""
        if shape_of(str(leaf.data.get("entityType") or "")) not in PORTED:
            return None
        cx, cy = centers[leaf.id]
        out = sign * ((leaf.w if axis == "x" else leaf.h) / 2 + float(leaf.data.get("strokeWidth") or 1) / 2)
        return (cx + out, port[1]) if axis == "x" else (port[0], cy + out)

    for plan in gridded:
        route = routes[plan["e"]["id"]]
        routes[route.edge_id] = route._replace(
            start=pinned(plan["s"], plan["axis"], plan["dir"], route.points[0]),
            end=pinned(plan["t"], plan["t_axis"], plan["t_sign"], route.points[-1]))
    return routes


def _into_a_name(bundle: List[dict], shifts: List[float], vertical: bool, names: Sequence[Box]) -> bool:
    """Whether a run moved by its shift would lie in a name's box; a run
    left where the router put it is the router's to answer for."""
    for run, shift in zip(bundle, shifts):
        if shift == 0:
            continue
        f = run["fixed"] + shift
        for x1, y1, x2, y2 in names:
            if vertical:
                if x1 < f < x2 and run["lo"] < y2 and run["hi"] > y1:
                    return True
            elif y1 < f < y2 and run["lo"] < x2 and run["hi"] > x1:
                return True
    return False


def nudge(routes: Dict[str, Optional[Route]], names: Sequence[Box] = ()) -> None:
    """Runs of different edges that share a corridor are moved apart, a
    few pixels each, so a bundle reads as its lines rather than as one; the
    ones with no company stay where they were. The first and last runs of
    an edge are its stubs out of the ports and are left alone, since the
    port is where the node is. Order within a bundle follows where each
    run came from on the axis it is moved along, so moved runs do not cross
    the runs that feed them. A bundle the spread would move into a name is
    spread to one side, away from it, or not at all: three lines in the
    corridor at the edge of "Policy" were spread seven pixels each way, and
    one ran through the word."""
    runs: List[dict] = []
    for route in routes.values():
        if route is None or len(route.points) < 4:
            continue
        pts = route.points
        for k in range(1, len(pts) - 2):
            a, b = pts[k], pts[k + 1]
            vertical = abs(a[0] - b[0]) < 0.01
            fixed = a[0] if vertical else a[1]
            lo, hi = sorted((a[1], b[1]) if vertical else (a[0], b[0]))
            # Where the run came from and goes to, across it: the neighbors'
            # far ends decide the order, so bundles do not braid.
            before = pts[k - 1][0] if vertical else pts[k - 1][1]
            after = pts[k + 2][0] if vertical else pts[k + 2][1]
            runs.append({"route": route, "k": k, "vertical": vertical, "fixed": fixed, "lo": lo, "hi": hi,
                         "order": (before + after) / 2, "edge": route.edge_id})
    for vertical in (True, False):
        pool = [r for r in runs if r["vertical"] == vertical]
        pool.sort(key=lambda r: (r["fixed"], r["lo"], r["edge"]))
        i = 0
        while i < len(pool):
            # A bundle: runs on one line, overlapping along it.
            bundle = [pool[i]]
            j = i + 1
            while j < len(pool) and abs(pool[j]["fixed"] - pool[i]["fixed"]) < 0.01                     and pool[j]["lo"] < max(r["hi"] for r in bundle) - 0.01:
                bundle.append(pool[j])
                j += 1
            i = j
            if len(bundle) < 2:
                continue
            bundle.sort(key=lambda r: (r["order"], r["edge"]))
            n = len(bundle)
            step = min(NUDGE, 2 * NUDGE_MAX / (n - 1))
            shifts = [(pos - (n - 1) / 2) * step for pos in range(n)]
            if _into_a_name(bundle, shifts, vertical, names):
                side = min(NUDGE, NUDGE_MAX / (n - 1))
                for alt in ([(pos - (n - 1)) * side for pos in range(n)], [pos * side for pos in range(n)], [0.0] * n):
                    if not _into_a_name(bundle, alt, vertical, names):
                        shifts = alt
                        break
            for run, shift in zip(bundle, shifts):
                pts = run["route"].points
                k = run["k"]
                for idx in (k, k + 1):
                    x, y = pts[idx]
                    pts[idx] = (x + shift, y) if vertical else (x, y + shift)
