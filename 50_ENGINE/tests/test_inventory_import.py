"""A spreadsheet of systems read as a sketch: a row per thing by its type
column, the connections off the columns that name other rows."""

from __future__ import annotations

import unittest

import terrane
from terrane.inventory_import import InventoryError, columns_of, sketch_from_inventory
from terrane.quick import check_sketch, read_any

from _fixture import REPO

PATH = REPO / "90_EXAMPLE" / "quick" / "sample-inventory.csv"
SAMPLE = PATH.read_text(encoding="utf-8")


class TestColumns(unittest.TestCase):
    def test_headers_are_known_loosely_and_the_rest_said(self) -> None:
        found, unknown = columns_of(["Application", "Type", "Business domain", "Description", "Hosting",
                                     "Criticality", "Calls", "Reads", "Writes", "Owner", "Last reviewed"])
        self.assertEqual(found, {"name": 0, "type": 1, "domain": 2, "description": 3, "hosting": 4,
                                 "criticality": 5, "out": 6, "reads": 7, "writes": 8, "owner": 9})
        self.assertEqual(unknown, ["Last reviewed"])
        with self.assertRaises(InventoryError):
            columns_of(["Shade", "Size"])


class TestSketch(unittest.TestCase):
    def test_rows_become_records_by_their_type_words(self) -> None:
        doc, notes = sketch_from_inventory(SAMPLE, name="The inventory")
        check_sketch(doc)
        self.assertEqual([s["system_id"] for s in doc["systems"]],
                         ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING", "SYS-MERCHANT-PORTAL", "SYS-CARD-SCHEME",
                          "SYS-OLD-GATEWAY"])
        self.assertEqual([d["name"] for d in doc["data_assets"]], ["Card ledger", "Transactions"])
        self.assertEqual([a["name"] for a in doc["actors"]], ["Merchant"])
        self.assertEqual([c["name"] for c in doc["capabilities"]], ["Payment processing"])
        self.assertEqual([t["name"] for t in doc["tech_services"]], ["Kubernetes platform"])
        self.assertEqual([p["name"] for p in doc["processes"]], ["Settlement reconciliation"])
        switch = doc["systems"][0]
        self.assertEqual(switch["company_domain"], "Payments")
        self.assertIn("Hosted on On-prem.", switch["description"])
        self.assertIn("criticality: High", switch["description"])
        self.assertEqual(doc["systems"][3]["hosting"], "External")  # SaaS, so external
        # A row's connections, by name; the data it reads and writes.
        interfaces = {(i["source_system_id"], i["target_system_id"]) for i in doc["interfaces"]}
        self.assertIn(("SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING"), interfaces)
        self.assertIn(("SYS-MERCHANT-PORTAL", "SYS-AUTHORIZATION-SWITCH"), interfaces)
        reads = {(r["system_id"], r["data_asset_id"], r["operation"]) for r in doc["relations"]["system_reads_writes"]}
        self.assertIn(("SYS-AUTHORIZATION-SWITCH", "DA-TRANSACTIONS", "Write"), reads)
        self.assertIn(("SYS-FRAUD-SCORING", "DA-TRANSACTIONS", "Read"), reads)
        self.assertIn(("SYS-AUTHORIZATION-SWITCH", "DA-CARD-LEDGER", "ReadWrite"), reads)
        uses = {(r["actor_id"], r["system_id"]) for r in doc["relations"]["actor_uses_system"]}
        self.assertEqual(uses, {("ACT-MERCHANT", "SYS-AUTHORIZATION-SWITCH"), ("ACT-MERCHANT", "SYS-MERCHANT-PORTAL")})
        # What a row names that is no row, and the columns with no field here, are said.
        self.assertTrue(any("'Nowhere' is named by 1 row(s)" in n for n in notes), notes)
        self.assertTrue(any("left out: Last reviewed" in n for n in notes), notes)
        self.assertTrue(any("from the spreadsheet" in n for n in notes), notes)

    def test_tabs_and_an_id_column_read_the_same_way(self) -> None:
        text = "key\tname\tkind\tdepends on\nA1\tAlpha\tsystem\tB2\nB2\tBeta\tdatabase\t\n"
        doc, _ = sketch_from_inventory(text)
        self.assertEqual(doc["systems"][0]["system_id"], "SYS-A1")
        self.assertEqual(doc["data_assets"][0]["data_asset_id"], "DA-B2")
        self.assertEqual(doc["relations"]["system_reads_writes"][0]["data_asset_id"], "DA-B2")

    def test_the_door_takes_the_file_by_its_suffix(self) -> None:
        doc, _ = read_any(PATH)
        self.assertIn("systems", doc)
        drawings = terrane.diagrams(str(PATH), date="2026-10-17")
        self.assertIn("imported", drawings)
        self.assertIn("Authorization switch", drawings["imported"].svg)
        # The shipped library's own findings are not laid at the sketch's door.
        self.assertFalse([n for n in drawings.notes if n.startswith("validate: ERROR")], drawings.notes)


if __name__ == "__main__":
    unittest.main()
