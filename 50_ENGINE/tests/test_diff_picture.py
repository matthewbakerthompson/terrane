"""What changed since a revision, as a picture: added in full, removed
dashed in red, changed with a heavy border, the rest one hop away faded."""

from __future__ import annotations

import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from terrane.diff import DiffError
from terrane.diff_picture import changes_between, changes_since, mark
from terrane.quick import LIBRARY_FOLDERS

from _fixture import REPO

SVG = "{http://www.w3.org/2000/svg}"


def _estate(name: str) -> Path:
    target = Path(tempfile.mkdtemp(prefix="aac-%s-" % name))
    for folder in ("10_MODEL", "30_VIEWS") + tuple(LIBRARY_FOLDERS):
        if (REPO / folder).is_dir():
            shutil.copytree(REPO / folder, target / folder, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def _step(after: Path) -> None:
    """A step on from the sample: a new system beside the switch, lines
    from the switch and to the ledger for it, the switch renamed, the
    credit bureau gone, and the card servicing API's line to the identity
    service on gRPC."""
    (after / "10_MODEL" / "systems" / "SYS-FRAUD-SCORE-NEW.yaml").write_text(
        "system_id: SYS-FRAUD-SCORE-NEW\nname: Fraud Scoring Service\nstatus: Planned\n"
        "togaf_layer: Application\narchitecture_domain: Application\ncompany_domain: Payments\n"
        "owner_org_id: ORG-PAYMENTS\ncriticality: High\nhosting: Cloud\n", encoding="utf-8")
    (after / "10_MODEL" / "interfaces" / "INT-AUTH-FRAUDSCORE.yaml").write_text(
        "interface_id: INT-AUTH-FRAUDSCORE\nname: Authorization Switch to Fraud Scoring\nstatus: Planned\n"
        "togaf_layer: Application\narchitecture_domain: Application\ncompany_domain: Payments\n"
        "source_system_id: SYS-AUTH-SWITCH\ntarget_system_id: SYS-FRAUD-SCORE-NEW\nowner_org_id: ORG-PAYMENTS\n"
        "protocol: gRPC\n", encoding="utf-8")
    (after / "10_MODEL" / "interfaces" / "INT-FRAUDSCORE-LEDGER.yaml").write_text(
        "interface_id: INT-FRAUDSCORE-LEDGER\nname: Fraud Scoring to Core Ledger\nstatus: Planned\n"
        "togaf_layer: Application\narchitecture_domain: Application\ncompany_domain: Payments\n"
        "source_system_id: SYS-FRAUD-SCORE-NEW\ntarget_system_id: SYS-CORE-LEDGER\nowner_org_id: ORG-PAYMENTS\n"
        "protocol: HTTPS\n", encoding="utf-8")
    switch = after / "10_MODEL" / "systems" / "SYS-AUTH-SWITCH.yaml"
    switch.write_text(switch.read_text(encoding="utf-8").replace("name: Authorization Switch",
                                                                  "name: Authorization Switch v2"), encoding="utf-8")
    (after / "10_MODEL" / "systems" / "SYS-CREDIT-BUREAU.yaml").unlink()
    line = after / "10_MODEL" / "interfaces" / "INT-CARDSVC-API-IDENTITY.yaml"
    line.write_text(line.read_text(encoding="utf-8").replace("protocol: HTTPS", "protocol: gRPC"), encoding="utf-8")


def _nodes(svg: str):
    root = ET.fromstring(svg)
    return {el.get("data-id"): el for el in root.iter(SVG + "g") if el.get("class") == "node"}


class TestChangePicture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before, cls.after = _estate("before"), _estate("after")
        _step(cls.after)
        cls.drawing = changes_between(cls.before, cls.after, since="yesterday", until="today", date="2026-10-17")

    def test_added_in_full_removed_dashed_changed_heavy_the_rest_faded(self) -> None:
        self.assertEqual(self.drawing.name, "changes")
        self.assertEqual(self.drawing.title, "What changed since yesterday")
        nodes = _nodes(self.drawing.svg)
        self.assertIn("SYS-FRAUD-SCORE-NEW", nodes)
        self.assertIn("SYS-CREDIT-BUREAU", nodes)
        self.assertIn("SYS-AUTH-SWITCH", nodes)
        self.assertIsNone(nodes["SYS-FRAUD-SCORE-NEW"].get("opacity"))
        self.assertIsNone(nodes["SYS-AUTH-SWITCH"].get("opacity"))
        removed = ET.tostring(nodes["SYS-CREDIT-BUREAU"], encoding="unicode")
        self.assertIn("stroke-dasharray", removed)
        self.assertIn("#dc2626", removed)
        changed = ET.tostring(nodes["SYS-AUTH-SWITCH"], encoding="unicode")
        self.assertIn('stroke-width="3"', changed)
        # A neighbor one hop away, drawn because the new service writes to it, is faded.
        self.assertEqual(nodes["SYS-CORE-LEDGER"].get("opacity"), "0.55")
        # The ledger is the estate's hub, and the hop stops at it: counted
        # off the rows from what was added or removed, the picture is ten
        # boxes; the view's expand clause hopping on from the ledger made
        # it sixty-three.
        self.assertLess(len(nodes), 20, sorted(nodes))
        self.assertIn("1 removed", self.drawing.svg)
        self.assertIn("Authorization Switch v2", self.drawing.svg)
        # The new line is drawn in full and the lines that did not move are
        # faded; the switch's to the ledger ends at the ledger's request
        # queue, which it goes through, as every diagram draws it.
        root = ET.fromstring(self.drawing.svg)
        edges = {el.get("data-id"): el for el in root.iter(SVG + "g") if el.get("class") == "edge"}
        new_line = [e for i, e in edges.items() if i.endswith("::SYS-AUTH-SWITCH::SYS-FRAUD-SCORE-NEW")]
        self.assertEqual(len(new_line), 1)
        self.assertIsNone(new_line[0].get("opacity"))
        old_lines = [e for i, e in edges.items() if i.endswith("::SYS-AUTH-SWITCH::OI-LEDGER-QUEUE")]
        self.assertTrue(old_lines and all(e.get("opacity") == "0.45" for e in old_lines))
        # A line that changed is heavy and not faded, and both its ends, unchanged, are boxes, faded.
        moved_line = [e for i, e in edges.items() if i.endswith("::SYS-CARDSVC-API::OI-IDENTITY-API")]
        self.assertEqual(len(moved_line), 1)
        self.assertIsNone(moved_line[0].get("opacity"))
        self.assertIn('stroke-width="3"', ET.tostring(moved_line[0], encoding="unicode"))
        self.assertEqual(nodes["SYS-IDENTITY-SVC"].get("opacity"), "0.55")
        self.assertEqual(nodes["SYS-CARDSVC-API"].get("opacity"), "0.55")

    def test_a_named_view_takes_the_same_marks(self) -> None:
        drawing = changes_between(self.before, self.after, since="yesterday", until="today",
                                  view_id="application-landscape", date="2026-10-17")
        self.assertEqual(drawing.name, "application-landscape")
        nodes = _nodes(drawing.svg)
        self.assertIn("SYS-FRAUD-SCORE-NEW", nodes)
        self.assertIn("stroke-dasharray", ET.tostring(nodes["SYS-CREDIT-BUREAU"], encoding="unicode"))
        self.assertEqual(nodes["SYS-CORE-LEDGER"].get("opacity"), "0.55")
        with self.assertRaises(DiffError):
            changes_between(self.before, self.after, view_id="product-architecture")
        with self.assertRaises(DiffError):
            changes_between(self.before, self.after, view_id="no-such-view")

    def test_nothing_changed_is_said_not_drawn(self) -> None:
        with self.assertRaises(DiffError) as caught:
            changes_between(self.before, self.before, since="a", until="b")
        self.assertIn("nothing changed", str(caught.exception))

    def test_a_revision_of_the_repository_draws(self) -> None:
        """Against the repository's own history: HEAD and the working tree
        hold the same model, so the picture is refused by name; an older
        commit draws."""
        with self.assertRaises(DiffError):
            changes_since(REPO, "HEAD")

    def test_the_command_writes_the_picture_or_says_why_not(self) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from terrane import cli

        target = Path(tempfile.mkdtemp(prefix="aac-diff-cli-")) / "change.svg"
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["--root", str(REPO), "diff", "HEAD", "HEAD", "--picture", str(target)])
        self.assertEqual(code, 2)
        self.assertIn("nothing changed", err.getvalue())
        self.assertFalse(target.exists())

    def test_the_marks_on_a_payload(self) -> None:
        from terrane.diff import Diff
        d = Diff("a", "b", [("systems", "SYS-NEW", "New")], [("systems", "SYS-OLD", "Old")],
                 [("systems", "SYS-MOVED", "Moved", []), ("interfaces", "INT-MOVED", "Moved line", [])], {},
                 {"system_reads_writes": [
                     {"system_id": "SYS-OLD", "data_asset_id": "DA-X", "operation": "Read"}]}, [], [], [], [], [], [])
        payload = {"elements": [
            {"data": {"id": "SYS-NEW"}}, {"data": {"id": "SYS-OLD"}}, {"data": {"id": "SYS-MOVED"}},
            {"data": {"id": "SYS-SAME"}}, {"data": {"id": "grp::x", "isGroup": True}},
            {"data": {"id": "e0", "source": "SYS-OLD", "target": "DA-X", "kind": "system_reads_writes"}},
            {"data": {"id": "e1", "source": "SYS-NEW", "target": "DA-X", "kind": "system_reads_writes"}},
            {"data": {"id": "e2", "source": "SYS-SAME", "target": "SYS-MOVED", "kind": "interfaces", "ref": "INT-MOVED"}},
        ]}
        mark(payload, d)
        by_id = {e["data"]["id"]: e["data"] for e in payload["elements"]}
        self.assertNotIn("faded", by_id["SYS-NEW"])
        self.assertEqual((by_id["SYS-OLD"]["dash"], by_id["SYS-OLD"]["stroke"]), ("dashed", "#dc2626"))
        self.assertEqual(by_id["SYS-MOVED"]["strokeWidth"], 3.0)
        self.assertTrue(by_id["SYS-SAME"]["faded"])
        self.assertNotIn("faded", by_id["grp::x"])
        self.assertEqual(by_id["e0"]["lineStyle"], "dashed")
        self.assertNotIn("lineStyle", by_id["e1"])
        # A line that did not move is faded; a removed one is not, so it reads.
        self.assertTrue(by_id["e1"]["faded"])
        self.assertNotIn("faded", by_id["e0"])
        # A line that changed is heavy, and reads.
        self.assertEqual(by_id["e2"]["strokeWidth"], 3.0)
        self.assertNotIn("faded", by_id["e2"])

    def test_both_ends_of_a_moved_line_are_boxes(self) -> None:
        from terrane.diff import Diff
        from terrane.diff_picture import _change_view
        from terrane.diff import Snapshot
        after = Snapshot({("interfaces", "INT-A-B"): {"source_system_id": "SYS-A", "target_system_id": "SYS-B"},
                          ("interfaces", "INT-E-F"): {"source_system_id": "SYS-E", "target_system_id": "SYS-F"}},
                         {}, {}, {}, {})
        before = Snapshot({}, {}, {}, {}, {})
        # A line added, a line changed, a row added: every end is a box.
        d = Diff("a", "b", [("interfaces", "INT-A-B", "A to B")], [], [("interfaces", "INT-E-F", "E to F", [])],
                 {"system_reads_writes": [{"system_id": "SYS-C", "data_asset_id": "DA-D", "operation": "Read"}]},
                 {}, [], [], [], [], [], [])
        view = _change_view(d, before, after, "a", "b")
        scoped = {(inc["type"], tuple(inc["where"]["id_in"])) for inc in view.scope["include"]}
        self.assertEqual(scoped, {("systems", ("SYS-A", "SYS-B", "SYS-E", "SYS-F", "SYS-C")), ("data_assets", ("DA-D",))})


if __name__ == "__main__":
    unittest.main()
