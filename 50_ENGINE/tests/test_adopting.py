"""An organization starting its own model from this repository.

Measured once by doing it: on the shipped repository, an empty model failed
the gate with twenty-five errors, and three imported systems made it sixty --
every product shape wanting a landing zone nobody had recorded yet, and every
view of a layer nobody had brought in yet. These hold the first day to what
AAC-15 says it is: `terrane clear`, a gate that passes on an empty model, views
that wait for their kind of thing rather than fail, and a test seed that stays
the sample's.
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli, importer, model as model_module, validate  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402
from terrane.query import load_views  # noqa: E402

from _fixture import REPO, Sandbox  # noqa: E402


def _run(*args) -> str:
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(list(args))
    assert code == 0, out.getvalue()
    return out.getvalue()


def _report(root: Path):
    return validate.run(model_module.load(root), load_views(root / "30_VIEWS"))


class TestClear(unittest.TestCase):
    def setUp(self) -> None:
        box = Sandbox(seed=True)
        self.root = box.__enter__()
        self.addCleanup(box.__exit__, None, None, None)

    def test_the_shipped_model_says_it_is_the_sample(self) -> None:
        self.assertTrue(cli.is_sample_estate(REPO))
        self.assertTrue(cli.is_sample_estate(self.root))

    def test_without_yes_nothing_is_removed(self) -> None:
        before = sorted(p for p in (self.root / "10_MODEL").rglob("*") if p.is_file())
        said = _run("--root", str(self.root), "clear")
        self.assertIn("Nothing has been changed", said)
        self.assertEqual(sorted(p for p in (self.root / "10_MODEL").rglob("*") if p.is_file()), before)

    def test_clear_leaves_settings_library_and_views(self) -> None:
        views = sorted(p.name for p in (self.root / "30_VIEWS").iterdir())
        _run("--root", str(self.root), "clear", "--yes", "--keep", "org_units")
        model = model_module.load(self.root)
        self.assertEqual(model.all_of("systems"), [])
        self.assertTrue(model.all_of("org_units"), "kept as asked")
        self.assertEqual(sorted(p.name for p in (self.root / "30_VIEWS").iterdir()), views)
        self.assertTrue((self.root / "10_MODEL" / "model.yaml").exists())
        self.assertFalse(cli.is_sample_estate(self.root))
        self.assertEqual(read_data_file(self.root / "10_MODEL" / "model.yaml").get("name"), "Architecture Model")

    def test_the_estates_answers_go_with_its_records(self) -> None:
        """`answers` and `patterns` in model.yaml name the sample's org units,
        systems and controls; left behind, the next estate's first vendor
        product would give its private egress to an org unit not there. The
        library hint above them stays, as every other comment does."""
        said = _run("--root", str(self.root), "clear")
        self.assertIn("would drop `answers` and `patterns`", said)
        _run("--root", str(self.root), "clear", "--yes")
        config_file = self.root / "10_MODEL" / "model.yaml"
        config = read_data_file(config_file)
        self.assertNotIn("answers", config)
        self.assertNotIn("patterns", config)
        text = config_file.read_text(encoding="utf-8")
        self.assertIn("# library_paths: [our-library]", text)
        self.assertNotIn("ORG-TECH", text)

    def test_an_unknown_kind_to_keep_is_refused(self) -> None:
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--root", str(self.root), "clear", "--yes", "--keep", "gadgets"]), 2)


class TestTheFirstDay(unittest.TestCase):
    """The insurer of AAC-15, three systems and an org unit."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox()
        cls.root = cls.box.__enter__()
        cls.empty = _report(cls.root)
        inventory = cls.root / "insurer"
        inventory.mkdir()
        (inventory / "org_units.csv").write_text(
            "org_unit_id,name,status\nORG-IT,Information Technology,Active\n", encoding="utf-8")
        (inventory / "systems.csv").write_text(
            "system_id,name,status,owner_org_id,criticality,company_domain,app_code\n"
            "SYS-POLICY-ADMIN,Policy Administration,Active,ORG-IT,High,Underwriting,APP001\n"
            "SYS-CLAIMS,Claims Workbench,Active,ORG-IT,High,Claims,APP002\n"
            "SYS-PORTAL,Agent Portal,Planned,ORG-IT,Medium,Distribution,APP003\n", encoding="utf-8")
        cls.outcome = importer.import_csv(cls.root, inventory, model_module.load(cls.root))
        cls.imported = _report(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def test_an_empty_model_passes_the_gate(self) -> None:
        self.assertEqual([f.format() for f in self.empty.errors], [])

    def test_a_shape_waits_for_its_landing_zone_once(self) -> None:
        waiting = [f for f in self.empty.warnings if f.code == "library.no_landing_zone"]
        self.assertTrue(waiting)
        shapes = [f.message.split()[1] for f in waiting]
        self.assertEqual(len(shapes), len(set(shapes)), "one finding per shape, not one per part")
        self.assertNotIn("library.unbound_component", [f.code for f in self.empty.errors])

    def test_the_columns_left_out_are_said(self) -> None:
        self.assertTrue(any("app_code" in line for line in self.outcome.skipped), self.outcome.skipped)

    def test_a_view_of_a_layer_not_brought_in_yet_waits(self) -> None:
        codes = {f.message.split()[1]: f.code for f in self.imported.warnings + self.imported.errors
                 if f.code.startswith("view.")}
        self.assertEqual(codes.get("capability-map"), "view.nothing_yet")
        self.assertEqual(codes.get("system-context"), "view.nothing_yet")

    def test_what_still_fails_is_a_filter_on_something_that_exists(self) -> None:
        """A view of systems in the sample's Servicing domain, in an estate
        with systems and no such domain, is a view to retarget: still an
        error, and the only kind left."""
        failing = {f.message.split()[1] for f in self.imported.errors}
        self.assertIn("domain-servicing", failing)
        self.assertEqual({f.code for f in self.imported.errors}, {"view.unresolvable"})
        for view_id in failing:
            view = [v for v in load_views(self.root / "30_VIEWS") if v.view_id == view_id][0]
            kinds = [c.get("type") for c in view.scope.get("include") or []]
            self.assertTrue(any(model_module.load(self.root).all_of(k) for k in kinds), view_id)


class TestTheSeedStaysTheSamples(unittest.TestCase):
    def test_refresh_leaves_the_seed_of_a_model_that_is_not_the_sample(self) -> None:
        with Sandbox(seed=True) as root:
            _run("--root", str(root), "clear", "--yes")
            seed = root / "90_EXAMPLE" / "csv" / "systems.csv"
            before = seed.read_bytes()
            said = _run("--root", str(root), "refresh")
            self.assertIn("not the sample estate", said)
            self.assertEqual(seed.read_bytes(), before)


def _server_for(root: Path):
    sys.path.insert(0, str(root / "50_ENGINE"))
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestTheComposersEndpoints(unittest.TestCase):
    """The view composer reads a vocabulary and previews data, not text."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox(seed=True)
        cls.root = cls.box.__enter__()
        cls.server = _server_for(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def test_the_vocabulary_is_read_from_the_model(self) -> None:
        vocab = self.server.api_view({"id": ["system-context"]}, None)["vocab"]
        systems = vocab["types"]["systems"]
        self.assertGreater(systems["count"], 0)
        status = [f for f in systems["fields"] if f["name"] == "status"][0]
        self.assertIn("Active", status["values"])
        names = {r["name"] for r in vocab["relations"]}
        self.assertIn("system_reads_writes", names)

    def test_a_preview_from_data_hands_back_the_file_it_would_save(self) -> None:
        data = self.server.api_view({"id": ["system-context"]}, None)["data"]
        data["title"] = "System Context, Retitled"
        payload = self.server.api_view_preview(None, {"id": "system-context", "data": data})
        from terrane.loader import parse_data_text

        self.assertEqual(parse_data_text(payload["text"])["title"], "System Context, Retitled")
        self.assertIn("# Only the systems actors reach directly.", payload["text"],
                      "the comment beside the expansion rule survives")
        self.assertGreater(payload["counts"]["nodes"], 0)

    def test_a_preview_from_text_hands_back_the_data(self) -> None:
        text = (self.root / "30_VIEWS" / "system-context.view.yaml").read_text(encoding="utf-8")
        payload = self.server.api_view_preview(None, {"text": text})
        self.assertEqual(payload["data"]["view_id"], "system-context")

    def test_a_new_view_is_written_plain(self) -> None:
        data = {"view_id": "probe-new", "title": "Probe", "kind": "map",
                "scope": {"include": [{"type": "systems"}]}}
        payload = self.server.api_view_preview(None, {"data": data})
        self.assertTrue(payload["text"].startswith("view_id: probe-new"))


if __name__ == "__main__":
    unittest.main()
