"""The organic layout drawn from Python is the app's: cose run in the
browser from the dagre seeds, as `unribbon()` runs it. The fixture under
`fixtures/organic/` is what the app's own page ended up with for a flat
view past what ELK takes, captured by `80_APP/tools/dev/layout_fixture.py`
from a probe view that was not kept; the fixture carries its payload."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from terrane.draw import render_svg
from terrane.draw.elk import open_runner
from terrane.draw.layered import is_ribbon, layout_layered
from terrane.draw.metrics import default_metrics
from terrane.draw.organic import COSE_OPTIONS, cose_graph, layout_organic
from terrane.draw.packed import prepare
from terrane.icons import IconMap

from _fixture import REPO, laid_on

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "organic"
WEB = REPO / "80_APP" / "web"


def _fixtures():
    return sorted(FIXTURES.glob("*.json"))


def _runner():
    runner = open_runner(WEB)
    if runner is None or not runner.has_cose:
        return None
    return runner


class TestGraph(unittest.TestCase):
    def test_the_graph_is_every_leaf_at_its_dagre_center_with_the_apps_size(self) -> None:
        fixture = json.loads(_fixtures()[0].read_text(encoding="utf-8"))
        payload = fixture["payload"]
        prep = prepare(payload)
        lay = layout_layered(payload, 1240, 871.4375, prep, default_metrics())
        graph = cose_graph(prep, lay)
        nodes = [e for e in graph["elements"] if "position" in e]
        edges = [e for e in graph["elements"] if "source" in e["data"]]
        self.assertEqual(len(nodes), len(prep.leaves))
        self.assertEqual(len(edges), len(prep.edges))
        for element in nodes:
            x, y, w, h = lay.leaves[element["data"]["id"]]
            self.assertEqual(element["position"], {"x": x, "y": y})
            self.assertEqual((element["data"]["w"], element["data"]["h"]), (w, h))
            self.assertGreater(element["data"]["border"], 0)
            self.assertTrue(element["data"]["shape"])
        self.assertEqual(graph["options"], COSE_OPTIONS)
        self.assertEqual(graph["options"]["nodeRepulsion"], 12000)
        self.assertEqual(graph["options"]["numIter"], 600)
        self.assertFalse(graph["options"]["randomize"])

    def test_the_fixture_is_a_ribbon_on_the_dagre_path(self) -> None:
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            # Neither ELK nor the layered pass drew it in the app: the organic one did.
            self.assertEqual((fixture["layout"]["layered"], fixture["layout"]["elk"]), (False, False), path.name)
            self.assertTrue(fixture["layout"].get("seeds"), "the app's seeds are what the fixture is reproduced from")
            payload = fixture["payload"]
            prep = prepare(payload)
            m = default_metrics()
            self.assertTrue(is_ribbon(prep, layout_layered(payload, 1240, 871.4375, prep, m), m), path.name)


@unittest.skipUnless(_runner() is not None, "no browser or no cytoscape bundle on this machine")
class TestEqualToTheApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _runner()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runner.close()

    def test_every_leaf_lands_where_the_app_put_it(self) -> None:
        for path in _fixtures():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            payload = fixture["payload"]
            prep = prepare(payload)
            lay = layout_layered(payload, *laid_on(fixture), prep, default_metrics())
            # The seeds the app recorded are where the Python dagre leaves things.
            for leaf_id, seed in fixture["layout"]["seeds"].items():
                self.assertAlmostEqual(lay.leaves[leaf_id][0], seed[0], places=6, msg=leaf_id)
                self.assertAlmostEqual(lay.leaves[leaf_id][1], seed[1], places=6, msg=leaf_id)
            out = layout_organic(prep, lay, self.runner, *laid_on(fixture))
            for leaf_id, app in fixture["nodes"].items():
                if app["group"]:
                    continue
                with self.subTest(view=path.stem, leaf=leaf_id):
                    x, y, _, _ = out.leaves[leaf_id]
                    self.assertAlmostEqual(x, app["x"], places=6)
                    self.assertAlmostEqual(y, app["y"], places=6)

    def test_the_picture_says_cose_and_is_the_same_bytes_twice(self) -> None:
        fixture = json.loads(_fixtures()[0].read_text(encoding="utf-8"))
        icons = IconMap(WEB)
        first = render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model",
                           elk=self.runner)
        second = render_svg(fixture["payload"], icon_loader=icons.read, model_name="Architecture Model",
                            elk=self.runner)
        self.assertIn('data-layout="cose"', first)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
