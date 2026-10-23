"""dagre 0.8.5, in Python, as far as the app's drawings exercise it.

The app ranks a layered drawing with the dagre the browser ships
(`80_APP/web/vendor/dagre.min.js`): one graph per boundary level, nodes with
a width and a height, unlabeled edges, `nodesep`, `ranksep`, `edgesep`, no
margins, and it reads back where each node's center landed. This module is
that library's pipeline written out in Python so the same graph lands on the
same centers: acyclic by depth-first search, ranking by network simplex over
a feasible tight tree, long edges split into dummy chains, ordering by
barycenter sweeps with a weighted crossing count, and coordinates by
Brandes-Köpf with the block-graph compaction dagre substitutes for the
paper's. `tests/test_draw_layered.py` holds the result equal to what the
browser computed, so a step here that dagre does not take, or the other way
round, fails there.

Where dagre breaks a tie it does so by the order its graph happens to hold
things in: the order nodes and edges were added, since graphlib keeps them
in plain objects, and a first-wins minimum. `Graph` below keeps the same
orders on purpose, including the one graphlib quirk that matters here: an
undirected graph stores each edge with its endpoints in lexical order, so
the tight tree's neighbors come out smaller-first. Nothing in the app's
graphs is a compound node, a self-edge or an edge label with a size, and
the steps that only act on those are carried as the no-ops they are rather
than ported in full; a graph that has one is refused rather than laid out
differently from dagre. lodash's `uniqueId` numbers the dummies; the
numbers never decide anything, so the counter here starts over per layout.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple


class DagreError(ValueError):
    """The graph asks for a part of dagre this port does not carry."""


# ---------------------------------------------------------------------------
# graphlib
# ---------------------------------------------------------------------------

#: graphlib's name for the invisible root every top-level node hangs from.
GRAPH_NODE = "\x00"
_UNSET = object()


class EdgeObj:
    """graphlib's frozen `{v, w, name}`: equal and hashable by its three
    parts, so `g.edge(e)` finds the label whichever copy `e` is."""

    __slots__ = ("v", "w", "name")

    def __init__(self, v: str, w: str, name: Optional[str] = None) -> None:
        self.v, self.w, self.name = v, w, name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, EdgeObj) and (self.v, self.w, self.name) == (other.v, other.w, other.name)

    def __hash__(self) -> int:
        return hash((self.v, self.w, self.name))

    def __repr__(self) -> str:
        return "EdgeObj(%r, %r, %r)" % (self.v, self.w, self.name)


def _edge_key(directed: bool, v: str, w: str, name: Optional[str]) -> Tuple[str, str, Optional[str]]:
    if not directed and v > w:
        v, w = w, v
    return (v, w, name)


class Graph:
    """graphlib's `Graph`, with every collection insertion-ordered the way a
    JavaScript object keeps string keys, since dagre's tie-breaks read
    those orders."""

    def __init__(self, directed: bool = True, multigraph: bool = False, compound: bool = False) -> None:
        self._directed = directed
        self._multigraph = multigraph
        self._compound = compound
        self._label: dict = {}
        self._default_node_label: Callable[[str], object] = lambda v: None
        self._default_edge_label: Callable[[str, str, Optional[str]], object] = lambda v, w, name: None
        self._nodes: Dict[str, object] = {}
        self._in: Dict[str, Dict[tuple, EdgeObj]] = {}
        self._preds: Dict[str, Dict[str, int]] = {}
        self._out: Dict[str, Dict[tuple, EdgeObj]] = {}
        self._sucs: Dict[str, Dict[str, int]] = {}
        self._edge_objs: Dict[tuple, EdgeObj] = {}
        self._edge_labels: Dict[tuple, object] = {}
        if compound:
            self._parent: Dict[str, str] = {}
            self._children: Dict[str, Dict[str, bool]] = {GRAPH_NODE: {}}

    # -- graph ------------------------------------------------------------
    def is_directed(self) -> bool:
        return self._directed

    def is_multigraph(self) -> bool:
        return self._multigraph

    def is_compound(self) -> bool:
        return self._compound

    def set_graph(self, label: dict) -> "Graph":
        self._label = label
        return self

    def graph(self) -> dict:
        return self._label

    def set_default_node_label(self, fn: Callable[[str], object]) -> "Graph":
        self._default_node_label = fn
        return self

    def set_default_edge_label(self, fn: Callable[[str, str, Optional[str]], object]) -> "Graph":
        self._default_edge_label = fn
        return self

    # -- nodes ------------------------------------------------------------
    def node_count(self) -> int:
        return len(self._nodes)

    def nodes(self) -> List[str]:
        return list(self._nodes)

    def sources(self) -> List[str]:
        return [v for v in self._nodes if not self._in[v]]

    def sinks(self) -> List[str]:
        return [v for v in self._nodes if not self._out[v]]

    def set_node(self, v: str, label: object = _UNSET) -> "Graph":
        if v in self._nodes:
            if label is not _UNSET:
                self._nodes[v] = label
            return self
        self._nodes[v] = label if label is not _UNSET else self._default_node_label(v)
        if self._compound:
            self._parent[v] = GRAPH_NODE
            self._children[v] = {}
            self._children[GRAPH_NODE][v] = True
        self._in[v] = {}
        self._preds[v] = {}
        self._out[v] = {}
        self._sucs[v] = {}
        return self

    def node(self, v: str):
        return self._nodes.get(v)

    def has_node(self, v: str) -> bool:
        return v in self._nodes

    def remove_node(self, v: str) -> "Graph":
        if v not in self._nodes:
            return self
        del self._nodes[v]
        if self._compound:
            self._remove_from_parents_child_list(v)
            del self._parent[v]
            for child in self.children(v):
                self.set_parent(child)
            del self._children[v]
        for e in list(self._in[v].values()):
            self.remove_edge(e)
        del self._in[v]
        del self._preds[v]
        for e in list(self._out[v].values()):
            self.remove_edge(e)
        del self._out[v]
        del self._sucs[v]
        return self

    def set_parent(self, v: str, parent: Optional[str] = None) -> "Graph":
        if not self._compound:
            raise DagreError("cannot set parent in a non-compound graph")
        if parent is None:
            parent = GRAPH_NODE
        else:
            ancestor = parent
            while ancestor is not None:
                if ancestor == v:
                    raise DagreError("setting %s as parent of %s would create a cycle" % (parent, v))
                ancestor = self.parent(ancestor)
            self.set_node(parent)
        self.set_node(v)
        self._remove_from_parents_child_list(v)
        self._parent[v] = parent
        self._children[parent][v] = True
        return self

    def _remove_from_parents_child_list(self, v: str) -> None:
        del self._children[self._parent[v]][v]

    def parent(self, v: str) -> Optional[str]:
        if self._compound:
            parent = self._parent.get(v)
            if parent != GRAPH_NODE:
                return parent
        return None

    def children(self, v: Optional[str] = None) -> List[str]:
        if v is None:
            v = GRAPH_NODE
        if self._compound:
            kids = self._children.get(v)
            if kids is not None:
                return list(kids)
        elif v == GRAPH_NODE:
            return self.nodes()
        elif v in self._nodes:
            return []
        return []

    def predecessors(self, v: str) -> List[str]:
        return list(self._preds[v]) if v in self._preds else []

    def successors(self, v: str) -> List[str]:
        return list(self._sucs[v]) if v in self._sucs else []

    def neighbors(self, v: str) -> List[str]:
        preds = self.predecessors(v)
        seen = set(preds)
        out = list(preds)
        for w in self.successors(v):
            if w not in seen:
                seen.add(w)
                out.append(w)
        return out

    # -- edges ------------------------------------------------------------
    def edge_count(self) -> int:
        return len(self._edge_objs)

    def edges(self) -> List[EdgeObj]:
        return list(self._edge_objs.values())

    def set_edge(self, v, w=None, label: object = _UNSET, name: Optional[str] = None) -> "Graph":
        if isinstance(v, EdgeObj):
            # `setEdge(edgeObj, value)`: the second argument is the label.
            if w is not None:
                label = w
            v, w, name = v.v, v.w, v.name
        key = _edge_key(self._directed, v, w, name)
        if key in self._edge_labels:
            if label is not _UNSET:
                self._edge_labels[key] = label
            return self
        if name is not None and not self._multigraph:
            raise DagreError("cannot set a named edge when multigraph is false")
        self.set_node(v)
        self.set_node(w)
        self._edge_labels[key] = label if label is not _UNSET else self._default_edge_label(v, w, name)
        v, w = key[0], key[1]
        obj = EdgeObj(v, w, name)
        self._edge_objs[key] = obj
        self._preds[w][v] = self._preds[w].get(v, 0) + 1
        self._sucs[v][w] = self._sucs[v].get(w, 0) + 1
        self._in[w][key] = obj
        self._out[v][key] = obj
        return self

    def edge(self, v, w=None, name: Optional[str] = None):
        if isinstance(v, EdgeObj):
            key = _edge_key(self._directed, v.v, v.w, v.name)
        else:
            key = _edge_key(self._directed, v, w, name)
        return self._edge_labels.get(key)

    def has_edge(self, v, w=None, name: Optional[str] = None) -> bool:
        if isinstance(v, EdgeObj):
            key = _edge_key(self._directed, v.v, v.w, v.name)
        else:
            key = _edge_key(self._directed, v, w, name)
        return key in self._edge_labels

    def remove_edge(self, v, w=None, name: Optional[str] = None) -> "Graph":
        if isinstance(v, EdgeObj):
            key = _edge_key(self._directed, v.v, v.w, v.name)
        else:
            key = _edge_key(self._directed, v, w, name)
        obj = self._edge_objs.get(key)
        if obj is None:
            return self
        v, w = key[0], key[1]
        del self._edge_labels[key]
        del self._edge_objs[key]
        self._preds[w][v] -= 1
        if not self._preds[w][v]:
            del self._preds[w][v]
        self._sucs[v][w] -= 1
        if not self._sucs[v][w]:
            del self._sucs[v][w]
        del self._in[w][key]
        del self._out[v][key]
        return self

    def in_edges(self, v: str, u: Optional[str] = None) -> List[EdgeObj]:
        edges = list(self._in[v].values()) if v in self._in else []
        if u is None:
            return edges
        return [e for e in edges if e.v == u]

    def out_edges(self, v: str, w: Optional[str] = None) -> List[EdgeObj]:
        edges = list(self._out[v].values()) if v in self._out else []
        if w is None:
            return edges
        return [e for e in edges if e.w == w]

    def node_edges(self, v: str, w: Optional[str] = None) -> List[EdgeObj]:
        return self.in_edges(v, w) + self.out_edges(v, w)


# ---------------------------------------------------------------------------
# lodash
# ---------------------------------------------------------------------------

class _Ids:
    """`_.uniqueId`: one counter for every prefix."""

    def __init__(self) -> None:
        self.n = 0

    def __call__(self, prefix: str) -> str:
        self.n += 1
        return "%s%d" % (prefix, self.n)


def _min_by(items: Iterable, key: Callable):
    """`_.minBy`: the first item whose key is smallest, skipping items whose
    key is None."""
    best, best_key = None, None
    for item in items:
        k = key(item)
        if k is None:
            continue
        if best_key is None or k < best_key:
            best, best_key = item, k
    return best


# ---------------------------------------------------------------------------
# util
# ---------------------------------------------------------------------------

def add_dummy_node(g: Graph, ids: _Ids, kind: str, attrs: dict, name: str) -> str:
    while True:
        v = ids(name)
        if not g.has_node(v):
            break
    attrs["dummy"] = kind
    g.set_node(v, attrs)
    return v


def simplify(g: Graph) -> Graph:
    simplified = Graph().set_graph(g.graph())
    for v in g.nodes():
        simplified.set_node(v, g.node(v))
    for e in g.edges():
        simple = simplified.edge(e.v, e.w) or {"weight": 0, "minlen": 1}
        label = g.edge(e)
        simplified.set_edge(e.v, e.w, {"weight": simple["weight"] + label["weight"],
                                       "minlen": max(simple["minlen"], label["minlen"])})
    return simplified


def as_non_compound_graph(g: Graph) -> Graph:
    simplified = Graph(multigraph=g.is_multigraph()).set_graph(g.graph())
    for v in g.nodes():
        if not g.children(v):
            simplified.set_node(v, g.node(v))
    for e in g.edges():
        simplified.set_edge(e, g.edge(e))
    return simplified


def max_rank(g: Graph) -> int:
    ranks = [g.node(v)["rank"] for v in g.nodes() if "rank" in g.node(v)]
    return max(ranks)


def build_layer_matrix(g: Graph) -> List[List[str]]:
    layering: List[Dict[int, str]] = [{} for _ in range(max_rank(g) + 1)]
    for v in g.nodes():
        node = g.node(v)
        if "rank" in node:
            layering[node["rank"]][node["order"]] = v
    # A JavaScript array indexed by order: read back in index order.
    return [[layer[i] for i in sorted(layer)] for layer in layering]


def normalize_ranks(g: Graph) -> None:
    low = min(g.node(v)["rank"] for v in g.nodes())
    for v in g.nodes():
        node = g.node(v)
        if "rank" in node:
            node["rank"] -= low


def remove_empty_ranks(g: Graph) -> None:
    offset = min(g.node(v)["rank"] for v in g.nodes())
    layers: Dict[int, List[str]] = {}
    for v in g.nodes():
        layers.setdefault(g.node(v)["rank"] - offset, []).append(v)
    delta = 0
    factor = g.graph()["nodeRankFactor"]
    for i in range(max(layers) + 1):
        vs = layers.get(i)
        if vs is None and i % factor != 0:
            delta -= 1
        elif delta and vs:
            for v in vs:
                g.node(v)["rank"] += delta


def intersect_rect(rect: dict, point: dict) -> dict:
    x, y = rect["x"], rect["y"]
    dx, dy = point["x"] - x, point["y"] - y
    w, h = rect["width"] / 2, rect["height"] / 2
    if not dx and not dy:
        raise DagreError("not possible to find intersection inside of the rectangle")
    if abs(dy) * w > abs(dx) * h:
        if dy < 0:
            h = -h
        sx, sy = h * dx / dy, h
    else:
        if dx < 0:
            w = -w
        sx, sy = w, w * dy / dx
    return {"x": x + sx, "y": y + sy}


# ---------------------------------------------------------------------------
# layout
# ---------------------------------------------------------------------------

GRAPH_DEFAULTS = {"ranksep": 50, "edgesep": 20, "nodesep": 50, "rankdir": "tb"}
GRAPH_NUM_ATTRS = ("nodesep", "edgesep", "ranksep", "marginx", "marginy")
GRAPH_ATTRS = ("acyclicer", "ranker", "rankdir", "align")
NODE_NUM_ATTRS = ("width", "height")
EDGE_NUM_ATTRS = ("minlen", "weight", "width", "height", "labeloffset")
EDGE_DEFAULTS = {"minlen": 1, "weight": 1, "width": 0, "height": 0, "labeloffset": 10, "labelpos": "r"}
EDGE_ATTRS = ("labelpos",)


def layout(g: Graph) -> None:
    """`dagre.layout(g)`: every node of `g` gets its center as `x` and `y`,
    every edge its `points`, the graph its `width` and `height`."""
    ids = _Ids()
    lg = _build_layout_graph(g)
    _run_layout(lg, ids)
    _update_input_graph(g, lg)


def _canonicalize(attrs: Optional[dict]) -> dict:
    return {str(k).lower(): v for k, v in (attrs or {}).items()}


def _select_number_attrs(obj: dict, attrs: Sequence[str]) -> dict:
    return {k: float(obj[k]) if not isinstance(obj[k], (int, float)) else obj[k] for k in attrs if k in obj}


def _build_layout_graph(input_graph: Graph) -> Graph:
    g = Graph(multigraph=True, compound=True)
    graph = _canonicalize(input_graph.graph())
    label = dict(GRAPH_DEFAULTS)
    label.update(_select_number_attrs(graph, GRAPH_NUM_ATTRS))
    label.update({k: graph[k] for k in GRAPH_ATTRS if k in graph})
    g.set_graph(label)
    for v in input_graph.nodes():
        node = _canonicalize(input_graph.node(v))
        attrs = {"width": 0, "height": 0}
        attrs.update(_select_number_attrs(node, NODE_NUM_ATTRS))
        g.set_node(v, attrs)
        g.set_parent(v, input_graph.parent(v) if input_graph.is_compound() else None)
    for e in input_graph.edges():
        edge = _canonicalize(input_graph.edge(e))
        attrs = dict(EDGE_DEFAULTS)
        attrs.update(_select_number_attrs(edge, EDGE_NUM_ATTRS))
        attrs.update({k: edge[k] for k in EDGE_ATTRS if k in edge})
        g.set_edge(e, attrs)
    return g


def _run_layout(g: Graph, ids: _Ids) -> None:
    _make_space_for_edge_labels(g)
    _remove_self_edges(g)
    _acyclic_run(g, ids)
    _nesting_run(g, ids)
    _rank(as_non_compound_graph(g))
    _inject_edge_label_proxies(g, ids)
    remove_empty_ranks(g)
    _nesting_cleanup(g)
    normalize_ranks(g)
    _assign_rank_min_max(g)
    _remove_edge_label_proxies(g)
    _normalize_run(g, ids)
    _parent_dummy_chains(g)
    _add_border_segments(g)
    _order(g, ids)
    _insert_self_edges(g)
    _coordinate_adjust(g)
    _position(g)
    _position_self_edges(g)
    _remove_border_nodes(g)
    _normalize_undo(g)
    _fixup_edge_label_coords(g)
    _coordinate_undo(g)
    _translate_graph(g)
    _assign_node_intersects(g)
    _reverse_points_for_reversed_edges(g)
    _acyclic_undo(g)


def _update_input_graph(input_graph: Graph, lg: Graph) -> None:
    for v in input_graph.nodes():
        label = input_graph.node(v)
        laid = lg.node(v)
        if label is not None:
            label["x"] = laid["x"]
            label["y"] = laid["y"]
            if lg.children(v):
                label["width"] = laid["width"]
                label["height"] = laid["height"]
    for e in input_graph.edges():
        label = input_graph.edge(e)
        laid = lg.edge(e)
        label["points"] = laid["points"]
        if "x" in laid:
            label["x"] = laid["x"]
            label["y"] = laid["y"]
    input_graph.graph()["width"] = lg.graph()["width"]
    input_graph.graph()["height"] = lg.graph()["height"]


def _make_space_for_edge_labels(g: Graph) -> None:
    graph = g.graph()
    graph["ranksep"] /= 2
    for e in g.edges():
        edge = g.edge(e)
        edge["minlen"] *= 2
        if str(edge["labelpos"]).lower() != "c":
            if graph["rankdir"] in ("TB", "BT"):
                edge["width"] += edge["labeloffset"]
            else:
                edge["height"] += edge["labeloffset"]


def _remove_self_edges(g: Graph) -> None:
    for e in g.edges():
        if e.v == e.w:
            raise DagreError("a self edge (%s) is outside what this port lays out" % e.v)


def _insert_self_edges(g: Graph) -> None:
    # No node carries `selfEdges`: `_remove_self_edges` refused them.
    layers = build_layer_matrix(g)
    for layer in layers:
        for i, v in enumerate(layer):
            g.node(v)["order"] = i


def _position_self_edges(g: Graph) -> None:
    pass


def _inject_edge_label_proxies(g: Graph, ids: _Ids) -> None:
    for e in g.edges():
        edge = g.edge(e)
        # The root's edges and a dummy chain's carry no size at all.
        if edge.get("width") and edge.get("height"):
            v, w = g.node(e.v), g.node(e.w)
            add_dummy_node(g, ids, "edge-proxy", {"rank": (w["rank"] - v["rank"]) / 2 + v["rank"], "e": e}, "_ep")


def _remove_edge_label_proxies(g: Graph) -> None:
    for v in g.nodes():
        node = g.node(v)
        if node.get("dummy") == "edge-proxy":
            g.edge(node["e"])["labelRank"] = node["rank"]
            g.remove_node(v)


def _assign_rank_min_max(g: Graph) -> None:
    top = 0
    for v in g.nodes():
        node = g.node(v)
        if node.get("borderTop"):
            node["minRank"] = g.node(node["borderTop"])["rank"]
            node["maxRank"] = g.node(node["borderBottom"])["rank"]
            top = max(top, node["maxRank"])
    g.graph()["maxRank"] = top


def _parent_dummy_chains(g: Graph) -> None:
    # With no compound node the path from a chain's tail to its head runs
    # through the invisible root alone, and every dummy is set as a child of
    # it, which is where it already is.
    pass


def _add_border_segments(g: Graph) -> None:
    for v in g.nodes():
        if g.children(v):
            raise DagreError("a compound node (%s) is outside what this port lays out" % v)


def _remove_border_nodes(g: Graph) -> None:
    pass


def _fixup_edge_label_coords(g: Graph) -> None:
    for e in g.edges():
        edge = g.edge(e)
        if "x" in edge:
            if edge["labelpos"] in ("l", "r"):
                edge["width"] -= edge["labeloffset"]
            if edge["labelpos"] == "l":
                edge["x"] -= edge["width"] / 2 + edge["labeloffset"]
            elif edge["labelpos"] == "r":
                edge["x"] += edge["width"] / 2 + edge["labeloffset"]


def _translate_graph(g: Graph) -> None:
    min_x = min_y = math.inf
    max_x = max_y = 0.0
    graph = g.graph()
    margin_x = graph.get("marginx") or 0
    margin_y = graph.get("marginy") or 0

    def extremes(attrs: dict) -> None:
        nonlocal min_x, max_x, min_y, max_y
        x, y, w, h = attrs["x"], attrs["y"], attrs["width"], attrs["height"]
        min_x = min(min_x, x - w / 2)
        max_x = max(max_x, x + w / 2)
        min_y = min(min_y, y - h / 2)
        max_y = max(max_y, y + h / 2)

    for v in g.nodes():
        extremes(g.node(v))
    for e in g.edges():
        edge = g.edge(e)
        if "x" in edge:
            extremes(edge)
    min_x -= margin_x
    min_y -= margin_y
    for v in g.nodes():
        node = g.node(v)
        node["x"] -= min_x
        node["y"] -= min_y
    for e in g.edges():
        edge = g.edge(e)
        for p in edge.get("points", []):
            p["x"] -= min_x
            p["y"] -= min_y
        if "x" in edge:
            edge["x"] -= min_x
        if "y" in edge:
            edge["y"] -= min_y
    graph["width"] = max_x - min_x + margin_x
    graph["height"] = max_y - min_y + margin_y


def _assign_node_intersects(g: Graph) -> None:
    for e in g.edges():
        edge = g.edge(e)
        node_v, node_w = g.node(e.v), g.node(e.w)
        if not edge.get("points"):
            edge["points"] = []
            p1, p2 = node_w, node_v
        else:
            p1, p2 = edge["points"][0], edge["points"][-1]
        edge["points"].insert(0, intersect_rect(node_v, p1))
        edge["points"].append(intersect_rect(node_w, p2))


def _reverse_points_for_reversed_edges(g: Graph) -> None:
    for e in g.edges():
        edge = g.edge(e)
        if edge.get("reversed"):
            edge["points"].reverse()


# ---------------------------------------------------------------------------
# acyclic
# ---------------------------------------------------------------------------

def _acyclic_run(g: Graph, ids: _Ids) -> None:
    if g.graph().get("acyclicer") == "greedy":
        raise DagreError("the greedy acyclicer is outside what this port lays out")
    for e in _dfs_fas(g):
        label = g.edge(e)
        g.remove_edge(e)
        label["forwardName"] = e.name
        label["reversed"] = True
        g.set_edge(e.w, e.v, label, ids("rev"))


def _dfs_fas(g: Graph) -> List[EdgeObj]:
    fas: List[EdgeObj] = []
    stack: Dict[str, bool] = {}
    visited: Dict[str, bool] = {}

    def dfs(v: str) -> None:
        if v in visited:
            return
        visited[v] = True
        stack[v] = True
        for e in g.out_edges(v):
            if e.w in stack:
                fas.append(e)
            else:
                dfs(e.w)
        del stack[v]

    for v in g.nodes():
        dfs(v)
    return fas


def _acyclic_undo(g: Graph) -> None:
    for e in g.edges():
        label = g.edge(e)
        if label.get("reversed"):
            g.remove_edge(e)
            forward = label.pop("forwardName")
            del label["reversed"]
            g.set_edge(e.w, e.v, label, forward)


# ---------------------------------------------------------------------------
# nesting graph
# ---------------------------------------------------------------------------

def _nesting_run(g: Graph, ids: _Ids) -> None:
    """Flat graphs only: the root dummy every node hangs from with a
    weightless edge, which is what keeps the ranking connected."""
    root = add_dummy_node(g, ids, "root", {}, "_root")
    depths = {v: 1 for v in g.children()}
    height = max(depths.values()) - 1
    node_sep = 2 * height + 1
    g.graph()["nestingRoot"] = root
    for e in g.edges():
        g.edge(e)["minlen"] *= node_sep
    for child in g.children():
        if g.children(child):
            raise DagreError("a compound node (%s) is outside what this port lays out" % child)
        if child != root:
            g.set_edge(root, child, {"weight": 0, "minlen": node_sep})
    g.graph()["nodeRankFactor"] = node_sep


def _nesting_cleanup(g: Graph) -> None:
    graph = g.graph()
    g.remove_node(graph["nestingRoot"])
    del graph["nestingRoot"]
    for e in g.edges():
        if g.edge(e).get("nestingEdge"):
            g.remove_edge(e)


# ---------------------------------------------------------------------------
# rank
# ---------------------------------------------------------------------------

def _slack(g: Graph, e: EdgeObj) -> float:
    return g.node(e.w)["rank"] - g.node(e.v)["rank"] - g.edge(e)["minlen"]


def _longest_path(g: Graph) -> None:
    visited: Dict[str, bool] = {}

    def dfs(v: str):
        label = g.node(v)
        if v in visited:
            return label["rank"]
        visited[v] = True
        ranks = [dfs(e.w) - g.edge(e)["minlen"] for e in g.out_edges(v)]
        rank = min(ranks) if ranks else 0
        label["rank"] = rank
        return rank

    for v in g.sources():
        dfs(v)


def _rank(g: Graph) -> None:
    ranker = g.graph().get("ranker")
    if ranker == "longest-path":
        _longest_path(g)
    elif ranker == "tight-tree":
        _longest_path(g)
        _feasible_tree(g)
    else:
        _network_simplex(g)


def _feasible_tree(g: Graph) -> Graph:
    t = Graph(directed=False)
    start = g.nodes()[0]
    size = g.node_count()
    t.set_node(start, {})
    while _tight_tree(t, g) < size:
        edge = _find_min_slack_edge(t, g)
        delta = _slack(g, edge) if t.has_node(edge.v) else -_slack(g, edge)
        for v in t.nodes():
            g.node(v)["rank"] += delta
    return t


def _tight_tree(t: Graph, g: Graph) -> int:
    def dfs(v: str) -> None:
        for e in g.node_edges(v):
            w = e.w if v == e.v else e.v
            if not t.has_node(w) and not _slack(g, e):
                t.set_node(w, {})
                t.set_edge(v, w, {})
                dfs(w)

    for v in t.nodes():
        dfs(v)
    return t.node_count()


def _find_min_slack_edge(t: Graph, g: Graph) -> EdgeObj:
    return _min_by(g.edges(), lambda e: _slack(g, e) if t.has_node(e.v) != t.has_node(e.w) else None)


def _network_simplex(g: Graph) -> None:
    g = simplify(g)
    _longest_path(g)
    t = _feasible_tree(g)
    _init_low_lim_values(t)
    _init_cut_values(t, g)
    while True:
        e = _leave_edge(t)
        if e is None:
            break
        f = _enter_edge(t, g, e)
        _exchange_edges(t, g, e, f)


def _init_cut_values(t: Graph, g: Graph) -> None:
    vs = _postorder(t, t.nodes())
    for v in vs[:-1]:
        parent = t.node(v)["parent"]
        t.edge(v, parent)["cutvalue"] = _calc_cut_value(t, g, v)


def _calc_cut_value(t: Graph, g: Graph, child: str) -> float:
    parent = t.node(child)["parent"]
    child_is_tail = True
    graph_edge = g.edge(child, parent)
    if graph_edge is None:
        child_is_tail = False
        graph_edge = g.edge(parent, child)
    cut = graph_edge["weight"]
    for e in g.node_edges(child):
        is_out = e.v == child
        other = e.w if is_out else e.v
        if other != parent:
            points_to_head = is_out == child_is_tail
            other_weight = g.edge(e)["weight"]
            cut += other_weight if points_to_head else -other_weight
            if t.has_edge(child, other):
                other_cut = t.edge(child, other)["cutvalue"]
                cut += -other_cut if points_to_head else other_cut
    return cut


def _init_low_lim_values(t: Graph, root: Optional[str] = None) -> None:
    if root is None:
        root = t.nodes()[0]
    _dfs_assign_low_lim(t, {}, 1, root, None)


def _dfs_assign_low_lim(t: Graph, visited: Dict[str, bool], next_lim: int, v: str, parent: Optional[str]) -> int:
    low = next_lim
    label = t.node(v)
    visited[v] = True
    for w in t.neighbors(v):
        if w not in visited:
            next_lim = _dfs_assign_low_lim(t, visited, next_lim, w, v)
    label["low"] = low
    label["lim"] = next_lim
    next_lim += 1
    if parent is not None:
        label["parent"] = parent
    else:
        label.pop("parent", None)
    return next_lim


def _leave_edge(t: Graph) -> Optional[EdgeObj]:
    for e in t.edges():
        if t.edge(e).get("cutvalue", 0) < 0:
            return e
    return None


def _enter_edge(t: Graph, g: Graph, edge: EdgeObj) -> EdgeObj:
    v, w = edge.v, edge.w
    if not g.has_edge(v, w):
        v, w = edge.w, edge.v
    v_label, w_label = t.node(v), t.node(w)
    tail = v_label
    flip = False
    if v_label["lim"] > w_label["lim"]:
        tail = w_label
        flip = True
    candidates = [e for e in g.edges()
                  if flip == _is_descendant(t.node(e.v), tail) and flip != _is_descendant(t.node(e.w), tail)]
    return _min_by(candidates, lambda e: _slack(g, e))


def _exchange_edges(t: Graph, g: Graph, e: EdgeObj, f: EdgeObj) -> None:
    t.remove_edge(e.v, e.w)
    t.set_edge(f.v, f.w, {})
    _init_low_lim_values(t)
    _init_cut_values(t, g)
    _update_ranks(t, g)


def _update_ranks(t: Graph, g: Graph) -> None:
    root = next(v for v in t.nodes() if not g.node(v).get("parent"))
    for v in _preorder(t, root)[1:]:
        parent = t.node(v)["parent"]
        edge = g.edge(v, parent)
        flipped = False
        if edge is None:
            edge = g.edge(parent, v)
            flipped = True
        g.node(v)["rank"] = g.node(parent)["rank"] + (edge["minlen"] if flipped else -edge["minlen"])


def _is_descendant(v_label: dict, root_label: dict) -> bool:
    return root_label["low"] <= v_label["lim"] <= root_label["lim"]


def _dfs_order(g: Graph, vs: Sequence[str], post: bool) -> List[str]:
    """graphlib's `alg.preorder` / `alg.postorder`."""
    navigate = g.successors if g.is_directed() else g.neighbors
    acc: List[str] = []
    visited: Dict[str, bool] = {}

    def walk(v: str) -> None:
        if v in visited:
            return
        visited[v] = True
        if not post:
            acc.append(v)
        for w in navigate(v):
            walk(w)
        if post:
            acc.append(v)

    for v in vs:
        walk(v)
    return acc


def _preorder(g: Graph, root: str) -> List[str]:
    return _dfs_order(g, [root], False)


def _postorder(g: Graph, vs: Sequence[str]) -> List[str]:
    return _dfs_order(g, vs, True)


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------

def _normalize_run(g: Graph, ids: _Ids) -> None:
    g.graph()["dummyChains"] = []
    for e in g.edges():
        _normalize_edge(g, e, ids)


def _normalize_edge(g: Graph, e: EdgeObj, ids: _Ids) -> None:
    v = e.v
    v_rank = g.node(v)["rank"]
    w = e.w
    w_rank = g.node(w)["rank"]
    name = e.name
    label = g.edge(e)
    label_rank = label.get("labelRank")
    if w_rank == v_rank + 1:
        return
    g.remove_edge(e)
    i = 0
    v_rank += 1
    while v_rank < w_rank:
        label["points"] = []
        attrs = {"width": 0, "height": 0, "edgeLabel": label, "edgeObj": e, "rank": v_rank}
        dummy = add_dummy_node(g, ids, "edge", attrs, "_d")
        if v_rank == label_rank:
            attrs["width"] = label["width"]
            attrs["height"] = label["height"]
            attrs["dummy"] = "edge-label"
            attrs["labelpos"] = label["labelpos"]
        g.set_edge(v, dummy, {"weight": label["weight"]}, name)
        if i == 0:
            g.graph()["dummyChains"].append(dummy)
        v = dummy
        i += 1
        v_rank += 1
    g.set_edge(v, w, {"weight": label["weight"]}, name)


def _normalize_undo(g: Graph) -> None:
    for v in g.graph()["dummyChains"]:
        node = g.node(v)
        label = node["edgeLabel"]
        g.set_edge(node["edgeObj"], label)
        while node.get("dummy"):
            w = g.successors(v)[0]
            g.remove_node(v)
            label["points"].append({"x": node["x"], "y": node["y"]})
            if node["dummy"] == "edge-label":
                label["x"], label["y"] = node["x"], node["y"]
                label["width"], label["height"] = node["width"], node["height"]
            v = w
            node = g.node(v)


# ---------------------------------------------------------------------------
# order
# ---------------------------------------------------------------------------

def _order(g: Graph, ids: _Ids) -> None:
    top = max_rank(g)
    down = [_build_layer_graph(g, rank, "inEdges", ids) for rank in range(1, top + 1)]
    up = [_build_layer_graph(g, rank, "outEdges", ids) for rank in range(top - 1, -1, -1)]
    layering = _init_order(g)
    _assign_order(g, layering)
    best_cc = math.inf
    best: List[List[str]] = layering
    i = 0
    last_best = 0
    while last_best < 4:
        _sweep_layer_graphs(down if i % 2 else up, i % 4 >= 2)
        layering = build_layer_matrix(g)
        cc = _cross_count(g, layering)
        if cc < best_cc:
            last_best = 0
            best = [list(layer) for layer in layering]
            best_cc = cc
        i += 1
        last_best += 1
    _assign_order(g, best)


def _build_layer_graph(g: Graph, rank: int, relationship: str, ids: _Ids) -> Graph:
    while True:
        root = ids("_root")
        if not g.has_node(root):
            break
    result = Graph(compound=True).set_graph({"root": root}).set_default_node_label(lambda v: g.node(v))
    for v in g.nodes():
        node = g.node(v)
        parent = g.parent(v)
        if node.get("rank") == rank or ("minRank" in node and node["minRank"] <= rank <= node["maxRank"]):
            result.set_node(v)
            result.set_parent(v, parent or root)
            incident = g.in_edges(v) if relationship == "inEdges" else g.out_edges(v)
            for e in incident:
                u = e.w if e.v == v else e.v
                edge = result.edge(u, v)
                weight = edge["weight"] if edge is not None else 0
                result.set_edge(u, v, {"weight": g.edge(e)["weight"] + weight})
            if "minRank" in node:
                result.set_node(v, {"borderLeft": node["borderLeft"][rank], "borderRight": node["borderRight"][rank]})
    return result


def _init_order(g: Graph) -> List[List[str]]:
    visited: Dict[str, bool] = {}
    simple = [v for v in g.nodes() if not g.children(v)]
    top = max(g.node(v)["rank"] for v in simple)
    layers: List[List[str]] = [[] for _ in range(top + 1)]

    def dfs(v: str) -> None:
        if v in visited:
            return
        visited[v] = True
        layers[g.node(v)["rank"]].append(v)
        for w in g.successors(v):
            dfs(w)

    for v in sorted(simple, key=lambda v: g.node(v)["rank"]):
        dfs(v)
    return layers


def _assign_order(g: Graph, layering: Sequence[Sequence[str]]) -> None:
    for layer in layering:
        for i, v in enumerate(layer):
            g.node(v)["order"] = i


def _sweep_layer_graphs(layer_graphs: Sequence[Graph], bias_right: bool) -> None:
    cg = Graph()
    for lg in layer_graphs:
        root = lg.graph()["root"]
        result = _sort_subgraph(lg, root, cg, bias_right)
        for i, v in enumerate(result["vs"]):
            lg.node(v)["order"] = i
        _add_subgraph_constraints(lg, cg, result["vs"])


def _add_subgraph_constraints(g: Graph, cg: Graph, vs: Sequence[str]) -> None:
    prev: Dict[str, str] = {}
    root_prev: Optional[str] = None
    for v in vs:
        child = g.parent(v)
        while child is not None:
            parent = g.parent(child)
            if parent is not None:
                prev_child = prev.get(parent)
                prev[parent] = child
            else:
                prev_child = root_prev
                root_prev = child
            if prev_child is not None and prev_child != child:
                cg.set_edge(prev_child, child)
                break
            child = parent


def _sort_subgraph(g: Graph, v: str, cg: Graph, bias_right: bool) -> dict:
    movable = g.children(v)
    node = g.node(v)
    bl = node.get("borderLeft") if node else None
    br = node.get("borderRight") if node else None
    subgraphs: Dict[str, dict] = {}
    if bl:
        movable = [w for w in movable if w != bl and w != br]
    barycenters = _barycenter(g, movable)
    for entry in barycenters:
        if g.children(entry["v"]):
            sub = _sort_subgraph(g, entry["v"], cg, bias_right)
            subgraphs[entry["v"]] = sub
            if "barycenter" in sub:
                _merge_barycenters(entry, sub)
    entries = _resolve_conflicts(barycenters, cg)
    for entry in entries:
        flat: List[str] = []
        for w in entry["vs"]:
            flat.extend(subgraphs[w]["vs"] if w in subgraphs else [w])
        entry["vs"] = flat
    result = _sort(entries, bias_right)
    if bl:
        result["vs"] = [bl] + result["vs"] + [br]
        if g.predecessors(bl):
            bl_pred = g.node(g.predecessors(bl)[0])
            br_pred = g.node(g.predecessors(br)[0])
            if "barycenter" not in result:
                result["barycenter"] = 0
                result["weight"] = 0
            result["barycenter"] = ((result["barycenter"] * result["weight"] + bl_pred["order"] + br_pred["order"])
                                    / (result["weight"] + 2))
            result["weight"] += 2
    return result


def _merge_barycenters(target: dict, other: dict) -> None:
    if "barycenter" in target:
        target["barycenter"] = ((target["barycenter"] * target["weight"] + other["barycenter"] * other["weight"])
                                / (target["weight"] + other["weight"]))
        target["weight"] += other["weight"]
    else:
        target["barycenter"] = other["barycenter"]
        target["weight"] = other["weight"]


def _barycenter(g: Graph, movable: Sequence[str]) -> List[dict]:
    out = []
    for v in movable:
        in_v = g.in_edges(v)
        if not in_v:
            out.append({"v": v})
        else:
            total = weight = 0
            for e in in_v:
                edge = g.edge(e)
                total += edge["weight"] * g.node(e.v)["order"]
                weight += edge["weight"]
            out.append({"v": v, "barycenter": total / weight, "weight": weight})
    return out


def _resolve_conflicts(entries: Sequence[dict], cg: Graph) -> List[dict]:
    mapped: Dict[str, dict] = {}
    for i, entry in enumerate(entries):
        tmp = mapped[entry["v"]] = {"indegree": 0, "in": [], "out": [], "vs": [entry["v"]], "i": i}
        if "barycenter" in entry:
            tmp["barycenter"] = entry["barycenter"]
            tmp["weight"] = entry["weight"]
    for e in cg.edges():
        entry_v = mapped.get(e.v)
        entry_w = mapped.get(e.w)
        if entry_v is not None and entry_w is not None:
            entry_w["indegree"] += 1
            entry_v["out"].append(entry_w)
    source_set = [entry for entry in mapped.values() if not entry["indegree"]]
    return _do_resolve_conflicts(source_set)


def _do_resolve_conflicts(source_set: List[dict]) -> List[dict]:
    entries: List[dict] = []
    while source_set:
        entry = source_set.pop()
        entries.append(entry)
        entry["in"].reverse()
        for u_entry in entry["in"]:
            if u_entry.get("merged"):
                continue
            if ("barycenter" not in u_entry or "barycenter" not in entry
                    or u_entry["barycenter"] >= entry["barycenter"]):
                _merge_entries(entry, u_entry)
        for w_entry in entry["out"]:
            w_entry["in"].append(entry)
            w_entry["indegree"] -= 1
            if w_entry["indegree"] == 0:
                source_set.append(w_entry)
    out = []
    for entry in entries:
        if entry.get("merged"):
            continue
        picked = {"vs": entry["vs"], "i": entry["i"]}
        if "barycenter" in entry:
            picked["barycenter"] = entry["barycenter"]
            picked["weight"] = entry["weight"]
        out.append(picked)
    return out


def _merge_entries(target: dict, source: dict) -> None:
    total = weight = 0
    if target.get("weight"):
        total += target["barycenter"] * target["weight"]
        weight += target["weight"]
    if source.get("weight"):
        total += source["barycenter"] * source["weight"]
        weight += source["weight"]
    target["vs"] = source["vs"] + target["vs"]
    target["barycenter"] = total / weight if weight else math.nan
    target["weight"] = weight
    target["i"] = min(source["i"], target["i"])
    source["merged"] = True


def _sort(entries: Sequence[dict], bias_right: bool) -> dict:
    sortable = [e for e in entries if "barycenter" in e]
    unsortable = sorted((e for e in entries if "barycenter" not in e), key=lambda e: -e["i"])
    sortable.sort(key=lambda e: (e["barycenter"], -e["i"] if bias_right else e["i"]))
    vs: List[List[str]] = []
    total = weight = 0
    index = 0

    def consume(index: int) -> int:
        while unsortable and unsortable[-1]["i"] <= index:
            last = unsortable.pop()
            vs.append(last["vs"])
            index += 1
        return index

    index = consume(index)
    for entry in sortable:
        index += len(entry["vs"])
        vs.append(entry["vs"])
        total += entry["barycenter"] * entry["weight"]
        weight += entry["weight"]
        index = consume(index)
    result: dict = {"vs": [v for part in vs for v in part]}
    if weight:
        result["barycenter"] = total / weight
        result["weight"] = weight
    return result


def _cross_count(g: Graph, layering: Sequence[Sequence[str]]) -> float:
    cc = 0
    for north, south in zip(layering, layering[1:]):
        cc += _two_layer_cross_count(g, north, south)
    return cc


def _two_layer_cross_count(g: Graph, north: Sequence[str], south: Sequence[str]) -> float:
    """Barth et al.'s weighted count: each edge, taken in north order and
    then by its south position, crosses every earlier edge that lands
    further along the south layer."""
    south_pos = {v: i for i, v in enumerate(south)}
    entries: List[Tuple[int, float]] = []
    for v in north:
        entries.extend(sorted(((south_pos[e.w], g.edge(e)["weight"]) for e in g.out_edges(v)), key=lambda t: t[0]))
    cc = 0
    for i, (pos, weight) in enumerate(entries):
        right = sum(w for p, w in entries[:i] if p > pos)
        cc += weight * right
    return cc


# ---------------------------------------------------------------------------
# coordinate system
# ---------------------------------------------------------------------------

def _coordinate_adjust(g: Graph) -> None:
    rankdir = str(g.graph()["rankdir"]).lower()
    if rankdir in ("lr", "rl"):
        _swap_width_height(g)


def _coordinate_undo(g: Graph) -> None:
    rankdir = str(g.graph()["rankdir"]).lower()
    if rankdir in ("bt", "rl"):
        for v in g.nodes():
            g.node(v)["y"] = -g.node(v)["y"]
        for e in g.edges():
            edge = g.edge(e)
            for p in edge.get("points", []):
                p["y"] = -p["y"]
            if "y" in edge:
                edge["y"] = -edge["y"]
    if rankdir in ("lr", "rl"):
        for v in g.nodes():
            node = g.node(v)
            node["x"], node["y"] = node["y"], node["x"]
        for e in g.edges():
            edge = g.edge(e)
            for p in edge.get("points", []):
                p["x"], p["y"] = p["y"], p["x"]
            if "x" in edge:
                edge["x"], edge["y"] = edge["y"], edge["x"]
        _swap_width_height(g)


def _swap_width_height(g: Graph) -> None:
    for v in g.nodes():
        node = g.node(v)
        node["width"], node["height"] = node["height"], node["width"]
    for e in g.edges():
        edge = g.edge(e)
        if "width" in edge or "height" in edge:
            edge["width"], edge["height"] = edge.get("height"), edge.get("width")


# ---------------------------------------------------------------------------
# position
# ---------------------------------------------------------------------------

def _position(g: Graph) -> None:
    g = as_non_compound_graph(g)
    _position_y(g)
    for v, x in _position_x(g).items():
        g.node(v)["x"] = x


def _position_y(g: Graph) -> None:
    layering = build_layer_matrix(g)
    rank_sep = g.graph()["ranksep"]
    prev_y = 0
    for layer in layering:
        if not layer:
            # dagre would carry NaN from here on; the app never shows one,
            # so an empty rank is a port bug and says so.
            raise DagreError("an empty rank between occupied ones")
        max_height = max(g.node(v)["height"] for v in layer)
        for v in layer:
            g.node(v)["y"] = prev_y + max_height / 2
        prev_y += max_height + rank_sep


def _position_x(g: Graph) -> Dict[str, float]:
    layering = build_layer_matrix(g)
    conflicts = _find_type1_conflicts(g, layering)
    for v, ws in _find_type2_conflicts(g, layering).items():
        conflicts.setdefault(v, {}).update(ws)
    xss: Dict[str, Dict[str, float]] = {}
    for vert in ("u", "d"):
        adjusted = layering if vert == "u" else list(reversed(layering))
        for horiz in ("l", "r"):
            if horiz == "r":
                adjusted = [list(reversed(inner)) for inner in adjusted]
            neighbor_fn = g.predecessors if vert == "u" else g.successors
            root, align = _vertical_alignment(g, adjusted, conflicts, neighbor_fn)
            xs = _horizontal_compaction(g, adjusted, root, align, horiz == "r")
            if horiz == "r":
                xs = {v: -x for v, x in xs.items()}
            xss[vert + horiz] = xs
    smallest = _find_smallest_width_alignment(g, xss)
    _align_coordinates(xss, smallest)
    return _balance(xss, g.graph().get("align"))


def _find_type1_conflicts(g: Graph, layering: Sequence[Sequence[str]]) -> Dict[str, Dict[str, bool]]:
    conflicts: Dict[str, Dict[str, bool]] = {}
    for prev_layer, layer in zip(layering, layering[1:]):
        k0 = 0
        scan_pos = 0
        prev_len = len(prev_layer)
        last = layer[-1] if layer else None
        for i, v in enumerate(layer):
            w = _find_other_inner_segment_node(g, v)
            k1 = g.node(w)["order"] if w else prev_len
            if w or v == last:
                for scan_node in layer[scan_pos:i + 1]:
                    for u in g.predecessors(scan_node):
                        u_label = g.node(u)
                        u_pos = u_label["order"]
                        if (u_pos < k0 or k1 < u_pos) and not (u_label.get("dummy") and g.node(scan_node).get("dummy")):
                            _add_conflict(conflicts, u, scan_node)
                scan_pos = i + 1
                k0 = k1
    return conflicts


def _find_type2_conflicts(g: Graph, layering: Sequence[Sequence[str]]) -> Dict[str, Dict[str, bool]]:
    # A type-2 conflict needs a border dummy, which only a compound node
    # makes; with none, dagre's scan compares every order against an
    # undefined bound and marks nothing.
    return {}


def _find_other_inner_segment_node(g: Graph, v: str) -> Optional[str]:
    if g.node(v).get("dummy"):
        for u in g.predecessors(v):
            if g.node(u).get("dummy"):
                return u
    return None


def _add_conflict(conflicts: Dict[str, Dict[str, bool]], v: str, w: str) -> None:
    if v > w:
        v, w = w, v
    conflicts.setdefault(v, {})[w] = True


def _has_conflict(conflicts: Dict[str, Dict[str, bool]], v: str, w: str) -> bool:
    if v > w:
        v, w = w, v
    return w in conflicts.get(v, {})


def _vertical_alignment(g: Graph, layering: Sequence[Sequence[str]], conflicts: Dict[str, Dict[str, bool]],
                        neighbor_fn: Callable[[str], List[str]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    root: Dict[str, str] = {}
    align: Dict[str, str] = {}
    pos: Dict[str, int] = {}
    for layer in layering:
        for order, v in enumerate(layer):
            root[v] = v
            align[v] = v
            pos[v] = order
    for layer in layering:
        prev_idx = -1
        for v in layer:
            ws = neighbor_fn(v)
            if ws:
                ws = sorted(ws, key=lambda w: pos[w])
                mp = (len(ws) - 1) / 2
                for i in range(int(math.floor(mp)), int(math.ceil(mp)) + 1):
                    w = ws[i]
                    if align[v] == v and prev_idx < pos[w] and not _has_conflict(conflicts, v, w):
                        align[w] = v
                        align[v] = root[v] = root[w]
                        prev_idx = pos[w]
    return root, align


def _horizontal_compaction(g: Graph, layering: Sequence[Sequence[str]], root: Dict[str, str],
                           align: Dict[str, str], reverse_sep: bool) -> Dict[str, float]:
    xs: Dict[str, float] = {}
    block_g = _build_block_graph(g, layering, root, reverse_sep)
    border_type = "borderLeft" if reverse_sep else "borderRight"

    def iterate(set_xs: Callable[[str], None], next_nodes: Callable[[str], List[str]]) -> None:
        stack = block_g.nodes()
        visited: Dict[str, bool] = {}
        while stack:
            elem = stack.pop()
            if elem in visited:
                set_xs(elem)
            else:
                visited[elem] = True
                stack.append(elem)
                stack.extend(next_nodes(elem))

    def pass1(elem: str) -> None:
        acc = 0
        for e in block_g.in_edges(elem):
            acc = max(acc, xs[e.v] + block_g.edge(e))
        xs[elem] = acc

    def pass2(elem: str) -> None:
        low = math.inf
        for e in block_g.out_edges(elem):
            low = min(low, xs[e.w] - block_g.edge(e))
        node = g.node(elem)
        if low != math.inf and node.get("borderType") != border_type:
            xs[elem] = max(xs[elem], low)

    iterate(pass1, block_g.predecessors)
    iterate(pass2, block_g.successors)
    for v in align:
        xs[v] = xs[root[v]]
    return xs


def _build_block_graph(g: Graph, layering: Sequence[Sequence[str]], root: Dict[str, str],
                       reverse_sep: bool) -> Graph:
    block = Graph()
    label = g.graph()
    sep_fn = _sep(label["nodesep"], label["edgesep"], reverse_sep)
    for layer in layering:
        u: Optional[str] = None
        for v in layer:
            v_root = root[v]
            block.set_node(v_root)
            if u is not None:
                u_root = root[u]
                prev_max = block.edge(u_root, v_root)
                block.set_edge(u_root, v_root, max(sep_fn(g, v, u), prev_max or 0))
            u = v
    return block


def _sep(node_sep: float, edge_sep: float, reverse_sep: bool) -> Callable[[Graph, str, str], float]:
    def fn(g: Graph, v: str, w: str) -> float:
        v_label, w_label = g.node(v), g.node(w)
        total = 0.0
        delta = 0.0
        total += v_label["width"] / 2
        if "labelpos" in v_label:
            pos = str(v_label["labelpos"]).lower()
            if pos == "l":
                delta = -v_label["width"] / 2
            elif pos == "r":
                delta = v_label["width"] / 2
        if delta:
            total += delta if reverse_sep else -delta
        delta = 0.0
        total += (edge_sep if v_label.get("dummy") else node_sep) / 2
        total += (edge_sep if w_label.get("dummy") else node_sep) / 2
        total += w_label["width"] / 2
        if "labelpos" in w_label:
            pos = str(w_label["labelpos"]).lower()
            if pos == "l":
                delta = w_label["width"] / 2
            elif pos == "r":
                delta = -w_label["width"] / 2
        if delta:
            total += delta if reverse_sep else -delta
        return total

    return fn


def _find_smallest_width_alignment(g: Graph, xss: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    def width_of(xs: Dict[str, float]) -> float:
        high, low = -math.inf, math.inf
        for v, x in xs.items():
            half = g.node(v)["width"] / 2
            high = max(x + half, high)
            low = min(x - half, low)
        return high - low

    return _min_by(xss.values(), width_of)


def _align_coordinates(xss: Dict[str, Dict[str, float]], align_to: Dict[str, float]) -> None:
    to_min, to_max = min(align_to.values()), max(align_to.values())
    for vert in ("u", "d"):
        for horiz in ("l", "r"):
            name = vert + horiz
            xs = xss[name]
            if xs is align_to:
                continue
            values = list(xs.values())
            delta = to_min - min(values) if horiz == "l" else to_max - max(values)
            if delta:
                xss[name] = {v: x + delta for v, x in xs.items()}


def _balance(xss: Dict[str, Dict[str, float]], align: Optional[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for v in xss["ul"]:
        if align:
            out[v] = xss[align.lower()][v]
        else:
            xs = sorted(xss[name][v] for name in xss)
            out[v] = (xs[1] + xs[2]) / 2
    return out
