"""The marks in the corner: the provider's own on a technology service, the
vendor's on a bought system where the vendor lets the mark travel, every
shipped file credited, and the technology line naming a vendor in words."""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.blocks import load_components  # noqa: E402
from terrane.icons import IconMap, web_dir  # noqa: E402
from terrane.techline import TechnologyLines  # noqa: E402

from _fixture import REPO, remove_scratch, seeded_model, seeded_root  # noqa: E402

WEB = REPO / "80_APP" / "web"


class TestIcons(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.icons = IconMap(WEB)

    def test_the_engine_finds_the_marks_beside_the_model_or_beside_itself(self) -> None:
        # The files stay with the app; the engine knows where they are, from
        # the model's root or, for a model rendered from another folder, its
        # own checkout, and says nothing where neither has them.
        self.assertEqual(web_dir(REPO), WEB)
        self.assertEqual(web_dir(seeded_root()), WEB)
        self.assertEqual(web_dir(Path("/nowhere")), WEB)
        # The bytes of a served path, for a painter; nothing for nothing.
        self.assertTrue(self.icons.read("icons/aws/eks.svg").lstrip().startswith(b"<"))
        self.assertIsNone(self.icons.read(""))
        self.assertIsNone(self.icons.read("icons/aws/no-such-mark.svg"))
        self.assertIsNone(self.icons.read("../50_ENGINE/terrane/icons.py"))

    def test_every_mapped_file_is_shipped_and_credited(self) -> None:
        data = json.loads((WEB / "icons" / "map.json").read_text(encoding="utf-8"))
        referenced = set(data["vendors"].values())
        for table in data["providers"].values():
            referenced.update(table["names"].values())
            referenced.update(table["kinds"].values())
        referenced.update(data["groups"].values())
        self.assertGreater(len(referenced), 100)
        missing = sorted(f for f in referenced if not (WEB / "icons" / f).exists())
        self.assertEqual(missing, [])
        credits = (WEB / "icons" / "CREDITS.md").read_text(encoding="utf-8")
        for owner in ("AWS", "Microsoft", "Google", "Simple Icons", "ServiceNow", "Workday"):
            self.assertIn(owner, credits)
        self.assertEqual(set(data["sources"]), {"aws", "azure", "gcp", "brands"})
        # A vendor mark carries its color: the collection's files have none
        # and would draw black.
        for mark in (WEB / "icons" / "brands").glob("*.svg"):
            head = mark.read_text(encoding="utf-8")[:200]
            self.assertRegex(head, r'<svg[^>]*\sfill="#[0-9A-Fa-f]{6}"', mark.name)

    def test_a_technology_service_carries_the_mark_of_what_it_is(self) -> None:
        of = self.icons.for_node
        self.assertEqual(of("tech_services", {"cloud_provider": "AWS", "name": "Amazon EKS", "service_name": "EKS"}), "icons/aws/eks.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "AWS", "name": "Amazon CloudFront and WAF", "service_name": "CloudFront"}), "icons/aws/cloudfront.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "AWS", "name": "Lending Public Subnet A", "service_name": "Subnet"}), "icons/aws/public-subnet.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "AWS", "name": "Lending App Subnet A", "service_name": "Subnet"}), "icons/aws/private-subnet.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "AWS", "name": "Lending NAT Gateway A", "service_name": "NAT Gateway"}), "icons/aws/nat-gateway.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "AWS", "name": "Installment Lending DNS", "product": "Amazon Route 53", "component_type": "dns"}), "icons/aws/route53.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "Azure", "name": "Azure SQL Database", "service_name": "Azure SQL"}), "icons/azure/sql-database.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "Azure", "name": "Merchant Portal Cache", "product": "Azure Cache for Redis"}), "icons/azure/cache-redis.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "GCP", "name": "Cloud SQL for PostgreSQL", "service_name": "Cloud SQL"}), "icons/gcp/cloud-sql.svg")
        # A name the map does not know falls back to the kind of component.
        self.assertEqual(of("tech_services", {"cloud_provider": "Azure", "name": "Platform Telemetry", "component_type": "observability"}), "icons/azure/monitor.svg")
        self.assertEqual(of("tech_services", {"cloud_provider": "Azure", "name": "Platform Thing", "component_type": "no-such-kind"}), "")
        # A vendor's own service, of no cloud of ours.
        self.assertEqual(of("tech_services", {"name": "Microsoft Entra ID", "service_name": "Entra ID"}), "icons/azure/entra-id.svg")
        self.assertEqual(of("tech_services", {"name": "Snowflake", "service_name": "Snowflake Data Cloud"}), "icons/brands/snowflake.svg")
        self.assertEqual(of("tech_services", {"name": "ServiceNow", "service_name": "ServiceNow ITSM and CMDB", "component_type": "itsm"}), "")
        self.assertEqual(of("tech_services", {"name": "Collibra", "service_name": "Collibra Data Intelligence", "component_type": "catalog"}), "")

    def test_a_boundary_carries_the_mark_of_the_kind_of_container_it_is(self) -> None:
        of = self.icons.for_group
        self.assertEqual(of("AWS"), "icons/aws/group-cloud.svg")
        self.assertEqual(of("AWS account"), "icons/aws/group-account.svg")
        self.assertEqual(of("AWS region"), "icons/aws/group-region.svg")
        self.assertEqual(of("public subnet"), "icons/aws/public-subnet.svg")
        self.assertEqual(of("private subnet"), "icons/aws/private-subnet.svg")
        self.assertEqual(of("Azure subscription"), "icons/azure/subscriptions.svg")
        self.assertEqual(of("on-prem"), "icons/aws/group-data-center.svg")
        # Google draws its containers as labeled boxes, and so do we; an
        # availability zone is a dashed box on every cloud.
        self.assertEqual(of("GCP project"), "")
        self.assertEqual(of("AWS availability zone"), "")
        self.assertEqual(of(""), "")

    def test_a_bought_system_carries_its_vendor_s_mark_where_it_may(self) -> None:
        of = self.icons.for_node
        self.assertEqual(of("systems", {"provider": "Microsoft Sentinel", "name": "Security Monitoring", "hosting": "SaaS"}), "icons/azure/sentinel.svg")
        self.assertEqual(of("systems", {"provider": "Snowflake", "name": "Customer 360 Semantic Layer", "hosting": "SaaS"}), "icons/brands/snowflake.svg")
        self.assertEqual(of("systems", {"hosting": "SaaS", "name": "Datadog APM"}), "icons/brands/datadog.svg")
        # A mark the collection has withdrawn at its owner's request is not
        # shipped, so the vendor is named under the system instead.
        self.assertEqual(of("systems", {"provider": "Microsoft", "name": "Dynamics 365 Customer Service", "hosting": "SaaS"}), "")
        self.assertEqual(of("systems", {"hosting": "SaaS", "name": "Salesforce CRM"}), "")
        self.assertFalse((WEB / "icons" / "brands" / "microsoft.svg").exists())
        # The vendors who keep their marks home get none; the line names them.
        self.assertEqual(of("systems", {"provider": "Pegasystems", "name": "Pega Smart Dispute", "hosting": "SaaS"}), "")
        self.assertEqual(of("systems", {"provider": "Workday", "name": "HR platform", "hosting": "SaaS"}), "")
        # A system of ours carries no vendor's mark whatever its name says:
        # the mark it wears is its platform's, which the payload adds.
        self.assertEqual(of("systems", {"provider": "In-house", "name": "Snowflake Loader", "hosting": "Azure"}), "")
        self.assertEqual(of("systems", {"name": "Core Card Ledger", "hosting": "On-prem"}), "")
        self.assertEqual(of("capabilities", {"name": "Salesforce"}), "")

    def test_a_bought_system_names_its_vendor_under_its_name(self) -> None:
        root = seeded_root()
        lines = TechnologyLines(seeded_model(), load_components(root))
        self.assertEqual(lines.of("systems", {"system_id": "SYS-NOPE", "hosting": "SaaS", "provider": "Workday"}), "Workday")
        self.assertEqual(lines.of("systems", {"system_id": "SYS-NOPE", "hosting": "SaaS", "provider": "ServiceNow"}), "ServiceNow")
        self.assertEqual(lines.of("systems", {"system_id": "SYS-NOPE", "hosting": "SaaS"}), "SaaS")
        self.assertEqual(lines.of("systems", {"system_id": "SYS-NOPE", "hosting": "Azure", "provider": "In-house"}), "")

    def test_a_system_of_ours_wears_the_mark_of_what_it_runs_on(self) -> None:
        """The service its technology line names first, so the logo and the
        words agree: AKS over "AKS · Event Hubs", Azure SQL over "Azure SQL".
        A system with no platform service wears nothing."""
        model = seeded_model()
        lines = TechnologyLines(model, load_components(seeded_root()))
        worn = 0
        for system in model.all_of("systems"):
            if self.icons.for_node("systems", system):
                continue
            lead = lines.lead(system)
            line = lines.of("systems", system)
            if lead is None:
                self.assertFalse(line and line not in ("SaaS", "external") and line != system.get("provider"), line)
                continue
            first = str(lead.get("service_name") or lead.get("name"))
            self.assertTrue(line.startswith(first), (line, first))
            if self.icons.for_node("tech_services", lead):
                worn += 1
        self.assertGreater(worn, 20)

    def test_every_mark_is_served_with_a_size(self) -> None:
        """A canvas drew a mark that says only its viewBox as a fragment:
        the Snowflake mark was a blue corner. The files stay as published;
        what is served and baked says its size."""
        import re
        from terrane.icons import sized

        marks = sorted((WEB / "icons").rglob("*.svg"))
        self.assertGreater(len(marks), 100)
        for mark in marks:
            with self.subTest(mark=mark.name):
                tag = re.search(rb"<svg\b[^>]*>", sized(mark.read_bytes())).group(0)
                self.assertRegex(tag, rb"\swidth=")
                self.assertRegex(tag, rb"\sheight=")
        snowflake = sized((WEB / "icons" / "brands" / "snowflake.svg").read_bytes())
        self.assertIn(b'<svg width="64" height="64" ', snowflake)
        # One that says its size is left as it is.
        eks = (WEB / "icons" / "aws" / "eks.svg").read_bytes()
        self.assertEqual(sized(eks), eks)

    def test_the_payload_carries_the_mark(self) -> None:
        root = seeded_root()
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        payload = server_module.api_graph({"view": ["technology-stack"]}, None)
        nodes = {e["data"]["id"]: e["data"] for e in payload["elements"] if not e["data"].get("isGroup") and not e["data"].get("source")}
        aks = next((n for n in nodes.values() if "Kubernetes" in n["label"] and n["entityType"] == "tech_services"), None)
        self.assertIsNotNone(aks)
        self.assertTrue(aks["icon"].startswith("icons/"), aks)
        self.assertTrue((WEB / aks["icon"][len("icons/"):]).exists() or (WEB / aks["icon"]).exists())
        self.assertTrue(all("icon" in n for n in nodes.values()))
        landscape = server_module.api_graph({"view": ["application-landscape"]}, None)
        systems = {e["data"]["id"]: e["data"] for e in landscape["elements"] if e["data"].get("entityType") == "systems"}
        self.assertEqual(systems["SYS-LENDING-API"]["icon"], "icons/aws/eks.svg")
        self.assertTrue(systems["SYS-LENDING-API"]["tech"].startswith("EKS"))
        network = server_module.api_graph({"view": ["network-topology"]}, None)
        groups = {e["data"]["bkey"]: e["data"] for e in network["elements"] if e["data"].get("isGroup")}
        self.assertEqual(groups["AWS account"]["icon"], "icons/aws/group-account.svg")
        self.assertEqual(groups["AWS region"]["icon"], "icons/aws/group-region.svg")
        self.assertEqual(groups["GCP project"]["icon"], "")



class TestTheCurationClearsOnlyWhatItWrote(unittest.TestCase):
    """`curate_icons.py` empties the icons folder file by file, and only a
    folder that holds what a curation writes: it once removed the folder
    whole, on a path worked out from its own."""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(REPO / "80_APP" / "tools"))
        cls.curate = importlib.import_module("curate_icons")

    def test_the_shipped_folder_is_one_it_would_clear(self) -> None:
        """Read only: the listing a curation would remove, every file in it."""
        listed = self.curate.curated_files(WEB / "icons")
        self.assertEqual(sorted(listed), sorted(p for p in (WEB / "icons").rglob("*") if p.is_file()))
        self.assertIn(WEB / "icons" / "map.json", listed)

    def test_a_folder_holding_anything_else_is_refused_whole(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-icons-"))
        self.addCleanup(remove_scratch, folder, "aac-icons-")
        (folder / "aws").mkdir()
        (folder / "aws" / "eks.svg").write_text("<svg/>", encoding="utf-8")
        (folder / "map.json").write_text("{}", encoding="utf-8")
        for stray in (folder / "notes.txt", folder / "aws" / "notes.txt"):
            with self.subTest(stray=stray.name):
                stray.write_text("mine", encoding="utf-8")
                with self.assertRaises(SystemExit) as caught:
                    self.curate.curated_files(folder)
                self.assertIn("nothing was removed", str(caught.exception))
                stray.unlink()
        self.assertEqual(len(self.curate.curated_files(folder)), 2)


if __name__ == "__main__":
    unittest.main()
