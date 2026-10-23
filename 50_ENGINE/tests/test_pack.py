"""The review pack from Python: a deck the standard library writes, with a
slide per view, that opens as a presentation."""

from __future__ import annotations

import io
import posixpath
import re
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree

from terrane import pptx
from terrane.draw.raster import NoRasterizer, open_rasterizer
from terrane.model import load
from terrane.pack import PackError, build_pack, choose
from terrane.query import load_views

from _fixture import REPO as REPO_ROOT

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def _png(width: int, height: int) -> bytes:
    """A blank PNG of the size, enough for the writer to measure."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff" * (width * 3) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _has_browser() -> bool:
    try:
        open_rasterizer().close()
        return True
    except NoRasterizer:
        return False


class TestWriter(unittest.TestCase):
    def _deck(self) -> pptx.Deck:
        deck = pptx.Deck("A deck")
        slide = deck.slide()
        slide.text(0.5, 0.5, 12, 1, "Hello & <goodbye>", size=22, bold=True)
        slide.text(0.5, 1.5, 12, 1, [[("Shelf", {"bold": True, "color": "3D4FA3"})], [("3.  A view", {})]], size=11)
        x, y, w, h = pptx.fitted((1240, 871), (0.5, 1.9, 12.3, 5.0))
        slide.image(_png(1240, 871), x, y, w, h)
        deck.slide().text(0.5, 0.5, 12, 1, "Second")
        return deck

    def test_every_part_is_named_and_well_formed(self):
        data = self._deck().to_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            self.assertEqual(names[0], "[Content_Types].xml")
            self.assertIn("ppt/presentation.xml", names)
            self.assertIn("ppt/slides/slide2.xml", names)
            self.assertIn("ppt/media/image1.png", names)
            types = zf.read("[Content_Types].xml").decode("utf-8")
            for name in names:
                if name.endswith(".xml"):
                    ElementTree.fromstring(zf.read(name))  # well-formed
                    if not name.startswith("_rels") and name != "[Content_Types].xml":
                        self.assertIn('PartName="/%s"' % name, types, name)
            # Every relationship target is a part of the file.
            for name in names:
                if name.endswith(".rels"):
                    folder = posixpath.dirname(posixpath.dirname(name))
                    for match in re.finditer(r'Target="([^"]+)"', zf.read(name).decode("utf-8")):
                        target = posixpath.normpath(posixpath.join(folder, match.group(1)))
                        self.assertIn(target, names, (name, match.group(1)))

    def test_text_is_escaped_and_sized(self):
        data = self._deck().to_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            slide = ElementTree.fromstring(zf.read("ppt/slides/slide1.xml"))
        runs = slide.findall(".//a:r", NS)
        self.assertEqual(runs[0].find("a:t", NS).text, "Hello & <goodbye>")
        self.assertEqual(runs[0].find("a:rPr", NS).get("sz"), "2200")
        self.assertEqual(runs[0].find("a:rPr", NS).get("b"), "1")
        self.assertEqual(runs[1].find("a:rPr", NS).find("a:solidFill/a:srgbClr", NS).get("val"), "3D4FA3")
        self.assertIsNone(runs[2].find("a:rPr", NS).get("b"))
        pic = slide.find(".//p:pic", NS)
        self.assertEqual(pic.find(".//a:blip", NS).get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"), "rId2")

    def test_fitted_keeps_the_aspect_and_centers(self):
        x, y, w, h = pptx.fitted((1240, 871), (0.5, 1.9, 12.3, 5.0))
        self.assertAlmostEqual(w / h, 1240 / 871, places=6)
        self.assertAlmostEqual(h, 5.0)
        self.assertAlmostEqual(x + w / 2, 0.5 + 12.3 / 2)
        x, y, w, h = pptx.fitted((400, 100), (0.5, 1.9, 12.3, 5.0))
        self.assertAlmostEqual(w, 12.3)
        self.assertAlmostEqual(y + h / 2, 1.9 + 5.0 / 2)

    def test_the_same_deck_is_the_same_bytes(self):
        self.assertEqual(self._deck().to_bytes(), self._deck().to_bytes())

    def test_png_size_reads_the_header(self):
        self.assertEqual(pptx.png_size(_png(33, 7)), (33, 7))
        with self.assertRaises(ValueError):
            pptx.png_size(b"<svg/>")

    def test_wide_slide_size(self):
        data = self._deck().to_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            pres = ElementTree.fromstring(zf.read("ppt/presentation.xml"))
        size = pres.find("p:sldSz", NS)
        self.assertEqual((size.get("cx"), size.get("cy")), ("12192000", "6858000"))
        self.assertEqual(len(pres.findall("p:sldIdLst/p:sldId", NS)), 2)


class TestChoice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load(REPO_ROOT)
        cls.views = load_views(REPO_ROOT / "30_VIEWS")

    def test_nothing_named_is_the_whole_estate_then_every_product(self):
        chosen = choose(self.views, self.model, [])
        ids = [view.view_id for view, subject, _ in chosen if not subject]
        self.assertIn("system-context", ids)
        self.assertNotIn("product-architecture", ids)
        self.assertIn("change-register", ids)  # a report, drawn as a table
        products = [(subject, category) for view, subject, category in chosen if view.view_id == "product-architecture"]
        self.assertEqual(len(products), len(self.model.entities["products"]))
        self.assertTrue(all(category == "Products" for _, category in products))
        # Whole-estate views come first, in the rail's order; products after.
        first_product = next(i for i, (_, subject, _) in enumerate(chosen) if subject)
        self.assertTrue(all(not subject for _, subject, _ in chosen[:first_product]))

    def test_named_views_as_named_with_a_subject(self):
        chosen = choose(self.views, self.model, ["domain-servicing", "product-architecture:PRD-IDENTITY"])
        self.assertEqual([(v.view_id, s) for v, s, _ in chosen],
                         [("domain-servicing", ""), ("product-architecture", "PRD-IDENTITY")])

    def test_a_reader_file_is_read_by_its_suffix_without_a_flag(self):
        from terrane.quick import draw_sketch
        with tempfile.TemporaryDirectory() as tmp:
            written, notes = draw_sketch(REPO_ROOT / "90_EXAMPLE" / "quick" / "sample.puml", Path(tmp),
                                         date="2026-10-17")
            self.assertEqual([p.name for p in written], ["sample--imported.svg"])
            self.assertTrue(any("from the PlantUML" in n for n in notes), notes)

    def test_an_unknown_view_or_a_missing_subject_is_refused_with_the_list(self):
        with self.assertRaises(PackError) as caught:
            choose(self.views, self.model, ["no-such-view"])
        self.assertIn("system-context", str(caught.exception))
        with self.assertRaises(PackError) as caught:
            choose(self.views, self.model, ["product-architecture"])
        self.assertIn("product-architecture:ID", str(caught.exception))


@unittest.skipUnless(_has_browser(), "no browser or resvg-py on this machine")
class TestPack(unittest.TestCase):
    def test_four_views_make_a_deck_of_a_cover_a_contents_and_the_views(self):
        said = []
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "deck.pptx"
            path, slides = build_pack(REPO_ROOT, out,
                                      ["system-context", "domain-servicing", "product-architecture:PRD-IDENTITY",
                                       "change-roadmap"], date="2026-10-17", log=said.append)
            self.assertEqual(path, out)
            self.assertEqual(slides, 6)
            self.assertEqual(said, [])
            with zipfile.ZipFile(out) as zf:
                cover = zf.read("ppt/slides/slide1.xml").decode("utf-8")
                contents = zf.read("ppt/slides/slide2.xml").decode("utf-8")
                third = zf.read("ppt/slides/slide3.xml").decode("utf-8")
                last = zf.read("ppt/slides/slide6.xml").decode("utf-8")
                images = [n for n in zf.namelist() if n.startswith("ppt/media/")]
            self.assertIn("Architecture review pack", cover)
            self.assertIn("Validate: 0 errors", cover)
            self.assertIn("Generated 2026-10-17", cover)
            self.assertIn("3.  System Context", contents)
            self.assertIn("6.  Roadmap  (timeline)", contents)
            self.assertIn("5.  Customer Identity Service", contents)  # the subject by name, as the sheet says it
            self.assertIn("System Context", third)
            self.assertIn("diagram  ·  ", third)
            self.assertIn("system-context", third)
            self.assertIn("timeline  ·  ", last)
            self.assertEqual(len(images), 4)

    def test_many_shelves_stack_down_three_columns(self):
        from terrane.pack import Entry, _contents
        from terrane.pptx import Deck
        entries = [Entry("View %d" % i, "", b"", "", "Shelf %d" % (i % 8), "") for i in range(48)]
        deck = Deck("x")
        _contents(deck, entries)
        xml = deck.slides[0].xml()
        # Three columns of text, and the eighth shelf is on the page.
        self.assertEqual(xml.count("<p:sp>"), 4)
        self.assertIn("Shelf 7", xml)
        self.assertIn("50.  View 47", xml)

    def test_a_sketch_and_a_read_file_pack_a_deck_from_the_command(self):
        import io
        from contextlib import redirect_stdout
        from terrane import cli
        quick = REPO_ROOT / "90_EXAMPLE" / "quick"
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["draw", str(quick / "payments.yaml"), "--out", tmp, "--pack", "--date", "2026-10-17"])
            self.assertEqual(code, 0, out.getvalue())
            deck = Path(tmp) / "payments.pptx"
            self.assertTrue(deck.is_file(), out.getvalue())
            with zipfile.ZipFile(deck) as zf:
                slides = [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
                cover = zf.read("ppt/slides/slide1.xml").decode("utf-8")
            self.assertEqual(len(slides), 2 + 4)  # a cover, a contents page, four pictures
            self.assertIn("Card payments, sketched", cover)
            # A reader's file, by its suffix, into a deck named for it.
            with redirect_stdout(io.StringIO()):
                code = cli.main(["draw", str(quick / "sample.drawio"), "--out", tmp, "--pack",
                                 str(Path(tmp) / "drawn.pptx"), "--date", "2026-10-17"])
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "drawn.pptx").is_file())

    def test_a_register_is_one_slide_unless_every_row_is_asked_for(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, slides = build_pack(REPO_ROOT, Path(tmp) / "one.pptx", ["control-coverage"], date="2026-10-17")
            self.assertEqual(slides, 3)  # a cover, a contents page, the first page of rows
            with zipfile.ZipFile(path) as zf:
                third = zf.read("ppt/slides/slide3.xml").decode("utf-8")
            self.assertIn("rows 1\u20138 of", third)
            path, slides = build_pack(REPO_ROOT, Path(tmp) / "all.pptx", ["control-coverage"], date="2026-10-17",
                                      all_rows=True)
            self.assertGreater(slides, 20)
            with zipfile.ZipFile(path) as zf:
                contents = zf.read("ppt/slides/slide2.xml").decode("utf-8")
            self.assertIn("(2 of ", contents)

    def test_a_view_that_cannot_be_drawn_is_said_and_left_out(self):
        said = []
        with tempfile.TemporaryDirectory() as tmp:
            path, slides = build_pack(REPO_ROOT, Path(tmp) / "deck.pptx",
                                      ["product-architecture:PRD-NOT-HERE", "system-context"], date="2026-10-17",
                                      log=said.append)
            self.assertEqual(slides, 3)
            with zipfile.ZipFile(path) as zf:
                contents = zf.read("ppt/slides/slide2.xml").decode("utf-8")
            # Numbered as the deck is, not as it was meant to be.
            self.assertIn("3.  System Context", contents)
        self.assertEqual(len(said), 1)
        self.assertIn("PRD-NOT-HERE", said[0])
        self.assertIn("left out", said[0])


if __name__ == "__main__":
    unittest.main()
