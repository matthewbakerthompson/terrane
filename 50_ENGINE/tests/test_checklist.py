"""Each rendered view held to the conventions the providers publish and
AAC-14 keeps: a title and a description; a legend that explains every
channel the drawing uses; boundaries named by kind and in the legend; no
edge drawn twice; labels, where a view asks for them, on every edge of that
kind; a technology line that says something the name does not; and the
Markdown and Mermaid beside the drawing carrying the same.
"""

from __future__ import annotations

import importlib
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.blocks import load_components  # noqa: E402
from terrane.palette import Palette, boundary_style  # noqa: E402
from terrane.query import group_kinds, resolve  # noqa: E402
from terrane.render_mermaid import render, render_markdown  # noqa: E402
from terrane.techline import TechnologyLines  # noqa: E402

from _fixture import REPO, drawable, seeded_model, seeded_root, seeded_views  # noqa: E402


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


def _nodes(payload):
    return [e["data"] for e in payload["elements"] if not e["data"].get("isGroup") and not e["data"].get("source")]


def _edges(payload):
    return [e["data"] for e in payload["elements"] if e["data"].get("source")]


def _groups(payload):
    return [e["data"] for e in payload["elements"] if e["data"].get("isGroup")]


class TestDiagramChecklist(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = seeded_root()
        cls.model = seeded_model()
        cls.views = seeded_views()
        cls.palette = Palette(cls.model.config.get("palette"))
        cls.server = _server(cls.root)
        cls.drawn = []
        for view in cls.views:
            bound = drawable(cls.model, view)
            if bound is None:
                continue
            try:
                payload = cls.server._graph_payload(cls.model, bound, cls.palette)
            except cls.server.ApiError:
                continue
            cls.drawn.append((view, bound, payload))

    def test_the_seed_draws_most_views(self) -> None:
        self.assertGreater(len(self.drawn), len(self.views) * 0.6)

    def test_every_view_has_a_title_and_a_description(self) -> None:
        for view in self.views:
            with self.subTest(view=view.view_id):
                self.assertTrue(view.title.strip())
                self.assertTrue(view.description.strip())

    def test_the_legend_explains_every_channel_drawn(self) -> None:
        for view, _bound, payload in self.drawn:
            with self.subTest(view=view.view_id):
                nodes, edges, groups = _nodes(payload), _edges(payload), _groups(payload)
                legend = payload["legend"]
                # Hue is the entity type: every type drawn, counted.
                self.assertEqual({t["key"]: t["count"] for t in legend["types"]},
                                 dict(Counter(n["entityType"] for n in nodes)))
                # The view's dimension: every value a node carries is a key.
                dim = legend["dimension"]
                if dim["name"] and nodes:
                    self.assertTrue({n["styleKey"] for n in nodes} <= {k["value"] for k in dim["keys"]})
                # Line style is the kind of relationship: every kind drawn.
                self.assertEqual({e["kind"] for e in legend["edges"]}, {e["kind"] for e in edges})
                # Boundaries: every provider-styled container is in the legend.
                self.assertEqual({b["key"] for b in legend["boundaries"]}, {g["bkey"] for g in groups if g["bkey"]})

    def test_boundaries_are_named_by_kind(self) -> None:
        for view, bound, payload in self.drawn:
            with self.subTest(view=view.view_id):
                graph = resolve(self.model, bound)
                kinds = group_kinds(graph)
                labels = {g["id"]: g["label"] for g in _groups(payload)}
                for path in graph.groups:
                    kind, provider = kinds.get(path, ("", ""))
                    style = boundary_style(kind, path[-1], provider, len(path))
                    label = labels["grp::" + "::".join(path)]
                    if style.word:
                        self.assertTrue(label.startswith(style.word + " "), (view.view_id, label))
                    else:
                        self.assertEqual(label, path[-1])

    def test_no_edge_is_drawn_twice_and_a_kind_is_labeled_throughout_or_not_at_all(self) -> None:
        for view, _bound, payload in self.drawn:
            with self.subTest(view=view.view_id):
                edges = _edges(payload)
                seen = Counter((e["source"], e["target"], e["kind"], e["label"]) for e in edges)
                self.assertEqual([k for k, c in seen.items() if c > 1], [])
                by_kind = {}
                # A line through an offered interface leaves what the
                # interface says once -- the protocol under its name -- to
                # the interface, and is neither labeled nor not.
                offered = {n["id"] for n in _nodes(payload) if n["entityType"] == "offered_interfaces"}
                for e in edges:
                    if e["kind"] == "interface" and not e["label"] and (e["source"] in offered or e["target"] in offered):
                        continue
                    by_kind.setdefault(e["kind"], []).append(bool(e["label"]))
                for kind, flags in by_kind.items():
                    self.assertIn(sum(flags), (0, len(flags)),
                                  "%s: %s edges are labeled on some and not on others" % (view.view_id, kind))

    def test_a_technology_line_says_what_the_name_does_not(self) -> None:
        for view, _bound, payload in self.drawn:
            with self.subTest(view=view.view_id):
                for n in _nodes(payload):
                    tech = n.get("tech", "")
                    # An offered interface says its protocol there, once
                    # for every line through it.
                    if n["entityType"] not in ("systems", "tech_services", "offered_interfaces"):
                        self.assertEqual(tech, "")
                    if tech:
                        self.assertNotEqual(tech.lower(), n["label"].lower())
                        self.assertLessEqual(len(tech), 48)

    def test_a_data_system_says_its_data_services_first(self) -> None:
        """A pipeline reads a queue and fills a warehouse; the warehouse is
        the point. A channel runs on a cluster and keeps a cache; the cluster
        is."""
        lines = TechnologyLines(self.model, load_components(self.root))
        self.assertEqual(lines.of("systems", self.model.get("systems", "SYS-LENDPERF-PIPELINE")), "BigQuery · Dataflow +3")
        self.assertEqual(lines.of("systems", self.model.get("systems", "SYS-LENDPERF-SEMANTIC")), "BigQuery · Looker")
        self.assertTrue(lines.of("systems", self.model.get("systems", "SYS-CARDSVC-API")).startswith("AKS"))

    def test_the_line_is_read_from_the_model(self) -> None:
        components = load_components(self.root)
        lines = TechnologyLines(self.model, components)
        compute = next(c for c in components.values() if c.category == "Compute")
        self.assertEqual(lines.of("tech_services", {"name": "Some Cluster", "component_type": compute.component_type_id}), compute.name)
        self.assertEqual(lines.of("tech_services", {"name": compute.name, "component_type": compute.component_type_id}), "")
        self.assertEqual(lines.of("tech_services", {"name": "Azure SQL", "product": "Azure SQL Database",
                                                    "component_type": compute.component_type_id}), "Azure SQL Database")
        self.assertEqual(lines.of("systems", {"system_id": "SYS-NOPE", "hosting": "SaaS"}), "SaaS")
        self.assertEqual(lines.of("systems", {"system_id": "SYS-NOPE"}), "")
        self.assertEqual(lines.of("capabilities", {"name": "Anything"}), "")
        # A system that uses platform services names them, two at most, the
        # rest counted; network and security services are not its technology.
        services = {r["tech_service_id"]: r for r in self.model.all_of("tech_services")}
        platform = {}
        estate = {}
        for row in self.model.relation_rows("system_uses_tech_service"):
            service = services.get(str(row["tech_service_id"]))
            component = components.get(str(service.get("component_type"))) if service else None
            if component is None:
                continue
            bucket = platform if component.category in ("Compute", "Application", "Integration", "Data", "Storage") else estate
            bucket.setdefault(str(row["system_id"]), []).append(service)
        self.assertTrue(platform)
        system_id, used = max(platform.items(), key=lambda kv: len(kv[1]))
        line = lines.of("systems", self.model.get("systems", system_id))
        shorts = {str(s.get("service_name") or s.get("name")) for s in used}
        self.assertTrue(any(short in line for short in shorts), (system_id, line, shorts))
        if len({s.lower() for s in shorts}) > 2:
            self.assertRegex(line, r" \+\d+$")
        only_estate = [s for s in estate if s not in platform]
        if only_estate:
            record = self.model.get("systems", only_estate[0])
            self.assertEqual(lines.of("systems", record), "SaaS" if record.get("hosting") == "SaaS" else
                             ("external" if record.get("hosting") == "External" else ""))

    def test_the_markdown_and_mermaid_carry_the_drawing(self) -> None:
        for view, bound, payload in self.drawn:
            if view.kind == "report":
                continue
            with self.subTest(view=view.view_id):
                graph = resolve(self.model, bound)
                text = render(graph, self.palette)
                md = render_markdown(graph, self.palette, self.model)
                self.assertIn("Generated from the model", text)
                self.assertTrue(md.startswith("# " + bound.title))
                self.assertIn("Generated from the model", md)
                if payload["legend"]["boundaries"]:
                    self.assertIn("**Boundaries**", md)
                if payload["flows"]:
                    self.assertIn("## Flows across this diagram", md)
                for n in _nodes(payload)[:5]:
                    self.assertIn(n["id"].replace("-", "_"), text)


if __name__ == "__main__":
    unittest.main()
