"""The editable deck: every node a shape of its own outline, every edge a
preset connector glued to it, set to the route the engine drew."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import terrane
from terrane.draw.dml import connector, node_path
from terrane.pack import build_pack

from _fixture import REPO

P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


class TestConnector(unittest.TestCase):
    def test_a_straight_run_is_a_straight_connector_flipped_toward_its_end(self) -> None:
        prst, rot, flip_h, flip_v, box, adj = connector([(10, 10), (110, 10)])
        self.assertEqual((prst, rot, flip_h, flip_v, adj), ("straightConnector1", 0, False, False, []))
        self.assertEqual(box, (10, 10, 100, 0))
        prst, rot, flip_h, flip_v, box, adj = connector([(110, 60), (10, 10)])
        self.assertEqual((flip_h, flip_v, box), (True, True, (10, 10, 100, 50)))

    def test_an_elbow_leaving_along_the_horizontal(self) -> None:
        # Right forty, down thirty, right sixty: a Z, its upright at forty of a hundred.
        self.assertEqual(connector([(0, 0), (40, 0), (40, 30), (100, 30)]),
                         ("bentConnector3", 0, False, False, (0, 0, 100, 30), [40000]))
        self.assertEqual(connector([(0, 0), (100, 0), (100, 30)]), ("bentConnector2", 0, False, False, (0, 0, 100, 30), []))
        # Four runs, then five, each bend measured from the start along its run.
        self.assertEqual(connector([(0, 0), (20, 0), (20, 10), (80, 10), (80, 50)])[5], [25000, 20000])
        self.assertEqual(connector([(0, 0), (20, 0), (20, 10), (60, 10), (60, 50), (100, 50)])[5], [20000, 20000, 60000])

    def test_an_elbow_leaving_along_the_vertical_is_turned_a_quarter(self) -> None:
        # Down thirty, left a hundred, down twenty: from the top right to the bottom left, the preset's own way.
        prst, rot, flip_h, flip_v, box, adj = connector([(100, 0), (100, 30), (0, 30), (0, 50)])
        self.assertEqual((prst, rot, flip_h, flip_v), ("bentConnector3", 5400000, False, False))
        # The unrotated box: the visual height for its width, about the same center (50, 25).
        self.assertEqual(box, (25, -25, 50, 100))
        self.assertEqual(adj, [60000])
        # Starting top left is a vertical flip; starting at the bottom a horizontal one.
        self.assertEqual(connector([(0, 0), (0, 30), (100, 30), (100, 50)])[2:4], (False, True))
        self.assertEqual(connector([(100, 50), (100, 20), (0, 20), (0, 0)])[2:4], (True, False))
        self.assertEqual(connector([(0, 50), (0, 20), (100, 20), (100, 0)])[2:4], (True, True))

    def test_what_the_presets_cannot_draw_goes_straight(self) -> None:
        # A curve, a U that comes back to the line it left on, six runs.
        self.assertEqual(connector([(0, 0), (50, 40), (100, 0)])[0], "straightConnector1")
        self.assertEqual(connector([(0, 0), (0, 30), (100, 30), (100, 0)])[0], "straightConnector1")
        self.assertEqual(connector([(0, 0), (10, 0), (10, 10), (20, 10), (20, 20), (30, 20), (30, 30)])[0],
                         "straightConnector1")
        # Collinear points fold into one run; a point on top of another is no run.
        self.assertEqual(connector([(0, 0), (20, 0), (40, 0), (40, 0.2), (40, 30), (100, 30)])[0], "bentConnector3")


class TestNodePath(unittest.TestCase):
    def test_each_shape_closes_in_its_own_space(self) -> None:
        for shape in ("round-rectangle", "rectangle", "ellipse", "barrel", "hexagon", "rhomboid", "octagon",
                      "cut-rectangle", "round-tag", "tag", "pentagon", "diamond", "round-octagon"):
            path = node_path(shape, 132, 36)
            self.assertTrue(path.startswith('<a:path w="132000" h="36000">'), shape)
            self.assertTrue(path.endswith("<a:close/></a:path>"), shape)
        # The eight-pixel cut of a cut rectangle, in path units.
        self.assertIn('<a:pt x="8000" y="0"/>', node_path("cut-rectangle", 132, 36))
        self.assertEqual(node_path("round-rectangle", 132, 36).count("<a:arcTo"), 4)
        self.assertEqual(node_path("ellipse", 100, 50).count("<a:arcTo"), 2)
        self.assertEqual(node_path("barrel", 100, 50).count("<a:quadBezTo"), 4)


class TestDeck(unittest.TestCase):
    def test_an_editable_deck_holds_glued_shapes_and_needs_no_picture(self) -> None:
        drawings = terrane.diagrams(str(REPO / "90_EXAMPLE" / "quick" / "sample.vsdx"), date="2026-10-17")
        scene = drawings["applications"].scene
        self.assertEqual((len(scene.nodes), len(scene.edges), len(scene.boundaries)), (7, 7, 1))
        out = Path(tempfile.mkdtemp(prefix="aac-dml-")) / "deck.pptx"
        drawings.pack(out, title="Visio", editable=True)
        with zipfile.ZipFile(out) as archive:
            slide = ET.fromstring(archive.read("ppt/slides/slide3.xml"))
            names = archive.namelist()
        # Nothing was rasterized: the deck was written with no browser.
        self.assertFalse(any(n.startswith("ppt/media/") for n in names))
        ids = [int(e.get("id")) for e in slide.iter(P + "cNvPr")]
        self.assertEqual(len(ids), len(set(ids)))
        nodes = [sp for sp in slide.iter(P + "sp") if sp.find(".//" + A + "custGeom") is not None]
        self.assertEqual(len(nodes), 7)
        connectors = list(slide.iter(P + "cxnSp"))
        self.assertEqual(len(connectors), 7)
        node_ids = {int(sp.find(".//" + P + "cNvPr").get("id")) for sp in nodes}
        for c in connectors:
            start, end = c.find(".//" + A + "stCxn"), c.find(".//" + A + "endCxn")
            self.assertIn(int(start.get("id")), node_ids)
            self.assertIn(int(end.get("id")), node_ids)
            self.assertIn(int(start.get("idx")), range(4))
            self.assertIn(c.find(".//" + A + "prstGeom").get("prst"),
                          ("straightConnector1", "bentConnector2", "bentConnector3", "bentConnector4", "bentConnector5"))
        self.assertTrue(any("editable" in (t.text or "") for t in slide.iter(A + "t")))
        self.assertTrue(any("Authorization switch" in (t.text or "") for t in slide.iter(A + "t")))

    def test_the_review_pack_opens_with_what_changed_when_something_did(self) -> None:
        said = []
        out = Path(tempfile.mkdtemp(prefix="aac-since-")) / "pack.pptx"
        # HEAD and the working tree hold the same model: said, and left out.
        path, slides = build_pack(REPO, out, ["system-context"], date="2026-10-17", log=said.append, since="HEAD")
        self.assertEqual(slides, 3)
        self.assertTrue(any("what changed since HEAD" in s and "left out" in s for s in said), said)

    def test_the_review_pack_takes_editable(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-dml-")) / "pack.pptx"
        path, slides = build_pack(REPO, out, ["system-context"], date="2026-10-17", log=lambda t: None, editable=True)
        self.assertEqual(slides, 3)
        with zipfile.ZipFile(path) as archive:
            slide = ET.fromstring(archive.read("ppt/slides/slide3.xml"))
        self.assertGreater(len(list(slide.iter(P + "cxnSp"))), 0)
        self.assertEqual(len(list(slide.iter(P + "pic"))), 0)


if __name__ == "__main__":
    unittest.main()
