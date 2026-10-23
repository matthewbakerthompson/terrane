"""ELK through the browser, held equal to the app.

The app hands a small, unlaned diagram to ELK; `terrane.draw.elk` builds the
same graph, lays it out with the same `elk.bundled.js` in a headless
browser and reads the answer back the same way. The fixtures under
`fixtures/elk/` are what the app's own page ended up with for seven such
views, captured by `80_APP/tools/dev/layout_fixture.py`; the tests lay the
same payloads out here and hold every leaf's center to the app's, the
direction to the one the app chose, every edge's ends to within the pixel
Cytoscape rounds them to, and the picture to the same bytes twice. Where
the machine has no browser they are skipped, and the dagre path draws.

The graph builder is held on its own, with no browser: the options the app
sets, the padding and minimum width of a boundary, the partitions of a
laned level, the label boxes, and the order of everything, since ELK's
answer depends on it.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.draw import render_svg  # noqa: E402
from terrane.draw.elk import PAD_TOP, ROOT_OPTIONS, elk_graph, layout_elk, open_runner  # noqa: E402
from terrane.draw.packed import prepare  # noqa: E402
from terrane.icons import IconMap  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "elk"
WEB = REPO / "80_APP" / "web"


def _fixtures():
    return sorted(FIXTURES.glob("*.json"))


class TestGraph(unittest.TestCase):
    def test_the_options_are_the_apps_and_there_is_no_post_compaction(self) -> None:
        """Every root option is one `elkGraph` sets, and neither sets ELK's
        post-compaction: it slid boxes along the rank after the lines
        crossing boundaries were routed, and six of the servicing domain's
        lines ran past their turn and back into open sheet."""
        app = (WEB / "app.js").read_text(encoding="utf-8")
        block = app.split("function elkGraph(", 1)[1].split("function applyElk(", 1)[0]
        for key, value in ROOT_OPTIONS.items():
            self.assertIn('"%s": "%s"' % (key, value), block, key)
        self.assertFalse([k for k in ROOT_OPTIONS if "postCompaction" in k])
        self.assertNotIn("postCompaction.strategy", block)

    def test_the_graph_is_the_apps(self) -> None:
        fixture = json.loads(_fixtures()[0].read_text(encoding="utf-8"))
        payload = fixture["payload"]
        prep = prepare(payload)
        graph = elk_graph(payload, prep, "LR")
        self.assertEqual(graph["id"], "__root")
        self.assertEqual(graph["layoutOptions"]["elk.direction"], "RIGHT")
        for key, value in ROOT_OPTIONS.items():
            self.assertEqual(graph["layoutOptions"][key], value, key)
        self.assertEqual(elk_graph(payload, prep, "TB")["layoutOptions"]["elk.direction"], "DOWN")
        # Every boundary is padded for its name and at least as wide as it;
        # every leaf has the size the app measured for it.
        groups = {g.id for g in prep.groups}
        leaves = {leaf.id: leaf for leaf in prep.leaves}

        def walk(node):
            for child in node.get("children", []):
                if child["id"] in groups:
                    self.assertTrue(child["layoutOptions"]["elk.padding"].startswith("[top=%d," % PAD_TOP))
                    self.assertRegex(child["layoutOptions"]["elk.nodeSize.minimum"], r"^\(\d+,40\)$")
                    walk(child)
                else:
                    self.assertEqual((child["width"], child["height"]), (leaves[child["id"]].w, leaves[child["id"]].h))

        walk(graph)
        # The edges in the payload's order, between leaves only, a label
        # box where one will be shown.
        edge_ids = [e["id"] for e in graph["edges"]]
        wanted = [e["id"] for e in prep.edges if e["source"] in leaves and e["target"] in leaves
                  and e["source"] != e["target"]]
        self.assertEqual(edge_ids, wanted)
        self.assertTrue(any("labels" in e for e in graph["edges"]))
        for edge in graph["edges"]:
            for label in edge.get("labels", []):
                self.assertGreater(label["width"], 0)
                self.assertEqual(label["height"], 19)


class TestEqualToTheApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = open_runner(WEB)
        if cls.runner is None:
            raise unittest.SkipTest("no browser or no elk.bundled.js here; the dagre path draws")

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "runner", None) is not None:
            cls.runner.close()

    def test_there_are_fixtures(self) -> None:
        self.assertGreaterEqual(len(_fixtures()), 6, "run 80_APP/tools/dev/layout_fixture.py --out tests/fixtures/elk")

    def test_every_leaf_lands_where_the_app_put_it(self) -> None:
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue((fixture.get("layout") or {}).get("elk"), "%s: the app drew it with ELK" % path.name)
            payload = fixture["payload"]
            prep = prepare(payload)
            result = layout_elk(payload, prep, self.runner, fixture["container"]["w"], fixture["container"]["h"])
            with self.subTest(path.name):
                self.assertEqual(result.layout.direction, fixture["layout"]["dir"])
                for leaf in prep.leaves:
                    app = fixture["nodes"][leaf.id]
                    x, y, w, h = result.layout.leaves[leaf.id]
                    self.assertAlmostEqual(x, app["x"], places=6, msg=leaf.id)
                    self.assertAlmostEqual(y, app["y"], places=6, msg=leaf.id)
                    self.assertEqual((w, h), (app["w"], app["h"]), leaf.id)
                # Every edge leaves and arrives where the app's does, to the
                # pixel the app rounds its endpoints to.
                by_id = {e["id"]: e for e in fixture["edges"]}
                for edge_id, route in result.routes.items():
                    app_edge = by_id.get(edge_id)
                    if app_edge is None or app_edge.get("free"):
                        continue
                    self.assertAlmostEqual(route.start[0], app_edge["s"][0], delta=1.01, msg=edge_id)
                    self.assertAlmostEqual(route.start[1], app_edge["s"][1], delta=1.01, msg=edge_id)
                    self.assertAlmostEqual(route.end[0], app_edge["t"][0], delta=1.01, msg=edge_id)
                    self.assertAlmostEqual(route.end[1], app_edge["t"][1], delta=1.01, msg=edge_id)

    def test_the_picture_says_elk_and_is_the_same_bytes_twice(self) -> None:
        # A view that draws both ways: the first fixture by name is the
        # ribbon, which has no dagre picture.
        fixture = json.loads((FIXTURES / "domain-servicing.json").read_text(encoding="utf-8"))
        icons = IconMap(WEB)
        first = render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model", elk=self.runner)
        second = render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model", elk=self.runner)
        self.assertIn('data-layout="elk"', first)
        self.assertEqual(first, second)
        without = render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model")
        self.assertIn('data-layout="dagre-for-elk"', without)

    def test_the_ribbon_goes_to_elk_as_the_app_sends_it(self) -> None:
        # Thirteen nodes and no boundaries: dagre ranks it into a line six
        # times taller than wide, and the app never shows that line, since
        # ELK takes a drawing this small. Without a runner the refusal says
        # what is missing.
        from terrane.draw import Undrawable
        fixture = json.loads((FIXTURES / "change-evidence-chain.json").read_text(encoding="utf-8"))
        self.assertEqual(fixture["layout"]["elk"], True)
        icons = IconMap(WEB)
        picture = render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model",
                             elk=self.runner)
        self.assertIn('data-layout="elk"', picture)
        with self.assertRaises(Undrawable) as caught:
            render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model")
        self.assertIn("needs a browser", str(caught.exception))


class TestSharedRunner(unittest.TestCase):
    def test_the_frame_mask_is_the_byte_by_byte_one(self) -> None:
        from terrane.draw.browser import mask_payload

        payload, mask = bytes(range(256)) * 3 + b"tail", b"\x01\x80\x00\xff"
        self.assertEqual(mask_payload(payload, mask), bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
        self.assertEqual(mask_payload(b"", mask), b"")

    def test_one_runner_per_bundle_kept_across_renders(self) -> None:
        from terrane.draw.elk import SharedRunner, open_runner
        from terrane.shipped import shipped_web

        first = open_runner(shipped_web())
        if first is None:
            self.skipTest("no browser on this machine")
        second = open_runner(shipped_web())
        self.assertIsInstance(first, SharedRunner)
        self.assertIs(first, second)
        # Closing is a courtesy: the browser stays for the next render.
        first.close()
        self.assertIs(open_runner(shipped_web()), first)


if __name__ == "__main__":
    unittest.main()
