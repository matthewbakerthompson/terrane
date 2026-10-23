"""The organic layout: Cytoscape's cose, run in the browser on the machine
and seeded from dagre as the app seeds it, for the flat graph past what
ELK takes that dagre ranks into a ribbon.

The app's `unribbon()`: when a layered drawing with no boundaries, too
large for ELK, comes out of dagre wider or taller than six to one, it
runs cose from where dagre left things (`randomize: false`), with the
app's repulsion, edge length and iteration count, and keeps bezier edges,
since right angles on a force layout lie about the geometry. The engine
does the same through the browser it already drives for ELK: the vendored
`cytoscape.min.js` evaluated in the page, a headless instance built with
every leaf at its dagre center and the app's size for it, the layout run,
the centers read back. Cose has no randomness once the seeds are given
(it draws a random direction only for two nodes at exactly one point), so
the picture is the same every time; and since Cytoscape itself runs, its
own habits run too, the one that reads a node's width as its height
included, which a port would have had to copy.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .layered import LayeredLayout
from .packed import Layout, Prepared, sheet_ratio

#: `unribbon()`'s options, in the order the app gives them.
COSE_OPTIONS = {
    "name": "cose", "animate": False, "randomize": False, "padding": 26,
    "nodeRepulsion": 12000, "idealEdgeLength": 90, "numIter": 600,
    "nodeDimensionsIncludeLabels": True,
}

#: Builds the instance, runs the layout and hands back every node's
#: center. The style gives each node the shape, size and border the app's
#: stylesheet gives it and no label, since the app's labels sit inside the
#: node.
COSE_SCRIPT = """
(function (graph) {
  // A real canvas of the app's sheet size, since cose tiles the components
  // of a graph by the canvas's aspect; and `preset`, to keep the positions
  // given: left to its default, Cytoscape runs a grid layout on the new
  // instance, which put every node on one point, where cose draws random
  // directions.
  var host = document.createElement("div");
  host.style.cssText = "position:absolute;left:0;top:0;width:" + graph.width + "px;height:" + graph.height + "px;";
  document.body.appendChild(host);
  var cy = window.cytoscape({
    container: host, styleEnabled: true, elements: graph.elements, layout: { name: "preset" },
    style: [{ selector: "node", style: { "width": "data(w)", "height": "data(h)", "border-width": "data(border)",
                                          "shape": "data(shape)", "label": "" } }]
  });
  cy.layout(graph.options).run();
  var out = {};
  cy.nodes().forEach(function (n) { var p = n.position(); out[n.id()] = [p.x, p.y]; });
  cy.destroy();
  host.remove();
  return JSON.stringify(out);
})(%s)
"""


def cose_graph(prep: Prepared, lay: LayeredLayout, sheet_width: float = 1240,
               sheet_height: float = 871.4375) -> dict:
    """What the page's Cytoscape is given: every leaf at its dagre center
    with the app's size and border for it, every edge between leaves, the
    app's options, and the sheet's size for the canvas."""
    elements: List[dict] = []
    for leaf in prep.leaves:
        x, y, w, h = lay.leaves[leaf.id]
        # What cose measures a node by is its bounding box, border and
        # miters included, and to the last bit: a plain rectangle of the
        # same box, computed another way, differed from the app's in the
        # fourteenth place, and six hundred iterations of a force layout
        # turned that into hundreds of pixels. So the node is given the
        # app's shape, size and border and Cytoscape measures it itself.
        elements.append({"data": {"id": leaf.id, "shape": leaf.shape, "w": w, "h": h,
                                  "border": float(leaf.data.get("strokeWidth") or 1)},
                         "position": {"x": x, "y": y}})
    present = {leaf.id for leaf in prep.leaves}
    for edge in prep.edges:
        if edge["source"] in present and edge["target"] in present:
            elements.append({"data": {"id": edge["id"], "source": edge["source"], "target": edge["target"]}})
    return {"elements": elements, "options": dict(COSE_OPTIONS), "width": sheet_width, "height": sheet_height}


def layout_organic(prep: Prepared, lay: LayeredLayout, runner, sheet_width: float = 1240,
                   sheet_height: float = 871.4375) -> Layout:
    """Where the app puts every leaf of a ribbon it lays out organically:
    the dagre layout `lay` as the seed, cose through `runner.cose`."""
    centers: Dict[str, Tuple[float, float]] = runner.cose(cose_graph(prep, lay, sheet_width, sheet_height))
    leaves: Dict[str, Tuple[float, float, int, int]] = {}
    for leaf in prep.leaves:
        _, _, w, h = lay.leaves[leaf.id]
        x, y = centers[leaf.id]
        leaves[leaf.id] = (float(x), float(y), w, h)
    return Layout(leaves, {}, sheet_ratio(sheet_width, sheet_height))
