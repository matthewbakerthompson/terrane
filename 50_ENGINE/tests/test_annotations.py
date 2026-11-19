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
fill casting no shadow, and the canvas's weights the same. How the words
are set (bold, italic, underlined, struck through, where they sit, a list),
refused where a kind cannot take it and drawn alike by every painter; a
diagram's saved styles read and refused as a look is, and the canvas's
five styles and what it paints all looks the engine reads. A link on
one of its own, an address on the web or for email and nothing else, made
a link of the picture's, a slide's hyperlink and draw.io's own. A
diagram's groups, read and refused where a key does not hold together, and
drawn by nothing. A swimlane, its pool and lanes read and refused where they
do not hold together, drawn alike by every painter, a lane named as the
record it stands for and listed on its page. A diagram's drawing layers,
read and refused where the keys do not hold together, a hidden one left
out of every picture, the rest drawn bottom first, and one under the
estate drawn under its records. A diagram's pages, each a view of its own
read from the diagram's fields and the page's, refused where a key or what
is on a page does not hold. Saved styles kept for the whole estate in
model.yaml, read and refused as a diagram's are and checked by validate.
A line's words at its start and its end, Dotted, how heavy it is and its
turns rounded, drawn alike by every painter from the canvas's numbers. Last, the file: the list is written before positions, a
diagram of its own shapes alone is saved, validated and drawn, and so are
its look, its saved styles and its groups.
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
from terrane.annotations import (FILLS, LINK, LOOK_KEYS, MOST_CORNERS, SHAPES, TEXT_SIZES,  # noqa: E402
                                 WEIGHTS, WORDS_ON, AnnotationError, check_look, read)
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
            (dict(note, look={"line": "wavy"}), "look.line is one of"),
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
    """A line's bends (`via`): a straight line's points of the sheet, and a
    square or curved line's turns kept where its stretches were moved by
    hand (V16), read, refused where they are no points, and drawn through
    by the picture and by the scene the deck and the draw.io page are
    painted from."""

    LINE = {"key": "l", "role": "line", "from": [0, 0], "to": [200, 0], "via": [[100, 80]]}

    def test_read_on_any_line_and_refused_where_they_are_no_points(self) -> None:
        self.assertEqual(read([self.LINE], "here")[0]["via"], [[100, 80]])
        self.assertEqual(read([dict(self.LINE, route="square")], "here")[0]["via"], [[100, 80]])
        for wrong, said in ((dict(self.LINE, via=[]), "bends at"),
                            (dict(self.LINE, via=[[1, 2, 3]]), "bends at"), (dict(self.LINE, via="here"), "bends at")):
            with self.subTest(wrong=wrong), self.assertRaises(AnnotationError) as caught:
                read([wrong], "here")
            self.assertIn(said, str(caught.exception))

    def test_a_square_line_keeps_its_turns_and_leaves_each_box_square(self) -> None:
        boxes = [{"key": "a", "role": "shape", "label": "A", "at": [0, 0], "size": [100, 50]},
                 {"key": "b", "role": "shape", "label": "B", "at": [300, 200], "size": [100, 50]}]
        # Its middle stretch carried to x 160, then a box that faces neither
        # turn: B's last turn needs a turn of its own toward B's middle.
        line = {"key": "l", "role": "line", "from": "a", "to": "b", "route": "square", "via": [[160, 25], [160, 120]]}
        own = [o for o in drawn.scene(boxes + [line], (0.0, 0.0), {}) if o.role == "line"][0]
        self.assertEqual(own.points, ((100.0, 25.0), (160.0, 25.0), (160.0, 120.0), (160.0, 225.0), (300.0, 225.0)))
        for p, q in zip(own.points, own.points[1:]):
            self.assertTrue(p[0] == q[0] or p[1] == q[1], (p, q))
        # A turn over its box leaves the box from under it, not its middle.
        line = dict(line, via=[[60, 120], [350, 120]])
        own = [o for o in drawn.scene(boxes + [line], (0.0, 0.0), {}) if o.role == "line"][0]
        self.assertEqual(own.points, ((60.0, 50.0), (60.0, 120.0), (350.0, 120.0), (350.0, 200.0)))
        self.assertEqual(drawn.kept_turns((0, 0, 10, 10), (100, 100, 110, 110), [(50, 5)]), [(50, 5), (50, 105.0)])

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

    def test_a_swimlane_is_drawn_from_the_same_numbers(self) -> None:
        for js, py in (("POOL_TITLE", drawn.POOL_TITLE), ("LANE_COLUMN", drawn.LANE_COLUMN),
                       ("LANE_BAND", drawn.LANE_BAND), ("BAND", drawn.BAND)):
            with self.subTest(name=js):
                self.assertEqual(self.scalar(js), py)

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
        self.assertEqual(sorted(props), sorted(LOOK_KEYS))


class TestWords(unittest.TestCase):
    """V16's words toolbar: `bold`, `italic`, `underline`, `strike`,
    `align` and a note's or text's `list` in a look, for all its words."""

    NOTE = {"key": "n", "role": "note", "label": "Moves in Q2\nKeeps its keys", "at": [0, 0], "size": [170, 80]}
    SHAPE = {"key": "s", "role": "shape", "shape": "rounded", "label": "Payments API\nREST", "at": [0, 0],
             "size": [150, 64]}

    def draw(self, item: dict, look: dict, box=None) -> str:
        item = dict(item, look=look)
        size = item["size"]
        return drawn._box(item, box or (0.0, 0.0, float(size[0]), float(size[1])), drawn_metrics())

    def test_read_and_refused_where_a_kind_cannot_take_it(self) -> None:
        look = {"bold": True, "italic": True, "underline": True, "strike": True, "align": "right"}
        self.assertEqual(read([dict(self.NOTE, look=dict(look, list=True))], "here")[0]["look"]["list"], True)
        self.assertEqual(read([dict(self.SHAPE, look=look)], "here")[0]["look"], look)
        frame = {"key": "f", "role": "frame", "label": "Platform", "at": [0, 0], "size": [300, 200]}
        line = {"key": "l", "role": "line", "from": [0, 0], "to": [10, 10]}
        for item, said in ((dict(frame, look={"bold": True}), "bold already"),
                           (dict(frame, look={"align": "center"}), "at its left"),
                           (dict(self.SHAPE, look={"list": True}), "a note's or text's words take, not a shape's"),
                           (dict(line, look={"italic": True}), "which a line's words do not take"),
                           (dict(self.NOTE, look={"bold": "yes"}), "look.bold is true, or left out"),
                           (dict(self.NOTE, look={"align": "justify"}), "look.align is one of left, center, right")):
            with self.subTest(said=said), self.assertRaises(AnnotationError) as caught:
                read([item], "here")
            self.assertIn(said, str(caught.exception))

    def test_the_picture_sets_a_notes_words(self) -> None:
        svg = self.draw(self.NOTE, {"bold": True, "italic": True, "underline": True, "strike": True})
        self.assertIn('font-weight="600" fill="%s" font-style="italic" text-decoration="underline line-through">'
                      'Moves in Q2</text>' % drawn.INK, svg)
        right = self.draw(self.NOTE, {"align": "right"})
        self.assertIn('<text x="160" ', right)
        self.assertIn('text-anchor="end">Moves in Q2</text>', right)

    def test_a_list_bullets_each_line_and_wraps_past_the_bullet(self) -> None:
        svg = self.draw(self.NOTE, {"list": True})
        self.assertEqual(svg.count(">•</text>"), 2)
        self.assertIn('<text x="10" ', svg)
        self.assertIn('<text x="23" ', svg)
        # A line the bullet narrows wraps a word sooner than it would bare.
        long = dict(self.NOTE, label="Keeps its keys in the vault, with rotation every ninety days")
        bare = self.draw(long, {}).count("</text>")
        listed = self.draw(long, {"list": True}).count("</text>") - 1
        self.assertGreaterEqual(listed, bare)

    def test_the_picture_sets_a_shapes_caption_with_its_name(self) -> None:
        svg = self.draw(self.SHAPE, {"bold": True, "align": "left"})
        self.assertIn('font-weight="600" fill="%s">REST</text>' % drawn.CAPTION_INK, svg)
        self.assertIn('<text x="8" ', svg)
        self.assertNotIn('text-anchor="middle"', svg)
        tab = drawn._box({"key": "f", "role": "frame", "label": "Platform", "look": {"italic": True}},
                         (0.0, 0.0, 300.0, 200.0), drawn_metrics())
        self.assertIn('font-style="italic">Platform</text>', tab)

    def test_the_slide_and_the_page_set_them(self) -> None:
        from terrane.draw.dml import _Sheet, _own_xml
        from terrane.render_drawio import _own_label, own_style
        sheet = _Sheet((0, 0, 400, 200), (0, 0, 4, 2))
        note = drawn.scene([dict(self.NOTE, look={"list": True, "italic": True, "underline": True, "strike": True})],
                           (0.0, 0.0), {})[0]
        self.assertEqual((note.listed, note.italic, note.underline, note.strike), (True, True, True, True))
        xml = _own_xml(2, note, sheet)
        self.assertEqual(xml.count('<a:buChar char="•"/>'), 2)
        self.assertIn(' i="1" u="sng" strike="sngStrike"', xml)
        self.assertIn("fontStyle=14;", own_style(note))
        self.assertIn("• Moves in Q2<br>• Keeps its keys", _own_label(note))
        shape = drawn.scene([dict(self.SHAPE, look={"bold": True, "align": "right"})], (0.0, 0.0), {})[0]
        self.assertIn('algn="r"', _own_xml(2, shape, sheet))
        self.assertIn("fontStyle=1;align=right;", own_style(shape))


class TestLink(unittest.TestCase):
    """The words toolbar's last button: `link:` on one of its own, where a
    click on it goes."""

    ADDRESS = "https://wiki.example/runbook?a=1&b=2"
    LINKED = {"key": "s", "role": "shape", "shape": "rounded", "label": "Runbook", "at": [0, 0], "size": [150, 64],
              "link": ADDRESS}

    def test_read_and_refused_unless_on_the_web_or_for_email(self) -> None:
        self.assertEqual(read([self.LINKED], "here")[0]["link"], self.ADDRESS)
        mail = dict(self.LINKED, role="note", link="mailto:ops@example.com")
        self.assertEqual(read([mail], "here")[0]["link"], "mailto:ops@example.com")
        line = {"key": "l", "role": "line", "from": [0, 0], "to": [10, 10], "link": "https://x.example"}
        for item, said in ((dict(self.LINKED, link="www.example.com"), "starting https://, http:// or mailto:"),
                           (dict(self.LINKED, link="javascript:alert(1)"), "starting https://"),
                           (dict(self.LINKED, link="https://a b"), "starting https://"),
                           (dict(self.LINKED, link="https://x.example/" + "a" * 2000), "starting https://"),
                           (line, "which a line does not")):
            with self.subTest(said=said, link=str(item.get("link"))[:30]), self.assertRaises(AnnotationError) as caught:
                read([item], "here")
            self.assertIn(said, str(caught.exception))

    def test_the_picture_makes_the_shape_a_link(self) -> None:
        svg = drawn._box(self.LINKED, (0.0, 0.0, 150.0, 64.0), drawn_metrics())
        safe = "https://wiki.example/runbook?a=1&amp;b=2"
        self.assertTrue(svg.startswith('<a href="%s" target="_blank" rel="noopener"><title>%s</title>' % (safe, safe)), svg[:120])
        self.assertTrue(svg.endswith("</a>"))
        self.assertIn('data-key="s" data-role="shape"', svg)
        self.assertFalse(drawn._box(dict(self.LINKED, link=""), (0.0, 0.0, 150.0, 64.0), drawn_metrics()).startswith("<a "))
        tile = drawn._box(self.LINKED, (0.0, 0.0, 150.0, 64.0), drawn_metrics(), "tiles")
        self.assertTrue(tile.startswith('<a href="%s"' % safe))

    def test_the_slide_and_the_page_carry_it(self) -> None:
        from terrane.draw.dml import scene_links, slide_shapes
        from terrane.draw.svg import Scene
        from terrane.pptx import REL, Deck
        from terrane.render_drawio import diagram_xml
        own = tuple(drawn.scene([self.LINKED, dict(self.LINKED, key="t", at=[200, 0])], (0.0, 0.0), {}))
        self.assertEqual(own[0].link, self.ADDRESS)
        scene = Scene((0.0, 0.0, 400.0, 100.0), [], [], [], True, "own", own)
        self.assertEqual(scene_links(scene), [self.ADDRESS])
        shapes = "".join(slide_shapes(scene, (0.5, 1.0, 12.8, 7.0), 2))
        self.assertEqual(shapes.count('><a:hlinkClick r:id="rIdLink1"/></p:cNvPr>'), 2)
        slide = Deck("t").slide()
        slide.hyperlinks(scene_links(scene))
        self.assertIn('<Relationship Id="rIdLink1" Type="%shyperlink" Target="https://wiki.example/runbook?a=1&amp;b=2" '
                      'TargetMode="External"/>' % REL, slide.rels(1))
        self.assertEqual(diagram_xml(scene).count('link="https://wiki.example/runbook?a=1&amp;b=2"'), 2)

    def test_the_canvas_takes_the_same_addresses(self) -> None:
        canvas = (REPO / "80_APP" / "web" / "canvas" / "canvas.js").read_text(encoding="utf-8")
        self.assertIn(r"var LINK = /^(https?:\/\/|mailto:)\S+$/;", canvas)
        self.assertEqual(LINK.pattern, r"(https?://|mailto:)\S+")


class TestGroups(unittest.TestCase):
    """V16's groups: the diagram's own picked and moved as one, a key and a
    name in `groups:` and `group:` on each of its own in one."""

    def view(self, groups, grouped=None):
        items = [dict(item) for item in LANDING[:3]]
        for key, group in (grouped or {}).items():
            next(item for item in items if item["key"] == key)["group"] = group
        return parse_view(dict(OWN_ONLY, annotations=items, groups=groups))

    def test_read_with_the_group_each_sits_in(self) -> None:
        view = self.view([{"key": "outer", "name": " Platform "}, {"key": "inner", "name": "Security", "group": "outer"}],
                         {"ou-security": "inner", "guardrails": "inner", "org": "outer"})
        self.assertEqual(view.groups, ({"key": "outer", "name": "Platform"},
                                       {"key": "inner", "name": "Security", "group": "outer"}))
        self.assertEqual([a.get("group") for a in view.annotations], ["outer", "inner", "inner"])
        self.assertEqual(parse_view(OWN_ONLY).groups, ())

    def test_refused_where_a_key_does_not_hold_together(self) -> None:
        for groups, grouped, said in (
                ("Platform", {}, "is a list, each a key, a name"),
                ([{"key": "g", "name": ""}], {}, "number 1 is a key, a name of up to 60 characters"),
                ([{"key": "g", "name": "x" * 61}], {}, "number 1 is a key, a name of up to 60 characters"),
                ([{"key": "g", "name": "G", "color": "red"}], {}, "number 1 is a key"),
                ([{"key": "g", "name": "G"}, {"key": "g", "name": "H"}], {}, "g is the key of two"),
                ([{"key": "g", "name": "G", "group": "h"}], {}, "g is in h, which the diagram does not name"),
                ([{"key": "g", "name": "G", "group": "g"}], {}, "g is in itself"),
                ([{"key": "g", "name": "G", "group": "h"}, {"key": "h", "name": "H", "group": "g"}], {},
                 "g is in itself, by way of h"),
                ([{"key": "g", "name": "G"}], {"org": "h"}, "org is in group h, which the diagram's groups do not name")):
            with self.subTest(said=said), self.assertRaises(ViewError) as caught:
                self.view(groups, grouped)
            self.assertIn(said, str(caught.exception))

    def test_only_a_box_is_in_one(self) -> None:
        line = {"key": "l", "role": "line", "from": [0, 0], "to": [10, 10], "group": "g"}
        for item, said in ((line, "which a line does not"),
                           (dict(LANDING[2], group=" "), "group is the key of one of the diagram's groups")):
            with self.subTest(said=said), self.assertRaises(AnnotationError) as caught:
                read([item], "here")
            self.assertIn(said, str(caught.exception))

    def test_the_schema_keeps_a_key_a_name_and_where_it_sits(self) -> None:
        schema = jsonschema.view_schema()["properties"]["groups"]["items"]
        self.assertEqual(schema["required"], ["key", "name"])
        self.assertEqual(sorted(schema["properties"]), ["group", "key", "name"])
        self.assertEqual(schema["properties"]["name"]["maxLength"], 60)

    def test_drawn_by_nothing(self) -> None:
        items = [{"key": "a", "role": "shape", "shape": "rounded", "label": "Gateway", "at": [0, 0], "size": [150, 64]},
                 {"key": "b", "role": "shape", "shape": "rounded", "label": "Ledger", "at": [200, 0], "size": [150, 64]}]
        grouped = [dict(item, group="g") for item in items]
        for layer in ("under", "over"):
            with self.subTest(layer=layer):
                self.assertEqual(drawn.paint(grouped, (0.0, 0.0), {}, drawn_metrics(), layer),
                                 drawn.paint(items, (0.0, 0.0), {}, drawn_metrics(), layer))
        self.assertEqual([o.box for o in drawn.scene(grouped, (0.0, 0.0), {})],
                         [o.box for o in drawn.scene(items, (0.0, 0.0), {})])

    def test_the_canvas_keeps_them_and_hears_a_double_click_first(self) -> None:
        web = REPO / "80_APP" / "web" / "canvas"
        engine = (web / "engine.js").read_text(encoding="utf-8")
        canvas = (web / "canvas.js").read_text(encoding="utf-8")
        self.assertIn("if (a.group) item.group = a.group;", engine)
        # Undo puts the groups back with what is in them, and the layers.
        self.assertIn("locked: cv.data.locked || [], groups: cv.data.groups || [], layers: cv.data.layers || null });",
                      canvas)
        # maxGraph's own double-click on a shape stops the event there: heard
        # on the way up, the words opened only on an empty spot.
        self.assertIn("      editText(cell);\n    }, true);", engine)
        # Ctrl+D on several gave every copy one key until a key in the
        # model counted as taken.
        self.assertIn('!used[role + "-" + n] && !s.model.getCell(idOf(role + "-" + n))', engine)


#: A swimlane as the canvas draws one: two lanes across it, the first
#: standing for an org unit, a shape in the second.
SWIMLANE = [
    {"key": "pool-1", "role": "pool", "label": "Card payment, by who does it", "at": [0, 0], "size": [960, 354]},
    {"key": "lane-1", "role": "lane", "label": "Payments Operations", "in": ["pool-1"], "at": [0, 34],
     "size": [960, 160], "stands_for": "ORG-PAYMENTS"},
    {"key": "lane-2", "role": "lane", "label": "Cardholder", "in": ["pool-1"], "at": [0, 194], "size": [960, 160]},
    {"key": "shape-1", "role": "shape", "shape": "rounded", "label": "Pays at checkout", "in": ["pool-1", "lane-2"],
     "at": [170, 50], "size": [150, 60]},
]


class TestSwimlanes(unittest.TestCase):
    """V16's swimlane: a pool, its lanes in it, what is drawn in a lane in
    it, and a lane that stands for a record."""

    def test_read_as_the_canvas_writes_one(self) -> None:
        read_back = read(SWIMLANE + [dict(SWIMLANE[0], key="pool-2", runs="down", names="top", at=[0, 400])], "here")
        self.assertEqual([a["role"] for a in read_back], ["pool", "lane", "lane", "shape", "pool"])
        self.assertEqual(read_back[1]["stands_for"], "ORG-PAYMENTS")
        self.assertEqual((read_back[4]["runs"], read_back[4]["names"]), ("down", "top"))

    def test_refused_where_it_does_not_hold_together(self) -> None:
        pool, lane, shape = SWIMLANE[0], SWIMLANE[1], SWIMLANE[3]
        for items, said in (
                ([dict(lane, **{"in": []})], "lane-1 is a lane, and sits in a swimlane"),
                ([pool, dict(shape, **{"in": ["pool-1"]})], "shape-1 sits in the swimlane pool-1 itself"),
                ([dict(pool, runs="sideways")], "runs is across or down"),
                ([dict(pool, names="bottom")], "names is where each lane's name sits"),
                ([pool, dict(lane, stands_for="")], "stands_for is the id of the record"),
                ([dict(pool, look={"fill": "rose"})], "look has fill, which a swimlane's pool does not take"),
                ([dict(shape, stands_for="ORG-PAYMENTS", **{"in": []})], "has stands_for, which a shape does not"),
                ([dict(pool, rotate=10)], "a pool is not turned")):
            with self.subTest(said=said), self.assertRaises(AnnotationError) as caught:
                read(items, "here")
            self.assertIn(said, str(caught.exception))

    def test_the_picture_draws_the_band_the_columns_and_the_names(self) -> None:
        svg, _ = drawn.paint(SWIMLANE, (0.0, 0.0), {}, drawn_metrics(), "under")
        self.assertIn('<rect x="0" y="0" width="960" height="34" fill="%s"' % drawn.BAND, svg)
        self.assertIn('<rect x="0" y="34" width="130" height="160" fill="%s"' % drawn.BAND, svg)
        self.assertIn(">Card payment, by who does it</text>", svg)
        # The org unit's name wraps in its column, and its id is under it.
        self.assertIn(">Payments</text>", svg)
        self.assertIn(">Operations</text>", svg)
        self.assertIn('fill="%s">ORG-PAYMENTS</text>' % drawn.CAPTION_INK, svg)
        # What is in a lane goes with the swimlane, under the estate.
        self.assertIn('data-key="shape-1"', svg)
        self.assertEqual(drawn.layer_of(SWIMLANE[3], drawn.place(SWIMLANE, (0.0, 0.0)), ()), "under")

    def test_names_at_the_top_sit_in_a_band(self) -> None:
        items = [dict(SWIMLANE[0], names="top")] + SWIMLANE[1:]
        svg, _ = drawn.paint(items, (0.0, 0.0), {}, drawn_metrics(), "under")
        self.assertIn('<rect x="0" y="34" width="960" height="40" fill="%s"' % drawn.BAND, svg)
        self.assertIn(">Payments Operations</text>", svg)

    def test_the_slide_and_the_page_draw_the_same_parts(self) -> None:
        from terrane.draw.dml import slide_shapes
        from terrane.draw.svg import Scene
        from terrane.render_drawio import diagram_xml
        own = tuple(drawn.scene(SWIMLANE, (0.0, 0.0), {}))
        by_key = {o.key: o for o in own}
        self.assertEqual((by_key["pool-1"].role, by_key["pool-1"].corners, by_key["pool-1"].label), ("frame", 0.0, ""))
        self.assertEqual(by_key["lane-1"].within, "pool-1")
        self.assertEqual(by_key["shape-1"].within, "lane-2")
        words = [o.label for o in own if o.within in ("pool-1", "lane-1") and o.role == "note"]
        self.assertEqual(words, ["Card payment, by who does it", "Payments\nOperations", "ORG-PAYMENTS"])
        scene = Scene((0.0, 0.0, 960.0, 354.0), [], [], [], True, "own", own)
        shapes = "".join(slide_shapes(scene, (0.5, 1.0, 12.8, 7.0), 2))
        self.assertIn(">ORG-PAYMENTS<", shapes)
        page = diagram_xml(scene)
        self.assertIn('id="own-lane-1"', page)
        self.assertIn('parent="own-lane-2"', page)
        self.assertIn("ORG-PAYMENTS", page)

    def test_a_lane_is_named_as_its_record_is_now(self) -> None:
        from terrane.annotations import follow_names
        model = seeded_model()
        named = follow_names([dict(SWIMLANE[1], label="Payments Ops (old)")], model)
        self.assertEqual(named[0]["label"], model.find("ORG-PAYMENTS")[1]["name"])
        gone = follow_names([dict(SWIMLANE[1], stands_for="ORG-NOT-HERE", label="Kept")], model)
        self.assertEqual(gone[0]["label"], "Kept")

    def test_the_records_page_lists_the_diagram_it_has_a_lane_on(self) -> None:
        from terrane import levels
        view = parse_view(dict(OWN_ONLY, annotations=SWIMLANE))
        groups = levels.diagrams_of(seeded_model(), [view], "ORG-PAYMENTS")
        lanes = [g for g in groups if g["kind"] == "lanes"]
        self.assertEqual([i["viewId"] for i in lanes[0]["items"]], ["landing-zone"])
        self.assertEqual(lanes[0]["name"], "")
        self.assertFalse([g for g in levels.diagrams_of(seeded_model(), [view], "ACT-CARDHOLDER") if g["kind"] == "lanes"])

    def test_the_schema_takes_it(self) -> None:
        item = jsonschema.view_schema()["properties"]["annotations"]["items"]
        self.assertIn("pool", item["properties"]["role"]["enum"])
        self.assertIn("lane", item["properties"]["role"]["enum"])
        self.assertEqual(item["properties"]["runs"]["enum"], ["across", "down"])
        self.assertEqual(item["properties"]["names"]["enum"], ["left", "top"])
        self.assertIn("stands_for", item["properties"])


#: Three drawing layers, top first, the estate's records between the
#: first two: notes over the records, the sketch under them, and a hidden
#: layer of review marks.
LAYERS = [{"key": "review", "name": "Review marks", "hidden": True}, {"key": "notes", "name": "Notes"},
          {"key": "estate"}, {"key": "sketch", "name": "Sketch", "locked": True}]


class TestLayers(unittest.TestCase):
    """V16's drawing layers: `layers:` top first, the estate's records
    among them, and `layer:` on each of the diagram's own."""

    ITEMS = [
        {"key": "f", "role": "frame", "label": "Platform", "at": [0, 0], "size": [400, 300], "layer": "sketch"},
        {"key": "in-f", "role": "note", "label": "In the frame", "in": ["f"], "at": [20, 40], "size": [120, 60]},
        {"key": "a", "role": "shape", "label": "Gateway", "at": [500, 0], "size": [150, 64]},
        {"key": "b", "role": "shape", "label": "Ledger", "at": [700, 0], "size": [150, 64], "layer": "sketch"},
        {"key": "r", "role": "note", "label": "Who signs off?", "at": [900, 0], "size": [150, 64], "layer": "review"},
        {"key": "l", "role": "line", "from": "a", "to": "b", "layer": "review"},
    ]

    def view(self, layers, items=None):
        return parse_view(dict(OWN_ONLY, layers=layers, annotations=items or self.ITEMS))

    def test_read_top_first_with_the_estate_among_them(self) -> None:
        view = self.view(LAYERS)
        self.assertEqual([layer["key"] for layer in view.layers], ["review", "notes", "estate", "sketch"])
        self.assertEqual(view.layers[2], {"key": "estate"})
        self.assertEqual(parse_view(OWN_ONLY).layers, ())

    def test_refused_where_the_keys_do_not_hold_together(self) -> None:
        for layers, items, said in (
                ("Notes", None, "is a list, top first"),
                ([{"name": "Notes"}], None, "number 1 is a key"),
                ([{"key": "notes", "name": "x" * 61}], None, "notes has a name of up to 60 characters"),
                ([{"key": "notes", "name": "Notes", "hidden": False}], None, "notes is hidden: true"),
                ([{"key": "notes", "name": "Notes"}, {"key": "notes", "name": "More"}], None, "notes is the key of two"),
                ([{"key": "estate", "name": "Records"}, {"key": "notes", "name": "Notes"}], None,
                 "estate is where the estate's records sit"),
                ([{"key": "estate"}], [], "has no layer to draw on"),
                (LAYERS, [dict(self.ITEMS[2], layer="nowhere")], "a is on layer nowhere, which the diagram's drawing"),
                (LAYERS, [dict(self.ITEMS[2], layer="estate")], "a is on layer estate")):
            with self.subTest(said=said), self.assertRaises(ViewError) as caught:
                self.view(layers, items)
            self.assertIn(said, str(caught.exception))
        with self.assertRaises(AnnotationError) as caught:
            read([dict(self.ITEMS[2], layer="")], "here")
        self.assertIn("layer is the key of one of the diagram's drawing layers", str(caught.exception))

    def test_a_hidden_layer_is_left_out_and_the_rest_drawn_bottom_first(self) -> None:
        from terrane.annotations import by_layer, layer_home
        self.assertEqual(layer_home(LAYERS), "notes")
        drawn_items = by_layer([dict(i) for i in self.ITEMS], LAYERS)
        # The review layer's note and line are gone; the sketch (under the
        # estate) first, the frame's note with its frame; then the notes.
        self.assertEqual([i["key"] for i in drawn_items], ["f", "in-f", "b", "a"])
        self.assertEqual([i["key"] for i in drawn_items if i.get("_under")], ["f", "in-f", "b"])
        self.assertEqual(by_layer([dict(i) for i in self.ITEMS], ()), [dict(i) for i in self.ITEMS])

    def test_a_layer_under_the_estate_is_drawn_under_its_records(self) -> None:
        from terrane.annotations import by_layer
        items = by_layer([dict(i) for i in self.ITEMS], LAYERS)
        boxes = drawn.place(items, (0.0, 0.0))
        self.assertEqual({i["key"]: drawn.layer_of(i, boxes, ()) for i in items},
                         {"f": "under", "in-f": "under", "b": "under", "a": "over"})
        under, _ = drawn.paint(items, (0.0, 0.0), {}, drawn_metrics(), "under")
        over, _ = drawn.paint(items, (0.0, 0.0), {}, drawn_metrics(), "over")
        self.assertIn('data-key="b"', under)
        self.assertNotIn('data-key="b"', over)
        self.assertNotIn("Who signs off?", under + over)

    def test_the_schema_takes_them(self) -> None:
        schema = jsonschema.view_schema()["properties"]
        self.assertEqual(schema["layers"]["items"]["required"], ["key"])
        self.assertEqual(sorted(schema["layers"]["items"]["properties"]), ["hidden", "key", "locked", "name"])
        self.assertIn("layer", schema["annotations"]["items"]["properties"])

    def test_the_canvas_names_the_estate_the_same(self) -> None:
        from terrane.annotations import ESTATE_LAYER
        canvas = (REPO / "80_APP" / "web" / "canvas" / "canvas.js").read_text(encoding="utf-8")
        engine = (REPO / "80_APP" / "web" / "canvas" / "engine.js").read_text(encoding="utf-8")
        self.assertIn('var ESTATE_LAYER = "%s";' % ESTATE_LAYER, canvas)
        self.assertIn('var ESTATE = "%s";' % ESTATE_LAYER, engine)


#: A diagram of two pages: its first, Payments, the file's top level, and
#: Settlement under pages.
PAGED = dict(OWN_ONLY, page="Payments", pages=[
    {"key": "page-2", "name": "Settlement",
     "annotations": [{"key": "note-1", "role": "note", "label": "Settle the batch", "at": [0, 0], "size": [184, 96]}]}])


class TestPages(unittest.TestCase):
    """V16's pages: the first the file's top level, the rest under
    `pages:`, each with the records it places and what it draws of its
    own, and each a view of its own."""

    def test_each_page_after_the_first_is_a_view_of_its_own(self) -> None:
        from terrane.query import PAGE_FIELDS
        view = parse_view(PAGED)
        self.assertEqual(view.page, "Payments")
        [settlement] = view.pages
        self.assertEqual((settlement.view_id, settlement.page, settlement.page_of),
                         ("landing-zone--page-2", "Settlement", "landing-zone"))
        self.assertEqual(settlement.title, "AWS landing zone \u00b7 Settlement")
        self.assertEqual([a["label"] for a in settlement.annotations], ["Settle the batch"])
        # Its name, look and the rest are the diagram's; what is on it its own.
        self.assertEqual((settlement.category, settlement.kind, settlement.look), (view.category, view.kind, view.look))
        self.assertEqual([a["key"] for a in view.annotations], ["org", "ou-security", "guardrails"])
        self.assertEqual(PAGE_FIELDS, ("places", "scope", "positions", "annotations", "groups", "locked"))
        self.assertEqual((parse_view(OWN_ONLY).page, parse_view(OWN_ONLY).pages), ("", ()))

    def test_refused_where_a_page_does_not_hold(self) -> None:
        page = PAGED["pages"][0]
        for pages, first, said in (
                ("Settlement", None, "pages is a list of its pages after the first"),
                ([dict(page, key="Page 2")], None, "number 1 is a key of small letters"),
                ([dict(page, title="Settlement")], None, "number 1 is a key"),
                ([page, dict(page, name="Again")], None, "page-2 is the key of two"),
                ([dict(page, annotations=[{"key": "x", "role": "blob", "at": [0, 0], "size": [1, 1]}])], None,
                 "page Settlement: view landing-zone--page-2: annotations: x has role 'blob'"),
                ([page], "x" * 61, "page is the name of its first page")):
            with self.subTest(said=said), self.assertRaises(ViewError) as caught:
                parse_view(dict(PAGED, pages=pages, **({"page": first} if first else {})))
            self.assertIn(said, str(caught.exception))

    def test_the_schema_takes_them(self) -> None:
        props = jsonschema.view_schema()["properties"]
        self.assertEqual(props["page"]["maxLength"], 60)
        page = props["pages"]["items"]
        self.assertEqual(page["required"], ["key", "name"])
        self.assertEqual(page["properties"]["annotations"], props["annotations"])
        self.assertIn("positions", page["properties"])


class TestSavedStyles(unittest.TestCase):
    """V16's Styles: a diagram's looks kept by name (`saved_styles:`),
    checked as a look is, and the canvas's own five and what it paints all
    looks the engine reads."""

    def view(self, styles):
        return parse_view(dict(OWN_ONLY, saved_styles=styles))

    def test_read_as_a_name_and_a_look(self) -> None:
        kept = self.view([{"name": " Edge ", "look": {"fill": "lavender", "line": "dashed", "bold": True}}])
        self.assertEqual(kept.saved_styles, ({"name": "Edge", "look": {"fill": "lavender", "line": "dashed", "bold": True}},))
        self.assertEqual(parse_view(OWN_ONLY).saved_styles, ())

    def test_refused_saying_what_to_fix(self) -> None:
        for styles, said in (("Edge", "is a list"),
                             ([{"name": "", "look": {}}], "a name of up to 40 characters"),
                             ([{"name": "x" * 41, "look": {}}], "a name of up to 40 characters"),
                             ([{"name": "Edge", "look": {}}, {"name": "edge", "look": {}}], "edge is the name of two"),
                             ([{"name": "Edge", "look": {"icon": "server"}}], "says what a shape is"),
                             ([{"name": "Edge", "look": {"fill": "teal"}}], "look.fill is one of")):
            with self.subTest(said=said), self.assertRaises(ViewError) as caught:
                self.view(styles)
            self.assertIn(said, str(caught.exception))

    def test_the_schema_keeps_a_name_and_a_look_with_no_icon(self) -> None:
        schema = jsonschema.view_schema()["properties"]["saved_styles"]["items"]
        self.assertEqual(schema["required"], ["name", "look"])
        self.assertNotIn("icon", schema["properties"]["look"]["properties"])

    def test_the_canvas_styles_and_paints_only_looks_the_engine_reads(self) -> None:
        canvas = (REPO / "80_APP" / "web" / "canvas" / "canvas.js").read_text(encoding="utf-8")
        block = canvas.split("var STYLES = [", 1)[1].split("];", 1)[0]
        styles = re.findall(r'\["(\w+)", (\{[^}]*\})\]', block)
        self.assertEqual([name for name, _ in styles], ["Service", "Data", "Outside", "Risk", "Quiet"])
        for name, literal in styles:
            look = eval(re.sub(r"(\w+):", r'"\1":', literal).replace("true", "True"))  # noqa: S307 -- our own file
            with self.subTest(style=name):
                check_look(look, name)
        paints = canvas.split("var PAINTS = {", 1)[1].split("};", 1)[0]
        for word in re.findall(r'"(\w+)"', paints):
            with self.subTest(paints=word):
                self.assertIn(word, LOOK_KEYS)


class TestEstateStyles(unittest.TestCase):
    """Saved styles kept for every diagram: `saved_styles` in model.yaml,
    read as a diagram's own are."""

    def test_read_as_a_name_and_a_look(self) -> None:
        from terrane.annotations import estate_styles
        self.assertEqual(estate_styles({"saved_styles": [{"name": " Hot path ", "look": {"fill": "rose"}}]}),
                         ({"name": "Hot path", "look": {"fill": "rose"}},))
        self.assertEqual(estate_styles({}), ())
        self.assertEqual(estate_styles(None), ())

    def test_refused_as_a_diagrams_are(self) -> None:
        from terrane.annotations import estate_styles
        for styles, said in (("Edge", "model.yaml: saved_styles is a list"),
                             ([{"name": "", "look": {}}], "a name of up to 40 characters"),
                             ([{"name": "Edge", "look": {}}, {"name": "EDGE", "look": {}}], "EDGE is the name of two"),
                             ([{"name": "Edge", "look": {"icon": "server"}}], "says what a shape is"),
                             ([{"name": "Edge", "look": {"fill": "teal"}}], "look.fill is one of")):
            with self.subTest(said=said), self.assertRaises(AnnotationError) as caught:
                estate_styles({"saved_styles": styles})
            self.assertIn(said, str(caught.exception))

    def test_validate_says_where_one_is_wrong(self) -> None:
        from types import SimpleNamespace
        from terrane import validate
        found = validate._check_estate_styles(SimpleNamespace(config={"saved_styles": [{"name": "X", "look": {"fill": "teal"}}]}))
        self.assertEqual([(f.code, f.where) for f in found], [("styles.estate", "10_MODEL/model.yaml")])
        self.assertEqual(validate._check_estate_styles(SimpleNamespace(config={})), [])

    def test_the_canvas_turns_a_group_as_one(self) -> None:
        engine = (REPO / "80_APP" / "web" / "canvas" / "engine.js").read_text(encoding="utf-8")
        canvas = (REPO / "80_APP" / "web" / "canvas" / "canvas.js").read_text(encoding="utf-8")
        self.assertIn("function turnTogether(keys, degrees)", engine)
        self.assertIn("picked, moved, copied and turned as one", canvas)


class TestLinePanel(unittest.TestCase):
    """V16's line picked, its first part: words at three places, Dotted,
    S, M or L, and rounded turns."""

    ITEMS = [
        {"key": "a", "role": "shape", "label": "Checkout web", "at": [0, 0], "size": [100, 50]},
        {"key": "b", "role": "shape", "label": "Card ledger", "at": [300, 200], "size": [100, 50]},
        {"key": "l", "role": "line", "from": "a", "to": "b", "route": "square", "turns": "rounded",
         "label": "reads balances", "labels": {"start": "every five minutes", "end": "read only"},
         "look": {"line": "dotted", "weight": "l"}},
    ]

    def test_read_and_refused(self) -> None:
        line = read(self.ITEMS, "here")[2]
        self.assertEqual((line["turns"], line["labels"]["end"], line["look"]["weight"]), ("rounded", "read only", "l"))
        base = self.ITEMS[2]
        for item, said in ((dict(base, turns="soft"), "turns is sharp or rounded"),
                           (dict(base, labels={"middle": "x"}), "labels is its words at its start and its end"),
                           (dict(base, labels={"start": ""}), "labels is its words"),
                           (dict(base, labels={}), "labels is its words"),
                           (dict(base, look={"weight": "xl"}), "one of s, m, l"),
                           (dict(base, look={"corners": 4}), "which a line does not have")):
            with self.subTest(said=said), self.assertRaises(AnnotationError) as caught:
                read(self.ITEMS[:2] + [item], "here")
            self.assertIn(said, str(caught.exception))

    def test_the_picture_draws_it_dotted_heavy_rounded_with_its_words(self) -> None:
        svg, _ = drawn.paint(self.ITEMS, (0.0, 0.0), {}, drawn_metrics(), "over")
        path = [line for line in svg.splitlines() if 'fill="none"' in line and "<path" in line][0]
        self.assertIn('stroke-width="2.5" stroke-dasharray="2 3"', path)
        self.assertIn("L190 25 Q200 25 200 35", path)
        for words in ("every five minutes", "reads balances", "read only"):
            self.assertIn(">%s</text>" % words, svg)
        # The start's words a share of the way in from the start.
        self.assertIn('<text x="160" y="28.91"', svg)

    def test_the_slide_and_the_page_draw_the_same(self) -> None:
        from terrane.draw.dml import slide_shapes
        from terrane.draw.svg import Scene
        from terrane.render_drawio import diagram_xml
        own = tuple(drawn.scene(self.ITEMS, (0.0, 0.0), {}))
        line = [o for o in own if o.role == "line"][0]
        self.assertEqual((line.weight, line.dotted, line.turns, dict(line.labels)),
                         (2.5, True, "rounded", {"start": "every five minutes", "end": "read only"}))
        scene = Scene((0.0, 0.0, 400.0, 250.0), [], [], [], True, "own", own)
        shapes = "".join(slide_shapes(scene, (0.5, 1.0, 12.8, 7.0), 2))
        self.assertIn('<a:prstDash val="sysDot"/>', shapes)
        self.assertIn("<a:quadBezTo>", shapes)
        self.assertIn(">every five minutes<", shapes)
        page = diagram_xml(scene)
        self.assertIn("rounded=1;", page)
        self.assertIn("strokeWidth=2.5;", page)
        self.assertIn("dashPattern=2 3;", page)
        self.assertIn('value="read only"', page)
        self.assertIn('<mxGeometry x="0.7" relative="1" as="geometry">', page)

    def test_the_canvas_draws_from_the_same_numbers(self) -> None:
        from terrane.annotations import LINE_WEIGHTS
        engine = ENGINE.read_text(encoding="utf-8")
        self.assertIn("var LINE_WEIGHTS = { s: %g, m: %g, l: %g }" % (LINE_WEIGHTS["s"], LINE_WEIGHTS["m"], LINE_WEIGHTS["l"]),
                      engine)
        self.assertIn('DASHES = { dashed: "%s", dotted: "%s" }' % (drawn.DASHES["dashed"], drawn.DASHES["dotted"]), engine)
        self.assertIn("END_LABEL_AT = %g;" % (1 - 2 * drawn.END_LABELS_AT), engine)


class TestHeads(unittest.TestCase):
    """V16's line picked, its ends: a head at each from four notations,
    read, drawn by the picture from its glyph, by the slide and the draw.io
    page, and by the canvas from the same table."""

    ITEMS = [
        {"key": "a", "role": "shape", "label": "Customer", "at": [0, 0], "size": [100, 50]},
        {"key": "b", "role": "shape", "label": "Order", "at": [300, 0], "size": [100, 50]},
        {"key": "l", "role": "line", "from": "a", "to": "b", "heads": {"start": "none-or-one", "end": "many"}},
    ]

    def test_read_and_refused(self) -> None:
        from terrane.annotations import heads_of
        line = read(self.ITEMS, "here")[2]
        self.assertEqual(heads_of(line), ("none-or-one", "many"))
        self.assertEqual(heads_of({"heads": {"end": "flow"}}), ("none", "flow"))
        self.assertEqual([heads_of({"ends": e}) for e in ("end", "both", "none")],
                         [("none", "arrow"), ("arrow", "arrow"), ("none", "none")])
        self.assertEqual(heads_of({}), ("none", "arrow"))
        base = self.ITEMS[2]
        for item, said in ((dict(base, heads={"middle": "dot"}), "heads is the head at its start and at its end"),
                           (dict(base, heads={"end": "crow"}), "each one of none, arrow"),
                           (dict(base, heads={}), "heads is the head"),
                           (dict(base, heads="many"), "heads is the head"),
                           (dict(base, ends="both"), "by heads or by ends, not both")):
            with self.subTest(said=said), self.assertRaises(AnnotationError) as caught:
                read(self.ITEMS[:2] + [item], "here")
            self.assertIn(said, str(caught.exception))

    def test_the_picture_draws_each_head_from_its_glyph(self) -> None:
        svg, _ = drawn.paint(self.ITEMS, (0.0, 0.0), {}, drawn_metrics(), "over")
        # None or one at its start: the line stops past its ring, which a
        # stroke runs on from to the box, a bar across it.
        self.assertIn('<path d="M115 25 L300 25" fill="none"', svg)
        self.assertIn('<circle cx="112.5" cy="25" r="2.5" fill="none" stroke=', svg)
        self.assertIn('<path d="M110 25 L100 25" fill="none"', svg)
        self.assertIn('<path d="M105 29.5 L105 20.5" fill="none"', svg)
        # Many at its end: the crow's foot, its toes on the box.
        self.assertIn('<path d="M300 20.5 L292 25 L300 29.5" fill="none"', svg)
        # A hollow head: the line stops at its base, drawn round, not filled.
        has = dict(self.ITEMS[2], heads={"end": "has"})
        svg, _ = drawn.paint(self.ITEMS[:2] + [has], (0.0, 0.0), {}, drawn_metrics(), "over")
        self.assertIn('<path d="M100 25 L288 25" fill="none"', svg)
        self.assertIn('<path d="M300 25 L294 21.5 L288 25 L294 28.5 Z" fill="none" stroke=', svg)
        # The plain arrow as it always was.
        plain = {k: v for k, v in self.ITEMS[2].items() if k != "heads"}
        svg, _ = drawn.paint(self.ITEMS[:2] + [plain], (0.0, 0.0), {}, drawn_metrics(), "over")
        self.assertIn('<path d="M300 25 L293 21.5 L293 28.5 Z" fill=', svg)
        self.assertIn('<path d="M100 25 L293 25" fill="none"', svg)

    def test_the_slide_and_the_page_draw_the_same(self) -> None:
        from terrane.draw.dml import slide_shapes
        from terrane.draw.svg import Scene
        from terrane.render_drawio import diagram_xml
        own = tuple(drawn.scene(self.ITEMS, (0.0, 0.0), {}))
        line = [o for o in own if o.role == "line"][0]
        self.assertEqual(line.heads, ("none-or-one", "many"))
        scene = Scene((0.0, 0.0, 400.0, 50.0), [], [], [], True, "own", own)
        shapes = "".join(slide_shapes(scene, (0.5, 1.0, 12.8, 7.0), 2))
        # Crow's foot has no line end in DrawingML: each head a shape.
        self.assertEqual(shapes.count('name="Head l"'), 2)
        self.assertNotIn("<a:tailEnd", shapes)
        page = diagram_xml(scene)
        self.assertIn("startArrow=ERzeroToOne;startFill=0;", page)
        self.assertIn("endArrow=ERmany;endFill=0;", page)
        # Those it has, PowerPoint draws itself.
        for head, end in (("arrow", "triangle"), ("dot", "oval"), ("made-of", "diamond"), ("serving", "arrow")):
            item = dict(self.ITEMS[2], heads={"end": head})
            scene = Scene((0.0, 0.0, 400.0, 50.0), [], [], [], True, "own",
                          tuple(drawn.scene(self.ITEMS[:2] + [item], (0.0, 0.0), {})))
            shapes = "".join(slide_shapes(scene, (0.5, 1.0, 12.8, 7.0), 2))
            with self.subTest(head=head):
                self.assertIn('<a:tailEnd type="%s" w="sm" len="sm"/>' % end, shapes)
                self.assertNotIn('name="Head l"', shapes)

    def test_the_canvas_draws_from_the_same_glyphs(self) -> None:
        from terrane.annotations import HEADS
        engine = ENGINE.read_text(encoding="utf-8")
        table = engine.split("var HEAD_GLYPHS = ", 1)[1].split(";\n", 1)[0]
        self.assertEqual(json.loads(table), drawn.HEAD_GLYPHS)
        self.assertEqual(tuple(drawn.HEAD_GLYPHS), HEADS)
        panel = (ENGINE.parent / "canvas.js").read_text(encoding="utf-8")
        groups = panel.split("var HEAD_GROUPS = [", 1)[1].split("\n  ];", 1)[0]
        self.assertEqual(tuple(re.findall(r'\["([a-z-]+)", "', groups)), HEADS)


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

    def test_a_diagrams_saved_styles_are_saved_after_its_look_and_read_back(self) -> None:
        styles = [{"name": "Edge", "look": {"fill": "lavender", "line": "dashed"}}]
        data = dict(OWN_ONLY, look="tiles", saved_styles=styles)
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertEqual(saved["errors"], [])
        text = (self.root / saved["path"]).read_text(encoding="utf-8")
        self.assertLess(text.index("\nlook: tiles\n"), text.index("\nsaved_styles:\n"))
        self.assertEqual(self.server.api_view({"id": [saved["id"]]}, {})["data"]["saved_styles"], styles)

    def test_a_diagrams_groups_are_saved_after_its_styles_and_read_back(self) -> None:
        styles = [{"name": "Edge", "look": {"fill": "lavender"}}]
        groups = [{"key": "group-1", "name": "Security"}]
        items = [dict(item) for item in LANDING[:3]]
        items[1]["group"] = items[2]["group"] = "group-1"
        data = dict(OWN_ONLY, saved_styles=styles, groups=groups, annotations=items)
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertEqual(saved["errors"], [])
        text = (self.root / saved["path"]).read_text(encoding="utf-8")
        self.assertLess(text.index("\nsaved_styles:\n"), text.index("\ngroups:\n"))
        self.assertLess(text.index("\ngroups:\n"), text.index("\nannotations:\n"))
        back = self.server.api_view({"id": [saved["id"]]}, {})["data"]
        self.assertEqual(back["groups"], groups)
        self.assertEqual([a.get("group") for a in back["annotations"]], [None, "group-1", "group-1"])
        refused = dict(data, groups=[])
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_canvas_save({}, {"id": None, "data": refused})
        self.assertIn("which the diagram's groups do not name", str(caught.exception))

    def test_a_swimlane_is_saved_and_read_back(self) -> None:
        data = dict(OWN_ONLY, annotations=SWIMLANE)
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertEqual(saved["errors"], [])
        back = self.server.api_view({"id": [saved["id"]]}, {})["data"]["annotations"]
        self.assertEqual(back, SWIMLANE)
        self.assertIn('data-role="lane"', self.server.api_svg({"view": [saved["id"]]}))

    def test_drawing_layers_are_saved_before_groups_and_drawn_as_they_say(self) -> None:
        data = dict(OWN_ONLY, layers=LAYERS, annotations=TestLayers.ITEMS,
                    groups=[{"key": "group-1", "name": "Pair"}])
        data["annotations"] = [dict(i, group="group-1") if i["key"] in ("a", "b") else i for i in TestLayers.ITEMS]
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertEqual(saved["errors"], [])
        text = (self.root / saved["path"]).read_text(encoding="utf-8")
        self.assertLess(text.index("\nlayers:\n"), text.index("\ngroups:\n"))
        self.assertEqual(self.server.api_view({"id": [saved["id"]]}, {})["data"]["layers"], LAYERS)
        graph = self.server.api_graph({"view": [saved["id"]]}, None)
        self.assertEqual([a["key"] for a in graph["annotations"]], ["f", "in-f", "b", "a"])
        svg = self.server.api_svg({"view": [saved["id"]]})
        self.assertIn("Gateway", svg)
        self.assertNotIn("Who signs off?", svg)

    def test_a_diagrams_pages_are_saved_last_drawn_alone_and_listed_once(self) -> None:
        data = dict(PAGED)
        del data["view_id"]
        saved = self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertEqual(saved["errors"], [])
        text = (self.root / saved["path"]).read_text(encoding="utf-8")
        self.assertLess(text.index("\ntitle: "), text.index("\npage: Payments\n"))
        self.assertLess(text.index("\nannotations:\n"), text.index("\npages:\n"))
        back = self.server.api_view({"id": [saved["id"]]}, {})["data"]
        self.assertEqual(back["pages"], PAGED["pages"])
        svg = self.server.api_svg({"view": [saved["id"] + "--page-2"]})
        self.assertIn("Settle the batch", svg)
        self.assertNotIn("Guardrails", svg)
        listed = [v["viewId"] for v in self.server.api_overview({}, None)["views"] if v["viewId"].startswith(saved["id"])]
        self.assertEqual(listed, [saved["id"]])

    def test_the_estates_styles_are_kept_in_model_yaml_and_offered(self) -> None:
        path = self.root / "10_MODEL" / "model.yaml"
        was = path.read_text(encoding="utf-8")
        try:
            kept = self.server.api_canvas_styles({}, {"styles": [{"name": "Hot path", "look": {"fill": "rose"}}]})
            self.assertEqual(kept["styles"], [{"name": "Hot path", "look": {"fill": "rose"}}])
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(was), "the rest of model.yaml is left as it was")
            self.assertIn("saved_styles:\n  - name: Hot path\n", text)
            self.assertEqual(self.server.api_canvas_parts({}, None)["styles"], kept["styles"])
            again = self.server.api_canvas_styles({}, {"styles": [{"name": "Quiet", "look": {"line": "none"}}]})
            self.assertEqual(path.read_text(encoding="utf-8").count("saved_styles:"), 1)
            self.assertEqual(again["styles"][0]["name"], "Quiet")
            with self.assertRaises(self.server.ApiError):
                self.server.api_canvas_styles({}, {"styles": [{"name": "Bad", "look": {"fill": "teal"}}]})
            self.server.api_canvas_styles({}, {"styles": []})
            self.assertEqual(path.read_text(encoding="utf-8"), was)
        finally:
            path.write_text(was, encoding="utf-8", newline="")

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
