"""The conventions the cloud providers publish, where this repository meets
them: boundaries drawn the way their provider draws them, named by kind;
flows walked across a diagram, hop by hop, with the steps that are not on
it said so; and the payload the app draws from carrying both.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.palette import Palette, boundary_label, boundary_style  # noqa: E402
from terrane.query import bind, group_kinds, resolve  # noqa: E402
from terrane.render_mermaid import boundary_legend, flows_across, render, render_markdown  # noqa: E402

from _fixture import REPO, seeded_model, seeded_views  # noqa: E402


class TestBoundaryStyles(unittest.TestCase):
    def test_each_provider_draws_its_own_containers(self) -> None:
        self.assertEqual(boundary_style("region", "eu-west-2", "AWS").dash, "dashed")
        self.assertEqual(boundary_style("cloud_account", "prod-lending", "AWS").word, "account")
        self.assertEqual(boundary_style("cloud_account", "azure-cards-prod", "Azure").word, "subscription")
        self.assertEqual(boundary_style("cloud_account", "lending-prod", "GCP").word, "project")
        self.assertEqual(boundary_style("network_zone", "Public", "AWS").key, "public subnet")
        self.assertEqual(boundary_style("network_zone", "Private-Data", "AWS").key, "private subnet")
        self.assertEqual(boundary_style("network_zone", "Private-App", "Azure").key, "Azure subnet")
        self.assertEqual(boundary_style("network_zone", "On-prem", "AWS").key, "on-prem")
        self.assertEqual(boundary_style("cloud_provider", "SaaS", "").dash, "dashed")

    def test_a_boundary_that_is_not_a_cloud_container_keeps_the_depth_tint(self) -> None:
        plain = boundary_style("company_domain", "Lending", "", 2)
        self.assertEqual(plain.key, "")
        self.assertEqual(plain.word, "")
        self.assertEqual(plain.stroke, "#8f9bb5")
        self.assertNotEqual(boundary_style("type", "systems", "", 1).fill, boundary_style("type", "systems", "", 3).fill)

    def test_the_name_carries_the_kind(self) -> None:
        self.assertEqual(boundary_label("region", "eu-west-2", "AWS"), "region eu-west-2")
        self.assertEqual(boundary_label("availability_zone", "eu-west-2a", "AWS"), "zone eu-west-2a")
        self.assertEqual(boundary_label("cloud_account", "azure-cards-prod", "Azure"), "subscription azure-cards-prod")
        self.assertEqual(boundary_label("network_zone", "Public", "AWS"), "Public")
        self.assertEqual(boundary_label("cloud_provider", "AWS", "AWS"), "AWS")
        self.assertEqual(boundary_label("company_domain", "Lending", ""), "Lending")


class TestBoundariesOnViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}
        cls.palette = Palette(cls.model.config.get("palette"))

    def test_the_committed_diagram_says_each_node_s_technology(self) -> None:
        """The second line in brackets is the app's technology line, read
        from the same model, so the two cannot disagree; a node with no
        line keeps a one-line label."""
        text = render(resolve(self.model, self.views["application-landscape"]), self.palette, self.model)
        self.assertIn('SYS_CARDSVC_API["Card Servicing Service<br/>[AKS · Card Servicing Cache]"]', text)
        self.assertIn('SYS_CORE_LEDGER["Core Card Ledger"]', text)
        bare = render(resolve(self.model, self.views["application-landscape"]), self.palette)
        self.assertIn('SYS_CARDSVC_API["Card Servicing Service"]', bare)

    def test_the_onboarding_view_knows_what_each_boundary_is(self) -> None:
        view = bind(self.views["onboarding"], {"product": "PRD-INSTALLMENT-LENDING"}, self.model)
        graph = resolve(self.model, view)
        kinds = group_kinds(graph)
        self.assertEqual(kinds[("AWS",)], ("cloud_provider", "AWS"))
        self.assertEqual(kinds[("AWS", "prod-lending")], ("cloud_account", "AWS"))
        region = next(k for k in kinds if len(k) == 3 and k[0] == "AWS")
        self.assertEqual(kinds[region][0], "region")
        # A SaaS system has no account or region, so its network tier sits
        # at depth two. It is still a network tier, not an account.
        self.assertEqual(kinds[("SaaS", "Edge")], ("network_zone", "SaaS"))
        keys = [b["key"] for b in boundary_legend(graph)]
        self.assertIn("AWS region", keys)
        self.assertIn("AWS account", keys)
        self.assertIn("private subnet", keys)
        self.assertIn("vendor tenancy", keys)
        self.assertNotIn("SaaS tenancy", keys)
        # Each kind once, however many boundaries are that kind.
        self.assertEqual(len(keys), len(set(keys)))

    def test_a_view_with_no_provider_level_infers_it_from_what_is_inside(self) -> None:
        graph = resolve(self.model, self.views["multi-az-deployment"])
        kinds = group_kinds(graph)
        self.assertTrue(kinds)
        self.assertTrue(all(provider == "AWS" for _kind, provider in kinds.values()))
        self.assertIn("availability_zone", {kind for kind, _p in kinds.values()})

    def test_mermaid_names_and_styles_the_boundaries(self) -> None:
        view = bind(self.views["onboarding"], {"product": "PRD-INSTALLMENT-LENDING"}, self.model)
        text = render(resolve(self.model, view), self.palette)
        self.assertIn('["account prod-lending"]', text)
        self.assertIn('["region eu-west-2"]', text)
        self.assertIn('["Edge"]', text)
        self.assertNotIn("tenancy Edge", text)
        self.assertRegex(text, r"classDef boundary\d+ fill:#f5fbfb,stroke:#00a4a6,color:#0b6e70,stroke-dasharray:6 3;")
        # A domain landscape keeps the tint, and says no kind.
        plain = render(resolve(self.model, self.views["application-landscape"]), self.palette)
        self.assertIn("stroke:#8f9bb5", plain)
        self.assertNotIn("stroke-dasharray:6 3", plain.split("classDef boundary")[1] if "classDef boundary" in plain else "")

    def test_the_markdown_lists_the_boundaries_drawn(self) -> None:
        view = bind(self.views["onboarding"], {"product": "PRD-INSTALLMENT-LENDING"}, self.model)
        text = render_markdown(resolve(self.model, view), self.palette, self.model)
        self.assertIn("**Boundaries** are drawn the way their provider draws them.", text)
        self.assertIn("| dashed `#00a4a6` | AWS region |", text)


class TestFlowsAcrossADiagram(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}
        cls.palette = Palette(cls.model.config.get("palette"))

    def test_an_interface_edge_knows_which_interface_it_draws(self) -> None:
        graph = resolve(self.model, self.views["application-landscape"])
        refs = {e.ref for e in graph.edges if e.kind == "interface"}
        self.assertTrue(refs)
        self.assertTrue(all(r.startswith("INT-") for r in refs))
        self.assertTrue(all(e.ref == "" for e in graph.edges if e.kind != "interface"))

    def test_the_flows_with_a_hop_on_the_drawing_are_found_with_their_steps(self) -> None:
        graph = resolve(self.model, self.views["application-landscape"])
        walks = flows_across(graph, self.model)
        self.assertTrue(walks)
        names = [w["name"] for w in walks]
        self.assertIn("Card Authorization", names)
        auth = next(w for w in walks if w["name"] == "Card Authorization")
        self.assertEqual([s["sequence"] for s in auth["steps"]], sorted(s["sequence"] for s in auth["steps"]))
        # The callout number is the step's place in the walk, not the
        # model's ordering value, which counts by tens.
        self.assertEqual([s["n"] for s in auth["steps"]], [1, 2, 3, 4])
        self.assertTrue(all(s["interfaceId"] and s["from"] and s["to"] for s in auth["steps"]))
        self.assertEqual(auth["drawn"], sum(1 for s in auth["steps"] if s["drawn"]))
        # The fullest walks first.
        self.assertEqual([w["drawn"] for w in walks], sorted((w["drawn"] for w in walks), reverse=True))

    def test_a_drawing_with_no_interfaces_has_no_walks(self) -> None:
        graph = resolve(self.model, self.views["capability-map"])
        self.assertEqual(flows_across(graph, self.model), [])

    def test_the_markdown_walks_the_flows(self) -> None:
        text = render_markdown(resolve(self.model, self.views["application-landscape"]), self.palette, self.model)
        self.assertIn("## Flows across this diagram", text)
        self.assertIn("**Card Authorization**", text)
        self.assertRegex(text, r"\n1\. .+ → .+")
        # A step off the diagram is said so, where there is one.
        servicing = bind(self.views["domain-landscape"], {"domain": "Servicing"}, self.model)
        context = render_markdown(resolve(self.model, servicing), self.palette, self.model)
        if "## Flows across this diagram" in context and "not on this diagram" in context:
            self.assertIn("— not on this diagram", context)


class TestThePayload(unittest.TestCase):
    def test_the_app_payload_carries_boundaries_refs_and_flows(self) -> None:
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = REPO
        payload = server_module.api_graph({"view": ["onboarding"], "p_product": ["PRD-INSTALLMENT-LENDING"]}, None)
        groups = [e["data"] for e in payload["elements"] if e["data"].get("isGroup")]
        account = next(g for g in groups if g["kind"] == "cloud_account" and g["provider"] == "AWS")
        self.assertEqual(account["label"], "account prod-lending")
        self.assertEqual(account["bstroke"], "#c7257e")
        self.assertEqual(account["bkey"], "AWS account")
        edges = [e["data"] for e in payload["elements"] if e["data"].get("source")]
        self.assertTrue(any(e["ref"].startswith("INT-") for e in edges if e["kind"] == "interface"))
        self.assertIn("boundaries", payload["legend"])
        self.assertIn("AWS region", [b["key"] for b in payload["legend"]["boundaries"]])
        landscape = server_module.api_graph({"view": ["application-landscape"]}, None)
        self.assertTrue(landscape["flows"])
        self.assertIn("steps", landscape["flows"][0])
        self.assertEqual(landscape["legend"]["boundaries"], [])


if __name__ == "__main__":
    unittest.main()
