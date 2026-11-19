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
    "GCP": [
        {"block": "stateless-service", "bind": {"container-platform": "TS-GCP-GKE", "observability": "TS-GCP-MONITORING"}},
        {"block": "transactional-store", "bind": {"relational-db": "TS-GCP-CLOUD-SQL", "kms": "TS-GCP-KMS"}},
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
    "ai-assistant-baseline": (["SYS-PROBE-API", "SYS-PROBE-CHAT", "SYS-PROBE-INFERENCE", "SYS-PROBE-INGEST",
                               "SYS-PROBE-INDEX", "SYS-PROBE-HISTORY"], {}),
    "ai-agent-baseline": (["SYS-PROBE-API", "SYS-PROBE-AGENT", "SYS-PROBE-ACTIONS"], {}),
    "customer-portal-baseline": (["SYS-PROBE-API", "SYS-PROBE-WEB", "SYS-PROBE-EDGE", "SYS-PROBE-ALB", "SYS-PROBE-DB",
                                  "SYS-PROBE-NOTIFY"], {}),
    "partner-api-baseline": (["SYS-PROBE-API", "SYS-PROBE-DB"], {"partners": ["SYS-CREDIT-BUREAU"]}),
}

#: Kits whose parts run on the public web tier, which the Azure shapes do not
#: carry; those are composed on AWS only.
AWS_ONLY = {"web-app-baseline", "customer-portal-baseline"}


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


class TestTheAIAssistant(unittest.TestCase):
    """One component on the canvas and never one box: a chat behind
    workforce sign-on, the API, the inference service calling the model
    through the AI gateway, the retrieval index and the conversations."""

    WANT = {
        "AWS": ("TS-AWS-BEDROCK", "TS-AWS-BEDROCK-GUARDRAILS", "TS-AWS-OPENSEARCH"),
        "Azure": ("TS-AZURE-FOUNDRY", "TS-AZURE-APIM", "TS-AZURE-AI-SEARCH"),
        "GCP": ("TS-GCP-GEMINI-PLATFORM", "TS-GCP-MODEL-ARMOR", "TS-GCP-VECTOR-SEARCH"),
    }

    def test_every_cloud_answers_what_it_asks_for(self) -> None:
        for provider, (models, gateway, vectors) in self.WANT.items():
            with self.subTest(provider=provider):
                out = _expand("ai-assistant-baseline", provider, {})
                uses = {(r["system_id"], r["tech_service_id"]) for r in out.relations.get("system_uses_tech_service", [])}
                # Every model call through the gateway; the passages embedded
                # with the same models; the index on the landing zone's vectors.
                self.assertIn(("SYS-PROBE-INFERENCE", models), uses)
                self.assertIn(("SYS-PROBE-INFERENCE", gateway), uses)
                self.assertIn(("SYS-PROBE-INGEST", models), uses)
                self.assertIn(("SYS-PROBE-INDEX", vectors), uses)
                self.assertIn(("SYS-PROBE-CHAT", "TS-ENTRA-ID"), uses)

    def test_the_parts_wire_as_an_assistant_does(self) -> None:
        out = _expand("ai-assistant-baseline", "AWS", {"sources": ["SYS-CRM", "SYS-ERP"]})
        lines = {(i["source_system_id"], i["target_system_id"]) for i in out.entities["interfaces"]}
        for line in (("SYS-PROBE-CHAT", "SYS-PROBE-API"), ("SYS-PROBE-API", "SYS-PROBE-INFERENCE"),
                     ("SYS-PROBE-INFERENCE", "SYS-PROBE-INDEX"), ("SYS-PROBE-INGEST", "SYS-PROBE-INDEX"),
                     ("SYS-PROBE-INFERENCE", "SYS-PROBE-HISTORY"),
                     # The documents it was told to answer from, each a feed.
                     ("SYS-CRM", "SYS-PROBE-INGEST"), ("SYS-ERP", "SYS-PROBE-INGEST")):
            self.assertIn(line, lines)
        assets = {a["data_asset_id"]: a for a in out.entities["data_assets"]}
        self.assertEqual(assets["DA-PROBE-CONVERSATIONS"]["pii_flag"], "Yes")
        self.assertEqual(assets["DA-PROBE-KNOWLEDGE"]["source_of_truth"], "SYS-PROBE-INDEX")
        reads = {(r["system_id"], r["data_asset_id"], r["operation"]) for r in out.relations["system_reads_writes"]}
        self.assertIn(("SYS-PROBE-INGEST", "DA-PROBE-KNOWLEDGE", "Write"), reads)
        self.assertIn(("SYS-PROBE-INFERENCE", "DA-PROBE-KNOWLEDGE", "Read"), reads)

    def test_the_second_estates_azure_answers_it_too(self) -> None:
        from terrane.archetype import resolve_kind

        thurman = REPO / "90_EXAMPLE" / "thurman-health"
        zone = landing_zone_index(
            record for _path, record in load_folder(thurman / "10_MODEL" / "tech_services")
            if isinstance(record, dict) and not record.get("archetype")
        )
        for kind, want in (("foundation-model-service", "TS-AZURE-FOUNDRY"), ("ai-gateway", "TS-AZURE-APIM"),
                           ("vector-database", "TS-AZURE-AI-SEARCH"), ("identity-provider", "TS-IDENTITY")):
            self.assertEqual(resolve_kind(kind, "Azure", zone)[0], want, kind)


def _expand_parts(modules: list, provider: str):
    """Parts assembled on their own, with the parts they require."""
    text = archetype_text_from_parts(
        REPO, archetype_id="probe-parts", title="Probe", description="A probe of some parts.",
        parameters=VOCAB, provider=provider, modules=modules, blocks=BLOCKS[provider],
    )
    shape = parse_archetype(parse_data_text(text, "test"))
    instance = {"product_id": "PRD-PROBE", "name": "Probe", "status": "Planned", "owner_org_id": "ORG-TECH",
                "parameters": {"slug": "probe", "product_name": "Probe", "owner_org": "ORG-TECH",
                               "domain": "Probing", "account": "prod-probe"}}
    return expand(instance, shape, "products", _library())


def _uses(out):
    return {(r["system_id"], r["tech_service_id"]) for r in out.relations.get("system_uses_tech_service", [])}


class TestWhatOrganizationsBuildAgain(unittest.TestCase):
    """The parts most organizations come to need: an AI agent, customer
    sign-in, a feed to analytics, a partner API and document intake, each
    resolved on every cloud's landing zone."""

    def test_an_agent_acts_through_the_tools_it_is_given(self) -> None:
        for provider, platform, gateway in (("AWS", "TS-AWS-AGENTCORE", "TS-AWS-BEDROCK-GUARDRAILS"),
                                            ("Azure", "TS-AZURE-FOUNDRY", "TS-AZURE-APIM"),
                                            ("GCP", "TS-GCP-GEMINI-PLATFORM", "TS-GCP-MODEL-ARMOR")):
            with self.subTest(provider=provider):
                out = _expand("ai-agent-baseline", provider, {"tools": ["SYS-CRM", "SYS-CORE-LEDGER"]})
                self.assertIn(("SYS-PROBE-AGENT", platform), _uses(out))
                self.assertIn(("SYS-PROBE-AGENT", gateway), _uses(out))
                lines = {(i["source_system_id"], i["target_system_id"]) for i in out.entities["interfaces"]}
                for line in (("SYS-PROBE-API", "SYS-PROBE-AGENT"), ("SYS-PROBE-AGENT", "SYS-PROBE-ACTIONS"),
                             ("SYS-PROBE-AGENT", "SYS-CRM"), ("SYS-PROBE-AGENT", "SYS-CORE-LEDGER")):
                    self.assertIn(line, lines)

    def test_customers_sign_in_on_the_clouds_customer_identity(self) -> None:
        for provider, ciam in (("AWS", "TS-AWS-COGNITO"), ("Azure", "TS-AZURE-EXTERNAL-ID"),
                               ("GCP", "TS-GCP-IDENTITY-PLATFORM")):
            with self.subTest(provider=provider):
                out = _expand_parts([{"module": "api-service"}, {"module": "web-channel"},
                                     {"module": "customer-sign-in"}], provider)
                self.assertIn(("SYS-PROBE-WEB", ciam), _uses(out))
                self.assertIn(("SYS-PROBE-API", ciam), _uses(out))

    def test_the_feed_to_analytics_is_change_data_capture(self) -> None:
        from terrane.connections import kind_of, load_connections

        out = _expand_parts([{"module": "api-service"}, {"module": "relational-datastore"},
                             {"module": "analytics-feed"}], "AWS")
        feed = {i["interface_id"]: i for i in out.entities["interfaces"]}["INT-PROBE-DB-ANALYTICS"]
        # Off the product's database into the estate's ingestion, the way out
        # of a database the library offers first.
        self.assertEqual((feed["source_system_id"], feed["target_system_id"]), ("SYS-PROBE-DB", "SYS-DATA-INGEST"))
        self.assertEqual(kind_of(feed, load_connections(REPO)), "change-data-capture")
        carried = {(r["interface_id"], r["data_asset_id"]) for r in out.relations["interface_transports_data_asset"]}
        self.assertIn(("INT-PROBE-DB-ANALYTICS", "DA-PROBE-OPERATIONAL"), carried)

    def test_partners_reach_the_api_through_the_gateway(self) -> None:
        out = _expand_parts([{"module": "api-service"},
                             {"module": "partner-api", "with": {"partners": ["SYS-CREDIT-BUREAU"]}}], "Azure")
        offered = {o["offered_interface_id"] for o in out.entities["offered_interfaces"]}
        self.assertIn("OI-PROBE-PARTNER-API", offered)
        call = [i for i in out.entities["interfaces"] if i["source_system_id"] == "SYS-CREDIT-BUREAU"][0]
        self.assertEqual((call["target_system_id"], call["offered_interface_id"]), ("SYS-PROBE-API", "OI-PROBE-PARTNER-API"))
        self.assertIn(("SYS-PROBE-API", "TS-AZURE-APIM"), _uses(out))

    def test_documents_are_read_by_the_clouds_document_processing(self) -> None:
        for provider, reader in (("AWS", "TS-AWS-TEXTRACT"), ("Azure", "TS-AZURE-DOC-INTELLIGENCE"),
                                 ("GCP", "TS-GCP-DOCUMENT-AI")):
            with self.subTest(provider=provider):
                out = _expand_parts([{"module": "api-service"}, {"module": "object-store"},
                                     {"module": "document-intake"}], provider)
                self.assertIn(("SYS-PROBE-INTAKE", reader), _uses(out))
                lines = {(i["source_system_id"], i["target_system_id"]) for i in out.entities["interfaces"]}
                self.assertIn(("SYS-PROBE-BUCKET", "SYS-PROBE-INTAKE"), lines)
                self.assertIn(("SYS-PROBE-INTAKE", "SYS-PROBE-API"), lines)

    def test_a_kind_a_part_uses_by_default_is_asked_of_every_landing_zone(self) -> None:
        # The object store part uses `object-store` by default; without the
        # Azure object store the check said nothing, and document intake on
        # Azure was refused when it was assembled.
        from terrane.archetype import landing_zone_gaps

        model = model_module.load(REPO)
        components = blocks.load_components(REPO)
        without = landing_zone_index(s for s in model.all_of("tech_services") if s["tech_service_id"] != "TS-AZURE-BLOB")
        gaps = landing_zone_gaps(load_modules(REPO), model.archetypes.values(), without, kinds=components)
        self.assertIn(("Azure", "object-store"), {(g.provider, g.kind) for g in gaps})
        whole = landing_zone_index(model.all_of("tech_services"))
        self.assertEqual(landing_zone_gaps(load_modules(REPO), model.archetypes.values(), whole, kinds=components), [])

    def test_the_second_estates_azure_answers_them_too(self) -> None:
        from terrane.archetype import resolve_kind

        thurman = REPO / "90_EXAMPLE" / "thurman-health"
        zone = landing_zone_index(
            record for _path, record in load_folder(thurman / "10_MODEL" / "tech_services")
            if isinstance(record, dict) and not record.get("archetype")
        )
        for kind, want in (("agent-platform", "TS-AZURE-FOUNDRY"), ("customer-identity", "TS-AZURE-EXTERNAL-ID"),
                           ("document-ai", "TS-AZURE-DOC-INTELLIGENCE")):
            self.assertEqual(resolve_kind(kind, "Azure", zone)[0], want, kind)


class TestApplicationTypes(unittest.TestCase):
    def test_the_application_types_name_real_kits_and_parts(self) -> None:
        types = load_build_types(REPO)
        modules = load_modules(REPO)
        model = model_module.load(REPO)
        self.assertEqual(check_build_types(types, modules, model.archetypes.values()), [])
        for type_id in ("internal-tool", "mobile-application", "event-driven-service", "batch-application",
                        "integration-adapter", "ai-service", "ai-assistant", "ai-agent", "reporting-application",
                        "web-application", "customer-portal", "partner-facing-api"):
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
                     "search-index", "ml-inference-service", "report-service", "partner-adapter", "internal-tool-baseline",
                     "assistant-chat", "retrieval-index", "conversation-history", "ai-assistant-baseline",
                     "agent-service", "ai-agent-baseline", "customer-sign-in", "analytics-feed", "partner-api",
                     "document-intake", "customer-portal-baseline", "partner-api-baseline"):
            self.assertFalse(any(part in m for m in unused), part)
        gaps = [f.message for f in report.findings if f.code == "library.landing_zone_gap"]
        self.assertEqual(gaps, [])


if __name__ == "__main__":
    unittest.main()
