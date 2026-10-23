"""Tests for what each diagram needs from the records (terrane.needs), and for
setting one field on many records at once (terrane.records.set_many).

What is checked: a view that selects by a field counts the records left off
for want of it, and only where a blank is a gap (a field every record must
have, or `exists: true`), not where it is an answer (a SaaS system with no
account); a grouped field counts the drawn records outside the boxes, and a
cloud placement is not asked of a record on no cloud; a line along a
reference field counts the records without one, and a hierarchy's top is not
a gap; a view over a type the estate has none of still says what it reads;
a view is empty, thin or full by what it draws; a subject view is counted
once it is bound and not before; the one list merges the views and counts a
missing relation from the model; the values offered are the lanes, the
field's list or the records a reference names; and setting a field on many
records changes each where it lives, a shared file once with its other lines
as they were, a harvested record moved into a file of its own, and a record
a shape made or an import rewrites refused with the reason -- all planned,
nothing written.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import __version__, needs, records  # noqa: E402
from terrane.estate import init_estate  # noqa: E402
from terrane.model import load  # noqa: E402
from terrane.query import bind, parse_view  # noqa: E402

PREFIX = "aac-needs-"

UNITS = """\
- org_unit_id: ORG-PAY
  name: Payments
  status: Active
- org_unit_id: ORG-CARDS
  name: Cards
  status: Active
"""

#: Five systems as a portfolio export leaves them: names, owners and a
#: lifecycle, two with a network zone, one retired, one bought as SaaS.
SYSTEMS = {
    "SYS-GATEWAY": "name: Payments Gateway\nstatus: Active\nowner_org_id: ORG-PAY\ncriticality: High\n"
                   "network_zone: Edge\nhosting: AWS\ncloud_provider: AWS\ncloud_account: prod-pay\n",
    "SYS-LEDGER": "name: Card Ledger\nstatus: Active\nowner_org_id: ORG-CARDS\ncriticality: High\n"
                  "network_zone: Private-Data\nhosting: On-prem\ncloud_provider: On-prem\n",
    "SYS-PORTAL": "name: Card Portal\nstatus: Planned\nowner_org_id: ORG-CARDS\ncriticality: Medium\n"
                  "hosting: Azure\ncloud_provider: Azure\n",
    "SYS-OLD": "name: Old Switch\nstatus: Retired\nowner_org_id: ORG-PAY\ncriticality: Low\n",
    "SYS-CRM": "name: Sales CRM\nstatus: Active\nowner_org_id: ORG-CARDS\ncriticality: Low\n"
               "hosting: SaaS\ncloud_provider: SaaS\n",
}

TIERED = """\
view_id: tiers
title: Tiers
kind: diagram
group_by: network_zone
lanes: [Edge, Public, Private-App, Private-Data, Shared-Services, On-prem]
scope:
  include:
    - type: systems
      where:
        status: [Active, Planned]
        network_zone: {exists: true}
edges:
  - via: interfaces
style:
  color_by: criticality
"""


def view(text: str):
    from terrane.loader import parse_data_text

    return parse_view(parse_data_text(text, "the view"))


class _Estate(unittest.TestCase):
    """An estate of its own in a temporary folder, the records written as
    a person would."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix=PREFIX))
        init_estate(self.root, "Needs", __version__)
        model_dir = self.root / "10_MODEL"
        (model_dir / "org_units").mkdir(parents=True)
        (model_dir / "org_units" / "units.yaml").write_text(UNITS, encoding="utf-8")
        (model_dir / "systems").mkdir()
        for entity_id, body in SYSTEMS.items():
            (model_dir / "systems" / (entity_id + ".yaml")).write_text(
                "system_id: %s\n%s" % (entity_id, body), encoding="utf-8")

    def tearDown(self) -> None:
        # Exactly the folder mkdtemp made, and nothing worked out from it.
        self.assertEqual(self.root.parent, Path(tempfile.gettempdir()))
        self.assertTrue(self.root.name.startswith(PREFIX))
        shutil.rmtree(self.root)

    def model(self):
        return load(self.root)

    def need(self, result, type_name: str, field: str):
        found = [n for n in result.needs if n.type == type_name and n.field == field]
        self.assertEqual(len(found), 1, "%s.%s in %s" % (type_name, field, [(n.type, n.field) for n in result.needs]))
        return found[0]


class TestWhatAViewReads(_Estate):
    def test_a_selecting_field_counts_what_it_leaves_off(self) -> None:
        result = needs.needs_of(self.model(), view(TIERED))
        self.assertEqual(result.drawn, 2)
        # The portal and the CRM are Active or Planned with no zone; the
        # retired switch is left off on purpose and is not counted.
        self.assertEqual(result.kept_off, ("SYS-CRM", "SYS-PORTAL"))
        zone = self.need(result, "systems", "network_zone")
        self.assertEqual(zone.roles, ("selects", "groups"))
        self.assertEqual((zone.asked, zone.lacking), (4, ("SYS-CRM", "SYS-PORTAL")))
        self.assertEqual(dict(zone.by_role), {"selects": 2, "groups": 0})
        self.assertTrue(zone.settable)
        # The lanes are what it takes, in their order.
        self.assertEqual([v for v, _ in zone.values][:2], ["Edge", "Public"])
        self.assertEqual(self.need(result, "systems", "interfaces").kind, "relation")
        self.assertEqual(self.need(result, "systems", "criticality").roles, ("shades",))
        # As many left off as drawn, and no lines between those drawn.
        self.assertEqual(result.state, "thin")

    def test_a_blank_that_is_an_answer_is_not_counted(self) -> None:
        text = TIERED.replace("        network_zone: {exists: true}\n", "        cloud_account: [prod-pay]\n")
        result = needs.needs_of(self.model(), view(text))
        self.assertEqual(result.kept_off, ())
        self.assertFalse([n for n in result.needs if n.field == "cloud_account" and "selects" in n.roles])

    def test_a_box_field_counts_the_drawn_outside_it_and_asks_a_cloud_placement_of_a_cloud(self) -> None:
        text = """\
view_id: places
title: Where
kind: map
group_by: [cloud_provider, region]
scope:
  include:
    - type: systems
      where:
        status: [Active, Planned]
"""
        result = needs.needs_of(self.model(), view(text))
        self.assertEqual(result.drawn, 4)
        region = self.need(result, "systems", "region")
        # The on-premise ledger and the SaaS CRM hold no region by nature.
        self.assertEqual((region.asked, region.lacking), (2, ("SYS-GATEWAY", "SYS-PORTAL")))
        self.assertEqual(self.need(result, "systems", "cloud_provider").lacking, ())

    def test_a_line_along_a_reference_counts_the_records_without_one(self) -> None:
        (self.root / "10_MODEL" / "systems" / "SYS-CRM.yaml").write_text(
            "system_id: SYS-CRM\nname: Sales CRM\nstatus: Active\ncriticality: Low\n", encoding="utf-8")
        text = """\
view_id: owners
title: Owners
kind: report
scope:
  include:
    - type: org_units
    - type: systems
      where:
        status: [Active, Planned]
edges:
  - via: owner
"""
        result = needs.needs_of(self.model(), view(text))
        owner = self.need(result, "systems", "owner_org_id")
        self.assertEqual((owner.roles, owner.lacking), (("lines",), ("SYS-CRM",)))
        self.assertEqual([v for v, _ in owner.values], ["ORG-CARDS", "ORG-PAY"])
        self.assertEqual([label for _, label in owner.values], ["Cards", "Payments"])

    def test_a_hierarchy_has_a_top_and_it_is_not_a_gap(self) -> None:
        text = """\
view_id: tree
title: Tree
scope:
  include:
    - type: capabilities
edges:
  - via: parent_capability_id
"""
        self.assertFalse([n for n in needs.needs_of(self.model(), view(text)).needs
                          if n.field == "parent_capability_id"])

    def test_a_view_of_a_type_the_estate_has_none_of_says_what_it_reads(self) -> None:
        network = Path(__file__).resolve().parents[2] / "30_VIEWS" / "network-topology.view.yaml"
        result = needs.needs_of(self.model(), view(network.read_text(encoding="utf-8")))
        self.assertEqual((result.state, result.drawn, result.problem), ("empty", 0, ""))
        said = [(n.field, n.kind, n.roles, n.asked) for n in result.needs]
        self.assertIn(("tags", "tag", ("selects",), 0), said)
        self.assertIn(("availability_zone", "field", ("groups",), 0), said)
        self.assertEqual(self.need(result, "tech_services", "tags").values, (("network-fabric", "network-fabric"),))


class TestStates(_Estate):
    def test_most_outside_the_outer_boxes_is_thin(self) -> None:
        text = """\
view_id: domains
title: Domains
kind: map
group_by: company_domain
scope:
  include:
    - type: systems
"""
        self.assertEqual(needs.needs_of(self.model(), view(text)).state, "thin")
        for entity_id in ("SYS-GATEWAY", "SYS-LEDGER", "SYS-PORTAL"):
            path = self.root / "10_MODEL" / "systems" / (entity_id + ".yaml")
            path.write_text(path.read_text(encoding="utf-8") + "company_domain: Payments\n", encoding="utf-8")
        self.assertEqual(needs.needs_of(self.model(), view(text)).state, "full")

    def test_more_left_off_than_drawn_is_thin_and_none_drawn_is_empty(self) -> None:
        for entity_id in ("SYS-GATEWAY",):
            path = self.root / "10_MODEL" / "systems" / (entity_id + ".yaml")
            path.write_text(path.read_text(encoding="utf-8").replace("network_zone: Edge\n", ""), encoding="utf-8")
        self.assertEqual(needs.needs_of(self.model(), view(TIERED)).state, "thin")
        path = self.root / "10_MODEL" / "systems" / "SYS-LEDGER.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("network_zone: Private-Data\n", ""), encoding="utf-8")
        result = needs.needs_of(self.model(), view(TIERED))
        self.assertEqual((result.state, result.drawn, len(result.kept_off)), ("empty", 0, 4))

    def test_a_diagram_with_no_lines_is_thin(self) -> None:
        text = TIERED.replace("network_zone: {exists: true}", "criticality: [High]").replace("kind: diagram", "kind: diagram")
        self.assertEqual(needs.needs_of(self.model(), view(text)).state, "thin")
        self.assertEqual(needs.needs_of(self.model(), view(text.replace("kind: diagram", "kind: map"))).state, "full")

    def test_a_subject_view_is_counted_once_it_is_bound(self) -> None:
        text = """\
view_id: one
title: "{system}"
kind: diagram
parameters:
  - name: system
    type: systems
scope:
  include:
    - type: systems
      where:
        id_in: ["{system}"]
  expand:
    - relation: interfaces
      types: [systems]
edges:
  - via: interfaces
"""
        model = self.model()
        unbound = needs.needs_of(model, view(text))
        self.assertEqual((unbound.state, unbound.needs), ("subject", []))
        bound = needs.needs_of(model, bind(view(text), {"system": "SYS-LEDGER"}, model), subject="SYS-LEDGER")
        self.assertEqual((bound.drawn, bound.state, bound.subject), (1, "thin", "SYS-LEDGER"))
        self.assertEqual(self.need(bound, "systems", "interfaces").lacking, ("SYS-LEDGER",))


class TestTheOneList(_Estate):
    def test_views_merge_and_a_relation_is_lacking_when_no_row_has_it(self) -> None:
        domains = view("view_id: domains\ntitle: Domains\nkind: map\ngroup_by: company_domain\n"
                       "scope:\n  include:\n    - type: systems\n      where:\n        status: [Active]\n")
        model = self.model()
        results = needs.estate_needs(model, [view(TIERED), domains])
        listed = needs.by_field(model, results, [view(TIERED), domains])
        rows = {(n.type, n.field): n for n in listed}
        self.assertEqual(rows[("systems", "network_zone")].lacking, ("SYS-CRM", "SYS-PORTAL"))
        self.assertEqual(rows[("systems", "company_domain")].views[0][:2], ("domains", "Domains"))
        self.assertEqual(rows[("systems", "interfaces")].lacking, ("SYS-GATEWAY", "SYS-LEDGER"))
        # Fields first, the most lacking first.
        self.assertEqual(listed[0].kind, "field")
        self.assertEqual(needs.states(results), {"full": 0, "thin": 2, "empty": 0, "subject": 0})


class TestSetOnMany(_Estate):
    def test_each_record_is_changed_where_it_lives_and_nothing_is_written(self) -> None:
        shared = self.root / "10_MODEL" / "systems" / "more.yaml"
        shared.write_text(
            "# Two systems kept together by hand.\n"
            "- system_id: SYS-A\n  name: A\n  status: Active\n  owner_org_id: ORG-PAY\n  criticality: Low\n"
            "\n# The second, with a remark.\n"
            "- system_id: SYS-B\n  name: B\n  status: Active\n  owner_org_id: ORG-PAY\n  criticality: Low\n",
            encoding="utf-8")
        before = {p: p.read_text(encoding="utf-8") for p in (self.root / "10_MODEL").rglob("*.yaml")}
        model = self.model()
        batch = records.set_many(model, self.root, "systems", ["SYS-PORTAL", "SYS-A", "SYS-B", "SYS-GATEWAY"],
                                 "network_zone", "Private-App")
        self.assertEqual(batch.changed, ["SYS-PORTAL", "SYS-A", "SYS-B", "SYS-GATEWAY"])
        self.assertEqual((batch.unchanged, batch.refused, batch.moved), ([], [], []))
        # Planned only: the disk is as it was.
        self.assertEqual({p: p.read_text(encoding="utf-8") for p in before}, before)
        self.assertEqual(sorted(p.name for p in batch.files), ["SYS-GATEWAY.yaml", "SYS-PORTAL.yaml", "more.yaml"])
        old, new = batch.files[shared]
        self.assertEqual(old, before[shared])
        self.assertIn("# The second, with a remark.\n", new)
        self.assertEqual(new.count("network_zone: Private-App"), 2)
        self.assertIn("network_zone: Private-App", batch.files[self.root / "10_MODEL" / "systems" / "SYS-GATEWAY.yaml"][1])
        self.assertNotIn("network_zone: Edge", batch.files[self.root / "10_MODEL" / "systems" / "SYS-GATEWAY.yaml"][1])
        for path, (_old, text) in batch.files.items():
            path.write_text(text, encoding="utf-8")
        zones = {r["system_id"]: r.get("network_zone") for r in load(self.root).all_of("systems")}
        self.assertEqual(zones["SYS-B"], "Private-App")

    def test_what_it_already_says_and_what_it_cannot_change(self) -> None:
        model = self.model()
        batch = records.set_many(model, self.root, "systems", ["SYS-GATEWAY", "SYS-NOPE"], "network_zone", "Edge")
        self.assertEqual((batch.changed, batch.unchanged), ([], ["SYS-GATEWAY"]))
        self.assertEqual(batch.refused, [("SYS-NOPE", "not a system here")])
        made = dict(model.get("systems", "SYS-CRM"), archetype_instance="PRD-X")
        with self.assertRaises(records.Refused) as caught:
            records.change(self.root, "systems", "SYS-CRM", made, {"name": "x"}, {})
        self.assertIn("Made by PRD-X", str(caught.exception))
        for field, value, said in (("network_zone", "DMZ", "not one of"), ("owner_org_id", "ORG-NONE", "not a org unit"),
                                   ("module", "x", "set by the shape"), ("hue", "x", "has no field")):
            with self.assertRaises(records.Refused) as caught:
                records.set_many(model, self.root, "systems", ["SYS-CRM"], field, value)
            self.assertIn(said, str(caught.exception).lower())

    def test_a_harvested_record_moves_and_a_tag_is_added(self) -> None:
        harvested = self.root / "10_MODEL" / "systems" / "from_business_layer.yaml"
        harvested.write_text(
            "- system_id: SYS-H1\n  name: H1\n  status: Proposed\n  owner_org_id: ORG-PAY\n  criticality: Low\n"
            "  source: Business architecture repository\n"
            "- system_id: SYS-H2\n  name: H2\n  status: Proposed\n  owner_org_id: ORG-PAY\n  criticality: Low\n"
            "  source: Business architecture repository\n", encoding="utf-8")
        model = self.model()
        batch = records.set_many(model, self.root, "systems", ["SYS-H1"], "region", "eu-west-2")
        self.assertEqual(batch.moved, ["SYS-H1"])
        moved = batch.files[self.root / "10_MODEL" / "systems" / "SYS-H1.yaml"]
        self.assertIsNone(moved[0])
        self.assertTrue(moved[1].startswith("# Moved out of systems/from_business_layer.yaml"))
        self.assertNotIn("SYS-H1", batch.files[harvested][1])
        self.assertIn("SYS-H2", batch.files[harvested][1])
        tagged = records.set_many(model, self.root, "systems", ["SYS-CRM"], "tags", "vendor")
        self.assertIn("tags: [vendor]", tagged.files[self.root / "10_MODEL" / "systems" / "SYS-CRM.yaml"][1])


class TestTheCommand(_Estate):
    def test_terrane_needs_says_it_in_the_terminal(self) -> None:
        import contextlib
        import io

        from terrane import cli

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["--root", str(self.root), "needs", "tiered-architecture"])
        self.assertEqual(code, 0)
        self.assertIn("Tiered Architecture: thin, 2 drawn, 2 left off for want of a field", out.getvalue())
        self.assertIn("systems.network_zone", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["--root", str(self.root), "needs"])
        self.assertIn("Kinds of record the estate has none of", out.getvalue())
        self.assertIn("tech_services", out.getvalue())



def _server(root: Path):
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestTheApp(_Estate):
    """The endpoints the app reads and writes by, on an estate of its own."""

    def test_needs_set_on_many_and_put_back(self) -> None:
        server = _server(self.root)
        # An import on Windows writes CRLF; Undo is to put the bytes back.
        crlf = self.root / "10_MODEL" / "systems" / "SYS-PORTAL.yaml"
        crlf.write_bytes(crlf.read_bytes().replace(bytes([10]), bytes([13, 10])))
        before = crlf.read_bytes()
        listed = server.api_needs({}, {})
        zone = [f for f in listed["fields"] if (f["type"], f["field"]) == ("systems", "network_zone")][0]
        self.assertEqual((zone["lacking"], zone["views"][0]["viewId"]), (2, "multi-az-deployment"))
        self.assertIn("tech_services", [k["type"] for k in listed["none"]])
        tiers = server.api_needs_view({"view": ["tiered-architecture"]}, {})
        self.assertEqual((tiers["state"], tiers["drawn"], tiers["keptOff"]), ("thin", 2, 2))
        lacking = server.api_needs_records({"type": ["systems"], "field": ["network_zone"],
                                            "view": ["tiered-architecture"]}, {})
        self.assertEqual([r["id"] for r in lacking["records"]], ["SYS-CRM", "SYS-PORTAL"])
        self.assertEqual(lacking["values"][0], {"value": "Edge", "label": "Edge"})
        self.assertEqual(lacking["records"][1]["context"]["owner_org_id"], "Cards")
        done = server.api_records_set({}, {"type": "systems", "field": "network_zone", "value": "Private-App",
                                           "ids": ["SYS-CRM", "SYS-PORTAL"]})
        self.assertEqual((done["changed"], done["refused"], done["files"], done["errors"]),
                         (["SYS-CRM", "SYS-PORTAL"], [], 2, []))
        self.assertEqual(server.api_needs_view({"view": ["tiered-architecture"]}, {})["keptOff"], 0)
        self.assertEqual(server.api_records_undo({}, {"token": done["undo"]})["restored"], 2)
        self.assertEqual(crlf.read_bytes(), before)
        self.assertEqual(server.api_needs_view({"view": ["tiered-architecture"]}, {})["keptOff"], 2)
        with self.assertRaises(server.ApiError):
            server.api_records_undo({}, {"token": done["undo"]})
        with self.assertRaises(server.ApiError) as refused:
            server.api_records_set({}, {"type": "systems", "field": "network_zone", "value": "DMZ", "ids": ["SYS-CRM"]})
        self.assertIn("not one of", refused.exception.message)

    def test_an_estate_started_and_opened_from_the_app(self) -> None:
        server = _server(self.root)
        other = Path(tempfile.mkdtemp(prefix=PREFIX))
        try:
            fresh = other / "northwind"
            started = server.api_estate_start({}, {"name": "Northwind Bank", "folder": str(fresh)})
            self.assertEqual((started["name"], started["records"], started["written"][0]),
                             ("Northwind Bank", 0, "10_MODEL/model.yaml"))
            self.assertEqual(server.REPO_ROOT, fresh.resolve())
            self.assertEqual(server.api_overview({}, {})["modelName"], "Northwind Bank")
            self.assertTrue(server.api_overview({}, {})["empty"])
            with self.assertRaises(server.ApiError):
                server.api_estate_start({}, {"name": "Again", "folder": str(fresh)})
            with self.assertRaises(server.ApiError):
                server.api_estate_open({}, {"path": str(other)})
            self.assertEqual(server.REPO_ROOT, fresh.resolve())
            back = server.api_estate_open({}, {"path": str(self.root)})
            self.assertEqual((back["name"], back["records"]), ("Needs", 7))
            listed = [e for e in server.api_estates({}, {})["estates"] if e["current"]]
            self.assertEqual([e["name"] for e in listed], ["Needs"])
        finally:
            self.assertEqual(other.parent, Path(tempfile.gettempdir()))
            shutil.rmtree(other)


if __name__ == "__main__":
    unittest.main()
