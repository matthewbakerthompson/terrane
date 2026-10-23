"""The wheel: a hub in the middle and its spokes on one ring, placed as
Cytoscape's concentric layout places them under the app's options.

`hub-and-spoke` asks for `layout: concentric`, and the app honors it: the
best-connected node in the center, everything else on one ring, spread
evenly, the first spoke straight down and the rest clockwise. The
algorithm here is Cytoscape's own, read from the bundle the app loads.
Every leaf gets a level value, the app's being 2 for the node of highest
degree and 1 for the rest; the leaves are sorted by it, a new ring begun
wherever the value drops by the level width (one); each ring's radius is
the larger of what keeps its nodes `minNodeSpacing` apart on the arc and
the previous ring's radius plus that spacing, where the spacing is the
largest node's outer side plus the option; `equidistant` then spaces the
rings evenly. The center is the container's, which here is the sheet's;
the sheet frames the drawing afterward, so where the center falls does
not show.

Sines and cosines are summed here rather than taken from the C library,
so the same drawing is the same bytes on every platform; the angles are
reduced to half a turn and the series is exact to the last place long
before its twenty-fourth term.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from .mode import Undrawable
from .packed import Layout, Leaf, Prepared, prepare, sheet_ratio

PI = 3.141592653589793
#: The app's options for the concentric layout.
MIN_NODE_SPACING = 70.0
LEVEL_WIDTH = 1.0
START_ANGLE = PI / 2
CLOCKWISE = True


def _reduce(angle: float) -> float:
    """The angle brought into [-pi, pi), where the series converges fast."""
    turn = 2 * PI
    return angle - turn * math.floor((angle + PI) / turn)


def sin(angle: float) -> float:
    x = _reduce(angle)
    term = total = x
    for k in range(1, 24):
        term *= -x * x / ((2 * k) * (2 * k + 1))
        total += term
        if abs(term) < 1e-18:
            break
    return total


def cos(angle: float) -> float:
    x = _reduce(angle)
    term = total = 1.0
    for k in range(1, 24):
        term *= -x * x / ((2 * k - 1) * (2 * k))
        total += term
        if abs(term) < 1e-18:
            break
    return total


def degrees(prep: Prepared) -> Dict[str, int]:
    """Cytoscape's `degree(false)` for every leaf: each edge at the node
    counted once, a loop not at all."""
    out = {leaf.id: 0 for leaf in prep.leaves}
    for edge in prep.edges:
        source, target = edge["source"], edge["target"]
        if source == target or source not in out or target not in out:
            continue
        out[source] += 1
        out[target] += 1
    return out


def rings(values: List[Tuple[float, Leaf]], spacing: float) -> List[Tuple[float, float, List[Leaf]]]:
    """Cytoscape's rings for leaves already sorted by value, highest first:
    each as (radius, step angle, leaves). `spacing` is the largest node's
    outer side plus the option."""
    levels: List[List[Tuple[float, Leaf]]] = [[]]
    for item in values:
        if levels[-1] and abs(levels[-1][0][0] - item[0]) >= LEVEL_WIDTH:
            levels.append([])
        levels[-1].append(item)
    out: List[Tuple[float, float, List[Leaf]]] = []
    radius = 0.0
    for level in levels:
        n = len(level)
        sweep = 2 * PI - 2 * PI / n
        step = sweep / max(1, n - 1)
        if n > 1:
            dx, dy = cos(step) - 1.0, sin(step)
            radius = max(math.sqrt(spacing * spacing / (dx * dx + dy * dy)), radius)
        out.append((radius, step, [leaf for _, leaf in level]))
        radius += spacing
    # `equidistant`: every ring the same distance out as the widest gap,
    # which for two rings is the second's own radius.
    gap = max((r for r, _, _ in out), default=0.0)
    spaced: List[Tuple[float, float, List[Leaf]]] = []
    at = out[0][0] if out else 0.0
    for r, step, leaves in out:
        spaced.append((at, step, leaves))
        at += gap
    return spaced


def layout_wheel(payload: dict, sheet_width: float = 1240, sheet_height: float = 871.4375,
                 prepared: Prepared = None) -> Layout:
    """Where the app puts every leaf of a view that asks for the wheel."""
    prep = prepared or prepare(payload)
    if prep.groups:
        raise Undrawable("%s asks for a wheel and has boundaries, which the wheel does not place"
                         % (payload.get("viewId") or "the view"), "concentric")
    degree = degrees(prep)
    top = max(degree.values(), default=0)
    ranked = sorted(((2.0 if degree[leaf.id] == top else 1.0, leaf) for leaf in prep.leaves),
                    key=lambda item: -item[0])  # stable, as Array.prototype.sort is
    largest = 0.0
    for leaf in prep.leaves:
        border = float(leaf.data.get("strokeWidth") or 1)
        largest = max(largest, leaf.w + border, leaf.h + border)
    # Cytoscape centers on its container, whose height is a whole pixel.
    cx, cy = sheet_width / 2, int(sheet_height + 0.5) / 2
    leaves: Dict[str, Tuple[float, float, int, int]] = {}
    for radius, step, ring in rings(ranked, largest + MIN_NODE_SPACING):
        for i, leaf in enumerate(ring):
            angle = START_ANGLE + (1 if CLOCKWISE else -1) * step * i
            leaves[leaf.id] = (cx + radius * cos(angle), cy + radius * sin(angle), leaf.w, leaf.h)
    return Layout(leaves, {}, sheet_ratio(sheet_width, sheet_height))
