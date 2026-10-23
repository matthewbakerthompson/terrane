"""Where an edge's label sits: the app's `placeEdgeLabels()`, in Python.

A label belongs on its own line. It sits on the run of its edge that holds
the midpoint, at the midpoint or slid along the run, upright or turned to
lie along a steep line, at the first spot that clears every node, every
boundary name, every label already placed, every stretch another edge
shares and every other edge's line it would lie along; with no clear spot
it shows nothing, which beats a smear, and a label lying along a line it
does not belong to was the smear this rule came from. Above a
budget of labeled edges the labels come off altogether, since a landscape
reads as lines and the protocol of any one of them is a hover away.

The geometry comes from `svg.py`'s edges rather than from Cytoscape, so the
spots chosen are the same kind of spot rather than the same pixel: this is
a placement heuristic, not the layout, and the equality test does not hold
it to the app. Sizes are estimated from the label face the way the app
estimates them, 5.8px a glyph and 15px tall.
"""

from __future__ import annotations

import math
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from .packed import title_width
from .shapes import edge_word

LABEL_CHAR = 5.8
LABEL_H = 15
LABEL_GAP = 4
LABEL_APART = 6
LABEL_SLIDES: List[float] = [0]
for _d in (10, 20, 30, 42, 56, 72, 90, 110, 134, 162, 194, 230, 270, 316):
    LABEL_SLIDES.extend((_d, -_d))
LABEL_RUN_MIN = 24
LABEL_OVERHANG = 16
LABEL_BUDGET = 36

Box = Tuple[float, float, float, float]


class Piece(NamedTuple):
    """A straight piece of an edge as drawn."""
    ax: float
    ay: float
    bx: float
    by: float
    length: float
    ux: float
    uy: float


class Run(NamedTuple):
    x: float
    y: float
    ux: float
    uy: float
    back: float
    ahead: float
    mid: bool


class Placed(NamedTuple):
    edge_id: str
    text: str
    x: float
    y: float
    turned: bool
    #: The direction the text runs in, a unit vector, never leftward;
    #: (1, 0) for an upright label.
    ux: float
    uy: float
    box: Box


def piece(ax: float, ay: float, bx: float, by: float) -> Optional[Piece]:
    length = math.hypot(bx - ax, by - ay)
    if length < 1:
        return None
    return Piece(ax, ay, bx, by, length, (bx - ax) / length, (by - ay) / length)


def label_px(text: str) -> float:
    return len(text) * LABEL_CHAR + 8 if text else 0


def overlaps(a: Box, b: Box) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def piece_crosses(box: Box, r: Piece) -> bool:
    """Liang-Barsky clipping of the piece against the box: true when
    anything of it is left inside."""
    t0, t1 = 0.0, 1.0
    dx, dy = r.bx - r.ax, r.by - r.ay
    p = (-dx, dx, -dy, dy)
    q = (r.ax - box[0], box[2] - r.ax, r.ay - box[1], box[3] - r.ay)
    for i in range(4):
        if p[i] == 0:
            if q[i] < 0:
                return False
        else:
            t = q[i] / p[i]
            if p[i] < 0:
                if t > t1:
                    return False
                if t > t0:
                    t0 = t
            else:
                if t < t0:
                    return False
                if t < t1:
                    t1 = t
    return True


def shared_stretch(cx: float, cy: float, ux: float, uy: float, along: float, own: str,
                   pieces: Sequence[Tuple[str, Piece]]) -> bool:
    """Whether the stretch of a run around `c` lies on another edge's piece:
    parallel, within three pixels, overlapping along the line."""
    for edge_id, r in pieces:
        if edge_id == own:
            continue
        if abs(ux * r.uy - uy * r.ux) > 0.08:
            continue
        dist = abs((r.ax - cx) * r.uy - (r.ay - cy) * r.ux)
        if dist > 3:
            continue
        t1 = (r.ax - cx) * ux + (r.ay - cy) * uy
        t2 = (r.bx - cx) * ux + (r.by - cy) * uy
        if max(min(t1, t2), -along) < min(max(t1, t2), along):
            return True
    return False


def edge_runs(mid: Tuple[float, float], segs: Sequence[Piece]) -> List[Run]:
    """The runs a label may sit on: the one holding the midpoint first,
    then the others long enough to hold anything, longest first."""
    holder, holder_t, best = None, 0.5, math.inf
    mx, my = mid
    for r in segs:
        t = ((mx - r.ax) * (r.bx - r.ax) + (my - r.ay) * (r.by - r.ay)) / (r.length * r.length)
        t = max(0.0, min(1.0, t))
        d = math.hypot(mx - (r.ax + t * (r.bx - r.ax)), my - (r.ay + t * (r.by - r.ay)))
        if d <= 6 and d < best:
            best, holder, holder_t = d, r, t
    if holder is None:
        holder, holder_t = segs[0], 0.5
        mx, my = (holder.ax + holder.bx) / 2, (holder.ay + holder.by) / 2
    others = sorted((r for r in segs if r is not holder and r.length >= LABEL_RUN_MIN),
                    key=lambda r: -r.length)
    runs = []
    for r in [holder] + others:
        is_mid = r is holder
        t = holder_t if is_mid else 0.5
        runs.append(Run(mx if is_mid else (r.ax + r.bx) / 2, my if is_mid else (r.ay + r.by) / 2,
                        r.ux, r.uy, t * r.length, (1 - t) * r.length, is_mid))
    return runs


def place_labels(edges: Sequence[dict], segments: Dict[str, List[Piece]], midpoints: Dict[str, Tuple[float, float]],
                 node_boxes: Sequence[Box], boundary_boxes: Sequence[Tuple[Box, str]],
                 show: Optional[bool] = None) -> List[Placed]:
    """`edges` are the payload's edge records, in order. `segments` and
    `midpoints` are by edge id. `boundary_boxes` carry each boundary's box
    and label. `show` forces the labels on or off; None applies the budget."""
    redundant = set()
    labeled = []
    for e in edges:
        text = str(e.get("label") or "")
        if not text:
            continue
        if text.lower() == str(edge_word(str(e.get("kind") or "")) or "").lower():
            redundant.add(e["id"])
            continue
        labeled.append(e)
    if show is None:
        show = len(labeled) <= LABEL_BUDGET
    if not show:
        return []

    taken: List[Box] = [(b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2) for b in node_boxes]
    lines: List[Box] = []
    for bb, label in boundary_boxes:
        taken.append((bb[0], bb[1], bb[0] + 24 + title_width(label), bb[1] + 30))
        lines.append((bb[0], bb[1] - 3, bb[2], bb[1] + 3))
        lines.append((bb[0], bb[3] - 3, bb[2], bb[3] + 3))
        lines.append((bb[0] - 3, bb[1], bb[0] + 3, bb[3]))
        lines.append((bb[2] - 3, bb[1], bb[2] + 3, bb[3]))
    pieces: List[Tuple[str, Piece]] = []
    for e in edges:
        for seg in segments.get(e["id"], []):
            pieces.append((e["id"], seg))

    placed: List[Placed] = []
    said = set()

    def clear_at(box: Box, pass_no: int, own: str, along: Tuple[float, float]) -> bool:
        apart = (box[0] - LABEL_APART, box[1] - LABEL_APART, box[2] + LABEL_APART, box[3] + LABEL_APART)
        for t in taken:
            if overlaps(box, t):
                return False
        if pass_no == 0:
            for ln in lines:
                if overlaps(box, ln):
                    return False
        for p in placed:
            if overlaps(apart, p.box):
                return False
        # The second pass lets a label sit on a boundary's border, and lets
        # another edge's line pass under it crosswise, which the label's
        # box covers; it never lets one lie along another edge's line, which
        # reads as that edge's label.
        inner = (box[0] + LABEL_GAP, box[1] + LABEL_GAP, box[2] - LABEL_GAP, box[3] - LABEL_GAP)
        for edge_id, seg in pieces:
            if edge_id != own and piece_crosses(inner, seg):
                if pass_no == 0 or abs(seg.ux * along[0] + seg.uy * along[1]) > 0.7:
                    return False
        return True

    # Longer labels first: the hardest to place, and a short one fits
    # around them more easily than the other way round.
    for e in sorted(labeled, key=lambda e: -len(str(e["label"]))):
        text = str(e["label"])
        pair = "|".join(sorted([e["source"], e["target"]])) + "|" + text
        if pair in said:
            continue
        segs = segments.get(e["id"]) or []
        if not segs:
            continue
        w, h = label_px(text), LABEL_H
        mid = midpoints[e["id"]]
        runs = edge_runs(mid, segs)
        found = None
        for pass_no in range(2):
            if found:
                break
            for run in runs:
                if found:
                    break
                flat = abs(run.uy) < 0.35
                for turn in range(1 if flat else 2):
                    if found:
                        break
                    along = w / 2 if turn else abs(run.ux) * w / 2 + abs(run.uy) * h / 2
                    hx = abs(run.ux) * w / 2 + abs(run.uy) * h / 2 if turn else w / 2
                    hy = abs(run.uy) * w / 2 + abs(run.ux) * h / 2 if turn else h / 2
                    for s in LABEL_SLIDES:
                        if s > 0 and s + along > run.ahead + LABEL_OVERHANG:
                            continue
                        if s < 0 and -s + along > run.back + LABEL_OVERHANG:
                            continue
                        if s == 0 and not run.mid and along > min(run.back, run.ahead) + LABEL_OVERHANG:
                            continue
                        cx, cy = run.x + s * run.ux, run.y + s * run.uy
                        if shared_stretch(cx, cy, run.ux, run.uy, min(along, 10), e["id"], pieces):
                            continue
                        box = (cx - hx - LABEL_GAP, cy - hy - LABEL_GAP, cx + hx + LABEL_GAP, cy + hy + LABEL_GAP)
                        if clear_at(box, pass_no, e["id"], (run.ux, run.uy) if turn else (1.0, 0.0)):
                            # Along the line, but never upside down: the
                            # direction itself rather than its angle, which
                            # would be the C library's atan2 and not the
                            # same number on every platform.
                            ux, uy = (run.ux + 0.0, run.uy + 0.0) if turn else (1.0, 0.0)
                            if ux < 0:
                                ux, uy = 0.0 - ux, 0.0 - uy
                            found = Placed(e["id"], text, cx, cy, bool(turn), ux, uy, box)
                            break
        if found:
            placed.append(found)
            said.add(pair)
    return placed
