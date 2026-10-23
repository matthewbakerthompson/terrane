"""Tests for a view placed on another as a boundary (terrane.places).

What is checked: a diagram that places Network Topology draws what that
view draws, inside its boundaries, along its lines and in its direction,
with the things pinned to the diagram among them; it follows the placed
view when the placed view changes, since nothing of it is copied; an
account left out or kept only is left off this diagram alone, and a field
the placed view already filters on is narrowed in the same key; a place
without the view's own boxes keeps the boundaries around what was pinned;
merging is the same however many times it is done; and a place naming a
view that is not there, or one that places others, is an error rather than
a diagram quietly drawn without it.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import jsonschema, places, validate  # noqa: E402
from terrane.query import load_views, resolve  # noqa: E402

from _fixture import REPO, seeded_model, setup_shared, teardown_shared  # noqa: E402

NETWORK = (REPO / "30_VIEWS" / "network-topology.view.yaml").read_text(encoding="utf-8")

#: A diagram as the canvas writes one: Network Topology placed, a system of
#: the lending account pinned to it.
DIAGRAM = """\
view_id: lending-onboarding
title: Lending onboarding
category: Application
kind: diagram
places:
  - view: network-topology
scope:
  pin: [SYS-LENDING-API]
edges:
  - via: interfaces
"""


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class _Views(unittest.TestCase):
    """A folder of views holding Network Topology and whatever a test adds."""

    def setUp(self) -> None:
        self.model = seeded_model()
        self.folder = Path(tempfile.mkdtemp(prefix="aac-places-"))
        self.write("network-topology.view.yaml", NETWORK)

    def tearDown(self) -> None:
        shutil.rmtree(self.folder)

    def write(self, name: str, text: str) -> None:
        (self.folder / name).write_text(text, encoding="utf-8")

    def views(self) -> dict:
        return {v.view_id: v for v in load_views(self.folder)}

    def drawn(self, view_id: str = "lending-onboarding"):
        return resolve(self.model, self.views()[view_id])


class TestMerging(_Views):
    def test_a_placed_view_brings_its_boxes_boundaries_and_lines(self) -> None:
        self.write("lending.view.yaml", DIAGRAM)
        views = self.views()
        network, diagram = views["network-topology"], views["lending-onboarding"]
        self.assertEqual(diagram.group_by, network.group_by)
        self.assertEqual(diagram.layout, network.layout)
        self.assertEqual([e["via"] for e in diagram.edges],
                         ["interfaces"] + [e["via"] for e in network.edges if e["via"] != "interfaces"])
        own = {n.key for n in resolve(self.model, network).nodes}
        graph = self.drawn()
        self.assertEqual({n.key for n in graph.nodes}, own | {"SYS-LENDING-API"})
        # The pinned system sits in the placed view's boundaries.
        lending = [n for n in graph.nodes if n.key == "SYS-LENDING-API"][0]
        self.assertEqual(lending.groups[:3], ("AWS", "prod-lending", "eu-west-2"))
        # The file is as the canvas wrote it: the merge is in memory.
        self.assertEqual(diagram.own.scope, {"pin": ["SYS-LENDING-API"]})
        self.assertEqual(diagram.own.group_by, [])

    def test_the_diagram_follows_the_placed_view(self) -> None:
        self.write("lending.view.yaml", DIAGRAM)
        before = {n.key for n in self.drawn().nodes}
        self.assertTrue(any(k.startswith("TS-GCPNET") for k in before))
        self.write("network-topology.view.yaml", NETWORK.replace(
            "tags_any: [network-fabric]", "tags_any: [network-fabric]\n        cloud_provider: [AWS]", 1))
        after = {n.key for n in self.drawn().nodes}
        self.assertFalse(any(k.startswith("TS-GCPNET") for k in after))
        self.assertIn("SYS-LENDING-API", after)

    def test_an_account_left_out_is_left_off_this_diagram_alone(self) -> None:
        self.write("lending.view.yaml", DIAGRAM.replace(
            "  - view: network-topology\n",
            "  - view: network-topology\n    leave_out:\n      cloud_account: [prod-riskops, gcp-analytics-prod]\n"))
        accounts = {n.record.get("cloud_account") for n in self.drawn().nodes}
        self.assertNotIn("prod-riskops", accounts)
        self.assertNotIn("gcp-analytics-prod", accounts)
        self.assertIn("gcp-lending-prod", accounts)
        # The placed view is as it was.
        whole = {n.record.get("cloud_account") for n in self.drawn("network-topology").nodes}
        self.assertIn("prod-riskops", whole)

    def test_only_keeps_one_account(self) -> None:
        self.write("lending.view.yaml", DIAGRAM.replace(
            "  - view: network-topology\n",
            "  - view: network-topology\n    only:\n      cloud_account: prod-lending\n"))
        parts = [n for n in self.drawn().nodes if n.entity_type == "tech_services"]
        self.assertTrue(parts)
        self.assertEqual({n.record.get("cloud_account") for n in parts}, {"prod-lending"})

    def test_without_its_parts_only_the_boundaries_round_the_pins_stay(self) -> None:
        self.write("lending.view.yaml", DIAGRAM.replace(
            "  - view: network-topology\n", "  - view: network-topology\n    parts: false\n"))
        graph = self.drawn()
        self.assertEqual([n.key for n in graph.nodes], ["SYS-LENDING-API"])
        self.assertEqual(graph.groups[:3], [("AWS",), ("AWS", "prod-lending"), ("AWS", "prod-lending", "eu-west-2")])

    def test_merging_twice_is_merging_once(self) -> None:
        self.write("lending.view.yaml", DIAGRAM)
        once = self.views()
        twice = {v.view_id: v for v in places.with_places(list(once.values()))}
        self.assertEqual(twice["lending-onboarding"].scope, once["lending-onboarding"].scope)
        self.assertEqual(twice["lending-onboarding"].edges, once["lending-onboarding"].edges)

    def test_a_limit_on_a_field_already_filtered_is_said_in_one_key(self) -> None:
        narrow = places._narrow_where
        self.assertEqual(narrow({"cloud_account": ["a", "b"]}, {"cloud_account": ["a"]}, {}), {"cloud_account": ["a"]})
        self.assertEqual(narrow({"cloud_account": {"not": ["a"]}}, {}, {"cloud_account": ["b"]}),
                         {"cloud_account": {"not": ["a", "b"]}})
        self.assertEqual(narrow({"cloud_account": ["a", "b"]}, {}, {"cloud_account": ["b"]}), {"cloud_account": ["a"]})
        self.assertEqual(narrow({}, {}, {"cloud_account": [""]}), {"cloud_account": {"not": [""]}})
        self.assertIsNone(narrow({"cloud_account": {"exists": True}}, {"cloud_account": ["a"]}, {}))


class TestChecks(_Views):
    def findings(self):
        report = validate.run(self.model, list(self.views().values()))
        return [(f.severity, f.code, f.message) for f in report.findings if f.code == "view.place"]

    def test_a_place_naming_no_view_here_is_an_error(self) -> None:
        self.write("lending.view.yaml", DIAGRAM.replace("view: network-topology", "view: network-topolgy"))
        self.assertEqual(self.findings(), [("error", "view.place",
                                            "view lending-onboarding places network-topolgy, which is not a view here")])
        # It still draws what it pins, rather than refusing to load.
        self.assertEqual([n.key for n in self.drawn().nodes], ["SYS-LENDING-API"])

    def test_a_placed_view_that_places_others_is_an_error(self) -> None:
        self.write("lending.view.yaml", DIAGRAM)
        self.write("wrapper.view.yaml", DIAGRAM.replace("view_id: lending-onboarding", "view_id: wrapper")
                   .replace("view: network-topology", "view: lending-onboarding"))
        found = self.findings()
        self.assertEqual([f[:2] for f in found], [("error", "view.place")])
        self.assertIn("wrapper places lending-onboarding, which places others", found[0][2])

    def test_the_schema_admits_a_diagram_of_places(self) -> None:
        try:
            import jsonschema as validator  # the third-party package, not aac's
        except ImportError:
            self.skipTest("no JSON Schema validator installed")
        if not hasattr(validator, "Draft202012Validator"):
            self.skipTest("the installed validator predates draft 2020-12")
        check = validator.Draft202012Validator(jsonschema.view_schema())
        placed = {"view_id": "x", "places": [{"view": "network-topology", "leave_out": {"cloud_account": ["a"]}}]}
        self.assertEqual([e.message for e in check.iter_errors(placed)], [])
        self.assertTrue(list(check.iter_errors({"view_id": "x"})))
        self.assertTrue(list(check.iter_errors({"view_id": "x", "places": [{"view": "a", "copy": True}]})))


if __name__ == "__main__":
    unittest.main()
