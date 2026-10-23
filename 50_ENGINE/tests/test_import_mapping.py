"""An inventory in its own words, imported through a mapping.

AAC-15 measured an organization's first week and found the gap was the
reshaping: an inventory has its own columns, its own values (`Tier 1`,
`Retired - pending`) and its own codes (`APP001`), and the importer took only
metamodel v2 CSVs. These hold `terrane import csv --map` to what the method says
it does: the sample in `60_SOURCES/inventory/` becomes a model the gate
passes; what the mapping does not place is held back and named, not guessed;
two rows that make one id and disagree are a conflict; a second run after the
mapping is fixed writes the held rows and nothing twice; and a mapping that is
wrong in itself is refused before anything is written.
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli, importer, inventory, jsonschema, loader, model as model_module, validate  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402
from terrane.query import load_views  # noqa: E402
from terrane.schema import CRITICALITY, ENTITY_TYPES  # noqa: E402

from _fixture import REPO, Sandbox, remove_scratch  # noqa: E402

SAMPLE = REPO / "60_SOURCES" / "inventory"


def _readers():
    """Each reader a mapping may be loaded with: PyYAML where it is
    installed, and the bundled one, which is all CI's model job has. An
    unquoted `Yes:` was refused by the first and accepted by the second."""
    from unittest import mock

    readers = [("bundled", mock.patch.object(loader, "_pyyaml", None))]
    if loader._pyyaml is not None:
        readers.insert(0, ("PyYAML", nullcontext()))
    return readers


def _model_files(root: Path):
    return sorted(p.relative_to(root).as_posix() for p in (root / "10_MODEL").rglob("*") if p.is_file())


class TestTheSampleInventory(unittest.TestCase):
    """The insurer's portfolio export and integration list, as shipped."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox()
        cls.root = cls.box.__enter__()
        cls.outcome = importer.import_csv(
            cls.root, SAMPLE, model_module.load(cls.root), mapping=SAMPLE / "mapping.yaml")
        cls.model = model_module.load(cls.root)
        cls.report = validate.run(cls.model, load_views(cls.root / "30_VIEWS"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def test_every_row_and_column_is_placed(self) -> None:
        self.assertEqual(self.outcome.held, [])
        self.assertEqual(self.outcome.conflicts, [])
        self.assertEqual(self.outcome.skipped, [], "every column is mapped or ignored")
        self.assertEqual(self.outcome.imported, {"org_units": 5, "systems": 10, "interfaces": 8})

    def test_ids_are_the_models_and_codes_are_kept(self) -> None:
        system = self.model.get("systems", "SYS-POLICY-ADMINISTRATION")
        self.assertIsNotNone(system)
        self.assertEqual(system["cmdb_ci_sys_id"], "APP001")
        self.assertIsNotNone(self.model.get("systems", "SYS-LEGACY-CLAIMS-MAINFRAME"),
                             "punctuation in a name is a separator, not an error")

    def test_values_are_the_metamodels(self) -> None:
        system = self.model.get("systems", "SYS-POLICY-ADMINISTRATION")
        self.assertEqual(system["criticality"], "High", "Tier 1")
        self.assertEqual(system["service_tier"], "Tier 1", "already the model's word")
        self.assertEqual(system["status"], "Active", "In Production")
        self.assertEqual(system["hosting"], "On-prem", "Data Center")
        self.assertEqual(self.model.get("systems", "SYS-LEGACY-CLAIMS-MAINFRAME")["status"], "Deprecated")
        billing = self.model.get("systems", "SYS-BILLING-AND-PAYMENTS")
        self.assertEqual((billing["hosting"], billing["cloud_provider"]), ("SaaS", "SaaS"))

    def test_references_resolve_by_name(self) -> None:
        system = self.model.get("systems", "SYS-POLICY-ADMINISTRATION")
        self.assertEqual(system["owner_org_id"], "ORG-UNDERWRITING-TECHNOLOGY")
        interface = self.model.get("interfaces", "INT-POLICY-RATING-REQUEST")
        self.assertEqual((interface["source_system_id"], interface["target_system_id"]),
                         ("SYS-POLICY-ADMINISTRATION", "SYS-RATING-ENGINE"))
        self.assertEqual((interface["protocol"], interface["integration_style"]), ("REST", "Request-response"))

    def test_a_department_named_by_many_rows_is_one_org_unit(self) -> None:
        self.assertEqual(sorted(r["org_unit_id"] for r in self.model.all_of("org_units")), [
            "ORG-CLAIMS-TECHNOLOGY", "ORG-DISTRIBUTION-TECHNOLOGY", "ORG-ENTERPRISE-TECHNOLOGY",
            "ORG-FINANCE-TECHNOLOGY", "ORG-UNDERWRITING-TECHNOLOGY"])

    def test_the_gate_finds_nothing_wrong_with_a_record(self) -> None:
        """What is left failing is the views about the sample estate that
        AAC-15 lists for retargeting, as after a v2 import."""
        self.assertEqual({f.code for f in self.report.errors}, {"view.unresolvable"})
        written = {str(p) for p in self.outcome.written}
        about_records = [f.format() for f in self.report.findings if f.where in written]
        self.assertEqual(about_records, [])

    def test_a_second_run_writes_nothing(self) -> None:
        again = importer.import_csv(
            self.root, SAMPLE, model_module.load(self.root), mapping=SAMPLE / "mapping.yaml")
        self.assertEqual(again.written, [])
        self.assertEqual(len(again.conflicts), 23)
        self.assertTrue(all("already in the model" in line for line in again.conflicts))


class TestALaterExport(unittest.TestCase):
    """The next quarter's export, after the portfolio renamed an application:
    its slug is a new id, its code is not, and the code wins."""

    def test_a_renamed_application_is_the_record_the_model_holds(self) -> None:
        with Sandbox() as root:
            importer.import_csv(root, SAMPLE, model_module.load(root), mapping=SAMPLE / "mapping.yaml")
            later = root / "later"
            later.mkdir()
            portfolio = (SAMPLE / "application_portfolio.csv").read_text(encoding="utf-8")
            self.assertEqual(portfolio.count("APP002,Claims Workbench,"), 1)
            (later / "application_portfolio.csv").write_text(
                portfolio.replace("APP002,Claims Workbench,", "APP002,Claims Hub,"), encoding="utf-8")
            (later / "integrations.csv").write_text(
                (SAMPLE / "integrations.csv").read_text(encoding="utf-8")
                + "IF-109,Claim photos,Claims Hub,Document Composition,REST,Real time,Live\n", encoding="utf-8")
            outcome = importer.import_csv(root, later, model_module.load(root), mapping=SAMPLE / "mapping.yaml")
            self.assertIn("system SYS-CLAIMS-HUB: APP002 is already SYS-CLAIMS-WORKBENCH in the model, "
                          "so it is not made a second time", outcome.conflicts)
            self.assertEqual(outcome.imported, {"interfaces": 1})
            model = model_module.load(root)
            self.assertIsNone(model.get("systems", "SYS-CLAIMS-HUB"))
            self.assertEqual(model.get("interfaces", "INT-CLAIM-PHOTOS")["source_system_id"],
                             "SYS-CLAIMS-WORKBENCH", "the new name finds the record it is")


#: Six applications with something wrong with most of them, and a file of
#: departments keyed by code. Each row is there for one reason.
APPS = """App ID,Application Name,Tier,Dept,Lifecycle,Notes
APP001,Policy Administration,Tier 1,IT,Live,
APP002,Claims Workbench,Tier 4,IT,Live,the tier nobody mapped
APP003,Agent Portal,Tier 2,Marketing,Live,a department that is not one
APP004,Rating Engine,Tier 2,,Live,no owner
APP005,Billing,Tier 1,IT,Live,
APP006,Billing,Tier 2,IT,Live,the same name with another tier
APP007,Document Composition,Tier 3,IT,Live,
APP007,Document Composition,Tier 3,IT,Live,
"""

DEPTS = """Dept,Department Name
IT,Information Technology
"""

LINKS = """Feed,From,To
Claims to policy,Claims Workbench,Policy Administration
Documents from policy,Policy Administration,Document Composition
"""

MAPPING = """description: A made-up inventory with something wrong in most rows.
org_units:
  file: depts.csv
  code: Dept
  id: {prefix: ORG-, from: code}
  columns:
    Department Name: name
  defaults:
    status: Active
systems:
  file: apps.csv
  code: App ID
  id: {prefix: SYS-, from: name}
  columns:
    Application Name: name
    Tier: criticality
    Dept: owner_org_id
    Lifecycle: status
  values:
    criticality:
      "Tier 1": High
      "Tier 2": Medium
      "Tier 3": Low
    status:
      Live: Active
interfaces:
  file: links.csv
  id: {prefix: INT-, from: name}
  columns:
    Feed: name
    From: source_system_id
    To: target_system_id
  defaults:
    status: Active
"""

#: What the report asked for, said in the mapping.
FIXED = MAPPING.replace('      "Tier 3": Low\n', '      "Tier 3": Low\n      "Tier 4": Low\n').replace(
    "    status:\n      Live: Active\n",
    "    status:\n      Live: Active\n    owner_org_id:\n      Marketing: ORG-IT\n  defaults:\n    owner_org_id: ORG-IT\n")


class TestWhatTheMappingDoesNotPlace(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox()
        cls.root = cls.box.__enter__()
        cls.source = cls.root / "inventory"
        cls.source.mkdir()
        for name, text in (("apps.csv", APPS), ("depts.csv", DEPTS), ("links.csv", LINKS),
                           ("mapping.yaml", MAPPING), ("fixed.yaml", FIXED)):
            (cls.source / name).write_text(text, encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["--root", str(cls.root), "import", "csv", "--from", str(cls.source),
                             "--map", str(cls.source / "mapping.yaml")])
        assert code == 0, out.getvalue()
        cls.said = out.getvalue()
        cls.model = model_module.load(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def test_what_could_be_placed_is_written(self) -> None:
        self.assertEqual(sorted(r["system_id"] for r in self.model.all_of("systems")),
                         ["SYS-DOCUMENT-COMPOSITION", "SYS-POLICY-ADMINISTRATION"])
        self.assertEqual(self.model.get("systems", "SYS-POLICY-ADMINISTRATION")["owner_org_id"], "ORG-IT",
                         "a reference by the inventory's code")
        self.assertEqual([r["interface_id"] for r in self.model.all_of("interfaces")],
                         ["INT-DOCUMENTS-FROM-POLICY"])

    def test_an_unmapped_value_holds_its_row_and_is_named(self) -> None:
        self.assertIn("system criticality: 'Tier 4' is not High, Medium or Low, "
                      "and the mapping does not say which it is (APP002)", self.said)

    def test_a_reference_to_nothing_holds_its_row(self) -> None:
        self.assertIn("system owner_org_id: 'Marketing' is no org unit in the model or in this import (APP003)",
                      self.said)

    def test_an_empty_required_field_holds_its_row(self) -> None:
        self.assertIn("system owner_org_id: empty, and the mapping gives no default (APP004)", self.said)

    def test_a_row_naming_a_held_row_is_held_with_it(self) -> None:
        self.assertIn("interface source_system_id: 'Claims Workbench' is a system this import holds back",
                      self.said)

    def test_two_rows_making_one_id_and_disagreeing_are_a_conflict(self) -> None:
        self.assertIn("system SYS-BILLING: 2 rows make this id and say different things (APP005, APP006)",
                      self.said)
        self.assertIsNone(self.model.get("systems", "SYS-BILLING"), "neither is the guess")

    def test_two_rows_saying_the_same_thing_are_one_record(self) -> None:
        self.assertNotIn("SYS-DOCUMENT-COMPOSITION:", self.said, "APP007 twice is not a conflict")
        self.assertIsNotNone(self.model.get("systems", "SYS-DOCUMENT-COMPOSITION"))

    def test_a_column_nothing_reads_is_said(self) -> None:
        self.assertIn("apps.csv: Notes is in neither columns nor ignore, so it was left out", self.said)

    def test_the_fixed_mapping_writes_the_held_rows_and_nothing_twice(self) -> None:
        before = {p: (self.root / p).read_bytes() for p in _model_files(self.root)}
        again = importer.import_csv(self.root, self.source, model_module.load(self.root),
                                    mapping=self.source / "fixed.yaml")
        self.assertEqual(again.held, [])
        self.assertEqual(again.imported, {"systems": 3, "interfaces": 1})
        for path, data in before.items():
            self.assertEqual((self.root / path).read_bytes(), data, "%s was written again" % path)
        model = model_module.load(self.root)
        self.assertEqual(model.get("systems", "SYS-CLAIMS-WORKBENCH")["criticality"], "Low")
        self.assertEqual(model.get("systems", "SYS-AGENT-PORTAL")["owner_org_id"], "ORG-IT")
        self.assertEqual(model.get("systems", "SYS-RATING-ENGINE")["owner_org_id"], "ORG-IT")
        self.assertTrue(any("SYS-BILLING" in line for line in again.conflicts), "still the inventory's to settle")
        report = validate.run(model, load_views(self.root / "30_VIEWS"))
        self.assertEqual([f.format() for f in report.findings
                          if f.code.split(".")[0] in ("field", "ref", "id")], [])


class TestAMappingThatCannotBeApplied(unittest.TestCase):
    """Refused whole, before anything is read or written."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="aac-map-"))
        self.addCleanup(remove_scratch, self.tmp, "aac-map-")
        (self.tmp / "apps.csv").write_text(APPS, encoding="utf-8")
        (self.tmp / "depts.csv").write_text(DEPTS, encoding="utf-8")
        (self.tmp / "links.csv").write_text(LINKS, encoding="utf-8")

    def _refused(self, text: str) -> str:
        """The refusal, which has to be the same whichever reader reads it."""
        path = self.tmp / "mapping.yaml"
        path.write_text(text, encoding="utf-8")
        said = {}
        for name, reader in _readers():
            with self.subTest(reader=name), reader:
                with self.assertRaises(inventory.MappingError) as caught:
                    inventory.apply(inventory.load_mapping(path), self.tmp, model_module.Model(self.tmp))
                said[name] = str(caught.exception)
        self.assertEqual(len(set(said.values())), 1, said)
        return next(iter(said.values()))

    def test_a_field_the_type_does_not_have(self) -> None:
        said = self._refused(MAPPING.replace("    Tier: criticality\n", "    Tier: critcality\n"))
        self.assertIn("critcality is not a field of a system", said)

    def test_a_value_mapped_to_one_the_metamodel_does_not_list(self) -> None:
        said = self._refused(MAPPING.replace('"Tier 1": High', '"Tier 1": Critical'))
        self.assertIn("'Tier 1' is mapped to 'Critical', which is not High, Medium or Low", said)

    def test_a_column_the_file_does_not_have(self) -> None:
        said = self._refused(MAPPING.replace("    Lifecycle: status\n", "    Lifecycel: status\n"))
        self.assertIn("apps.csv has no 'Lifecycel' column", said)

    def test_yes_unquoted(self) -> None:
        said = self._refused(MAPPING.replace("      Live: Active\n", "      Yes: Active\n"))
        self.assertIn("line 25: Yes is a boolean to one YAML reader and text to another; quote it", said)

    def test_a_boolean_in_any_case_and_a_number_that_comes_back_as_other_digits(self) -> None:
        said = self._refused(MAPPING.replace("      Live: Active\n", "      Live: Active\n      01: Active\n")
                             .replace("    status: Active\n", "    status: yEs\n"))
        self.assertIn("01 may be read as a number", said)
        self.assertIn("yEs is a boolean", said)

    def test_quoted_they_are_text_to_both(self) -> None:
        path = self.tmp / "mapping.yaml"
        path.write_text(MAPPING.replace("      Live: Active\n", '      "Yes": Active\n      "01": Active\n'),
                        encoding="utf-8")
        for name, reader in _readers():
            with self.subTest(reader=name), reader:
                values = inventory.load_mapping(path)["systems"].values["status"]
                self.assertEqual(values, {"yes": "Active", "01": "Active"})

    def test_the_sample_means_the_same_to_both_readers(self) -> None:
        loaded = {}
        for name, reader in _readers():
            with reader:
                loaded[name] = inventory.load_mapping(SAMPLE / "mapping.yaml")
        self.assertEqual(len({repr(v) for v in loaded.values()}), 1)

    def test_an_id_said_twice(self) -> None:
        said = self._refused(MAPPING.replace("    Application Name: name\n",
                                             "    Application Name: name\n    App ID: system_id\n"))
        self.assertIn("system_id is both a column (App ID) and an id rule", said)

    def test_every_problem_at_once(self) -> None:
        said = self._refused(MAPPING.replace("    Tier: criticality\n", "    Tier: critcality\n")
                             .replace('"Tier 1": High', '"Tier 1": Critical')
                             .replace("org_units:", "org_unitz:"))
        for words in ("critcality", "Critical", "org_unitz is not a kind of record"):
            self.assertIn(words, said)

    def test_the_command_says_so_and_writes_nothing(self) -> None:
        with Sandbox() as root:
            path = self.tmp / "mapping.yaml"
            path.write_text(MAPPING.replace('"Tier 1": High', '"Tier 1": Critical'), encoding="utf-8")
            before = _model_files(root)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = cli.main(["--root", str(root), "import", "csv", "--from", str(self.tmp), "--map", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("'Critical'", err.getvalue())
            self.assertEqual(_model_files(root), before)


class TestTheSlug(unittest.TestCase):
    def test_slugs(self) -> None:
        self.assertEqual(inventory.slug("Legacy Claims (Mainframe)"), "LEGACY-CLAIMS-MAINFRAME")
        self.assertEqual(inventory.slug("  Gestión de Pólizas "), "GESTION-DE-POLIZAS")
        self.assertEqual(inventory.slug("app001"), "APP001")
        self.assertEqual(inventory.slug("---"), "")

    def test_fold_sets_aside_case_and_spacing_only(self) -> None:
        self.assertEqual(inventory.fold("  Tier   1 "), inventory.fold("tier 1"))
        self.assertNotEqual(inventory.fold("Tier-1"), inventory.fold("Tier 1"))


class TestTheSchema(unittest.TestCase):
    """The engine ships no validator; these hold the schema to the metamodel
    by structure, and the sample to the schema with a real validator where
    one is installed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = jsonschema.import_mapping_schema()
        cls.defs = cls.schema["$defs"]

    def test_fields_and_values_are_the_metamodels(self) -> None:
        self.assertEqual(set(self.schema["properties"]) - {"description"}, set(ENTITY_TYPES))
        fields = self.defs["systems-fields"]["enum"]
        self.assertIn("criticality", fields)
        self.assertNotIn("archetype", fields, "made by a shape, never imported")
        self.assertEqual(self.defs["criticality"]["enum"], list(CRITICALITY))
        systems = self.schema["properties"]["systems"]["properties"]
        self.assertEqual(systems["values"]["properties"]["criticality"], {"$ref": "#/$defs/criticality-values"})
        self.assertEqual(systems["defaults"]["properties"]["owner_org_id"], {"$ref": "#/$defs/id"})

    def test_the_sample_names_only_what_it_allows(self) -> None:
        sample = read_data_file(SAMPLE / "mapping.yaml")
        for kind, spec in sample.items():
            self.assertIn(kind, self.schema["properties"])
            if kind == "description":
                continue
            self.assertTrue(set(spec) <= set(self.defs["entry"]["propertyNames"]["enum"]), kind)
            fields = self.defs["%s-fields" % kind]["enum"] + [ENTITY_TYPES[kind].pk]
            for column, targets in spec["columns"].items():
                for target in targets if isinstance(targets, list) else [targets]:
                    self.assertIn(target, fields, "%s %s" % (kind, column))

    def test_the_sample_validates(self) -> None:
        try:
            import jsonschema as validator  # the third-party package, not aac's
        except ImportError:
            self.skipTest("no JSON Schema validator installed")
        if not hasattr(validator, "Draft202012Validator"):
            self.skipTest("the installed validator predates draft 2020-12")
        import json

        schema = json.loads((REPO / "40_SCHEMAS" / "import_mapping.schema.json").read_text(encoding="utf-8"))
        check = validator.Draft202012Validator(schema)
        self.assertEqual([e.message for e in check.iter_errors(read_data_file(SAMPLE / "mapping.yaml"))], [])
        wrong = read_data_file(SAMPLE / "mapping.yaml")
        wrong["systems"]["values"]["criticality"]["Tier 1"] = "Critical"
        wrong["systems"]["columns"]["Tier"] = "critcality"
        self.assertEqual(len(list(check.iter_errors(wrong))), 2)

    def test_it_is_written_with_the_others(self) -> None:
        self.assertTrue((REPO / "40_SCHEMAS" / "import_mapping.schema.json").exists())


if __name__ == "__main__":
    unittest.main()
