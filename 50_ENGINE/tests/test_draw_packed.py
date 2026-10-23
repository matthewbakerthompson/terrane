"""The Python drawing held equal to the app's.

The app is the spec for a packed map: `fixtures/layout/*.json` is what the
running app computed for each one, read back from Cytoscape by
`80_APP/tools/dev/layout_fixture.py` -- every node's center and size, every
boundary's box, the sheet it was fitted to -- beside the payload it drew
from. `terrane.draw.packed` lays the same payload out for the same sheet and
must land every node on the same point. A boundary is allowed the few
pixels Cytoscape adds for its children's borders, which the app's own
layout does not count either; its center is held to under a pixel.

The painter is checked for what a picture can be checked for without eyes:
it is well-formed, it carries every node and boundary, it is the same
bytes twice, and it refuses nothing the layout produced. The pictures
themselves are compared by looking, with the app's PNG beside each SVG in
`80_APP/tools/dev/out/`.
"""

from __future__ import annotations

import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.draw import default_metrics, layout_packed, prepare, render_svg  # noqa: E402
from terrane.draw.packed import label_box  # noqa: E402
from terrane.draw.shapes import POLYGONS  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "layout"
REPO = Path(__file__).resolve().parents[2]
WEB = REPO / "80_APP" / "web"


def _fixtures():
    return sorted(FIXTURES.glob("*.json"))


def _icon(served: str):
    path = WEB / served
    return path.read_bytes() if served and path.is_file() else None


class TestLayoutEqualsApp(unittest.TestCase):
    def test_fixtures_exist(self) -> None:
        self.assertTrue(_fixtures(), "no layout fixtures; run 80_APP/tools/dev/layout_fixture.py")

    def test_every_node_lands_where_the_app_put_it(self) -> None:
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            prep = prepare(fixture["payload"])
            layout = layout_packed(fixture["payload"], fixture["container"]["w"], fixture["container"]["h"], prep)
            with self.subTest(view=fixture["view"]):
                self.assertEqual(len(prep.leaves), sum(1 for n in fixture["nodes"].values() if not n["group"]))
                for leaf in prep.leaves:
                    app = fixture["nodes"][leaf.id]
                    x, y, w, h = layout.leaves[leaf.id]
                    self.assertAlmostEqual(x, app["x"], places=6, msg=leaf.id)
                    self.assertAlmostEqual(y, app["y"], places=6, msg=leaf.id)
                    self.assertEqual((w, h), (app["w"], app["h"]), leaf.id)
                    # The box was sized from the same facts: what sits in
                    # the corner and how many edges touch it.
                    self.assertEqual(leaf.corner, app["corner"], leaf.id)
                    self.assertEqual(leaf.degree, app["degree"], leaf.id)

    def test_every_boundary_sits_where_the_app_drew_it(self) -> None:
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            prep = prepare(fixture["payload"])
            layout = layout_packed(fixture["payload"], fixture["container"]["w"], fixture["container"]["h"], prep)
            with self.subTest(view=fixture["view"]):
                for group in prep.groups:
                    app = fixture["nodes"][group.id]
                    x1, y1, x2, y2 = layout.groups[group.id]
                    self.assertLess(abs((x1 + x2) / 2 - app["x"]), 1.0, group.id)
                    self.assertLess(abs((y1 + y2) / 2 - app["y"]), 1.0, group.id)
                    # Cytoscape sizes a compound from its children's boxes
                    # with their borders; the layout's extent counts bodies.
                    self.assertLess(abs((x2 - x1) - app["ow"]), 8, group.id)
                    self.assertLess(abs((y2 - y1) - app["oh"]), 8, group.id)

    def test_the_shapes_are_cytoscapes(self) -> None:
        """The polygons the painter draws are the ones the renderer reported."""
        fixture = json.loads(_fixtures()[0].read_text(encoding="utf-8"))
        for name, points in POLYGONS.items():
            with self.subTest(shape=name):
                reported = fixture["shapes"].get(name)
                self.assertIsNotNone(reported, name)
                self.assertEqual(len(reported), len(points))
                for ours, theirs in zip(points, reported):
                    self.assertAlmostEqual(ours, theirs, places=3)

    def test_label_box_matches_the_calibration(self) -> None:
        # One line, no corner, no technology: 64 minimum plus padding.
        self.assertEqual(label_box("Ledger", "", "", 0), (92, 36))
        # Three lines of a long name with a mark and a technology line, and
        # the height a seven-edge hub needs for its fan.
        self.assertEqual(label_box("Dispute Management Platform Integration Gateway", "ticon", "AKS", 7), (170, 84))

    def test_boxes_of_one_kind_are_even(self) -> None:
        """Every box of one kind in a drawing is as wide as the widest of
        them and as tall as the tallest name among them; a fan of
        connections still makes one taller, and another kind keeps its own
        size. Sized each from its own name, the context diagram's systems
        ran from 92 to 182 pixels wide."""
        def node(i, label, kind="systems"):
            return {"data": {"id": i, "label": label, "entityType": kind}}
        hub_edges = [{"data": {"id": "e%d" % k, "source": "HUB", "target": "S%d" % k}} for k in range(5)]
        payload = {"elements": [node("A", "Ledger"), node("B", "Dispute Management Platform Integration Gateway"),
                                node("HUB", "Hub")] + [node("S%d" % k, "Spoke %d" % k, "actors") for k in range(5)]
                   + hub_edges}
        prep = prepare(payload)
        size = {leaf.id: (leaf.w, leaf.h) for leaf in prep.leaves}
        widest, tallest = label_box("Dispute Management Platform Integration Gateway", "ticon", "", 0)
        self.assertEqual(size["A"], (widest, tallest))
        self.assertEqual(size["B"], (widest, tallest))
        # Five connections want sixty pixels, more than three lines need.
        self.assertEqual(size["HUB"], (widest, max(tallest, 5 * 12)))
        spokes = {size["S%d" % k] for k in range(5)}
        self.assertEqual(len(spokes), 1)
        self.assertNotEqual(spokes.pop()[0], widest)


class TestPainter(unittest.TestCase):
    def test_svg_is_well_formed_and_carries_everything(self) -> None:
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            payload = fixture["payload"]
            svg = render_svg(payload, sheet_width=fixture["container"]["w"], sheet_height=fixture["container"]["h"],
                             icon_loader=_icon, model_name="Test")
            with self.subTest(view=fixture["view"]):
                root = ET.fromstring(svg)
                self.assertTrue(root.tag.endswith("svg"))
                ids = {el.get("data-id") for el in root.iter() if el.get("data-id")}
                for element in payload["elements"]:
                    data = element["data"]
                    if not data.get("source"):
                        self.assertIn(data["id"], ids)
                edges = [el for el in root.iter() if el.get("class") == "edge"]
                self.assertEqual(len(edges), payload["counts"]["edges"])
                # The sheet names the view and carries its legend's first type.
                self.assertIn(payload["title"], svg)
                self.assertIn(payload["legend"]["types"][0]["label"], svg)

    def test_same_bytes_twice(self) -> None:
        fixture = json.loads(_fixtures()[0].read_text(encoding="utf-8"))
        kwargs = dict(sheet_width=fixture["container"]["w"], sheet_height=fixture["container"]["h"], icon_loader=_icon)
        self.assertEqual(render_svg(fixture["payload"], **kwargs), render_svg(fixture["payload"], **kwargs))

    def test_plain_drawing_has_no_sheet(self) -> None:
        fixture = json.loads(_fixtures()[0].read_text(encoding="utf-8"))
        svg = render_svg(fixture["payload"], sheet=False)
        self.assertNotIn("Generated from the model", svg)
        self.assertNotIn('class="head"', svg)

    def test_labels_follow_the_budget(self) -> None:
        """Past thirty-six labeled connections the labels come off; forced
        on, every placeable one is drawn."""
        by_view = {}
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            labeled = sum(1 for e in fixture["payload"]["elements"] if e["data"].get("source") and e["data"].get("label"))
            by_view[fixture["view"]] = (fixture["payload"], labeled)
        for view, (payload, labeled) in by_view.items():
            with self.subTest(view=view):
                auto = render_svg(payload, sheet=False).count('class="edge-label"')
                forced = render_svg(payload, sheet=False, labels=True).count('class="edge-label"')
                if labeled > 36:
                    self.assertEqual(auto, 0)
                else:
                    self.assertEqual(auto, forced)
                if labeled:
                    self.assertGreater(forced, 0)


class TestMetrics(unittest.TestCase):
    def test_the_faces_the_painter_uses_were_measured(self) -> None:
        m = default_metrics()
        for family, weight in (("Geist", 400), ("Geist", 500), ("Geist", 600), ("Geist Mono", 500)):
            self.assertIn("%s/%d" % (family, weight), m.faces)

    def test_width_scales_and_wraps(self) -> None:
        m = default_metrics()
        w12 = m.width("Authorization Switch", "Geist", 600, 12)
        self.assertAlmostEqual(m.width("Authorization Switch", "Geist", 600, 24), 2 * w12, places=6)
        # Twelve-point Geist 600 sets this name in about 130 pixels: it
        # wraps at the node's 124px and stays on one line at 132.
        self.assertEqual(len(m.wrap("Installment Lending Database", 124, "Geist", 600, 12)), 2)
        self.assertEqual(m.wrap("Ledger", 124, "Geist", 600, 12), ["Ledger"])
        fitted = m.fit("Snowflake Data Cloud · Service Bus · Event Hubs", 100, "Geist", 500, 8)
        self.assertTrue(fitted.endswith("…"))
        self.assertLess(m.width(fitted, "Geist", 500, 8), 100)


if __name__ == "__main__":
    unittest.main()
