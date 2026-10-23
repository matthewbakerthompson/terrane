"""ELK, through the browser: the app's own layout for the small diagrams.

The app hands a small, unlaned diagram -- thirty leaves and eight
boundaries at most, which is most of the subject views -- to ELK, the
Eclipse Layout Kernel, and ELK lays a boundary out as a container rather
than as the box around wherever its children landed, routes every edge
orthogonally around nodes and boundaries, and puts each label where it
overlaps nothing. The Python drawing had dagre for those, the app's own
fallback, and the sheet said so. A port of ELK's layered algorithm is a
far larger piece of work than dagre was; the other road is to run the
same `elk.bundled.js` the app loads, in the same kind of place, a browser,
which the engine already drives for PNGs (`terrane.draw.browser`). This is
that road: the graph is built exactly as `elkGraph` in `app.js` builds it,
option for option and in the same order, laid out by elkjs in a headless
Chrome or Edge, and read back the way `applyElk` reads it, so the picture
is the app's picture. ELK is deterministic for a given graph, so the SVG
is the same bytes on every run and every platform, which the committed
pictures depend on. Without a browser the dagre path draws and the sheet
says `dagre-for-elk`, as before.
"""

from __future__ import annotations

import atexit
import json
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

from .browser import Chrome, browser_path
from .labels import LABEL_H, label_px
from .layered import LayeredLayout
from .packed import Group, Leaf, Prepared, title_room
from .shapes import LAYOUT, edge_word

Point = Tuple[float, float]
Box = Tuple[float, float, float, float]

#: The room ELK leaves at the top of a container for the boundary's name.
PAD_TOP = LAYOUT["boundaryPad"] + 14
#: The root's options, as `elkGraph` sets them; the direction is filled in
#: per run.
ROOT_OPTIONS = {
    "elk.algorithm": "layered",
    "elk.hierarchyHandling": "INCLUDE_CHILDREN",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.layered.spacing.nodeNodeBetweenLayers": "44",
    "elk.spacing.nodeNode": "18",
    "elk.spacing.edgeNode": "12",
    "elk.spacing.edgeEdge": "10",
    "elk.layered.spacing.edgeNodeBetweenLayers": "16",
    "elk.layered.spacing.edgeEdgeBetweenLayers": "10",
    "elk.spacing.componentComponent": "36",
    "elk.spacing.edgeLabel": "4",
    "elk.edgeLabels.inline": "true",
    "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
    "elk.layered.nodePlacement.favorStraightEdges": "true",
    "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
    "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
    # No post-compaction, as the app has none: it slid boxes along the rank
    # after the lines crossing boundaries were routed, and those lines ran
    # past their turn and back.
    "elk.layered.compaction.connectedComponents": "true",
    "elk.layered.unnecessaryBendpoints": "true",
    "elk.layered.thoroughness": "10",
    "elk.padding": "[top=12,left=12,bottom=12,right=12]",
}
#: What the app keeps the other direction for: a markedly better fit.
OTHER_DIRECTION_WINS = 1.3
VENDOR_FILE = "elk.bundled.js"

Runner = Callable[[dict], dict]


class ElkRoute(NamedTuple):
    """An edge as ELK routed it, in drawing coordinates: where it leaves,
    where it bends, where it arrives."""
    edge_id: str
    start: Point
    bends: List[Point]
    end: Point


class ElkLayout(NamedTuple):
    layout: LayeredLayout
    routes: Dict[str, ElkRoute]
    #: Edge id to the center of the label ELK placed, for the labels it was
    #: given (the ones that would be shown).
    labels: Dict[str, Point]
    #: ELK's own size of the whole drawing, for choosing the direction.
    width: float
    height: float


def elk_graph(payload: dict, prep: Prepared, direction: str) -> dict:
    """`elkGraph(cy, dir)`: the ELK graph of the drawing, the nodes and
    boundaries nested as the payload nests them and in its order, each
    boundary padded for its name and at least as wide as it, the siblings
    that are boundaries of a laned field partitioned in the lanes' order,
    and every edge between two leaves with a box for the label that will
    be shown."""
    lanes = {str(k): [str(v) for v in vs] for k, vs in (payload.get("lanes") or {}).items()}
    by_id: Dict[str, object] = {}
    for leaf in prep.leaves:
        by_id[leaf.id] = leaf
    for group in prep.groups:
        by_id[group.id] = group
    children: Dict[Optional[str], List[str]] = {}
    for element in payload.get("elements", []):
        data = element.get("data") or {}
        if data.get("source") or data.get("id") not in by_id:
            continue
        children.setdefault(data.get("parent") or None, []).append(str(data["id"]))

    def lane_index(node) -> Optional[int]:
        data = node.data
        order = lanes.get(str(data.get("kind") or ""))
        if not order:
            return None
        value = str(data.get("value"))
        return order.index(value) if value in order else len(order)

    def lanes_of(kid_ids: List[str], parent: dict) -> None:
        indices = {k: lane_index(by_id[k]) for k in kid_ids}
        indices = {k: i for k, i in indices.items() if i is not None}
        if not indices:
            return
        parent.setdefault("layoutOptions", {})["elk.partitioning.activate"] = "true"
        most = max(indices.values())
        for child in parent.get("children", []):
            child.setdefault("layoutOptions", {})["elk.partitioning.partition"] = str(indices.get(child["id"], most + 1))

    def build(node_id: str) -> dict:
        node = by_id[node_id]
        out: dict = {"id": node_id}
        if isinstance(node, Group):
            kids = children.get(node_id, [])
            out["children"] = [build(k) for k in kids]
            pad = LAYOUT["boundaryPad"]
            out["layoutOptions"] = {
                "elk.padding": "[top=%d,left=%d,bottom=%d,right=%d]" % (PAD_TOP, pad, pad, pad),
                "elk.nodeSize.minimum": "(%d,40)" % (title_room(str(node.data.get("label") or ""))
                                                     + (28 if node.data.get("icon") else 0)),
                "elk.nodeSize.constraints": "MINIMUM_SIZE",
            }
            lanes_of(kids, out)
        else:
            assert isinstance(node, Leaf)
            out["width"] = node.w
            out["height"] = node.h
        return out

    roots = children.get(None, [])
    root: dict = {"id": "__root", "children": [build(r) for r in roots], "edges": []}
    root["layoutOptions"] = dict(ROOT_OPTIONS)
    root["layoutOptions"]["elk.direction"] = "DOWN" if direction == "TB" else "RIGHT"
    lanes_of(roots, root)
    leaves = {leaf.id for leaf in prep.leaves}
    said = set()
    for edge in prep.edges:
        source, target = str(edge.get("source")), str(edge.get("target"))
        if source not in leaves or target not in leaves or source == target:
            continue
        entry: dict = {"id": str(edge["id"]), "sources": [source], "targets": [target]}
        text = str(edge.get("label") or "")
        redundant = bool(text) and text.lower() == str(edge_word(str(edge.get("kind") or "")) or "").lower()
        pair = "|".join(sorted([source, target])) + "|" + text
        if text and not redundant and pair not in said:
            said.add(pair)
            entry["labels"] = [{"text": text, "width": label_px(text) + 6, "height": LABEL_H + 4}]
        root["edges"].append(entry)
    return root


def apply_elk(prep: Prepared, out: dict, direction: str, ratio: float) -> ElkLayout:
    """`applyElk(cy, root)`: ELK's answer in drawing coordinates. Every
    position ELK gives is relative to its container, so the containers'
    origins are walked down; a leaf's center is its box's middle; an edge's
    section and label come back through the origin of the node the edge is
    attached to."""
    origin: Dict[str, Point] = {str(out.get("id") or "__root"): (0.0, 0.0)}
    centers: Dict[str, Point] = {}
    boxes: Dict[str, Box] = {}

    def walk(node: dict, ox: float, oy: float) -> None:
        for child in node.get("children") or []:
            ax, ay = ox + float(child.get("x") or 0), oy + float(child.get("y") or 0)
            origin[str(child["id"])] = (ax, ay)
            w, h = float(child.get("width") or 0), float(child.get("height") or 0)
            if child.get("children"):
                boxes[str(child["id"])] = (ax, ay, ax + w, ay + h)
                walk(child, ax, ay)
            else:
                centers[str(child["id"])] = (ax + w / 2, ay + h / 2)

    walk(out, 0.0, 0.0)
    leaves = {leaf.id: (centers[leaf.id][0], centers[leaf.id][1], leaf.w, leaf.h)
              for leaf in prep.leaves if leaf.id in centers}
    groups = {group.id: boxes[group.id] for group in prep.groups if group.id in boxes}
    edges: List[dict] = []

    def collect(node: dict) -> None:
        edges.extend(node.get("edges") or [])
        for child in node.get("children") or []:
            collect(child)

    collect(out)
    routes: Dict[str, ElkRoute] = {}
    labels: Dict[str, Point] = {}
    root_origin = origin[str(out.get("id") or "__root")]
    for edge in edges:
        o = origin.get(str(edge.get("container") or ""), root_origin)

        def absolute(point: dict) -> Point:
            return (o[0] + float(point.get("x") or 0), o[1] + float(point.get("y") or 0))

        sections = edge.get("sections") or []
        if sections:
            section = sections[0]
            routes[str(edge["id"])] = ElkRoute(str(edge["id"]), absolute(section["startPoint"]),
                                               [absolute(b) for b in section.get("bendPoints") or []],
                                               absolute(section["endPoint"]))
        placed = (edge.get("labels") or [None])[0]
        if placed and "x" in placed:
            labels[str(edge["id"])] = absolute({"x": float(placed["x"]) + float(placed.get("width") or 0) / 2,
                                                "y": float(placed["y"]) + float(placed.get("height") or 0) / 2})
    layout = LayeredLayout(leaves=leaves, groups=groups, ratio=ratio, direction=direction, edge_axis={})
    return ElkLayout(layout, routes, labels, float(out.get("width") or 1), float(out.get("height") or 1))


def layout_elk(payload: dict, prep: Prepared, runner: Runner, sheet_width: float = 1240,
               sheet_height: float = 871.4375) -> ElkLayout:
    """`layoutElk(cy, dir, tryBoth)`: the drawing laid out in the view's
    direction and the other, keeping the one that fits the sheet at the
    larger zoom unless the view's own is close."""
    preferred = "TB" if str(payload.get("layout") or "LR").upper() in ("TB", "TD", "BT") else "LR"
    other = "LR" if preferred == "TB" else "TB"
    ratio = sheet_width / sheet_height if sheet_height else 1.4

    def run(direction: str) -> ElkLayout:
        return apply_elk(prep, runner(elk_graph(payload, prep, direction)), direction, ratio)

    def zoom(result: ElkLayout) -> float:
        return min(sheet_width / max(result.width, 1), sheet_height / max(result.height, 1))

    own = run(preferred)
    alternative = run(other)
    return alternative if zoom(alternative) > zoom(own) * OTHER_DIRECTION_WINS else own


def vendor_file(web: Optional[Path], name: str = VENDOR_FILE) -> Optional[Path]:
    """Where `elk.bundled.js` is (or another of the app's vendored scripts,
    by `name`): the app's vendor folder in a repository, the copy in the
    package otherwise, None when neither has it."""
    if web is None:
        return None
    path = Path(web) / "vendor" / name
    return path if path.is_file() else None


#: The app's Cytoscape, for the organic pass (`terrane.draw.organic`).
CYTOSCAPE_FILE = "cytoscape.min.js"


class ElkRunner:
    """One headless browser with elkjs loaded, laying out graph after graph;
    opened on the first graph, so a render that meets no small diagram
    launches nothing. `means` says what runs it, for the sheet and the
    index. Close it, or use it as a context manager. With the app's
    Cytoscape at hand as well (`cytoscape`), the same page runs the organic
    pass for the ribbons the app lays out that way (`cose`)."""

    def __init__(self, script: Path, cytoscape: Optional[Path] = None) -> None:
        self.script = Path(script)
        self.cytoscape = Path(cytoscape) if cytoscape else None
        self.means = Path(browser_path() or "").stem or "browser"
        self._browser: Optional[Chrome] = None
        self._page = None
        self._cytoscape_loaded = False

    @property
    def has_cose(self) -> bool:
        return self.cytoscape is not None

    def cose(self, graph: dict) -> Dict[str, Tuple[float, float]]:
        """Every node's center after Cytoscape's cose, run headless in the
        page on `graph` as `terrane.draw.organic.cose_graph` builds it."""
        from .organic import COSE_SCRIPT

        if self.cytoscape is None:
            raise RuntimeError("no cytoscape bundle at hand for the organic layout")
        if self._page is None:
            self._open()
        assert self._page is not None
        if not self._cytoscape_loaded:
            self._page.evaluate(self.cytoscape.read_text(encoding="utf-8"))
            if not self._page.evaluate('typeof window.cytoscape === "function"'):
                raise RuntimeError("%s did not define cytoscape" % self.cytoscape)
            self._cytoscape_loaded = True
        text = self._page.evaluate(COSE_SCRIPT % json.dumps(graph))
        return {node_id: (float(xy[0]), float(xy[1])) for node_id, xy in json.loads(text).items()}

    def _open(self) -> None:
        self._browser = Chrome(width=1200, height=800).__enter__()
        self._page = self._browser.page("about:blank")
        # The bundle is a plain script: evaluating its text defines ELK on
        # the window, the way a script tag would.
        self._page.evaluate(self.script.read_text(encoding="utf-8"))
        if not self._page.evaluate('typeof window.ELK === "function"'):
            raise RuntimeError("%s did not define ELK" % self.script)
        self._page.evaluate("window.__elk = new window.ELK()")

    def __call__(self, graph: dict) -> dict:
        if self._page is None:
            self._open()
        assert self._page is not None
        text = self._page.evaluate(
            "window.__elk.layout(%s).then(function (out) { return JSON.stringify(out); })" % json.dumps(graph),
            await_promise=True)
        return json.loads(text)

    def close(self) -> None:
        if self._browser is not None:
            self._browser.__exit__(None, None, None)
            self._browser = None
            self._page = None
            self._cytoscape_loaded = False

    def __enter__(self) -> "ElkRunner":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class SharedRunner:
    """The process's one ELK runner for a bundle, handed out to every
    render and never closed by them: a notebook drawing sketch after
    sketch paid a browser launch, a bundle sent and a second's wait on
    each, and a test suite paid it a few hundred times. `close` is a
    courtesy that keeps the browser; the process closes it at exit, and a
    browser that has gone away is opened again on the next graph."""

    def __init__(self, runner: ElkRunner) -> None:
        self._runner = runner

    @property
    def means(self) -> str:
        return self._runner.means

    @property
    def has_cose(self) -> bool:
        return self._runner.has_cose

    def _retrying(self, work):
        try:
            return work()
        except (ConnectionError, OSError, RuntimeError):
            self._runner.close()
            return work()

    def __call__(self, graph: dict) -> dict:
        return self._retrying(lambda: self._runner(graph))

    def cose(self, graph: dict) -> Dict[str, Tuple[float, float]]:
        return self._retrying(lambda: self._runner.cose(graph))

    def close(self) -> None:
        pass

    def __enter__(self) -> "SharedRunner":
        return self

    def __exit__(self, *exc) -> None:
        pass


_SHARED: Dict[Path, SharedRunner] = {}


def _close_shared() -> None:
    for shared in _SHARED.values():
        shared._runner.close()
    _SHARED.clear()


atexit.register(_close_shared)


def open_runner(web: Optional[Path]) -> Optional[SharedRunner]:
    """An ELK runner when the machine has a browser and the bundle is at
    hand; None otherwise, and the dagre path draws. One runner per bundle
    for the whole process (`SharedRunner`), its browser opened on the
    first graph and kept for the next render."""
    script = vendor_file(web)
    if script is None or not browser_path():
        return None
    key = script.resolve()
    if key not in _SHARED:
        _SHARED[key] = SharedRunner(ElkRunner(script, vendor_file(web, CYTOSCAPE_FILE)))
    return _SHARED[key]
