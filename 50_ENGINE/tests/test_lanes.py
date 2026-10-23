"""Tiers in their own order: a grouped field's values are laid out in the
order the view gives, or the field's own enumeration, whatever the edges
between them say."""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import jsonschema  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402
from terrane.palette import ORDINAL, Palette  # noqa: E402
from terrane.query import Node, ViewError, group_paths, parse_view, resolve  # noqa: E402
from terrane.render_mermaid import render  # noqa: E402
from terrane.schema import NETWORK_ZONES  # noqa: E402

from _fixture import REPO, seeded_model, seeded_root, seeded_views  # noqa: E402

BASE = {"view_id": "probe", "scope": {"include": [{"type": "systems"}]}, "group_by": "network_zone"}


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestLanes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}
        cls.palette = Palette(cls.model.config.get("palette"))

    def test_the_enumeration_is_the_default_and_the_view_can_say_otherwise(self) -> None:
        self.assertEqual(parse_view(dict(BASE)).lanes, {"network_zone": list(NETWORK_ZONES)})
        self.assertEqual(parse_view(dict(BASE, lanes=False)).lanes, {})
        self.assertEqual(parse_view(dict(BASE, lanes=["Private-Data", "Edge"])).lanes, {"network_zone": ["Private-Data", "Edge"]})
        nested = parse_view(dict(BASE, group_by=["cloud_provider", "network_zone"], lanes={"network_zone": ["On-prem"]}))
        self.assertEqual(nested.lanes["network_zone"], ["On-prem"])
        # A provider is enumerated but has no reading order: it follows the
        # edges unless the view says otherwise. A lifecycle and a scale do.
        self.assertNotIn("cloud_provider", nested.lanes)
        self.assertEqual(parse_view(dict(BASE, group_by="cloud_provider")).lanes, {})
        self.assertEqual(parse_view(dict(BASE, group_by="actor_kind")).lanes, {})
        self.assertEqual(parse_view(dict(BASE, group_by="company_domain")).lanes, {})
        self.assertEqual(parse_view(dict(BASE, group_by="status")).lanes["status"][:3], ["Proposed", "Planned", "Active"])
        self.assertEqual(parse_view(dict(BASE, group_by="capability_tier")).lanes["capability_tier"], list(ORDINAL["capability_tier"]))
        self.assertEqual(parse_view(dict(BASE, group_by="cloud_provider", lanes=["SaaS", "AWS"])).lanes, {"cloud_provider": ["SaaS", "AWS"]})
        with self.assertRaises(ViewError):
            parse_view(dict(BASE, lanes="Edge"))
        with self.assertRaises(ViewError):
            parse_view(dict(BASE, group_by=[], lanes=["Edge"]))

    def test_unknown_values_follow_the_named_ones_in_their_own_order(self) -> None:
        nodes = [
            Node(z.lower(), z, "systems", (0, z), (z,), "x", {}, ("network_zone",))
            for z in ("Zulu", "Public", "Alpha", "Edge")
        ]
        paths = group_paths(nodes, {"network_zone": ["Edge", "Public"]})
        self.assertEqual([p[-1] for p in paths], ["Edge", "Public", "Alpha", "Zulu"])
        # Without lanes, or without the field behind the level, by name.
        self.assertEqual([p[-1] for p in group_paths(nodes)], ["Alpha", "Edge", "Public", "Zulu"])
        bare = [Node(z.lower(), z, "systems", (0, z), (z,), "x", {}) for z in ("Zulu", "Edge")]
        self.assertEqual([p[-1] for p in group_paths(bare, {"network_zone": ["Zulu"]})], ["Edge", "Zulu"])

    def test_the_tier_diagram_reads_edge_to_data(self) -> None:
        view = self.views["tiered-architecture"]
        self.assertEqual(view.lanes["network_zone"][0], "Edge")
        graph = resolve(self.model, view)
        drawn = [p[-1] for p in graph.groups]
        self.assertGreater(len(drawn), 2)
        self.assertEqual(drawn, [z for z in NETWORK_ZONES if z in drawn])
        # The Mermaid declares the tiers in that order too.
        text = render(graph, self.palette)
        at = [text.index('["%s"]' % z) for z in drawn]
        self.assertEqual(at, sorted(at))

    def test_the_payload_carries_the_lanes_and_each_boundary_its_value(self) -> None:
        server = _server(seeded_root())
        view = self.views["tiered-architecture"]
        payload = server._graph_payload(self.model, view, self.palette)
        self.assertEqual(payload["lanes"]["network_zone"][0], "Edge")
        groups = [e["data"] for e in payload["elements"] if e["data"].get("isGroup")]
        self.assertEqual([g["value"] for g in groups], [p[-1] for p in resolve(self.model, view).groups])
        self.assertTrue(all(g["kind"] == "network_zone" for g in groups))
        # A nested view orders the zones inside each region the same way.
        onboarding = self.views["onboarding"]
        self.assertEqual(onboarding.lanes.get("network_zone"), list(NETWORK_ZONES))

    def test_the_schema_admits_lanes(self) -> None:
        schema = jsonschema.view_schema()
        self.assertIn("lanes", schema["properties"])
        self.assertIn("false", json.dumps(schema["properties"]["lanes"]))

    def test_every_shipped_view_is_one_the_schema_admits(self) -> None:
        """The schema had fallen far enough behind that every shipped view
        failed it, with nothing reading a view against it."""
        try:
            import jsonschema as validator  # the third-party package, not aac's
        except ImportError:
            self.skipTest("no JSON Schema validator installed")
        if not hasattr(validator, "Draft202012Validator"):
            self.skipTest("the installed validator predates draft 2020-12")
        check = validator.Draft202012Validator(jsonschema.view_schema())
        for path in sorted((REPO / "30_VIEWS").glob("*.view.yaml")):
            with self.subTest(view=path.name):
                self.assertEqual([e.message for e in check.iter_errors(read_data_file(path))], [])


if __name__ == "__main__":
    unittest.main()
