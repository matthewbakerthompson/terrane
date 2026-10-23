"""A diagram arranged by hand: the positions kept on the canvas, laid over
the layout. `arrangeKept()` in the app's `app.js`, line for line.

A diagram drawn on the canvas is laid out until a box is moved; from then
on it is arranged, and its file keeps `positions`, one line per box and
per boundary (`terrane.query.View.positions`). Laid out afresh on every
drawing, a diagram of Network Topology given a second system turned two
zones side by side into one above the other: a layout run again from
scratch keeps nothing of the last one. So here the layout only proposes.

Every boundary is a frame of its own, and the sheet is the outermost one.
A thing kept has its corner in the frame around it: a box its top-left, a
boundary the corner of its frame, so moving a boundary moves what is in it
and changes one line. Frames are settled from the inside out. In a frame
where something is kept, whatever is not (a part placed since, a subnet
the placed view gained) goes where there is room beside what is there, in
the order the layout read them, and nothing kept moves. In a frame where
nothing is kept, its things keep the layout's arrangement of them, so a
boundary new to an arranged diagram arrives as the layout drew it.

The frame of a boundary is laid where its parent's position says; its
drawn box is still its children plus the padding, so a box moved past its
boundary's edge widens the boundary rather than leaving it.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from ..query import position_key
from .layered import LayeredLayout
from .packed import Group, Leaf, Prepared, js_round, title_room
from .shapes import LAYOUT

Box = Tuple[float, float, float, float]

#: The room left between something placed where there is room and what
#: was there: the gaps the packed layout leaves between boxes.
GAP_X = 24
GAP_Y = 20


def _union(boxes: Sequence[Box]) -> Box:
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def _shift(box: Box, at: Tuple[float, float]) -> Box:
    return (box[0] + at[0], box[1] + at[1], box[2] + at[0], box[3] + at[1])


def _padded(group: Group, content: Box) -> Box:
    """A boundary's extent around what it holds, as the layout sizes it:
    the padding, and room for its name when the name is the wider."""
    pad = LAYOUT["boundaryPad"]
    extra = max(0, title_room(group.data.get("label", "")) + (28 if group.data.get("icon") else 0)
                - (content[2] - content[0])) / 2
    return (content[0] - pad - extra, content[1] - pad - LAYOUT["boundaryLabel"], content[2] + pad + extra,
            content[3] + pad)


def free_spot(occupied: Sequence[Box], w: float, h: float) -> Tuple[float, float]:
    """Where a box of this size goes in a frame holding these: beside or
    under one of them, clear of all by the gaps, growing what the frame
    holds least, and of equal growth the highest and then the leftmost, so
    a hole is filled in reading order before the frame grows."""
    whole = _union(occupied)
    candidates = [(whole[0], whole[3] + GAP_Y), (whole[2] + GAP_X, whole[1])]
    for r in occupied:
        candidates.append((r[2] + GAP_X, r[1]))
        candidates.append((r[0], r[3] + GAP_Y))
    best: Optional[Tuple[float, float, float]] = None
    for x, y in candidates:
        if any(r[0] - GAP_X < x + w and x < r[2] + GAP_X and r[1] - GAP_Y < y + h and y < r[3] + GAP_Y
               for r in occupied):
            continue
        grown = (max(whole[2], x + w) - min(whole[0], x)) * (max(whole[3], y + h) - min(whole[1], y))
        if best is None or (grown, y, x) < best:
            best = (grown, y, x)
    assert best is not None  # under everything is always clear
    return best[2], best[1]


def arrange(prep: Prepared, lay: LayeredLayout, positions: Dict[str, Sequence[float]]) -> LayeredLayout:
    """The layout with what was kept put back where it was kept, and the
    rest placed around it. `lay` is the layout's own proposal, which
    decides where anything not kept goes; a drawing with nothing kept is
    returned as it came."""
    kept = {str(k): (float(v[0]), float(v[1])) for k, v in (positions or {}).items()}
    if not kept:
        return lay
    children: Dict[Optional[str], List[object]] = {}
    for group in prep.groups:
        children.setdefault(group.parent, []).append(group)
    for leaf in prep.leaves:
        children.setdefault(leaf.parent, []).append(leaf)
    path: Dict[str, Tuple[str, ...]] = {}
    for group in prep.groups:
        path[group.id] = (path[group.parent] if group.parent else ()) + (str(group.data.get("value")),)

    def key(node) -> str:
        if isinstance(node, Group):
            return position_key(path[node.id])
        return position_key(path[node.parent] if node.parent else (), node.id)

    def auto_extent(node) -> Box:
        if isinstance(node, Leaf):
            x, y = lay.leaves[node.id][:2]
            return (x - node.w / 2, y - node.h / 2, x + node.w / 2, y + node.h / 2)
        return _padded(node, _union([auto_extent(c) for c in children.get(node.id, [])]))

    at: Dict[str, Tuple[float, float]] = {}
    extent: Dict[str, Box] = {}

    def own(node) -> Box:
        return (0.0, 0.0, float(node.w), float(node.h)) if isinstance(node, Leaf) else extent[node.id]

    def frame(parent: Optional[Group]) -> None:
        kids = children.get(parent.id if parent else None, [])
        for kid in kids:
            if isinstance(kid, Group):
                frame(kid)
        held = [kid for kid in kids if key(kid) in kept]
        if not held:
            proposed = [(kid, auto_extent(kid)) for kid in kids]
            mx, my = min(a[0] for _k, a in proposed), min(a[1] for _k, a in proposed)
            for kid, a in proposed:
                o = own(kid)
                at[kid.id] = (a[0] - mx - o[0], a[1] - my - o[1])
        else:
            occupied: List[Box] = []
            for kid in held:
                at[kid.id] = kept[key(kid)]
                occupied.append(_shift(own(kid), at[kid.id]))
            # In the order the layout read them; on a tie, the payload's.
            fresh = sorted((kid for kid in kids if key(kid) not in kept),
                           key=lambda kid: (auto_extent(kid)[1], auto_extent(kid)[0]))
            for kid in fresh:
                o = own(kid)
                x, y = free_spot(occupied, o[2] - o[0], o[3] - o[1])
                at[kid.id] = (x - o[0], y - o[1])
                occupied.append((x, y, x + o[2] - o[0], y + o[3] - o[1]))
        if parent is not None:
            extent[parent.id] = _padded(parent, _union([_shift(own(kid), at[kid.id]) for kid in kids]))

    frame(None)

    leaves: Dict[str, Tuple[float, float, int, int]] = {}
    groups: Dict[str, Box] = {}

    def lay_down(parent: Optional[Group], ox: float, oy: float) -> None:
        for kid in children.get(parent.id if parent else None, []):
            px, py = at[kid.id]
            if isinstance(kid, Group):
                groups[kid.id] = _shift(extent[kid.id], (ox + px, oy + py))
                lay_down(kid, ox + px, oy + py)
            else:
                leaves[kid.id] = (ox + px + kid.w / 2, oy + py + kid.h / 2, kid.w, kid.h)

    lay_down(None, 0.0, 0.0)
    return lay._replace(leaves=leaves, groups=groups)


def kept_from(prep: Prepared, lay: LayeredLayout) -> Dict[str, Tuple[int, int]]:
    """What a drawing keeps the moment it is first arranged: every box and
    boundary where it is now, in whole pixels. `keepAll()` in the app. A
    box's corner is its top-left; a boundary's is the least corner of what
    it holds, so the first thing in every frame sits near [0, 0]. Each
    corner is rounded where it is on the sheet and the difference taken
    after, so arranging what was kept puts every box back within half a
    pixel, however deep it sits."""
    children: Dict[Optional[str], List[object]] = {}
    for group in prep.groups:
        children.setdefault(group.parent, []).append(group)
    for leaf in prep.leaves:
        children.setdefault(leaf.parent, []).append(leaf)
    keys = keys_of(prep)
    corner: Dict[str, Tuple[int, int]] = {}

    def visit(parent: Optional[Group]) -> None:
        kids = children.get(parent.id if parent else None, [])
        for kid in kids:
            if isinstance(kid, Group):
                visit(kid)
            else:
                x, y = lay.leaves[kid.id][:2]
                corner[kid.id] = (js_round(x - kid.w / 2), js_round(y - kid.h / 2))
        if parent is not None and kids:
            corner[parent.id] = (min(corner[k.id][0] for k in kids), min(corner[k.id][1] for k in kids))

    visit(None)
    out: Dict[str, Tuple[int, int]] = {}

    def record(parent: Optional[Group], origin: Tuple[int, int]) -> None:
        for kid in children.get(parent.id if parent else None, []):
            out[keys[kid.id]] = (corner[kid.id][0] - origin[0], corner[kid.id][1] - origin[1])
            if isinstance(kid, Group):
                record(kid, corner[kid.id])

    top = children.get(None, [])
    if top:
        record(None, (min(corner[k.id][0] for k in top), min(corner[k.id][1] for k in top)))
    return out


def keys_of(prep: Prepared) -> Dict[str, str]:
    """Every box's and boundary's key in `positions`, by its id on the
    drawing: what a test or a caller names a thing by."""
    path: Dict[str, Tuple[str, ...]] = {}
    out: Dict[str, str] = {}
    for group in prep.groups:
        path[group.id] = (path[group.parent] if group.parent else ()) + (str(group.data.get("value")),)
        out[group.id] = position_key(path[group.id])
    for leaf in prep.leaves:
        out[leaf.id] = position_key(path[leaf.parent] if leaf.parent else (), leaf.id)
    return out

