"""Which layout a view gets, the way `drawGraph()` decides it on Auto.

The app reads the payload before it draws: a map with nothing connected is
tiles; a view that asks for a wheel or an organic layout gets that; a
catalog with few edges per node is packed even when it calls itself a
diagram, and so is every map; everything else is layered, by ELK where the
drawing is small and unlaned and by dagre otherwise. The Python drawing
covers the tiles, the packed, the wheel and the dagre paths, and the ELK
and organic ones through a browser. What it does not cover is refused
here with the reason, so a caller can say why rather than draw something
else; without a browser the ELK views are drawn the way the app draws
them without ELK, on the dagre path, and the mode says so.
"""

from __future__ import annotations

from typing import NamedTuple, Optional

from .packed import Prepared, prepare

#: A graph with this few edges per node is a catalog rather than a flow.
CATALOG_EDGE_RATIO = 0.5
#: What `elkFits` hands to ELK: nothing laned, this many leaves and
#: boundaries at most.
ELK_LEAVES = 30
ELK_GROUPS = 8


class Undrawable(ValueError):
    """The app draws this view a way the Python drawing does not cover.
    `layout` is that way in a word -- tiles, organic, concentric -- for an
    index that has room for a word and not for the reason."""

    def __init__(self, message: str, layout: str = "") -> None:
        super().__init__(message)
        self.layout = layout


class Mode(NamedTuple):
    #: "tiles", "packed", "wheel" or "layered".
    kind: str
    #: True when the app itself would hand the drawing to ELK: the Python
    #: picture is the app's dagre fallback, not the picture the app shows.
    fallback: bool


def is_tile_map(payload: dict) -> bool:
    return payload.get("kind") == "map" and not payload.get("sketch") and not any(
        e["data"].get("source") for e in payload.get("elements", []))


def is_catalog(payload: dict) -> bool:
    counts = payload.get("counts") or {}
    nodes, edges = int(counts.get("nodes", 0)), int(counts.get("edges", 0))
    return nodes > 8 and edges / max(nodes, 1) < CATALOG_EDGE_RATIO


def elk_fits(payload: dict, prep: Prepared) -> bool:
    lanes = payload.get("lanes") or {}
    laned = any(lanes.get(str(g.data.get("kind") or "")) for g in prep.groups)
    return not laned and len(prep.leaves) <= ELK_LEAVES and len(prep.groups) <= ELK_GROUPS


def drawing_mode(payload: dict, prepared: Optional[Prepared] = None) -> Mode:
    """The layout the app would give this view on Auto, or `Undrawable`
    with the reason the Python drawing cannot give it."""
    view = payload.get("viewId") or payload.get("title") or "the view"
    if is_tile_map(payload):
        return Mode("tiles", False)
    asked = str(payload.get("layout") or "").lower()
    if asked == "concentric":
        return Mode("wheel", False)
    if asked in ("cose", "grid"):
        raise Undrawable("%s asks for a %s layout, which has no Python layout" % (view, asked), asked)
    if is_catalog(payload) or payload.get("kind") == "map":
        return Mode("packed", False)
    prep = prepared or prepare(payload)
    return Mode("layered", elk_fits(payload, prep))
