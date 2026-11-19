"""Networks made once per account, and every system landing in them.

A workload network is a technology service on a network shape: the VPC or
virtual network itself, whose expansion is its subnets, its NAT gateways,
its attachment to the landing zone's transit hub and its link to the
landing zone's resolver. A system in a cloud account and a network zone
lands in that account's subnets for the zone (`model.place_by_zone`), so a
network is made once and every product in the account reuses it. Until
2026-11-04 the lending product's subnet rows were written by hand, no other
product was placed, and no Azure subscription had a network.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import model as model_module  # noqa: E402
from terrane.blocks import LibraryError, parse_component  # noqa: E402

from _fixture import REPO, Sandbox  # noqa: E402

THURMAN = REPO / "90_EXAMPLE" / "thurman-health"


def uses(model, system_id: str):
    return sorted(str(r["tech_service_id"]) for r in model.relation_rows("system_uses_tech_service")
                  if r["system_id"] == system_id)


def joins(model, from_id: str):
    return sorted((str(r["to_tech_service_id"]), str(r.get("connection") or ""))
                  for r in model.relation_rows("tech_service_connects_to") if r["from_tech_service_id"] == from_id)


class TestEverySystemLandsInItsAccount(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = model_module.load(REPO)
        cls.thurman = model_module.load(THURMAN)

    def test_the_lending_product_lands_in_both_zones_as_it_was_written(self) -> None:
        for system, tier in (("SYS-LENDING-API", "APP"), ("SYS-LENDING-WEB", "APP"), ("SYS-LENDING-WORKER", "APP"),
                             ("SYS-LENDING-DB", "DATA"), ("SYS-LENDING-ALB", "PUB")):
            self.assertIn("TS-NET-SUB-LEND-%s-A" % tier, uses(self.model, system))
            self.assertIn("TS-NET-SUB-LEND-%s-B" % tier, uses(self.model, system))

    def test_a_system_that_names_its_subnet_is_left_as_it_says(self) -> None:
        # The bucket is drawn in the one data subnet its endpoint is in.
        self.assertEqual([u for u in uses(self.model, "SYS-LENDING-BUCKET") if "-SUB-" in u], ["TS-NET-SUB-LEND-DATA-A"])

    def test_a_kind_that_sits_in_no_subnet_is_not_placed(self) -> None:
        semantic = self.model.get("systems", "SYS-LENDPERF-SEMANTIC")
        self.assertEqual((semantic["component_type"], semantic["network_zone"]), ("bi", "Private-Data"))
        self.assertFalse([u for u in uses(self.model, "SYS-LENDPERF-SEMANTIC") if "SUB" in u])

    def test_a_subnet_of_another_region_is_not_the_systems(self) -> None:
        got = uses(self.model, "SYS-POSFIN-API")
        self.assertIn("TS-GCPNET-SUB-LEND-APP", got)
        self.assertNotIn("TS-GCPNET-SUB-LEND-APP-DR", got)

    def test_every_azure_product_lands_in_its_subscription(self) -> None:
        for system in self.model.all_of("systems"):
            if system.get("cloud_provider") != "Azure" or system.get("network_zone") not in (
                    "Private-App", "Private-Data", "Public", "Shared-Services") or not system.get("cloud_account"):
                continue
            with self.subTest(system=system["system_id"]):
                subnets = [u for u in uses(self.model, system["system_id"]) if u.startswith("TS-NET-SUB-AZ-")]
                self.assertEqual(len(subnets), 1, uses(self.model, system["system_id"]))
                subnet = self.model.get("tech_services", subnets[0])
                self.assertEqual((subnet["cloud_account"], subnet["network_zone"]),
                                 (system["cloud_account"], system["network_zone"]))

    def test_thurman_healths_patient_portal_lands_in_its_subscription(self) -> None:
        placed = {s["system_id"]: uses(self.thurman, s["system_id"]) for s in self.thurman.all_of("systems")
                  if s.get("cloud_account") == "azure-patient-prod" and s.get("network_zone")}
        self.assertTrue(placed)
        for system_id, got in placed.items():
            zone = self.thurman.get("systems", system_id)["network_zone"]
            want = {"Private-App": "APP", "Private-Data": "DATA", "Shared-Services": "SHARED"}[zone]
            self.assertIn("TS-NET-SUB-PATIENT-%s" % want, got, system_id)


class TestAWorkloadNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = model_module.load(REPO)

    def test_the_virtual_network_makes_its_subnets_and_its_nat(self) -> None:
        vnet = self.model.get("tech_services", "TS-NET-VNET-AZ-CARDS")
        self.assertEqual((vnet["component_type"], vnet["cloud_account"], vnet["archetype"]),
                         ("vpc", "azure-cards-prod", "azure-workload-network"))
        app = self.model.get("tech_services", "TS-NET-SUB-AZ-CARDS-APP")
        self.assertEqual((app["name"], app["component_type"], app["network_zone"], app["availability_zone"],
                          app["cloud_account"], app["region"], app["owner_org_id"], app["provider"]),
                         ("Cards App Subnet", "subnet", "Private-App", "zone-redundant", "azure-cards-prod", "uksouth",
                          "ORG-TECH", "Microsoft Azure"))
        # A network's parts are its own, never the landing zone's: a part
        # asking for a kind must not find a subnet.
        self.assertNotIn("landing-zone", app.get("tags") or [])
        self.assertEqual(self.model.get("tech_services", "TS-NET-NAT-AZ-CARDS-NAT")["component_type"], "nat-gateway")

    def test_it_attaches_to_the_hub_and_takes_its_names_from_the_resolver(self) -> None:
        self.assertIn(("TS-NET-VNET-AZ-CARDS", "network attachment"), joins(self.model, "TS-AZURE-VWAN"))
        self.assertEqual(joins(self.model, "TS-NET-VNET-AZ-CARDS"), [
            ("TS-AZURE-PRIVATE-DNS", "resolver"), ("TS-NET-NAT-AZ-CARDS-NAT", "egress route"),
            ("TS-NET-SUB-AZ-CARDS-APP", "subnet"), ("TS-NET-SUB-AZ-CARDS-DATA", "subnet")])


class TestMadeOnceUsedByEveryProduct(unittest.TestCase):
    """A new account: its network written once, and a system added after it
    in the account lands in it with nothing said about subnets."""

    def test_a_new_accounts_network_is_used_by_what_lands_there(self) -> None:
        with Sandbox() as root:
            model_dir = root / "10_MODEL"
            (model_dir / "tech_services").mkdir(parents=True, exist_ok=True)
            (model_dir / "systems").mkdir(parents=True, exist_ok=True)
            (model_dir / "model.yaml").write_text("answers:\n  platform_org: ORG-NET\n", encoding="utf-8")
            (model_dir / "tech_services" / "zone.yaml").write_text("""
- tech_service_id: TS-HUB
  name: Transit Gateway
  cloud_provider: AWS
  component_type: transit-gateway
  tags: [landing-zone]
- tech_service_id: TS-RESOLVER
  name: Route 53 Resolver
  cloud_provider: AWS
  component_type: dns
  tags: [landing-zone]
- tech_service_id: TS-NET-VPC-CLAIMS
  name: Claims VPC
  status: Planned
  cloud_account: prod-claims
  region: eu-west-2
  archetype: aws-workload-network
  parameters:
    slug: claims
    network_name: Claims
    account: prod-claims
    subnets:
      - {id: APP-A, name: App Subnet A, zone: Private-App, az: a}
      - {id: APP-B, name: App Subnet B, zone: Private-App, az: b}
      - {id: DATA-A, name: Data Subnet A, zone: Private-Data, az: a}
- tech_service_id: TS-NET-VPC-CARDS
  name: Cards VPC
  cloud_account: prod-cards
  archetype: aws-workload-network
  parameters:
    slug: cards
    network_name: Cards
    account: prod-cards
""", encoding="utf-8")
            (model_dir / "systems" / "claims.yaml").write_text("""
- system_id: SYS-CLAIMS-API
  name: Claims API
  cloud_account: prod-claims
  region: eu-west-2
  network_zone: Private-App
- system_id: SYS-CLAIMS-BUCKET
  name: Claims documents
  component_type: object-store
  cloud_account: prod-claims
  network_zone: Private-Data
""", encoding="utf-8")
            model = model_module.load(root)
            self.assertEqual(uses(model, "SYS-CLAIMS-API"), ["TS-NET-SUB-CLAIMS-APP-A", "TS-NET-SUB-CLAIMS-APP-B"])
            self.assertEqual(uses(model, "SYS-CLAIMS-BUCKET"), [])
            subnet = model.get("tech_services", "TS-NET-SUB-CLAIMS-DATA-A")
            self.assertEqual((subnet["owner_org_id"], subnet["status"], subnet["availability_zone"]),
                             ("ORG-NET", "Planned", "eu-west-2a"))
            self.assertIn(("TS-NET-VPC-CLAIMS", "network attachment"), joins(model, "TS-HUB"))
            # A network that says nothing of its subnets has the standard
            # layout: three tiers across two zones, a NAT gateway in each.
            cards = [t for t in model.all_of("tech_services") if t.get("archetype_instance") == "TS-NET-VPC-CARDS"]
            self.assertEqual(sorted((t["component_type"], t.get("network_zone"), t["availability_zone"]) for t in cards), [
                ("nat-gateway", "Public", "eu-west-2a"), ("nat-gateway", "Public", "eu-west-2b"),
                ("subnet", "Private-App", "eu-west-2a"), ("subnet", "Private-App", "eu-west-2b"),
                ("subnet", "Private-Data", "eu-west-2a"), ("subnet", "Private-Data", "eu-west-2b"),
                ("subnet", "Public", "eu-west-2a"), ("subnet", "Public", "eu-west-2b")])


class TestTheSubnetField(unittest.TestCase):
    def test_a_kind_says_whether_it_sits_in_a_subnet(self) -> None:
        from terrane.blocks import load_components

        library = load_components(REPO)
        for kind in ("object-store", "bi", "cdn", "crm", "identity-provider", "foundation-model-service"):
            self.assertFalse(library[kind].subnet, kind)
        for kind in ("relational-db", "web-app", "service-api", "etl", "container-platform"):
            self.assertTrue(library[kind].subnet, kind)
        with self.assertRaises(LibraryError):
            parse_component({"component_type_id": "x", "subnet": "no"})


if __name__ == "__main__":
    unittest.main()
