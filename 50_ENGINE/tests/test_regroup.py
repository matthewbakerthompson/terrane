"""Moving a box into another boundary on a drawing.

A boundary is one value of a field the view groups by, so the drop sets that
field on the record and the box moves on every drawing grouped by it. These
hold the three things the app is told rather than left to guess: which
boundaries a drop can mean and the value each stores, what a drop would
change or why it cannot, and which drawings the box moves on, joins or comes
off -- checked against what a real save then draws.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import model as model_module, regroup  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.query import bind, load_views, resolve  # noqa: E402

from _fixture import REPO, Sandbox, drawable, seeded_root, setup_shared, teardown_shared  # noqa: E402


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


def _view(views, view_id):
    return [v for v in views if v.view_id == view_id][0]


def _where(model, view, entity_id):
    for node in resolve(model, view).nodes:
        if node.key == entity_id:
            return node.groups
    return None


class TestTheBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = model_module.load(seeded_root())
        cls.views = load_views(seeded_root() / "30_VIEWS")

    def test_a_field_boundary_stores_the_value_its_records_hold(self) -> None:
        graph = resolve(self.model, _view(self.views, "integration-architecture"))
        found = regroup.boundaries(graph)
        self.assertEqual(set(found), set(graph.groups))
        for node in graph.nodes:
            # An offered interface is in its owner's boundary and says no category of its own.
            if node.groups and node.entity_type != "offered_interfaces":
                self.assertEqual(found[node.groups], ("system_category", node.record["system_category"]))

    def test_a_reference_boundary_is_labeled_by_name_and_stores_the_id(self) -> None:
        graph = resolve(self.model, _view(self.views, "capability-map"))
        found = regroup.boundaries(graph)
        parents = {path: b for path, b in found.items() if b.field == "parent_capability_id"}
        self.assertTrue(parents)
        for path, boundary in parents.items():
            parent = self.model.get("capabilities", boundary.value)
            self.assertIsNotNone(parent, boundary.value)
            self.assertEqual(path[-1], parent["name"])

    def test_a_kind_of_thing_or_a_relation_is_not_a_field_to_set(self) -> None:
        for view_id in ("framework-landscape", "data-and-processes"):
            with self.subTest(view=view_id):
                view = drawable(self.model, _view(self.views, view_id))
                graph = resolve(self.model, view)
                self.assertTrue(graph.groups)
                self.assertEqual(regroup.boundaries(graph), {})

    def test_the_drawing_carries_each_boundary_s_field_and_value(self) -> None:
        server = _server_for(seeded_root())
        palette = Palette(self.model.config.get("palette"))
        payload = server._graph_payload(self.model, _view(self.views, "capability-map"), palette)
        groups = [e["data"] for e in payload["elements"] if e["data"].get("isGroup")]
        self.assertTrue(groups)
        for group in groups:
            self.assertIn(group["field"], ("capability_tier", "parent_capability_id"))
            if group["field"] == "parent_capability_id":
                self.assertEqual(self.model.get("capabilities", group["stored"])["name"], group["value"])
        payload = server._graph_payload(self.model, drawable(self.model, _view(self.views, "data-and-processes")), palette)
        groups = [e["data"] for e in payload["elements"] if e["data"].get("isGroup")]
        self.assertTrue(groups)
        self.assertTrue(all(g["field"] is None and g["stored"] is None for g in groups))


class TestThePlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.views = load_views(seeded_root() / "30_VIEWS")

    def setUp(self) -> None:
        # Loaded per test: two of them change a record in memory.
        self.model = model_module.load(seeded_root())

    def _a_system_in(self, view_id, field):
        graph = resolve(self.model, _view(self.views, view_id))
        values = sorted({str(n.record.get(field)) for n in graph.nodes if n.record.get(field)})
        # A system: an offered interface sits in its owner's boundary and
        # holds none of the fields the boundary is made of.
        node = [n for n in graph.nodes if n.groups and n.record.get(field)][0]
        other = [v for v in values if v != str(node.record[field])][0]
        return node.key, node.record[field], other

    def test_a_drop_into_another_category_sets_the_category(self) -> None:
        system, now, other = self._a_system_in("integration-architecture", "system_category")
        plan = regroup.plan(self.model, self.views, system, [("system_category", other)])
        self.assertIsNone(plan.blocked)
        self.assertEqual(plan.changes, [regroup.Change("system_category", now, other)])
        here = [d for d in plan.drawings if d.view_id == "integration-architecture"]
        self.assertEqual([d.effect for d in here], ["moves"])
        # Only drawings grouped by the field are named.
        for drawing in plan.drawings:
            self.assertIn("system_category", _view(self.views, drawing.view_id).group_by)

    def test_the_boundary_it_is_in_changes_nothing(self) -> None:
        system, now, _other = self._a_system_in("integration-architecture", "system_category")
        plan = regroup.plan(self.model, self.views, system, [("system_category", now)])
        self.assertEqual((plan.changes, plan.drawings, plan.blocked), ([], [], None))

    def test_only_the_levels_that_differ_are_changed(self) -> None:
        view = drawable(self.model, _view(self.views, "network-topology"))
        graph = resolve(self.model, view)
        found = regroup.boundaries(graph)
        node = [n for n in graph.nodes if len(n.groups) >= 2][0]
        sibling = [p for p in found if len(p) == 2 and p[0] == node.groups[0] and p[1] != node.groups[1]]
        self.assertTrue(sibling, "another account under %s" % node.groups[0])
        into = [tuple(found[sibling[0][:i]]) for i in (1, 2)]
        plan = regroup.plan(self.model, self.views, node.key, into)
        self.assertEqual([c.field for c in plan.changes], [found[sibling[0]].field])

    def test_a_field_the_thing_does_not_have_is_said(self) -> None:
        asset = self.model.all_of("data_assets")[0]
        plan = regroup.plan(self.model, self.views, asset["data_asset_id"], [("system_category", "Core")])
        self.assertIn("has no system category", plan.blocked)
        self.assertEqual(plan.changes, [])

    def test_a_kind_of_thing_is_not_a_boundary_to_move_into(self) -> None:
        system = self.model.all_of("systems")[0]
        plan = regroup.plan(self.model, self.views, system["system_id"], [("type", "Data Asset")])
        self.assertIn("Those boxes are types", plan.blocked)

    def test_an_imported_record_says_where_it_is_changed(self) -> None:
        graph = resolve(self.model, _view(self.views, "capability-map"))
        found = regroup.boundaries(graph)
        node = [n for n in graph.nodes if len(n.groups) == 2][0]
        other = [b for p, b in found.items() if b.field == "parent_capability_id" and p != node.groups][0]
        plan = regroup.plan(self.model, self.views, node.key, [other])
        self.assertIn("Imported from", plan.blocked)
        self.assertIn("next one", plan.blocked)

    def test_a_generated_record_points_at_its_shape(self) -> None:
        system, _now, other = self._a_system_in("integration-architecture", "system_category")
        # The seed holds no product on a shape, so one is made generated here:
        # what refuses it is the stamp an expansion leaves on what it made.
        self.model.find(system)[1]["archetype_instance"] = "PRD-SOMETHING"
        plan = regroup.plan(self.model, self.views, system, [("system_category", other)])
        self.assertIn("Made by PRD-SOMETHING", plan.blocked)
        self.assertIn("overrides", plan.blocked)

    def test_a_subject_drawing_is_named_with_its_subject(self) -> None:
        view = _view(self.views, "product-architecture")
        bound = bind(view, {"product": "PRD-CARD-SERVICING"}, self.model)
        graph = resolve(self.model, bound)
        found = regroup.boundaries(graph)
        zones = {b.value for b in found.values() if b.field == "network_zone"}
        node = [n for n in graph.nodes if n.record.get("network_zone") and len(zones - {n.record["network_zone"]})][0]
        other = sorted(zones - {node.record["network_zone"]})[0]
        plan = regroup.plan(self.model, self.views, node.key, [("network_zone", other)])
        mine = [d for d in plan.drawings if d.view_id == "product-architecture" and d.subject == "PRD-CARD-SERVICING"]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0].effect, "moves")
        self.assertEqual(mine[0].subject_name, self.model.get("products", "PRD-CARD-SERVICING")["name"])


class TestTheEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _server_for(seeded_root())
        cls.model = model_module.load(seeded_root())

    def test_it_says_the_change_by_name_and_marks_the_drawing_on_screen(self) -> None:
        graph = resolve(self.model, _view(load_views(seeded_root() / "30_VIEWS"), "capability-map"))
        node = [n for n in graph.nodes if len(n.groups) == 2][0]
        got = self.server.api_regroup_options(None, {
            "id": node.key, "into": [{"field": "capability_tier", "value": node.record["capability_tier"]}],
            "view": "capability-map",
        })
        self.assertEqual((got["changes"], got["drawings"], got["blocked"]), ([], [], None))
        system = self.model.get("systems", "SYS-AUTH-SWITCH")
        other = "Channel" if system["system_category"] != "Channel" else "Core"
        got = self.server.api_regroup_options(None, {
            "id": "SYS-AUTH-SWITCH", "into": [{"field": "system_category", "value": other}],
            "view": "integration-architecture",
        })
        change = got["changes"][0]
        self.assertEqual((change["words"], change["before"], change["after"]),
                         ("system category", system["system_category"], other))
        here = [d for d in got["drawings"] if d["here"]]
        self.assertEqual([d["view"] for d in here], ["integration-architecture"])

    def test_a_reference_is_said_with_the_names_the_drawing_used(self) -> None:
        system = [s for s in self.model.all_of("systems") if s.get("owner_org_id")][0]
        other = [o for o in self.model.all_of("org_units") if o["org_unit_id"] != system["owner_org_id"]][0]
        got = self.server.api_regroup_options(None, {
            "id": system["system_id"], "into": [{"field": "owner_org_id", "value": other["org_unit_id"]}],
        })
        change = got["changes"][0]
        self.assertEqual(change["words"], "owner org")
        self.assertEqual(change["afterLabel"], other["name"])
        self.assertEqual(change["beforeLabel"], self.model.get("org_units", system["owner_org_id"])["name"])

    def test_refusals(self) -> None:
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_regroup_options(None, {"id": "SYS-NOT-THERE", "into": [{"field": "system_category", "value": "Core"}]})
        self.assertEqual(caught.exception.status, 404)
        with self.assertRaises(self.server.ApiError):
            self.server.api_regroup_options(None, {"id": "SYS-AUTH-SWITCH", "into": []})


class TestTheMove(unittest.TestCase):
    def setUp(self) -> None:
        box = Sandbox(seed=True)
        self.root = box.__enter__()
        self.addCleanup(box.__exit__, None, None, None)
        self.server = _server_for(self.root)
        self.views = load_views(self.root / "30_VIEWS")

    def test_the_plan_says_what_the_save_then_draws(self) -> None:
        """Every drawing the plan names behaves as it said once the one-field
        save is made, the drawing a scope takes it off included; and Undo,
        the same save with the old value, leaves the file as it was."""
        model = model_module.load(self.root)
        graph = resolve(model, _view(self.views, "domain-servicing"))
        candidates = [n.key for n in graph.nodes if n.groups == ("Servicing",)]
        chosen = None
        for system in candidates:
            plan = regroup.plan(model, self.views, system, [("company_domain", "Lending")])
            if any(d.effect == "leaves" for d in plan.drawings):
                chosen = plan
                break
        self.assertIsNotNone(chosen, "a Servicing system whose move takes it off domain-servicing")
        record = model.get("systems", chosen.entity_id)
        path = Path(record["_source_file"])
        # Text, not bytes: the seed's importer writes the platform's line
        # endings and a save writes LF, which `.gitattributes` makes one.
        before = path.read_text(encoding="utf-8")

        self.server.api_save(None, {"type": "systems", "id": chosen.entity_id, "patch": True,
                                    "values": {"company_domain": "Lending"}})
        after_lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(after_lines), len(before.splitlines()))
        moved = model_module.load(self.root)
        for drawing in chosen.drawings:
            with self.subTest(view=drawing.view_id, subject=drawing.subject):
                view = _view(self.views, drawing.view_id)
                if drawing.subject:
                    view_now = bind(view, {view.parameters[0].name: drawing.subject}, model)
                    view_then = bind(view, {view.parameters[0].name: drawing.subject}, moved)
                else:
                    view_now = view_then = view
                was, now = _where(model, view_now, chosen.entity_id), _where(moved, view_then, chosen.entity_id)
                effect = "moves" if was is not None and now is not None else "joins" if was is None else "leaves"
                self.assertEqual(effect, drawing.effect)
                if effect == "moves":
                    self.assertNotEqual(was, now)

        self.server.api_save(None, {"type": "systems", "id": chosen.entity_id, "patch": True,
                                    "values": {"company_domain": record["company_domain"]}})
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_a_harvested_record_is_told_it_moves_file(self) -> None:
        shared = self.root / "10_MODEL" / "systems" / "from_business_layer.yaml"
        shared.write_text(
            "- system_id: SYS-HARVESTED-ONE\n"
            "  name: Harvested One\n"
            "  system_category: Application\n"
            "  source: Business layer process map\n",
            encoding="utf-8",
        )
        model = model_module.load(self.root)
        plan = regroup.plan(model, self.views, "SYS-HARVESTED-ONE", [("system_category", "Core")])
        self.assertIsNone(plan.blocked)
        self.assertIn("from_business_layer.yaml", plan.note)
        self.assertIn("file of its own", plan.note)


if __name__ == "__main__":
    unittest.main()
