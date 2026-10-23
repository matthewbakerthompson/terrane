"""Tests for the model-as-tables and coverage endpoints.

Both are read-only, so the risk is not corruption but dishonesty: a table that
quietly drops a column, or a gap report that cries wolf. A coverage report with
false positives in it gets ignored, and then it may as well not exist.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import model as model_module  # noqa: E402
from terrane.query import load_views, resolve  # noqa: E402
from terrane.schema import ENTITY_TYPES, RELATION_TYPES  # noqa: E402

from _fixture import REPO, seeded_root, setup_shared, teardown_shared  # noqa: E402


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


class TestTables(unittest.TestCase):
    server = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _server(seeded_root())
        cls.model = model_module.load(seeded_root())

    def test_the_catalog_lists_every_table_in_the_metamodel(self) -> None:
        catalog = self.server.api_table({}, None)
        self.assertEqual(
            [e["id"] for e in catalog["entities"]], sorted(ENTITY_TYPES)
        )
        self.assertEqual(
            [r["id"] for r in catalog["relations"]], sorted(RELATION_TYPES)
        )

    def test_the_catalog_counts_match_the_model(self) -> None:
        catalog = self.server.api_table({}, None)
        for entry in catalog["entities"]:
            self.assertEqual(entry["count"], len(self.model.all_of(entry["id"])), entry["id"])
        for entry in catalog["relations"]:
            self.assertEqual(
                entry["count"], len(self.model.relation_rows(entry["id"])), entry["id"]
            )

    def test_every_entity_type_renders_a_table(self) -> None:
        for type_name in ENTITY_TYPES:
            with self.subTest(type=type_name):
                table = self.server.api_table({"type": [type_name]}, None)
                self.assertEqual(table["kind"], "entity")
                self.assertEqual(table["count"], len(self.model.all_of(type_name)))
                self.assertEqual(len(table["rows"]), table["count"])

    def test_every_relation_renders_a_table(self) -> None:
        for name in RELATION_TYPES:
            with self.subTest(relation=name):
                table = self.server.api_table({"relation": [name]}, None)
                self.assertEqual(table["kind"], "relation")
                self.assertEqual(table["count"], len(self.model.relation_rows(name)))

    def test_no_field_a_record_carries_is_left_out(self) -> None:
        """A table that quietly drops a column is worse than no table: someone
        concludes the data is not there when it is."""
        for type_name in ENTITY_TYPES:
            table = self.server.api_table({"type": [type_name]}, None)
            columns = {c["name"] for c in table["columns"]}
            for record in self.model.all_of(type_name):
                for key in record:
                    if key in self.server.INTERNAL_KEYS:
                        continue
                    with self.subTest(type=type_name, field=key):
                        self.assertIn(key, columns)

    def test_undeclared_fields_are_shown_and_marked(self) -> None:
        """A field nobody declared is a typo or a convention forming. Either
        way it should be visible rather than silently dropped."""
        table = self.server.api_table({"type": ["systems"]}, None)
        declared = {f.name for f in ENTITY_TYPES["systems"].fields}
        for column in table["columns"]:
            if column["name"].startswith("_"):
                continue
            self.assertEqual(column["declared"], column["name"] in declared, column["name"])

    def test_the_filled_count_is_the_truth(self) -> None:
        table = self.server.api_table({"type": ["systems"]}, None)
        for column in table["columns"]:
            expected = sum(
                1 for row in table["rows"]
                if row.get(column["name"]) not in (None, "", [], {})
            )
            self.assertEqual(column["filled"], expected, column["name"])

    def test_every_cell_is_something_a_csv_can_hold(self) -> None:
        """Lists and mappings have to be flattened, or the download is broken
        for exactly the records that carry the most information."""
        for type_name in ENTITY_TYPES:
            for row in self.server.api_table({"type": [type_name]}, None)["rows"]:
                for key, value in row.items():
                    with self.subTest(type=type_name, field=key):
                        self.assertIsInstance(value, (str, int, float, bool, type(None)))

    def test_a_relation_row_carries_both_ends_by_name(self) -> None:
        """The ids are the record; the names are what makes it readable."""
        for name, spec in RELATION_TYPES.items():
            table = self.server.api_table({"relation": [name]}, None)
            for row in table["rows"]:
                with self.subTest(relation=name):
                    self.assertTrue(row["_left"])
                    self.assertTrue(row["_right"])
                    located = self.model.find(str(row[spec.left_column]))
                    if located:
                        self.assertEqual(
                            row["_left"],
                            located[1].get("name") or row[spec.left_column],
                        )

    def test_the_file_column_points_at_something_that_exists(self) -> None:
        root = seeded_root()
        for type_name in ENTITY_TYPES:
            for row in self.server.api_table({"type": [type_name]}, None)["rows"]:
                if not row["_file"]:
                    continue
                with self.subTest(file=row["_file"]):
                    self.assertTrue((root / row["_file"]).exists(), row["_file"])

    def test_the_primary_key_is_the_first_column(self) -> None:
        for type_name, entity_type in ENTITY_TYPES.items():
            table = self.server.api_table({"type": [type_name]}, None)
            with self.subTest(type=type_name):
                self.assertEqual(table["columns"][0]["name"], entity_type.pk)
                self.assertTrue(table["columns"][0]["pk"])

    def test_an_unknown_table_is_a_404(self) -> None:
        for query in ({"type": ["unicorns"]}, {"relation": ["system_eats_capability"]}):
            with self.subTest(query=query):
                with self.assertRaises(self.server.ApiError) as caught:
                    self.server.api_table(query, None)
                self.assertEqual(caught.exception.status, 404)


class TestCoverage(unittest.TestCase):
    server = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _server(seeded_root())
        cls.model = model_module.load(seeded_root())
        cls.payload = cls.server.api_coverage(None, None)

    def test_the_totals_match_the_model(self) -> None:
        totals = self.payload["totals"]
        self.assertEqual(
            totals["entities"], sum(len(self.model.all_of(n)) for n in ENTITY_TYPES)
        )
        self.assertEqual(
            totals["relations"],
            sum(len(self.model.relation_rows(n)) for n in RELATION_TYPES),
        )
        self.assertEqual(totals["views"], len(load_views(seeded_root() / "30_VIEWS")))

    def test_every_gap_names_something_that_exists(self) -> None:
        for gap in self.payload["gaps"]:
            for item in gap["items"]:
                with self.subTest(gap=gap["key"], id=item["id"]):
                    self.assertIsNotNone(self.model.find(item["id"]), item["id"])

    def test_no_gap_is_reported_empty(self) -> None:
        """A list of zeroes buries the findings that matter."""
        for gap in self.payload["gaps"]:
            self.assertGreater(gap["count"], 0, gap["key"])
            self.assertEqual(gap["count"], len(gap["items"]), gap["key"])

    def test_every_gap_says_why_it_matters(self) -> None:
        for gap in self.payload["gaps"]:
            with self.subTest(gap=gap["key"]):
                self.assertTrue(gap["title"].strip())
                self.assertGreater(len(gap["why"]), 40, gap["key"])

    def test_interfaces_are_not_reported_as_undrawn(self) -> None:
        """Regression: interfaces are drawn as the edges between systems, never
        as nodes, so counting nodes alone said all 35 were on no diagram."""
        undrawn = [g for g in self.payload["gaps"] if g["key"] == "undrawn.interfaces"]
        drawn_ids = set()
        for view in load_views(seeded_root() / "30_VIEWS"):
            try:
                keys = {n.key for n in resolve(self.model, view).nodes}
            except Exception:
                continue
            for record in self.model.all_of("interfaces"):
                if (str(record.get("source_system_id")) in keys
                        and str(record.get("target_system_id")) in keys):
                    drawn_ids.add(str(record["interface_id"]))
        self.assertTrue(drawn_ids, "fixture has no interface between two drawn systems")
        if undrawn:
            self.assertFalse(set(undrawn[0]["items"]) & drawn_ids)

    def test_external_actors_are_not_reported_as_unowned(self) -> None:
        """An external actor has no internal owner by definition, and flagging
        every cardholder is how a gap report gets ignored."""
        gap = [g for g in self.payload["gaps"] if g["key"] == "owner.missing.actors"]
        flagged = {i["id"] for g in gap for i in g["items"]}
        for actor in self.model.all_of("actors"):
            if str(actor.get("internal", "")).lower() == "no":
                self.assertNotIn(str(actor["actor_id"]), flagged)

    def test_flows_are_not_reported_as_undrawn(self) -> None:
        """A flow renders its own sequence diagram; it is never on a view."""
        self.assertFalse([g for g in self.payload["gaps"] if g["key"] == "undrawn.flows"])

    def test_an_unrealized_capability_is_found(self) -> None:
        realized = {
            str(r["capability_id"])
            for r in self.model.relation_rows("system_realizes_capability")
        } | {
            str(r["capability_id"])
            for r in self.model.relation_rows("product_realizes_capability")
        }
        expected = {
            str(c["capability_id"]) for c in self.model.all_of("capabilities")
        } - realized
        gap = [g for g in self.payload["gaps"] if g["key"] == "capability.unrealized"]
        found = {i["id"] for g in gap for i in g["items"]}
        self.assertEqual(found, expected)

    def test_field_coverage_counts_what_is_filled(self) -> None:
        for block in self.payload["fields"]:
            records = self.model.all_of(block["type"])
            self.assertEqual(block["count"], len(records))
            for field in block["fields"]:
                expected = sum(
                    1 for r in records if r.get(field["name"]) not in (None, "", [], {})
                )
                with self.subTest(type=block["type"], field=field["name"]):
                    self.assertEqual(field["filled"], expected)

    def test_field_coverage_skips_the_primary_key(self) -> None:
        """It is always 100% by definition, and it crowds out the rest."""
        for block in self.payload["fields"]:
            names = {f["name"] for f in block["fields"]}
            self.assertNotIn(ENTITY_TYPES[block["type"]].pk, names)

    def test_the_plural_comes_from_the_metamodel(self) -> None:
        """Deriving it from the singular label produced "capabilitys"."""
        for block in self.payload["fields"]:
            self.assertEqual(block["plural"], block["type"].replace("_", " "))


if __name__ == "__main__":
    unittest.main()
