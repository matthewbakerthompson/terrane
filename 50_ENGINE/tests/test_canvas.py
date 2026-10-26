"""Tests for the canvas's endpoints: New diagram, drawn by placing things.

What is checked: the picker is offered the library's parts for the boxes a
diagram draws, the views that box what they draw, Network Topology's
accounts and zones and the systems; a part is found by what each cloud
calls it, and one dropped into an account of a cloud is that cloud's
product, the person's choice of its products kept; a part placed is a record with the
part's defaults and the fields of every boundary it was dropped into, its
id made from the name it was given, a name already taken numbered rather
than reused, and what the kind of record needs and the drop did not say
listed rather than guessed; a diagram is written the first time something
is on it, with an id from its title that no view has, and rewritten by
value after, a line someone added by hand kept; one placing a view that is
not here is refused with nothing written; a drawing of placed views draws
through the preview the canvas uses; and the overview says which diagrams
open on the canvas.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.blocks import offered  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402

from _fixture import REPO, Sandbox  # noqa: E402

INTO = [
    {"field": "cloud_provider", "value": "AWS"},
    {"field": "cloud_account", "value": "prod-lending"},
    {"field": "region", "value": "eu-west-2"},
    {"field": "availability_zone", "value": "eu-west-2a"},
]


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestCanvas(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sandbox = Sandbox(seed=True)
        cls.root = cls.sandbox.__enter__()
        cls.server = _server(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sandbox.__exit__(None, None, None)

    def test_the_picker_offers_parts_views_accounts_zones_and_systems(self) -> None:
        got = self.server.api_canvas_parts({}, {})
        self.assertEqual({p["type"] for p in got["parts"]}, {"systems", "tech_services"})
        self.assertEqual(got["parts"][0]["type"], "systems")
        self.assertEqual(got["network"], "network-topology")
        network = [v for v in got["views"] if v["id"] == "network-topology"][0]
        self.assertEqual(network["fold"]["field"], "cloud_account")
        labels = [v["label"] for v in network["fold"]["values"]]
        self.assertIn("AWS · prod-lending", labels)
        # The on-prem parts have no account, and are left out by their cloud.
        self.assertEqual(labels[-1], "On-prem")
        self.assertIn("prod-lending", [a["value"] for a in got["accounts"]])
        self.assertIn("Private-App", [z["value"] for z in got["zones"]])
        self.assertEqual(got["counts"]["systems"], len(got["systems"]))
        # A view that tables what it shows, or is about one subject, is not
        # a boundary to place.
        self.assertTrue(all(not v["id"].startswith("product-") or v["nodes"] for v in got["views"]))

    def test_a_part_is_found_by_what_each_cloud_calls_it(self) -> None:
        parts = {p["id"]: p for p in self.server.api_canvas_parts({}, {})["parts"]}
        self.assertEqual({c: parts["vm"]["products"][c] for c in ("AWS", "Azure", "GCP")},
                         {"AWS": ["Amazon EC2"], "Azure": ["Azure Virtual Machines"], "GCP": ["Compute Engine"]})
        # A choice is split at "or"; a pair joined by "and" is one answer;
        # an aside is no part of a name, though the whole answer is sent too.
        self.assertEqual(parts["container-platform"]["products"]["AWS"], ["Amazon EKS", "ECS"])
        self.assertEqual(offered("AWS Cost Explorer and Budgets"), ["AWS Cost Explorer and Budgets"])
        self.assertEqual(offered("Gemini Enterprise (formerly Agentspace)"), ["Gemini Enterprise"])
        self.assertEqual(offered("MinIO or a NAS"), ["MinIO", "NAS"])
        self.assertIn("formerly", " ".join(parts["ai-assistant"]["providers"].values()))

    def test_a_part_dropped_into_an_account_is_that_clouds_product(self) -> None:
        made = self.server.api_canvas_record({}, {"part": "vm", "into": INTO})
        self.assertEqual((made["name"], made["product"]), ("Amazon EC2", "Amazon EC2"))
        record = read_data_file(self.root / made["path"])
        self.assertEqual((record.get("product"), record.get("cloud_provider")), ("Amazon EC2", "AWS"))
        # The person's choice of the cloud's products is kept, and a name of
        # their own with it; one that is not this cloud's is the usual one.
        chosen = self.server.api_canvas_record({}, {"part": "container-platform", "into": INTO, "product": "ECS",
                                                    "name": "Lending batch cluster"})
        self.assertEqual((chosen["name"], chosen["product"]), ("Lending batch cluster", "ECS"))
        wrong = self.server.api_canvas_record({}, {"part": "container-platform", "into": INTO, "product": "Cloud Run"})
        self.assertEqual(wrong["product"], "Amazon EKS")
        # In no cloud's account it is the part, and no product is claimed.
        loose = self.server.api_canvas_record({}, {"part": "vm", "into": []})
        self.assertEqual((loose["name"], loose["product"]), ("Virtual machine", ""))
        self.assertIsNone(read_data_file(self.root / loose["path"]).get("product"))

    def test_a_part_is_a_record_named_and_placed_where_it_was_dropped(self) -> None:
        made = self.server.api_canvas_record({}, {"part": "web-app", "into": INTO, "name": "Lending portal"})
        self.assertEqual((made["id"], made["type"], made["name"]), ("SYS-LENDING-PORTAL", "systems", "Lending portal"))
        self.assertEqual(made["missing"], ["owner_org_id", "criticality"])
        record = read_data_file(self.root / made["path"])
        self.assertEqual({k: record.get(k) for k in ("status", "component_type", "network_zone", "cloud_account",
                                                       "region", "availability_zone", "owner_org_id")},
                         {"status": "Planned", "component_type": "web-app", "network_zone": "Private-App",
                          "cloud_account": "prod-lending", "region": "eu-west-2",
                          "availability_zone": "eu-west-2a", "owner_org_id": None})
        again = self.server.api_canvas_record({}, {"part": "web-app", "into": [], "name": "Lending portal"})
        self.assertEqual((again["id"], again["name"]), ("SYS-LENDING-PORTAL-2", "Lending portal 2"))
        with self.assertRaises(self.server.ApiError):
            self.server.api_canvas_record({}, {"part": "no-such-part"})

    def test_a_diagram_is_written_as_it_is_drawn(self) -> None:
        data = {"title": "Lending onboarding", "category": "Application", "kind": "diagram",
                "places": [{"view": "network-topology", "leave_out": {"cloud_account": ["prod-riskops"]}}],
                "scope": {"pin": ["SYS-LENDING-API"]}, "edges": [{"via": "interfaces"}]}
        first = self.server.api_canvas_save({}, {"id": None, "data": dict(data)})
        self.assertEqual((first["id"], first["created"]), ("lending-onboarding", True))
        path = self.root / first["path"]
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("view_id: lending-onboarding\ntitle: Lending onboarding\n"))
        self.assertIn("places:\n  - view: network-topology\n", text)
        # A second new diagram of the same title is given an id of its own.
        other = self.server.api_canvas_save({}, {"id": None, "data": dict(data)})
        self.assertEqual(other["id"], "lending-onboarding-2")
        # A line added by hand survives the next save.
        path.write_text(text.replace("kind: diagram\n", "kind: diagram\n# drawn for the lending review\n"),
                        encoding="utf-8")
        later = dict(data, title="Lending onboarding, AWS")
        self.server.api_canvas_save({}, {"id": "lending-onboarding", "data": later})
        text = path.read_text(encoding="utf-8")
        self.assertIn("# drawn for the lending review", text)
        self.assertIn('title: "Lending onboarding, AWS"', text)
        # Drawn through the preview the canvas uses: the placed view's
        # boundaries, its parts and the pin, the account left out gone.
        payload = self.server.api_view_preview({}, {"id": "lending-onboarding", "data": dict(later, view_id="lending-onboarding")})
        groups = [e["data"]["value"] for e in payload["elements"] if e["data"].get("isGroup")]
        self.assertIn("prod-lending", groups)
        self.assertNotIn("prod-riskops", groups)
        drawn = [e["data"]["id"] for e in payload["elements"] if not e["data"].get("isGroup") and not e["data"].get("source")]
        self.assertIn("SYS-LENDING-API", drawn)
        # The overview says it opens on the canvas, and Network Topology does not.
        listed = {v["viewId"]: v for v in self.server.api_overview({}, {})["views"]}
        self.assertTrue(listed["lending-onboarding"]["canvas"])
        self.assertFalse(listed["network-topology"]["canvas"])

    def test_a_diagram_placing_a_view_not_here_is_refused(self) -> None:
        data = {"title": "Nowhere", "kind": "diagram", "places": [{"view": "no-such-view"}]}
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertIn("places no-such-view, which is not a view here", str(caught.exception))
        self.assertFalse((self.root / "30_VIEWS" / "nowhere.view.yaml").exists())


if __name__ == "__main__":
    unittest.main()
