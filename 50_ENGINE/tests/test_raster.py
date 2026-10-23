"""A PNG with nothing installed: the drawing shot through a browser on the
machine, or resvg-py where that is what there is.

The tests hold that a sheet comes back as a PNG of twice its size, that a
picture saves itself as PNG by its suffix, and that `terrane draw --png` writes
one beside each SVG and says what it went through. Where the machine has
neither a browser nor resvg-py they are skipped with the refusal's words,
which are the words a person gets.
"""

from __future__ import annotations

import io
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import terrane  # noqa: E402
from terrane import cli  # noqa: E402
from terrane.draw.raster import NoRasterizer, open_rasterizer  # noqa: E402
from terrane.quick import EXAMPLE  # noqa: E402

PNG_HEAD = b"\x89PNG\r\n\x1a\n"


def _png_size(data: bytes):
    assert data[:8] == PNG_HEAD, data[:8]
    return struct.unpack(">II", data[16:24])


class TestRaster(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.shoot = open_rasterizer()
        except NoRasterizer as exc:
            raise unittest.SkipTest(str(exc))
        cls.picture = terrane.diagrams(EXAMPLE)["payments-by-hosting"]

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "shoot"):
            cls.shoot.close()

    def test_the_sheet_is_shot_at_twice_its_size(self) -> None:
        png = self.shoot(self.picture.svg)
        box = [float(v) for v in ET.fromstring(self.picture.svg).get("viewBox").split()]
        width, height = _png_size(png)
        self.assertAlmostEqual(width, box[2] * 2, delta=2)
        self.assertAlmostEqual(height, box[3] * 2, delta=2)

    def test_a_picture_saves_itself_as_png_by_its_suffix(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-png-"))
        path = self.picture.save(folder / "hosting.png")
        self.assertTrue(path.read_bytes().startswith(PNG_HEAD))
        svg = self.picture.save(folder / "hosting.svg")
        self.assertTrue(svg.read_text(encoding="utf-8").startswith("<svg"))

    def test_the_command_writes_a_png_beside_each_svg_and_says_how(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-png-"))
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["draw", str(EXAMPLE), "--out", str(out), "--png"])
        self.assertEqual(code, 0, text.getvalue())
        self.assertIn("PNG through %s" % self.shoot.means, text.getvalue())
        for name in ("payments--payments-by-hosting", "payments--FLOW-AUTH"):
            self.assertTrue((out / (name + ".svg")).is_file(), name)
            self.assertTrue((out / (name + ".png")).read_bytes().startswith(PNG_HEAD), name)


class TestSharedRasterizer(unittest.TestCase):
    def test_one_rasterizer_per_scale_kept_across_runs(self) -> None:
        from terrane.draw.raster import NoRasterizer, SharedRasterizer, open_rasterizer

        try:
            first = open_rasterizer()
        except NoRasterizer:
            self.skipTest("no way to make a PNG on this machine")
        self.assertIsInstance(first, SharedRasterizer)
        self.assertIs(open_rasterizer(), first)
        self.assertIsNot(open_rasterizer(scale=1.0), first)
        # Closing is a courtesy: the one the process keeps is handed out again.
        first.close()
        self.assertIs(open_rasterizer(), first)


if __name__ == "__main__":
    unittest.main()
