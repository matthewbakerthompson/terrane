"""The estate as an Excel workbook: a contents sheet, a sheet per type
with the CSV export's columns, the relations, the same bytes twice, and
the systems sheet read back by the spreadsheet reader."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import terrane
from terrane.excel_import import sheets, sketch_from_excel
from terrane.render_excel import estate_sheets, export_excel, sheet_name, workbook_bytes
from terrane.schema import ENTITY_TYPES

from _fixture import REPO, seeded_model, setup_shared, teardown_shared


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestWorkbook(unittest.TestCase):
    def test_sheets_round_trip_through_the_reader(self) -> None:
        data = workbook_bytes([("First", [["Name", "Type"], ["Ledger", "Database"], ["", "x"]]),
                               ("Bad/Name:Here", [["a"]])])
        read = sheets(data)
        self.assertEqual([name for name, _ in read], ["First", "Bad_Name_Here"])
        self.assertEqual(read[0][1], [["Name", "Type"], ["Ledger", "Database"], ["", "x"]])
        self.assertEqual(sheet_name("x" * 40), "x" * 31)

    def test_the_same_sheets_are_the_same_bytes(self) -> None:
        rows = [("S", [["a", "b"], ["1", "2"]])]
        self.assertEqual(workbook_bytes(rows), workbook_bytes(rows))


class TestTheSameOnEveryPlatform(unittest.TestCase):
    """zipfile records the system that made each entry, 0 on Windows and 3
    elsewhere, unless the writer says: the workbook committed from Windows
    was stale on the public repository's first Linux run. Both writers say
    0, and a test can see that from any platform."""

    def test_every_entry_says_the_same_system_and_time(self) -> None:
        import io
        import zipfile

        from terrane.pptx import Deck

        workbook = workbook_bytes([("Contents", [["Sheet", "Holds"], ["a", "b"]])])
        deck = Deck("x")
        deck.slide()
        for made in (workbook, deck.to_bytes()):
            with zipfile.ZipFile(io.BytesIO(made)) as z:
                self.assertEqual({(i.create_system, i.date_time) for i in z.infolist()},
                                 {(0, (1980, 1, 1, 0, 0, 0))})


class TestEstate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.sheets = estate_sheets(cls.model)

    def test_a_contents_sheet_then_the_systems_then_every_type_then_the_relations(self) -> None:
        names = [name for name, _ in self.sheets]
        self.assertEqual(names[:2], ["Contents", "systems"])
        self.assertEqual(names[-1], "relations")
        present = [t for t in ENTITY_TYPES if self.model.all_of(t)]
        self.assertEqual(set(names[1:-1]), set(present))
        by_name = dict(self.sheets)
        systems = by_name["systems"]
        self.assertEqual(systems[0][:2], ["system_id", "name"])
        self.assertEqual(len(systems) - 1, len(self.model.all_of("systems")))
        self.assertEqual(by_name["relations"][0], ["relation", "from", "to", "qualifier", "value"])
        from terrane.schema import RELATION_TYPES
        total_rows = sum(len(self.model.relation_rows(r)) for r in RELATION_TYPES)
        self.assertEqual(len(by_name["relations"]) - 1, total_rows)
        contents = by_name["Contents"]
        self.assertEqual(contents[0], ["Sheet", "Holds", "Rows"])
        self.assertIn(["systems", "system", str(len(systems) - 1)], contents)

    def test_the_interfaces_sheet_says_each_connections_kind(self) -> None:
        from terrane.connections import kind_of, load_connections

        sheet = dict(self.sheets)["interfaces"]
        self.assertEqual(sheet[0][-1], "kind")
        kinds = load_connections(self.model.root)
        said = {row[0]: row[-1] for row in sheet[1:]}
        for interface in self.model.all_of("interfaces"):
            self.assertEqual(said[interface["interface_id"]], kind_of(interface, kinds) or "", interface["interface_id"])
        self.assertGreater(sum(1 for k in said.values() if k), len(said) // 2)

    def test_the_workbook_reads_back_as_the_inventory_and_opens_the_same_twice(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-xlsx-")) / "estate.xlsx"
        path = export_excel(self.model, out)
        first = path.read_bytes()
        read = sheets(first)
        self.assertEqual(read[0][0], "Contents")
        doc, notes = sketch_from_excel(first, name="back")
        # Every sheet but the contents page is in the method's own vocabulary, so the
        # whole estate comes back: every system by id, every relation row.
        self.assertTrue(notes[0].endswith("; left alone: 'Contents'"), notes[0])
        ids = {s["system_id"] for s in doc["systems"]}
        self.assertEqual(ids, set(self.model.entities["systems"]))
        from terrane.schema import RELATION_TYPES as _RELATIONS
        self.assertEqual(sum(len(rows) for rows in doc["relations"].values()),
                         sum(len(self.model.relation_rows(r)) for r in _RELATIONS))
        self.assertEqual(export_excel(self.model, out).read_bytes(), first)

    def test_the_door(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-xlsx-")) / "e.xlsx"
        path = terrane.export_excel(REPO, out)
        self.assertTrue(path.is_file())
        self.assertGreater(len(sheets(path.read_bytes())), 10)


class TestSketchWorkbook(unittest.TestCase):
    def test_a_sketch_becomes_sheets_of_its_own_records(self) -> None:
        from terrane.render_excel import sketch_sheets
        doc = {"model": {"name": "Two boxes"},
               "systems": [{"system_id": "SYS-B", "name": "B", "hosting": "SaaS"}, {"system_id": "SYS-A", "name": "A"}],
               "interfaces": [{"interface_id": "INT-1", "source_system_id": "SYS-A", "target_system_id": "SYS-B", "protocol": "HTTPS"}],
               "relations": {"system_reads_writes": [{"system_id": "SYS-A", "data_asset_id": "DA-X", "operation": "Read"}]},
               "views": ["system-context"]}
        sheets_ = dict(sketch_sheets(doc))
        self.assertEqual(list(dict(sketch_sheets(doc))), ["Contents", "model", "systems", "interfaces", "relations", "views"])
        self.assertEqual(sheets_["model"], [["key", "value"], ["name", "Two boxes"]])
        # A view named by its id alone is a shipped view; the row says so by saying nothing else.
        self.assertEqual(sheets_["views"][1], ["system-context"] + [""] * 9)
        # The id first, then every key any record has, the records sorted by id.
        self.assertEqual(sheets_["systems"], [["system_id", "name", "hosting"], ["SYS-A", "A", ""], ["SYS-B", "B", "SaaS"]])
        self.assertEqual(sheets_["relations"][1], ["system_reads_writes", "SYS-A", "DA-X", "operation", "Read"])
        self.assertIn("what the drawing said", sheets_["Contents"][1][1])

    def test_the_visio_sample_in_and_an_inventory_out(self) -> None:
        drawings = terrane.diagrams(str(REPO / "90_EXAMPLE" / "quick" / "sample.vsdx"), date="2026-10-17")
        out = Path(tempfile.mkdtemp(prefix="aac-xlsx-")) / "visio.xlsx"
        drawings.excel(out)
        read = dict(sheets(out.read_bytes()))
        self.assertEqual(read["systems"][0][:2], ["system_id", "name"])
        self.assertEqual(sorted(r[0] for r in read["systems"][1:]), ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING"])
        self.assertEqual(sorted(r[0] for r in read["data_assets"][1:]), ["DA-CARD-LEDGER", "DA-REPORTING-MART"])
        # The placeholders the door filled in to draw it are not here.
        self.assertNotIn("org_units", read)
        # The pictures of a repository have no sketch; what they show is the workbook.
        terrane.diagrams(str(REPO), views=["system-context"], date="2026-10-17").excel(out)
        read = dict(sheets(out.read_bytes()))
        self.assertEqual([r[0] for r in read["views"][1:]], ["system-context"])
        self.assertIn("systems", read)

    def test_the_command_writes_the_workbook_beside_the_pictures(self) -> None:
        import io
        from contextlib import redirect_stdout

        from terrane import cli

        folder = Path(tempfile.mkdtemp(prefix="aac-xlsx-"))
        source = folder / "sample.vsdx"
        source.write_bytes((REPO / "90_EXAMPLE" / "quick" / "sample.vsdx").read_bytes())
        with redirect_stdout(io.StringIO()):
            code = cli.main(["draw", str(source), "--excel", "--date", "2026-10-17"])
        self.assertEqual(code, 0)
        self.assertTrue((folder / "sample.xlsx").is_file())


if __name__ == "__main__":
    unittest.main()
