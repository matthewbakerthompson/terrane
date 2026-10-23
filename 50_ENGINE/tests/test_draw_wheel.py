"""The wheel drawn from Python is the app's concentric layout: the fixture
under `fixtures/wheel/` is what the app's own page ended up with for the
hub view, captured by `80_APP/tools/dev/layout_fixture.py`."""

from __future__ import annotations

import json
import math
import re
import unittest
from pathlib import Path

from terrane.draw import Undrawable, drawing_mode, render_svg
from terrane.draw.packed import Leaf, prepare
from terrane.draw.wheel import cos, degrees, layout_wheel, rings, sin
from terrane.icons import IconMap

from _fixture import REPO, laid_on

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wheel"
WEB = REPO / "80_APP" / "web"


def _fixtures():
    return sorted(FIXTURES.glob("*.json"))


def _leaf(name: str, w: int = 170, h: int = 52) -> Leaf:
    return Leaf(name, {"id": name, "label": name, "strokeWidth": 1.4}, None, "round-rectangle", "", 0, w, h)


class TestAlgorithm(unittest.TestCase):
    def test_the_series_is_the_library_to_the_last_places(self) -> None:
        for angle in (0.0, 0.3, math.pi / 2, 7 * math.pi / 6, 11 * math.pi / 6, 2 * math.pi + 0.5, -2.0):
            self.assertAlmostEqual(sin(angle), math.sin(angle), places=14, msg=angle)
            self.assertAlmostEqual(cos(angle), math.cos(angle), places=14, msg=angle)

    def test_one_hub_and_three_spokes(self) -> None:
        # The hub alone on a ring of radius nought; the spokes on a ring the
        # spacing out, since three nodes on an arc need less than that.
        hub, a, b, c = _leaf("HUB"), _leaf("A"), _leaf("B"), _leaf("C")
        out = rings([(2.0, hub), (1.0, a), (1.0, b), (1.0, c)], 241.4)
        self.assertEqual([len(ring) for _, _, ring in out], [1, 3])
        self.assertAlmostEqual(out[0][0], 0.0)
        self.assertAlmostEqual(out[1][0], 241.4)
        self.assertAlmostEqual(out[1][1], 2 * math.pi / 3)

    def test_two_hubs_tie_in_the_middle_ring(self) -> None:
        # Two nodes of the top degree share the inner ring, half the
        # spacing apart on either side; `equidistant` pushes the outer ring
        # out by the widest gap, which is the inner ring's own radius plus
        # the spacing, so the rings stay a spacing apart.
        h1, h2, a, b = _leaf("H1"), _leaf("H2"), _leaf("A"), _leaf("B")
        out = rings([(2.0, h1), (2.0, h2), (1.0, a), (1.0, b)], 100.0)
        self.assertEqual([len(ring) for _, _, ring in out], [2, 2])
        self.assertAlmostEqual(out[0][0], 50.0)
        self.assertAlmostEqual(out[1][0], 50.0 + 150.0)

    def test_degree_counts_each_edge_once_and_no_loop(self) -> None:
        payload = {"elements": [
            {"data": {"id": "A", "label": "A", "entityType": "system"}},
            {"data": {"id": "B", "label": "B", "entityType": "system"}},
            {"data": {"id": "e1", "source": "A", "target": "B"}},
            {"data": {"id": "e2", "source": "B", "target": "A"}},
            {"data": {"id": "e3", "source": "A", "target": "A"}},
        ]}
        self.assertEqual(degrees(prepare(payload)), {"A": 2, "B": 2})

    def test_the_mode_is_the_wheel_and_the_organic_layout_is_still_refused(self) -> None:
        payload = {"viewId": "v", "layout": "concentric", "kind": "diagram", "counts": {"nodes": 2, "edges": 1},
                   "elements": [{"data": {"id": "A", "label": "A", "entityType": "system"}},
                                {"data": {"id": "B", "label": "B", "entityType": "system"}},
                                {"data": {"id": "e", "source": "A", "target": "B"}}]}
        self.assertEqual(drawing_mode(payload).kind, "wheel")
        with self.assertRaises(Undrawable) as caught:
            drawing_mode(dict(payload, layout="cose"))
        self.assertEqual(caught.exception.layout, "cose")


class TestEqualToTheApp(unittest.TestCase):
    def test_there_is_a_fixture(self) -> None:
        self.assertGreaterEqual(len(_fixtures()), 1, "run 80_APP/tools/dev/layout_fixture.py for the hub view")

    def test_every_leaf_lands_where_the_app_put_it(self) -> None:
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(fixture["layout"]["layered"], False, path.name)
            payload = fixture["payload"]
            lay = layout_wheel(payload, *laid_on(fixture))
            for leaf_id, app in fixture["nodes"].items():
                if app["group"]:
                    continue
                with self.subTest(view=path.stem, leaf=leaf_id):
                    x, y, w, h = lay.leaves[leaf_id]
                    self.assertAlmostEqual(x, app["x"], places=6)
                    self.assertAlmostEqual(y, app["y"], places=6)
                    self.assertEqual((w, h), (app["w"], app["h"]))

    def test_the_picture_says_concentric_and_every_line_starts_where_the_apps_does(self) -> None:
        icons = IconMap(WEB)
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            first = render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model")
            second = render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model")
            self.assertIn('data-layout="concentric"', first)
            self.assertEqual(first, second)
            for app_edge in fixture["edges"]:
                match = re.search(r'<g class="edge" data-id="%s".*?<path d="M([-\d.]+) ([-\d.]+) L([-\d.]+) ([-\d.]+)"'
                                  % re.escape(app_edge["id"]), first, re.S)
                self.assertIsNotNone(match, app_edge["id"])
                sx, sy, ex, ey = (float(v) for v in match.groups())
                # The drawing is framed on the sheet, so the points are the
                # app's up to one translation; the vectors along each line
                # are what must agree, and the line's start is the border
                # point the app computed.
                app_dx, app_dy = app_edge["t"][0] - app_edge["s"][0], app_edge["t"][1] - app_edge["s"][1]
                length = math.hypot(app_dx, app_dy)
                own = math.hypot(ex - sx, ey - sy)
                self.assertLess(abs(own - length), 8, app_edge["id"])  # the arrow head's length
                self.assertAlmostEqual((ex - sx) / own, app_dx / length, places=3, msg=app_edge["id"])
                self.assertAlmostEqual((ey - sy) / own, app_dy / length, places=3, msg=app_edge["id"])


if __name__ == "__main__":
    unittest.main()
