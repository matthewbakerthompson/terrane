"""The pictures of the estate as a workbook: what the slides show, as
records and pages, written beside the deck and read back as the same
pages; a register said and left out."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import terrane
from terrane.excel_import import sheets
from terrane.quick import read_any, render_sketch
from terrane.schema import ENTITY_TYPES

from _fixture import REPO, setup_shared, teardown_shared


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestShown(unittest.TestCase):
    def test_the_pictures_of_a_repository_travel_as_a_workbook_and_come_back_as_the_same_pages(self) -> None:
        asked = ["system-context", {"use": "product-architecture", "with": {"product": "PRD-CARD-SERVICING"}}]
        drawings = terrane.diagrams(str(REPO), views=asked, date="2026-10-17")
        out = Path(tempfile.mkdtemp(prefix="aac-shown-")) / "pictures.xlsx"
        drawings.excel(out)
        doc, _notes = read_any(out)
        self.assertEqual([v["view_id"] for v in doc["views"]],
                         ["system-context", "product-architecture--PRD-CARD-SERVICING"])
        # Several levels of grouping come back as the list they were.
        self.assertEqual(doc["views"][1]["group_by"], ["cloud_provider", "cloud_account", "network_zone"])
        # Every box on the pictures is a row on the sheets.
        shown = {n.id for d in drawings.values() if d.scene is not None for n in d.scene.nodes}
        on_sheets = {r[ENTITY_TYPES[t].pk] for t in ENTITY_TYPES for r in doc.get(t, [])}
        self.assertTrue(shown <= on_sheets, sorted(shown - on_sheets))
        # The flows drawn beside the views travel too, as records and their steps.
        self.assertEqual(sorted(f["flow_id"] for f in doc["flows"]), sorted(n for n in drawings if n.startswith("FLOW-")))
        self.assertIn("flow_step", doc["relations"])
        # The product travels as what its shape made, the shape itself said and left out.
        product = next(p for p in doc["products"] if p["product_id"] == "PRD-CARD-SERVICING")
        self.assertNotIn("archetype", product)
        self.assertTrue(all("archetype_instance" not in s for s in doc["systems"]))
        shaped = [n for n in drawings.notes if n.endswith("the workbook holds what the shapes made, not the shapes")]
        self.assertEqual(len(shaped), 1, drawings.notes)
        self.assertTrue(shaped[0].startswith("1 product on a shape (PRD-CARD-SERVICING)"), shaped[0])
        # What the records point at came along, so nothing dangles when the workbook is read back.
        self.assertTrue(any(n.endswith("came along, since what is shown points at them: 5 org units") or
                            "came along, since what is shown points at them" in n for n in drawings.notes), drawings.notes)
        self.assertIn("org_units", doc)
        # Read back, the pages draw the same boxes, and validate finds no error in what came back.
        again = render_sketch(doc, date="2026-10-17")
        self.assertEqual([n for n in again.notes if "ERROR" in n], [])
        self.assertEqual(sorted(again), sorted(drawings))
        for name, drawing in drawings.items():
            if drawing.scene is not None:
                self.assertEqual(sorted(n.id for n in again[name].scene.nodes),
                                 sorted(n.id for n in drawing.scene.nodes), name)

    def test_the_second_estate_goes_through_the_loop_with_its_own_kinds(self) -> None:
        from terrane.join import join_estate

        thurman = REPO / "90_EXAMPLE" / "thurman-health"
        drawings = terrane.diagrams(str(thurman), views=["system-context", "application-landscape"], date="2026-10-17")
        out = Path(tempfile.mkdtemp(prefix="aac-shown-")) / "thurman.xlsx"
        drawings.excel(out)
        # The kind column names the health system's own kinds, which the shipped catalog has not heard of.
        rows = dict(sheets(out.read_bytes()))["interfaces"]
        column = rows[0].index("kind")
        kinds_said = {row[column] for row in rows[1:] if column < len(row)}
        self.assertIn("hl7v2-feed", kinds_said)
        self.assertIn("api-call", kinds_said)
        # Read back for the estate and adopted with corrections on, the untouched workbook changes nothing.
        doc, _notes = read_any(out, root=thurman)
        result = join_estate(doc, thurman, dry_run=True, correct=True)
        self.assertEqual((result.changed, result.rows_corrected, result.added, result.rows_added), ({}, 0, {}, 0))
        # And it draws again, clean.
        again = render_sketch(doc, date="2026-10-17")
        self.assertEqual(sorted(n for n in again if not n.startswith("FLOW-")), ["application-landscape", "system-context"])
        self.assertEqual([n for n in again.notes if "ERROR" in n], [])

    def test_the_pack_writes_the_workbook_of_what_the_slides_show(self) -> None:
        from terrane.pack import build_pack

        tmp = Path(tempfile.mkdtemp(prefix="aac-shown-"))
        said: list = []
        path, slides = build_pack(REPO, tmp / "deck.pptx", ["system-context", "control-coverage"], date="2026-10-17",
                                  log=said.append, excel=tmp / "deck.xlsx")
        self.assertTrue(path.is_file() and slides > 2)
        read = dict(sheets((tmp / "deck.xlsx").read_bytes()))
        self.assertIn("systems", read)
        self.assertEqual([r[0] for r in read["views"][1:]], ["system-context"])
        self.assertTrue(any("control-coverage" in n and "not in the workbook" in n for n in said), said)


if __name__ == "__main__":
    unittest.main()
