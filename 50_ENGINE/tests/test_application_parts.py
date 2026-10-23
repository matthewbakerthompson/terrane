"""Tests for the standard components of an application and the standard
applications made of them.

What is checked: each application kit composes into a shape on AWS and, where
its parts land there, on Azure; expands with the systems and interfaces it
promises; the kinds its parts ask for (the API gateway, the identity
provider, the bus, the foundation model service) resolve on the landing zone;
the application types in 29_TYPES hold a product to the kit they require; and
the library counts a part the types list as composed.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import blocks, model as model_module, validate  # noqa: E402
from terrane.archetype import expand, landing_zone_index, parse_archetype  # noqa: E402
from terrane.build_types import check_build_types, conformance, load_build_types  # noqa: E402
from terrane.compose import archetype_text_from_parts  # noqa: E402
from terrane.loader import load_folder, read_data_file, parse_data_text  # noqa: E402
from terrane.answers import estate_answers  # noqa: E402
from terrane.modules import load_modules, members_of  # noqa: E402

from _fixture import REPO  # noqa: E402

VOCAB = ["slug", "product_name", "owner_org", "domain", "account", "region", "criticality", "classification"]

BLOCKS = {
    "AWS": [
        {"block": "stateless-service", "bind": {"container-platform": "TS-AWS-EKS", "observability": "TS-AWS-CLOUDWATCH"}},
        {"block": "transactional-store", "bind": {"relational-db": "TS-AWS-RDS", "kms": "TS-AWS-KMS"}},
        {"block": "public-web-tier", "bind": {"cdn": "TS-AWS-CLOUDFRONT", "load-balancer": "TS-AWS-ALB"}},
    ],
    "Azure": [
        {"block": "stateless-service", "bind": {"container-platform": "TS-AZURE-AKS", "observability": "TS-AZURE-MONITOR"}},
        {"block": "transactional-store", "bind": {"relational-db": "TS-AZURE-SQL", "kms": "TS-AZURE-KEYVAULT"}},
    ],
}

#: Each kit, the systems it promises for slug `probe`, and the answers the
#: kit itself asks for.
KITS = {
    "web-app-baseline": (["SYS-PROBE-API", "SYS-PROBE-WEB", "SYS-PROBE-EDGE", "SYS-PROBE-ALB", "SYS-PROBE-DB"], {}),
    "mobile-app-baseline": (["SYS-PROBE-API", "SYS-PROBE-MOBILE", "SYS-PROBE-DB"], {}),
    "internal-tool-baseline": (["SYS-PROBE-API", "SYS-PROBE-ADMIN", "SYS-PROBE-DB"], {}),
    "event-service-baseline": (["SYS-PROBE-API", "SYS-PROBE-CONSUMER", "SYS-PROBE-WORKER", "SYS-PROBE-EVENTS"],
                               {"source_system": "SYS-CORE-LEDGER"}),
    "batch-app-baseline": (["SYS-PROBE-API", "SYS-PROBE-JOBS", "SYS-PROBE-DB"], {}),
    "adapter-baseline": (["SYS-PROBE-API", "SYS-PROBE-ADAPTER"], {"partner": "Experian", "target_system": "SYS-CREDIT-BUREAU"}),
    "ml-service-baseline": (["SYS-PROBE-API", "SYS-PROBE-INFERENCE"], {}),
    "reporting-baseline": (["SYS-PROBE-API", "SYS-PROBE-DB", "SYS-PROBE-REPORTS"], {}),
}

#: Kits whose parts run on the public web tier, which the Azure shapes do not
#: carry; those are composed on AWS only.
AWS_ONLY = {"web-app-baseline"}


def _library():
    components = blocks.load_components(REPO)
    landing = landing_zone_index(
        record for _path, record in load_folder(REPO / "10_MODEL" / "tech_services")
        if isinstance(record, dict)
    )
    # And what the estate answers, as the loader passes it: the parts ask the
    # estate who owns the egress and where the audit trail goes.
    answers = estate_answers(read_data_file(REPO / "10_MODEL" / "model.yaml"))
    return components, blocks.load_blocks(REPO, components), load_modules(REPO), landing, answers


def _expand(kit_id: str, provider: str, answers: dict):
    text = archetype_text_from_parts(
        REPO, archetype_id="probe-" + kit_id, title="Probe", description="A probe of one kit.",
        parameters=VOCAB, provider=provider,
        modules=[{"module": kit_id, "with": answers}] if answers else [{"module": kit_id}],
        blocks=BLOCKS[provider],
    )
    shape = parse_archetype(parse_data_text(text, "test"))
    instance = {"product_id": "PRD-PROBE", "name": "Probe", "status": "Planned", "owner_org_id": "ORG-TECH",
                "parameters": {"slug": "probe", "product_name": "Probe", "owner_org": "ORG-TECH",
                               "domain": "Probing", "account": "prod-probe"}}
    return expand(instance, shape, "products", _library())


class TestKits(unittest.TestCase):
    def test_every_kit_expands_on_aws_with_the_systems_it_promises(self) -> None:
        for kit_id, (systems, answers) in KITS.items():
            with self.subTest(kit=kit_id):
                out = _expand(kit_id, "AWS", answers)
                got = sorted(s["system_id"] for s in out.entities["systems"])
                self.assertEqual(got, sorted(systems))
                for member in members_of(load_modules(REPO)[kit_id], load_modules(REPO)):
                    self.assertIn(member, out.modules_applied)

    def test_the_same_kits_expand_on_azure(self) -> None:
        for kit_id, (systems, answers) in KITS.items():
            if kit_id in AWS_ONLY:
                continue
            with self.subTest(kit=kit_id):
                out = _expand(kit_id, "Azure", answers)
                got = sorted(s["system_id"] for s in out.entities["systems"])
                self.assertEqual(got, sorted(systems))

    def test_the_components_wire_to_the_api_and_to_what_they_use(self) -> None:
        out = _expand("mobile-app-baseline", "AWS", {})
        interfaces = {i["interface_id"]: i for i in out.entities["interfaces"]}
        self.assertEqual(interfaces["INT-PROBE-MOBILE-API"]["target_system_id"], "SYS-PROBE-API")
        uses = {(r["system_id"], r["tech_service_id"]) for r in out.relations.get("system_uses_tech_service", [])}
        # The app reaches the API through the AWS landing zone's gateway.
        self.assertIn(("SYS-PROBE-MOBILE", "TS-AWS-APIGW"), uses)
        out = _expand("ml-service-baseline", "Azure", {})
        uses = {(r["system_id"], r["tech_service_id"]) for r in out.relations.get("system_uses_tech_service", [])}
        self.assertIn(("SYS-PROBE-INFERENCE", "TS-AZURE-FOUNDRY"), uses)
        out = _expand("internal-tool-baseline", "AWS", {})
        uses = {(r["system_id"], r["tech_service_id"]) for r in out.relations.get("system_uses_tech_service", [])}
        self.assertIn(("SYS-PROBE-ADMIN", "TS-ENTRA-ID"), uses)
        out = _expand("adapter-baseline", "AWS", {"partner": "Experian", "target_system": "SYS-CREDIT-BUREAU"})
        interfaces = {i["interface_id"]: i for i in out.entities["interfaces"]}
        self.assertEqual(interfaces["INT-PROBE-ADAPTER-PARTNER"]["target_system_id"], "SYS-CREDIT-BUREAU")
        self.assertIn("Experian", out.entities["systems"][-1]["name"] + "".join(s["name"] for s in out.entities["systems"]))


class TestApplicationTypes(unittest.TestCase):
    def test_the_application_types_name_real_kits_and_parts(self) -> None:
        types = load_build_types(REPO)
        modules = load_modules(REPO)
        model = model_module.load(REPO)
        self.assertEqual(check_build_types(types, modules, model.archetypes.values()), [])
        for type_id in ("internal-tool", "mobile-application", "event-driven-service", "batch-application",
                        "integration-adapter", "ai-service", "reporting-application", "web-application"):
            self.assertIn(type_id, types)
            self.assertTrue(all(modules[r].is_kit for r in types[type_id].requires))

    def test_a_type_holds_a_product_to_its_kit(self) -> None:
        types = load_build_types(REPO)
        modules = load_modules(REPO)
        whole = conformance(types["internal-tool"], ["api-service", "admin-console", "relational-datastore"], modules)
        self.assertTrue(whole.clean)
        partial = conformance(types["internal-tool"], ["api-service", "relational-datastore"], modules)
        self.assertEqual(partial.missing, ["internal-tool-baseline"])

    def test_a_part_the_types_list_counts_as_composed(self) -> None:
        report = validate.run(model_module.load(REPO))
        unused = [f.message for f in report.findings if f.code == "library.unused_part"]
        for part in ("mobile-channel", "admin-console", "scheduled-job", "event-consumer", "notification-service",
                     "search-index", "ml-inference-service", "report-service", "partner-adapter", "internal-tool-baseline"):
            self.assertFalse(any(part in m for m in unused), part)
        gaps = [f.message for f in report.findings if f.code == "library.landing_zone_gap"]
        self.assertEqual(gaps, [])


if __name__ == "__main__":
    unittest.main()
