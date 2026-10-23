"""A record is changed where it lives.

Six hundred records in the model share a file with others, and the app's form
used to write every save to `<folder>/<ID>.yaml`: a second copy beside the
first, and a model the next load refused. These hold the save, the delete and
the import to the file the record is actually in.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import importer, model as model_module, records  # noqa: E402
from terrane.loader import parse_data_text, read_data_file  # noqa: E402

from _fixture import EXAMPLE_CSV, REPO, Sandbox  # noqa: E402

SHARED = """# Two systems written by hand into one file.
#
# The comment above the first record stays where it is.

- system_id: SYS-ALPHA
  name: Alpha
  description: >
    A description wrapped by hand
    over two lines.
  status: Active
  owner_org_id: ORG-A
  criticality: Medium

# The second one.
- system_id: SYS-BETA
  name: Beta
  status: Planned
  owner_org_id: ORG-A
  criticality: Low
"""


def _values(text: str, entity_id: str) -> dict:
    record = [r for r in parse_data_text(text) if r["system_id"] == entity_id][0]
    return {k: v for k, v in record.items() if k != "system_id"}


class TestRecordLines(unittest.TestCase):
    def test_an_unchanged_save_changes_nothing(self) -> None:
        self.assertEqual(records.replace_item(SHARED, "systems", "SYS-ALPHA", _values(SHARED, "SYS-ALPHA")), SHARED)

    def test_one_field_changed_is_one_line_changed(self) -> None:
        values = _values(SHARED, "SYS-ALPHA")
        values["criticality"] = "High"
        after = records.replace_item(SHARED, "systems", "SYS-ALPHA", values)
        before_lines, after_lines = SHARED.splitlines(), after.splitlines()
        self.assertEqual(len(before_lines), len(after_lines))
        changed = [(a, b) for a, b in zip(before_lines, after_lines) if a != b]
        self.assertEqual(changed, [("  criticality: Medium", "  criticality: High")])

    def test_the_wrapped_description_survives_a_change_elsewhere(self) -> None:
        values = _values(SHARED, "SYS-ALPHA")
        values["status"] = "Deprecated"
        after = records.replace_item(SHARED, "systems", "SYS-ALPHA", values)
        self.assertIn("    A description wrapped by hand\n    over two lines.", after)

    def test_a_field_sent_empty_is_cleared(self) -> None:
        values = _values(SHARED, "SYS-BETA")
        del values["status"]
        after = records.replace_item(SHARED, "systems", "SYS-BETA", values)
        beta = [r for r in parse_data_text(after) if r["system_id"] == "SYS-BETA"][0]
        self.assertNotIn("status", beta)

    def test_a_field_the_form_never_offers_is_kept(self) -> None:
        """The old writer dropped `archetype` and every key that is not a
        field, so correcting a product's name took it off its shape."""
        text = (
            "product_id: PRD-X\nname: X\narchetype: some-shape\n"
            "parameters:\n  slug: x\nmodules:\n  - module: a-part\n"
        )
        lines = records.merge_record(text.splitlines(), "products", "PRD-X", {"name": "Y"})
        data = parse_data_text("\n".join(lines))
        self.assertEqual(data["name"], "Y")
        self.assertEqual(data["archetype"], "some-shape")
        self.assertEqual(data["parameters"], {"slug": "x"})
        self.assertEqual(data["modules"], [{"module": "a-part"}])

    def test_remove_takes_one_record_and_its_gap(self) -> None:
        after = records.remove_item(SHARED, "systems", "SYS-ALPHA")
        self.assertEqual([r["system_id"] for r in parse_data_text(after)], ["SYS-BETA"])
        self.assertIn("# The comment above the first record stays where it is.", after)
        self.assertNotIn("\n\n\n", after)

    def test_append_adds_one_record(self) -> None:
        after = records.append_item(SHARED, "systems", "SYS-GAMMA", {"name": "Gamma", "status": "Active"})
        self.assertTrue(after.startswith(SHARED.rstrip("\n")))
        self.assertEqual([r["system_id"] for r in parse_data_text(after)], ["SYS-ALPHA", "SYS-BETA", "SYS-GAMMA"])

    def test_an_unknown_field_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            records.replace_item(SHARED, "systems", "SYS-ALPHA", {"shade": "red"})

    def test_a_missing_record_is_a_key_error(self) -> None:
        with self.assertRaises(KeyError):
            records.replace_item(SHARED, "systems", "SYS-NONE", {})


class TestHome(unittest.TestCase):
    def test_the_kinds(self) -> None:
        with Sandbox() as root:
            folder = root / "10_MODEL" / "systems"
            folder.mkdir(parents=True)
            own = folder / "SYS-OWN.yaml"
            own.write_text("system_id: SYS-OWN\nname: Own\n", encoding="utf-8")
            shared = folder / "shared.yaml"
            shared.write_text(SHARED, encoding="utf-8")
            self.assertEqual(records.home_of("systems", {"_source_file": str(own)}).kind, "own")
            self.assertEqual(records.home_of("systems", {"_source_file": str(shared)}).kind, "shared")
            self.assertEqual(
                records.home_of("systems", {"_source_file": str(shared), "source": "Somewhere"}).kind,
                "harvested")
            self.assertEqual(
                records.home_of("capabilities", {"_source_file": str(shared), "source": "Somewhere"}).kind,
                "imported")
            self.assertEqual(records.home_of("systems", {"archetype_instance": "PRD-X"}).kind, "generated")


def _server_for(root: Path):
    sys.path.insert(0, str(root / "50_ENGINE"))
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestSaveWhereItLives(unittest.TestCase):
    """Through the endpoint, against a seeded sandbox with shared files."""

    def _sandbox(self):
        box = Sandbox(seed=True)
        root = box.__enter__()
        self.addCleanup(box.__exit__, None, None, None)
        folder = root / "10_MODEL" / "systems"
        (folder / "shared.yaml").write_text(
            SHARED.replace("ORG-A", "ORG-TECH"), encoding="utf-8")
        harvested = folder / "from_business_layer.yaml"
        harvested.write_text(
            "# Harvested.\n\n- system_id: SYS-HARVEST\n  name: Harvested thing\n"
            "  status: Proposed\n  owner_org_id: ORG-TECH\n  criticality: Medium\n"
            "  source: Business architecture repository\n\n"
            "- system_id: SYS-HARVEST-TWO\n  name: Another\n  status: Proposed\n"
            "  owner_org_id: ORG-TECH\n  criticality: Low\n"
            "  source: Business architecture repository\n",
            encoding="utf-8",
        )
        return root, _server_for(root)

    def test_a_shared_record_is_edited_in_place(self) -> None:
        root, server = self._sandbox()
        shared = root / "10_MODEL" / "systems" / "shared.yaml"
        values = _values(shared.read_text(encoding="utf-8"), "SYS-ALPHA")
        values["criticality"] = "High"
        res = server.api_save(None, {"type": "systems", "id": "SYS-ALPHA", "values": values})
        self.assertEqual(Path(res["path"]).name, "shared.yaml")
        self.assertFalse((root / "10_MODEL" / "systems" / "SYS-ALPHA.yaml").exists())
        loaded = model_module.load(root)
        self.assertEqual(loaded.get("systems", "SYS-ALPHA")["criticality"], "High")
        self.assertEqual(loaded.get("systems", "SYS-BETA")["name"], "Beta")

    def test_a_harvested_record_moves_into_its_own_file(self) -> None:
        root, server = self._sandbox()
        folder = root / "10_MODEL" / "systems"
        values = _values((folder / "from_business_layer.yaml").read_text(encoding="utf-8"), "SYS-HARVEST")
        values["description"] = "What it does, from its owner."
        res = server.api_save(None, {"type": "systems", "id": "SYS-HARVEST", "values": values})
        self.assertTrue(res["moved"])
        own = folder / "SYS-HARVEST.yaml"
        self.assertTrue(own.exists())
        record = read_data_file(own)
        self.assertEqual(record["source"], "Business architecture repository",
                         "it keeps saying where it came from until somebody confirms it")
        left = [r["system_id"] for r in read_data_file(folder / "from_business_layer.yaml")]
        self.assertEqual(left, ["SYS-HARVEST-TWO"])
        model_module.load(root)

    def test_an_imported_record_is_refused_and_nothing_changes(self) -> None:
        root, server = self._sandbox()
        loaded = model_module.load(root)
        capability = loaded.all_of("capabilities")[0]
        path = Path(capability["_source_file"])
        if not capability.get("source"):
            self.skipTest("the seed's capabilities carry no source")
        before = path.read_text(encoding="utf-8")
        with self.assertRaises(server.ApiError) as caught:
            server.api_save(None, {"type": "capabilities", "id": capability["capability_id"],
                                   "values": {"name": "Renamed"}})
        self.assertEqual(caught.exception.status, 409)
        self.assertIn("import", str(caught.exception))
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_a_save_the_reload_refuses_is_undone(self) -> None:
        """The plain save path used to write and reload with nothing to put
        back, so a refused reload left the bad file for the next start."""
        root, server = self._sandbox()
        shared = root / "10_MODEL" / "systems" / "shared.yaml"
        before = shared.read_text(encoding="utf-8")
        real, calls = server._load_all, []

        def refuses_after_the_write():
            calls.append(1)
            if len(calls) > 1:
                raise server.ModelError("refused on reload")
            return real()

        server._load_all = refuses_after_the_write
        self.addCleanup(setattr, server, "_load_all", real)
        values = _values(before, "SYS-ALPHA")
        values["criticality"] = "High"
        with self.assertRaises(server.ApiError) as caught:
            server.api_save(None, {"type": "systems", "id": "SYS-ALPHA", "values": values})
        self.assertIn("refused on reload", str(caught.exception))
        self.assertEqual(shared.read_text(encoding="utf-8"), before)

    def test_an_unknown_field_is_refused_before_anything_is_written(self) -> None:
        root, server = self._sandbox()
        shared = root / "10_MODEL" / "systems" / "shared.yaml"
        before = shared.read_text(encoding="utf-8")
        with self.assertRaises(server.ApiError):
            server.api_save(None, {"type": "systems", "id": "SYS-ALPHA", "values": {"shade": "red"}})
        self.assertEqual(shared.read_text(encoding="utf-8"), before)

    def test_deleting_a_shared_record_takes_only_it(self) -> None:
        root, server = self._sandbox()
        server.api_delete(None, {"id": "SYS-BETA"})
        shared = root / "10_MODEL" / "systems" / "shared.yaml"
        self.assertEqual([r["system_id"] for r in read_data_file(shared)], ["SYS-ALPHA"])

    def test_deleting_a_harvested_record_says_how_to_strike_it(self) -> None:
        _root, server = self._sandbox()
        with self.assertRaises(server.ApiError) as caught:
            server.api_delete(None, {"id": "SYS-HARVEST"})
        self.assertIn("aliases.yaml", str(caught.exception))

    def test_the_inspector_is_told_where_it_lives(self) -> None:
        _root, server = self._sandbox()
        payload = server.api_entity({"id": ["SYS-HARVEST"]}, None)
        self.assertEqual(payload["home"]["kind"], "harvested")
        self.assertTrue(payload["home"]["note"])


class TestImportKeepsWhatIsThere(unittest.TestCase):
    def test_a_second_reference_set_lands_beside_the_first(self) -> None:
        with Sandbox(seed=True) as root:
            shipped = root / "10_MODEL" / "org_units" / "org_units.yaml"
            before = shipped.read_text(encoding="utf-8")
            extra = root / "extra"
            extra.mkdir()
            (extra / "org_units.csv").write_text(
                "org_unit_id,name,status,shade\nORG-NEWCO,New company unit,Active,red\n", encoding="utf-8")
            outcome = importer.import_csv(root, extra, model_module.load(root))
            self.assertEqual(shipped.read_text(encoding="utf-8"), before)
            self.assertTrue((root / "10_MODEL" / "org_units" / "imported_org_units.yaml").exists())
            self.assertIsNotNone(model_module.load(root).get("org_units", "ORG-NEWCO"))
            self.assertTrue(any("shade" in line for line in outcome.skipped), outcome.skipped)

    def test_relations_are_added_not_written_over(self) -> None:
        with Sandbox(seed=True) as root:
            target = root / "10_MODEL" / "relations" / "imported_relations.yaml"
            before = read_data_file(target)
            extra = root / "extra"
            (extra / "relations").mkdir(parents=True)
            loaded = model_module.load(root)
            system = loaded.all_of("systems")[0]["system_id"]
            service = loaded.all_of("tech_services")[0]["tech_service_id"]
            (extra / "relations" / "system_uses_tech_service.csv").write_text(
                "system_id,tech_service_id\n%s,%s\n" % (system, service), encoding="utf-8")
            importer.import_csv(root, extra, loaded)
            after = read_data_file(target)
            for name, rows in before.items():
                for row in rows:
                    self.assertIn(row, after[name])
            model_module.load(root)


class TestTheHarvestLeavesPromotedSystemsAlone(unittest.TestCase):
    def test_a_system_outside_the_harvest_file_is_held(self) -> None:
        sys.path.insert(0, str(REPO / "50_ENGINE" / "tools"))
        import import_business_layer as business

        with Sandbox() as root:
            folder = root / "10_MODEL" / "systems"
            folder.mkdir(parents=True)
            (folder / "SYS-PROMOTED.yaml").write_text(
                "system_id: SYS-PROMOTED\nname: Promoted\nsource: Business architecture repository\n",
                encoding="utf-8")
            (folder / business.HARVEST_FILE).write_text(
                "- system_id: SYS-STILL\n  name: Still harvested\n"
                "  source: Business architecture repository\n", encoding="utf-8")
            held = business.existing_ids(root, "systems")
            self.assertIn("SYS-PROMOTED", held)
            self.assertNotIn("SYS-STILL", held)


if __name__ == "__main__":
    unittest.main()
