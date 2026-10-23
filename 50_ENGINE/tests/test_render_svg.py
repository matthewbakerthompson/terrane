"""`terrane render` writes the view as the app draws it, as SVG beside the
Mermaid, from the payload builder the app itself reads.

The builder moved from the app's server into the engine so the engine
could draw without importing the app; the first test holds the app's
payload equal to the engine's, which is what lets the committed SVG, the
canvas and the review pack be one picture. The rest is the render command:
an SVG for every view the engine lays out, none for the ones the app alone
draws, the index and each view's page saying which, a stale picture gone,
the same bytes on a second run, and a PNG through what the machine has, when it
is installed, and a plain sentence when it is not.
"""

from __future__ import annotations

import importlib
import io
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli  # noqa: E402
from terrane.blocks import load_components  # noqa: E402
from terrane.icons import IconMap, web_dir  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.payload import graph_payload  # noqa: E402

from _fixture import REPO, drawable, remove_scratch, seeded_model, seeded_root, seeded_views  # noqa: E402

#: The views the render tests draw: a packed map, a dagre diagram, a tile
#: map, a subject view, one picture per subject, and the one ribbon the app
#: lays out organically, which is left to it.
VIEWS = ("application-landscape", "network-topology", "capability-map", "change-footprint", "change-evidence-chain",
         "change-register")


def _has_runner() -> bool:
    """Whether the ribbon the app hands to ELK is drawn here: a browser on
    the machine and the app's bundle at hand."""
    from terrane.draw.elk import open_runner

    runner = open_runner(REPO / "80_APP" / "web")
    if runner is None:
        return False
    runner.close()
    return True


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


def _render(root: Path, out: Path, *extra: str) -> str:
    text = io.StringIO()
    argv = ["--root", str(root), "render", "--out", str(out)]
    for view in VIEWS:
        argv += ["--view", view]
    with redirect_stdout(text):
        code = cli.main(argv + list(extra))
    assert code == 0, text.getvalue()
    return text.getvalue()


class TestTheEngineBuildsTheAppsPayload(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = seeded_root()
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}
        cls.palette = Palette(cls.model.config.get("palette"))
        cls.server = _server(cls.root)

    def test_the_app_and_the_engine_build_one_payload(self) -> None:
        icons = IconMap(web_dir(self.root))
        components = load_components(self.root)
        for view_id in ("application-landscape", "tiered-architecture", "network-topology", "product-architecture"):
            view = drawable(self.model, self.views[view_id])
            with self.subTest(view=view_id):
                self.assertEqual(
                    self.server._graph_payload(self.model, view, self.palette),
                    graph_payload(self.model, view, self.palette, icons, components),
                )

    def test_the_payload_carries_the_marks_and_the_styles(self) -> None:
        icons = IconMap(web_dir(self.root))
        payload = graph_payload(self.model, self.views["network-topology"], self.palette, icons,
                                load_components(self.root))
        nodes = [e["data"] for e in payload["elements"] if not e["data"].get("isGroup") and not e["data"].get("source")]
        groups = [e["data"] for e in payload["elements"] if e["data"].get("isGroup")]
        edges = [e["data"] for e in payload["elements"] if e["data"].get("source")]
        self.assertTrue(any(n["icon"].startswith("icons/") for n in nodes))
        self.assertTrue(any(g["icon"].startswith("icons/") for g in groups))
        self.assertTrue(all(e["lineStyle"] in ("solid", "dashed", "dotted") for e in edges))
        self.assertEqual(payload["counts"], {"nodes": len(nodes), "edges": len(edges)})
        self.assertEqual([t["key"] for t in payload["legend"]["types"]], ["tech_services"])


class TestRenderWritesTheSvg(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = seeded_root()
        cls.tmp = Path(tempfile.mkdtemp(prefix="aac-svg-"))
        cls.out = cls.tmp / "artifacts"
        cls.said = _render(cls.root, cls.out)

    @classmethod
    def tearDownClass(cls) -> None:
        remove_scratch(cls.tmp, "aac-svg-")

    def test_every_kind_gets_an_svg_the_tile_map_included(self) -> None:
        svg = self.out / "svg"
        self.assertTrue((svg / "application-landscape.svg").is_file())
        self.assertTrue((svg / "network-topology.svg").is_file())
        tiles = ET.fromstring((svg / "capability-map.svg").read_text(encoding="utf-8"))
        self.assertEqual(tiles.get("data-layout"), "tiles")
        # The ribbon the app hands to ELK is drawn through the browser where
        # there is one, and left to the app, saying so, where there is not.
        if _has_runner():
            self.assertTrue((svg / "change-evidence-chain.svg").is_file())
            self.assertNotIn("left to the app", self.said)
        else:
            self.assertFalse((svg / "change-evidence-chain.svg").exists())
            self.assertIn("left to the app, which draws it as elk", self.said)
        self.assertNotIn("draws it as tiles", self.said)
        # The Mermaid is still written for every view, picture or not.
        self.assertTrue((self.out / "mermaid" / "capability-map.mmd").is_file())
        # A subject view is one picture per subject, named like its Mermaid.
        subjects = sorted(p.stem for p in (self.out / "mermaid").glob("change-footprint--*.mmd"))
        self.assertTrue(subjects)
        self.assertEqual(sorted(p.stem for p in svg.glob("change-footprint--*.svg")), subjects)

    def test_the_picture_is_the_sheet_with_the_marks_inside_and_no_date(self) -> None:
        text = (self.out / "svg" / "network-topology.svg").read_text(encoding="utf-8")
        root = ET.fromstring(text)
        self.assertEqual(root.get("data-layout"), "dagre")
        self.assertIn("data:image/svg+xml;base64,", text)
        self.assertIn("edit the model, not the picture", text)
        # The faces are named, not embedded, so the file is the drawing alone.
        self.assertNotIn("@font-face", text)
        self.assertIn('font-family="Geist', text)
        # The backing is white and whole: a doubled percent sign once left
        # it out, and a viewer that shows transparency as black showed black.
        self.assertIn('<rect width="100%" height="100%" fill="#ffffff"/>', text)
        packed = ET.fromstring((self.out / "svg" / "application-landscape.svg").read_text(encoding="utf-8"))
        self.assertEqual(packed.get("data-layout"), "packed")

    def test_the_index_and_the_page_say_where_the_picture_is(self) -> None:
        index = (self.out / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("| View | Drawing | Nodes | Edges | Description |", index)
        self.assertIn("| [SVG](svg/application-landscape.svg) |", index)
        self.assertIn("| [SVG](svg/capability-map.svg) |", index)
        if _has_runner():
            self.assertNotIn("app only", index)
        else:
            self.assertIn("| elk, app only |", index)
        self.assertNotIn("tiles, app only", index)
        page = (self.out / "docs" / "application-landscape.md").read_text(encoding="utf-8")
        self.assertIn("![Application Landscape](../svg/application-landscape.svg)", page)
        self.assertLess(page.index("```mermaid"), page.index("../svg/application-landscape.svg"))
        self.assertIn("../svg/capability-map.svg", (self.out / "docs" / "capability-map.md").read_text(encoding="utf-8"))

    def test_a_second_render_writes_the_same_bytes(self) -> None:
        before = {p.name: p.read_bytes() for p in (self.out / "svg").glob("*.svg")}
        _render(self.root, self.out)
        after = {p.name: p.read_bytes() for p in (self.out / "svg").glob("*.svg")}
        self.assertEqual(before, after)

    def test_a_picture_nothing_draws_any_more_goes(self) -> None:
        # A subject's picture that no longer qualifies goes; a report's is
        # drawn afresh, as the table it is.
        report = self.out / "svg" / "change-register.svg"
        gone = self.out / "svg" / "change-footprint--wp-no-such-package.svg"
        report.write_text("<svg/>", encoding="utf-8")
        gone.write_text("<svg/>", encoding="utf-8")
        _render(self.root, self.out)
        self.assertIn('data-layout="table"', report.read_text(encoding="utf-8"))
        self.assertFalse(gone.exists())
        page = (self.out / "docs" / "change-register.md").read_text(encoding="utf-8")
        self.assertIn("](../svg/change-register.svg)", page)

    def test_the_mermaid_format_alone_writes_no_svg(self) -> None:
        out = self.tmp / "mermaid-only"
        said = _render(self.root, out, "--format", "mermaid")
        self.assertFalse((out / "svg").exists())
        self.assertNotIn("drawn as SVG", said)
        # Nor an index without its drawing column: a run of one format
        # writes no index at all (round a hundred and four), and this line
        # went on reading one for the two rounds after, unseen while CI was off.
        self.assertFalse((out / "INDEX.md").exists())

    def test_a_png_comes_from_what_the_machine_has_and_says_so(self) -> None:
        from terrane.draw.raster import NoRasterizer, open_rasterizer

        out = self.tmp / "png"
        said = _render(self.root, out, "--png")
        try:
            means = open_rasterizer().means
        except NoRasterizer:
            self.assertIn("--png asked for, but", said)
            self.assertIn("resvg-py is not installed", said)
            self.assertFalse((out / "png").exists())
        else:
            self.assertIn("PNG through %s" % means, said)
            png = out / "png" / "application-landscape.png"
            self.assertTrue(png.is_file())
            self.assertTrue(png.read_bytes().startswith(b"\x89PNG"))
        self.assertTrue((out / "svg" / "application-landscape.svg").is_file())


if __name__ == "__main__":
    unittest.main()
