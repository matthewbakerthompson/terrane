"""Tests for actors, flows, sequence rendering and the linkage endpoints.

The flow tests exist because of a real defect. A step used to name a *system*,
which let a flow describe a hop that is not in the model; the first diagram
rendered said so out loud ("no interface recorded"). A step now names an
interface, and `test_every_step_is_a_real_interface` is what keeps it that way.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import importer, model as model_module, render_sequence  # noqa: E402
from terrane.query import load_views, resolve  # noqa: E402
from terrane.schema import ENTITY_TYPES, RELATION_TYPES  # noqa: E402

from _fixture import (  # noqa: E402
    EXAMPLE_CSV,
    REPO,
    Sandbox as _Sandbox,
    seeded_model,
    seeded_root,
    setup_shared,
    teardown_shared,
)


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestActors(unittest.TestCase):
    """Who is outside the estate. Without these, no context diagram exists."""

    def test_actors_are_a_first_class_entity(self) -> None:
        self.assertIn("actors", ENTITY_TYPES)
        self.assertEqual(ENTITY_TYPES["actors"].pk, "actor_id")

    def test_the_seeded_model_has_actors_of_several_kinds(self) -> None:
        actors = seeded_model().all_of("actors")
        self.assertGreaterEqual(len(actors), 5)
        kinds = {str(a.get("actor_kind")) for a in actors}
        # A context diagram with only people on it is not a context diagram.
        self.assertIn("Person", kinds)
        self.assertTrue(kinds & {"External system", "Regulator", "Organization"})

    def test_every_actor_link_points_at_a_real_system(self) -> None:
        model = seeded_model()
        for row in model.relation_rows("actor_uses_system"):
            self.assertIsNotNone(
                model.get("actors", str(row["actor_id"])), str(row["actor_id"])
            )
            self.assertIsNotNone(
                model.get("systems", str(row["system_id"])), str(row["system_id"])
            )

    def test_actors_survive_a_csv_round_trip(self) -> None:
        """An entity type the exporter forgets is one the app quietly loses."""
        self.assertTrue((EXAMPLE_CSV / "actors.csv").exists())
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            self.assertEqual(
                {str(a["actor_id"]) for a in model_module.load(root).all_of("actors")},
                {str(a["actor_id"]) for a in seeded_model().all_of("actors")},
            )


class TestContextViews(unittest.TestCase):
    """The basic diagrams the actors made possible."""

    def _graph(self, name: str):
        root = seeded_root()
        views = {v.view_id: v for v in load_views(root / "30_VIEWS")}
        self.assertIn(name, views)
        return resolve(model_module.load(root), views[name])

    def test_system_context_puts_actors_on_the_diagram(self) -> None:
        graph = self._graph("system-context")
        kinds = {node.entity_type for node in graph.nodes}
        self.assertIn("actors", kinds)
        self.assertIn("systems", kinds)
        self.assertTrue(graph.edges)

    def test_actor_channels_separates_internal_from_external(self) -> None:
        graph = self._graph("actor-channels")
        groups = {node.groups[0] for node in graph.nodes if node.groups}
        self.assertGreater(len(groups), 1)

    def test_the_new_basic_views_all_select_something(self) -> None:
        """A view that renders an empty diagram is worse than no view."""
        for name in ("system-context", "actor-channels", "ownership",
                     "technology-stack", "lifecycle-portfolio", "data-lineage"):
            with self.subTest(view=name):
                self.assertTrue(self._graph(name).nodes, name)


class TestSequenceRendering(unittest.TestCase):
    def setUp(self) -> None:
        self.model = seeded_model()
        self.flows = render_sequence.all_flows(self.model)

    def test_the_model_has_flows(self) -> None:
        self.assertGreaterEqual(len(self.flows), 3)

    def test_every_flow_renders_a_sequence_diagram(self) -> None:
        for flow_id in self.flows:
            with self.subTest(flow=flow_id):
                text = render_sequence.render(self.model, flow_id)
                self.assertIn("sequenceDiagram", text)
                self.assertIn("  autonumber", text)
                self.assertNotIn("No steps recorded", text)

    def test_every_step_is_a_real_interface(self) -> None:
        """Regression: a step used to name a system, which let flows invent hops."""
        spec = RELATION_TYPES["flow_step"]
        self.assertEqual(spec.right, "interfaces")
        for row in self.model.relation_rows("flow_step"):
            self.assertIsNotNone(
                self.model.get("interfaces", str(row["interface_id"])),
                str(row["interface_id"]),
            )

    def test_no_diagram_ever_admits_a_missing_hop(self) -> None:
        for flow_id in self.flows:
            self.assertNotIn(
                "no interface recorded", render_sequence.render(self.model, flow_id)
            )

    def test_only_request_response_hops_draw_a_reply(self) -> None:
        """Drawing a response that never happens is how these diagrams lie."""
        for flow_id in self.flows:
            steps = render_sequence.steps_for(self.model, flow_id)
            replies = sum(
                1 for s in steps
                if str(s["interface"].get("integration_style")) == "Request-response"
            )
            text = render_sequence.render(self.model, flow_id)
            self.assertEqual(text.count("-->>"), replies, flow_id)

    def test_a_batch_flow_draws_no_replies(self) -> None:
        batch = [
            f for f in self.flows
            if render_sequence.steps_for(self.model, f)
            and all(
                str(s["interface"].get("integration_style")) != "Request-response"
                for s in render_sequence.steps_for(self.model, f)
            )
        ]
        self.assertTrue(batch, "expected at least one flow with no synchronous hop")
        for flow_id in batch:
            self.assertNotIn("-->>", render_sequence.render(self.model, flow_id))

    def test_participants_are_real_systems_in_first_appearance_order(self) -> None:
        for flow_id in self.flows:
            steps = render_sequence.steps_for(self.model, flow_id)
            order = render_sequence.participants(self.model, steps)
            self.assertEqual(len(order), len(set(order)))
            for system_id in order:
                self.assertIsNotNone(self.model.get("systems", system_id), system_id)
            first = steps[0]["interface"]
            self.assertEqual(order[0], str(first.get("source_system_id")))

    def test_steps_order_numerically_not_alphabetically(self) -> None:
        keys = [render_sequence._sequence_key(v) for v in ("2", "10", "100")]
        self.assertEqual(keys, sorted(keys))

    def test_a_flow_with_no_steps_says_so_rather_than_rendering_nothing(self) -> None:
        model = seeded_model()
        model.entities["flows"]["FLOW-EMPTY"] = {
            "flow_id": "FLOW-EMPTY", "name": "Empty", "_source": "test"
        }
        text = render_sequence.render(model, "FLOW-EMPTY")
        self.assertIn("No steps recorded", text)

    def test_an_unknown_flow_raises(self) -> None:
        with self.assertRaises(KeyError):
            render_sequence.render(self.model, "FLOW-NOPE")

    def test_labels_are_stripped_of_characters_mermaid_breaks_on(self) -> None:
        for flow_id in self.flows:
            for line in render_sequence.render(self.model, flow_id).splitlines():
                if "->>" in line or "-)" in line:
                    self.assertLessEqual(line.count(":"), 1, line)

    def test_markdown_carries_a_row_per_step(self) -> None:
        for flow_id in self.flows:
            text = render_sequence.render_markdown(self.model, flow_id)
            self.assertIn("```mermaid", text)
            steps = render_sequence.steps_for(self.model, flow_id)
            self.assertEqual(len(re.findall(r"^\| \d+ \|", text, re.M)), len(steps))

    def test_rendered_artifacts_are_committed_and_current(self) -> None:
        """Artifacts are committed, so a stale one is a lie in the repository.

        The filename is the flow id verbatim, as the renderer writes it. An
        earlier version of this test lowercased it, which passed on a
        case-insensitive filesystem and failed the moment CI ran on Linux.
        """
        model = model_module.load(REPO)
        for flow_id in render_sequence.all_flows(model):
            mmd = REPO / "70_ARTIFACTS" / "flows" / ("%s.mmd" % flow_id)
            doc = REPO / "70_ARTIFACTS" / "docs" / ("%s.md" % flow_id)
            for path in (mmd, doc):
                with self.subTest(path=path.name):
                    self.assertTrue(path.exists(), str(path))
            self.assertEqual(
                mmd.read_text(encoding="utf-8"), render_sequence.render(model, flow_id)
            )
            # The committed page carries the drawing `terrane render` writes
            # beside the Mermaid, so the comparison asks for it too.
            self.assertEqual(
                doc.read_text(encoding="utf-8"),
                render_sequence.render_markdown(model, flow_id, picture="../svg/%s.svg" % flow_id),
            )


class TestLinkageEndpoints(unittest.TestCase):
    """The app writing relations, and the four guards on it."""

    def _server(self, root: Path):
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        return server_module

    def _seeded_server(self, root: Path):
        importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
        return self._server(root)

    def test_options_only_offer_relations_that_fit_the_entity(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            system = str(model_module.load(root).all_of("systems")[0]["system_id"])
            payload = server.api_relations({"id": [system]}, None)
            self.assertEqual(payload["type"], "systems")
            self.assertTrue(payload["options"])
            for option in payload["options"]:
                spec = RELATION_TYPES[option["relation"]]
                end = spec.left if option["side"] == "left" else spec.right
                self.assertEqual(end, "systems")
                self.assertTrue(option["candidates"])

    def test_an_unknown_entity_is_a_404(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_relations({"id": ["SYS-NOPE"]}, None)
            self.assertEqual(caught.exception.status, 404)

    def test_a_link_is_written_and_reloads_into_the_model(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            model = model_module.load(root)
            existing = {
                (str(r["system_id"]), str(r["capability_id"]))
                for r in model.relation_rows("system_realizes_capability")
            }
            pair = next(
                (str(s["system_id"]), str(c["capability_id"]))
                for s in model.all_of("systems")
                for c in model.all_of("capabilities")
                if (str(s["system_id"]), str(c["capability_id"])) not in existing
            )
            result = server.api_relate(
                None,
                {"relation": "system_realizes_capability", "left": pair[0], "right": pair[1]},
            )
            self.assertEqual(result["errors"], [])
            self.assertTrue(result["path"].endswith(server.APP_RELATIONS))

            reloaded = model_module.load(root)
            self.assertIn(
                pair,
                {
                    (str(r["system_id"]), str(r["capability_id"]))
                    for r in reloaded.relation_rows("system_realizes_capability")
                },
            )

    def test_the_wrong_type_on_an_end_is_refused(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            model = model_module.load(root)
            capability = str(model.all_of("capabilities")[0]["capability_id"])
            with self.assertRaises(server.ApiError) as caught:
                server.api_relate(
                    None,
                    {
                        "relation": "system_realizes_capability",
                        "left": capability,
                        "right": capability,
                    },
                )
            self.assertIn("expects a systems", str(caught.exception))

    def test_a_duplicate_link_is_refused(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            row = model_module.load(root).relation_rows("system_realizes_capability")[0]
            with self.assertRaises(server.ApiError) as caught:
                server.api_relate(
                    None,
                    {
                        "relation": "system_realizes_capability",
                        "left": str(row["system_id"]),
                        "right": str(row["capability_id"]),
                    },
                )
            self.assertEqual(caught.exception.status, 409)

    def test_a_hand_authored_link_cannot_be_removed_by_the_app(self) -> None:
        """The app does not edit a file it did not create."""
        with _Sandbox() as root:
            server = self._seeded_server(root)
            row = model_module.load(root).relation_rows("system_realizes_capability")[0]
            with self.assertRaises(server.ApiError) as caught:
                server.api_unrelate(
                    None,
                    {
                        "relation": "system_realizes_capability",
                        "left": str(row["system_id"]),
                        "right": str(row["capability_id"]),
                    },
                )
            self.assertEqual(caught.exception.status, 409)
            self.assertIn(server.APP_RELATIONS, str(caught.exception))

    def test_what_the_app_wrote_the_app_can_remove(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            model = model_module.load(root)
            existing = {
                (str(r["system_id"]), str(r["capability_id"]))
                for r in model.relation_rows("system_realizes_capability")
            }
            pair = next(
                (str(s["system_id"]), str(c["capability_id"]))
                for s in model.all_of("systems")
                for c in model.all_of("capabilities")
                if (str(s["system_id"]), str(c["capability_id"])) not in existing
            )
            body = {
                "relation": "system_realizes_capability", "left": pair[0], "right": pair[1]
            }
            server.api_relate(None, body)
            self.assertTrue(
                any(
                    link["editable"]
                    for link in server.api_relations({"id": [pair[0]]}, None)["existing"]
                )
            )
            server.api_unrelate(None, body)
            self.assertNotIn(
                pair,
                {
                    (str(r["system_id"]), str(r["capability_id"]))
                    for r in model_module.load(root).relation_rows(
                        "system_realizes_capability"
                    )
                },
            )

    def test_an_unknown_relation_is_refused(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            for call in (server.api_relate, server.api_unrelate):
                with self.assertRaises(server.ApiError):
                    call(None, {"relation": "system_eats_capability", "left": "A", "right": "B"})

    def test_an_end_that_is_not_an_identifier_is_refused(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_relate(
                    None,
                    {
                        "relation": "system_realizes_capability",
                        "left": "../../etc/passwd",
                        "right": "CAP-ANY",
                    },
                )
            self.assertIn("identifiers", str(caught.exception))

    def test_flows_endpoint_resolves_every_hop_to_names(self) -> None:
        with _Sandbox() as root:
            server = self._seeded_server(root)
            flows = server.api_flows(None, None)["flows"]
            self.assertGreaterEqual(len(flows), 3)
            for flow in flows:
                self.assertIn("sequenceDiagram", flow["mermaid"])
                self.assertTrue(flow["steps"])
                for step in flow["steps"]:
                    self.assertTrue(step["from"] and step["to"])
                    # Resolved to a name, not left as the raw identifier.
                    self.assertNotEqual(step["from"], step["fromId"])


class TestFocusViews(unittest.TestCase):
    """The neighborhood view, built on the fly rather than from a view file.

    Focus never writes, so these share one seeded sandbox. Building a fresh one
    per test cost more than every other class in this file put together.
    """

    server = None

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

    def test_a_focus_view_centers_on_the_entity(self) -> None:
        payload = self.server.api_focus({"id": ["SYS-AUTH-SWITCH"], "depth": ["1"]}, None)
        self.assertEqual(payload["focusId"], "SYS-AUTH-SWITCH")
        self.assertEqual(payload["depth"], 1)
        ids = {e["data"]["id"] for e in payload["elements"] if not e["data"].get("isGroup")}
        self.assertIn("SYS-AUTH-SWITCH", ids)
        self.assertGreater(payload["counts"]["nodes"], 1)

    def test_depth_widens_the_neighborhood(self) -> None:
        counts = [
            self.server.api_focus({"id": ["SYS-AUTH-SWITCH"], "depth": [str(d)]}, None)[
                "counts"
            ]["nodes"]
            for d in (1, 2, 3)
        ]
        self.assertEqual(counts, sorted(counts))
        self.assertLess(counts[0], counts[2])

    def test_depth_is_clamped_at_both_ends(self) -> None:
        self.assertEqual(
            self.server.api_focus({"id": ["SYS-AUTH-SWITCH"], "depth": ["0"]}, None)["depth"], 1
        )
        self.assertEqual(
            self.server.api_focus({"id": ["SYS-AUTH-SWITCH"], "depth": ["99"]}, None)["depth"],
            self.server.FOCUS_MAX_DEPTH,
        )

    def test_a_non_numeric_depth_is_refused(self) -> None:
        with self.assertRaises(self.server.ApiError):
            self.server.api_focus({"id": ["SYS-AUTH-SWITCH"], "depth": ["deep"]}, None)

    def test_an_unknown_entity_is_a_404(self) -> None:
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_focus({"id": ["SYS-NOPE"]}, None)
        self.assertEqual(caught.exception.status, 404)

    def test_a_focus_view_hides_no_kind_of_connection(self) -> None:
        """An authored view chooses its edges. An exploratory one must not."""
        offered = {spec["via"] for spec in self.server.FOCUS_EDGES}
        self.assertTrue(set(RELATION_TYPES) <= offered)
        self.assertTrue({"interfaces", "owner", "source_of_truth"} <= offered)

    def test_every_entity_type_has_a_neighborhood(self) -> None:
        """Regression: an org unit drew as a single box with nothing around it.

        `neighbors` walked the relation tables and ignored reference fields, so
        an org unit — whose only link to anything is the `owner_org_id` on the
        records it owns — had no neighbors at all.
        """
        model = seeded_model()
        for type_name in ("systems", "org_units", "data_assets", "actors",
                          "tech_services", "products", "interfaces"):
            records = model.all_of(type_name)
            if not records:
                continue
            entity_id = str(records[0][ENTITY_TYPES[type_name].pk])
            with self.subTest(type=type_name, id=entity_id):
                payload = self.server.api_focus({"id": [entity_id]}, None)
                self.assertGreater(payload["counts"]["nodes"], 1, entity_id)


class TestAdjacency(unittest.TestCase):
    """`neighbors` underpins every focus view and every relation-free expand."""

    def test_neighbors_follow_reference_fields(self) -> None:
        model = seeded_model()
        owners = {
            str(s["owner_org_id"]) for s in model.all_of("systems") if s.get("owner_org_id")
        }
        self.assertTrue(owners, "fixture needs an org unit that owns a system")
        for org_id in sorted(owners):
            owned = {
                str(s["system_id"]) for s in model.all_of("systems")
                if str(s.get("owner_org_id")) == org_id
            }
            with self.subTest(org=org_id):
                self.assertTrue(owned <= model.neighbors(org_id))

    def test_the_index_is_undirected(self) -> None:
        model = seeded_model()
        for entity_id in list(model.entities["systems"])[:5]:
            for other in model.neighbors(entity_id):
                self.assertIn(entity_id, model.neighbors(other))

    def test_nothing_is_its_own_neighbor(self) -> None:
        model = seeded_model()
        for type_name in ENTITY_TYPES:
            for entity_id in model.entities.get(type_name, {}):
                self.assertNotIn(entity_id, model.neighbors(entity_id))

    def test_adding_a_relation_invalidates_the_cached_index(self) -> None:
        """A stale index would quietly hide everything created in the app."""
        with _Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            model = model_module.load(root)
            system = str(model.all_of("systems")[0]["system_id"])
            before = set(model.neighbors(system))  # builds the cache
            capability = next(
                str(c["capability_id"]) for c in model.all_of("capabilities")
                if str(c["capability_id"]) not in before
            )
            model._add_relation(
                "system_realizes_capability",
                {"system_id": system, "capability_id": capability},
                "test",
            )
            self.assertIn(capability, model.neighbors(system))


if __name__ == "__main__":
    unittest.main()
