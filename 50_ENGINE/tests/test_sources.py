"""Tests for Settings > Sources: an export brought in or held against the model.

What is checked: an upload reads as a table, a CSV in either encoding Excel
saves and a workbook's first sheet with a header row (a title above it
passed over), or the sheet asked for; a suggestion of what each column is
comes off the column names alone, and the kind it reads them for can be
chosen; the words a field needs matched are listed with their counts, a
word that is already the model's needing nothing; what a person chose is a
mapping the engine accepts, and the file it is kept as reads back as the
same mapping, an export's `Yes` and `01` quoted; the preview says what
bringing it in would write, the rows a missing word holds back and what the
checks would newly say, with nothing written; a source kept is a folder of
60_SOURCES that never lands in another source's; the mapping engine reads a
sheet of a workbook as it reads a CSV; and through the app's endpoints, an
upload is staged outside the repository, previewed, brought in and kept,
its staging folder gone after.
"""

from __future__ import annotations

import base64
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import inventory, model as model_module, sources  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402
from terrane.query import load_views  # noqa: E402
from terrane.render_excel import workbook_bytes  # noqa: E402

from _fixture import REPO, Sandbox  # noqa: E402

SAMPLE = REPO / "60_SOURCES" / "inventory"
PORTFOLIO = (SAMPLE / "application_portfolio.csv").read_bytes()

#: The words the sample's mapping matches, as a person would choose them.
WORDS = {
    "status": {"In Production": "Active", "In Development": "Planned", "Under Evaluation": "Proposed",
               "Retired - pending": "Deprecated"},
    "criticality": {"Tier 1": "High", "Tier 2": "Medium", "Tier 3": "Low"},
    "hosting": {"Data Center": "On-prem", "Vendor Hosted": "SaaS"},
}


def _portfolio_mapping(table, words=WORDS, units=True):
    suggestion = sources.suggest(table, _SHARED["model"])
    return sources.build_mapping(table, suggestion["kind"], suggestion["columns"], code=suggestion["code"],
                                 values=words, prefix=suggestion["prefix"],
                                 units_from="Owning Department" if units else None)


_SHARED: dict = {}


def setUpModule() -> None:
    sandbox = Sandbox(seed=True)
    _SHARED["sandbox"] = sandbox
    _SHARED["root"] = sandbox.__enter__()
    _SHARED["model"] = model_module.load(_SHARED["root"])
    _SHARED["views"] = load_views(_SHARED["root"] / "30_VIEWS")


def tearDownModule() -> None:
    _SHARED["sandbox"].__exit__(None, None, None)


class TestReading(unittest.TestCase):
    def test_a_csv_reads_as_its_header_and_rows(self) -> None:
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        self.assertEqual(len(table.rows), 10)
        self.assertEqual(table.header[:2], ["App ID", "Application Name"])
        self.assertEqual(table.rows[0]["Application Name"], "Policy Administration")
        self.assertIsNone(table.sheet)

    def test_a_csv_excel_saved_in_the_windows_code_page_reads(self) -> None:
        data = "Name,Owner\nCafé Ledger,Finance\n".encode("cp1252")
        table = sources.read_table("apps.csv", data)
        self.assertEqual(table.rows[0]["Name"], "Café Ledger")
        self.assertEqual(sources.utf8_csv(data).decode("utf-8").splitlines()[1], "Café Ledger,Finance")

    def test_a_workbook_reads_its_first_sheet_with_a_header_row(self) -> None:
        data = workbook_bytes([
            ("Read me", [["Exported from the portfolio tool"]]),
            ("Applications", [["Application portfolio, October"], ["App ID", "Application Name", "Lifecycle Status"],
                              ["APP001", "Policy Administration", "In Production"],
                              ["APP002", "Claims Workbench", "In Production"]]),
        ])
        table = sources.read_table("portfolio.xlsx", data)
        self.assertEqual(table.sheet, "Applications")
        self.assertEqual(table.sheets, ["Read me", "Applications"])
        self.assertEqual(table.header, ["App ID", "Application Name", "Lifecycle Status"])
        self.assertEqual([r["Application Name"] for r in table.rows], ["Policy Administration", "Claims Workbench"])
        with self.assertRaises(sources.SourceError):
            sources.read_table("portfolio.xlsx", data, "Nope")

    def test_anything_else_is_refused_by_name(self) -> None:
        for name, data in (("apps.json", b"{}"), ("apps.csv", b"just one column\nx\n")):
            with self.subTest(name=name):
                with self.assertRaises(sources.SourceError):
                    sources.read_table(name, data)

    def test_a_column_says_what_it_holds(self) -> None:
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        status = [c for c in sources.columns_of(table) if c["column"] == "Lifecycle Status"][0]
        self.assertEqual(status["distinct"], 4)
        self.assertEqual(status["filled"], 10)
        self.assertEqual(dict(status["values"])["In Production"], 7)


class TestSuggesting(unittest.TestCase):
    def test_the_portfolio_reads_as_systems(self) -> None:
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        got = sources.suggest(table, _SHARED["model"])
        self.assertEqual(got["kind"], "systems")
        self.assertEqual(got["code"], "App ID")
        self.assertEqual(got["prefix"], "SYS-")
        self.assertEqual({c: t[0] for c, t in got["columns"].items()}, {
            "Application Name": "name", "Description": "description", "Lifecycle Status": "status",
            "Business Criticality": "criticality", "Owning Department": "owner_org_id", "Hosting": "hosting",
            "Last Reviewed": "last_reviewed"})

    def test_an_integration_list_reads_as_interfaces(self) -> None:
        table = sources.read_table("integrations.csv", (SAMPLE / "integrations.csv").read_bytes())
        got = sources.suggest(table, _SHARED["model"])
        self.assertEqual(got["kind"], "interfaces")
        self.assertEqual(got["columns"]["Source Application"], ["source_system_id"])
        self.assertEqual(got["columns"]["Target Application"], ["target_system_id"])
        self.assertEqual(got["prefix"], "INT-")

    def test_a_kind_the_person_chooses_is_read_for_that_kind(self) -> None:
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        got = sources.suggest(table, _SHARED["model"], "org_units")
        self.assertEqual(got["kind"], "org_units")
        self.assertNotIn("criticality", [t for ts in got["columns"].values() for t in ts])


class TestWords(unittest.TestCase):
    def test_each_word_with_its_rows_and_the_model_word_it_already_is(self) -> None:
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        got = sources.words_needed(table, "systems", {"Hosting": ["hosting"], "Owning Department": ["owner_org_id"]},
                                   _SHARED["model"])
        hosting = got["words"][0]
        self.assertEqual(hosting["field"], "hosting")
        words = {w["word"]: (w["rows"], w["same"]) for w in hosting["words"]}
        self.assertEqual(words, {"Data Center": (4, ""), "Azure": (2, "Azure"), "AWS": (2, "AWS"),
                                 "Vendor Hosted": (2, "")})
        owner = got["refs"][0]
        self.assertEqual((owner["field"], owner["found"], len(owner["missing"])), ("owner_org_id", 0, 5))


class TestMapping(unittest.TestCase):
    def test_what_was_chosen_is_a_mapping_the_engine_takes(self) -> None:
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        data = _portfolio_mapping(table)
        maps = inventory.parse_mapping(data)
        self.assertEqual(sorted(maps), ["org_units", "systems"])
        self.assertEqual(maps["systems"].code, "App ID")
        self.assertEqual(maps["systems"].ignore, ["Business Owner", "Annual Run Cost"])
        # A word that is already the model's needs no line.
        self.assertNotIn("azure", maps["systems"].values.get("hosting", {}))

    def test_the_kept_file_reads_back_as_the_same_mapping(self) -> None:
        table = sources.read_table("apps.csv", b"Name,Status,Owner\nLedger,Yes,ORG-A\nSwitch,01,ORG-B\n")
        data = sources.build_mapping(table, "systems", {"Name": ["name"], "Status": ["status"]},
                                     values={"status": {"Yes": "Active", "01": "Planned"}}, prefix="SYS-")
        tmp = Path(tempfile.mkdtemp(prefix="terrane-map-"))
        try:
            path = tmp / "mapping.yaml"
            path.write_text(sources.render_mapping(data), encoding="utf-8")
            # The file a person can read and the command line applies; the
            # export's `Yes` and `01` are quoted, so no reader takes them for
            # a boolean or a number.
            loaded = inventory.load_mapping(path)
            self.assertEqual(loaded["systems"].values["status"], {"yes": "Active", "01": "Planned"})
            self.assertEqual(sources.choice_of(read_data_file(path))["columns"], {"Name": ["name"], "Status": ["status"]})
        finally:
            shutil.rmtree(tmp)


class TestPreview(unittest.TestCase):
    def _folder(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="terrane-src-"))
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "application_portfolio.csv").write_bytes(PORTFOLIO)
        return tmp

    def test_it_says_what_bringing_it_in_would_write_and_writes_nothing(self) -> None:
        root = _SHARED["root"]
        before = sorted(p.relative_to(root) for p in (root / "10_MODEL").rglob("*") if p.is_file())
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        got = sources.preview(_SHARED["model"], _SHARED["views"], self._folder(), _portfolio_mapping(table))
        self.assertEqual({k: len(v) for k, v in got.added.items()}, {"org_units": 5, "systems": 10})
        self.assertEqual((got.held, got.held_rows, got.conflicts), ([], 0, []))
        # The checks ran on the model with them in it: five High systems
        # with no service tier, which the sample's own mapping fills.
        tiers = [f for f in got.findings if f.code == "governance.tier"]
        self.assertEqual(len(tiers), 5)
        after = sorted(p.relative_to(root) for p in (root / "10_MODEL").rglob("*") if p.is_file())
        self.assertEqual(before, after)
        self.assertIsNone(_SHARED["model"].find("SYS-POLICY-ADMINISTRATION"))

    def test_a_word_with_no_match_holds_its_rows_back(self) -> None:
        words = {k: dict(v) for k, v in WORDS.items()}
        del words["hosting"]["Vendor Hosted"]
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        got = sources.preview(_SHARED["model"], _SHARED["views"], self._folder(), _portfolio_mapping(table, words))
        self.assertEqual(len(got.added["systems"]), 8)
        self.assertEqual(got.held_rows, 2)
        self.assertTrue(any("Vendor Hosted" in line for line in got.held), got.held)


class TestKeeping(unittest.TestCase):
    def test_a_source_is_a_folder_of_its_own(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="terrane-keep-"))
        self.addCleanup(shutil.rmtree, tmp)
        table = sources.read_table("application_portfolio.csv", PORTFOLIO)
        data = _portfolio_mapping(table)
        # A folder holding files and no note of whose they are, the shipped
        # sample's, is not written into.
        (tmp / "60_SOURCES" / "inventory").mkdir(parents=True)
        (tmp / "60_SOURCES" / "inventory" / "README.md").write_text("ours\n", encoding="utf-8")
        folder = sources.keep(tmp, "Inventory", {"application_portfolio.csv": PORTFOLIO}, data)
        self.assertEqual(folder.name, "inventory-2")
        self.assertEqual((tmp / "60_SOURCES" / "inventory" / "README.md").read_text(encoding="utf-8"), "ours\n")
        # Kept again under the same name, it is the same folder.
        self.assertEqual(sources.keep(tmp, "Inventory", {"application_portfolio.csv": PORTFOLIO}, data), folder)
        sources.note_run(folder, {"systems": 10, "org_units": 5}, 0, when="2026-10-20")
        listed = [s for s in sources.list_sources(tmp) if s["id"] == "inventory-2"][0]
        self.assertEqual((listed["name"], listed["kind"], listed["simple"]), ("Inventory", "brings in", True))
        self.assertEqual(listed["last"]["added"], {"systems": 10, "org_units": 5})
        _folder, kept = sources.mapping_of(tmp, "inventory-2")
        self.assertEqual(sources.choice_of(kept)["unitsFrom"], "Owning Department")

    def test_the_repository_lists_its_sample_and_its_cmdb_export(self) -> None:
        listed = {s["id"]: s for s in sources.list_sources(REPO)}
        self.assertEqual(listed["inventory"]["kind"], "brings in")
        self.assertFalse(listed["inventory"]["simple"])
        self.assertEqual(listed["servicenow"]["kind"], "compares")
        counts = sources.compare_counts(_SHARED["model"], REPO, listed["servicenow"])
        self.assertEqual(counts["records"], 16)


class TestWorkbooks(unittest.TestCase):
    def test_the_mapping_engine_reads_a_sheet_as_it_reads_a_csv(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="terrane-xlsx-"))
        self.addCleanup(shutil.rmtree, tmp)
        owner = sorted(r["org_unit_id"] for r in _SHARED["model"].all_of("org_units"))[0]
        rows = [line.split(",") for line in ["Application Name,Lifecycle Status,Owning Department,Business Criticality",
                                              "Ledger,In Production,%s,Tier 1" % owner]]
        (tmp / "apps.xlsx").write_bytes(workbook_bytes([("Notes", [["see the next sheet"]]), ("Apps", rows)]))
        data = {"systems": {"file": "apps.xlsx", "sheet": "Apps", "id": {"prefix": "SYS-", "from": "name"},
                            "columns": {"Application Name": "name", "Lifecycle Status": "status",
                                        "Owning Department": "owner_org_id", "Business Criticality": "criticality"},
                            "values": {"status": {"In Production": "Active"}, "criticality": {"Tier 1": "High"}}}}
        got = inventory.apply(inventory.parse_mapping(data), tmp, _SHARED["model"])
        self.assertEqual(([r["system_id"] for r in got.rows.get("systems", [])], got.held), (["SYS-LEDGER"], []))
        # The owner is found by its id, as it is from a CSV.
        self.assertEqual(got.rows["systems"][0]["owner_org_id"], owner)
        with self.assertRaises(inventory.MappingError):
            inventory.parse_mapping({"systems": dict(data["systems"], file="apps.csv")})


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestEndpoints(unittest.TestCase):
    def test_an_upload_is_staged_previewed_brought_in_and_kept(self) -> None:
        with Sandbox(seed=True) as root:
            server = _server(root)
            read = server.api_sources_read({}, {"name": "application_portfolio.csv",
                                                "data": base64.b64encode(PORTFOLIO).decode("ascii")})
            staged = server._STAGED[read["token"]]["dir"]
            # Staged outside the repository until it is brought in.
            self.assertNotIn(Path(root).resolve(), Path(staged).resolve().parents)
            choice = {"kind": read["suggestion"]["kind"], "columns": read["suggestion"]["columns"],
                      "code": read["suggestion"]["code"], "prefix": read["suggestion"]["prefix"],
                      "values": WORDS, "unitsFrom": "Owning Department"}
            words = server.api_sources_words({}, {"token": read["token"], "choice": choice})
            self.assertEqual([g["field"] for g in words["words"]], ["status", "criticality", "hosting"])
            preview = server.api_sources_preview({}, {"token": read["token"], "choice": choice})
            self.assertEqual(preview["counts"], {"org_units": 5, "systems": 10})
            self.assertIn('"Application Name": name', preview["mapping"])
            self.assertFalse((root / "10_MODEL" / "systems" / "SYS-POLICY-ADMINISTRATION.yaml").exists())
            done = server.api_sources_bring_in({}, {"token": read["token"], "choice": choice,
                                                    "keep": "Application portfolio"})
            self.assertEqual(done["imported"], {"org_units": 5, "systems": 10})
            self.assertEqual((done["source"], done["errors"]), ("application-portfolio", []))
            self.assertTrue((root / "10_MODEL" / "systems" / "SYS-POLICY-ADMINISTRATION.yaml").is_file())
            self.assertFalse(Path(staged).exists())
            self.assertNotIn(read["token"], server._STAGED)
            listed = server.api_sources({}, {})["sources"]
            kept = [s for s in listed if s["id"] == "application-portfolio"][0]
            self.assertEqual(kept["last"]["added"], {"systems": 10, "org_units": 5})
            # Brought in again from what was kept: nothing new, nothing changed.
            again = server.api_sources_preview({}, {"source": "application-portfolio"})
            self.assertEqual(again["counts"], {})
            self.assertEqual(sum(len(v) for v in again["present"].values()), 15)

    def test_the_project_keeps_credentials_out(self) -> None:
        with Sandbox() as root:
            server = _server(root)
            (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
            before = server.api_project({}, {})
            self.assertFalse(before["secretsKeptOut"])
            self.assertIn(".env", before["secretsMissing"])
            self.assertEqual(server.api_project_guard({}, {}), {"changed": True})
            self.assertTrue(server.api_project({}, {})["secretsKeptOut"])
            self.assertTrue((root / ".gitignore").read_text(encoding="utf-8").startswith("node_modules/\n"))


if __name__ == "__main__":
    unittest.main()
