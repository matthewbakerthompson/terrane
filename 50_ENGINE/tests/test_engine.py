"""Tests for model loading, archetype expansion, views, rendering and drift."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cmdb, exports, model as model_module, validate  # noqa: E402
from terrane.archetype import Archetype, ArchetypeError, expand, parse_archetype  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.query import ViewError, bind, load_views, parse_view, resolve  # noqa: E402
from terrane.render_mermaid import label, node_id, render  # noqa: E402
from terrane.render_structurizr import render_workspace  # noqa: E402
from terrane.scaffold import ScaffoldError, scaffold_entity  # noqa: E402

from _fixture import Sandbox, drawable, seeded_model, seeded_root, seeded_views  # noqa: E402
from _fixture import teardown_shared  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def tearDownModule():  # noqa: N802
    teardown_shared()


def _load():
    """The shipped model is empty; tests read a seeded sandbox instead."""
    return seeded_model()


SIMPLE_ARCHETYPE = {
    "archetype_id": "test-shape",
    "applies_to": "products",
    "parameters": [
        {"name": "slug", "required": True},
        {"name": "tier", "default": "Tier 2"},
    ],
    "provides": {
        "systems": [
            {
                "system_id": "SYS-{slug|upper}-A",
                "name": "{slug} A",
                "status": "Active",
                "owner_org_id": "ORG-PLATFORM-ENG",
                "criticality": "Medium",
                "service_tier": "{tier}",
            },
            {
                "system_id": "SYS-{slug|upper}-B",
                "name": "{slug} B",
                "status": "Active",
                "owner_org_id": "ORG-PLATFORM-ENG",
                "criticality": "Low",
            },
        ],
        "interfaces": [
            {
                "interface_id": "INT-{slug|upper}-AB",
                "name": "A to B",
                "status": "Active",
                "source_system_id": "SYS-{slug|upper}-A",
                "target_system_id": "SYS-{slug|upper}-B",
            }
        ],
    },
    "relations": {
        "product_includes_system": [
            {"product_id": "{product_id}", "system_id": "SYS-{slug|upper}-A"},
            {"product_id": "{product_id}", "system_id": "SYS-{slug|upper}-B"},
        ]
    },
}


class TestArchetypeExpansion(unittest.TestCase):
    def setUp(self) -> None:
        self.archetype: Archetype = parse_archetype(dict(SIMPLE_ARCHETYPE))

    def _instance(self, **extra) -> dict:
        base = {
            "product_id": "PRD-TEST",
            "name": "Test",
            "status": "Active",
            "owner_org_id": "ORG-PLATFORM-ENG",
            "archetype": "test-shape",
            "parameters": {"slug": "demo"},
        }
        base.update(extra)
        return base

    def test_parameters_substitute_into_ids_and_names(self) -> None:
        result = expand(self._instance(), self.archetype, "products")
        ids = [s["system_id"] for s in result.entities["systems"]]
        self.assertEqual(ids, ["SYS-DEMO-A", "SYS-DEMO-B"])

    def test_defaulted_parameter_is_applied(self) -> None:
        result = expand(self._instance(), self.archetype, "products")
        first = result.entities["systems"][0]
        self.assertEqual(first["service_tier"], "Tier 2")

    def test_supplied_parameter_beats_the_default(self) -> None:
        instance = self._instance(parameters={"slug": "demo", "tier": "Tier 1"})
        result = expand(instance, self.archetype, "products")
        self.assertEqual(result.entities["systems"][0]["service_tier"], "Tier 1")

    def test_override_applies_to_one_generated_entity(self) -> None:
        instance = self._instance(overrides={"SYS-DEMO-A": {"criticality": "High"}})
        result = expand(instance, self.archetype, "products")
        by_id = {s["system_id"]: s for s in result.entities["systems"]}
        self.assertEqual(by_id["SYS-DEMO-A"]["criticality"], "High")
        self.assertEqual(by_id["SYS-DEMO-B"]["criticality"], "Low")

    def test_exclude_removes_the_entity_and_everything_pointing_at_it(self) -> None:
        instance = self._instance(exclude=["SYS-DEMO-B"])
        result = expand(instance, self.archetype, "products")
        ids = [s["system_id"] for s in result.entities["systems"]]
        self.assertEqual(ids, ["SYS-DEMO-A"])
        # The interface targeting the excluded system must go too, or the model
        # is left with an edge to something that does not exist.
        self.assertNotIn("interfaces", result.entities)
        self.assertEqual(
            [r["system_id"] for r in result.relations["product_includes_system"]],
            ["SYS-DEMO-A"],
        )
        self.assertEqual(result.dropped_dependents, [("INT-DEMO-AB", "SYS-DEMO-B")])

    def test_exclusion_cascades_until_nothing_more_drops(self) -> None:
        """A dependent of a dependent goes too, wherever the shape lists it.
        The cascade stopped one step out: excluding a product's store dropped
        the data asset mastered in it, and the API's read-write row to that
        asset stayed and dangled. Here an interface names an offered
        interface on the excluded system, and is listed before it, so one
        pass in the shape's order would keep it."""
        system = {"status": "Active", "owner_org_id": "ORG-PLATFORM-ENG", "criticality": "Low"}
        interfaces = [{
            "interface_id": "INT-{slug|upper}-AC", "name": "A to C", "status": "Active",
            "source_system_id": "SYS-{slug|upper}-A", "target_system_id": "SYS-{slug|upper}-C",
            "offered_interface_id": "OI-{slug|upper}-B",
        }]
        offered = [{"offered_interface_id": "OI-{slug|upper}-B", "name": "B API",
                    "system_id": "SYS-{slug|upper}-B"}]
        systems = [dict(system, system_id="SYS-{slug|upper}-%s" % s, name=s) for s in "ABC"]
        for order in (("interfaces", "offered_interfaces"), ("offered_interfaces", "interfaces")):
            with self.subTest(order=order):
                listed = {"interfaces": interfaces, "offered_interfaces": offered}
                provides = {name: listed[name] for name in order}
                provides["systems"] = systems
                provides["data_assets"] = [{"data_asset_id": "DA-{slug|upper}-X", "name": "X"}]
                shape = parse_archetype(dict(SIMPLE_ARCHETYPE, provides=provides, relations={
                    "interface_carries_data": [
                        {"interface_id": "INT-{slug|upper}-AC", "data_asset_id": "DA-{slug|upper}-X"},
                    ],
                }))
                result = expand(self._instance(exclude=["SYS-DEMO-B"]), shape, "products")
                self.assertEqual(
                    [s["system_id"] for s in result.entities["systems"]], ["SYS-DEMO-A", "SYS-DEMO-C"]
                )
                self.assertNotIn("offered_interfaces", result.entities)
                self.assertNotIn("interfaces", result.entities)
                self.assertNotIn("interface_carries_data", result.relations)
                # Each says what it pointed at, the nearest thing that went.
                self.assertEqual(
                    sorted(result.dropped_dependents),
                    [("INT-DEMO-AC", "OI-DEMO-B"), ("OI-DEMO-B", "SYS-DEMO-B")],
                )

    def test_the_loader_says_which_exclusion_a_dependent_went_with(self) -> None:
        """The offered interface was not excluded, so the interface that
        named it is not said to have referenced something excluded."""
        shape = (
            "archetype_id: chain-probe\napplies_to: products\n"
            "parameters:\n  - name: slug\n    required: true\n"
            "provides:\n  systems:\n"
            + "".join('    - system_id: "SYS-{slug|upper}-%s"\n      name: %s\n' % (s, s) for s in "ABC")
            + "  interfaces:\n"
            '    - interface_id: "INT-{slug|upper}-AC"\n      name: A to C\n'
            '      source_system_id: "SYS-{slug|upper}-A"\n      target_system_id: "SYS-{slug|upper}-C"\n'
            '      offered_interface_id: "OI-{slug|upper}-B"\n'
            "  offered_interfaces:\n"
            '    - offered_interface_id: "OI-{slug|upper}-B"\n      name: B API\n'
            '      system_id: "SYS-{slug|upper}-B"\n'
        )
        product = (
            "product_id: PRD-CHAIN\nname: Chain\nstatus: Planned\nowner_org_id: ORG-TECH\n"
            "archetype: chain-probe\nparameters:\n  slug: chain\nexclude:\n  - SYS-CHAIN-B\n"
        )
        with Sandbox() as root:
            (root / "20_ARCHETYPES" / "chain-probe.yaml").write_text(shape, encoding="utf-8")
            (root / "10_MODEL" / "products").mkdir()
            (root / "10_MODEL" / "products" / "PRD-CHAIN.yaml").write_text(product, encoding="utf-8")
            model = model_module.load(root)
        dropped = [w for w in model.warnings if w.startswith("PRD-CHAIN:")]
        self.assertEqual(sorted(dropped), [
            "PRD-CHAIN: INT-CHAIN-AC dropped because it referenced OI-CHAIN-B, which went with "
            "excluded SYS-CHAIN-B",
            "PRD-CHAIN: OI-CHAIN-B dropped because it referenced excluded SYS-CHAIN-B",
        ])

    def test_missing_required_parameter_is_an_error(self) -> None:
        with self.assertRaises(ArchetypeError):
            expand(self._instance(parameters={}), self.archetype, "products")

    def test_undeclared_parameter_is_an_error(self) -> None:
        instance = self._instance(parameters={"slug": "demo", "nope": 1})
        with self.assertRaises(ArchetypeError):
            expand(instance, self.archetype, "products")

    def test_override_of_something_not_produced_is_an_error(self) -> None:
        instance = self._instance(overrides={"SYS-TYPO": {"criticality": "High"}})
        with self.assertRaises(ArchetypeError):
            expand(instance, self.archetype, "products")

    def test_exclude_of_something_not_produced_is_an_error(self) -> None:
        with self.assertRaises(ArchetypeError):
            expand(self._instance(exclude=["SYS-TYPO"]), self.archetype, "products")

    def test_generated_entities_record_their_origin(self) -> None:
        result = expand(self._instance(), self.archetype, "products")
        for record in result.entities["systems"]:
            self.assertEqual(record["archetype_instance"], "PRD-TEST")
            self.assertEqual(record["archetype"], "test-shape")


class TestSeededModel(unittest.TestCase):
    """A model seeded from 90_EXAMPLE must load and pass its own gates."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = _load()
        cls.views = seeded_views()

    def test_model_loads(self) -> None:
        self.assertGreater(len(self.model.all_of("systems")), 10)
        self.assertGreater(len(self.model.all_of("interfaces")), 10)

    def test_validation_reports_no_errors(self) -> None:
        report = validate.run(self.model, self.views)
        self.assertEqual(
            [f.format() for f in report.errors], [], "a seeded model must be clean"
        )

    def test_a_subject_view_with_nothing_to_draw_is_a_warning_not_a_fault(self) -> None:
        """The seed's products carry no `archetype`, so the onboarding view
        selects nothing here. That is an empty selection, reported as one; it
        used to be bound to nothing and reported as unresolvable."""
        report = validate.run(self.model, self.views)
        empties = [f for f in report.warnings if f.code == "view.no_subjects"]
        self.assertTrue(any("onboarding" in f.message for f in empties))
        self.assertFalse(any(f.code == "view.unresolvable" for f in report.errors))

    def test_ids_are_unique_across_entity_types(self) -> None:
        seen = set()
        for type_name, records in self.model.entities.items():
            for entity_id in records:
                self.assertNotIn(entity_id, seen, "%s reuses id %s" % (type_name, entity_id))
                seen.add(entity_id)

    def test_products_reference_their_systems(self) -> None:
        """A seeded model is import-built and therefore flat.

        Archetype expansion is covered by TestArchetypeExpansion against a
        constructed archetype; here the invariant is that products actually
        gather systems, however they were authored.
        """
        rows = self.model.relation_rows("product_includes_system")
        self.assertGreater(len(rows), len(self.model.all_of("products")))
        for row in rows:
            self.assertIsNotNone(self.model.get("systems", str(row["system_id"])))

    def test_every_view_resolves(self) -> None:
        for view in self.views:
            with self.subTest(view=view.view_id):
                bound = drawable(self.model, view)
                if bound is None:
                    continue  # nothing in the seed for this subject view
                graph = resolve(self.model, bound)
                self.assertGreater(len(graph.nodes), 0)


class TestViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = _load()

    def test_scope_filter_selects_by_field(self) -> None:
        view = parse_view(
            {
                "view_id": "t",
                "scope": {"include": [{"type": "systems", "where": {"status": "Planned"}}]},
            }
        )
        graph = resolve(self.model, view)
        self.assertTrue(all(n.record["status"] == "Planned" for n in graph.nodes))

    def test_new_system_appears_without_touching_the_view(self) -> None:
        """The whole point of views-as-queries."""
        view = parse_view(
            {
                "view_id": "t",
                "scope": {"include": [{"type": "systems", "where": {"status": "Active"}}]},
            }
        )
        before = len(resolve(self.model, view).nodes)
        self.model.entities["systems"]["SYS-BRAND-NEW"] = {
            "system_id": "SYS-BRAND-NEW",
            "name": "Brand New Thing",
            "status": "Active",
            "owner_org_id": "ORG-PLATFORM-ENG",
            "criticality": "Low",
            "_type": "systems",
            "_source_file": "<test>",
        }
        after = len(resolve(self.model, view).nodes)
        self.assertEqual(after, before + 1)
        del self.model.entities["systems"]["SYS-BRAND-NEW"]

    def test_tags_any_matches(self) -> None:
        view = parse_view(
            {
                "view_id": "t",
                "scope": {"include": [{"type": "systems", "where": {"tags_any": ["vendor"]}}]},
            }
        )
        graph = resolve(self.model, view)
        self.assertGreater(len(graph.nodes), 0)
        for node in graph.nodes:
            self.assertIn("vendor", self.model.tags(node.record))

    def test_not_operator_excludes(self) -> None:
        view = parse_view(
            {
                "view_id": "t",
                "scope": {
                    "include": [
                        {"type": "systems", "where": {"status": {"not": ["Planned"]}}}
                    ]
                },
            }
        )
        graph = resolve(self.model, view)
        self.assertTrue(all(n.record["status"] != "Planned" for n in graph.nodes))

    def _systems_where(self, where: dict) -> set:
        view = parse_view(
            {"view_id": "t", "scope": {"include": [{"type": "systems", "where": where}]}}
        )
        return {n.record["system_id"] for n in resolve(self.model, view).nodes}

    def test_has_any_selects_only_what_the_relation_reaches(self) -> None:
        governed = {
            row["system_id"]
            for row in self.model.relation_rows("system_governed_by_control")
        }
        selected = self._systems_where({"has_any": ["system_governed_by_control"]})
        self.assertTrue(selected)
        self.assertEqual(selected, governed & selected)

    def test_has_none_is_the_complement_of_has_any(self) -> None:
        """The pair has to partition the type, or a gap report built on
        `has_none` would quietly disagree with the diagram built on
        `has_any`."""
        relation = "system_governed_by_control"
        every = {s["system_id"] for s in self.model.all_of("systems")}
        with_it = self._systems_where({"has_any": [relation]})
        without = self._systems_where({"has_none": [relation]})
        self.assertEqual(with_it | without, every)
        self.assertEqual(with_it & without, set())

    def test_has_all_needs_every_relation_named(self) -> None:
        both = ["system_governed_by_control", "system_subject_to_policy"]
        self.assertEqual(
            self._systems_where({"has_all": both}),
            self._systems_where({"has_any": [both[0]]})
            & self._systems_where({"has_any": [both[1]]}),
        )

    def test_a_has_filter_follows_a_reference_field_too(self) -> None:
        """`has_` accepts anything `expand` accepts, which includes a plain
        reference field like a control's `policy_id`."""
        view = parse_view(
            {
                "view_id": "t",
                "scope": {
                    "include": [{"type": "controls", "where": {"has_any": ["policy_id"]}}]
                },
            }
        )
        selected = {n.record["control_id"] for n in resolve(self.model, view).nodes}
        self.assertTrue(selected)
        for control in self.model.all_of("controls"):
            if control.get("policy_id"):
                self.assertIn(control["control_id"], selected)

    def test_a_misspelled_relation_in_a_has_filter_is_refused(self) -> None:
        """Silently matching nothing is how a filter on a typo passes review."""
        with self.assertRaises(ViewError):
            self._systems_where({"has_any": ["system_governed_by_contrl"]})

    def test_expansion_pulls_in_neighbors(self) -> None:
        narrow = parse_view(
            {
                "view_id": "t",
                "scope": {"include": [{"type": "systems", "where": {"id_in": ["SYS-CORE-LEDGER"]}}]},
            }
        )
        wide = parse_view(
            {
                "view_id": "t",
                "scope": {
                    "include": [{"type": "systems", "where": {"id_in": ["SYS-CORE-LEDGER"]}}],
                    "expand": [{"relation": "interfaces", "depth": 1, "types": ["systems"]}],
                },
            }
        )
        self.assertEqual(len(resolve(self.model, narrow).nodes), 1)
        self.assertGreater(len(resolve(self.model, wide).nodes), 1)

    def test_max_nodes_truncates_and_says_so(self) -> None:
        view = parse_view(
            {
                "view_id": "t",
                "scope": {"include": [{"type": "systems"}]},
                "limits": {"max_nodes": 3},
            }
        )
        graph = resolve(self.model, view)
        self.assertEqual(len(graph.nodes), 3)
        self.assertTrue(any("max_nodes" in note for note in graph.notes))
        whole = resolve(self.model, view._replace(limits={}))
        self.assertEqual(graph.cut, len(whole.nodes) - 3)
        # The scope names every system, so all three kept are of what it
        # named; this said "showing the 3 the scope names and the first 0
        # of the rest".
        self.assertIn("showing the first 3 of the %d the scope names" % len(whole.nodes), graph.notes[0])

    def test_a_report_is_never_cut_and_says_when_it_passes_its_limit(self) -> None:
        """A table has no page to fit. Cut at its sixty, the capability
        realization report kept the estate's systems and the first five
        capabilities by id, and so listed five of its rows. Past its limit a
        report is listed whole, and the limit says only that the scope may
        have stopped filtering."""
        view = parse_view(
            {
                "view_id": "t",
                "kind": "report",
                "scope": {"include": [{"type": "systems"}]},
                "limits": {"max_nodes": 3},
            }
        )
        graph = resolve(self.model, view)
        whole = resolve(self.model, view._replace(limits={}))
        self.assertGreater(len(whole.nodes), 3)
        self.assertEqual([n.key for n in graph.nodes], [n.key for n in whole.nodes])
        self.assertEqual(graph.cut, 0)
        self.assertTrue(any("a report is listed whole" in note for note in graph.notes), graph.notes)
        codes = [f.code for f in validate.run(self.model, [view]).warnings]
        self.assertIn("view.past_limit", codes)
        self.assertNotIn("view.truncated", codes)
        # Within its limit it says nothing.
        roomy = view._replace(limits={"max_nodes": len(whole.nodes)})
        self.assertFalse(resolve(self.model, roomy).notes)
        self.assertNotIn("view.past_limit", [f.code for f in validate.run(self.model, [roomy]).warnings])

    def test_empty_selection_is_an_error(self) -> None:
        view = parse_view(
            {
                "view_id": "t",
                "scope": {"include": [{"type": "systems", "where": {"status": "Nonexistent"}}]},
            }
        )
        with self.assertRaises(ViewError):
            resolve(self.model, view)

    def test_unknown_edge_relation_is_an_error(self) -> None:
        view = parse_view(
            {
                "view_id": "t",
                "scope": {"include": [{"type": "systems"}]},
                "edges": [{"via": "not_a_relation"}],
            }
        )
        with self.assertRaises(ViewError):
            resolve(self.model, view)


class TestRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = _load()
        cls.views = seeded_views()
        cls.palette = Palette()

    def test_node_ids_are_mermaid_safe(self) -> None:
        self.assertEqual(node_id("SYS-CARDSVC-WEB"), "SYS_CARDSVC_WEB")
        self.assertEqual(node_id("9lives"), "n_9lives")

    def test_labels_escape_characters_that_break_mermaid(self) -> None:
        self.assertNotIn('"', label('a "quoted" name'))
        self.assertNotIn("|", label("a|b"))
        self.assertNotIn("<", label("<script>"))

    def test_comment_marker_survives_formatting(self) -> None:
        """A `%%` eaten by %-formatting would break the whole diagram."""
        graph = resolve(self.model, self.views[0])
        output = render(graph, self.palette)
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("%") and not stripped.startswith("%%"):
                self.fail("single-percent line would not parse as Mermaid: %r" % line)

    def test_every_edge_endpoint_is_a_declared_node(self) -> None:
        for view in self.views:
            bound = drawable(self.model, view)
            if bound is None:
                continue  # nothing in the seed for this subject view
            graph = resolve(self.model, bound)
            declared = {node_id(n.key) for n in graph.nodes}
            for edge in graph.edges:
                with self.subTest(view=view.view_id, edge=edge):
                    self.assertIn(node_id(edge.source), declared)
                    self.assertIn(node_id(edge.target), declared)

    def test_subgraphs_are_balanced(self) -> None:
        for view in self.views:
            bound = drawable(self.model, view)
            if bound is None:
                continue  # nothing in the seed for this subject view
            output = render(resolve(self.model, bound), self.palette)
            opens = sum(1 for l in output.splitlines() if l.strip().startswith("subgraph "))
            closes = sum(1 for l in output.splitlines() if l.strip() == "end")
            self.assertEqual(opens, closes, "unbalanced subgraphs in %s" % view.view_id)

    def test_structurizr_workspace_has_balanced_braces(self) -> None:
        graphs = [
            resolve(self.model, bound)
            for bound in (drawable(self.model, v) for v in self.views if "structurizr" in v.renderers)
            if bound is not None  # nothing in the seed for a subject view yields None
        ]
        dsl = render_workspace(self.model, graphs, self.palette)
        self.assertEqual(dsl.count("{"), dsl.count("}"))
        self.assertIn("workspace ", dsl)


class TestExports(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = _load()

    def test_csv_export_writes_entity_and_relation_tables(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            written = exports.export_csv(self.model, Path(tmp))
            names = {p.name for p in written}
            self.assertIn("systems.csv", names)
            self.assertIn("system_uses_tech_service.csv", names)
            text = (Path(tmp) / "systems.csv").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("system_id,"))
            self.assertNotIn("_source_file", text)

    def test_backstage_export_omits_internal_fields(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            written = exports.export_backstage(self.model, Path(tmp))
            text = written[0].read_text(encoding="utf-8")
            self.assertIn("backstage.io/v1alpha1", text)
            self.assertNotIn("_source_file", text)


class TestCmdbReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = _load()
        cls.rows = cmdb.read_ci_export(
            REPO / "60_SOURCES" / "servicenow" / "sample_cmdb_ci_export.csv"
        )
        cls.field_sot = cmdb.load_field_sot(
            REPO / "60_SOURCES" / "servicenow" / "field_sot.yaml"
        )

    def test_normalize_name_strips_noise(self) -> None:
        self.assertEqual(
            cmdb.normalize_name("Collections Workspace Web App"),
            cmdb.normalize_name("Collections Workspace Web"),
        )

    def test_exact_sys_id_link_is_reported_as_linked(self) -> None:
        result = cmdb.reconcile(self.model, self.rows, self.field_sot)
        linked = [r for r in result.rows if r.confidence == "linked"]
        self.assertGreater(len(linked), 0)

    def test_fuzzy_match_is_a_candidate_not_a_match(self) -> None:
        result = cmdb.reconcile(self.model, self.rows, self.field_sot)
        candidates = [r for r in result.rows if r.category == "CANDIDATE_MATCH"]
        self.assertGreater(len(candidates), 0)
        for row in candidates:
            self.assertIn("Not applied", row.note)

    def test_junk_cis_land_in_cmdb_only(self) -> None:
        result = cmdb.reconcile(self.model, self.rows, self.field_sot)
        names = {r.cmdb_name for r in result.rows if r.category == "CMDB_ONLY"}
        self.assertIn("PRINTSRV07", names)

    def test_servicenow_vocabulary_is_translated_before_comparison(self) -> None:
        result = cmdb.reconcile(self.model, self.rows, self.field_sot)
        # `1` means operational; it must not be reported as a status mismatch.
        status_mismatches = [
            r for r in result.rows if r.category == "ATTR_MISMATCH" and r.field == "status"
        ]
        self.assertEqual(status_mismatches, [])

    def test_reconciliation_does_not_mutate_the_model(self) -> None:
        before = {s["system_id"]: dict(s) for s in self.model.all_of("systems")}
        cmdb.reconcile(self.model, self.rows, self.field_sot)
        after = {s["system_id"]: dict(s) for s in self.model.all_of("systems")}
        self.assertEqual(before, after)


class TestScaffold(unittest.TestCase):
    def test_scaffold_includes_every_required_field(self) -> None:
        text = scaffold_entity("systems", "SYS-EXAMPLE", {"name": "Example"})
        for field in ("system_id", "name", "status", "owner_org_id", "criticality"):
            self.assertIn(field, text)

    def test_scaffold_rejects_an_existing_id(self) -> None:
        with self.assertRaises(ScaffoldError):
            scaffold_entity("systems", "SYS-CORE-LEDGER", {}, _load())

    def test_scaffold_rejects_unknown_fields(self) -> None:
        with self.assertRaises(ScaffoldError):
            scaffold_entity("systems", "SYS-EXAMPLE", {"nonsense": "x"})


if __name__ == "__main__":
    unittest.main()


class TestNestedBoundaries(unittest.TestCase):
    """Multi-level `group_by`, which is what infrastructure views need."""

    def _node(self, **fields):
        record = {"_type": "systems", "system_id": "SYS-X", "name": "X"}
        record.update(fields)
        return record

    def test_single_string_group_by_still_works(self) -> None:
        view = parse_view({"view_id": "t", "group_by": "company_domain",
                           "scope": {"include": [{"type": "systems"}]}})
        self.assertEqual(list(view.group_by), ["company_domain"])

    def test_levels_nest_outermost_first(self) -> None:
        from terrane.query import _groups_of
        path = _groups_of(
            self._node(cloud_provider="AWS", cloud_account="prod-x",
                       region="eu-west-2", network_zone="Private-App"),
            ["cloud_provider", "cloud_account", "region", "network_zone"],
        )
        self.assertEqual(path, ("AWS", "prod-x", "eu-west-2", "Private-App"))

    def test_unset_levels_collapse_rather_than_drawing_empty_boxes(self) -> None:
        from terrane.query import _groups_of
        # A SaaS third party has no account and no region.
        path = _groups_of(
            self._node(cloud_provider="SaaS", network_zone="Edge"),
            ["cloud_provider", "cloud_account", "region", "network_zone"],
        )
        self.assertEqual(path, ("SaaS", "Edge"))

    def test_repeated_levels_collapse_to_one(self) -> None:
        from terrane.query import _groups_of
        path = _groups_of(
            self._node(cloud_provider="On-prem", network_zone="On-prem"),
            ["cloud_provider", "cloud_account", "region", "network_zone"],
        )
        self.assertEqual(path, ("On-prem",))

    def test_group_paths_lists_parents_before_children(self) -> None:
        from terrane.query import Node, group_paths
        nodes = [
            Node("a", "A", "systems", (0, "a"), ("AWS", "acct", "eu-west-2"), "x", {}),
            Node("b", "B", "systems", (0, "b"), ("AWS", "acct"), "x", {}),
        ]
        paths = group_paths(nodes)
        for i, path in enumerate(paths):
            if len(path) > 1:
                self.assertIn(path[:-1], paths[:i], "parent must precede child")

    def test_boundary_ids_do_not_collide_across_branches(self) -> None:
        """Two `Private-App` zones in different accounts are different boxes."""
        from terrane.render_mermaid import group_id
        a = group_id(("AWS", "prod-a", "eu-west-2", "Private-App"))
        b = group_id(("AWS", "prod-b", "eu-west-2", "Private-App"))
        self.assertNotEqual(a, b)

    def test_shipped_infrastructure_view_nests(self) -> None:
        """Bound by hand: the seed's products are plain rows with no
        `archetype`, so `render_for` selects nothing there, and the view
        is what is under test, not the selection."""
        model = _load()
        views = {v.view_id: v for v in seeded_views()}
        graph = resolve(model, bind(views["onboarding"], {"product": "PRD-INSTALLMENT-LENDING"}, model))
        depths = {len(p) for p in graph.groups}
        self.assertGreaterEqual(max(depths), 3, "expected genuinely nested boundaries")
        self.assertTrue(all(n.groups for n in graph.nodes if n.record.get("cloud_provider")))

    def test_nested_subgraphs_are_balanced_in_mermaid(self) -> None:
        model = _load()
        views = {v.view_id: v for v in seeded_views()}
        bound = bind(views["onboarding"], {"product": "PRD-INSTALLMENT-LENDING"}, model)
        output = render(resolve(model, bound), Palette())
        opens = sum(1 for l in output.splitlines() if l.strip().startswith("subgraph "))
        closes = sum(1 for l in output.splitlines() if l.strip() == "end")
        self.assertEqual(opens, closes)
        self.assertNotIn("Unassigned", output)


class TestInfrastructureTopology(unittest.TestCase):
    """The traditional infrastructure views and what they rest on."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = _load()
        cls.views = {v.view_id: v for v in seeded_views()}

    def test_infrastructure_connects_to_infrastructure(self) -> None:
        """Without a tech-service-to-tech-service relation there is no
        topology diagram: the model could say what a system runs on but not
        how a VPC reaches a data center."""
        rows = self.model.relation_rows("tech_service_connects_to")
        self.assertGreater(len(rows), 10)
        for row in rows:
            for column in ("from_tech_service_id", "to_tech_service_id"):
                self.assertIsNotNone(
                    self.model.get("tech_services", str(row[column])),
                    "%s points at something that is not a technology service" % column,
                )

    def test_hybrid_edge_reaches_the_data_center(self) -> None:
        """A cloud topology that cannot show the path back on-premise is
        missing the expensive half of every onboarding."""
        reaching = {
            str(r["from_tech_service_id"])
            for r in self.model.relation_rows("tech_service_connects_to")
            if r["to_tech_service_id"] == "TS-ONPREM-DC"
        }
        self.assertIn("TS-NET-DX", reaching)
        self.assertIn("TS-NET-VPN", reaching, "a single hybrid path is not a topology")

    def test_every_workload_subnet_is_paired_across_zones(self) -> None:
        """Multi-AZ is a claim each system makes in `resilience`. The subnets
        have to back it up, or the claim is decoration."""
        by_tier = {}
        for record in self.model.all_of("tech_services"):
            if record.get("service_name") != "Subnet":
                continue
            key = (record.get("cloud_account"), record.get("network_zone"))
            by_tier.setdefault(key, set()).add(record.get("availability_zone"))
        self.assertTrue(by_tier, "expected subnets in the model")
        for key, zones in by_tier.items():
            self.assertGreaterEqual(
                len(zones), 2, "%s exists in only one availability zone: %s" % (key, zones)
            )

    def test_topology_view_holds_only_fabric(self) -> None:
        """Scoped on a tag, not on `service_category: Network`, which also
        catches managed services that have no account and floated loose."""
        graph = resolve(self.model, self.views["network-topology"])
        for node in graph.nodes:
            self.assertIn(
                "network-fabric", self.model.tags(node.record),
                "%s is on the topology diagram but is not tagged fabric" % node.key,
            )

    def test_every_topology_node_sits_inside_a_boundary(self) -> None:
        """A node with no boundary path renders in a stray unlabeled box."""
        for view_id in ("network-topology", "multi-az-deployment", "dr-topology"):
            graph = resolve(self.model, self.views[view_id])
            for node in graph.nodes:
                self.assertTrue(
                    node.groups, "%s in %s has no placement" % (node.key, view_id)
                )

    def test_tiered_view_separates_the_zones(self) -> None:
        graph = resolve(self.model, self.views["tiered-architecture"])
        tiers = {g[0] for g in graph.groups}
        for expected in ("Private-App", "Private-Data", "On-prem"):
            self.assertIn(expected, tiers)


class TestPalette(unittest.TestCase):
    """Two properties, both of which were once wrong.

    Colors used to be handed out in encounter order from a palette shared by
    every view, so a box's color depended on which diagrams had been drawn
    before it: `terrane render` and the app disagreed about the same view, and
    inserting a view recolored the ones after it.
    """

    def setUp(self) -> None:
        self.model = seeded_model()
        self.views = seeded_views()

    def _keys(self, view_id: str):
        view = next(v for v in self.views if v.view_id == view_id)
        return {node.style_key for node in resolve(self.model, view).nodes}

    def test_a_value_is_the_same_color_in_two_fresh_palettes(self) -> None:
        first, second = Palette(), Palette()
        for key in ("Person", "Edge", "AWS", "Restricted", "Some Vendor Ltd"):
            self.assertEqual(first.swatch(key), second.swatch(key), key)

    def test_encounter_order_does_not_change_the_answer(self) -> None:
        keys = sorted(self._keys("technology-stack"))
        forward, backward = Palette(), Palette()
        forward.assign(keys)
        backward.assign(list(reversed(keys)))
        for key in keys:
            self.assertEqual(forward.swatch(key), backward.swatch(key), key)

    def test_one_shared_palette_agrees_with_a_fresh_one_per_view(self) -> None:
        """`terrane render` uses one palette for everything; the app uses one per
        request. If those disagreed, the wiki and the screen would too."""
        shared = Palette()
        for view_id in [v.view_id for v in self.views]:
            try:
                keys = self._keys(view_id)
            except ViewError:
                continue
            solo = Palette()
            shared.assign(keys)
            solo.assign(keys)
            for key in keys:
                self.assertEqual(shared.swatch(key), solo.swatch(key), (view_id, key))

    def test_no_view_puts_two_categories_on_one_color(self) -> None:
        """A legend with two rows the same color is not a legend."""
        for view_id in [v.view_id for v in self.views]:
            try:
                keys = self._keys(view_id)
            except ViewError:
                continue
            palette = Palette()
            palette.assign(keys)
            strokes = [palette.swatch(key).stroke for key in sorted(keys)]
            with self.subTest(view=view_id):
                self.assertEqual(len(strokes), len(set(strokes)), sorted(keys))

    def test_every_enumerated_value_has_a_deliberate_color(self) -> None:
        from terrane import schema

        enums = (
            schema.STATUS, schema.CRITICALITY, schema.DOMAINS, schema.LAYERS,
            schema.ABSTRACTION, schema.CLASSIFICATION, schema.ENVIRONMENT,
            schema.TIER, schema.INTEGRATION_STYLES, schema.ACTOR_KINDS,
            schema.CLOUD_PROVIDERS, schema.NETWORK_ZONES, schema.RESILIENCE,
        )
        palette = Palette()
        for values in enums:
            with self.subTest(values=values[0]):
                for value in values:
                    self.assertIn(value, palette.named, value)
                # Distinct within the enumeration, which is what a view colors by.
                strokes = [palette.named[v].stroke for v in values]
                self.assertEqual(len(strokes), len(set(strokes)), values)

    def test_an_override_in_model_yaml_wins(self) -> None:
        palette = Palette({"High": {"fill": "#000000", "stroke": "#111111"}})
        self.assertEqual(palette.swatch("High").stroke, "#111111")


class TestViewKinds(unittest.TestCase):
    """Three kinds, and the kind has to mean something.

    Six of the twenty-six views answer a question with a set rather than
    showing a structure. Drawing a set as a graph adds nothing except the
    suggestion that the lines between the rows mean something.
    """

    def setUp(self) -> None:
        self.model = seeded_model()
        self.views = seeded_views()

    def test_every_view_declares_a_kind(self) -> None:
        from terrane.query import VIEW_KINDS

        for view in self.views:
            with self.subTest(view=view.view_id):
                self.assertIn(view.kind, VIEW_KINDS)

    def test_an_undeclared_view_is_guessed_rather_than_assumed(self) -> None:
        """Defaulting to `diagram` is how six of them ended up drawn as graphs."""
        from terrane.query import parse_view

        base = {"view_id": "x", "scope": {"include": [{"type": "systems"}]}}
        self.assertEqual(parse_view(dict(base, group_by="type")).kind, "report")
        self.assertEqual(parse_view(dict(base)).kind, "map")
        self.assertEqual(
            parse_view(dict(base, edges=[{"via": "interfaces"}])).kind, "diagram"
        )

    def test_a_declared_kind_wins(self) -> None:
        from terrane.query import parse_view

        view = parse_view({"view_id": "x", "kind": "map", "group_by": "type",
                           "scope": {"include": [{"type": "systems"}]}})
        self.assertEqual(view.kind, "map")

    def test_a_report_renders_as_a_table_not_a_graph(self) -> None:
        from terrane.render_mermaid import render_table

        reports = [v for v in self.views if v.kind == "report"]
        self.assertTrue(reports, "the fixture should have some reports")
        for view in reports:
            with self.subTest(view=view.view_id):
                text = render_table(resolve(self.model, view))
                self.assertIn("|---", text)
                self.assertNotIn("flowchart", text)
                self.assertNotIn("```mermaid", text)

    def test_a_report_table_has_a_row_per_relationship(self) -> None:
        from terrane.matrix import matrix_of
        from terrane.render_mermaid import render_table

        for view in [v for v in self.views if v.kind == "report"]:
            graph = resolve(self.model, view)
            # A report that asks for a grid is a row per thing down the side,
            # not per relationship; test_landscapes holds the frameworks one.
            if not graph.edges or matrix_of(graph) is not None:
                continue
            rows = [
                line for line in render_table(graph).splitlines()
                if line.startswith("| ") and not line.startswith("| From")
            ]
            with self.subTest(view=view.view_id):
                self.assertEqual(len(rows), len(graph.edges))

    def test_no_report_is_committed_as_a_diagram(self) -> None:
        """A stale .mmd for a report is the old rendering left behind."""
        for view in [v for v in self.views if v.kind == "report"]:
            path = REPO / "70_ARTIFACTS" / "mermaid" / ("%s.mmd" % view.view_id)
            with self.subTest(view=view.view_id):
                self.assertFalse(path.exists(), str(path))

    def test_an_oversized_diagram_says_so(self) -> None:
        """Past a page it has stopped being a diagram, and that is a modeling
        finding rather than a layout problem."""
        from terrane.query import DIAGRAM_MAX_NODES, parse_view

        graph = resolve(self.model, parse_view({
            "view_id": "too-big", "kind": "diagram",
            "scope": {"include": [{"type": "capabilities"}]},
            "edges": [{"via": "interfaces"}],
        }))
        self.assertGreater(len(graph.nodes), DIAGRAM_MAX_NODES)
        self.assertTrue(
            any("become a landscape" in note for note in graph.notes), graph.notes
        )

    def test_a_map_is_allowed_to_be_large(self) -> None:
        from terrane.query import parse_view

        graph = resolve(self.model, parse_view({
            "view_id": "big-map", "kind": "map",
            "scope": {"include": [{"type": "capabilities"}]},
        }))
        self.assertFalse(any("become a landscape" in n for n in graph.notes))


class TestParameterizedViews(unittest.TestCase):
    """A view that takes a subject.

    Every other view here is about the whole estate, so "show me the
    architecture of the authorization switch" — the most common thing an
    architect is asked for — had no answer.
    """

    def setUp(self) -> None:
        self.model = seeded_model()
        self.views = seeded_views()
        self.view = next(v for v in self.views if v.view_id == "system-architecture")

    def test_it_declares_what_it_needs(self) -> None:
        self.assertEqual([p.name for p in self.view.parameters], ["system"])
        self.assertEqual(self.view.parameters[0].type, "systems")
        self.assertTrue(self.view.parameters[0].required)

    def test_resolving_it_unbound_is_refused(self) -> None:
        """Unbound it would match a scope full of tokens, select nothing, and
        look like an empty model rather than a missing argument."""
        from terrane.query import ViewError

        with self.assertRaises(ViewError) as caught:
            resolve(self.model, self.view)
        self.assertIn("has not been given", str(caught.exception))

    def test_binding_draws_the_subject(self) -> None:
        from terrane.query import bind

        graph = resolve(self.model, bind(self.view, {"system": "SYS-AUTH-SWITCH"}, self.model))
        self.assertIn("SYS-AUTH-SWITCH", {n.key for n in graph.nodes})
        self.assertGreater(len(graph.edges), 0)

    def test_the_title_uses_the_name_not_the_id(self) -> None:
        """A diagram titled SYS-AUTH-SWITCH is a diagram nobody wants."""
        from terrane.query import bind

        bound = bind(self.view, {"system": "SYS-AUTH-SWITCH"}, self.model)
        record = self.model.get("systems", "SYS-AUTH-SWITCH")
        self.assertIn(record["name"], bound.title)
        self.assertNotIn("SYS-AUTH-SWITCH", bound.title)

    def test_a_value_of_the_wrong_type_is_refused(self) -> None:
        from terrane.query import ViewError, bind

        capability = str(self.model.all_of("capabilities")[0]["capability_id"])
        with self.assertRaises(ViewError):
            bind(self.view, {"system": capability}, self.model)

    def test_a_missing_value_is_refused(self) -> None:
        from terrane.query import ViewError, bind

        with self.assertRaises(ViewError):
            bind(self.view, {}, self.model)

    def test_render_targets_come_from_the_model(self) -> None:
        """A high-criticality system with no architecture diagram is the gap
        this closes, so the selection is a query rather than a kept list."""
        from terrane.query import render_targets

        targets = render_targets(self.model, self.view)
        self.assertTrue(targets)
        expected = {
            str(s["system_id"]) for s in self.model.all_of("systems")
            if s.get("criticality") == "High" and s.get("status") in ("Active", "Planned")
        }
        self.assertEqual({value for _name, value in targets}, expected)

    def test_every_target_draws_something(self) -> None:
        from terrane.query import bind, render_targets

        for parameter, value in render_targets(self.model, self.view):
            with self.subTest(subject=value):
                graph = resolve(self.model, bind(self.view, {parameter: value}, self.model))
                self.assertGreater(len(graph.nodes), 1, value)

    def test_a_view_without_parameters_is_untouched(self) -> None:
        from terrane.query import bind, render_targets

        plain = next(v for v in self.views if not v.parameters)
        self.assertIs(bind(plain, {"anything": "x"}), plain)
        self.assertEqual(render_targets(self.model, plain), [])
