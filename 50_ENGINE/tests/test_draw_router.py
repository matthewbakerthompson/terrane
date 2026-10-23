"""The grid router: every line around everything, squarely, the same twice.

The layered fixtures hold the node placement equal to the app; the router
draws the lines between those nodes, and what a line must get right can be
checked without eyes. Every route is orthogonal, every run of it stays out
of every node it does not join, every line leaves and arrives at a port a
margin out from a side of its node; every edge between two nodes gets a
route; and the same payload routes to the same bytes twice. The app's own
three-piece router stays available as `routing="pieces"`, and the layered
fixtures go on holding it to the app.
"""

from __future__ import annotations

import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.draw import default_metrics, prepare, render_svg  # noqa: E402
from terrane.draw.layered import layout_layered, leaf_box  # noqa: E402
from terrane.draw.router import MARGIN, route_grid  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "layered"


def _layered_fixtures():
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(FIXTURES.glob("*.json"))]


def _routed(fixture):
    payload = fixture["payload"]
    prep = prepare(payload)
    lay = layout_layered(payload, fixture["container"]["w"], fixture["container"]["h"], prep, default_metrics())
    return prep, lay, route_grid(prep, lay, lay.direction == "TB")


def _run_crosses(a, b, box, slack=0.0):
    """Whether the straight run from a to b passes through the box's inside,
    the box grown by `slack` (shrunk when negative)."""
    x1, y1, x2, y2 = box[0] - slack, box[1] - slack, box[2] + slack, box[3] + slack
    if abs(a[0] - b[0]) < 0.01:
        return x1 < a[0] < x2 and min(a[1], b[1]) < y2 and max(a[1], b[1]) > y1
    return y1 < a[1] < y2 and min(a[0], b[0]) < x2 and max(a[0], b[0]) > x1


class TestGridRouter(unittest.TestCase):
    def test_there_are_layered_fixtures(self) -> None:
        self.assertTrue(_layered_fixtures(), "no layered fixtures; run 80_APP/tools/dev/layout_fixture.py")

    def test_every_edge_is_routed_orthogonally(self) -> None:
        for fixture in _layered_fixtures():
            prep, lay, routes = _routed(fixture)
            with self.subTest(view=fixture["view"]):
                leaves = {leaf.id for leaf in prep.leaves}
                for e in prep.edges:
                    route = routes.get(e["id"])
                    joins = e["source"] in leaves and e["target"] in leaves and e["source"] != e["target"]
                    self.assertEqual(route is not None, joins, e["id"])
                    if route is None:
                        continue
                    self.assertGreaterEqual(len(route.points), 1, e["id"])
                    for a, b in zip(route.points, route.points[1:]):
                        self.assertTrue(abs(a[0] - b[0]) < 0.01 or abs(a[1] - b[1]) < 0.01, (e["id"], a, b))

    def test_no_run_passes_through_a_node(self) -> None:
        for fixture in _layered_fixtures():
            prep, lay, routes = _routed(fixture)
            with self.subTest(view=fixture["view"]):
                boxes = {leaf.id: leaf_box(leaf, (lay.leaves[leaf.id][0], lay.leaves[leaf.id][1]))
                         for leaf in prep.leaves}
                for e in prep.edges:
                    route = routes.get(e["id"])
                    if route is None:
                        continue
                    for a, b in zip(route.points, route.points[1:]):
                        for lid, box in boxes.items():
                            if lid in (e["source"], e["target"]):
                                continue
                            # Never through the node itself, nor within the
                            # pixel of it a nudged bundle may reach.
                            self.assertFalse(_run_crosses(a, b, box, -1.0), (e["id"], lid, a, b))

    def test_lines_leave_and_arrive_squarely(self) -> None:
        """The first and last points are ports: a margin straight out from a
        side of the node (half the gap, in a tight stack), so the painter's
        line leaves and its arrow arrives square."""
        for fixture in _layered_fixtures():
            prep, lay, routes = _routed(fixture)
            with self.subTest(view=fixture["view"]):
                leaves = {leaf.id: leaf for leaf in prep.leaves}
                for route in routes.values():
                    if route is None:
                        continue
                    first, last = route.points[0], route.points[-1]
                    e = next(e for e in prep.edges if e["id"] == route.edge_id)
                    for end, point in ((e["source"], first), (e["target"], last)):
                        x, y, _, _ = lay.leaves[end]
                        box = leaf_box(leaves[end], (x, y))
                        beside_x = box[1] < point[1] < box[3] and (point[0] <= box[0] or point[0] >= box[2])
                        beside_y = box[0] < point[0] < box[2] and (point[1] <= box[1] or point[1] >= box[3])
                        self.assertTrue(beside_x or beside_y, (route.edge_id, point, box))
                        stub = min(abs(point[0] - box[0]), abs(point[0] - box[2])) if beside_x \
                            else min(abs(point[1] - box[1]), abs(point[1] - box[3]))
                        self.assertTrue(0.5 <= stub <= MARGIN + 0.01, (route.edge_id, stub))

    def test_same_routes_twice(self) -> None:
        fixture = _layered_fixtures()[0]
        _p, _l, first = _routed(fixture)
        _p, _l, second = _routed(fixture)
        self.assertEqual(first, second)

    def test_the_painter_draws_both_routers(self) -> None:
        fixture = _layered_fixtures()[0]
        payload = fixture["payload"]
        grid = render_svg(payload, sheet=False)
        pieces = render_svg(payload, sheet=False, routing="pieces")
        for text in (grid, pieces):
            root = ET.fromstring(text)
            edges = [el for el in root.iter() if el.get("class") == "edge"]
            self.assertEqual(len(edges), payload["counts"]["edges"])
        self.assertNotEqual(grid, pieces)
        self.assertEqual(grid, render_svg(payload, sheet=False))


if __name__ == "__main__":
    unittest.main()
