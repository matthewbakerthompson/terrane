"""Tests for the governance layer: controls, policies, and where the estate
enforces them.

The register is imported and the enforcement points are authored, so most of
what is checked here is that the join between the two stays honest: a derived
pair says what it was derived from, a gap report names only what is actually
missing, and impact runs the way an audit would expect it to.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from terrane import impact, validate  # noqa: E402
from terrane.query import (  # noqa: E402
    bind,
    parse_view,
    reference_fields,
    render_targets,
    resolve,
)
from terrane.schema import ENTITY_TYPES, RELATION_TYPES  # noqa: E402

import import_business_layer as business  # noqa: E402

from _fixture import (  # noqa: E402
    REPO,
    drawable,
    seeded_model,
    seeded_root,
    seeded_views,
    setup_shared,
    teardown_shared,
)


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestContract(unittest.TestCase):
    """What the metamodel names, this repository names the same way."""

    def test_controls_and_policies_are_canonical(self) -> None:
        for name in ("controls", "policies"):
            with self.subTest(entity=name):
                self.assertFalse(ENTITY_TYPES[name].extension)

    def test_the_four_canonical_relations_carry_the_metamodel_columns(self) -> None:
        # As `architecture_method_metamodel.v2.canonical.json` lists them. A
        # renamed column here is a silently empty column on the Collibra side.
        expected = {
            "system_governed_by_control": ("systems", "controls", "system_id", "control_id"),
            "system_subject_to_policy": ("systems", "policies", "system_id", "policy_id"),
            "data_governed_by_control": ("data_assets", "controls", "data_asset_id", "control_id"),
            "data_subject_to_policy": ("data_assets", "policies", "data_asset_id", "policy_id"),
        }
        for name, shape in expected.items():
            spec = RELATION_TYPES[name]
            with self.subTest(relation=name):
                self.assertEqual(
                    (spec.left, spec.right, spec.left_column, spec.right_column), shape
                )
                self.assertFalse(spec.extension)
                self.assertIsNone(spec.qualifier)

    def test_the_derived_relations_are_extensions_and_carry_a_basis(self) -> None:
        for name in ("capability_governed_by_control", "capability_subject_to_policy"):
            with self.subTest(relation=name):
                self.assertTrue(RELATION_TYPES[name].extension)
                self.assertEqual(RELATION_TYPES[name].qualifier, "basis")


class TestDerivation(unittest.TestCase):
    """The capability join, on a hand-built business layer."""

    CAPS = [
        {"capability_id": "CAP-X"},
        {"capability_id": "CAP-X-01", "parent_capability_id": "CAP-X"},
        {"capability_id": "CAP-X-01-A", "parent_capability_id": "CAP-X-01"},
        {"capability_id": "CAP-Y"},
    ]
    SUPPORTS = [
        {"process_id": "P-1", "capability_id": "CAP-X-01-A"},
        {"process_id": "P-2", "capability_id": "CAP-Y"},
    ]
    GOVERNED = [
        {"process_id": "P-1", "control_id": "CTL-A"},
        {"process_id": "P-2", "control_id": "CTL-GHOST"},
    ]
    SUBJECT = [{"process_id": "P-1", "policy_id": "POL-A"}]

    def _derive(self) -> dict:
        return business.derived_governance(
            self.SUPPORTS, self.GOVERNED, self.SUBJECT, self.CAPS, {"CTL-A"}, {"POL-A"}
        )

    def test_a_process_join_says_so(self) -> None:
        rows = self._derive()["capability_governed_by_control"]
        self.assertIn(
            {"capability_id": "CAP-X-01-A", "control_id": "CTL-A", "basis": "Process"}, rows
        )

    def test_it_rolls_up_to_every_ancestor_and_says_that_too(self) -> None:
        rows = self._derive()["capability_governed_by_control"]
        for ancestor in ("CAP-X-01", "CAP-X"):
            with self.subTest(capability=ancestor):
                self.assertIn(
                    {"capability_id": ancestor, "control_id": "CTL-A", "basis": "Descendant"},
                    rows,
                )

    def test_a_control_the_register_does_not_hold_is_dropped(self) -> None:
        """A pair naming a control that is not in the register would be a
        dangling reference, which fails the load, so it is never written."""
        rows = self._derive()["capability_governed_by_control"]
        self.assertFalse(any(r["control_id"] == "CTL-GHOST" for r in rows))
        self.assertFalse(any(r["capability_id"] == "CAP-Y" for r in rows))

    def test_policies_derive_the_same_way(self) -> None:
        rows = self._derive()["capability_subject_to_policy"]
        self.assertEqual(
            {(r["capability_id"], r["basis"]) for r in rows},
            {("CAP-X-01-A", "Process"), ("CAP-X-01", "Descendant"), ("CAP-X", "Descendant")},
        )

    def test_the_output_is_ordered(self) -> None:
        """Generated files are committed, so their order has to be a function
        of the data and not of the input order."""
        rows = self._derive()["capability_governed_by_control"]
        self.assertEqual(
            rows, sorted(rows, key=lambda r: (r["capability_id"], r["control_id"], r["basis"]))
        )


class TestReferenceFieldEdges(unittest.TestCase):
    """A field that points at another entity is a relationship the model
    already records, and a view can follow it without a relation table."""

    def test_only_reference_fields_qualify(self) -> None:
        self.assertTrue(reference_fields("policy_id"))
        self.assertTrue(reference_fields("parent_capability_id"))
        self.assertFalse(reference_fields("name"))
        self.assertFalse(reference_fields("system_uses_tech_service"))
        self.assertFalse(reference_fields(None))

    def test_a_view_can_expand_along_one_and_draw_it(self) -> None:
        model = seeded_model()
        view = parse_view({
            "view_id": "probe",
            "kind": "report",
            "group_by": "type",
            "scope": {
                "include": [{"type": "policies"}],
                "expand": [{"relation": "policy_id", "depth": 1, "types": ["controls"]}],
            },
            "edges": [{"via": "policy_id"}],
        })
        graph = resolve(model, view)
        self.assertTrue(any(n.entity_type == "controls" for n in graph.nodes))
        edge = next(e for e in graph.edges if e.kind == "policy_id")
        # From the record to what it points at, labeled with the field.
        self.assertTrue(edge.source.startswith("CTL-"))
        self.assertTrue(edge.target.startswith("POL-"))
        self.assertEqual(edge.label, "policy")


class TestSeededEstate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def test_the_register_comes_through_the_csv_seed(self) -> None:
        self.assertGreaterEqual(len(self.model.all_of("controls")), 30)
        self.assertGreaterEqual(len(self.model.all_of("policies")), 5)
        self.assertTrue(self.model.relation_rows("system_governed_by_control"))
        self.assertTrue(self.model.relation_rows("capability_governed_by_control"))

    def test_every_control_gives_effect_to_a_policy_the_model_holds(self) -> None:
        policies = {p["policy_id"] for p in self.model.all_of("policies")}
        for control in self.model.all_of("controls"):
            with self.subTest(control=control["control_id"]):
                self.assertIn(control.get("policy_id"), policies)

    def test_the_gates_pass(self) -> None:
        report = validate.run(self.model, seeded_views())
        self.assertEqual(report.errors, [])

    def test_a_restricted_system_with_no_control_warns_and_does_not_fail(self) -> None:
        report = validate.run(self.model, seeded_views())
        self.assertIn("governance.no_control", {f.code for f in report.warnings})
        self.assertNotIn("governance.no_control", {f.code for f in report.errors})

    def test_the_warning_is_silent_without_a_register(self) -> None:
        """A model that holds no controls cannot be asked which systems record
        none of them. Warning anyway would fire on every system in every
        model, and a warning that always fires is one nobody reads."""
        model = seeded_model()
        model.entities["controls"] = {}
        for name in RELATION_TYPES:
            if RELATION_TYPES[name].right == "controls":
                model.relations[name] = []
        report = validate.run(model)
        self.assertNotIn("governance.no_control", {f.code for f in report.findings})

    def test_the_governance_views_draw_something(self) -> None:
        for view in seeded_views():
            if view.category != "Governance":
                continue
            with self.subTest(view=view.view_id):
                bound = drawable(self.model, view)
                if bound is None:
                    continue  # nothing in the seed for this subject view
                graph = resolve(self.model, bound)
                self.assertTrue(graph.nodes)
                self.assertTrue(graph.edges)

    def test_every_governance_subject_has_something_to_draw(self) -> None:
        """Not just the one `drawable` picks. `has_any` on `render_for` is
        what makes this hold: a system with no control, no policy and no
        capability to inherit one through drew as a single box, and the
        coverage report says that better than a picture of nothing."""
        view = next(v for v in seeded_views() if v.view_id == "system-governance")
        targets = render_targets(self.model, view)
        self.assertTrue(targets)
        for parameter, value in targets:
            with self.subTest(system=value):
                bound = bind(view, {parameter: value}, self.model)
                self.assertTrue(resolve(self.model, bound).edges)

    def test_a_subject_survives_its_own_diagram_being_cut(self) -> None:
        """The ledger's governance matches fifty-odd entities and the view
        keeps forty. Cut by id alone, `SYS-` sorts after every `CAP-` and
        `CTL-`, and the committed diagram of the ledger's governance had no
        ledger in it. What the scope names survives the cut."""
        view = next(v for v in seeded_views() if v.view_id == "system-governance")
        graph = resolve(self.model, bind(view, {"system": "SYS-CORE-LEDGER"}, self.model))
        self.assertTrue(graph.notes, "the ledger is meant to hit max_nodes; pick a bigger system")
        self.assertIn("SYS-CORE-LEDGER", {node.key for node in graph.nodes})
        self.assertIn("the scope names", graph.notes[0])

    def test_a_system_with_nothing_governing_it_gets_no_diagram(self) -> None:
        """The filter is doing work, rather than passing because the seed
        happens to govern everything."""
        view = next(v for v in seeded_views() if v.view_id == "system-governance")
        orphan = {
            "system_id": "SYS-UNGOVERNED",
            "name": "Ungoverned Thing",
            "status": "Active",
            "owner_org_id": "ORG-PLATFORM-ENG",
            "criticality": "High",
            "data_classification_supported": "Restricted",
            "_type": "systems",
            "_source_file": "<test>",
        }
        self.model.entities["systems"]["SYS-UNGOVERNED"] = orphan
        try:
            picked = {value for _parameter, value in render_targets(self.model, view)}
            self.assertNotIn("SYS-UNGOVERNED", picked)
        finally:
            del self.model.entities["systems"]["SYS-UNGOVERNED"]


class TestInstanceCarriesItsRows(unittest.TestCase):
    """A product file can be the whole story of a product: the controls its
    shape cannot know are recorded on the instance, not in the shared file."""

    def test_the_screening_instance_carries_the_sanctions_control(self) -> None:
        from _fixture import REPO
        from terrane import model as model_module

        model = model_module.load(REPO)
        governed = {(r["system_id"], r["control_id"]) for r in model.relations["system_governed_by_control"]}
        self.assertIn(("SYS-SCREENING-VENDOR", "CTL-SANCTIONS"), governed)
        self.assertIn(("SYS-SCREENING-GATEWAY", "CTL-SANCTIONS"), governed)
        shared = (REPO / "10_MODEL" / "relations" / "governance.yaml").read_text(encoding="utf-8")
        self.assertNotIn("CTL-SANCTIONS", shared)


class TestBusinessLayerEstate(unittest.TestCase):
    """What the second import brings: processes, the systems they were
    mapped against, and the joins, with the two repositories' ids reconciled."""

    @classmethod
    def setUpClass(cls) -> None:
        from _fixture import REPO
        from terrane import model as model_module

        cls.model = model_module.load(REPO)

    def test_processes_arrived_with_their_value_streams(self) -> None:
        processes = self.model.entities["processes"]
        self.assertGreater(len(processes), 100)
        placed = [p for p in processes.values() if p.get("value_stream_id")]
        self.assertGreater(len(placed), 50)
        for p in placed:
            self.assertIn(p["value_stream_id"], self.model.entities["value_streams"])

    def test_aliases_land_a_process_on_this_estates_id(self) -> None:
        rows = self.model.relations["process_uses_system"]
        used = {r["system_id"] for r in rows}
        self.assertIn("SYS-CORE-LEDGER", used)
        self.assertNotIn("SYS-CORE", used)
        self.assertNotIn("SYS-MANUAL", used)
        self.assertNotIn("SYS-MANUAL", self.model.entities["systems"])
        for r in rows:
            self.assertIn(r["system_id"], self.model.entities["systems"], r)

    def test_harvested_systems_say_where_they_came_from(self) -> None:
        harvested = [s for s in self.model.entities["systems"].values()
                     if s.get("source") == "Business architecture repository"]
        self.assertGreater(len(harvested), 20)
        self.assertNotIn("SYS-CORE-LEDGER", [s["system_id"] for s in harvested])

    def test_realizations_are_derived_across_the_organization(self) -> None:
        rows = self.model.relations["system_realizes_capability"]
        systems = {r["system_id"] for r in rows}
        capabilities = {r["capability_id"] for r in rows}
        self.assertGreater(len(rows), 100)
        self.assertGreater(len(systems), 25)
        self.assertGreater(len(capabilities), 60)

    def test_framework_references_reach_level_one(self) -> None:
        rows = self.model.relations["capability_references_framework"]
        self.assertGreater(len(rows), 150)
        frameworks = {r["framework_id"] for r in rows}
        for fw in ("FW-BIAN", "FW-ITIL", "FW-CRI", "FW-DMBOK"):
            self.assertIn(fw, frameworks)
        self.assertTrue(all(r.get("ref") for r in rows))


class TestImpact(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def test_retiring_a_system_affects_the_controls_it_enforces(self) -> None:
        row = self.model.relation_rows("system_governed_by_control")[0]
        result = impact.analyze(self.model, str(row["system_id"]), max_distance=1)
        self.assertIn(str(row["control_id"]), {h.entity_id for h in result.downstream})

    def test_a_control_depends_on_the_policy_it_gives_effect_to(self) -> None:
        control = next(c for c in self.model.all_of("controls") if c.get("policy_id"))
        result = impact.analyze(self.model, str(control["control_id"]), max_distance=1)
        self.assertIn(str(control["policy_id"]), {h.entity_id for h in result.upstream})

    def test_a_policy_change_reaches_what_is_subject_to_it(self) -> None:
        row = self.model.relation_rows("system_subject_to_policy")[0]
        result = impact.analyze(self.model, str(row["policy_id"]), max_distance=1)
        self.assertIn(str(row["system_id"]), {h.entity_id for h in result.downstream})


class TestCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = seeded_root()
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        cls.server = server_module
        cls.model = seeded_model()
        cls.gaps = {g["key"]: g for g in server_module.api_coverage({}, {})["gaps"]}

    def test_the_governance_gaps_are_reported(self) -> None:
        for key in (
            "control.unenforced",
            "system.restricted-no-control",
            "system.inherited-control-unrecorded",
            "data.pii-no-policy",
        ):
            with self.subTest(gap=key):
                self.assertIn(key, self.gaps)

    def test_restricted_systems_named_are_restricted_and_ungoverned(self) -> None:
        governed = {
            str(r["system_id"]) for r in self.model.relation_rows("system_governed_by_control")
        }
        for item in self.gaps["system.restricted-no-control"]["items"]:
            with self.subTest(system=item["id"]):
                self.assertNotIn(item["id"], governed)
                record = self.model.get("systems", item["id"])
                self.assertEqual(record["data_classification_supported"], "Restricted")

    def test_the_inherited_gap_names_only_systems_that_really_inherit(self) -> None:
        """A gap report with a false positive in it gets ignored, and then it
        may as well not exist."""
        expected = {}
        for row in self.model.relation_rows("capability_governed_by_control"):
            expected.setdefault(str(row["capability_id"]), set()).add(str(row["control_id"]))
        recorded = {}
        for row in self.model.relation_rows("system_governed_by_control"):
            recorded.setdefault(str(row["system_id"]), set()).add(str(row["control_id"]))
        realizes = {}
        for row in self.model.relation_rows("system_realizes_capability"):
            realizes.setdefault(str(row["system_id"]), set()).add(str(row["capability_id"]))
        # The gap is per capability: a system that records the controls of
        # one capability it realizes and none of another's is still a gap
        # for the second, now that realizations reach across the estate.
        for item in self.gaps["system.inherited-control-unrecorded"]["items"]:
            with self.subTest(system=item["id"]):
                have = recorded.get(item["id"], set())
                open_for = [
                    capability for capability in realizes.get(item["id"], ())
                    if expected.get(capability) and not (expected[capability] & have)
                ]
                self.assertTrue(open_for, "listed, but every governed capability it realizes has a control recorded")

    def test_an_unenforced_control_is_one_nothing_points_at(self) -> None:
        enforced = set()
        for name in ("system_governed_by_control", "data_governed_by_control"):
            enforced |= {str(r["control_id"]) for r in self.model.relation_rows(name)}
        for item in self.gaps["control.unenforced"]["items"]:
            self.assertNotIn(item["id"], enforced)

    def test_no_register_means_no_governance_gaps(self) -> None:
        model = seeded_model()
        model.entities["controls"] = {}
        self.assertEqual(self.server._governance_gaps(model), [])


if __name__ == "__main__":
    unittest.main()
