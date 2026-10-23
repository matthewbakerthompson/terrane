"""An Excel workbook read as the spreadsheet of systems it is: the sheet
with the inventory found, the rows above its header skipped, the text out
of the shared strings, and the sketch the CSV sample gives."""

from __future__ import annotations

import io
import unittest
import zipfile

import terrane
from terrane.excel_import import ExcelError, sheets, sketch_from_excel
from terrane.inventory_import import sketch_from_inventory
from terrane.quick import check_sketch, read_any, render_sketch, sketch_from_inventory_file
from terrane.render_excel import sketch_sheets, workbook_bytes
from terrane.schema import ENTITY_TYPES

from _fixture import REPO

XLSX = REPO / "90_EXAMPLE" / "quick" / "sample-inventory.xlsx"
#: What a page says that the views sheet carries; styling and limits are the defaults either way.
VIEW_KEYS = ("view_id", "title", "kind", "layout", "group_by", "description", "scope", "edges")
CSV = REPO / "90_EXAMPLE" / "quick" / "sample-inventory.csv"


class TestSheets(unittest.TestCase):
    def test_two_sheets_with_their_cells(self) -> None:
        read = sheets(XLSX.read_bytes())
        self.assertEqual([name for name, _ in read], ["Notes", "Systems"])
        notes, systems = read[0][1], read[1][1]
        self.assertEqual(notes[0][0], "Card payments, the application inventory")
        # The title row, a blank row, then the header the CSV has.
        self.assertEqual(systems[0][0], "Application inventory, 2026")
        self.assertEqual(systems[2][:3], ["Application", "Type", "Business domain"])
        self.assertEqual(systems[3][0], "Authorization switch")

    def test_a_date_excel_kept_as_a_number_is_the_date(self) -> None:
        buffer = io.BytesIO()
        ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("xl/workbook.xml", '<workbook %s><sheets><sheet name="systems" sheetId="1"/></sheets></workbook>' % ns)
            archive.writestr("xl/styles.xml", (
                '<styleSheet %s><numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy\\-mm\\-dd"/></numFmts>'
                '<cellXfs count="4"><xf numFmtId="0"/><xf numFmtId="14"/><xf numFmtId="164"/><xf numFmtId="22"/></cellXfs>'
                '</styleSheet>') % ns)
            archive.writestr("xl/worksheets/sheet1.xml", (
                '<worksheet %s><sheetData>'
                '<row r="1"><c r="A1" t="inlineStr"><is><t>system_id</t></is></c><c r="B1" t="inlineStr"><is><t>last_reviewed</t></is></c>'
                '<c r="C1" t="inlineStr"><is><t>launch</t></is></c><c r="D1" t="inlineStr"><is><t>seen</t></is></c>'
                '<c r="E1" t="inlineStr"><is><t>count</t></is></c><c r="F1" t="inlineStr"><is><t>broken</t></is></c></row>'
                '<row r="2"><c r="A2" t="inlineStr"><is><t>SYS-A</t></is></c><c r="B2" s="1"><v>46096</v></c>'
                '<c r="C2" s="2"><v>46096.5</v></c><c r="D2" s="3"><v>46096.5</v></c><c r="E2" s="0"><v>46096</v></c>'
                '<c r="F2" t="e"><v>#N/A</v></c></row>'
                '</sheetData></worksheet>') % ns)
        rows = dict(sheets(buffer.getvalue()))["systems"]
        # A built-in date format, a custom one and a date-and-time one are dates; a plain number stays a
        # number; a formula's error is no value at all.
        self.assertEqual(rows[1], ["SYS-A", "2026-03-15", "2026-03-15", "2026-03-15 12:00", "46096", ""])

    def test_what_is_not_a_workbook_is_refused(self) -> None:
        with self.assertRaises(ExcelError):
            sheets(b"not a zip")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", "<w/>")
        with self.assertRaises(ExcelError):
            sheets(buffer.getvalue())

    def test_inline_strings_numbers_and_gaps(self) -> None:
        sheet = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                 '<row r="1"><c r="A1" t="inlineStr"><is><t>Name</t></is></c><c r="C1" t="inlineStr"><is><t>Type</t></is></c></row>'
                 '<row r="2"><c r="A2" t="inlineStr"><is><t>Ledger</t></is></c><c r="B2"><v>3.0</v></c><c r="C2" t="inlineStr"><is><t>Database</t></is></c><c r="D2" t="b"><v>1</v></c></row>'
                 '</sheetData></worksheet>')
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Only" sheetId="1"/></sheets></workbook>')
            archive.writestr("xl/worksheets/sheet1.xml", sheet)
        read = sheets(buffer.getvalue())
        self.assertEqual(read, [("Only", [["Name", "", "Type"], ["Ledger", "3", "Database", "Yes"]])])


class TestSketch(unittest.TestCase):
    def test_the_workbook_reads_as_the_csv_does(self) -> None:
        from_xlsx, notes = sketch_from_excel(XLSX.read_bytes(), name="The inventory")
        from_csv, _ = sketch_from_inventory(CSV.read_text(encoding="utf-8"), name="The inventory")
        check_sketch(from_xlsx)
        for key in ("systems", "data_assets", "actors", "capabilities", "tech_services", "processes", "interfaces"):
            self.assertEqual(from_xlsx.get(key), from_csv.get(key), key)
        self.assertEqual(from_xlsx.get("relations"), from_csv.get("relations"))
        self.assertTrue(notes[0].startswith("read "), notes[0])
        self.assertEqual(notes[1], "sheet 'Systems' of the workbook read; left alone: 'Notes'")

    def test_a_workbook_with_no_inventory_sheet_is_said(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Budget" sheetId="1"/></sheets></workbook>')
            archive.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Quarter</t></is></c><c r="B1" t="inlineStr"><is><t>Spend</t></is></c></row></sheetData></worksheet>')
        with self.assertRaises(ExcelError) as caught:
            sketch_from_excel(buffer.getvalue())
        self.assertIn("'Budget'", str(caught.exception))

    def test_the_doors_take_the_file_by_its_suffix(self) -> None:
        doc, notes = read_any(XLSX)
        self.assertIn("systems", doc)
        drawings = terrane.diagrams(str(XLSX), date="2026-10-17")
        self.assertIn("imported", drawings)
        self.assertIn("Authorization switch", drawings["imported"].svg)
        import tempfile
        from pathlib import Path
        folder = Path(tempfile.mkdtemp(prefix="aac-xlsx-"))
        target = folder / "inventory.xlsx"
        target.write_bytes(XLSX.read_bytes())
        sketch, notes = sketch_from_inventory_file(target)
        self.assertEqual(sketch.name, "inventory.yaml")
        self.assertIn("Read from inventory.xlsx by `terrane draw --from-inventory`", sketch.read_text(encoding="utf-8"))


class TestTypedWorkbook(unittest.TestCase):
    def test_a_workbook_in_the_methods_own_vocabulary_reads_as_its_records(self) -> None:
        data = workbook_bytes([
            ("Contents", [["Sheet", "Holds"], ["systems", "system"]]),
            ("systems", [["system_id", "name", "hosting", "shelf"], ["SYS-A", "A", "SaaS", "red"],
                         ["", "no id", "", ""], ["SYS-B", "B", "", ""]]),
            # Headed by its id column, whatever the sheet is called.
            ("Data", [["data_asset_id", "name"], ["DA-X", "X"]]),
            ("relations", [["relation", "from", "to", "qualifier", "value"],
                           ["system_reads_writes", "SYS-A", "DA-X", "operation", "Read"],
                           ["system_reads_writes", "SYS-B", "DA-MISSING", "operation", "Read"],
                           ["made_up", "SYS-A", "SYS-B", "", ""]]),
        ])
        doc, notes = sketch_from_excel(data, name="typed")
        check_sketch(doc)
        self.assertEqual(doc["systems"], [{"system_id": "SYS-A", "name": "A", "hosting": "SaaS"},
                                          {"system_id": "SYS-B", "name": "B"}])
        self.assertEqual(doc["data_assets"], [{"data_asset_id": "DA-X", "name": "X"}])
        self.assertEqual(doc["relations"], {"system_reads_writes": [
            {"system_id": "SYS-A", "data_asset_id": "DA-X", "operation": "Read"}]})
        self.assertTrue(notes[0].startswith("read 2 systems, 1 data assets and 1 relation row(s) from 3 sheet(s)"), notes[0])
        self.assertIn("left alone: 'Contents'", notes[0])
        self.assertIn("sheet 'systems': columns a system has no field for, left alone: 'shelf'", notes)
        self.assertIn("sheet 'systems': row 3 has no system_id; left out", notes)
        self.assertIn("sheet 'relations': 'made_up' is no relation of the method; 1 row(s) left out", notes)
        self.assertIn("sheet 'relations': 'DA-MISSING' is named by 1 row(s) and is on no sheet; left out", notes)
        view = doc["views"][0]
        self.assertEqual(view["edges"], [{"via": "system_reads_writes", "label": "operation"}])
        self.assertEqual([i["type"] for i in view["scope"]["include"]], ["systems", "data_assets"])
        self.assertNotIn("group_by", view)

    def test_a_drawing_through_the_workbook_comes_back_as_the_same_records(self) -> None:
        import json

        before, _ = read_any(REPO / "90_EXAMPLE" / "quick" / "sample.vsdx")
        after, notes = sketch_from_excel(workbook_bytes(sketch_sheets(before)), name="sample")
        check_sketch(after)

        def records(doc: dict) -> dict:
            return {t: sorted(doc[t], key=lambda r: json.dumps(r, sort_keys=True)) for t in ENTITY_TYPES if doc.get(t)}

        def relation_rows(doc: dict) -> dict:
            return {k: sorted(json.dumps(r, sort_keys=True) for r in v) for k, v in doc["relations"].items()}

        self.assertEqual(records(after), records(before))
        self.assertEqual(relation_rows(after), relation_rows(before))
        self.assertEqual([n for n in notes if "left out" in n], [])
        # The pages survive: the views sheet says what each shows and which lines.
        self.assertEqual([v["view_id"] for v in after["views"]], ["applications", "data"])
        for mine, theirs in zip(after["views"], before["views"]):
            self.assertEqual({k: mine.get(k) for k in VIEW_KEYS}, {k: theirs.get(k) for k in VIEW_KEYS}, mine["view_id"])
        self.assertNotIn("interfaces", [i["type"] for i in after["views"][0]["scope"]["include"]])
        drawings = render_sketch(after, date="2026-10-18")
        self.assertEqual(list(drawings), ["applications", "data"])
        self.assertIn("Fraud scoring", drawings["applications"].svg)
        # Not merely the same records: the same pictures, byte for byte.
        direct = render_sketch(before, date="2026-10-18")
        for view_id in drawings:
            self.assertEqual(drawings[view_id].svg, direct[view_id].svg, view_id)

    def test_a_page_by_types_and_a_shipped_view_come_back(self) -> None:
        before, _ = read_any(REPO / "90_EXAMPLE" / "quick" / "sample.mmd")
        self.assertTrue(all("where" not in i for i in before["views"][0]["scope"]["include"]))
        after, notes = sketch_from_excel(workbook_bytes(sketch_sheets(before)), name="sample")
        self.assertEqual(len(after["views"]), len(before["views"]))
        for mine, theirs in zip(after["views"], before["views"]):
            self.assertEqual({k: mine.get(k) for k in VIEW_KEYS}, {k: theirs.get(k) for k in VIEW_KEYS}, mine["view_id"])
        named = {"model": {"name": "x"}, "systems": [{"system_id": "SYS-A", "name": "A"}], "views": ["system-context"]}
        back, _ = sketch_from_excel(workbook_bytes(sketch_sheets(named)), name="x")
        self.assertEqual(back["views"], ["system-context"])

    def test_a_page_that_names_nothing_on_the_sheets_is_said(self) -> None:
        data = workbook_bytes([
            ("systems", [["system_id", "name"], ["SYS-A", "A"]]),
            ("views", [["view_id", "title", "kind", "layout", "group_by", "description", "types", "nodes", "edges"],
                       ["one", "One", "diagram", "TB", "", "", "", "SYS-A;SYS-GONE", "interfaces (protocol)"],
                       ["two", "Two", "", "", "", "", "widgets", "SYS-GONE", ""],
                       ["", "no id", "", "", "", "", "", "", ""]]),
        ])
        doc, notes = sketch_from_excel(data, name="pages")
        self.assertEqual([v["view_id"] for v in doc["views"]], ["one"])
        self.assertEqual(doc["views"][0]["scope"], {"include": [{"type": "systems", "where": {"id_in": ["SYS-A"]}}]})
        self.assertEqual(doc["views"][0]["edges"], [{"via": "interfaces", "label": "protocol"}])
        self.assertEqual(doc["views"][0]["layout"], "TB")
        self.assertIn("sheet 'views': one: on no sheet, left out: 'SYS-GONE'", notes)
        self.assertIn("sheet 'views': two: no type called 'widgets'; left out", notes)
        self.assertIn("sheet 'views': two shows nothing on the sheets; left out", notes)
        self.assertIn("sheet 'views': row 4 has no view_id and no use; left out", notes)

    def test_a_product_on_a_shape_and_one_from_parts_come_back_and_draw_the_same(self) -> None:
        for example in ("on-a-shape.yaml", "from-parts.yaml"):
            before, _ = read_any(REPO / "90_EXAMPLE" / "quick" / example)
            said: list = []
            after, _notes = sketch_from_excel(workbook_bytes(sketch_sheets(before, said)), name=example)
            self.assertEqual(said, [], example)
            # The sketch's own name, from the model sheet, not the file's.
            self.assertEqual(after["model"], before["model"], example)
            self.assertEqual(after["products"], before["products"], example)
            self.assertEqual(after.get("systems"), before.get("systems"), example)
            # The subject views come back as the shipped view they use, with what.
            self.assertEqual(after["views"], before["views"], example)
            mine, theirs = render_sketch(after, date="2026-10-18"), render_sketch(before, date="2026-10-18")
            self.assertEqual(list(mine), list(theirs), example)
            for view_id in mine:
                self.assertEqual(mine[view_id].svg, theirs[view_id].svg, "%s %s" % (example, view_id))

    def test_what_is_not_a_cell_is_said_and_the_rest_comes_back(self) -> None:
        doc = {"model": {"name": "odd"},
               "products": [{"product_id": "PRD-X", "name": "X",
                             "compose": {"provider": "AWS", "blocks": [{"block": "BLK-K8S"}],
                                         "modules": [{"module": "async-worker", "as": "slow", "with": {"runs_on": "BLK-K8S"}}]},
                             "parameters": {"owner": "ORG-1"}}]}
        said: list = []
        sheets_ = dict(sketch_sheets(doc, said))
        self.assertEqual(said, ["sheet 'products': PRD-X: compose.blocks is not a cell; left out"])
        header, row = sheets_["products"]
        self.assertEqual(dict(zip(header, row)), {
            "product_id": "PRD-X", "name": "X", "compose.provider": "AWS",
            "compose.modules": "async-worker as slow (runs_on=BLK-K8S)", "parameters.owner": "ORG-1"})
        back, _ = sketch_from_excel(workbook_bytes(sketch_sheets(doc)), name="odd")
        self.assertEqual(back["products"][0]["compose"], {
            "provider": "AWS", "modules": [{"module": "async-worker", "as": "slow", "with": {"runs_on": "BLK-K8S"}}]})
        self.assertEqual(back["products"][0]["parameters"], {"owner": "ORG-1"})

    def test_the_kind_column_fills_an_interface_of_none_and_changes_one_of_another(self) -> None:
        data = workbook_bytes([
            ("systems", [["system_id", "name"], ["SYS-A", "A"], ["SYS-B", "B"], ["SYS-C", "C"]]),
            ("interfaces", [["interface_id", "source_system_id", "target_system_id", "protocol", "integration_style", "kind"],
                            ["INT-1", "SYS-A", "SYS-B", "", "", "api-call"],
                            ["INT-2", "SYS-A", "SYS-C", "AMQP", "Event", "Request on a queue"],
                            ["INT-3", "SYS-B", "SYS-C", "HTTPS", "Request-response", "api-call"],
                            ["INT-4", "SYS-C", "SYS-A", "SFTP", "Batch", "carrier pigeon"]]),
        ])
        doc, notes = sketch_from_excel(data, name="kinds")
        by_id = {i["interface_id"]: i for i in doc["interfaces"]}
        # Neither style nor protocol: the kind's whole proposal.
        self.assertEqual((by_id["INT-1"]["integration_style"], by_id["INT-1"]["protocol"], by_id["INT-1"]["auth_method"]),
                         ("Request-response", "HTTPS", "OAuth2"))
        self.assertEqual(by_id["INT-1"]["patterns"], ["api-front-door"])
        # Another kind's fields: the defining pair changes, the rest is left.
        self.assertEqual((by_id["INT-2"]["integration_style"], by_id["INT-2"]["protocol"]), ("Request-response", "MQ"))
        self.assertNotIn("auth_method", by_id["INT-2"])
        # Fields that already say the kind: as written.
        self.assertEqual(by_id["INT-3"], {"interface_id": "INT-3", "source_system_id": "SYS-B", "target_system_id": "SYS-C",
                                          "protocol": "HTTPS", "integration_style": "Request-response"})
        # A word naming no kind is said and left.
        self.assertEqual((by_id["INT-4"]["protocol"], by_id["INT-4"]["integration_style"]), ("SFTP", "Batch"))
        self.assertTrue(any(n.startswith("sheet 'interfaces': INT-4: no connection kind called 'carrier pigeon'") for n in notes), notes)
        self.assertIn("sheet 'interfaces': 2 interface(s) given their kind from the kind column", notes)
        self.assertNotIn("kind", by_id["INT-1"])
        # The kind travels as a word: written out again, the sheet says it.
        sheets_ = dict(sketch_sheets(doc))
        header = sheets_["interfaces"][0]
        self.assertIn("kind", header)
        kinds_said = {row[0]: row[header.index("kind")] for row in sheets_["interfaces"][1:]}
        self.assertEqual((kinds_said["INT-1"], kinds_said["INT-2"], kinds_said["INT-3"], kinds_said["INT-4"]),
                         ("api-call", "queued-request", "api-call", "partner-file"))


if __name__ == "__main__":
    unittest.main()
