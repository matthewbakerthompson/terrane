"""A report drawn as the table it is, on the sheet, paged for a deck."""

from __future__ import annotations

import unittest
from xml.etree import ElementTree

from terrane.draw.table import ROWS_PER_PAGE, pages, render_table_svg, table_of
from terrane.query import resolve

from _fixture import seeded_model, seeded_views


def _graph(view_id: str):
    model = seeded_model()
    view = next(v for v in seeded_views() if v.view_id == view_id)
    return resolve(model, view)


class TestTable(unittest.TestCase):
    def test_the_columns_are_the_relationships_ends_and_a_constant_one_is_said_once(self) -> None:
        columns, rows, said = table_of(_graph("change-register"))
        self.assertEqual(columns, ["From", "Relationship", "To", "Detail"])
        self.assertEqual(len(rows), 19)
        self.assertEqual(said, [])
        self.assertEqual(rows[0].cells[0][1][:3], "ACR")  # the id under the name
        columns, rows, said = table_of(_graph("platform-dependencies"))
        self.assertEqual(columns, ["From", "To"])
        self.assertEqual(said, ["Relationship, on every row: system uses tech service"])

    def test_pages_cut_the_rows_for_a_deck(self) -> None:
        graph = _graph("control-coverage")
        cut = pages(graph)
        self.assertEqual(cut[0], (1, ROWS_PER_PAGE))
        self.assertEqual(cut[-1][1], len(table_of(graph)[1]))
        self.assertEqual(pages(_graph("change-register")), [(1, 8), (9, 16), (17, 19)])

    def test_the_sheet_holds_every_row_and_a_page_says_which(self) -> None:
        graph = _graph("change-register")
        svg = render_table_svg(graph, model_name="Architecture Model")
        root = ElementTree.fromstring(svg)
        self.assertEqual(root.get("data-layout"), "table")
        rows = [g for g in root.iter("{http://www.w3.org/2000/svg}g") if g.get("class") == "row"]
        self.assertEqual(len(rows), 19)
        self.assertIn("19 rows", svg)
        self.assertIn("Change Register", svg)
        page = render_table_svg(graph, model_name="Architecture Model", rows_from=17, rows_to=19)
        root = ElementTree.fromstring(page)
        rows = [g for g in root.iter("{http://www.w3.org/2000/svg}g") if g.get("class") == "row"]
        self.assertEqual([g.get("data-row") for g in rows], ["17", "18", "19"])
        self.assertIn("rows 17–19 of 19", page)
        self.assertLess(len(page), len(svg))

    def test_the_same_report_is_the_same_bytes(self) -> None:
        graph = _graph("ownership")
        self.assertEqual(render_table_svg(graph, model_name="x"), render_table_svg(graph, model_name="x"))


if __name__ == "__main__":
    unittest.main()
