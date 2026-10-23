"""The timeline and the flows drawn from Python.

A timeline is a grid of quarters, the way the app draws it; a flow is a
sequence diagram, the way the Mermaid has always said it. The tests hold
what a picture of either must get right without eyes: a bar per dated
thing and a chip per system it reaches, the current quarter marked only
when a day is given; a participant per system a flow touches and the
actor that starts it, a message per hop in the flow's order with its
number, a reply only where the interface answers; well-formed, the same
bytes twice, and written by `terrane render` beside the Mermaid with the pages
and the index pointing at them.
"""

from __future__ import annotations

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
from terrane.draw import render_sequence_svg, render_timeline_svg  # noqa: E402
from terrane.draw.timeline import quarter_index, quarter_label, quarter_of_day  # noqa: E402
from terrane.icons import IconMap, web_dir  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.payload import graph_payload  # noqa: E402
from terrane.query import resolve  # noqa: E402
from terrane.render_sequence import all_flows, participants, steps_for  # noqa: E402

from _fixture import REPO, seeded_model, seeded_root, seeded_views, setup_shared, teardown_shared  # noqa: E402


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _roadmap_payload():
    root = seeded_root()
    model = seeded_model()
    view = next(v for v in seeded_views() if v.kind == "timeline")
    web = web_dir(root)
    icons = IconMap(web if web else REPO / "80_APP" / "web")
    return graph_payload(model, view, Palette(model.config.get("palette")), icons, load_components(root),
                         graph=resolve(model, view)), model


class TestQuarters(unittest.TestCase):
    def test_quarters_count_and_say_themselves(self) -> None:
        self.assertEqual(quarter_index("2026-Q3"), 2026 * 4 + 2)
        self.assertEqual(quarter_label(2026 * 4 + 2), "2026 Q3")
        self.assertIsNone(quarter_index("2026-03"))
        self.assertIsNone(quarter_index(""))
        self.assertEqual(quarter_of_day("2026-10-17"), 2026 * 4 + 3)
        self.assertIsNone(quarter_of_day("soon"))


class TestTimeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload, cls.model = _roadmap_payload()
        cls.svg = render_timeline_svg(cls.payload, model_name="Test")
        cls.root = ET.fromstring(cls.svg)

    def test_a_bar_per_dated_thing_and_a_chip_per_system_reached(self) -> None:
        dated = [e["data"] for e in self.payload["elements"]
                 if not e["data"].get("source") and not e["data"].get("isGroup")
                 and quarter_index(e["data"].get("start")) is not None]
        bars = [el for el in self.root.iter() if el.get("class") == "bar"]
        self.assertEqual(len(bars), len(dated))
        self.assertEqual({b.get("data-id") for b in bars}, {d["id"] for d in dated})
        chips = [el for el in self.root.iter() if el.get("class") == "chip"]
        self.assertTrue(chips)
        # A chip is a system an edge reaches from a bar, never a bar.
        self.assertFalse({c.get("data-id") for c in chips} & {d["id"] for d in dated})

    def test_the_sheet_says_what_it_is(self) -> None:
        self.assertEqual(self.root.get("data-layout"), "timeline")
        self.assertIn(self.payload["title"], self.svg)
        self.assertIn("work packages", self.svg)
        self.assertIn("Planned", self.svg)

    def test_the_current_quarter_is_marked_only_when_a_day_is_given(self) -> None:
        self.assertNotIn("this quarter", self.svg)
        dated = render_timeline_svg(self.payload, model_name="Test", date="2026-10-17")
        self.assertIn("this quarter", dated)
        self.assertIn("2026-10-17", dated)

    def test_same_bytes_twice(self) -> None:
        self.assertEqual(self.svg, render_timeline_svg(self.payload, model_name="Test"))

    def test_nothing_dated_says_so(self) -> None:
        bare = dict(self.payload)
        bare["elements"] = [e for e in self.payload["elements"] if e["data"].get("isGroup")]
        svg = render_timeline_svg(bare, model_name="Test")
        self.assertIn("nothing to place", svg)
        ET.fromstring(svg)


class TestSequence(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.palette = Palette(cls.model.config.get("palette"))

    def test_every_flow_draws_its_participants_and_hops(self) -> None:
        for flow_id in all_flows(self.model):
            with self.subTest(flow=flow_id):
                svg = render_sequence_svg(self.model, flow_id, self.palette, model_name="Test")
                root = ET.fromstring(svg)
                self.assertEqual(root.get("data-layout"), "sequence")
                steps = steps_for(self.model, flow_id)
                systems = participants(self.model, steps)
                drawn = [el for el in root.iter() if el.get("class") == "participant"]
                drawn_systems = [el for el in drawn if el.get("data-type") == "systems"]
                self.assertEqual([el.get("data-id") for el in drawn_systems], systems)
                actors = [el for el in drawn if el.get("data-type") == "actors"]
                self.assertLessEqual(len(actors), 1)
                messages = [el for el in root.iter() if el.get("class") == "message"]
                hops = [el for el in messages if el.get("data-kind") in ("call", "event") and el.get("data-interface")]
                self.assertEqual([el.get("data-interface") for el in hops],
                                 [str(s["interface"]["interface_id"]) for s in steps])
                replies = [el for el in messages if el.get("data-kind") == "reply"]
                answering = [s for s in steps
                             if str(s["interface"].get("integration_style") or "Request-response") == "Request-response"]
                self.assertEqual(len(replies), len(answering))
                # The trigger from the actor is the one call with no interface.
                triggers = [el for el in messages if el.get("data-kind") == "call" and not el.get("data-interface")]
                self.assertEqual(len(triggers), len(actors))
                self.assertEqual(svg, render_sequence_svg(self.model, flow_id, self.palette, model_name="Test"))

    def test_a_flow_with_no_steps_says_so(self) -> None:
        flow_id = all_flows(self.model)[0]
        kept = self.model.relations["flow_step"]
        self.model.relations["flow_step"] = [r for r in kept if str(r.get("flow_id")) != flow_id]
        try:
            svg = render_sequence_svg(self.model, flow_id, self.palette, model_name="Test")
        finally:
            self.model.relations["flow_step"] = kept
        self.assertIn("nothing to sequence", svg)
        ET.fromstring(svg)


class TestRenderWritesThem(unittest.TestCase):
    def test_the_timeline_and_the_flows_land_beside_the_mermaid(self) -> None:
        root = seeded_root()
        out = Path(tempfile.mkdtemp(prefix="aac-tl-"))
        timeline = next(v for v in seeded_views() if v.kind == "timeline")
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["--root", str(root), "render", "--out", str(out), "--view", timeline.view_id])
        self.assertEqual(code, 0, text.getvalue())
        self.assertTrue((out / "svg" / ("%s.svg" % timeline.view_id)).is_file())
        page = (out / "docs" / ("%s.md" % timeline.view_id)).read_text(encoding="utf-8")
        self.assertIn("](../svg/%s.svg)" % timeline.view_id, page)
        index = (out / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("| [SVG](svg/%s.svg) |" % timeline.view_id, index)
        for flow_id in all_flows(seeded_model()):
            self.assertTrue((out / "svg" / ("%s.svg" % flow_id)).is_file(), flow_id)
            self.assertIn("](../svg/%s.svg)" % flow_id, (out / "docs" / ("%s.md" % flow_id)).read_text(encoding="utf-8"))
            self.assertIn("[SVG](svg/%s.svg)" % flow_id, index)


if __name__ == "__main__":
    unittest.main()
