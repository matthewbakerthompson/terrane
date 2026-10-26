"""Tests for what a diagram draws of its own (`annotations` on a view,
terrane.annotations, terrane.draw.annotations).

What is checked: the list reads as the V13 frame writes it, and what cannot
be drawn is refused saying what to fix -- a missing or doubled key, a role
or a shape or a look it does not have, a corner or a size that is not two
numbers, a frame it sits in that is not a frame, a line's end that is
neither an id nor a point; a view carries the list and the schema admits
it. Then the drawing: a diagram of its own shapes alone resolves to nothing
of the model rather than being refused, and the payload carries the list;
alone, the picture is the shapes, a frame's contents placed from its
corner; a frame is stacked by what holds it, on a boundary it is inside and
under one it is around; beside the estate's records, a frame on the bare
sheet is under the boundaries and the rest over the boxes, a line joined to
its record; a square line turns across or down the wider gap and a curved
one through the same turns; a line ends on an ellipse's and a diamond's
outline. The canvas draws from the same numbers: the shapes, the fills and
the sizes in engine.js are the ones here. Last,
the file: the list is written before positions, and a diagram of its own
shapes alone is saved, validated and drawn.
"""

from __future__ import annotations

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import jsonschema, places  # noqa: E402
from terrane.annotations import FILLS, SHAPES, TEXT_SIZES, AnnotationError, read  # noqa: E402
from terrane.blocks import load_components  # noqa: E402
from terrane.draw import annotations as drawn  # noqa: E402
from terrane.draw.svg import render_svg  # noqa: E402
from terrane.draw.metrics import default_metrics as drawn_metrics  # noqa: E402
from terrane.icons import IconMap, web_dir  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.payload import graph_payload  # noqa: E402
from terrane.query import ViewError, load_views, parse_view, resolve  # noqa: E402

from _fixture import REPO, Sandbox, seeded_model, seeded_root, setup_shared, teardown_shared  # noqa: E402

#: The V13 frame's own example: two frames, one in the other, a note in the
#: outer one, and a line from a record to the note.
LANDING = [
    {"key": "org", "role": "frame", "label": "AWS Organization", "at": [20, 74], "size": [792, 624]},
    {"key": "ou-security", "role": "frame", "label": "Security OU", "in": ["org"], "at": [20, 94], "size": [236, 360]},
    {"key": "guardrails", "role": "note", "in": ["org"], "at": [546, 492], "size": [226, 70],
     "label": "Guardrails: every account is denied the regions but eu-west-2"},
    {"key": "line-1", "role": "line", "from": "SYS-LENDING-API", "to": "guardrails"},
]

#: A diagram with nothing of the estate on it, only its own.
OWN_ONLY = {"view_id": "landing-zone", "title": "AWS landing zone", "category": "Technology", "kind": "diagram",
            "annotations": LANDING[:3]}

#: The lending diagram the canvas writes, with the landing zone's shapes.
DIAGRAM = {
    "view_id": "lending-onboarding", "title": "Lending onboarding", "category": "Application", "kind": "diagram",
    "places": [{"view": "network-topology", "only": {"cloud_account": ["prod-lending"]}}],
    "scope": {"pin": ["SYS-LENDING-API"]}, "edges": [{"via": "interfaces"}], "annotations": LANDING,
}

ENGINE = REPO / "80_APP" / "web" / "canvas" / "engine.js"


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestReading(unittest.TestCase):
    def test_the_frames_example_reads_as_it_is_written(self) -> None:
        self.assertEqual(read(LANDING, "here"), LANDING)
        self.assertEqual(read(None, "here"), [])

    def test_what_cannot_be_drawn_is_refused_saying_what_to_fix(self) -> None:
        note = {"key": "n", "role": "note", "at": [0, 0], "size": [10, 10]}
        cases = [
            ({"role": "note"}, "has no key"),
            ("a note", "is not a mapping"),
            (dict(note, role="sticker"), "has role 'sticker'"),
            (dict(note, tint="red"), "has tint, which a note does not"),
            (dict(note, at=[0]), "at is its corner"),
            (dict(note, size=[0, 10]), "both more than nought"),
            (dict(note, role="shape", shape="star"), "shape is one of"),
            (dict(note, look={"fill": "teal"}), "look.fill is one of"),
            (dict(note, look={"line": "dotted"}), "look.line is one of"),
            (dict(note, look={"font": "s"}), "look has font"),
            (dict(note, **{"in": ["nowhere"]}), "n is in nowhere, which is not a frame"),
            ({"key": "l", "role": "line", "from": "SYS-X", "to": {"x": 1}}, "to is a record's id"),
            ({"key": "l", "role": "line", "from": "SYS-X", "to": [1, 2], "ends": "start"}, "ends is one of"),
            ({"key": "l", "role": "line", "from": "SYS-X", "to": [1, 2], "route": "zigzag"}, "route is one of"),
            ({"key": "l", "role": "line", "from": "SYS-X", "to": [1, 2], "at": [0, 0]}, "which a line does not"),
        ]
        for item, said in cases:
            with self.subTest(said=said):
                with self.assertRaises(AnnotationError) as caught:
                    read([item], "view x: annotations")
                self.assertIn(said, str(caught.exception))
        with self.assertRaises(AnnotationError) as twice:
            read([note, dict(note)], "view x: annotations")
        self.assertIn("n is the key of two items", str(twice.exception))
        with self.assertRaises(AnnotationError):
            read({"key": "n"}, "view x: annotations")

    def test_a_view_carries_them_and_refuses_a_list_it_cannot_draw(self) -> None:
        self.assertEqual(list(parse_view(OWN_ONLY).annotations), LANDING[:3])
        self.assertEqual(list(parse_view({"view_id": "plain", "scope": {"include": []}}).annotations), [])
        with self.assertRaises(ViewError) as caught:
            parse_view(dict(OWN_ONLY, annotations=[{"key": "a", "role": "note"}]))
        self.assertIn("view landing-zone: annotations: a: at is its corner", str(caught.exception))

    def test_the_schema_admits_them(self) -> None:
        try:
            import jsonschema as validator  # the third-party package, not aac's
        except ImportError:
            self.skipTest("no JSON Schema validator installed")
        if not hasattr(validator, "Draft202012Validator"):
            self.skipTest("the installed validator predates draft 2020-12")
        check = validator.Draft202012Validator(jsonschema.view_schema())
        self.assertEqual([e.message for e in check.iter_errors(OWN_ONLY)], [])
        self.assertEqual([e.message for e in check.iter_errors(DIAGRAM)], [])
        self.assertTrue(list(check.iter_errors(dict(OWN_ONLY, annotations=[{"key": "a", "role": "sticker"}]))))


class _Drawn(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        root = seeded_root()
        cls.views = load_views(root / "30_VIEWS")
        cls.args = (Palette(cls.model.config.get("palette")), IconMap(web_dir(root)), load_components(root))

    def payload(self, data: dict) -> dict:
        return graph_payload(self.model, places.attach(parse_view(data), self.views), *self.args)


def _owned(svg: str) -> list:
    """Each of the diagram's own as the picture draws it, in drawing order:
    its key, its role, and its first rectangle or path's corner."""
    root = ET.fromstring(svg)
    out = []
    for g in root.iter("{http://www.w3.org/2000/svg}g"):
        if g.get("class") != "own":
            continue
        shape = next(iter(g), None)
        out.append((g.get("data-key"), g.get("data-role"), shape))
    return out


class TestDrawing(_Drawn):
    def test_its_own_shapes_alone_resolve_to_nothing_of_the_model(self) -> None:
        graph = resolve(self.model, parse_view(OWN_ONLY))
        self.assertEqual((graph.nodes, graph.edges, graph.groups), ([], [], []))
        # Without them, a diagram with nothing on it is still no view.
        with self.assertRaises(ViewError):
            resolve(self.model, parse_view(dict(OWN_ONLY, annotations=[])))

    def test_the_payload_carries_them_and_a_plain_view_has_none(self) -> None:
        self.assertEqual(self.payload(OWN_ONLY)["annotations"], LANDING[:3])
        plain = dict(DIAGRAM)
        del plain["annotations"]
        self.assertNotIn("annotations", self.payload(plain))

    def test_alone_the_picture_is_the_shapes_each_placed_from_its_frame(self) -> None:
        svg = render_svg(self.payload(OWN_ONLY), sheet=False)
        self.assertEqual(ET.fromstring(svg).get("data-layout"), "own")
        owned = _owned(svg)
        self.assertEqual([k for k, _, _ in owned], ["org", "ou-security", "guardrails"])
        org, inner = owned[0][2], owned[1][2]
        # The inner frame's corner is the outer one's and its own `at`.
        self.assertEqual(float(inner.get("x")) - float(org.get("x")), 20)
        self.assertEqual(float(inner.get("y")) - float(org.get("y")), 94)
        self.assertIn("Guardrails: every account is", svg)

    def test_a_frame_is_stacked_by_what_holds_it(self) -> None:
        # An account and a zone in it, outermost first, as a drawing lists them.
        account, zone = (0.0, 0.0, 400.0, 300.0), (10.0, 30.0, 200.0, 200.0)
        inner = {"key": "f", "role": "frame", "at": [20, 40], "size": [100, 80]}
        around_zone = {"key": "z", "role": "frame", "at": [5, 20], "size": [300, 250]}
        around = {"key": "g", "role": "frame", "at": [-20, -40], "size": [600, 500]}
        note = {"key": "n", "role": "note", "in": ["f"], "at": [4, 4], "size": [40, 40]}
        loose = {"key": "o", "role": "note", "at": [0, 0], "size": [10, 10]}
        items = [inner, around_zone, around, note, loose]
        boxes = drawn.place(items, (0.0, 0.0))
        # In the zone: above it. Round the zone, in the account: above the
        # account, under the zone. Round both: under the estate.
        self.assertEqual([drawn.layer_of(a, boxes, [account, zone]) for a in items], [1, 0, "under", 1, "over"])
        self.assertEqual(drawn.layer_of(inner, boxes, []), "under")

    def test_beside_the_records_frames_go_under_and_the_rest_over(self) -> None:
        svg = render_svg(self.payload(DIAGRAM), sheet=False)
        self.assertLess(svg.index('data-key="org"'), svg.index('class="boundary"'))
        # What sits in a frame goes with it, under; the line from the lending
        # API to the note is over every box.
        self.assertLess(svg.index('data-key="guardrails"'), svg.index('class="boundary"'))
        self.assertGreater(svg.index('data-key="line-1"'), svg.rindex('class="node"'))
        alone = dict(DIAGRAM, annotations=[dict(LANDING[2], key="by-itself", **{"in": []})])
        loose = render_svg(self.payload(alone), sheet=False)
        self.assertGreater(loose.index('data-key="by-itself"'), loose.rindex('class="node"'))

    def test_a_square_line_turns_down_the_wider_gap_and_a_curved_one_through_the_same_turns(self) -> None:
        left, right = (0.0, 0.0, 100.0, 50.0), (300.0, 200.0, 400.0, 260.0)
        # 200 across and 150 down between them: across is the wider gap.
        self.assertEqual(drawn.square(left, right), [(200.0, 25.0), (200.0, 230.0)])
        below = (40.0, 400.0, 90.0, 450.0)
        self.assertEqual(drawn.square(left, below), [(50.0, 225.0), (65.0, 225.0)])
        self.assertEqual(drawn.square(left, (50.0, 10.0, 150.0, 60.0)), [])
        items = [{"key": "a", "role": "shape", "shape": "rectangle", "at": [0, 0], "size": [100, 50]},
                 {"key": "b", "role": "shape", "shape": "rectangle", "at": [300, 200], "size": [100, 60]}]
        for route, piece in (("square", " L"), ("curved", "Q")):
            with self.subTest(route=route):
                line = {"key": "l", "role": "line", "from": "a", "to": "b", "route": route}
                svg, _ = drawn.paint(items + [line], (0.0, 0.0), {}, drawn_metrics(), "over")
                path = re.search(r'data-role="line">\s*<path d="([^"]+)"', svg).group(1)
                self.assertTrue(path.startswith("M100 25"), path)
                self.assertIn(piece, path)

    def test_a_line_ends_on_an_ellipses_and_a_diamonds_outline(self) -> None:
        box = (0.0, 0.0, 100.0, 50.0)
        self.assertEqual(drawn._clip(box, (50, 25), (150, 25)), (100, 25))
        self.assertEqual(drawn._clip(box, (50, 25), (50, 125), "ellipse"), (50, 50))
        x, y = drawn._clip(box, (50, 25), (150, 125), "diamond")
        # On the diamond's edge: |dx|/50 + |dy|/25 = 1.
        self.assertAlmostEqual(abs(x - 50) / 50 + abs(y - 25) / 25, 1)
        self.assertLess(x, 100)


def _js(text: str, name: str, close: str) -> str:
    """A `var NAME = ...` literal of engine.js, its comments taken out."""
    body = text.split("var %s = " % name, 1)[1].split(close, 1)[0] + close.strip()[-1]
    return "\n".join(line.split("//")[0] for line in body.splitlines())


class TestTheSameNumbersAsTheCanvas(unittest.TestCase):
    """The picture is the canvas's only if it draws from the canvas's own
    numbers; engine.js says them as JavaScript, read here."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = ENGINE.read_text(encoding="utf-8")

    def literal(self, name: str, close: str):
        js = _js(self.text, name, close)
        python = re.sub(r"(?m)^(\s*)([\w-]+|\"[\w-]+\"):", r'\1"\2":', js).replace('""', '"')
        python = re.sub(r"([{,]\s*)(\w+):", r'\1"\2":', python)
        return eval(python, {"K": drawn.K})  # noqa: S307 -- our own file's literals

    def test_the_shapes_are_drawn_from_the_same_paths(self) -> None:
        paths = self.literal("OWN_PATHS", "\n  }")
        self.assertEqual(sorted(paths), sorted(drawn.PATHS))
        for name, prog in paths.items():
            with self.subTest(shape=name):
                self.assertEqual([list(op) for op in prog], [list(op) for op in drawn.PATHS[name]])

    def test_the_menu_lists_the_shapes_the_file_takes(self) -> None:
        menu = self.literal("OWN_SHAPES", "\n  ]")
        self.assertEqual(tuple(name for name, _ in menu), SHAPES)

    def test_the_fills_and_the_sizes_are_the_same(self) -> None:
        self.assertEqual({k: tuple(v) for k, v in self.literal("FILLS", "\n  }").items()}, FILLS)
        self.assertEqual(self.literal("TEXT_SIZES", "}"), TEXT_SIZES)
        self.assertEqual(self.literal("ROLE_FILL", "}"), drawn.ROLE_FILL)


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

    def test_they_are_written_before_positions_in_the_order_drawn(self) -> None:
        data = dict(DIAGRAM, positions={"AWS": [0, 0]})
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        text = (self.root / saved["path"]).read_text(encoding="utf-8")
        self.assertLess(text.index("\nannotations:\n"), text.index("\npositions:\n"))
        self.assertLess(text.index("key: org"), text.index("key: guardrails"))
        back = self.server.api_view({"id": [saved["id"]]}, {})["data"]["annotations"]
        self.assertEqual(back, LANDING)

    def test_a_diagram_of_its_own_shapes_alone_is_saved_checked_and_drawn(self) -> None:
        data = dict(OWN_ONLY)
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertEqual((saved["created"], saved["errors"]), (True, []))
        svg = self.server.api_svg({"view": [saved["id"]]})
        self.assertEqual(svg.count('class="own"'), 3)


if __name__ == "__main__":
    unittest.main()
