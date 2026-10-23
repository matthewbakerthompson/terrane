"""What changed between two revisions, in the model's own terms."""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli, diff as diff_module  # noqa: E402
from terrane.diff import Snapshot, as_dict, diff, format_markdown  # noqa: E402

from _fixture import REPO  # noqa: E402


def _snapshot(entities=None, relations=None, views=None, shapes=None, parts=None, kinds=None) -> Snapshot:
    return Snapshot(entities or {}, relations or {}, views or {}, shapes or {}, parts or {}, kinds or {})


class TestTheDiffItself(unittest.TestCase):
    """Against snapshots built by hand, so each kind of change is one case."""

    def test_an_entity_added_removed_and_changed(self) -> None:
        before = _snapshot(entities={
            ("systems", "SYS-A"): {"system_id": "SYS-A", "name": "A", "status": "Planned"},
            ("systems", "SYS-B"): {"system_id": "SYS-B", "name": "B"},
        })
        after = _snapshot(entities={
            ("systems", "SYS-A"): {"system_id": "SYS-A", "name": "A", "status": "Active", "tier": "1"},
            ("systems", "SYS-C"): {"system_id": "SYS-C", "name": "C"},
        })
        d = diff(before, after, "v1", "v2")
        self.assertEqual(d.added, [("systems", "SYS-C", "C")])
        self.assertEqual(d.removed, [("systems", "SYS-B", "B")])
        self.assertEqual(len(d.changed), 1)
        _t, _i, _n, changes = d.changed[0]
        self.assertEqual([(c.field, c.before, c.after) for c in changes],
                         [("status", "Planned", "Active"), ("tier", "", "1")])
        self.assertFalse(d.empty)

    def test_a_connections_kind_is_said_in_the_librarys_words(self) -> None:
        # The reviewer changed one connection's kind by one word, and the
        # change log said two fields: the kind comes first, above them.
        line = {"interface_id": "INT-X", "name": "X", "protocol": "MQ", "integration_style": "Request-response"}
        moved = dict(line, protocol="HTTPS", integration_style="Batch")
        before = _snapshot(entities={("interfaces", "INT-X"): line}, kinds={"INT-X": "queued-request"})
        after = _snapshot(entities={("interfaces", "INT-X"): moved}, kinds={"INT-X": "scheduled-pull"})
        _t, _i, _n, changes = diff(before, after, "v1", "v2").changed[0]
        self.assertEqual([(c.field, c.before, c.after) for c in changes],
                         [("kind", "queued-request", "scheduled-pull"), ("integration_style", "Request-response", "Batch"),
                          ("protocol", "MQ", "HTTPS")])
        self.assertIn("`kind` queued-request → scheduled-pull", format_markdown(diff(before, after, "v1", "v2")))
        # The library moved under a connection whose own fields did not: that is a change too, the one line.
        same = _snapshot(entities={("interfaces", "INT-X"): line}, kinds={"INT-X": "queued-request"})
        renamed = _snapshot(entities={("interfaces", "INT-X"): line}, kinds={})
        _t, _i, _n, changes = diff(same, renamed).changed[0]
        self.assertEqual([(c.field, c.before, c.after) for c in changes], [("kind", "queued-request", "")])
        # A connection of no kind, before and after, says nothing of kinds.
        self.assertEqual(diff(_snapshot(entities={("interfaces", "INT-X"): line}),
                              _snapshot(entities={("interfaces", "INT-X"): line})).changed, [])
        # The repository's own snapshot carries the kinds its library says.
        snap = diff_module.snapshot(REPO)
        self.assertEqual(snap.kinds.get("INT-AUTH-LEDGER"), "queued-request")
        self.assertTrue(len(snap.kinds) > 100, len(snap.kinds))

    def test_relationship_rows_views_and_library(self) -> None:
        before = _snapshot(
            relations={"product_includes_system": [(("product_id", "P"), ("system_id", "S1"))]},
            views={"a": ("A", "diagram"), "gone": ("Gone", "map")},
            shapes={"shape": "3.0.0"}, parts={"old": "Old"},
        )
        after = _snapshot(
            relations={"product_includes_system": [(("product_id", "P"), ("system_id", "S1")),
                                                   (("product_id", "P"), ("system_id", "S2"))]},
            views={"a": ("A", "timeline"), "new": ("New", "report")},
            shapes={"shape": "3.1.0"}, parts={"new": "New"},
        )
        d = diff(before, after, "v1", "v2")
        self.assertEqual(d.relations_added, {"product_includes_system": [{"product_id": "P", "system_id": "S2"}]})
        self.assertEqual(d.relations_removed, {})
        self.assertEqual(d.views_added, [("new", "New")])
        self.assertEqual(d.views_removed, [("gone", "Gone")])
        self.assertEqual([(v, [(c.field, c.before, c.after) for c in cs]) for v, _t, cs in d.views_changed],
                         [("a", [("kind", "diagram", "timeline")])])
        self.assertEqual(d.shapes_changed, [("shape", "3.0.0", "3.1.0")])
        self.assertEqual((d.parts_added, d.parts_removed), (["new"], ["old"]))

    def test_the_change_as_a_workbook(self) -> None:
        from terrane.excel_import import sheets
        from terrane.render_excel import change_sheets, workbook_bytes

        before = _snapshot(entities={("systems", "SYS-A"): {"system_id": "SYS-A", "name": "A", "status": "Planned"},
                                     ("systems", "SYS-B"): {"system_id": "SYS-B", "name": "B"}},
                           relations={"system_reads_writes": [(("system_id", "SYS-A"), ("data_asset_id", "DA-X"))]},
                           views={"gone": ("Gone", "map")}, shapes={"shape": "3.0.0"})
        after = _snapshot(entities={("systems", "SYS-A"): {"system_id": "SYS-A", "name": "A", "status": "Active"},
                                    ("systems", "SYS-C"): {"system_id": "SYS-C", "name": "C"}},
                          relations={}, views={}, shapes={"shape": "3.1.0"}, parts={"new": "New"})
        d = diff(before, after, "v1", "v2")
        book = dict(sheets(workbook_bytes(change_sheets(d))))
        self.assertEqual(list(book), ["Contents", "added", "removed", "changed", "relations", "views", "library"])
        self.assertEqual(book["added"][1], ["systems", "SYS-C", "C"])
        self.assertEqual(book["removed"][1], ["systems", "SYS-B", "B"])
        self.assertEqual(book["changed"][1], ["systems", "SYS-A", "A", "status", "Planned", "Active"])
        self.assertEqual(book["relations"][1], ["removed", "system_reads_writes", "SYS-A", "DA-X", "operation"])
        self.assertEqual(book["views"][1], ["removed", "gone", "Gone"])
        self.assertEqual(book["library"][1:], [["changed", "shape", "shape", "3.0.0", "3.1.0"], ["added", "part", "new"]])
        # Nothing changed: a contents page that says so, and no other sheet.
        empty = dict(sheets(workbook_bytes(change_sheets(diff(before, before, "v1", "v1")))))
        self.assertEqual(list(empty), ["Contents"])
        self.assertIn("nothing changed", empty["Contents"][-1][1])

    def test_the_change_as_a_workbook_from_the_repository_and_the_command(self) -> None:
        import tempfile

        import terrane
        from terrane.excel_import import sheets

        out = Path(tempfile.mkdtemp(prefix="aac-diff-")) / "change.xlsx"
        # HEAD, not HEAD~1: the public repository starts as one commit, and
        # CI checks out one commit deep, so neither has a parent to compare.
        path = terrane.export_changes(REPO, "HEAD", out)
        book = dict(sheets(path.read_bytes()))
        self.assertEqual(book["Contents"][0], ["Sheet", "Holds", "Rows"])
        self.assertIn("HEAD", book["Contents"][1][1])
        with redirect_stdout(io.StringIO()) as printed:
            code = cli.main(["--root", str(REPO), "diff", "HEAD", "--excel", str(out)])
        self.assertEqual(code, 0)
        self.assertIn("what changed from HEAD", printed.getvalue())

    def test_the_page_and_the_payload_say_the_same(self) -> None:
        before = _snapshot(entities={("systems", "SYS-A"): {"system_id": "SYS-A", "name": "A", "status": "Planned"}})
        after = _snapshot(entities={("systems", "SYS-A"): {"system_id": "SYS-A", "name": "A", "status": "Active"}})
        d = diff(before, after, "v1", "the working tree")
        page = format_markdown(d)
        self.assertIn("# What changed since v1", page)
        self.assertIn("### systems — 1 changed", page)
        self.assertIn("- A (`SYS-A`): `status` Planned → Active", page)
        payload = as_dict(d)
        self.assertEqual(payload["totals"]["changed"], 1)
        self.assertEqual(payload["changed"][0]["changes"], [{"field": "status", "before": "Planned", "after": "Active"}])

    def test_nothing_changed_says_so(self) -> None:
        s = _snapshot(entities={("systems", "SYS-A"): {"system_id": "SYS-A", "name": "A"}})
        d = diff(s, s, "v1", "v1")
        self.assertTrue(d.empty)
        self.assertIn("Nothing.", format_markdown(d))


class TestAgainstGit(unittest.TestCase):
    """The pipeline end to end: export a revision, load it with the engine,
    compare. HEAD against HEAD holds the same architecture whatever HEAD is,
    which is the one thing this can assert without depending on history."""

    def test_a_revision_exports_and_loads(self) -> None:
        root = diff_module.export_revision(REPO, "HEAD")
        self.assertTrue((root / "10_MODEL" / "model.yaml").exists())
        snap = diff_module.snapshot(root)
        self.assertTrue(any(t == "systems" for t, _i in snap.entities))
        self.assertIn("system-context", snap.views)

    def test_an_estate_in_a_subfolder_exports_with_the_library_it_names(self) -> None:
        # The second estate names the repository's library two folders up
        # and its own beside it; the export of its own folders alone did
        # not load, and HEAD against the working tree was an error.
        second = REPO / "90_EXAMPLE" / "thurman-health"
        root = diff_module.export_revision(second, "HEAD")
        self.assertEqual(root.name, "thurman-health")
        self.assertTrue((root / "10_MODEL" / "model.yaml").is_file())
        self.assertTrue((root.parent.parent / "24_CONNECTIONS").is_dir())
        snap = diff_module.snapshot(root)
        lines = {i for t, i in snap.entities if t == "interfaces"}
        self.assertTrue(lines)
        # Every interface of a kind, by the repository's kinds and Thurman's own.
        self.assertEqual(set(snap.kinds), lines)
        self.assertTrue(diff_module.between(second, "HEAD").empty)

    def test_head_against_head_is_empty(self) -> None:
        d = diff_module.between(REPO, "HEAD", "HEAD")
        self.assertTrue(d.empty, format_markdown(d))

    def test_an_unknown_revision_is_an_error_not_a_guess(self) -> None:
        with self.assertRaises(diff_module.DiffError):
            diff_module.export_revision(REPO, "no-such-revision-anywhere")

    def test_the_command_prints_the_page(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["--root", str(REPO), "diff", "HEAD", "HEAD"])
        self.assertEqual(code, 0)
        self.assertIn("Nothing.", out.getvalue())


if __name__ == "__main__":
    unittest.main()
