"""Tests for the CSV importer and the app's write paths.

The delete tests are here because of a real bug: an earlier guard decided
whether a file held several records by checking whether its text started with
`-`. A leading comment defeated that, so deleting one org unit deleted the file
holding all eight of them. Anything that removes files gets a regression test.
"""

from __future__ import annotations

import csv
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import importer, model as model_module, validate  # noqa: E402
from terrane.query import load_views  # noqa: E402
from terrane.schema import ENTITY_TYPES  # noqa: E402

from _fixture import EXAMPLE_CSV, REPO, Sandbox as _Sandbox  # noqa: E402


class TestImporter(unittest.TestCase):
    def test_example_csvs_exist(self) -> None:
        self.assertTrue((EXAMPLE_CSV / "systems.csv").exists())

    def test_import_populates_an_empty_model(self) -> None:
        with _Sandbox() as root:
            empty = model_module.load(root)
            self.assertEqual(sum(len(v) for v in empty.entities.values()), 0)

            outcome = importer.import_csv(root, EXAMPLE_CSV, empty)
            self.assertGreater(len(outcome.written), 20)

            loaded = model_module.load(root)
            self.assertGreater(len(loaded.all_of("systems")), 10)
            self.assertGreater(len(loaded.all_of("interfaces")), 10)

    def test_imported_model_validates_clean(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            loaded = model_module.load(root)
            report = validate.run(loaded, load_views(root / "30_VIEWS"))
            self.assertEqual([f.format() for f in report.errors], [])

    def test_import_is_a_faithful_round_trip(self) -> None:
        """Export then import must not lose or invent entities."""
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            loaded = model_module.load(root)
            for type_name in ("systems", "interfaces", "data_assets", "capabilities"):
                csv_path = EXAMPLE_CSV / ("%s.csv" % type_name)
                if not csv_path.exists():
                    continue
                # Counted with the csv module, not by lines: descriptions
                # contain embedded newlines inside quoted fields.
                with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                    rows = sum(1 for _ in csv.DictReader(handle))
                self.assertEqual(
                    len(loaded.all_of(type_name)), rows,
                    "%s: model holds a different count than the CSV" % type_name,
                )

    def test_derived_archetype_fields_are_not_imported(self) -> None:
        """A flattened export cannot round-trip archetype linkage.

        Importing `archetype` back onto a system would make the loader treat it
        as an instance and expand it a second time.
        """
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            loaded = model_module.load(root)
            for type_name in ENTITY_TYPES:
                for record in loaded.all_of(type_name):
                    self.assertIsNone(record.get("archetype_instance"))

    def test_existing_records_are_reported_not_overwritten(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            first = model_module.load(root)
            path = first.get("systems", "SYS-CORE-LEDGER")["_source_file"]
            marker = Path(path).read_text(encoding="utf-8") + "\n# hand edit\n"
            Path(path).write_text(marker, encoding="utf-8")

            outcome = importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            self.assertGreater(len(outcome.conflicts), 0)
            self.assertIn("# hand edit", Path(path).read_text(encoding="utf-8"))

    def test_overwrite_replaces_when_asked(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            path = Path(model_module.load(root).get("systems", "SYS-CORE-LEDGER")["_source_file"])
            path.write_text(path.read_text(encoding="utf-8") + "\n# hand edit\n", encoding="utf-8")
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root), overwrite=True)
            self.assertNotIn("# hand edit", path.read_text(encoding="utf-8"))

    def test_only_limits_what_is_imported(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root), only=["org_units"])
            loaded = model_module.load(root)
            self.assertGreater(len(loaded.all_of("org_units")), 0)
            self.assertEqual(len(loaded.all_of("systems")), 0)

    def test_blank_columns_are_dropped_not_written_empty(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            path = Path(model_module.load(root).get("systems", "SYS-STATEMENTS")["_source_file"])
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(': ""', text)
            self.assertNotIn(":\n", text.replace("\n\n", "\n"))


def _server_for(root: Path):
    """The app server module, pointed at a sandbox, without an HTTP server."""
    sys.path.insert(0, str(root / "50_ENGINE"))
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestAppWritePaths(unittest.TestCase):
    """The app server's guards, exercised without starting an HTTP server."""

    def _server(self, root: Path):
        return _server_for(root)

    def test_shared_reference_file_is_never_deleted(self) -> None:
        """Regression: this once removed all eight org units at once."""
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            server = self._server(root)

            shared_file = root / "10_MODEL" / "org_units" / "org_units.yaml"
            self.assertTrue(shared_file.exists())
            units = model_module.load(root).all_of("org_units")
            before = len(units)
            self.assertGreater(before, 1)
            shared_id = str(units[0]["org_unit_id"])

            with self.assertRaises(server.ApiError) as caught:
                server.api_delete(None, {"id": shared_id})
            self.assertEqual(caught.exception.status, 409)

            self.assertTrue(shared_file.exists())
            self.assertEqual(len(model_module.load(root).all_of("org_units")), before)

    def test_leading_comment_does_not_defeat_the_shared_file_guard(self) -> None:
        """The exact shape of the original bug."""
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            shared_file = root / "10_MODEL" / "org_units" / "org_units.yaml"
            text = shared_file.read_text(encoding="utf-8")
            self.assertTrue(text.lstrip().startswith("#"), "fixture should lead with a comment")

            server = self._server(root)
            shared_id = str(model_module.load(root).all_of("org_units")[0]["org_unit_id"])
            with self.assertRaises(server.ApiError):
                server.api_delete(None, {"id": shared_id})
            self.assertTrue(shared_file.exists())

    def test_single_record_file_deletes_cleanly(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            server = self._server(root)
            path = Path(model_module.load(root).get("systems", "SYS-STATEMENTS")["_source_file"])
            self.assertTrue(path.exists())
            server.api_delete(None, {"id": "SYS-STATEMENTS"})
            self.assertFalse(path.exists())

    def test_delete_refuses_outside_the_model_folder(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            server = self._server(root)
            with self.assertRaises(server.ApiError):
                server.api_delete(None, {"id": "../../etc/passwd"})

    def test_save_refuses_an_unknown_field(self) -> None:
        with _Sandbox() as root:
            server = self._server(root)
            with self.assertRaises(server.ApiError):
                server.api_save(None, {
                    "type": "systems", "id": "SYS-NEW", "values": {"nonsense": "x"},
                })

    def test_save_writes_a_readable_file(self) -> None:
        with _Sandbox() as root:
            server = self._server(root)
            server.api_save(None, {
                "type": "systems",
                "id": "SYS-NEW",
                "values": {
                    "name": "New System", "status": "Active",
                    "owner_org_id": "ORG-X", "criticality": "Low",
                    "tags": "one, two",
                },
            })
            text = (root / "10_MODEL" / "systems" / "SYS-NEW.yaml").read_text(encoding="utf-8")
            self.assertIn("system_id: SYS-NEW", text)
            self.assertIn("tags: [one, two]", text)
            self.assertNotIn(': ""', text)


if __name__ == "__main__":
    unittest.main()


class TestLibraryPanel(unittest.TestCase):
    """The Library panel's fourth shelf: the landing zones, read off the model
    the way the catalog page reads them."""

    def test_the_landing_zones_are_on_the_shelf(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            server = _server_for(root)
            zones = {z["provider"]: z for z in server.api_library(None, None)["landingZones"]}
            self.assertEqual(sorted(zones), ["AWS", "Azure", "GCP"])
            self.assertIn("gcp-digital-product", zones["GCP"]["shapes"])
            self.assertEqual(zones["GCP"]["gaps"], 0)
            self.assertIn("aws-product-onboarding", zones["AWS"]["shapes"])
            azure = {k["kind"]: k for k in zones["Azure"]["kinds"]}
            # Event Hubs answers for the stream the rewards worker asked for,
            # with who asks; and Key Vault answering for a kind that is not
            # its own, saying which it is.
            self.assertFalse(azure["event-stream"]["gap"])
            self.assertEqual(azure["event-stream"]["services"][0]["id"], "TS-AZURE-EVENTHUBS")
            self.assertEqual(azure["event-stream"]["askedBy"], ["async-worker (stream)"])
            self.assertEqual(zones["Azure"]["gaps"], 0)
            self.assertFalse(azure["kms"]["gap"])
            # Untag Event Hubs and the shelf shows the gap, the row to read.
            model = model_module.load(root)
            record = next(s for s in model.all_of("tech_services") if s["tech_service_id"] == "TS-AZURE-EVENTHUBS")
            record["tags"] = [t for t in model.list_of(record, "tags") if t != "landing-zone"]
            gapped = {z["provider"]: z for z in server._library_landing_zones(model)}
            self.assertTrue({k["kind"]: k for k in gapped["Azure"]["kinds"]}["event-stream"]["gap"])
            self.assertEqual(gapped["Azure"]["gaps"], 1)
            self.assertEqual(azure["kms"]["services"][0]["alsoKind"], "secrets-manager")
            self.assertIsNone(azure["secrets-manager"]["services"][0]["alsoKind"])
            aws = {k["kind"]: k for k in zones["AWS"]["kinds"]}
            self.assertTrue(aws["hybrid-link"]["ambiguous"])
            self.assertEqual(zones["AWS"]["gaps"], 0)


class TestLibraryAdoption(unittest.TestCase):
    """The Library panel's shapes-and-the-estate shelf, off the seed."""

    def test_the_estate_is_measured_against_the_shapes(self) -> None:
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            server = _server_for(root)
            adoption = server.api_library(None, None)["adoption"]
            # The seed is an export: its products carry no archetype, so none
            # is on a shape there, and the ones that are in the repository
            # come out as candidates for the shape they sit on.
            self.assertEqual(adoption["onShapes"], [])
            fits = {(c["product"], c["shape"]) for c in adoption["candidates"]}
            self.assertIn(("PRD-CARD-SERVICING", "azure-digital-product"), fits)
            self.assertIn(("PRD-REWARDS", "azure-digital-product"), fits)


class TestDriftPanel(unittest.TestCase):
    """The same reconciliation the command runs, for the app, read-only."""

    def test_the_model_is_reconciled_against_the_sample_export(self) -> None:
        import shutil

        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            source = REPO / "60_SOURCES" / "servicenow"
            (root / "60_SOURCES" / "servicenow").mkdir(parents=True)
            for name in ("sample_cmdb_ci_export.csv", "field_sot.yaml"):
                shutil.copy(source / name, root / "60_SOURCES" / "servicenow" / name)
            server = _server_for(root)
            payload = server.api_cmdb_drift({}, None)
            self.assertEqual(payload["export"], "60_SOURCES/servicenow/sample_cmdb_ci_export.csv")
            self.assertGreater(payload["ciRecords"], 10)
            self.assertEqual(payload["coverage"]["systems"], len(model_module.load(root).all_of("systems")))
            self.assertIn("ATTR_MISMATCH", payload["counts"])
            self.assertTrue(any(r["category"] == "ATTR_MISMATCH" and r["field"] for r in payload["rows"]))
            self.assertIn("MODEL_ONLY", payload["actions"])

    def test_an_export_outside_the_repository_is_refused(self) -> None:
        with _Sandbox() as root:
            server = _server_for(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_cmdb_drift({"export": ["../../etc/passwd"]}, None)
            self.assertEqual(caught.exception.status, 400)
            with self.assertRaises(server.ApiError) as missing:
                server.api_cmdb_drift({}, None)
            self.assertEqual(missing.exception.status, 404)


class TestStaticSiteExport(unittest.TestCase):
    """The hosted demo must answer every GET the UI actually makes."""

    def _export(self, root):
        import importlib
        sys.path.insert(0, str(REPO / "80_APP" / "tools"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import server as server_module
        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        import export_site
        importlib.reload(export_site)
        export_site.server = server_module
        export_site.REPO_ROOT = root
        return export_site

    def test_every_view_and_entity_is_baked(self) -> None:
        """One file per view and per entity, whatever the model holds.

        Deliberately seeded with two entity types rather than the whole model.
        The exporter is O(entities) and bakes six reports for each, so running
        it over 433 of them made this one test 139 of the suite's 280 seconds
        while exercising exactly the same code paths. What is under test is
        that the loop covers everything it is given.
        """
        import json
        with _Sandbox() as root:
            importer.import_csv(
                root, EXAMPLE_CSV, model_module.load(root),
                only=["systems", "org_units"],
            )
            export_site = self._export(root)
            out = root / "site"
            export_site.copy_assets(out)
            export_site.bake_api(out)

            overview = json.loads((out / "api" / "overview.json").read_text(encoding="utf-8"))
            for view in overview["views"]:
                self.assertTrue(
                    (out / "api" / "graph" / ("%s.json" % view["viewId"])).exists(),
                    "view %s was not baked" % view["viewId"],
                )
                # And in every other tone, under its own folder, which is where
                # the shim looks when the page asks for that tone.
                for tone in overview["tones"][1:]:
                    self.assertTrue(
                        (out / "api" / tone / "graph" / ("%s.json" % view["viewId"])).exists(),
                        "view %s was not baked in %s" % (view["viewId"], tone),
                    )
            for tone in overview["tones"][1:]:
                toned = json.loads((out / "api" / tone / "overview.json").read_text(encoding="utf-8"))
                self.assertNotEqual(toned["swatches"], overview["swatches"], "the %s overview is not its own" % tone)
            # A view that takes a subject is baked once per subject the
            # picker offers, so the hosted demo can change the diagram.
            systems = json.loads((out / "api" / "list" / "systems.json").read_text(encoding="utf-8"))["items"]
            self.assertTrue(systems)
            for view in overview["views"]:
                if "system" not in (view.get("parameters") or []):
                    continue
                for item in systems:
                    self.assertTrue(
                        (out / "api" / "graph" / view["viewId"] / ("system--%s.json" % item["id"])).exists(),
                        "%s was not baked for %s" % (view["viewId"], item["id"]),
                    )
            listing = json.loads((out / "api" / "list.json").read_text(encoding="utf-8"))
            self.assertGreater(len(listing["items"]), 10)
            self.assertLess(len(listing["items"]), 200, "seed the subset, not the model")
            for item in listing["items"]:
                self.assertTrue(
                    (out / "api" / "entity" / ("%s.json" % item["id"])).exists(),
                    "entity %s was not baked" % item["id"],
                )

    def test_a_folder_that_holds_anything_is_refused_and_left_alone(self) -> None:
        """The bake once cleared `--out` with `shutil.rmtree`, whatever it
        named, and `--out .` named the repository. A folder that holds
        anything is refused now, before a byte is written, and kept as it
        was."""
        import io
        from contextlib import redirect_stderr

        with _Sandbox() as root:
            export_site = self._export(root)
            mine = root / "site" / "mine.txt"
            mine.parent.mkdir()
            mine.write_text("kept", encoding="utf-8")
            before = sorted(p.name for p in root.iterdir())
            for out in (".", str(mine.parent)):
                with self.subTest(out=out):
                    said = io.StringIO()
                    with redirect_stderr(said):
                        self.assertEqual(export_site.main(["--out", out]), 2)
                    self.assertIn("nothing was written", said.getvalue())
            self.assertEqual(sorted(p.name for p in root.iterdir()), before)
            self.assertEqual([p.name for p in mine.parent.iterdir()], ["mine.txt"])
            self.assertEqual(mine.read_text(encoding="utf-8"), "kept")

    def test_shim_is_installed_before_the_app(self) -> None:
        with _Sandbox(seed=True) as root:
            export_site = self._export(root)
            out = root / "site"
            export_site.copy_assets(out)
            html = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn("static-shim.js", html)
            self.assertLess(
                html.index("static-shim.js"), html.index('src="app.js"'),
                "the shim has to replace fetch before app.js makes a request",
            )

    def test_each_published_estate_links_the_others(self) -> None:
        """Every site gets the list, its own entry marked, and a link that
        resolves from where that page is: a folder's own `api/` beside it,
        not the top site's."""
        import json
        import tempfile
        export_site = self._export(REPO)
        sites = [("", "The sample estate", "A card issuer"), ("thurman-health", "Thurman Health", "A health system")]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            export_site.link_estates(out, sites)
            top = json.loads((out / "estates.json").read_text(encoding="utf-8"))["estates"]
            inner = json.loads((out / "thurman-health" / "estates.json").read_text(encoding="utf-8"))["estates"]
        self.assertEqual([(e["name"], e["href"], e["here"]) for e in top],
                         [("The sample estate", "./", True), ("Thurman Health", "thurman-health/", False)])
        self.assertEqual([(e["href"], e["here"]) for e in inner], [("../", False), ("./", True)])
        self.assertEqual(top[1]["line"], "A health system")

    def test_every_published_estate_is_a_model_of_its_own(self) -> None:
        """An estate the site publishes is a root with a model in it, not the
        sample, and its folder cannot land on top of the site's own files."""
        from terrane.cli import is_sample_estate
        export_site = self._export(REPO)
        taken = set(export_site.ASSETS) | {"api", "index.html", "static-shim.js", export_site.ESTATES_FILE}
        self.assertTrue(export_site.ESTATES)
        for folder, root, line in export_site.ESTATES:
            with self.subTest(estate=folder):
                self.assertRegex(folder, r"^[a-z0-9][a-z0-9-]*$")
                self.assertNotIn(folder, taken)
                self.assertTrue((REPO / root / "10_MODEL" / "model.yaml").is_file())
                self.assertFalse(is_sample_estate(REPO / root))
                self.assertTrue(line)

    def test_the_tab_names_the_model(self) -> None:
        """Two estates side by side were two tabs called "Terrane", and the
        old replacement looked for a title the page no longer had."""
        import json
        import tempfile
        export_site = self._export(REPO)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            export_site.copy_assets(out)
            (out / "api").mkdir()
            (out / "api" / "overview.json").write_text(json.dumps({"modelName": "Thurman Health"}), encoding="utf-8")
            export_site.name_the_page(out)
            html = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>Thurman Health · Terrane, read-only</title>", html)

    def test_app_js_is_copied_unmodified(self) -> None:
        """The hosted demo must not be able to drift from the local tool."""
        with _Sandbox(seed=True) as root:
            export_site = self._export(root)
            out = root / "site"
            export_site.copy_assets(out)
            self.assertEqual(
                (out / "app.js").read_bytes(),
                (REPO / "80_APP" / "web" / "app.js").read_bytes(),
            )

    def test_every_entity_type_has_a_hue_and_a_shape(self) -> None:
        """Hue and shape carry the entity type, so a type the palette or the
        shape table has never heard of draws as an anonymous gray box. That
        happened to the change entities, and it is the kind of omission that
        only shows up by looking at the running app."""
        from terrane.palette import TYPE_SWATCHES

        shapes = self._app_shapes()
        for name in ENTITY_TYPES:
            with self.subTest(entity=name):
                self.assertIn(name, TYPE_SWATCHES)
                self.assertIn(name, shapes)

    def test_every_shape_has_a_legend_swatch(self) -> None:
        """A shape with no swatch falls back to a rounded rectangle, so the
        legend quietly says something the diagram does not."""
        app_js = (REPO / "80_APP" / "web" / "app.js").read_text(encoding="utf-8")
        drawn = set(re.findall(r"^\s+\"([a-z-]+)\": '<", app_js, re.M))
        self.assertTrue(drawn)
        self.assertEqual(set(self._app_shapes().values()) - drawn, set())

    @staticmethod
    def _app_shapes() -> dict:
        """The `SHAPES` table out of `app.js`, read as text.

        Parsing the app's JavaScript from a Python test is not elegant. The
        alternative is a browser in the suite, and the thing being checked --
        that a new entity type was given a hue and a shape -- is worth a
        regular expression.
        """
        app_js = (REPO / "80_APP" / "web" / "app.js").read_text(encoding="utf-8")
        block = app_js.split("var SHAPES = {", 1)[1].split("};", 1)[0]
        return dict(re.findall(r"(\w+):\s*\"([a-z-]+)\"", block))

    def test_site_makes_no_third_party_requests(self) -> None:
        with _Sandbox(seed=True) as root:
            export_site = self._export(root)
            out = root / "site"
            export_site.copy_assets(out)
            for name in ("index.html", "styles.css", "app.js", "static-shim.js"):
                text = (out / name).read_text(encoding="utf-8")
                for scheme in ("http://", "https://"):
                    for line in text.splitlines():
                        if scheme in line and ("src=" in line or "url(" in line or "href=" in line):
                            self.fail("%s loads something off-origin: %s" % (name, line.strip()))


class TestRecentChanges(unittest.TestCase):
    """The home page's recent changes come from git, where there is one."""

    def test_the_log_is_honest_where_there_is_no_history(self) -> None:
        with _Sandbox() as root:
            server = _server_for(root)
            payload = server.api_log({}, None)
            self.assertEqual(payload["commits"], [])
            self.assertTrue(payload.get("why"), "an empty log says why it is empty")

    def test_the_log_lists_the_repository_commits(self) -> None:
        server = _server_for(REPO)
        payload = server.api_log({"n": ["3"]}, None)
        # CI checks the repository out one commit deep, so the log there is
        # one line long; asking for three is a ceiling, not a promise.
        self.assertTrue(1 <= len(payload["commits"]) <= 3, payload)
        for commit in payload["commits"]:
            self.assertEqual(sorted(commit), ["date", "sha", "subject"])
            self.assertRegex(commit["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(commit["subject"])


class TestEveryPageKeepsItsPlace(unittest.TestCase):
    """A reload on the Model, the Library, Checks or a flow landed on Home or
    the capability map: those pages wrote no address. And hiding the
    sidebar on any page but a drawing left no way back, since the button
    sat in the drawing's head, which every page hides. Both read off the
    app's own files, as the shapes are above."""

    WEB = REPO / "80_APP" / "web"
    # Drawn on the sheet, not opened over it: their address is the view's.
    DRAWN = {"report", "timeline"}

    def _app(self) -> str:
        return (self.WEB / "app.js").read_text(encoding="utf-8")

    def test_every_page_writes_an_address(self) -> None:
        app_js = self._app()
        panels = set(re.findall(r'state\.panel = "([a-z]+)"', app_js))
        self.assertIn("library", panels)
        addressed = app_js.split("  function syncUrl() {", 1)[1].split("  function readUrl() {", 1)[0]
        for panel in sorted(panels - self.DRAWN):
            with self.subTest(panel=panel):
                self.assertIn('"%s"' % panel, addressed,
                              "the %s page writes no address, so a reload loses it" % panel)

    def test_every_address_written_is_read_back(self) -> None:
        app_js = self._app()
        written = app_js.split("  function pageHash() {", 1)[1].split("  function isPageHash(", 1)[0]
        read = app_js.split("  function isPageHash(w) {", 1)[1].split("  }", 1)[0]
        pages = set(re.findall(r'return "#([a-z]+)', written))
        self.assertEqual(pages, {"model", "library", "checks", "flows"})
        for page in sorted(pages):
            with self.subTest(page=page):
                self.assertIn("w.%s !== undefined" % page, read)

    def test_the_way_back_to_the_sidebar_is_outside_the_head_pages_hide(self) -> None:
        html = (self.WEB / "index.html").read_text(encoding="utf-8")
        stage = html.index('<main class="stage">')
        head = html.index('<div class="stage-head">')
        button = html.index('id="btnRailOpen"')
        self.assertLess(stage, button)
        self.assertLess(button, head, "the button is back in the head that showPanel hides")
        self.assertIn('.querySelector(".stage-head").hidden = on', self._app(),
                      "if the pages stop hiding the head, this test is guarding the wrong thing")


class TestTheTour(unittest.TestCase):
    """The tour is offered once, on Home, and the offer can be put away for
    good. Put away with no way back, it would be the hidden sidebar again:
    so Help, the jump box and Home's banner each start it, and the steps it
    names are the seven the design file draws (V11)."""

    def _app(self) -> str:
        return (REPO / "80_APP" / "web" / "app.js").read_text(encoding="utf-8")

    @staticmethod
    def _function(app_js: str, name: str) -> str:
        body = app_js.split("  function %s(" % name, 1)[1]
        return body.split("\n  function ", 1)[0]

    def test_the_tour_can_always_be_started_again(self) -> None:
        app_js = self._app()
        self.assertIn('tourStore("off")', app_js, "the offer can be put away for good")
        for where in ("openGuide", "openStart"):
            with self.subTest(where=where):
                self.assertIn("startTour(", self._function(app_js, where))
        actions = app_js.split("return here.concat(", 1)[1].split(");", 1)[0]
        self.assertIn('name: "Take the tour"', actions)
        self.assertIn("startTour(", actions)

    def test_the_seven_steps_the_design_draws(self) -> None:
        steps = self._app().split("var TOUR_STEPS = [", 1)[1].split("\n  ];", 1)[0]
        titles = re.findall(r'\{ title: "([^"]+)"', steps)
        self.assertEqual(titles, ["Every diagram, by layer", "Open one", "Press a box", "What depends on it",
                                  "Move around", "The model underneath", "Draw your own"])
        self.assertNotIn("coach", self._app().replace("COACH", ""), "the strip the tour replaced is gone")
