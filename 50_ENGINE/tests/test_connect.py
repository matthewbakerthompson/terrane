"""Connecting two things from the drawing.

Drop one box on another and the app asks the server every way the metamodel
lets those two kinds of thing be joined. Nothing offered may be refused for
its types, what is recorded already must say so, and a connection the
drawing would not show must be told it would not. These hold the options,
the one-field save they use for a reference, and the whole-view save that
draws a new kind of line.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import model as model_module  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402
from terrane.schema import RELATION_TYPES  # noqa: E402

from _fixture import REPO, Sandbox, seeded_root, setup_shared, teardown_shared  # noqa: E402


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _server_for(root: Path):
    sys.path.insert(0, str(root / "50_ENGINE"))
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


def _options(server, a, b, view=None):
    query = {"from": [a], "to": [b]}
    if view:
        query["view"] = [view]
    return server.api_connect_options(query, None)


class TestTheOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _server_for(seeded_root())
        cls.model = model_module.load(seeded_root())

    def _an_interface(self):
        record = self.model.all_of("interfaces")[0]
        return record["source_system_id"], record["target_system_id"], record["interface_id"]

    def test_two_systems_may_call_each_other_either_way(self) -> None:
        source, target, interface_id = self._an_interface()
        got = _options(self.server, source, target)["options"]
        calls = [o for o in got if o["kind"] == "interface"]
        self.assertEqual({(o["from"], o["to"]) for o in calls}, {(source, target), (target, source)})
        forward = [o for o in calls if o["from"] == source][0]
        self.assertTrue(forward["exists"])
        self.assertIn(interface_id, forward["existing"])

    def test_every_relation_offered_fits_its_ends(self) -> None:
        """Nothing in the chooser can be refused for its types."""
        pairs = [
            (self.model.all_of("systems")[0]["system_id"], self.model.all_of("data_assets")[0]["data_asset_id"]),
            (self.model.all_of("systems")[0]["system_id"], self.model.all_of("tech_services")[0]["tech_service_id"]),
            (self.model.all_of("actors")[0]["actor_id"], self.model.all_of("systems")[0]["system_id"]),
        ]
        for a, b in pairs:
            with self.subTest(pair=(a, b)):
                got = _options(self.server, a, b)["options"]
                self.assertTrue(got, "something joins %s and %s" % (a, b))
                for option in got:
                    if option["kind"] != "relation":
                        continue
                    spec = RELATION_TYPES[option["relation"]]
                    self.assertEqual(self.model.find(option["from"])[0], spec.left)
                    self.assertEqual(self.model.find(option["to"])[0], spec.right)

    def test_a_qualifier_offers_the_words_already_used(self) -> None:
        rows = self.model.relation_rows("system_reads_writes")
        row = [r for r in rows if r.get("operation")][0]
        got = _options(self.server, row["system_id"], row["data_asset_id"])["options"]
        reads = [o for o in got if o.get("relation") == "system_reads_writes"][0]
        self.assertEqual(reads["qualifier"], "operation")
        self.assertIn(str(row["operation"]), reads["values"])
        self.assertTrue(reads["exists"])

    def test_a_reference_field_is_offered_and_its_current_value_shown(self) -> None:
        system = [s for s in self.model.all_of("systems") if s.get("owner_org_id")][0]
        other = [o for o in self.model.all_of("org_units") if o["org_unit_id"] != system["owner_org_id"]][0]
        got = _options(self.server, system["system_id"], other["org_unit_id"])["options"]
        owner = [o for o in got if o.get("field") == "owner_org_id"][0]
        self.assertEqual(owner["from"], system["system_id"])
        self.assertEqual(owner["current"], system["owner_org_id"])
        self.assertFalse(owner["exists"])

    def test_with_a_view_each_option_says_whether_it_would_be_drawn(self) -> None:
        source, target, _ = self._an_interface()
        got = _options(self.server, source, target, view="integration-architecture")["options"]
        self.assertTrue(all(o["drawn"] is True for o in got if o["kind"] == "interface"))
        got = _options(self.server, source, target)["options"]
        self.assertTrue(all(o["drawn"] is None for o in got))

    def test_refusals(self) -> None:
        a = self.model.all_of("systems")[0]["system_id"]
        with self.assertRaises(self.server.ApiError) as caught:
            _options(self.server, a, "SYS-NOT-THERE")
        self.assertEqual(caught.exception.status, 404)
        with self.assertRaises(self.server.ApiError):
            _options(self.server, a, a)


class TestTheWrites(unittest.TestCase):
    def setUp(self) -> None:
        box = Sandbox(seed=True)
        self.root = box.__enter__()
        self.addCleanup(box.__exit__, None, None, None)
        self.server = _server_for(self.root)

    def test_a_patch_sets_one_field_and_keeps_the_rest(self) -> None:
        model = model_module.load(self.root)
        system = [s for s in model.all_of("systems") if s.get("owner_org_id") and s.get("description")][0]
        other = [o for o in model.all_of("org_units") if o["org_unit_id"] != system["owner_org_id"]][0]
        path = Path(system["_source_file"])
        before = path.read_text(encoding="utf-8").splitlines()
        self.server.api_save(None, {"type": "systems", "id": system["system_id"], "patch": True,
                                    "values": {"owner_org_id": other["org_unit_id"]}})
        after = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(before), len(after))
        self.assertEqual([b for b, a in zip(before, after) if a != b],
                         ["owner_org_id: %s" % system["owner_org_id"]])
        self.assertEqual(model_module.load(self.root).get("systems", system["system_id"])["owner_org_id"],
                         other["org_unit_id"])

    def test_a_patch_needs_something_to_patch(self) -> None:
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_save(None, {"type": "systems", "id": "SYS-NOT-THERE", "patch": True,
                                        "values": {"name": "x"}})
        self.assertEqual(caught.exception.status, 404)

    def test_a_view_saved_from_its_data_keeps_its_comments(self) -> None:
        path = self.root / "30_VIEWS" / "system-context.view.yaml"
        before = path.read_text(encoding="utf-8")
        data = self.server.api_view({"id": ["system-context"]}, None)["data"]
        data["edges"] = list(data["edges"]) + [{"via": "system_uses_tech_service"}]
        res = self.server.api_view_compose(None, {"id": "system-context", "data": data})
        after = path.read_text(encoding="utf-8")
        self.assertIsNone(res["problem"])
        self.assertEqual(read_data_file(path)["edges"][-1], {"via": "system_uses_tech_service"})
        for line in before.splitlines():
            if line.strip().startswith("#"):
                self.assertIn(line, after)

    def test_a_view_cannot_be_renamed_through_its_data(self) -> None:
        data = self.server.api_view({"id": ["system-context"]}, None)["data"]
        data["view_id"] = "something-else"
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_view_compose(None, {"id": "system-context", "data": data})
        self.assertEqual(caught.exception.status, 409)


class TestTheComplaintWithEitherParser(unittest.TestCase):
    def test_the_complaint_itself_is_kept(self) -> None:
        """libyaml follows a position with the complaint, not an echo of the
        source line; skipping the line after every position dropped it."""
        server = _server_for(seeded_root())
        message = server._yaml_complaint(
            'while parsing a block mapping\n  in "<unicode string>", line 1, column 1\n'
            'did not find expected key\n  in "<unicode string>", line 2, column 3')
        self.assertIn("did not find expected key", message)
        self.assertIn("line 2", message)
        echoed = server._yaml_complaint(
            'while parsing a block mapping\n  in "<unicode string>", line 1, column 1:\n'
            '    view_id: x\n    ^\nexpected <block end>, but found \'<block mapping start>\'\n'
            '  in "<unicode string>", line 2, column 3:\n      : bad\n      ^')
        self.assertNotIn("view_id: x", echoed)
        self.assertIn("expected <block end>", echoed)


if __name__ == "__main__":
    unittest.main()
