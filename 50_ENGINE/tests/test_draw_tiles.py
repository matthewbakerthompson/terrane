"""The Python tile map held equal to the app's.

The app is the spec for a map with nothing connected: `fixtures/tiles/*.json`
is every box of the eleven tile maps as the running app laid them out, read
back from the page by `80_APP/tools/dev/layout_fixture.py` -- each band,
card, grid and tile with its class, its id, its text and the lines the
browser broke that text into, and the host's width and padding. The app
draws these as HTML, so the geometry is the stylesheet's: `terrane.draw.tiles`
does that arithmetic for the same payload at the same width and must put
every box on the same pixel.

The tolerance is a sixteenth of a pixel. Chrome lays out in 1/64 px units
and, when an `fr` division does not come out even, hands the remainder to
the first columns a unit each, so a box in the fifth column of a grid can
sit 4/64 px from the float division; nothing else is allowed. The lines are
held exactly, since a name breaking one word earlier moves every box under
it by a line's height: Chrome's greedy breaking for a tile, and for a card's
name its `text-wrap: balance`, which is a score over the break opportunities
with a penalty on a lone last word where the name has three or more places
to break, and a bisection to the pixel where it has fewer.
"""

from __future__ import annotations

import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.draw import TileLayout, default_metrics, drawing_mode, layout_tiles, render_svg  # noqa: E402
from terrane.draw.tiles import (CARD_NAME, EXPORT_PADDING, TILE_NAME, balance_lines, border_px, break_lines,  # noqa: E402
                            clamp_lines, columns, tile_meta)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tiles"
REPO = Path(__file__).resolve().parents[2]
WEB = REPO / "80_APP" / "web"
#: Chrome's 1/64 px units, and the remainder of a division handed to the
#: first columns one unit each.
TOL = 1 / 16


def _fixtures():
    return sorted(FIXTURES.glob("*.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _layout(fixture: dict) -> TileLayout:
    return layout_tiles(fixture["payload"], fixture["host"]["clientWidth"], padding=tuple(fixture["host"]["padding"]))


def _items(fixture: dict, cls: str):
    """The page's elements of one class, in document order."""
    return [item for item in fixture["items"] if item["cls"].split()[0] == cls]


def _icon(served: str):
    path = WEB / served
    return path.read_bytes() if served and path.is_file() else None


class TestLayoutEqualsApp(unittest.TestCase):
    def assertBox(self, ours, theirs, what: str) -> None:
        for name, a, b in zip("xywh", ours, theirs):
            self.assertAlmostEqual(a, b, delta=TOL, msg="%s %s: ours %.4f app %.4f" % (what, name, a, b))

    def test_fixtures_exist(self) -> None:
        # Twelve: the six framework and domain maps retired when the whole
        # map and the one framework landscape took their place keep their
        # fixtures, which are still the app's geometry for six shapes of
        # tile map that an estate's own views can draw.
        self.assertEqual(len(_fixtures()), 12, "twelve tile maps; run 80_APP/tools/dev/layout_fixture.py")

    def test_the_app_drew_every_fixture_as_tiles_in_geist(self) -> None:
        for path in _fixtures():
            fixture = _load(path)
            with self.subTest(view=fixture["view"]):
                self.assertTrue(fixture["tiles"])
                self.assertTrue(fixture["geist"], "the page was measured before its face loaded")
                self.assertEqual(drawing_mode(fixture["payload"]).kind, "tiles")

    def test_every_tile_sits_where_the_app_put_it(self) -> None:
        """Box, border, the name's lines and box, the technology line."""
        for path in _fixtures():
            fixture = _load(path)
            lay = _layout(fixture)
            tiles = lay.all_tiles()
            app_tiles = _items(fixture, "tile")
            app_names = _items(fixture, "tile-name")
            app_techs = iter(_items(fixture, "tile-sub"))
            with self.subTest(view=fixture["view"]):
                self.assertEqual([t.id for t in tiles], [a["id"] for a in app_tiles], "the tiles, in the page's order")
                for tile, app, name in zip(tiles, app_tiles, app_names):
                    self.assertBox((tile.x, tile.y, tile.w, tile.h), app["box"], tile.id)
                    self.assertEqual(tile.border, app["border"][0], tile.id)
                    # The page keeps the lines past the clamp, hidden; the
                    # painter shows two, the second ending in an ellipsis.
                    if len(name["lines"]) > 2:
                        self.assertEqual(tile.name.lines[0], name["lines"][0], tile.id)
                        self.assertTrue(tile.name.lines[1].endswith("…"), tile.id)
                    else:
                        self.assertEqual(tile.name.lines, name["lines"], tile.id)
                    self.assertBox((tile.name.x, tile.name.y, tile.name.w, tile.name.h), name["box"], tile.id + " name")
                    if tile.tech:
                        tech = next(app_techs)
                        self.assertEqual(tile.tech.lines, [tech["text"]], tile.id)
                        self.assertBox((tile.tech.x, tile.tech.y, tile.tech.w, tile.tech.h), tech["box"],
                                       tile.id + " tech")

    def test_every_card_is_the_apps(self) -> None:
        """Box, the name's balanced lines and box, the count's box."""
        for path in _fixtures():
            fixture = _load(path)
            lay = _layout(fixture)
            cards = lay.all_cards()
            with self.subTest(view=fixture["view"]):
                app_cards = _items(fixture, "tcard")
                self.assertEqual(len(cards), len(app_cards))
                for card, app, name, count in zip(cards, app_cards, _items(fixture, "tcard-name"),
                                                  _items(fixture, "tcard-n")):
                    self.assertBox((card.x, card.y, card.w, card.h), app["box"], card.id)
                    self.assertEqual(card.name.lines, name["lines"], card.id)
                    self.assertBox((card.name.x, card.name.y, card.name.w, card.name.h), name["box"], card.id + " name")
                    self.assertEqual(card.count.lines, [count["text"]], card.id)
                    self.assertBox((card.count.x, card.count.y, card.count.w, card.count.h), count["box"],
                                   card.id + " count")

    def test_every_band_is_the_apps(self) -> None:
        for path in _fixtures():
            fixture = _load(path)
            lay = _layout(fixture)
            with self.subTest(view=fixture["view"]):
                app_bands = _items(fixture, "tband")
                self.assertEqual(len(lay.bands), len(app_bands))
                for band, app in zip(lay.bands, app_bands):
                    self.assertBox((band.x, band.y, band.w, band.h), app["box"], band.id)
                    self.assertEqual(band.first, app["border"][0] == 0, band.id)
                for cls, part in (("tband-name", "name"), ("tband-gloss", "gloss"), ("tband-n", "count")):
                    texts = [getattr(b, part) for b in lay.bands if getattr(b, part)]
                    apps = _items(fixture, cls)
                    self.assertEqual(len(texts), len(apps), cls)
                    for ours, theirs in zip(texts, apps):
                        self.assertBox((ours.x, ours.y, ours.w, ours.h), theirs["box"], cls)
                        if theirs.get("lines"):
                            self.assertEqual(ours.lines, theirs["lines"], cls)
                        else:
                            self.assertEqual(ours.lines, [theirs["text"]], cls)

    def test_every_grid_is_the_apps(self) -> None:
        for path in _fixtures():
            fixture = _load(path)
            lay = _layout(fixture)
            with self.subTest(view=fixture["view"]):
                grids = lay.all_grids()
                app_grids = _items(fixture, "tgrid")
                self.assertEqual(len(grids), len(app_grids))
                for grid, app in zip(grids, app_grids):
                    self.assertBox((grid.x, grid.y, grid.w, grid.h), app["box"], "grid")
                    self.assertEqual(grid.listed, "is-list" in app["cls"])

    def test_the_host_is_as_tall_as_the_page_scrolls(self) -> None:
        """Where the map outgrows the window, the page's scroll height is
        the layout's height, to the whole pixel the page reports."""
        for path in _fixtures():
            fixture = _load(path)
            host = fixture["host"]
            if host["scrollHeight"] <= host["clientHeight"]:
                continue
            with self.subTest(view=fixture["view"]):
                self.assertAlmostEqual(_layout(fixture).height, host["scrollHeight"], delta=1)

    def test_the_page_was_wide_enough_to_mean_something(self) -> None:
        """Every fixture was captured at the app's default sheet width, so
        the committed fixtures and the default drawing agree."""
        for path in _fixtures():
            self.assertEqual(_load(path)["host"]["clientWidth"], 1240, path.name)


class TestChromesRules(unittest.TestCase):
    """The pieces of the stylesheet's arithmetic that are not obvious."""

    def test_a_fractional_border_snaps_to_whole_pixels(self) -> None:
        # The palette's 1.0, 1.4 and 2.6 become --tw 1px, 1.25px and 2px;
        # Chrome draws 1, 1 and 2.
        self.assertEqual([border_px(w) for w in (1.0, 1.4, 2.6, 2.0, 0.5)], [1, 1, 2, 1, 1])

    def test_auto_fill_columns(self) -> None:
        self.assertEqual(columns(1200, 198, 10), (5, 232))
        self.assertEqual(columns(1048, 172, 7), (5, 204))
        self.assertEqual(columns(212, 200, 10), (1, 212))
        self.assertEqual(columns(100, 172, 7), (1, 100))

    def test_greedy_breaking_does_not_break_at_a_slash(self) -> None:
        m = default_metrics()
        self.assertEqual(break_lines(m, "Identity Verification & KYC/CIP", 161.6, TILE_NAME),
                         ["Identity Verification &", "KYC/CIP"])
        # A hyphen before a letter is one: the BIAN tile is 172 inside.
        self.assertEqual(break_lines(m, "Fraud Loss Recovery & Write-off", 172, TILE_NAME),
                         ["Fraud Loss Recovery & Write-", "off"])

    def test_a_long_name_is_clamped_to_two_lines_with_an_ellipsis(self) -> None:
        m = default_metrics()
        lines = break_lines(m, "Manage application configuration and feature flags", 172.16, TILE_NAME, anywhere=True)
        self.assertEqual(len(lines), 3)
        shown = clamp_lines(m, lines, 172.16, TILE_NAME)
        self.assertEqual(len(shown), 2)
        self.assertTrue(shown[1].endswith("…"))

    def test_balance_penalizes_a_lone_last_word(self) -> None:
        """With three or more places to break, Chrome scores the breaks and
        a single word on the last line costs as much as a line, so the
        less even split wins where it keeps the last line long."""
        m = default_metrics()
        self.assertEqual(balance_lines(m, "Data & Analytics Management", 162.984, CARD_NAME),
                         ["Data &", "Analytics Management"])
        self.assertEqual(balance_lines(m, "11.0 Manage External Relationships", 193.390625, CARD_NAME),
                         ["11.0 Manage", "External Relationships"])
        self.assertEqual(balance_lines(m, "1.0 Develop Vision and Strategy", 193.390625, CARD_NAME),
                         ["1.0 Develop Vision", "and Strategy"])

    def test_balance_bisects_where_there_are_two_places_to_break(self) -> None:
        """The bisection stops a pixel short, so which of two breaks a hair
        apart it lands on depends on the width it started from."""
        m = default_metrics()
        self.assertEqual(balance_lines(m, "Regulations and Compliance", 166.796875, CARD_NAME),
                         ["Regulations and", "Compliance"])
        self.assertEqual(balance_lines(m, "Regulations and Compliance", 163, CARD_NAME),
                         ["Regulations", "and Compliance"])

    def test_tile_meta_is_the_stage_heads(self) -> None:
        fixture = _load(FIXTURES / "capability-map.json")
        self.assertEqual(tile_meta(fixture["payload"]), "136 capabilities · 22 groups")


class TestPainter(unittest.TestCase):
    def test_svg_is_well_formed_and_carries_everything(self) -> None:
        ns = {"svg": "http://www.w3.org/2000/svg"}
        for path in _fixtures():
            fixture = _load(path)
            payload = fixture["payload"]
            with self.subTest(view=fixture["view"]):
                svg = render_svg(payload, icon_loader=_icon, font_url_prefix="/fonts/")
                root = ET.fromstring(svg)
                self.assertEqual(root.get("data-layout"), "tiles")
                tiles = root.findall(".//svg:g[@class='tile']", ns)
                self.assertEqual(len(tiles), payload["counts"]["nodes"])
                self.assertEqual({t.get("data-id") for t in tiles},
                                 {e["data"]["id"] for e in payload["elements"] if not e["data"].get("isGroup")})
                groups = sum(1 for e in payload["elements"] if e["data"].get("isGroup"))
                bands = root.findall(".//svg:g[@class='band']", ns)
                cards = root.findall(".//svg:g[@class='card']", ns)
                self.assertEqual(len(bands) + len(cards), groups)
                self.assertIn(payload["title"], svg)
                self.assertIn(payload["legend"]["types"][0]["label"], svg)
                self.assertIn(tile_meta(payload), svg)

    def test_same_bytes_twice(self) -> None:
        fixture = _load(_fixtures()[0])
        self.assertEqual(render_svg(fixture["payload"], icon_loader=_icon), render_svg(fixture["payload"], icon_loader=_icon))

    def test_the_plain_drawing_is_the_apps_export(self) -> None:
        """Without the sheet, the picture is the host as the PNG button
        clones it: the sheet's width, the export's padding, no title block."""
        fixture = _load(FIXTURES / "capability-map.json")
        lay = layout_tiles(fixture["payload"], 1240)
        self.assertEqual(lay.padding, EXPORT_PADDING)
        svg = render_svg(fixture["payload"], sheet=False)
        root = ET.fromstring(svg)
        self.assertEqual(float(root.get("width")), 1240)
        self.assertAlmostEqual(float(root.get("height")), lay.height, places=2)
        self.assertNotIn('class="head"', svg)
        self.assertNotIn("Generated from the model", svg)

    def test_the_map_wraps_to_the_sheets_width(self) -> None:
        payload = _load(FIXTURES / "capability-domains.json")["payload"]
        self.assertGreater(layout_tiles(payload, 900).height, layout_tiles(payload, 1240).height)
        self.assertGreater(len(ET.fromstring(render_svg(payload, sheet_width=900)).findall(".//*[@data-id]")), 0)


if __name__ == "__main__":
    unittest.main()
