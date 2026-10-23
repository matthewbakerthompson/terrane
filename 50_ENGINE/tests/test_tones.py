"""The app's two tones, Stone and Graphite, each a whole diagram palette.

What has to hold: every entity type has a hue of its own in every tone, so a
type the tones forgot cannot draw as an anonymous gray box; the text on every
fill is readable at the deepest tint an ordinal value gives it; classic, which
every export is drawn in unless an estate says otherwise, did not move; an
estate picks its base and overrides a bucket in every tone or in one; and the
server draws in the tone the page asks for, which is what makes the boxes on a
drawing and the swatch beside its layer agree.
"""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import schema  # noqa: E402
from terrane.palette import (BASES, NAMED, ORDINAL, TONES, TYPE_SWATCHES, Palette, _mix,  # noqa: E402
                         boundary_style)
from terrane.schema import ENTITY_TYPES  # noqa: E402

from _fixture import REPO  # noqa: E402


def _luminance(color: str) -> float:
    def channel(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    color = color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TestTheBases(unittest.TestCase):
    def test_the_app_s_tones_are_bases(self) -> None:
        self.assertEqual(TONES, ("stone", "graphite"))
        for tone in TONES:
            self.assertIn(tone, BASES)

    def test_every_entity_type_has_a_hue_in_every_tone(self) -> None:
        for tone in ("classic",) + TONES:
            types = BASES[tone].types
            for name in ENTITY_TYPES:
                with self.subTest(tone=tone, entity=name):
                    self.assertIn(name, types)

    def test_no_two_types_share_a_stroke_in_a_tone(self) -> None:
        """Hue is the entity type. Two types on one stroke is a legend with
        two rows the same color; the tones were drawn to avoid it, and this
        keeps the next edit honest."""
        for tone in TONES:
            strokes = [s.stroke for name, s in BASES[tone].types.items() if name != "default"]
            with self.subTest(tone=tone):
                self.assertEqual(len(strokes), len(set(strokes)))

    def test_the_text_on_every_fill_is_readable_at_its_deepest_tint(self) -> None:
        """An ordinal value pulls the fill toward the stroke; the strongest
        pulls furthest. The names on those boxes have to stay readable, which
        WCAG puts at 4.5 to 1 for text this size."""
        for tone in TONES:
            base = BASES[tone]
            for name, swatch in base.types.items():
                deepest = _mix(swatch.fill, swatch.stroke, 0.34)
                with self.subTest(tone=tone, entity=name):
                    self.assertGreaterEqual(_contrast(swatch.ink, swatch.fill), 4.5)
                    self.assertGreaterEqual(_contrast(swatch.ink, deepest), 4.5)

    def test_every_enumerated_value_has_a_deliberate_color_in_every_tone(self) -> None:
        enums = (
            schema.STATUS, schema.CRITICALITY, schema.DOMAINS, schema.LAYERS,
            schema.ABSTRACTION, schema.CLASSIFICATION, schema.ENVIRONMENT,
            schema.TIER, schema.INTEGRATION_STYLES, schema.ACTOR_KINDS,
            schema.CLOUD_PROVIDERS, schema.NETWORK_ZONES, schema.RESILIENCE,
        )
        for tone in TONES:
            palette = Palette(None, tone)
            for values in enums:
                with self.subTest(tone=tone, values=values[0]):
                    for value in values:
                        self.assertIn(value, palette.named, value)
                    strokes = [palette.named[v].stroke for v in values]
                    self.assertEqual(len(strokes), len(set(strokes)), values)

    def test_an_ordinal_value_still_deepens_in_a_tone(self) -> None:
        for tone in TONES:
            palette = Palette(None, tone)
            high, low = (palette.node_style("systems", "criticality", v) for v in ORDINAL["criticality"][::2])
            with self.subTest(tone=tone):
                self.assertGreater(high.width, low.width)
                self.assertNotEqual(high.fill, low.fill)


class TestClassicDidNotMove(unittest.TestCase):
    """Every committed picture under 70_ARTIFACTS is drawn in classic. A
    tone that leaked into it would rewrite seven hundred files."""

    def test_no_tone_and_no_base_is_classic(self) -> None:
        palette = Palette()
        self.assertEqual(palette.tone, "classic")
        self.assertEqual(palette.types, TYPE_SWATCHES)
        self.assertEqual(palette.named, NAMED)

    def test_a_plain_boundary_is_drawn_the_same_with_or_without_the_palette(self) -> None:
        for depth in (1, 2, 3, 4):
            self.assertEqual(boundary_style("company_domain", "Lending", "", depth),
                             boundary_style("company_domain", "Lending", "", depth, palette=Palette()))

    def test_a_provider_s_box_is_the_provider_s_in_every_tone(self) -> None:
        classic = boundary_style("region", "eu-west-2", "AWS")
        for tone in TONES:
            self.assertEqual(boundary_style("region", "eu-west-2", "AWS", 1, palette=Palette(None, tone)), classic)

    def test_a_tone_s_plain_boundary_is_its_own(self) -> None:
        stone = boundary_style("company_domain", "Lending", "", 1, palette=Palette(None, "stone"))
        self.assertEqual(stone.fill, BASES["stone"].depth_fills[0])
        self.assertEqual(stone.stroke, BASES["stone"].boundary_stroke)


class TestTheEstateChooses(unittest.TestCase):
    def test_the_estate_names_its_base(self) -> None:
        self.assertEqual(Palette({"base": "graphite"}).tone, "graphite")
        self.assertEqual(Palette({"base": "no-such-tone"}).tone, "classic")

    def test_the_tone_asked_for_wins_over_the_base(self) -> None:
        self.assertEqual(Palette({"base": "graphite"}, "stone").tone, "stone")
        self.assertEqual(Palette({"base": "graphite"}, "no-such-tone").tone, "graphite")

    def test_a_bucket_at_the_top_applies_in_every_tone(self) -> None:
        config = {"systems": {"fill": "#eeeeee", "stroke": "#123456"}}
        for tone in (None,) + TONES:
            with self.subTest(tone=tone):
                self.assertEqual(Palette(config, tone).type_swatch("systems").stroke, "#123456")

    def test_a_section_named_for_a_tone_applies_in_that_tone_alone(self) -> None:
        config = {"systems": {"fill": "#eeeeee", "stroke": "#123456"},
                  "graphite": {"systems": {"fill": "#dddddd", "stroke": "#654321"}}}
        self.assertEqual(Palette(config, "graphite").type_swatch("systems").stroke, "#654321")
        self.assertEqual(Palette(config, "stone").type_swatch("systems").stroke, "#123456")
        # Its ink defaults to the tone's, not classic's slate.
        self.assertEqual(Palette(config, "graphite").type_swatch("systems").ink, BASES["graphite"].ink)


class TestTheServerDrawsInTheTone(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = REPO
        cls.server = server_module

    def _system_fill(self, payload: dict) -> str:
        node = next(e["data"] for e in payload["elements"]
                    if e["data"].get("entityType") == "systems" and e["data"].get("styleKey") == "Medium")
        return node["fill"]

    def test_a_drawing_comes_in_the_tone_asked_for(self) -> None:
        expected = {tone: Palette(None, tone).node_style("systems", "criticality", "Medium").fill for tone in TONES}
        for tone in TONES:
            payload = self.server.api_graph({"view": ["application-landscape"], "tone": [tone]}, None)
            with self.subTest(tone=tone):
                self.assertEqual(self._system_fill(payload), expected[tone])

    def test_a_drawing_with_no_tone_is_the_estate_s_own(self) -> None:
        payload = self.server.api_graph({"view": ["application-landscape"]}, None)
        estate = Palette(self.server._load_all()[0].config.get("palette"))
        self.assertEqual(self._system_fill(payload), estate.node_style("systems", "criticality", "Medium").fill)

    def test_the_overview_says_the_tones_and_carries_their_swatches(self) -> None:
        for tone in TONES:
            overview = self.server.api_overview({"tone": [tone]}, None)
            with self.subTest(tone=tone):
                self.assertEqual(overview["tones"], list(TONES))
                self.assertIn(overview["tone"], TONES)
                self.assertEqual(overview["swatches"]["systems"]["stroke"], BASES[tone].types["systems"].stroke)
                for view in overview["views"]:
                    if view["ok"]:
                        self.assertEqual(sum(view["types"].values()), view["nodes"], view["viewId"])

    def test_a_flow_s_heads_are_the_systems_of_the_tone(self) -> None:
        for tone in TONES:
            flows = self.server.api_flows({"tone": [tone]}, None)
            self.assertEqual(flows["swatch"]["fill"], BASES[tone].types["systems"].fill)


if __name__ == "__main__":
    unittest.main()
