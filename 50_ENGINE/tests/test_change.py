"""Tests for the change layer: roadmaps, work packages and change requests.

The model could always say a system was Planned. What it could not say was
when the thing lands, under whose initiative, or on whose decision, and every
test here is about one of those three staying answerable: the schedule is a
join rather than a column of semicolons, the gates notice a plan with nothing
delivering it, and a date that cannot be compared is reported instead of being
compared anyway.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import validate  # noqa: E402
from terrane.query import bind, reference_fields, render_targets, resolve  # noqa: E402
from terrane.render_mermaid import quarter_bounds, render_timeline, render_timeline_markdown  # noqa: E402
from terrane.schema import ENTITY_TYPES, RELATION_TYPES  # noqa: E402

from _fixture import (  # noqa: E402
    seeded_model,
    seeded_views,
    setup_shared,
    teardown_shared,
)

CHANGE_TYPES = ("roadmaps", "work_packages", "architecture_change_requests")


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestContract(unittest.TestCase):
    """What the canonical metamodel names, this repository names the same way."""

    def test_all_three_are_canonical_with_the_canonical_keys(self) -> None:
        expected = {
            "roadmaps": "roadmap_id",
            "work_packages": "work_package_id",
            # Not `architecture_change_request_id`. The canonical key drops the
            # prefix, and a consumer joining on the metamodel's column name
            # would find nothing if this repository invented its own.
            "architecture_change_requests": "change_request_id",
        }
        for name, pk in expected.items():
            with self.subTest(entity=name):
                entity_type = ENTITY_TYPES[name]
                self.assertEqual(entity_type.pk, pk)
                self.assertFalse(entity_type.extension)

    def test_the_relations_are_extensions(self) -> None:
        """The metamodel carries what a work package touches as a semicolon
        list on the record, not as a table, so the tables are ours."""
        for name in ("work_package_affects_system", "change_request_affects_system"):
            with self.subTest(relation=name):
                self.assertTrue(RELATION_TYPES[name].extension)

    def test_a_roadmap_is_reached_by_a_reference_field_not_a_relation(self) -> None:
        owners = dict(reference_fields("roadmap_id"))
        self.assertIn("work_packages", owners)
        self.assertNotIn("roadmap_id", RELATION_TYPES)
        self.assertNotIn("work_package_on_roadmap", RELATION_TYPES)


class TestSeededEstate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def test_the_change_layer_survives_the_csv_round_trip(self) -> None:
        """The seed is an export re-imported, so a field the exporter drops
        would show up here as an entity that arrived without its links."""
        for name in CHANGE_TYPES:
            with self.subTest(entity=name):
                self.assertTrue(self.model.all_of(name))
        packages = self.model.all_of("work_packages")
        self.assertTrue(all(p.get("roadmap_id") for p in packages))
        self.assertTrue(any(p.get("change_request_id") for p in packages))
        self.assertTrue(self.model.relation_rows("work_package_affects_system"))

    def test_every_roadmap_a_work_package_names_is_one_the_model_holds(self) -> None:
        roadmaps = {r["roadmap_id"] for r in self.model.all_of("roadmaps")}
        for package in self.model.all_of("work_packages"):
            with self.subTest(work_package=package["work_package_id"]):
                self.assertIn(package["roadmap_id"], roadmaps)

    def test_the_gates_pass(self) -> None:
        report = validate.run(self.model, seeded_views())
        self.assertEqual(report.errors, [])

    def test_every_planned_system_is_delivered_by_something(self) -> None:
        """Which is what makes `change.unscheduled` a finding rather than the
        normal state of the estate."""
        report = validate.run(self.model)
        self.assertNotIn("change.unscheduled", {f.code for f in report.findings})

    def test_the_change_views_draw_something(self) -> None:
        drawn = 0
        for view in seeded_views():
            if view.view_id not in ("change-roadmap", "change-register"):
                continue
            with self.subTest(view=view.view_id):
                graph = resolve(self.model, view)
                self.assertTrue(graph.nodes)
                self.assertTrue(graph.edges)
                drawn += 1
        self.assertEqual(drawn, 2)

    def test_the_roadmap_is_drawn_on_quarters(self) -> None:
        """Roadmaps and work packages carried quarters for three rounds before
        anything drew them. The timeline is a gantt: a bar per package inside
        its roadmap, the systems it touches under the bar rather than on it."""
        self.assertEqual(quarter_bounds("2026-Q3"), ("2026-07-01", "2026-09-30"))
        self.assertEqual(quarter_bounds("2027-Q1"), ("2027-01-01", "2027-03-31"))
        self.assertIsNone(quarter_bounds("2026-07"))
        view = next(v for v in seeded_views() if v.view_id == "change-roadmap")
        self.assertEqual(view.kind, "timeline")
        graph = resolve(self.model, view)
        text = render_timeline(graph)
        self.assertTrue(text.startswith("gantt\n"))
        self.assertIn("  section Consumer Lending Growth\n", text)
        self.assertIn(
            "  Build installment lending on AWS :active, WP_LENDING_AWS, 2026-01-01, 2026-09-30",
            text,
        )
        self.assertNotIn("SYS-LENDING-API", text, "a system has no quarter and is not a bar")
        page = render_timeline_markdown(graph)
        self.assertIn("```mermaid\ngantt", page)
        self.assertIn("Installment Lending Service (builds)", page)
        self.assertEqual(text, render_timeline(graph))

    def test_a_work_package_s_footprint_is_read_off_the_estate(self) -> None:
        """What a work package touches in the business is derived, not
        declared: the screening onboarding changes the auth switch, the
        switch writes the transaction record, and eight processes read it.
        No row says the onboarding touches a process; the estate does."""
        view = next(v for v in seeded_views() if v.view_id == "change-footprint")
        # One per work package with a footprint: the merchant portal's is the
        # sixth, the first package for a product assembled from parts; the
        # seventh lands point-of-sale finance on Google Cloud, the eighth
        # buys its affordability data there, the ninth curates its
        # performance data in BigQuery.
        self.assertEqual(len(render_targets(self.model, view)), 9)
        graph = resolve(self.model, bind(view, {"work_package": "WP-SCREENING-ONBOARD"}, self.model))
        ids = {}
        for node in graph.nodes:
            pk = ENTITY_TYPES[node.entity_type].pk
            ids.setdefault(node.entity_type, set()).add(str(node.record.get(pk)))
        self.assertIn("SYS-AUTH-SWITCH", ids["systems"])
        self.assertIn("DA-TRANSACTION", ids["data_assets"])
        self.assertEqual(len(ids["processes"]), 8)
        self.assertNotIn("tech_services", ids)  # a footprint, not a topology
        self.assertLessEqual({"Builds", "Changes"}, {edge.label for edge in graph.edges})
        self.assertFalse([
            row for row in self.model.relation_rows("process_uses_system")
            if row.get("system_id") == "SYS-AUTH-SWITCH"
        ])

    def test_the_effect_qualifier_distinguishes_a_build_from_a_release(self) -> None:
        """A work package that only builds new systems can slip; one that
        changes a live system is a release. A view that cannot tell them apart
        is decoration, so the qualifier has to survive the round trip."""
        effects = {
            str(row.get("effect"))
            for row in self.model.relation_rows("work_package_affects_system")
        }
        self.assertIn("Builds", effects)
        self.assertIn("Changes", effects)


class TestGates(unittest.TestCase):
    """Each check fires on the thing it names, and on nothing else."""

    def _codes(self, model) -> set:
        return {f.code for f in validate.run(model).findings}

    def test_a_planned_system_nothing_delivers_is_reported(self) -> None:
        model = seeded_model()
        model.entities["systems"]["SYS-ORPHAN"] = {
            "system_id": "SYS-ORPHAN",
            "name": "Unscheduled Thing",
            "status": "Planned",
            "owner_org_id": "ORG-PLATFORM-ENG",
            "criticality": "Low",
            "_type": "systems",
            "_source_file": "<test>",
        }
        self.assertIn("change.unscheduled", self._codes(model))

    def test_it_is_silent_in_a_model_that_schedules_nothing(self) -> None:
        """A model with no work packages cannot be asked which planned systems
        have none. Warning anyway would fire on every planned system in every
        model that has not adopted the change layer."""
        model = seeded_model()
        model.entities["work_packages"] = {}
        self.assertNotIn("change.unscheduled", self._codes(model))

    def test_a_work_package_with_no_decision_behind_it_is_reported(self) -> None:
        """Deliberately true of the seeded estate: one package was funded in
        the planning round without going to the board, and a change register
        that could not say so would not be worth keeping."""
        self.assertIn("change.no_decision", self._codes(seeded_model()))

    def test_work_on_a_decision_that_said_no_is_reported(self) -> None:
        """`change.no_decision` is the package that never went to the board;
        this is the one that went, was told to wait, and is scheduled anyway.
        The seeded estate has none: its deferred request has no package
        behind it, which is what deferred means. Pointing a planned package
        at it makes one."""
        self.assertNotIn("change.against_decision", self._codes(seeded_model()))
        model = seeded_model()
        package = next(iter(model.entities["work_packages"].values()))
        package["change_request_id"] = "ACR-2026-030"
        package["status"] = "Planned"
        self.assertIn("change.against_decision", self._codes(model))

    def test_a_retired_package_on_a_deferred_decision_is_not_reported(self) -> None:
        """The work stopped, which is what the decision asked for."""
        model = seeded_model()
        package = next(iter(model.entities["work_packages"].values()))
        package["change_request_id"] = "ACR-2026-030"
        package["status"] = "Retired"
        self.assertNotIn("change.against_decision", self._codes(model))

    def test_a_package_that_ends_before_it_starts_is_an_error(self) -> None:
        model = seeded_model()
        package = model.all_of("work_packages")[0]
        package["start_date"], package["end_date"] = "2026-Q3", "2026-Q1"
        report = validate.run(model)
        self.assertIn("change.dates", {f.code for f in report.errors})

    def test_a_date_that_is_not_a_quarter_is_reported_not_compared(self) -> None:
        """The comparison is a string comparison, which is sound for YYYY-Qn
        and confidently wrong for anything else."""
        model = seeded_model()
        package = model.all_of("work_packages")[0]
        package["start_date"], package["end_date"] = "Q3 2026", "Q1 2026"
        report = validate.run(model)
        codes = {f.code for f in report.findings}
        self.assertIn("change.quarter", codes)
        self.assertNotIn("change.dates", {f.code for f in report.errors})


if __name__ == "__main__":
    unittest.main()
