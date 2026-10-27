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
the sizes in engine.js are the ones here. Icon tiles, a diagram's other
look: read from the view, a shape's icon one of the plain icons or a mark
the app ships, a tile drawn with its icon or a mark in its place, its words
over the lines on what lies under them, an end held at a point of its tile,
the slide and the page drawing the tile, and the canvas's numbers the
same. The Style tab's settings: how much of a fill shows, how heavy an
edge is, the corners' radius and no shadow, read and refused where they
mean nothing, drawn by the picture, the slide and the page, a see-through
fill casting no shadow, and the canvas's weights the same. Last, the
file: the list is written before positions, a diagram of its own shapes
alone is saved, validated and drawn, and so is its look.
"""

from __future__ import annotations

import base64
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import jsonschema, places  # noqa: E402
from terrane.annotations import (FILLS, MOST_CORNERS, SHAPES, TEXT_SIZES, WEIGHTS, WORDS_ON,  # noqa: E402
                                 AnnotationError, read)
from terrane.blocks import load_components  # noqa: E402
from terrane.draw import annotations as drawn  # noqa: E402
from terrane.draw.svg import render_svg  # noqa: E402
from terrane.draw.metrics import default_metrics as drawn_metrics  # noqa: E402
from terrane.icons import MARK_SETS, IconMap, web_dir  # noqa: E402
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


class TestTheSceneIsThePicture(unittest.TestCase):
    """What another painter gets (`scene`, the deck's and the draw.io page's
    source) is what the picture drew: the same places, layers and points."""

    def test_the_same_places_layers_and_line_points(self) -> None:
        items = [{"key": "a", "role": "shape", "shape": "rectangle", "at": [0, 0], "size": [100, 50]},
                 {"key": "b", "role": "shape", "shape": "rectangle", "at": [300, 200], "size": [100, 60]},
                 {"key": "f", "role": "frame", "at": [-20, -20], "size": [500, 320]},
                 {"key": "n", "role": "note", "in": ["f"], "at": [10, 10], "size": [40, 30], "label": "Hi"},
                 {"key": "l", "role": "line", "from": "a", "to": "b", "route": "square", "ends": "both"},
                 {"key": "x", "role": "line", "from": "a", "to": "SYS-GONE"}]
        got = {o.key: o for o in drawn.scene(items, (0.0, 0.0), {})}
        boxes = drawn.place(items, (0.0, 0.0))
        for key in "abfn":
            self.assertEqual(got[key].box, boxes[key])
        self.assertEqual([got[k].layer for k in "abfn"], ["over", "over", "under", "under"])
        self.assertEqual(got["n"].within, "f")
        self.assertEqual(got["n"].fill, FILLS["yellow"])
        self.assertTrue(got["n"].shadow)
        self.assertFalse(got["f"].shadow)
        line = got["l"]
        self.assertEqual(line.points, ((100.0, 25.0), (200.0, 25.0), (200.0, 230.0), (300.0, 230.0)))
        self.assertEqual((line.source, line.target, line.ends, line.route), ("a", "b", "both", "square"))
        # The picture's path runs through the same points, short of each head.
        svg, _ = drawn.paint(items, (0.0, 0.0), {}, drawn_metrics(), "over")
        self.assertIn(" L200 25 L200 230 ", svg)
        # A line to a record not on the drawing is off both.
        self.assertNotIn("x", got)
        self.assertNotIn('data-key="x"', svg)


class TestHeldEnds(unittest.TestCase):
    """An end held at a point of its box (`from_at`, `to_at`): read, refused
    on a point end or past the box, drawn from that point, a square line
    leaving square from it, and the draw.io page holding it there."""

    ITEMS = [{"key": "a", "role": "shape", "at": [0, 0], "size": [100, 50]},
             {"key": "b", "role": "shape", "at": [300, 100], "size": [100, 50]},
             {"key": "l", "role": "line", "from": "a", "to": "b", "from_at": [1, 0.25]}]

    def test_read_on_a_box_end_and_refused_on_a_point_or_past_the_box(self) -> None:
        self.assertEqual(read(self.ITEMS, "here")[2]["from_at"], [1, 0.25])
        line = self.ITEMS[2]
        for wrong, said in ((dict(line, from_at=[1.5, 0]), "from 0 to 1"), (dict(line, to_at="top"), "from 0 to 1"),
                            (dict(line, **{"from": [5, 5]}), "is a point")):
            with self.subTest(wrong=wrong), self.assertRaises(AnnotationError) as caught:
                read(self.ITEMS[:2] + [wrong], "here")
            self.assertIn(said, str(caught.exception))

    def test_a_straight_line_starts_where_it_is_held(self) -> None:
        own = [o for o in drawn.scene(self.ITEMS, (0.0, 0.0), {}) if o.key == "l"][0]
        self.assertEqual(own.points[0], (100.0, 12.5))
        self.assertEqual(own.from_at, (1.0, 0.25))
        from terrane.render_drawio import own_line_style
        self.assertIn("exitX=1;exitY=0.25;exitPerimeter=0;", own_line_style(own))
        self.assertNotIn("entryX", own_line_style(own))

    def test_a_square_line_leaves_square_a_margin_out_first(self) -> None:
        items = self.ITEMS[:2] + [dict(self.ITEMS[2], route="square", from_at=[0.5, 0])]
        own = [o for o in drawn.scene(items, (0.0, 0.0), {}) if o.key == "l"][0]
        self.assertEqual(own.points[:2], ((50.0, 0.0), (50.0, -10.0)))
        for i in range(len(own.points) - 1):
            p, q = own.points[i], own.points[i + 1]
            self.assertTrue(p[0] == q[0] or p[1] == q[1], own.points)
            self.assertFalse(drawn._cuts(p, q, (0.0, 0.0, 100.0, 50.0)), "through its own box: %r" % (own.points,))


class TestAroundBoxes(unittest.TestCase):
    """A square or curved line around the boxes in its way (`detour`): the
    plain turns when nothing is in the way, a way round when something is,
    and the plain turns again when the boxes leave no way; the picture
    routes it so; and the canvas's own copy in engine.js, run in a browser,
    lands on the same points for the same boxes."""

    A, B = (0.0, 0.0, 100.0, 50.0), (400.0, 0.0, 500.0, 50.0)

    def _clear_of(self, a, b, pts, walls) -> None:
        run = [((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)] + list(pts) + [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)]
        for i in range(len(run) - 1):
            p, q = run[i], run[i + 1]
            self.assertTrue(p[0] == q[0] or p[1] == q[1], "a run neither across nor down: %r to %r" % (p, q))
            for o in walls:
                self.assertFalse(drawn._cuts(p, q, o), "%r to %r runs through %r" % (p, q, o))

    def test_nothing_in_the_way_keeps_the_plain_turns(self) -> None:
        plain = drawn.square(self.A, self.B)
        self.assertEqual(drawn.detour(self.A, self.B, [(200.0, 200.0, 260.0, 240.0)], plain), plain)

    def test_a_box_in_the_way_is_gone_around_squarely(self) -> None:
        plain = drawn.square(self.A, self.B)
        wall = (200.0, -40.0, 300.0, 90.0)
        pts = drawn.detour(self.A, self.B, [wall], plain)
        self.assertNotEqual(pts, plain)
        self._clear_of(self.A, self.B, pts, [wall])
        # Out of a side's middle and into one: under the wall, two bends
        # dearer than going straight, cheaper than the four over and back.
        self.assertTrue(pts[0][0] == 50.0 or pts[0][1] == 25.0, pts)
        self.assertTrue(pts[-1][0] == 450.0 or pts[-1][1] == 25.0, pts)
        self.assertEqual(pts, [(50.0, 100.0), (450.0, 100.0)])
        self.assertEqual(drawn.detour(self.A, self.B, [wall], plain), pts)

    def test_a_point_end_and_a_box_hemmed_in(self) -> None:
        wall = (200.0, -40.0, 300.0, 90.0)
        point = (600.0, 300.0, 600.0, 300.0)
        plain = drawn.square(self.A, point)
        pts = drawn.detour(self.A, point, [wall, (330.0, 150.0, 640.0, 200.0)], plain)
        self._clear_of(self.A, point, pts, [wall, (330.0, 150.0, 640.0, 200.0)])
        hem = [(-30.0, -30.0, 130.0, -15.0), (-30.0, 65.0, 130.0, 80.0), (-30.0, -30.0, -15.0, 80.0),
               (115.0, -30.0, 130.0, 80.0)]
        plain = drawn.square(self.A, self.B)
        self.assertEqual(drawn.detour(self.A, self.B, hem, plain), plain)

    def test_the_picture_routes_a_square_line_around_a_note(self) -> None:
        items = [{"key": "a", "role": "shape", "at": [0, 0], "size": [100, 50]},
                 {"key": "b", "role": "shape", "at": [400, 0], "size": [100, 50]},
                 {"key": "n", "role": "note", "at": [200, -40], "size": [100, 130]},
                 {"key": "l", "role": "line", "from": "a", "to": "b", "route": "square"}]
        own = [o for o in drawn.scene(items, (0.0, 0.0), {}) if o.key == "l"][0]
        self.assertGreater(len(own.points), 2)
        self._clear_of(self.A, self.B, own.points[1:-1], [(200.0, -40.0, 300.0, 90.0)])
        svg, _ = drawn.paint(items, (0.0, 0.0), {}, drawn_metrics(), "over")
        path = re.search(r'data-key="l" data-role="line">\s*<path d="([^"]+)"', svg).group(1)
        self.assertGreater(path.count("L"), 2)

    def test_the_canvas_routes_as_the_picture_does(self) -> None:
        import json

        from terrane.draw.browser import Chrome, browser_path

        if not browser_path():
            self.skipTest("no browser on this machine")
        engine = (REPO / "80_APP" / "web" / "canvas" / "engine.js").read_text(encoding="utf-8")
        source = "function detour(" + engine.split("  function detour(", 1)[1].split("\n  }\n", 1)[0] + "\n}"
        seed, cases = 7, []

        def rand(n: int) -> int:
            nonlocal seed
            seed = (seed * 1103515245 + 12345) % 2147483648
            return seed % n

        for _ in range(40):
            a = (float(rand(200)), float(rand(200)), 0.0, 0.0)
            a = (a[0], a[1], a[0] + 40 + rand(80) + 0.37, a[1] + 30 + rand(40) + 0.5)
            b = (float(400 + rand(300)), float(rand(400)), 0.0, 0.0)
            b = (b[0], b[1], b[0] + 40 + rand(80), b[1] + 30 + rand(40) + 0.25)
            walls = []
            for _w in range(rand(9)):
                x, y = float(rand(700)), float(rand(450))
                walls.append((x, y, x + 20 + rand(120) + 0.125, y + 20 + rand(90)))
            cases.append({"a": a, "b": b, "o": walls, "p": drawn.square(a, b)})
        want = [[list(p) for p in drawn.detour(c["a"], c["b"], c["o"], c["p"])] for c in cases]
        self.assertTrue(any(len(w) > 2 for w in want), "no case went around anything")
        with Chrome() as chrome:
            page = chrome.page("about:blank")
            got = json.loads(page.evaluate("(function () {\n%s\nreturn JSON.stringify(%s.map(function (c) { "
                                           "return detour(c.a, c.b, c.o, c.p); })); })()" % (source, json.dumps(cases))))
        self.assertEqual(got, want)


class TestBends(unittest.TestCase):
    """A straight line bent at points of the sheet (`via`), read, refused on
    a line that turns by itself, and drawn through its bends by the picture
    and by the scene the deck and the draw.io page are painted from."""

    LINE = {"key": "l", "role": "line", "from": [0, 0], "to": [200, 0], "via": [[100, 80]]}

    def test_read_on_a_straight_line_and_refused_where_it_turns_by_itself(self) -> None:
        self.assertEqual(read([self.LINE], "here")[0]["via"], [[100, 80]])
        for wrong, said in ((dict(self.LINE, route="square"), "turns by itself"),
                            (dict(self.LINE, route="curved"), "turns by itself"), (dict(self.LINE, via=[]), "bends at"),
                            (dict(self.LINE, via=[[1, 2, 3]]), "bends at"), (dict(self.LINE, via="here"), "bends at")):
            with self.subTest(wrong=wrong), self.assertRaises(AnnotationError) as caught:
                read([wrong], "here")
            self.assertIn(said, str(caught.exception))

    def test_the_picture_and_the_scene_go_through_its_bends_from_the_sheets_corner(self) -> None:
        svg, _ = drawn.paint([self.LINE], (10.0, 20.0), {}, drawn_metrics(), "over")
        self.assertIn("M10 20 L110 100 L", svg)
        own = drawn.scene([self.LINE], (10.0, 20.0), {})[0]
        self.assertEqual(own.points, ((10.0, 20.0), (110.0, 100.0), (210.0, 20.0)))


class TestTurned(unittest.TestCase):
    """A shape, a note or text turned about its middle (`rotate`), read,
    refused on a frame or past a turn, and drawn turned by every painter."""

    NOTE = {"key": "n", "role": "note", "label": "Turned", "at": [100, 50], "size": [80, 40], "rotate": 30}

    def test_read_on_a_box_and_refused_on_a_frame_or_past_a_turn(self) -> None:
        self.assertEqual(read([self.NOTE], "here")[0]["rotate"], 30)
        for wrong, said in ((dict(self.NOTE, role="frame"), "not turned"), (dict(self.NOTE, rotate=360), "less than 360"),
                            (dict(self.NOTE, rotate="30"), "degrees"), (dict(self.NOTE, rotate=True), "degrees")):
            with self.subTest(wrong=wrong), self.assertRaises(AnnotationError) as caught:
                read([wrong], "here")
            self.assertIn(said, str(caught.exception))

    def test_the_picture_the_slide_and_the_page_turn_it_about_its_middle(self) -> None:
        svg, _ = drawn.paint([self.NOTE], (0.0, 0.0), {}, drawn_metrics(), "over")
        self.assertIn('data-role="note" transform="rotate(30 140 70)"', svg)
        own = drawn.scene([self.NOTE], (0.0, 0.0), {})[0]
        self.assertEqual(own.rotate, 30.0)
        from terrane.draw.dml import _Sheet, _own_xml
        from terrane.render_drawio import own_style
        self.assertIn('<a:xfrm rot="1800000">', _own_xml(2, own, _Sheet((0, 0, 400, 200), (0, 0, 4, 2))))
        self.assertIn("rotation=30;", own_style(own))
        self.assertNotIn("rot=", _own_xml(2, own._replace(rotate=0.0), _Sheet((0, 0, 400, 200), (0, 0, 4, 2))))


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
        self.assertEqual(self.literal("FILLS", "\n  }"), FILLS)
        self.assertEqual(self.literal("FILL_ORDER", "]"), list(FILLS))
        self.assertEqual(self.literal("WORDS_ON", "}"), WORDS_ON)
        self.assertEqual(self.literal("TEXT_SIZES", "}"), TEXT_SIZES)
        self.assertEqual(self.literal("ROLE_FILL", "}"), drawn.ROLE_FILL)

    def scalar(self, name: str):
        found = re.search(r"\b%s = ([^,;]+)[,;]" % name, self.text)
        return eval(found.group(1))  # noqa: S307 -- our own file's literals

    def test_the_inks_the_shadow_and_the_corners_are_the_same(self) -> None:
        """Illustrated is one look in two painters only while both say its
        numbers alike."""
        for js, py in (("INK", drawn.INK), ("LINE_INK", drawn.LINE_INK), ("CAPTION_INK", drawn.CAPTION_INK),
                       ("PAPER", drawn.PAPER), ("SHADOW", drawn.SHADOW), ("ROUND", drawn.ROUND),
                       ("CAPTION_STEP", drawn.CAPTION_STEP), ("TAB_PAD", drawn.TAB_PAD)):
            with self.subTest(name=js):
                self.assertEqual(self.scalar(js), py)
        face = re.search(r'\bNAME_FACE = "([^"]*)"', self.text).group(1)
        self.assertTrue(face.startswith("'%s'" % drawn.NAME_FACE[0]), face)

    def test_the_tiles_numbers_and_the_marks_sets_are_the_same(self) -> None:
        """Icon tiles likewise, and the marks a tile can carry."""
        for name in ("TILE", "TILE_ROUND", "TILE_GLOW", "TILE_ICON", "TILE_GAP", "TILE_WORDS_OVER", "TILE_INK",
                     "TILE_CAPTION", "TILE_LINE", "TILE_FRAME", "TILE_FRAME_INK", "TILE_SHEET", "TILE_GROUND_PAD"):
            with self.subTest(name=name):
                self.assertEqual(self.scalar(name), getattr(drawn, name))
        self.assertEqual(self.literal("TILE_FILLS", "\n  }"), {k: list(v) for k, v in drawn.TILE_FILLS.items()})
        self.assertEqual(self.literal("KIND_ICONS", "\n  }"), drawn.KIND_ICONS)
        sets = re.search(r"var MARK_SETS = (\[.*?\]\]);", self.text).group(1)
        self.assertEqual(json.loads(sets), [list(s) for s in MARK_SETS])


class TestIconTiles(unittest.TestCase):
    """Icon tiles (V16): every shape a tile of its color with an icon, or
    a provider's or vendor's own mark in the tile's place, its words under
    it; a frame a pale panel, lines gray and under the tiles."""

    WEB = REPO / "80_APP" / "web"

    def box(self, item: dict, box=(0.0, 0.0, 150.0, 64.0)) -> str:
        return drawn._box(dict({"key": "k", "role": "shape"}, **item), box, drawn_metrics(), "tiles")

    def test_a_view_says_its_look_and_is_illustrated_when_it_says_nothing(self) -> None:
        self.assertEqual(parse_view(OWN_ONLY).look, "illustrated")
        self.assertEqual(parse_view(dict(OWN_ONLY, look="tiles")).look, "tiles")
        with self.assertRaises(ViewError) as caught:
            parse_view(dict(OWN_ONLY, look="glass"))
        self.assertIn("view landing-zone: look is one of illustrated, tiles", str(caught.exception))

    def test_a_shape_names_a_plain_icon_or_a_mark_the_app_ships(self) -> None:
        shape = {"key": "s", "role": "shape", "at": [0, 0], "size": [150, 64]}
        for icon in ("server", "aws/lambda", "azure/key-vault", "gcp/bigquery", "brands/snowflake"):
            with self.subTest(icon=icon):
                self.assertEqual(read([dict(shape, look={"icon": icon})], "here")[0]["look"]["icon"], icon)
        for icon, said in (("aws/no-such-mark", "no mark the app ships"), ("AWS/Lambda", "a provider's mark"),
                           ("aws/lambda/x", "a provider's mark"), ("icons/aws/lambda", "a provider's mark")):
            with self.subTest(icon=icon), self.assertRaises(AnnotationError) as caught:
                read([dict(shape, look={"icon": icon})], "here")
            self.assertIn(said, str(caught.exception))

    def test_a_tile_is_its_color_a_glow_and_its_icon(self) -> None:
        svg = self.box({"label": "Checkout web", "look": {"fill": "lavender", "icon": "monitor"}})
        top, foot = drawn.TILE_FILLS["lavender"]
        self.assertIn('<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/>' % (top, foot), svg)
        self.assertIn('rx="12" fill="%s" fill-opacity="0.25" class="glow"/>' % foot, svg)
        self.assertIn(drawn.own_icons()["monitor"], svg)
        # Named nothing, a shape carries its kind's icon.
        self.assertIn(drawn.own_icons()["database"], self.box({"shape": "cylinder", "label": "Ledger"}))

    def test_a_mark_stands_in_the_tiles_place_as_it_is_shipped(self) -> None:
        """Nothing behind it and nothing recolored: the providers publish
        their marks to be used unaltered (icons/CREDITS.md)."""
        svg = self.box({"label": "Fraud scoring", "look": {"fill": "rose", "icon": "aws/lambda"}})
        data = base64.b64encode((self.WEB / "icons" / "aws" / "lambda.svg").read_bytes()).decode("ascii")
        self.assertIn('<image x="51" y="8" width="48" height="48" href="data:image/svg+xml;base64,%s"/>' % data, svg)
        self.assertNotIn('class="glow"', svg)
        self.assertNotIn("linearGradient", svg)

    def test_a_tile_and_its_words_are_drawn_over_the_lines_on_what_lies_under_them(self) -> None:
        """A shape in a frame sits in the layer under the lines, so every
        tile is drawn last, its words on the frame's fill, or a line leaving
        the tile downward ran through its name."""
        items = [{"key": "f", "role": "frame", "label": "Platform", "at": [0, 0], "size": [400, 300],
                  "look": {"fill": "mint"}},
                 {"key": "a", "role": "shape", "label": "Checkout web", "in": ["f"], "at": [20, 40], "size": [150, 64]},
                 {"key": "b", "role": "shape", "label": "Card scheme", "at": [500, 40], "size": [150, 64]},
                 {"key": "l", "role": "line", "from": "a", "to": "b", "from_at": [0.5, 1]}]
        under, _ = drawn.paint(items, (0.0, 0.0), {}, drawn_metrics(), "under", (), "tiles")
        over, _ = drawn.paint(items, (0.0, 0.0), {}, drawn_metrics(), "over", (), "tiles")
        self.assertNotIn('data-role="shape"', under)
        self.assertLess(over.index('data-role="line"'), over.index('data-key="a" data-role="shape"'))
        inside = over.split('data-key="a" data-role="shape"', 1)[1].split('data-key="b"', 1)[0]
        outside = over.split('data-key="b" data-role="shape"', 1)[1]
        self.assertEqual([o.key for o in drawn.scene(items, (0.0, 0.0), {}, (), "tiles")], ["f", "l", "a", "b"])
        # A line listed first once took the diagram's look for its own, and
        # what came after it lost its tile on the slide and the page.
        first = drawn.scene([items[3]] + items[:3], (0.0, 0.0), {}, (), "tiles")
        self.assertEqual({o.key: o.look for o in first if o.role == "shape"}, {"a": "tiles", "b": "tiles"})
        self.assertEqual(next(o for o in first if o.role == "line").edge, drawn.TILE_LINE)
        self.assertIn('fill="%s" class="ground"/>' % FILLS["mint"], inside)
        self.assertIn('fill="%s" class="ground"/>' % drawn.TILE_SHEET, outside)
        self.assertIn(">Checkout web</text>", inside)

    def test_an_end_held_at_a_point_of_a_shape_is_that_point_of_its_tile(self) -> None:
        """The box is wider than the tile; held at its left side, an arrow
        stopped short in the air."""
        items = [{"key": "a", "role": "shape", "label": "Web", "at": [0, 40], "size": [150, 64]},
                 {"key": "b", "role": "shape", "label": "Ledger", "at": [500, 40], "size": [150, 64]},
                 {"key": "l", "role": "line", "from": "a", "to": "b", "to_at": [0, 0.5]}]
        tiled = next(o for o in drawn.scene(items, (0.0, 0.0), {}, (), "tiles") if o.role == "line")
        self.assertEqual(tiled.points[-1], (551.0, 72.0))
        self.assertEqual(drawn.scene(items, (0.0, 0.0), {})[-1].points[-1], (500.0, 72.0))

    def test_the_slide_and_the_page_draw_the_tile_and_its_words_under_it(self) -> None:
        from terrane.draw.dml import _Sheet, _own_xml
        from terrane.render_drawio import own_style
        items = [{"key": "a", "role": "shape", "label": "Checkout web", "at": [0, 0], "size": [150, 64],
                  "look": {"fill": "lavender"}}]
        own = drawn.scene(items, (0.0, 0.0), {}, (), "tiles")[0]
        top, foot = drawn.TILE_FILLS["lavender"]
        style = own_style(own)
        self.assertIn("fillColor=%s;gradientColor=%s;gradientDirection=south;" % (top, foot), style)
        self.assertIn("verticalLabelPosition=bottom;", style)
        xml = _own_xml(2, own, _Sheet((0, 0, 400, 200), (0, 0, 4, 2)))
        self.assertIn('<a:prstGeom prst="roundRect">', xml)
        self.assertIn('<a:gs pos="0"><a:srgbClr val="%s"/></a:gs>' % top.lstrip("#").upper(), xml)
        self.assertIn('anchor="t"', xml)

    def test_the_icons_file_reads_and_has_every_kinds_icon(self) -> None:
        icons = drawn.own_icons()
        self.assertGreaterEqual(len(icons), 24)
        for kind, name in drawn.KIND_ICONS.items():
            with self.subTest(kind=kind):
                self.assertIn("<", icons[name])


class TestStyle(unittest.TestCase):
    """The Style tab's settings (V16, redrawn for Illustrated): `opacity`,
    `weight`, `corners` and `shadow: none` in a look."""

    SHAPE = {"key": "s", "role": "shape", "shape": "rectangle", "label": "Ledger", "at": [0, 0], "size": [150, 64]}

    def box(self, item: dict, look: str = "illustrated") -> str:
        return drawn._box(dict(self.SHAPE, **item), (0.0, 0.0, 150.0, 64.0), drawn_metrics(), look)

    def test_read_and_refused_where_they_mean_nothing(self) -> None:
        look = {"opacity": 60, "weight": "l", "corners": 10, "shadow": "none"}
        self.assertEqual(read([dict(self.SHAPE, look=look)], "here")[0]["look"], look)
        line = {"key": "l", "role": "line", "from": [0, 0], "to": [10, 10]}
        for item, said in ((dict(self.SHAPE, look={"opacity": 5}), "a whole percent from 10 to 100"),
                           (dict(self.SHAPE, look={"opacity": 60.5}), "a whole percent"),
                           (dict(self.SHAPE, look={"opacity": True}), "a whole percent"),
                           (dict(self.SHAPE, look={"weight": "xl"}), "one of s, m, l"),
                           (dict(self.SHAPE, look={"corners": MOST_CORNERS + 1}), "from 0 to %d" % MOST_CORNERS),
                           (dict(self.SHAPE, look={"shadow": "soft"}), "look.shadow is none"),
                           (dict(line, look={"opacity": 60}), "which a line does not have"),
                           (dict(self.SHAPE, role="frame", look={"shadow": "none"}), "which a frame does not cast")):
            with self.subTest(said=said), self.assertRaises(AnnotationError) as caught:
                read([item], "here")
            self.assertIn(said, str(caught.exception))

    def test_the_picture_draws_them(self) -> None:
        svg = self.box({"look": {"opacity": 60, "weight": "l", "corners": 10}})
        self.assertIn('rx="10" fill="#fffdf8" fill-opacity="0.6" stroke="%s" stroke-width="2"' % drawn.INK, svg)
        self.assertIn('stroke-width="1"', self.box({"look": {"weight": "s"}}))
        # Square, a rounded box is a plain rectangle; an ellipse has no
        # corners to round, Illustrated.
        self.assertNotIn("rx=", self.box({"shape": "rounded", "look": {"corners": 0}}))
        self.assertIsNone(drawn.corners_of(dict(self.SHAPE, shape="ellipse", look={"corners": 10})))
        self.assertEqual(drawn.corners_of(dict(self.SHAPE, shape="ellipse", look={"corners": 10}), "tiles"), 10.0)

    def test_no_shadow_when_it_says_none_or_its_fill_is_see_through(self) -> None:
        self.assertIn('class="shadow"', self.box({}))
        self.assertNotIn('class="shadow"', self.box({"look": {"shadow": "none"}}))
        self.assertNotIn('class="shadow"', self.box({"look": {"opacity": 90}}))

    def test_as_tiles_a_tile_takes_its_corners_and_opacity(self) -> None:
        svg = self.box({"look": {"corners": 4, "opacity": 50}}, "tiles")
        self.assertIn('rx="4" fill="%s" fill-opacity="0.12" class="glow"' % drawn.TILE_FILLS["white"][1], svg)
        self.assertRegex(svg, r'rx="4" fill="url\(#tile-s\)" fill-opacity="0.5"/>')

    def test_the_slide_and_the_page_draw_them(self) -> None:
        from terrane.draw.dml import _Sheet, _own_xml
        from terrane.render_drawio import own_style
        sheet = _Sheet((0, 0, 400, 200), (0, 0, 4, 2))
        own = drawn.scene([dict(self.SHAPE, look={"opacity": 60, "weight": "l", "corners": 16})], (0.0, 0.0), {})[0]
        self.assertEqual((own.opacity, own.weight, own.corners), (0.6, 2.0, 16.0))
        xml = _own_xml(2, own, sheet)
        self.assertIn('<a:srgbClr val="FFFDF8"><a:alpha val="60000"/></a:srgbClr>', xml)
        self.assertIn('<a:ln w="%d">' % sheet.line(2.0), xml)
        self.assertIn('<a:gd name="adj" fmla="val 25000"/>', xml)
        style = own_style(own)
        for part in ("strokeWidth=2;", "fillOpacity=60;", "rounded=1;absoluteArcSize=1;arcSize=32;"):
            with self.subTest(part=part):
                self.assertIn(part, style)
        self.assertNotIn("shadow=1;", style)

    def test_the_canvas_weighs_an_edge_alike(self) -> None:
        engine = ENGINE.read_text(encoding="utf-8")
        self.assertIn("var WEIGHTS = { s: %g, m: %g, l: %g };" % (WEIGHTS["s"], WEIGHTS["m"], WEIGHTS["l"]), engine)
        canvas = (REPO / "80_APP" / "web" / "canvas" / "canvas.js").read_text(encoding="utf-8")
        self.assertIn('class: "cv-range", min: "0", max: "%d"' % MOST_CORNERS, canvas)

    def test_the_schema_admits_them(self) -> None:
        props = jsonschema.view_schema()["properties"]["annotations"]["items"]["properties"]["look"]["properties"]
        self.assertEqual(sorted(props), sorted(["fill", "line", "text", "icon", "opacity", "weight", "corners", "shadow"]))


class TestIllustrated(unittest.TestCase):
    """The look of the diagram's own (V16): the app's own picture
    language, ink edges, a hard shadow, a name over a caption."""

    def box(self, item: dict, box=(0.0, 0.0, 150.0, 64.0)) -> str:
        return drawn._box(dict({"key": "k"}, **item), box, drawn_metrics())

    def test_a_shape_and_a_note_stand_on_a_hard_shadow(self) -> None:
        shape = self.box({"role": "shape", "shape": "rounded", "label": "Payments API"})
        self.assertIn('<rect x="4" y="4" width="150" height="64" rx="6" fill="%s" class="shadow"/>' % drawn.INK, shape)
        self.assertIn('stroke="%s"' % drawn.INK, shape)
        self.assertIn('class="shadow"', self.box({"role": "note", "label": "Goes live"}))
        for flat in ({"role": "text", "label": "A title"}, {"role": "frame", "label": "Platform"},
                     {"role": "shape", "label": "Edgeless", "look": {"line": "none"}}):
            with self.subTest(role=flat["role"]):
                self.assertNotIn('class="shadow"', self.box(flat, (0.0, 0.0, 300.0, 200.0)))

    def test_the_first_line_is_the_name_and_the_rest_a_caption(self) -> None:
        rows = drawn.named_rows("Payments API\n\nREST, three regions", 136, drawn_metrics(), 13)
        self.assertEqual([(t, f, s) for t, f, s in rows],
                         [("Payments API", drawn.NAME_FACE, 13), ("REST, three regions", ("Geist", 400), 11)])
        svg = self.box({"role": "shape", "label": "Payments API\nREST, three regions"})
        self.assertIn('font-family="%s"' % drawn.NAME_FAMILIES, svg)
        self.assertIn('fill="%s" text-anchor="middle">REST, three regions' % drawn.CAPTION_INK, svg)
        self.assertLess(svg.index("Payments API"), svg.index("REST, three regions"))

    def test_accent_carries_its_words_in_paper(self) -> None:
        svg = self.box({"role": "shape", "label": "Payments API\nREST", "look": {"fill": "accent"}})
        self.assertIn('fill="%s"' % FILLS["accent"], svg)
        self.assertIn('fill="%s" text-anchor="middle" font-family' % WORDS_ON["accent"], svg)
        self.assertIn('fill="%s" fill-opacity="0.75"' % WORDS_ON["accent"], svg)

    def test_a_frame_is_unfilled_and_named_on_an_ink_tab(self) -> None:
        svg = self.box({"role": "frame", "label": "Payments platform"}, (0.0, 0.0, 400.0, 300.0))
        self.assertIn('fill="none" stroke="%s"' % drawn.INK, svg)
        self.assertRegex(svg, r'<rect x="12" y="-[\d.]+" width="[\d.]+" height="[\d.]+" rx="3" fill="%s"/>' % drawn.INK)
        self.assertIn('fill="%s">Payments platform</text>' % drawn.PAPER, svg)

    def test_the_cylinders_lid_is_wound_as_its_body(self) -> None:
        """Wound the other way, the lid was a hole in the fill, and the ink
        shadow under it showed through as a black band."""
        lid = drawn.PATHS["cylinder"][5:]
        self.assertEqual(lid[0], ("M", 1, 0.12))
        self.assertEqual(lid[1][-2:], (0, 0.12))

    def test_the_display_face_rides_only_where_it_is_set(self) -> None:
        from terrane.draw.svg import font_face_urls
        named = self.box({"role": "shape", "label": "Payments API"})
        self.assertIn("Libre Franklin", font_face_urls("fonts/", named))
        self.assertNotIn("Libre Franklin", font_face_urls("fonts/", self.box({"role": "note", "label": "x"})))

    def test_words_on_many_lines_are_written_as_they_were(self) -> None:
        """Folded, a name and its caption came back joined by a space."""
        from terrane import yamlish
        from terrane.sketch import yaml_text
        text = yaml_text({"annotations": [{"key": "s", "label": "Payments API\nREST, three regions"}]})
        self.assertIn("label: |-", text)
        self.assertEqual(yamlish.loads(text)["annotations"][0]["label"], "Payments API\nREST, three regions")


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

    def test_a_diagrams_look_is_saved_read_and_drawn(self) -> None:
        data = dict(OWN_ONLY, look="tiles", annotations=[
            {"key": "s", "role": "shape", "label": "Fraud scoring", "at": [0, 0], "size": [150, 64],
             "look": {"icon": "aws/lambda"}}])
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertEqual(saved["errors"], [])
        text = (self.root / saved["path"]).read_text(encoding="utf-8")
        self.assertLess(text.index("\nlook: tiles\n"), text.index("\nannotations:\n"))
        self.assertEqual(self.server.api_view({"id": [saved["id"]]}, {})["data"]["look"], "tiles")
        svg = self.server.api_svg({"view": [saved["id"]]})
        self.assertIn("data:image/svg+xml;base64,", svg)
        self.assertIn('data-key="s" data-role="shape"', svg)
        self.assertIn('class="ground"', svg)

    def test_the_marks_are_listed_for_the_panel_and_baked_for_the_hosted_copy(self) -> None:
        marks = self.server.api_icons({}, None)["marks"]
        self.assertEqual(marks, IconMap(REPO / "80_APP" / "web").listing())
        self.assertIn(("GET", "/api/icons"), self.server.ROUTES)
        shim = (REPO / "80_APP" / "web" / "static-shim.js").read_text(encoding="utf-8")
        self.assertIn('if (p === "api/icons") return "api/icons.json";', shim)
        site = (REPO / "80_APP" / "tools" / "export_site.py").read_text(encoding="utf-8")
        self.assertIn('_write(api / "icons.json", _call(server.api_icons))', site)

    def test_a_diagram_of_its_own_shapes_alone_is_saved_checked_and_drawn(self) -> None:
        data = dict(OWN_ONLY)
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertEqual((saved["created"], saved["errors"]), (True, []))
        svg = self.server.api_svg({"view": [saved["id"]]})
        self.assertEqual(svg.count('class="own"'), 3)


if __name__ == "__main__":
    unittest.main()
