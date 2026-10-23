"""The Python layered drawing held equal to the app's.

The app is the spec for a layered diagram on its dagre path:
`fixtures/layered/*.json` is what the running app computed for each of the
nine, read back from Cytoscape by `80_APP/tools/dev/layout_fixture.py` --
every node's center and size and box, every boundary's box, the direction
the app chose, the axis it ranked each edge along, and the points of every
routed edge as drawn. `terrane.draw.layered` lays the same payload out for the
same sheet, through the dagre port in `terrane.draw.dagre`, and must land every
leaf on the same point, choose the same direction, rank every edge along
the same axis, and turn every edge at the same place.

The tolerances, where there are any, are the app's own rounding: a route's
turn is written into Cytoscape as a weight along the chord to four decimals
and a distance to two, so the drawn point can sit a chord's twenty-thousandth
from the exact one; a leaf's center is held to six decimal places, since
the port does the same arithmetic in the same order.
"""

from __future__ import annotations

import json
import math
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.draw import Undrawable, default_metrics, drawing_mode, layout_layered, prepare, render_svg  # noqa: E402
from terrane.draw import dagre, layered  # noqa: E402
from terrane.draw.layered import TUCK_BREADTHS, group_box, leaf_box, route_layered, tuck_ranks  # noqa: E402
from terrane.draw.packed import _Item  # noqa: E402
from terrane.draw.router import route_grid  # noqa: E402
from terrane.draw.svg import ELLIPSE, arrow_width, polygon_points, round_corner  # noqa: E402
from _fixture import laid_in  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "layered"
PACKED_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "layout"
REPO = Path(__file__).resolve().parents[2]
WEB = REPO / "80_APP" / "web"


def _fixtures():
    return sorted(FIXTURES.glob("*.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _layout(fixture: dict):
    prep = prepare(fixture["payload"])
    return prep, layout_layered(fixture["payload"], *laid_in(fixture), prep)


def _icon(served: str):
    path = WEB / served
    return path.read_bytes() if served and path.is_file() else None


class TestLayoutEqualsApp(unittest.TestCase):
    def test_fixtures_exist(self) -> None:
        self.assertEqual(len(_fixtures()), 9, "nine dagre views; run 80_APP/tools/dev/layout_fixture.py")

    def test_the_app_drew_every_fixture_on_the_dagre_path(self) -> None:
        for path in _fixtures():
            fixture = _load(path)
            with self.subTest(view=fixture["view"]):
                self.assertTrue(fixture["layout"]["layered"], "the app did not route this one")
                self.assertFalse(fixture["layout"]["elk"], "the app handed this one to ELK")
                self.assertFalse(drawing_mode(fixture["payload"]).fallback)

    def test_every_leaf_lands_where_the_app_put_it(self) -> None:
        for path in _fixtures():
            fixture = _load(path)
            prep, lay = _layout(fixture)
            with self.subTest(view=fixture["view"]):
                self.assertEqual(len(prep.leaves), sum(1 for n in fixture["nodes"].values() if not n["group"]))
                for leaf in prep.leaves:
                    app = fixture["nodes"][leaf.id]
                    x, y, w, h = lay.leaves[leaf.id]
                    self.assertAlmostEqual(x, app["x"], places=6, msg=leaf.id)
                    self.assertAlmostEqual(y, app["y"], places=6, msg=leaf.id)
                    self.assertEqual((w, h), (app["w"], app["h"]), leaf.id)
                    self.assertEqual(leaf.corner, app["corner"], leaf.id)
                    self.assertEqual(leaf.degree, app["degree"], leaf.id)

    def test_the_direction_and_the_edge_axes_are_the_apps(self) -> None:
        for path in _fixtures():
            fixture = _load(path)
            prep, lay = _layout(fixture)
            with self.subTest(view=fixture["view"]):
                self.assertEqual(lay.direction, fixture["layout"]["dir"])
                self.assertEqual(lay.edge_axis, fixture["layout"]["axis"])

    def test_every_boundary_is_drawn_where_the_app_drew_it(self) -> None:
        """The box the painter draws for a compound is Cytoscape's: the
        children's boxes with their borders and their miters, the padding,
        the room for its own name."""
        for path in _fixtures():
            fixture = _load(path)
            prep, lay = _layout(fixture)
            memo = {}
            with self.subTest(view=fixture["view"]):
                for group in prep.groups:
                    app = fixture["nodes"][group.id]
                    for ours, theirs in zip(group_box(prep, lay, group, memo), app["bb"]):
                        self.assertAlmostEqual(ours, theirs, places=6, msg=group.id)

    def test_the_layouts_own_extent_is_near_the_drawn_box(self) -> None:
        """The extent the layout sized a boundary with counts bodies, not
        borders, so the drawn box is larger by what every level of nesting
        adds -- a border and a pixel of antialiasing a side, under three
        pixels, five levels deep at most -- and off center by what one side's nesting adds that the other's does
        not. The drawn box is held exactly above; this holds the extent to
        that sum."""
        for path in _fixtures():
            fixture = _load(path)
            prep, lay = _layout(fixture)
            with self.subTest(view=fixture["view"]):
                for group in prep.groups:
                    app = fixture["nodes"][group.id]
                    x1, y1, x2, y2 = lay.groups[group.id]
                    self.assertLess(abs((x1 + x2) / 2 - app["x"]), 6.0, group.id)
                    self.assertLess(abs((y1 + y2) / 2 - app["y"]), 6.0, group.id)
                    self.assertLess(abs((x2 - x1) - app["ow"]), 36, group.id)
                    self.assertLess(abs((y2 - y1) - app["oh"]), 36, group.id)

    def test_every_node_box_is_cytoscapes(self) -> None:
        """The box the router and the sheet fit read: the border, its
        miters on a sharp-cornered shape, and a pixel of antialiasing."""
        for path in list(_fixtures()) + sorted(PACKED_FIXTURES.glob("*.json")):
            fixture = _load(path)
            prep = prepare(fixture["payload"])
            with self.subTest(view=fixture["view"]):
                for leaf in prep.leaves:
                    app = fixture["nodes"][leaf.id]
                    for ours, theirs in zip(leaf_box(leaf, (app["x"], app["y"])), app["bb"]):
                        self.assertAlmostEqual(ours, theirs, places=6, msg=leaf.id)

    def test_every_edge_turns_where_the_app_turned_it(self) -> None:
        """The grid router's corners, drawn by the app (`planGrid`) and
        routed by the Python (`route_grid`), the same to the app's rounding."""
        for path in _fixtures():
            fixture = _load(path)
            prep, lay = _layout(fixture)
            routes = route_grid(prep, lay, lay.direction == "TB")
            by_id = {e["id"]: e for e in fixture["edges"]}
            with self.subTest(view=fixture["view"]):
                self.assertEqual(set(routes), set(by_id))
                for edge_id, route in routes.items():
                    app = by_id[edge_id]
                    self.assertEqual(route is None, bool(app["free"]), edge_id)
                    if route is None:
                        continue
                    pts = app["pts"]
                    drawn = [(pts[i], pts[i + 1]) for i in range(2, len(pts) - 2, 2)]
                    self.assertEqual(len(drawn), len(route.points), edge_id)
                    sx, sy = lay.leaves[app["id"].split("::")[1]][:2]
                    tx, ty = lay.leaves[app["id"].split("::")[2]][:2]
                    slack = 0.00005 * math.hypot(tx - sx, ty - sy) + 0.01
                    for (ax, ay), (bx, by) in zip(drawn, route.points):
                        self.assertLess(abs(ax - bx), slack, edge_id)
                        self.assertLess(abs(ay - by), slack, edge_id)

    def test_the_three_pieces_are_the_apps(self) -> None:
        """The fallback for an edge the grid cannot carry, planned on the
        app's page beside its drawing (`__aacLayout.pieces`) and by
        `route_layered`, to the same points and the same ends."""
        for path in _fixtures():
            fixture = _load(path)
            prep, lay = _layout(fixture)
            routes = route_layered(prep, lay, lay.direction == "TB")
            planned = fixture["pieces"]
            centers = {leaf.id: lay.leaves[leaf.id][:2] for leaf in prep.leaves}
            with self.subTest(view=fixture["view"]):
                self.assertEqual(set(routes), set(planned))
                for edge_id, route in routes.items():
                    app = planned[edge_id]
                    self.assertEqual(route is None, app is None, edge_id)
                    if route is None:
                        continue
                    self.assertEqual(len(route.points), len(app["points"]), edge_id)
                    for ours, theirs in zip(route.points, app["points"]):
                        self.assertAlmostEqual(ours[0], theirs[0], places=6, msg=edge_id)
                        self.assertAlmostEqual(ours[1], theirs[1], places=6, msg=edge_id)
                    _, source, target = edge_id.split("::")
                    for ours, theirs, end in ((route.start, app["sep"], source), (route.end, app["tep"], target)):
                        self.assertEqual(ours is None, theirs == "outside-to-node", edge_id)
                        if ours is None:
                            continue
                        ox, oy = (float(v[:-2]) for v in theirs.split())
                        self.assertAlmostEqual(ours[0], centers[end][0] + ox, places=6, msg=edge_id)
                        self.assertAlmostEqual(ours[1], centers[end][1] + oy, places=6, msg=edge_id)

    def test_the_line_leaves_and_arrives_where_the_app_does(self) -> None:
        """The painter's endpoints against Cytoscape's: on the outer border,
        or pinned to the port's place on a straight side, the target's
        pulled back under the arrow head; and the midpoint a label hangs
        from."""
        from terrane.draw.svg import _layered_edges, polygon_points
        for path in _fixtures():
            fixture = _load(path)
            prep, lay = _layout(fixture)
            centers = {leaf.id: lay.leaves[leaf.id][:2] for leaf in prep.leaves}
            polygons = {}
            for leaf in prep.leaves:
                x, y, w, h = lay.leaves[leaf.id]
                border = float(leaf.data.get("strokeWidth") or 1)
                polygons[leaf.id] = polygon_points(leaf.shape, x, y, w + border, h + border)
            edges = {e.data["id"]: e for e in _layered_edges(prep, lay, centers, polygons, 1.6)}
            with self.subTest(view=fixture["view"]):
                for app in fixture["edges"]:
                    edge = edges[app["id"]]
                    pts = app["pts"]
                    for ours, theirs in ((edge.points[0], (pts[0], pts[1])), (edge.points[-1], (pts[-2], pts[-1]))):
                        self.assertLess(math.hypot(ours[0] - theirs[0], ours[1] - theirs[1]), 1.0, app["id"])
                    self.assertLess(math.hypot(edge.mid[0] - app["mid"][0], edge.mid[1] - app["mid"][1]), 1.0,
                                    app["id"])


def _through(box, a, b) -> bool:
    """Whether the straight piece from a to b passes through the box:
    Liang-Barsky clipping, true when anything of it is left."""
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - box[0]), (dx, box[2] - a[0]), (-dy, a[1] - box[1]), (dy, box[3] - a[1])):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            if t > t1:
                return False
            t0 = max(t0, t)
        else:
            if t < t0:
                return False
            t1 = min(t1, t)
    return True


def _text(fixture, group):
    """The name's text itself: the router's box for it without the air, so
    a line in the corridor at the edge of that box, beside the word, is
    not counted as through it."""
    x1, y1, x2, y2 = layered.boundary_word(fixture["nodes"][group.id]["bb"], group)
    return (x1 + 4, y1 + 3, x2 - 4, y2 - 3)


def _pieces(app_edge):
    pts = app_edge["pts"]
    return [((pts[i], pts[i + 1]), (pts[i + 2], pts[i + 3])) for i in range(0, len(pts) - 2, 2)]


class TestCollisions(unittest.TestCase):
    """What a line no longer runs into, read off the app's own drawings,
    each from a picture where it did: a boundary's name on its border, a
    line through a name, a line slanting out of its place in a fan, a line
    through a boundary it has no business in."""

    def _groups(self, fixture):
        prep = prepare(fixture["payload"])
        return {g.id: g for g in prep.groups}

    def test_a_boundary_name_is_one_line_inside_its_box(self) -> None:
        """"account prod-riskops" wrapped at the 132 pixels every node label
        wraps at, and the first line sat on the account's border."""
        fixture = _load(FIXTURES / "network-topology.json")
        svg = render_svg(fixture["payload"], sheet_width=fixture["container"]["w"],
                         sheet_height=fixture["container"]["h"], icon_loader=_icon)
        ns = "{http://www.w3.org/2000/svg}"
        boundaries = [el for el in ET.fromstring(svg).iter() if el.get("class") == "boundary"]
        self.assertEqual(len(boundaries), 20)
        labels = {g.id: str(g.data.get("label") or "") for g in self._groups(fixture).values()}
        for el in boundaries:
            texts = el.findall(ns + "text")
            with self.subTest(boundary=el.get("data-id")):
                self.assertEqual([t.text for t in texts], [labels[el.get("data-id")]])
                # The baseline a full line below the border: the word is in.
                self.assertGreater(float(texts[0].get("y")) - 11, float(el.find(ns + "rect").get("y")))

    def test_the_apps_name_widths_are_the_measured_ones(self) -> None:
        """The router's box for a name is the word as Chrome draws it; the
        app carries the advances as a table, and it is this one."""
        source = (WEB / "app.js").read_text(encoding="utf-8")
        found = re.search(r"var NAME_ADVANCE = (\{.*?\});", source, re.S)
        self.assertIsNotNone(found)
        self.assertEqual(json.loads(found.group(1)), layered.NAME_ADVANCE)
        self.assertEqual(len(layered.NAME_ADVANCE), 95)
        # A long name is narrower than its nominal width, a short capital
        # one wider: the reason the nominal width would not do.
        self.assertAlmostEqual(layered.name_width("subscription azure-platform-prod"), 180.75, places=6)
        self.assertAlmostEqual(len("subscription azure-platform-prod") * 6.1, 195.2, places=6)
        # Advances only: "AW" kerns a pixel and a half, and the box is that
        # much wider than the word, not narrower.
        self.assertAlmostEqual(layered.name_width("AWS"), 26.05, places=6)
        self.assertGreater(layered.name_width("AWS"), default_metrics().width("AWS", "Geist", 600, 11))

    def test_the_long_run_to_the_edge_tier_clears_private_app(self) -> None:
        """Tiered Architecture's line from the screening vendor turned ten
        short of the first row of a tier, which is in the tier's padding,
        and struck "Private-App" through."""
        fixture = _load(FIXTURES / "tiered-architecture.json")
        word = _text(fixture, self._groups(fixture)["grp::Private-App"])
        for app in fixture["edges"]:
            with self.subTest(edge=app["id"]):
                self.assertFalse(any(_through(word, a, b) for a, b in _pieces(app)))

    def test_no_line_runs_through_a_name_on_the_network_topology(self) -> None:
        """Cloud DNS's line to the data center climbed through "project
        gcp-lending-prod" and "region europe-west1"; every name there has a
        way round."""
        fixture = _load(FIXTURES / "network-topology.json")
        for gid, group in self._groups(fixture).items():
            word = _text(fixture, group)
            for app in fixture["edges"]:
                with self.subTest(boundary=gid, edge=app["id"]):
                    self.assertFalse(any(_through(word, a, b) for a, b in _pieces(app)))

    def test_a_fanned_line_leaves_and_arrives_square(self) -> None:
        """A line fanned along a straight side leaves from its place in the
        fan. Found on the ray from the center, Card Servicing Service's line
        to Customer Identity API slanted across three hundred and fifty
        pixels, and two hundred and thirty pieces on the nine drawings did
        the same."""
        for path in _fixtures():
            fixture = _load(path)
            prep = prepare(fixture["payload"])
            shapes = {leaf.id: leaf.shape for leaf in prep.leaves}
            for app in fixture["edges"]:
                if app["free"]:
                    continue
                _, source, target = app["id"].split("::")
                pieces = _pieces(app)
                with self.subTest(view=fixture["view"], edge=app["id"]):
                    for leaf, (a, b) in ((source, pieces[0]), (target, pieces[-1])):
                        if shapes[leaf] in layered.PORTED:
                            self.assertTrue(abs(a[0] - b[0]) < 0.5 or abs(a[1] - b[1]) < 0.5, (a, b))

    def test_the_line_to_customer_identity_keeps_out_of_private_data(self) -> None:
        """On the onboarding drawing it climbed inside Private-Data, beside
        its border, to reach the platform subscription: a box that holds
        neither end, in and out again."""
        fixture = _load(FIXTURES / "onboarding.json")
        bb = fixture["nodes"]["grp::Azure::azure-cards-prod::uksouth::Private-Data"]["bb"]
        app = next(e for e in fixture["edges"] if e["id"] == "e2::SYS-CARDSVC-API::OI-IDENTITY-API")
        self.assertFalse(any(_through(bb, a, b) for a, b in _pieces(app)))


class TestDagre(unittest.TestCase):
    """The port on graphs small enough to reason about."""

    def _graph(self, rankdir: str = "TB") -> dagre.Graph:
        g = dagre.Graph()
        g.set_graph({"rankdir": rankdir, "nodesep": 26, "ranksep": 48, "edgesep": 14, "marginx": 0, "marginy": 0})
        g.set_default_edge_label(lambda v, w, name: {})
        return g

    def test_a_chain_ranks_down_the_page(self) -> None:
        g = self._graph()
        for v in "abc":
            g.set_node(v, {"width": 100, "height": 40})
        g.set_edge("a", "b")
        g.set_edge("b", "c")
        dagre.layout(g)
        self.assertEqual([g.node(v)["x"] for v in "abc"], [50, 50, 50])
        self.assertEqual([g.node(v)["y"] for v in "abc"], [20, 108, 196])
        self.assertEqual((g.graph()["width"], g.graph()["height"]), (100, 216))

    def test_a_chain_ranks_across_the_page(self) -> None:
        g = self._graph("LR")
        for v in "ab":
            g.set_node(v, {"width": 100, "height": 40})
        g.set_edge("a", "b")
        dagre.layout(g)
        self.assertEqual((g.node("a")["x"], g.node("a")["y"]), (50, 20))
        self.assertEqual((g.node("b")["x"], g.node("b")["y"]), (198, 20))

    def test_a_cycle_is_broken_and_laid_out(self) -> None:
        g = self._graph()
        for v in "ab":
            g.set_node(v, {"width": 60, "height": 30})
        g.set_edge("a", "b")
        g.set_edge("b", "a")
        dagre.layout(g)
        self.assertEqual(g.node("a")["y"], 15)
        self.assertEqual(g.node("b")["y"], 93)
        self.assertEqual(len(g.edge("b", "a")["points"]), 3)

    def test_siblings_sit_a_nodesep_apart(self) -> None:
        g = self._graph()
        for v in "abc":
            g.set_node(v, {"width": 60, "height": 30})
        g.set_edge("a", "b")
        g.set_edge("a", "c")
        dagre.layout(g)
        self.assertEqual(g.node("c")["x"] - g.node("b")["x"], 86)
        self.assertEqual(g.node("a")["x"], (g.node("b")["x"] + g.node("c")["x"]) / 2)

    def test_what_the_port_does_not_carry_is_refused(self) -> None:
        g = self._graph()
        g.set_node("a", {"width": 10, "height": 10})
        g.set_edge("a", "a")
        with self.assertRaises(dagre.DagreError):
            dagre.layout(g)


class TestTuck(unittest.TestCase):
    """A level that holds boundaries, tucked: `tuck_ranks` on a level small
    enough to reason about, left to right, a rank gap of 48."""

    def _level(self):
        # A rank 0..300 along; then a rank whose tall boundary B and short
        # boundary C share a center line at 548; then two leaves at 900.
        items = [_Item("A", True, 300, 100, (0, 0, 0, 0)), _Item("B", True, 400, 300, (0, 0, 0, 0)),
                 _Item("C", True, 100, 50, (0, 0, 0, 0)), _Item("L1", False, 100, 40, (0, 0, 0, 0)),
                 _Item("L2", False, 100, 60, (0, 0, 0, 0))]
        target = {"A": (150, 200), "B": (548, 150), "C": (548, 340), "L1": (900, 50), "L2": (900, 150)}
        preds = {"B": ["A"], "C": ["A"], "L1": ["B"]}
        tuck_ranks(items, target, False, 48, preds)
        return {k: (x, y) for k, (x, y) in target.items()}, {it.id: it for it in items}

    def test_a_boundary_goes_into_the_hole_beside_a_short_one(self) -> None:
        at, items = self._level()
        # A hangs from the top; C, a rank later, fits under it inside the
        # level's breadth and goes there; B cannot, and stays a rank on.
        self.assertEqual(at["A"], (150, 50))
        self.assertEqual(at["C"][0] - 50, 0)
        self.assertEqual(at["C"][1] - 25, 100 + 26)
        self.assertEqual(at["B"], (300 + 48 + 200, 150))

    def test_a_ranks_leaves_move_as_one_row(self) -> None:
        at, items = self._level()
        # Both up to a rank gap after B, the deepest thing they sit beside,
        # still on one center line and each where it was across.
        self.assertEqual(at["L1"][0], at["L2"][0])
        self.assertEqual(at["L1"][0] - 50, 748 + 48)
        self.assertEqual((at["L1"][1], at["L2"][1]), (50, 150))

    def test_what_a_leaf_points_at_stays_a_rank_after_it(self) -> None:
        items = [_Item("G", True, 200, 100, (0, 0, 0, 0)), _Item("P", False, 100, 40, (0, 0, 0, 0)),
                 _Item("Q", False, 100, 40, (0, 0, 0, 0))]
        # Q's rank holds nothing beside it across, so only its arrow keeps
        # it from sliding up beside P.
        target = {"G": (100, 50), "P": (50, 300), "Q": (198, 500)}
        tuck_ranks(items, target, False, 48, {"Q": ["P"]})
        self.assertEqual(target["Q"][0] - 50, target["P"][0] + 50 + 48)

    def test_the_network_topologys_holes_are_filled(self) -> None:
        fixture = _load(FIXTURES / "network-topology.json")
        boxes = fixture["nodes"]
        shared, riskops = boxes["grp::AWS::shared-network"]["bb"], boxes["grp::AWS::prod-riskops"]["bb"]
        aws, gcp, onprem = boxes["grp::AWS"]["bb"], boxes["grp::GCP"]["bb"], boxes["grp::On-prem"]["bb"]
        # Risk Ops under the shared-network account, in its column (the
        # drawn boxes differ by their borders and names), not a rank on under
        # Lending; On-prem under AWS beside GCP, not past AWS's right edge.
        self.assertAlmostEqual(riskops[0], shared[0], delta=8)
        self.assertGreater(riskops[1], shared[3])
        self.assertLess(onprem[2], aws[2])
        self.assertGreater(onprem[1], aws[3])
        self.assertGreater(onprem[0], gcp[2])

    def test_tucking_never_fits_the_sheet_worse_than_dagre(self) -> None:
        # Weighed tucked alone, the turn kept six capability alignments in
        # a direction dagre had them turn out of, up to a seventh wider; a
        # row of leaves pushed past a hung boundary made Lending
        # Performance's top level longer. Neither may come back.
        m = default_metrics()
        for path in _fixtures():
            fixture = _load(path)
            payload, (w, h) = fixture["payload"], laid_in(fixture)
            prep = prepare(payload)

            def fit(lay):
                x1, y1, x2, y2 = layered.elements_box(prep, lay, m)
                return min(w / (x2 - x1), h / (y2 - y1))

            own = str(payload.get("layout") or "LR")
            other = "LR" if own == "TB" else "TB"
            raw_own = fit(layered.layout_hierarchy(payload, w, h, own, False, False, prep, False))
            raw_other = fit(layered.layout_hierarchy(payload, w, h, other, False, False, prep, False))
            raw = raw_other if raw_other > raw_own * 1.3 else raw_own
            with self.subTest(view=fixture["view"]):
                self.assertGreaterEqual(fit(layout_layered(payload, w, h, prep, m)), raw - 1e-9)

    def test_the_breadths_tried_are_the_apps(self) -> None:
        app = (WEB / "app.js").read_text(encoding="utf-8")
        found = re.search(r"var TUCK_BREADTHS = \[([^\]]*)\];", app)
        self.assertIsNotNone(found)
        self.assertEqual(tuple(float(v) for v in found.group(1).split(",")), TUCK_BREADTHS)


class TestMode(unittest.TestCase):
    def test_the_nine_are_layered_on_the_dagre_path(self) -> None:
        for path in _fixtures():
            fixture = _load(path)
            mode = drawing_mode(fixture["payload"])
            self.assertEqual((mode.kind, mode.fallback), ("layered", False), fixture["view"])

    def test_the_packed_maps_are_packed(self) -> None:
        for path in sorted(PACKED_FIXTURES.glob("*.json")):
            fixture = _load(path)
            self.assertEqual(drawing_mode(fixture["payload"]).kind, "packed", fixture["view"])

    def test_a_tile_map_is_tiles_a_wheel_is_the_wheel_and_an_organic_layout_is_refused(self) -> None:
        tiles = {"viewId": "t", "kind": "map", "elements": [{"data": {"id": "a", "label": "A"}}],
                 "counts": {"nodes": 1, "edges": 0}}
        self.assertEqual(drawing_mode(tiles).kind, "tiles")
        wheel = {"viewId": "w", "kind": "diagram", "layout": "concentric", "counts": {"nodes": 3, "edges": 2},
                 "elements": [{"data": {"id": "a", "label": "A"}}, {"data": {"id": "b", "label": "B"}},
                              {"data": {"id": "e", "source": "a", "target": "b"}}]}
        self.assertEqual(drawing_mode(wheel).kind, "wheel")
        with self.assertRaises(Undrawable) as caught:
            drawing_mode(dict(wheel, layout="cose"))
        self.assertIn("cose", str(caught.exception))

    def test_a_small_unlaned_diagram_is_the_apps_elk_drawing(self) -> None:
        fixture = _load(FIXTURES / "onboarding.json")
        payload = json.loads(json.dumps(fixture["payload"]))
        payload["lanes"] = {}
        # Nine leaves in twelve boundaries: past ELK's eight boundaries.
        self.assertFalse(drawing_mode(payload).fallback)
        kept = [e for e in payload["elements"] if not e["data"].get("isGroup")]
        for element in kept:
            element["data"].pop("parent", None)
        payload["elements"] = kept
        self.assertTrue(drawing_mode(payload).fallback)


class TestPainter(unittest.TestCase):
    def test_svg_is_well_formed_and_carries_everything(self) -> None:
        for path in _fixtures():
            fixture = _load(path)
            payload = fixture["payload"]
            svg = render_svg(payload, sheet_width=fixture["container"]["w"], sheet_height=fixture["container"]["h"],
                             icon_loader=_icon, model_name="Test")
            with self.subTest(view=fixture["view"]):
                root = ET.fromstring(svg)
                self.assertEqual(root.get("data-layout"), "dagre")
                ids = {el.get("data-id") for el in root.iter() if el.get("data-id")}
                for element in payload["elements"]:
                    data = element["data"]
                    if not data.get("source"):
                        self.assertIn(data["id"], ids)
                edges = [el for el in root.iter() if el.get("class") == "edge"]
                self.assertEqual(len(edges), payload["counts"]["edges"])
                # A layered line stands at full weight, orthogonal, with
                # its corners rounded.
                for el in edges:
                    self.assertIsNone(el.get("opacity"))
                    line = el.find("{http://www.w3.org/2000/svg}path")
                    self.assertEqual(line.get("stroke-width"), "1.6")
                self.assertTrue(any(" A10 10 0 0 " in el.find("{http://www.w3.org/2000/svg}path").get("d")
                                    for el in edges))

    def test_same_bytes_twice(self) -> None:
        fixture = _load(_fixtures()[0])
        kwargs = dict(sheet_width=fixture["container"]["w"], sheet_height=fixture["container"]["h"], icon_loader=_icon)
        self.assertEqual(render_svg(fixture["payload"], **kwargs), render_svg(fixture["payload"], **kwargs))

    def test_a_standing_in_drawing_says_so(self) -> None:
        fixture = _load(FIXTURES / "onboarding.json")
        payload = json.loads(json.dumps(fixture["payload"]))
        payload["lanes"] = {}
        kept = [e for e in payload["elements"] if not e["data"].get("isGroup")]
        for element in kept:
            element["data"].pop("parent", None)
        payload["elements"] = kept
        root = ET.fromstring(render_svg(payload, sheet=False))
        self.assertEqual(root.get("data-layout"), "dagre-for-elk")

    def test_labels_follow_the_budget(self) -> None:
        """Past thirty-six labeled connections the labels come off; forced
        on, every placeable one is drawn. A label that only repeats what
        the line style says is never counted or placed."""
        from terrane.draw.shapes import edge_word
        for path in _fixtures():
            fixture = _load(path)
            payload = fixture["payload"]
            labeled = sum(1 for e in payload["elements"] if e["data"].get("source") and e["data"].get("label")
                          and str(e["data"]["label"]).lower() != str(edge_word(str(e["data"].get("kind") or ""))
                                                                     or "").lower())
            with self.subTest(view=fixture["view"]):
                auto = render_svg(payload, sheet=False).count('class="edge-label"')
                forced = render_svg(payload, sheet=False, labels=True).count('class="edge-label"')
                if labeled > 36:
                    self.assertEqual(auto, 0)
                else:
                    self.assertEqual(auto, forced)
                if labeled:
                    self.assertGreater(forced, 0)


class TestTheSameBytesEverywhere(unittest.TestCase):
    """CI compares the committed SVG byte for byte on a Linux runner with
    what Windows rendered, so the painter may use nothing whose last bit
    depends on the platform's C library: the four basic operations and
    sqrt are the same number everywhere under IEEE 754, and so is
    `math.hypot`, which is CPython's own; sin, cos, acos, atan2 and pow
    are not, and one bit of tan(45 degrees) once turned a radius of 3.265
    into 3.27 on one platform and 3.26 on the other."""

    def test_the_drawing_code_asks_the_c_library_for_nothing_but_sqrt(self) -> None:
        import re

        forbidden = re.compile(r"math\.(?:acos|asin|atan2?|cosh?|sinh?|tanh?|exp|expm1|log(?:2|10|1p)?|pow|degrees|"
                               r"radians|fmod|erfc?|gamma|lgamma)\b|\*\*\s*(?:0\.|\d+\.\d)")
        for path in sorted((REPO / "50_ENGINE" / "terrane" / "draw").glob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#", 1)[0]
                self.assertIsNone(forbidden.search(code), "%s:%d: %s" % (path.name, number, line.strip()))

    def test_a_right_angle_corner_pulled_in_keeps_its_radius_exactly(self) -> None:
        # A piece 6.53 long holds a corner pulled in to 3.265 on each side,
        # and the radius of a right-angle turn is that same number, exactly,
        # not 3.265 times a tan(45 degrees) a bit off 1.
        corner = round_corner((0.0, 50.0), (6.53, 50.0), (6.53, 60.0), 10.0)
        self.assertIsNotNone(corner)
        self.assertEqual(corner.radius, 3.265)
        self.assertEqual(corner.tin, (3.265, 50.0))
        self.assertEqual(corner.tout, (6.53, 50.0 + 3.265))
        # A corner of the asked radius on long pieces sits where it did.
        wide = round_corner((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), 10.0)
        self.assertEqual(wide.radius, 10.0)
        self.assertEqual(wide.tin, (90.0, 0.0))
        self.assertEqual(wide.tout, (100.0, 10.0))
        self.assertAlmostEqual(wide.center[0], 90.0, places=9)
        self.assertAlmostEqual(wide.center[1], 10.0, places=9)
        # Straight through and doubling back are not corners.
        self.assertIsNone(round_corner((0.0, 0.0), (10.0, 0.0), (20.0, 0.0), 10.0))
        self.assertIsNone(round_corner((0.0, 0.0), (10.0, 0.0), (0.0, 0.0), 10.0))

    def test_the_ellipse_and_the_arrow_come_from_literals(self) -> None:
        self.assertEqual(len(ELLIPSE), 36)
        self.assertEqual(ELLIPSE[0], (1.0, 0.0))
        self.assertEqual(ELLIPSE[9], (0.0, 1.0))
        self.assertEqual(ELLIPSE[18], (-1.0, 0.0))
        self.assertEqual(ELLIPSE[27], (0.0, -1.0))
        self.assertEqual(ELLIPSE[3], (0.8660254037844387, 0.5))
        self.assertEqual(ELLIPSE[6], (0.5, 0.8660254037844387))
        for c, s in ELLIPSE:
            self.assertAlmostEqual(c * c + s * s, 1.0, places=12)
        points = polygon_points("ellipse", 10.0, 20.0, 40.0, 20.0)
        self.assertEqual(points[0], (30.0, 20.0))
        self.assertEqual(points[9], (10.0, 30.0))
        # Every line the painter draws is under the arrow's floor, and a
        # line that is not is refused rather than sized by the C library.
        self.assertEqual(arrow_width(1.3, 1.1), 29.0 * 1.1)
        self.assertEqual(arrow_width(1.6, 1.1), 29.0 * 1.1)
        with self.assertRaises(ValueError):
            arrow_width(5.0, 1.0)


if __name__ == "__main__":
    unittest.main()
