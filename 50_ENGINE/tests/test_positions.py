"""Tests for a diagram arranged by hand (`positions` on a view, terrane.draw.arranged).

What is checked: a view's positions are read as whole-pixel corners keyed
by where a thing sits, and a value that is not two numbers is refused
rather than drawn somewhere; they are the diagram's own, kept through the
merge with the view it places and never taken from it; the schema admits
them; the payload carries them only for a diagram that has some. Then the
arrangement: what a drawing keeps the moment it is arranged puts every box
back within half a pixel; one box moved moves that box alone, and a
boundary moved moves what is in it; a system placed on an arranged
diagram -- laid out afresh, a second system turned two zones side by
side into one above the other -- moves nothing already there and goes where
there is room in its boundary; a box whose boundary changed has no place
kept in the new one; the SVG draws the arrangement and says so. Last, the
file: positions written last and in key order, one line changed when one
box moves, and a key a reader would take apart quoted.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import jsonschema, places, yamlish  # noqa: E402
from terrane.blocks import load_components  # noqa: E402
from terrane.draw import arranged  # noqa: E402
from terrane.draw.layered import layout_layered  # noqa: E402
from terrane.draw.packed import prepare  # noqa: E402
from terrane.draw.svg import render_svg  # noqa: E402
from terrane.icons import IconMap, web_dir  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.payload import graph_payload  # noqa: E402
from terrane.query import ViewError, load_views, parse_view, position_key  # noqa: E402
from terrane.sketch import dump_yaml  # noqa: E402

from _fixture import REPO, Sandbox, seeded_model, seeded_root, setup_shared, teardown_shared  # noqa: E402

NETWORK = (REPO / "30_VIEWS" / "network-topology.view.yaml").read_text(encoding="utf-8")

#: A diagram as the canvas writes one: one account of Network Topology
#: placed, a system of the lending account pinned to it.
DIAGRAM = {
    "view_id": "lending-onboarding", "title": "Lending onboarding", "category": "Application", "kind": "diagram",
    "places": [{"view": "network-topology", "only": {"cloud_account": ["prod-lending"]}}],
    "scope": {"pin": ["SYS-LENDING-API"]}, "edges": [{"via": "interfaces"}],
}

#: Where the lending API sits on that diagram, and so its key.
API = "AWS / prod-lending / eu-west-2 / SYS-LENDING-API"


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestReading(unittest.TestCase):
    def test_positions_are_whole_pixel_corners_by_key(self) -> None:
        view = parse_view(dict(DIAGRAM, positions={API: [12, 40.4], "AWS": [0, -8]}))
        self.assertEqual(view.positions, {API: (12, 40), "AWS": (0, -8)})
        self.assertEqual(parse_view(DIAGRAM).positions, {})
        self.assertEqual(position_key(("AWS", "prod-lending"), "SYS-X"), "AWS / prod-lending / SYS-X")
        self.assertEqual(position_key(("AWS", "prod-lending")), "AWS / prod-lending")

    def test_a_position_that_is_not_two_numbers_is_refused(self) -> None:
        for wrong in ([1, 2, 3], [1], "1, 2", [True, 2], ["a", 2], None):
            with self.subTest(value=wrong), self.assertRaises(ViewError) as caught:
                parse_view(dict(DIAGRAM, positions={API: wrong}))
            self.assertIn("should be [x, y]", str(caught.exception))
        with self.assertRaises(ViewError):
            parse_view(dict(DIAGRAM, positions=[[API, 1, 2]]))

    def test_the_schema_admits_positions_and_refuses_a_bad_one(self) -> None:
        try:
            import jsonschema as validator  # the third-party package, not aac's
        except ImportError:
            self.skipTest("no JSON Schema validator installed")
        if not hasattr(validator, "Draft202012Validator"):
            self.skipTest("the installed validator predates draft 2020-12")
        check = validator.Draft202012Validator(jsonschema.view_schema())
        self.assertEqual([e.message for e in check.iter_errors(dict(DIAGRAM, positions={API: [1, 2]}))], [])
        self.assertTrue(list(check.iter_errors(dict(DIAGRAM, positions={API: [1, 2, 3]}))))
        self.assertTrue(list(check.iter_errors(dict(DIAGRAM, positions={API: "here"}))))


class TestTheDiagramsOwn(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="aac-positions-"))
        # The placed view arranged on its own; none of that may reach the
        # diagram that places it.
        (self.folder / "network-topology.view.yaml").write_text(
            NETWORK.rstrip("\n") + "\npositions:\n  AWS: [400, 400]\n", encoding="utf-8")
        text = "\n".join(dump_yaml(dict(DIAGRAM, positions={API: [8, 16]}))) + "\n"
        (self.folder / "lending.view.yaml").write_text(text, encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.folder)

    def test_positions_survive_the_merge_and_are_never_the_placed_views(self) -> None:
        views = {v.view_id: v for v in load_views(self.folder)}
        diagram = views["lending-onboarding"]
        self.assertEqual(diagram.positions, {API: (8, 16)})
        self.assertEqual(diagram.own.positions, {API: (8, 16)})
        self.assertEqual(views["network-topology"].positions, {"AWS": (400, 400)})
        twice = {v.view_id: v for v in places.with_places(list(views.values()))}
        self.assertEqual(twice["lending-onboarding"].positions, {API: (8, 16)})

    def test_the_payload_carries_positions_only_when_there_are_some(self) -> None:
        model = seeded_model()
        views = load_views(self.folder)
        by_id = {v.view_id: v for v in views}
        root = seeded_root()
        args = (Palette(model.config.get("palette")), IconMap(web_dir(root)), load_components(root))
        self.assertEqual(graph_payload(model, by_id["lending-onboarding"], *args)["positions"], {API: [8, 16]})
        plain = parse_view(dict(DIAGRAM))
        self.assertNotIn("positions", graph_payload(model, places.attach(plain, views), *args))


class _Drawn(unittest.TestCase):
    """The lending diagram's payload, laid out the way the app lays it out
    on its dagre path, and what it keeps when first arranged."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        root = seeded_root()
        cls.views = load_views(root / "30_VIEWS")
        cls.args = (Palette(cls.model.config.get("palette")), IconMap(web_dir(root)), load_components(root))

    def drawn(self, data: dict):
        payload = graph_payload(self.model, places.attach(parse_view(data), self.views), *self.args)
        prep = prepare(payload)
        return payload, prep, layout_layered(payload, prepared=prep)

    def corners(self, prep, lay) -> dict:
        """Every box's top-left, as kept positions are said."""
        return {leaf.id: (lay.leaves[leaf.id][0] - leaf.w / 2, lay.leaves[leaf.id][1] - leaf.h / 2)
                for leaf in prep.leaves}


class TestArranging(_Drawn):
    def setUp(self) -> None:
        self.payload, self.prep, self.lay = self.drawn(DIAGRAM)
        self.kept = arranged.kept_from(self.prep, self.lay)
        self.keys = arranged.keys_of(self.prep)

    def test_every_box_and_boundary_is_kept_by_where_it_sits(self) -> None:
        self.assertEqual(set(self.kept), set(self.keys.values()))
        self.assertIn(API, self.kept)
        self.assertIn("AWS / prod-lending / eu-west-2", self.kept)
        # The first thing in a frame sits at its corner.
        self.assertEqual(self.kept["AWS"], (0, 0))

    def test_what_is_kept_puts_every_box_back_within_half_a_pixel(self) -> None:
        again = arranged.arrange(self.prep, self.lay, self.kept)
        before, after = self.corners(self.prep, self.lay), self.corners(self.prep, again)
        first = self.prep.leaves[0].id
        dx, dy = after[first][0] - before[first][0], after[first][1] - before[first][1]
        for leaf_id in before:
            self.assertLessEqual(abs(after[leaf_id][0] - before[leaf_id][0] - dx), 1.0, leaf_id)
            self.assertLessEqual(abs(after[leaf_id][1] - before[leaf_id][1] - dy), 1.0, leaf_id)
        # Every kept corner is where the arrangement drew it.
        self.assertEqual(arranged.kept_from(self.prep, again), self.kept)

    def test_one_box_moved_moves_that_box_alone(self) -> None:
        start = arranged.arrange(self.prep, self.lay, self.kept)
        moved = dict(self.kept)
        moved[API] = (moved[API][0] + 40, moved[API][1] + 16)
        after = arranged.arrange(self.prep, self.lay, moved)
        for leaf in self.prep.leaves:
            want = (40, 16) if leaf.id == "SYS-LENDING-API" else (0, 0)
            got = (after.leaves[leaf.id][0] - start.leaves[leaf.id][0], after.leaves[leaf.id][1] - start.leaves[leaf.id][1])
            self.assertEqual(got, want, leaf.id)

    def test_a_boundary_moved_takes_what_is_in_it(self) -> None:
        start = arranged.arrange(self.prep, self.lay, self.kept)
        zone = [k for k in self.kept if k.endswith("/ eu-west-2a")][0]
        moved = dict(self.kept)
        moved[zone] = (moved[zone][0] - 30, moved[zone][1] + 50)
        after = arranged.arrange(self.prep, self.lay, moved)
        inside = {leaf.id for leaf in self.prep.leaves if self.keys[leaf.id].startswith(zone + " / ")}
        self.assertTrue(inside)
        for leaf in self.prep.leaves:
            want = (-30, 50) if leaf.id in inside else (0, 0)
            got = (after.leaves[leaf.id][0] - start.leaves[leaf.id][0], after.leaves[leaf.id][1] - start.leaves[leaf.id][1])
            self.assertEqual(got, want, leaf.id)

    def test_a_system_placed_on_an_arranged_diagram_moves_nothing_already_there(self) -> None:
        start = arranged.arrange(self.prep, self.lay, self.kept)
        _payload, prep, lay = self.drawn(dict(DIAGRAM, scope={"pin": ["SYS-LENDING-API", "SYS-LENDING-WORKER"]}))
        after = arranged.arrange(prep, lay, self.kept)
        for leaf_id, at in start.leaves.items():
            self.assertEqual(after.leaves[leaf_id][:2], at[:2], leaf_id)
        # The new one is in its boundary's frame, clear of every box there.
        keys = arranged.keys_of(prep)
        worker = keys["SYS-LENDING-WORKER"]
        frame = worker.rsplit(" / ", 1)[0]
        box = self.corners(prep, after)["SYS-LENDING-WORKER"]
        leaf = [lf for lf in prep.leaves if lf.id == "SYS-LENDING-WORKER"][0]
        for other in prep.leaves:
            if other.id == leaf.id or keys[other.id].rsplit(" / ", 1)[0] != frame:
                continue
            o = self.corners(prep, after)[other.id]
            apart = (box[0] + leaf.w <= o[0] or o[0] + other.w <= box[0]
                     or box[1] + leaf.h <= o[1] or o[1] + other.h <= box[1])
            self.assertTrue(apart, other.id)

    def test_a_box_kept_in_another_boundary_is_placed_afresh(self) -> None:
        moved = dict(self.kept)
        # Kept where it was before a move into zone eu-west-2a, which the
        # record now says: the old line names a frame it is not in.
        moved["AWS / prod-lending / eu-west-2 / eu-west-2a / SYS-LENDING-API"] = (-500, -500)
        after = arranged.arrange(self.prep, self.lay, moved)
        start = arranged.arrange(self.prep, self.lay, self.kept)
        self.assertEqual(after.leaves["SYS-LENDING-API"], start.leaves["SYS-LENDING-API"])

    def test_the_svg_draws_the_arrangement_and_says_so(self) -> None:
        moved = dict(self.kept)
        moved[API] = (moved[API][0] + 40, moved[API][1] + 16)
        positions = {k: list(v) for k, v in moved.items()}
        svg = render_svg(dict(self.payload, positions=positions), sheet=False)
        root = ET.fromstring(svg)
        self.assertEqual(root.get("data-layout"), "arranged")
        plain = ET.fromstring(render_svg(self.payload, sheet=False))
        self.assertNotEqual(plain.get("data-layout"), "arranged")


class TestTheFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sandbox = Sandbox(seed=True)
        cls.root = cls.sandbox.__enter__()
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = cls.root
        cls.server = server_module

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sandbox.__exit__(None, None, None)

    def test_positions_are_written_last_and_one_box_moved_is_one_line(self) -> None:
        kept = {API: [8, 16], "AWS": [0, 0], "AWS / prod-lending": [0, 0]}
        first = self.server.api_canvas_save({}, {"id": None, "data": dict(DIAGRAM, positions=kept)})
        path = self.root / first["path"]
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("positions:\n  AWS: [0, 0]\n  AWS / prod-lending: [0, 0]\n  %s: [8, 16]\n" % API))
        moved = dict(kept, **{API: [48, 32]})
        self.server.api_canvas_save({}, {"id": first["id"], "data": dict(DIAGRAM, positions=moved)})
        after = path.read_text(encoding="utf-8")
        changed = [(a, b) for a, b in zip(text.splitlines(), after.splitlines()) if a != b]
        self.assertEqual(changed, [("  %s: [8, 16]" % API, "  %s: [48, 32]" % API)])
        # Read back as the app and every drawing read it.
        self.assertEqual(self.server.api_view({"id": [first["id"]]}, {})["data"]["positions"][API], [48, 32])

    def test_a_key_a_reader_would_take_apart_is_quoted(self) -> None:
        data = {"positions": {"Lending: Ops / SYS-X": [1, 2], "# not a comment": [3, 4], "AWS / SYS-Y": [5, 6]}}
        text = "\n".join(dump_yaml(data)) + "\n"
        self.assertIn('  "Lending: Ops / SYS-X": [1, 2]\n', text)
        self.assertIn('  "# not a comment": [3, 4]\n', text)
        self.assertIn("  AWS / SYS-Y: [5, 6]\n", text)
        self.assertEqual(yamlish.loads(text), data)


if __name__ == "__main__":
    unittest.main()
