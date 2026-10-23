"""Pinning a thing to one drawing, and hiding one from it.

A view is a query, and still is. `scope.pin` and `scope.hide` are the two
decisions a person may add about one drawing, by id; the app writes them with
the smallest change that does what was asked, keeps every other line of the
file, and lists them on the drawing. These hold the engine's reading of them,
the endpoint's arithmetic, and the rewrite that must not reflow a hand-written
view.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import records, validate  # noqa: E402
from terrane.loader import parse_data_text, read_data_file  # noqa: E402
from terrane.query import load_views, parse_view, resolve  # noqa: E402

from _fixture import REPO, Sandbox, seeded_model, setup_shared, teardown_shared  # noqa: E402


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _view(scope: dict, **extra) -> object:
    data = {"view_id": "probe", "kind": "diagram", "scope": scope,
            "edges": [{"via": "interfaces"}]}
    data.update(extra)
    return parse_view(data)


def _ids(model, view) -> set:
    return {n.key for n in resolve(model, view).nodes}


class TestTheEngineReadsThem(unittest.TestCase):
    def setUp(self) -> None:
        self.model = seeded_model()
        systems = sorted(r["system_id"] for r in self.model.all_of("systems"))
        self.a, self.b, self.c = systems[0], systems[1], systems[2]

    def test_a_pin_adds_one_thing(self) -> None:
        view = _view({"include": [{"type": "systems", "where": {"id_in": [self.a]}}], "pin": [self.b]})
        self.assertEqual(_ids(self.model, view), {self.a, self.b})

    def test_a_pin_is_not_a_seed(self) -> None:
        """Pinned on a context drawing, the SIEM should not bring every
        system that sends it logs."""
        view = _view({
            "include": [{"type": "systems", "where": {"id_in": [self.a]}}],
            "expand": [{"relation": "interfaces", "depth": 1}],
            "pin": [self.b],
        })
        alone = _view({
            "include": [{"type": "systems", "where": {"id_in": [self.a]}}],
            "expand": [{"relation": "interfaces", "depth": 1}],
        })
        self.assertEqual(_ids(self.model, view), _ids(self.model, alone) | {self.b})

    def test_a_view_may_be_pins_alone(self) -> None:
        self.assertEqual(_ids(self.model, _view({"pin": [self.a, self.b]})), {self.a, self.b})

    def test_a_pin_survives_the_cut(self) -> None:
        view = _view({"include": [{"type": "systems"}], "pin": [self.c]}, limits={"max_nodes": 1})
        self.assertIn(self.c, _ids(self.model, view))

    def test_hide_removes_and_beats_a_pin(self) -> None:
        view = _view({"include": [{"type": "systems", "where": {"id_in": [self.a, self.b]}}],
                      "pin": [self.c], "hide": [self.b, self.c]})
        self.assertEqual(_ids(self.model, view), {self.a})

    def test_a_pin_on_something_gone_draws_and_is_reported(self) -> None:
        view = _view({"include": [{"type": "systems", "where": {"id_in": [self.a]}}],
                      "pin": ["SYS-NOT-THERE"]})
        self.assertEqual(_ids(self.model, view), {self.a})
        findings = validate.run(self.model, [view])
        self.assertIn("view.stale_pin", [f.code for f in findings.warnings])


class TestTheRewriteKeepsTheFile(unittest.TestCase):
    def test_every_committed_view_survives_a_rewrite_unchanged(self) -> None:
        for path in sorted((REPO / "30_VIEWS").glob("*.view.yaml")):
            with self.subTest(view=path.name):
                text = path.read_text(encoding="utf-8-sig")
                self.assertEqual(records.rewrite(text, parse_data_text(text)), text)

    def test_a_pin_is_two_added_lines_and_nothing_else(self) -> None:
        for path in sorted((REPO / "30_VIEWS").glob("*.view.yaml")):
            with self.subTest(view=path.name):
                text = path.read_text(encoding="utf-8-sig")
                data = parse_data_text(text)
                data["scope"] = dict(data.get("scope") or {}, pin=["SYS-X"], hide=["SYS-Y"])
                after = records.rewrite(text, data)
                self.assertEqual(parse_data_text(after), data)
                before_lines, after_lines = text.splitlines(), after.splitlines()
                self.assertEqual(len(after_lines), len(before_lines) + 2)
                self.assertEqual([l for l in after_lines if l not in before_lines],
                                 ["  pin: [SYS-X]", "  hide: [SYS-Y]"])


def _server_for(root: Path):
    sys.path.insert(0, str(root / "50_ENGINE"))
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestTheEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        box = Sandbox(seed=True)
        self.root = box.__enter__()
        self.addCleanup(box.__exit__, None, None, None)
        self.server = _server_for(self.root)
        self.path = self.root / "30_VIEWS" / "probe.view.yaml"
        model = self.server._load_all()[0]
        systems = sorted(r["system_id"] for r in model.all_of("systems"))
        self.a, self.b, self.c = systems[0], systems[1], systems[2]
        self.text = (
            "# A probe view, written by hand.\n"
            "view_id: probe\n"
            "title: Probe\n"
            "kind: diagram\n"
            "description: >\n"
            "  Two systems, described over\n"
            "  two lines on purpose.\n"
            "scope:\n"
            "  include:\n"
            "    # The pair this view is about.\n"
            "    - type: systems\n"
            "      where:\n"
            "        id_in: [%s, %s]\n"
            "edges:\n"
            "  - via: interfaces\n" % (self.a, self.b)
        )
        self.path.write_text(self.text, encoding="utf-8")

    def change(self, **body):
        return self.server.api_view_membership(None, dict(body, view="probe"))

    def scope(self) -> dict:
        return read_data_file(self.path)["scope"]

    def test_showing_what_the_query_does_not_bring_pins_it(self) -> None:
        res = self.change(show=[self.c])
        self.assertEqual([c["what"] for c in res["changes"]], ["pinned"])
        self.assertEqual(self.scope()["pin"], [self.c])
        self.assertIn("# The pair this view is about.", self.path.read_text(encoding="utf-8"))
        self.assertIn("  Two systems, described over\n  two lines on purpose.", self.path.read_text(encoding="utf-8"))

    def test_showing_what_is_already_drawn_changes_nothing(self) -> None:
        res = self.change(show=[self.a])
        self.assertEqual(res["changes"], [])
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.text)

    def test_hiding_a_pinned_thing_only_unpins_it(self) -> None:
        self.change(show=[self.c])
        res = self.change(hide=[self.c])
        self.assertEqual([c["what"] for c in res["changes"]], ["unpinned"])
        self.assertNotIn("pin", self.scope())
        self.assertNotIn("hide", self.scope())
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.text)

    def test_hiding_and_showing_again_leaves_the_file_as_it_was(self) -> None:
        self.change(hide=[self.a])
        self.assertEqual(self.scope()["hide"], [self.a])
        res = self.change(show=[self.a])
        self.assertEqual([c["what"] for c in res["changes"]], ["shown"])
        self.assertEqual(self.path.read_bytes(), self.text.encode("utf-8"),
                         "byte for byte, line endings included")

    def test_a_hide_that_empties_the_view_says_so(self) -> None:
        res = self.change(hide=[self.a, self.b])
        self.assertTrue(res["problem"])

    def test_the_drawing_lists_its_pins_by_name(self) -> None:
        self.change(show=[self.c], hide=[self.a])
        payload = self.server.api_graph({"view": ["probe"]}, None)
        membership = payload["membership"]
        self.assertTrue(membership["editable"])
        self.assertEqual([p["id"] for p in membership["pinned"]], [self.c])
        self.assertEqual([p["id"] for p in membership["hidden"]], [self.a])
        self.assertTrue(membership["pinned"][0]["name"])

    def test_refusals(self) -> None:
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_view_membership(None, {"view": "no-such-view", "show": [self.a]})
        self.assertEqual(caught.exception.status, 404)
        with self.assertRaises(self.server.ApiError) as caught:
            self.change(show=["SYS-NOT-THERE"])
        self.assertEqual(caught.exception.status, 404)
        with self.assertRaises(self.server.ApiError):
            self.change()

    def test_the_views_load_with_the_change(self) -> None:
        self.change(show=[self.c], hide=[self.a])
        views = {v.view_id: v for v in load_views(self.root / "30_VIEWS")}
        self.assertEqual(views["probe"].scope["pin"], [self.c])


if __name__ == "__main__":
    unittest.main()
