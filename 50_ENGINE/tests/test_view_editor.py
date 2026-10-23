"""Tests for the view editor and the diagram source endpoints.

Everything in this repository is a query, so the thing worth letting someone
edit is the query. That makes the editor a write path into `30_VIEWS/`, and
every write path here gets a guard and a test for it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import importer, model as model_module  # noqa: E402
from terrane.loader import ModelFileError, parse_data_text  # noqa: E402
from terrane.query import load_views  # noqa: E402

from _fixture import (  # noqa: E402
    EXAMPLE_CSV,
    REPO,
    Sandbox as _Sandbox,
    seeded_root,
    setup_shared,
    teardown_shared,
)


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _server(root: Path):
    sys.path.insert(0, str(root / "50_ENGINE"))
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


def _seeded(root: Path):
    importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
    return _server(root)


class TestParseDataText(unittest.TestCase):
    """The editor must go through the same reader as the files on disk."""

    def test_it_reads_what_the_loader_reads(self) -> None:
        self.assertEqual(parse_data_text("a: 1\nb: [x, y]"), {"a": 1, "b": ["x", "y"]})

    def test_a_syntax_error_is_raised_not_swallowed(self) -> None:
        with self.assertRaises(ModelFileError):
            parse_data_text("a: [1,\n")

    def test_every_committed_view_round_trips_through_it(self) -> None:
        """If the in-memory reader disagreed with the file reader, the editor
        would refuse to open views that load perfectly well."""
        from terrane.loader import read_data_file

        for path in sorted((REPO / "30_VIEWS").glob("*.view.yaml")):
            with self.subTest(view=path.name):
                self.assertEqual(
                    parse_data_text(path.read_text(encoding="utf-8-sig"), path.name),
                    read_data_file(path),
                )


class TestYamlComplaint(unittest.TestCase):
    """What the editor shows when the text does not parse."""

    server = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _server(seeded_root())

    def _complain(self, text: str) -> str:
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_view_preview(None, {"text": text})
        return str(caught.exception)

    def test_the_source_name_and_caret_are_stripped(self) -> None:
        message = self._complain("view_id: x\n  : bad")
        self.assertNotIn("<unicode string>", message)
        self.assertNotIn("^", message)

    def test_the_position_survives(self) -> None:
        """The line number is the only part of the complaint that locates it."""
        self.assertIn("line 2", self._complain("view_id: x\n  : bad"))

    def test_an_unparseable_text_still_says_something(self) -> None:
        self.assertTrue(self._complain("view_id: [x").strip())


class TestViewEditor(unittest.TestCase):
    def _starter(self, server, view_id: str) -> str:
        return (
            server.api_view({}, None)["text"]
            .replace("my-view", view_id)
            .replace("My View", view_id.title())
        )

    def test_reading_a_view_returns_its_file_verbatim(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            payload = server.api_view({"id": ["application-landscape"]}, None)
            path = root / payload["path"]
            self.assertEqual(payload["text"], path.read_text(encoding="utf-8-sig"))
            self.assertFalse(payload["isNew"])

    def test_the_starter_draws_something_on_the_first_preview(self) -> None:
        """An empty box is a worse place to start than a working example."""
        with _Sandbox() as root:
            server = _seeded(root)
            payload = server.api_view({}, None)
            self.assertTrue(payload["isNew"])
            preview = server.api_view_preview(None, {"text": payload["text"]})
            self.assertGreater(preview["counts"]["nodes"], 0)
            self.assertTrue(preview["preview"])

    def test_the_help_is_taken_from_the_model_not_written_by_hand(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            help_ = server.api_view({}, None)["help"]
            from terrane.schema import ENTITY_TYPES, RELATION_TYPES

            self.assertEqual(help_["types"], sorted(ENTITY_TYPES))
            self.assertTrue(set(RELATION_TYPES) <= set(help_["edgeVia"]))
            self.assertIn("company_domain", help_["groupFields"])
            # Reference fields are ids, and grouping a diagram by an id gives
            # one boundary per node, which is not a boundary.
            self.assertNotIn("owner_org_id", help_["groupFields"])

    def test_an_unknown_view_is_a_404(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_view({"id": ["no-such-view"]}, None)
            self.assertEqual(caught.exception.status, 404)

    def test_preview_writes_nothing(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            before = sorted(p.name for p in (root / "30_VIEWS").iterdir())
            server.api_view_preview(None, {"text": self._starter(server, "ghost")})
            self.assertEqual(sorted(p.name for p in (root / "30_VIEWS").iterdir()), before)

    def test_save_creates_a_file_the_engine_then_loads(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            text = self._starter(server, "probe")
            result = server.api_view_save(None, {"text": text})

            self.assertTrue(result["created"])
            self.assertEqual(result["path"], str(Path("30_VIEWS") / "probe.view.yaml"))
            self.assertIsNone(result["problem"])
            self.assertGreater(result["counts"]["nodes"], 0)
            # Written verbatim: the app is not a formatter.
            self.assertEqual((root / result["path"]).read_text(encoding="utf-8"), text)
            self.assertIn(
                "probe", [v.view_id for v in load_views(root / "30_VIEWS")]
            )

    def test_saving_an_edit_updates_in_place(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            server.api_view_save(None, {"text": self._starter(server, "probe")})
            before = len(list((root / "30_VIEWS").iterdir()))

            edited = self._starter(server, "probe").replace("max_nodes: 60", "max_nodes: 3")
            result = server.api_view_save(None, {"id": "probe", "text": edited})

            self.assertFalse(result["created"])
            self.assertEqual(result["counts"]["nodes"], 3)
            self.assertEqual(len(list((root / "30_VIEWS").iterdir())), before)

    def test_a_duplicate_id_is_refused(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_view_save(
                    None, {"text": self._starter(server, "application-landscape")}
                )
            self.assertEqual(caught.exception.status, 409)

    def test_renaming_in_place_is_refused(self) -> None:
        """Otherwise one file would claim an id and another would too."""
        with _Sandbox() as root:
            server = _seeded(root)
            server.api_view_save(None, {"text": self._starter(server, "probe")})
            with self.assertRaises(server.ApiError) as caught:
                server.api_view_save(
                    None,
                    {"id": "probe", "text": self._starter(server, "probe").replace(
                        "view_id: probe", "view_id: probe-two")},
                )
            self.assertEqual(caught.exception.status, 409)
            self.assertFalse((root / "30_VIEWS" / "probe-two.view.yaml").exists())

    def test_editing_a_view_that_does_not_exist_is_a_404(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_view_save(None, {"id": "nope", "text": self._starter(server, "nope")})
            self.assertEqual(caught.exception.status, 404)

    def test_an_id_that_is_not_an_identifier_is_refused(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            for bad in ("../escape", "has space", "", "/absolute"):
                with self.subTest(id=bad):
                    text = self._starter(server, "probe").replace(
                        "view_id: probe", "view_id: %r" % bad
                    )
                    with self.assertRaises(server.ApiError):
                        server.api_view_save(None, {"text": text})

    def test_a_view_that_draws_nothing_is_saved_and_reported(self) -> None:
        """Losing half-finished work is worse than saving something empty."""
        with _Sandbox() as root:
            server = _seeded(root)
            text = self._starter(server, "empty").replace("type: systems", "type: unicorns")
            result = server.api_view_save(None, {"text": text})
            self.assertTrue((root / result["path"]).exists())
            self.assertIn("unicorns", result["problem"])
            self.assertEqual(result["counts"], {"nodes": 0, "edges": 0})

    def test_malformed_text_never_reaches_the_disk(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            before = sorted(p.name for p in (root / "30_VIEWS").iterdir())
            for bad in ("::: not yaml", "- a list", "title: no id here"):
                with self.subTest(text=bad):
                    with self.assertRaises(server.ApiError) as caught:
                        server.api_view_save(None, {"text": bad})
                    self.assertEqual(caught.exception.status, 422)
            self.assertEqual(sorted(p.name for p in (root / "30_VIEWS").iterdir()), before)

    def test_an_edit_that_would_break_the_load_is_rolled_back(self) -> None:
        """A file that only parses in memory is not saved; it is a landmine."""
        with _Sandbox() as root:
            server = _seeded(root)
            original = server.api_view({"id": ["application-landscape"]}, None)
            duplicate = (root / "30_VIEWS" / "clash.view.yaml")
            duplicate.write_text(original["text"], encoding="utf-8")
            try:
                with self.assertRaises(server.ApiError) as caught:
                    server.api_view_save(
                        None, {"id": "application-landscape", "text": original["text"]}
                    )
                self.assertEqual(caught.exception.status, 409)
                self.assertEqual(
                    (root / original["path"]).read_text(encoding="utf-8-sig"),
                    original["text"],
                )
            finally:
                duplicate.unlink()

    def test_delete_removes_the_file_and_only_that_view(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            server.api_view_save(None, {"text": self._starter(server, "probe")})
            before = len(load_views(root / "30_VIEWS"))
            server.api_view_delete(None, {"id": "probe"})
            self.assertFalse((root / "30_VIEWS" / "probe.view.yaml").exists())
            self.assertEqual(len(load_views(root / "30_VIEWS")), before - 1)

    def test_deleting_an_unknown_view_is_a_404(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_view_delete(None, {"id": "no-such-view"})
            self.assertEqual(caught.exception.status, 404)


class TestDiagramSource(unittest.TestCase):
    """The source behind whatever is on screen."""

    server = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _server(seeded_root())

    def test_every_view_offers_both_formats(self) -> None:
        for view in load_views(seeded_root() / "30_VIEWS"):
            with self.subTest(view=view.view_id):
                try:
                    payload = self.server.api_source({"view": [view.view_id]}, None)
                except self.server.ApiError as exc:
                    # A subject view with nothing to draw in the seed offers
                    # nothing, and says so. Anything else is still a failure.
                    self.assertEqual(exc.status, 404)
                    self.assertIn("nothing qualifies yet", str(exc))
                    continue
                ids = [f["id"] for f in payload["formats"]]
                self.assertEqual(ids, ["mermaid", "structurizr"])
                for form in payload["formats"]:
                    self.assertTrue(form["text"].strip(), form["id"])

    def test_a_subject_view_with_nothing_to_draw_says_so(self) -> None:
        """The seed's products carry no `archetype`, so the onboarding view
        selects nothing here. The answer is that nothing qualifies, not that
        a value is missing for a parameter no candidate exists for."""
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_source({"view": ["onboarding"]}, None)
        self.assertEqual(caught.exception.status, 404)
        self.assertIn("nothing qualifies yet", str(caught.exception))

    def test_the_mermaid_matches_the_committed_artifact(self) -> None:
        """The app and `terrane render` must not be two different renderers."""
        server = _server(REPO)
        for path in sorted((REPO / "70_ARTIFACTS" / "mermaid").glob("*.mmd")):
            view_id = path.stem
            with self.subTest(view=view_id):
                payload = server.api_source({"view": [view_id]}, None)
                mermaid = next(f for f in payload["formats"] if f["id"] == "mermaid")
                self.assertEqual(mermaid["text"], path.read_text(encoding="utf-8"))

    def test_a_focus_view_has_a_source_too(self) -> None:
        """It has no artifact on disk, so this is the only way to get one out."""
        payload = self.server.api_source({"focus": ["SYS-AUTH-SWITCH"], "depth": ["1"]}, None)
        self.assertEqual(payload["viewId"], "focus")
        self.assertIn("flowchart", payload["formats"][0]["text"])

    def test_an_unknown_view_is_a_404(self) -> None:
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_source({"view": ["no-such-view"]}, None)
        self.assertEqual(caught.exception.status, 404)


if __name__ == "__main__":
    unittest.main()
