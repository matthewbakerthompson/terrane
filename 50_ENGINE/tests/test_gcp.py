"""The third cloud: a Google Cloud landing zone of the same kinds as the AWS
and Azure zones, a digital shape resolved against it, a product that lands
there drawn in Google's boundary style with Google's marks, and a candidate
told apart by cloud when two shapes share their parts."""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import importer, model as model_module  # noqa: E402
from terrane.adoption import candidates  # noqa: E402
from terrane.archetype import landing_zone_gaps, landing_zone_index  # noqa: E402
from terrane.modules import load_modules  # noqa: E402

from _fixture import EXAMPLE_CSV, REPO, Sandbox, seeded_model, seeded_root  # noqa: E402

PRODUCT = {
    "archetype": "gcp-digital-product", "id": "PRD-GCPTEST",
    "values": {"name": "Dealer Finance Desk", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
               "criticality": "Medium", "company_domain": "Probing"},
    "parameters": {"slug": "dealer", "product_name": "Dealer Finance Desk", "owner_org": "ORG-PRODUCT",
                   "domain": "Probing", "account": "gcp-probe-prod"},
}


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    # A fresh sandbox is empty until the example seed is imported into it;
    # the landing zone the shape resolves against lives in that seed.
    importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
    return server_module


class TestGoogleCloud(unittest.TestCase):
    def test_the_landing_zone_answers_for_every_kind_the_shape_asks(self) -> None:
        model = seeded_model()
        shape = model.archetypes["gcp-digital-product"]
        self.assertEqual(shape.provider, "GCP")
        zone = landing_zone_index(model.all_of("tech_services"))
        kinds = {kind for (provider, kind) in zone if provider == "GCP"}
        for needed in ("container-platform", "api-gateway", "relational-db", "kms", "secrets-manager",
                       "message-queue", "event-stream", "observability", "dns", "waf", "cache", "backup",
                       "warehouse", "etl", "workflow", "bi"):
            self.assertIn(needed, kinds)
        gaps = [g for g in landing_zone_gaps(load_modules(seeded_root()), [shape], zone)]
        self.assertEqual(gaps, [])

    def test_a_product_lands_there_as_it_does_on_the_other_clouds(self) -> None:
        with Sandbox() as root:
            server = _server(root)
            res = server.api_instantiate({}, PRODUCT)
            self.assertIn("SYS-DEALER-API", res["generated"])
            self.assertIn("SYS-DEALER-DB", res["generated"])
            self.assertEqual(res["errors"], [])
            payload = server.api_graph({"view": ["onboarding"], "p_product": ["PRD-GCPTEST"]}, None)
            groups = {g["data"]["label"]: g["data"] for g in payload["elements"] if g["data"].get("isGroup")}
            self.assertIn("project gcp-probe-prod", groups)
            self.assertEqual(groups["project gcp-probe-prod"]["bkey"], "GCP project")
            self.assertIn("region europe-west2", groups)
            nodes = {n["data"]["id"]: n["data"] for n in payload["elements"] if not n["data"].get("isGroup") and not n["data"].get("source")}
            self.assertTrue(nodes["SYS-DEALER-API"]["tech"].startswith("GKE"))
            self.assertEqual(nodes["SYS-DEALER-DB"]["tech"], "Cloud SQL")
            architecture = server.api_graph({"view": ["product-architecture"], "p_product": ["PRD-GCPTEST"]}, None)
            marks = {n["data"]["label"]: n["data"]["icon"] for n in architecture["elements"]
                     if n["data"].get("entityType") == "tech_services"}
            self.assertEqual(marks.get("Google Kubernetes Engine"), "icons/gcp/gke.svg")
            self.assertEqual(marks.get("Apigee"), "icons/gcp/apigee.svg")

    def test_the_network_estate_draws_two_clouds_and_the_data_center(self) -> None:
        from terrane.query import load_views, resolve

        model = seeded_model()
        view = next(v for v in load_views(seeded_root() / "30_VIEWS") if v.view_id == "network-topology")
        graph = resolve(model, view)
        self.assertLessEqual(len(graph.nodes), view.limits.get("max_nodes", 40))
        self.assertIn(("GCP",), graph.groups)
        self.assertIn(("GCP", "gcp-shared-network"), graph.groups)
        self.assertIn(("GCP", "gcp-lending-prod"), graph.groups)
        self.assertIn(("GCP", "gcp-lending-prod", "europe-west1"), graph.groups)
        # Both clouds reach the one data center, each by two paths.
        into_dc = {e.source for e in graph.edges if e.target == "TS-ONPREM-DC"}
        self.assertTrue({"TS-NET-DX", "TS-NET-VPN"} <= into_dc)
        self.assertTrue({"TS-GCP-INTERCONNECT", "TS-GCPNET-HA-VPN"} <= into_dc)

    def test_a_bought_capability_reaches_its_vendor_by_the_private_path_on_google_cloud(self) -> None:
        with Sandbox() as root:
            server = _server(root)
            res = server.api_instantiate({}, {
                "archetype": "vendor-saas-service-gcp", "id": "PRD-OBTEST",
                "values": {"name": "Probe Vendor", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
                           "criticality": "Medium", "company_domain": "Probing"},
                "parameters": {"slug": "obt", "product_name": "Probe Vendor", "vendor": "Probe Ltd",
                               "owner_org": "ORG-PRODUCT", "domain": "Probing", "upstream_system": "SYS-CORE-LEDGER",
                               "account": "gcp-probe-prod"},
            })
            self.assertEqual(res["errors"], [])
            for made in ("SYS-OBT-VENDOR", "SYS-OBT-GATEWAY", "SYS-OBT-EGRESS", "SYS-OBT-WEBHOOKS"):
                self.assertIn(made, res["generated"])
            model = model_module.load(root)
            uses = {(str(r["system_id"]), str(r["tech_service_id"])) for r in model.relation_rows("system_uses_tech_service")}
            self.assertIn(("SYS-OBT-EGRESS", "TS-GCP-PSC"), uses)
            egress = model.get("systems", "SYS-OBT-EGRESS")
            self.assertEqual(egress["cloud_provider"], "GCP")
            self.assertEqual(egress["cloud_account"], "gcp-probe-prod")
            vendor = model.get("systems", "SYS-OBT-VENDOR")
            self.assertEqual(vendor["provider"], "Probe Ltd")
            # The shape answers the listener's consumer with the caller, so
            # the product said nothing about it.
            consumer = model.get("interfaces", "INT-OBT-WEBHOOKS-CONSUMER")
            self.assertEqual(consumer["target_system_id"], "SYS-CORE-LEDGER")

    def test_a_second_spoke_and_the_first_dataset_in_bigquery(self) -> None:
        """The analytics project is a second spoke on the hub, and the batch
        shape with a Google binding lands a data product there: Pub/Sub in
        from the source system the shape asks for, Dataflow, BigQuery, and
        the marks BigQuery and Looker carry."""
        from terrane.query import load_views, resolve

        model = seeded_model()
        view = next(v for v in load_views(seeded_root() / "30_VIEWS") if v.view_id == "network-topology")
        graph = resolve(model, view)
        self.assertLessEqual(len(graph.nodes), view.limits.get("max_nodes", 40))
        self.assertIn(("GCP", "gcp-analytics-prod"), graph.groups)
        self.assertIn(("GCP", "gcp-analytics-prod", "europe-west1"), graph.groups, "the analytics project has a standby region too")
        self.assertIn(("TS-GCP-SHARED-VPC", "TS-GCPNET-SUB-ANALYTICS-DATA"), {(e.source, e.target) for e in graph.edges})
        with Sandbox() as root:
            server = _server(root)
            res = server.api_instantiate({}, {
                "archetype": "batch-data-product-gcp", "id": "PRD-LPTEST",
                "values": {"name": "Probe Performance", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
                           "criticality": "Medium", "company_domain": "Probing"},
                "parameters": {"slug": "lpt", "product_name": "Probe Performance", "owner_org": "ORG-PRODUCT",
                               "domain": "Probing", "source_system": "SYS-POSFIN-EVENTS", "account": "gcp-analytics-prod"},
            })
            self.assertEqual(res["errors"], [])
            made = model_module.load(root)
            uses = {(str(r["system_id"]), str(r["tech_service_id"])) for r in made.relation_rows("system_uses_tech_service")}
            self.assertIn(("SYS-LPT-PIPELINE", "TS-GCP-BIGQUERY"), uses)
            self.assertIn(("SYS-LPT-PIPELINE", "TS-GCP-DATAFLOW"), uses)
            ingest = made.get("interfaces", "INT-LPT-INGEST")
            self.assertEqual(ingest["source_system_id"], "SYS-POSFIN-EVENTS")
            self.assertEqual(ingest["protocol"], "Pub/Sub")
            self.assertEqual(made.get("systems", "SYS-LPT-PIPELINE")["cloud_account"], "gcp-analytics-prod")
            architecture = server.api_graph({"view": ["product-architecture"], "p_product": ["PRD-LPTEST"]}, None)
            marks = {n["data"]["label"]: n["data"].get("icon") for n in architecture["elements"]
                     if n["data"].get("entityType") == "tech_services"}
            self.assertEqual(marks.get("BigQuery"), "icons/gcp/bigquery.svg")
            self.assertEqual(marks.get("Looker"), "icons/gcp/looker.svg")
            # The committed product's dataset has a reader on the Azure side,
            # so its architecture is two clouds on one sheet.
            drawn = server.api_graph({"view": ["product-architecture"], "p_product": ["PRD-LENDING-PERFORMANCE"]}, None)
            groups = {g["data"]["label"] for g in drawn["elements"] if g["data"].get("isGroup")}
            self.assertTrue({"GCP", "Azure", "subscription azure-risk-prod"} <= groups, groups)
            edges = {(e["data"]["source"], e["data"]["target"]) for e in drawn["elements"] if e["data"].get("source")}
            self.assertIn(("SYS-LENDPERF-SEMANTIC", "SYS-REG-REPORTING"), edges)

    def test_two_shapes_with_the_same_parts_are_told_apart_by_cloud(self) -> None:
        model = seeded_model()
        shapes = list(model.archetypes.values())
        found = candidates(model, shapes, load_modules(seeded_root()))
        for candidate in found:
            if candidate.archetype_id == "gcp-digital-product":
                clouds = {str(r.get("cloud_provider") or r.get("hosting") or "") for r in model.all_of("systems")
                          if any(row.get("system_id") == r["system_id"] and row.get("product_id") == candidate.product_id
                                 for row in model.relation_rows("product_includes_system"))}
                self.assertIn("GCP", clouds, "a product off Google Cloud offered the Google shape: %s" % candidate.product_id)
        azure = [c.product_id for c in found if c.archetype_id == "azure-digital-product"]
        self.assertTrue(azure)
        self.assertEqual(len(azure), len(set(azure)))


if __name__ == "__main__":
    unittest.main()
