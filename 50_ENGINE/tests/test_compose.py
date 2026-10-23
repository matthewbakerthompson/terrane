"""Tests for composing a shape from parts, and a project from them.

The claim is that an archetype can be chosen rather than written: pick the
modules, the blocks with what the landing zone provides, the patterns and the
vocabulary, and the file comes out in the form the shipped shapes have. What
is checked here is that the text parses as an archetype, expands, asks the
instance for what a chosen part still needs, refuses a part without what it
requires, and derives the same entity defaults the shipped shapes carry.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import blocks, importer, model as model_module  # noqa: E402
from terrane.archetype import expand, landing_zone_index, parse_archetype  # noqa: E402
from terrane.compose import keep_comments, ComposeError, archetype_from_parts, archetype_text_from_parts, entity_defaults_for  # noqa: E402
from terrane.loader import load_folder, read_data_file, parse_data_text  # noqa: E402
from terrane.answers import estate_answers  # noqa: E402
from terrane.modules import load_modules  # noqa: E402

from _fixture import EXAMPLE_CSV, REPO, Sandbox  # noqa: E402

VOCAB = ["slug", "product_name", "owner_org", "domain", "account", "region", "criticality", "classification"]


def _library():
    components = blocks.load_components(REPO)
    # With the landing zone, so a part's kinds resolve the way they do in
    # the app and the loader: the shipped shapes bind nothing themselves.
    landing = landing_zone_index(
        record for _path, record in load_folder(REPO / "10_MODEL" / "tech_services")
        if isinstance(record, dict)
    )
    # And what the estate answers, as the loader passes it: the parts ask the
    # estate who owns the egress and where the audit trail goes.
    answers = estate_answers(read_data_file(REPO / "10_MODEL" / "model.yaml"))
    return components, blocks.load_blocks(REPO, components), load_modules(REPO), landing, answers


class TestEntityDefaults(unittest.TestCase):
    def test_a_token_only_where_the_shape_has_the_parameter(self) -> None:
        d = entity_defaults_for("AWS", ["slug", "product_name", "owner_org", "domain"])
        self.assertEqual(d["all"]["company_domain"], "{domain}")
        self.assertEqual(d["systems"]["owner_org_id"], "{owner_org}")
        self.assertNotIn("cloud_account", d["systems"])
        self.assertEqual(d["systems"]["hosting"], "AWS")
        self.assertIn("tech_services", d)

    def test_no_provider_means_no_cloud_and_no_tech_service_block(self) -> None:
        d = entity_defaults_for(None, VOCAB)
        self.assertNotIn("hosting", d["systems"])
        self.assertNotIn("tech_services", d)
        self.assertEqual(d["systems"]["cloud_account"], "{account}")


class TestComposing(unittest.TestCase):
    def test_a_composed_shape_parses_expands_and_asks_for_what_a_part_needs(self) -> None:
        text = archetype_text_from_parts(
            REPO, archetype_id="probe-shape", title="Probe shape", description="A probe.",
            parameters=VOCAB, provider="AWS",
            modules=[{"module": "api-service"}, {"module": "web-channel"}, {"module": "vendor-tenancy"},
                     {"module": "api-outbound"}],
            blocks=[{"block": "stateless-service", "bind": {"container-platform": "TS-AWS-EKS"}}],
            # The gateway's front door is a kind the block does not bind, so
            # the composer is told which service is the API gateway here.
            bind={"api-gateway": "TS-AWS-APIGW"},
            patterns=["workload-account-baseline"],
        )
        data = parse_data_text(text, "test")
        shape = parse_archetype(data)
        self.assertEqual(shape.archetype_id, "probe-shape")
        self.assertEqual(shape.bind, {"api-gateway": "TS-AWS-APIGW"})
        # api-outbound needs a caller_system the shape does not bind, so the
        # instance is asked for it.
        names = [p.name for p in shape.parameters]
        self.assertIn("caller_system", names)
        self.assertIn("vendor", names)
        self.assertTrue(next(p for p in shape.parameters if p.name == "caller_system").required)
        instance = {"product_id": "PRD-P", "name": "Probe", "status": "Planned", "owner_org_id": "ORG-TECH",
                    "parameters": {"slug": "probe", "product_name": "Probe", "owner_org": "ORG-TECH",
                                   "domain": "Probing", "account": "prod-probe", "caller_system": "SYS-CRM",
                                   "vendor": "Acme"}}
        out = expand(instance, shape, "products", _library())
        systems = sorted(s["system_id"] for s in out.entities["systems"])
        self.assertEqual(systems, ["SYS-PROBE-API", "SYS-PROBE-GATEWAY", "SYS-PROBE-VENDOR", "SYS-PROBE-WEB"])
        self.assertEqual(out.instance.get("patterns"), ["workload-account-baseline"])
        api = next(s for s in out.entities["systems"] if s["system_id"] == "SYS-PROBE-API")
        self.assertEqual(api["cloud_account"], "prod-probe")
        # A bound component creates nothing; the unbound ones are the product's own.
        created = {t["tech_service_id"] for t in out.entities.get("tech_services", [])}
        self.assertNotIn("TS-AWS-EKS", created)
        self.assertIn("TS-PROBE-CACHE", created)

    def test_a_part_without_what_it_requires_is_refused(self) -> None:
        with self.assertRaises(ComposeError) as caught:
            archetype_from_parts(REPO, "x", "X", "Desc.", VOCAB, modules=[{"module": "private-egress"}])
        self.assertIn("requires", str(caught.exception))

    def test_a_part_that_runs_on_a_missing_block_is_refused(self) -> None:
        with self.assertRaises(ComposeError) as caught:
            archetype_from_parts(REPO, "x", "X", "Desc.", VOCAB, provider="AWS",
                                 modules=[{"module": "api-service"}, {"module": "relational-datastore"}],
                                 blocks=[{"block": "stateless-service"}])
        self.assertIn("transactional-store", str(caught.exception))

    def test_blocks_need_a_provider(self) -> None:
        with self.assertRaises(ComposeError):
            archetype_from_parts(REPO, "x", "X", "Desc.", VOCAB, blocks=[{"block": "stateless-service"}])

    def test_unknown_parts_are_refused(self) -> None:
        for bad in ({"modules": [{"module": "no-such"}]}, {"blocks": [{"block": "no-such"}], "provider": "AWS"},
                    {"patterns": ["no-such"]}):
            with self.assertRaises(ComposeError):
                archetype_from_parts(REPO, "x", "X", "Desc.", VOCAB, **bad)

    def test_a_binding_must_name_a_component_of_the_block(self) -> None:
        with self.assertRaises(ComposeError):
            archetype_from_parts(REPO, "x", "X", "Desc.", VOCAB, provider="AWS",
                                 blocks=[{"block": "stateless-service", "bind": {"cdn": "TS-AWS-CLOUDFRONT"}}])

    def test_a_block_may_resolve_against_another_cloud(self) -> None:
        """Multi-cloud: one product, blocks on two providers."""
        data = archetype_from_parts(
            REPO, "x", "X", "Desc.", VOCAB, provider="AWS",
            blocks=[{"block": "stateless-service", "bind": {"container-platform": "TS-AWS-EKS"}},
                    {"block": "public-api-tier", "provider": "Azure", "bind": {"api-gateway": "TS-AZURE-APIM"}}],
        )
        by_id = {b["block"]: b for b in data["blocks"]}
        self.assertNotIn("provider", by_id["stateless-service"])
        self.assertEqual(by_id["public-api-tier"]["provider"], "Azure")
        text = archetype_text_from_parts(
            REPO, archetype_id="x", title="X", description="Desc.", parameters=VOCAB, provider="AWS",
            blocks=[{"block": "public-api-tier", "provider": "Azure"}],
        )
        shape = parse_archetype(parse_data_text(text, "test"))
        instance = {"product_id": "PRD-P", "name": "Probe", "status": "Planned", "owner_org_id": "ORG-TECH",
                    "parameters": {"slug": "probe", "product_name": "Probe", "owner_org": "ORG-TECH",
                                   "domain": "Probing", "account": "prod-probe"}}
        out = expand(instance, shape, "products", _library())
        gateway = next(t for t in out.entities["tech_services"] if t["tech_service_id"].endswith("-API-GATEWAY"))
        self.assertEqual(gateway["provider"], "Azure")

    def test_a_shape_needs_a_description(self) -> None:
        with self.assertRaises(ComposeError):
            archetype_from_parts(REPO, "x", "X", " ", VOCAB)


class TestComposeEndpoints(unittest.TestCase):
    def _server(self, root: Path):
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
        return server_module

    def test_the_options_list_what_the_composer_offers(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            opt = server.api_compose_options(None, None)
            self.assertIn("slug", [p["name"] for p in opt["vocabulary"]])
            self.assertIn("AWS", opt["providers"])
            self.assertTrue(any(m["id"] == "api-outbound" for m in opt["modules"]))
            block = next(b for b in opt["blocks"] if b["id"] == "public-web-tier")
            self.assertIn("waf", [c["id"] for c in block["components"]])
            self.assertTrue(any(s["id"] == "TS-AWS-EKS" for s in opt["shared"]))

    def test_composed_text_saves_through_the_editor_and_instantiates(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            made = server.api_archetype_compose(None, {
                "id": "probe-shape", "title": "Probe shape", "description": "A probe.",
                "parameters": VOCAB, "provider": "AWS",
                "modules": [{"module": "api-service", "with": {}}, {"module": "relational-datastore", "with": {}}],
                "blocks": [{"block": "stateless-service", "bind": {"container-platform": "TS-AWS-EKS"}},
                           {"block": "transactional-store", "bind": {"relational-db": "TS-AWS-RDS"}}],
                "patterns": [],
            })
            preview = server.api_archetype_preview(None, {"text": made["text"]})
            self.assertGreater(preview["counts"]["entities"], 3)
            saved = server.api_archetype_save(None, {"text": made["text"]})
            self.assertTrue(saved["created"])
            self.assertEqual(saved["errors"], [])
            server.api_instantiate(None, {
                "archetype": "probe-shape", "id": "PRD-PROBE",
                "values": {"name": "Probe", "status": "Planned", "owner_org_id": "ORG-PRODUCT"},
                "parameters": {"slug": "probe", "product_name": "Probe", "owner_org": "ORG-PRODUCT",
                               "domain": "Probing", "account": "prod-probe"},
            })
            model = model_module.load(root)
            self.assertIn("SYS-PROBE-API", model.entities["systems"])
            self.assertIn("SYS-PROBE-DB", model.entities["systems"])


class TestInlineComposition(unittest.TestCase):
    """A product assembled from parts with no shape: `compose:` on the
    instance is the shape of one, built as the model loads."""

    ASSEMBLED = """
product_id: PRD-ASM
name: Assembled Portal
status: Planned
owner_org_id: ORG-PRODUCT
criticality: Medium
company_domain: Probing
compose:
  provider: Azure
  modules:
    - module: api-service
      with:
        runs_on: [public-api-tier.api-gateway, stateless-service]
    - module: web-channel
    - module: relational-datastore
      with: {protocol: TDS, system_suffix: STORE}
    - module: event-publisher
parameters:
  slug: asm
  product_name: Assembled Portal
  owner_org: ORG-PRODUCT
  domain: Probing
  account: azure-probe-prod
overrides:
  SYS-ASM-API:
    service_tier: Tier 3
exclude: [TS-ASM-CACHE]
"""

    def _write(self, root: Path, text: str, name: str = "PRD-ASM") -> Path:
        path = root / "10_MODEL" / "products" / ("%s.yaml" % name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_an_assembled_product_expands_like_one_on_a_shape(self) -> None:
        with Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            self._write(root, self.ASSEMBLED)
            model = model_module.load(root)
            self.assertIn("compose:PRD-ASM", model.composed)
            self.assertNotIn("compose:PRD-ASM", model.archetypes)
            for entity_id in ("SYS-ASM-API", "SYS-ASM-WEB", "SYS-ASM-STORE", "SYS-ASM-EVENTS"):
                self.assertIn(entity_id, model.entities["systems"], entity_id)
            api = model.get("systems", "SYS-ASM-API")
            self.assertEqual(api["archetype"], "compose:PRD-ASM")
            self.assertEqual(api["archetype_instance"], "PRD-ASM")
            self.assertEqual(api["service_tier"], "Tier 3")
            self.assertEqual(api["module"], "api-service")
            self.assertEqual(api["cloud_account"], "azure-probe-prod")
            self.assertEqual(api["status"], "Planned")
            self.assertNotIn("TS-ASM-CACHE", model.entities["tech_services"])
            product = model.get("products", "PRD-ASM")
            self.assertIn("event-fanout", product["patterns"])

    def test_blocks_are_borrowed_from_the_provider_shape(self) -> None:
        with Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            self._write(root, self.ASSEMBLED)
            model = model_module.load(root)
            shape = model.composed["compose:PRD-ASM"]
            # Bound as the Azure shape binds them: to the landing zone, which
            # answers with the estate's own services.
            binds = {b["block"]: b.get("bind", {}) for b in shape.blocks}
            self.assertEqual(binds["stateless-service"]["container-platform"], "landing-zone")
            self.assertEqual(binds["transactional-store"]["relational-db"], "landing-zone")
            self.assertEqual(binds["public-api-tier"]["api-gateway"], "landing-zone")
            ran_on = {r["tech_service_id"] for r in model.relation_rows("system_uses_tech_service")
                      if r["system_id"] == "SYS-ASM-API"}
            self.assertIn("TS-AZURE-APIM", ran_on)
            # The web channel's hostname and firewall policy are the product's own.
            self.assertIn("TS-ASM-DNS", model.entities["tech_services"])
            self.assertIn("TS-ASM-WAF", model.entities["tech_services"])
            rows = {(r["system_id"], r["tech_service_id"]) for r in model.relation_rows("system_uses_tech_service")}
            self.assertIn(("SYS-ASM-WEB", "TS-AZURE-AKS"), rows)

    def test_a_part_without_what_it_requires_fails_by_file_and_name(self) -> None:
        with Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            text = self.ASSEMBLED.replace("    - module: api-service\n      with:\n        runs_on: [public-api-tier.api-gateway, stateless-service]\n", "")
            self._write(root, text)
            with self.assertRaises(model_module.ModelError) as caught:
                model_module.load(root)
            self.assertIn("PRD-ASM.yaml", str(caught.exception))
            self.assertIn("requires api-service", str(caught.exception))

    def test_a_product_cannot_be_both_on_a_shape_and_assembled(self) -> None:
        with Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            self._write(root, self.ASSEMBLED.replace("compose:\n", "archetype: azure-digital-product\ncompose:\n"))
            with self.assertRaises(model_module.ModelError) as caught:
                model_module.load(root)
            self.assertIn("not both", str(caught.exception))

    def test_compose_takes_only_what_a_shape_would(self) -> None:
        with Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            self._write(root, self.ASSEMBLED.replace("  provider: Azure\n", "  provider: Azure\n  vendor: Acme\n"))
            with self.assertRaises(model_module.ModelError) as caught:
                model_module.load(root)
            self.assertIn("does not take vendor", str(caught.exception))

    def test_the_catalog_and_adoption_know_an_assembled_product(self) -> None:
        from terrane.render_library import render_adoption, render_modules
        from terrane.validate import run as run_gates

        with Sandbox() as root:
            importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
            self._write(root, self.ASSEMBLED)
            model = model_module.load(root)
            modules = load_modules(root)
            adoption = render_adoption(modules, model.archetypes.values(), model)
            self.assertIn("## Assembled from parts", adoption)
            self.assertIn("`PRD-ASM`", adoption)
            self.assertIn("`event-publisher`", adoption)
            catalog = render_modules(modules, model.archetypes.values(), model)
            self.assertIn("Assembled Portal (assembled)", catalog)
            report = run_gates(model, [])
            # The assembled product is not a candidate for the shape it
            # happens to match: it was assembled, not hand-authored.
            self.assertFalse(any(f.code == "library.shape_candidate" and "PRD-ASM" in f.message
                                 for f in report.warnings))

    def test_the_assembled_file_text_round_trips(self) -> None:
        from terrane.compose import assembled_text

        text = assembled_text(
            "products", "PRD-ASM",
            {"name": "Assembled Portal", "status": "Planned", "owner_org_id": "ORG-PRODUCT"},
            {"provider": "Azure", "modules": [{"module": "api-service", "with": {"uses": ["TS-AZURE-KEYVAULT"]}},
                                              {"module": "web-channel", "with": {}}]},
            {"slug": "asm", "product_name": "Assembled Portal", "owner_org": "ORG-PRODUCT", "domain": "Probing",
             "account": "azure-probe-prod"},
            overrides={"SYS-ASM-API": {"service_tier": "Tier 3"}}, exclude=["TS-ASM-CACHE"],
        )
        data = parse_data_text(text, "PRD-ASM.yaml")
        self.assertEqual(data["compose"]["provider"], "Azure")
        self.assertEqual([m["module"] for m in data["compose"]["modules"]], ["api-service", "web-channel"])
        self.assertNotIn("with", data["compose"]["modules"][1])
        self.assertEqual(data["overrides"]["SYS-ASM-API"]["service_tier"], "Tier 3")
        self.assertEqual(data["exclude"], ["TS-ASM-CACHE"])
        self.assertTrue(text.startswith("# Assembled in the app"))


class TestAssembleEndpoints(unittest.TestCase):
    """The Assemble panel's three calls: the chunks, the preview, the file."""

    def _server(self, root: Path):
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
        return server_module

    BODY = {
        "id": "PRD-ASM", "values": {"name": "Assembled Portal", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
                                    "criticality": "Medium", "company_domain": "Probing"},
        "compose": {"provider": "Azure", "modules": [
            {"module": "api-service", "with": {"runs_on": ["public-api-tier.api-gateway", "stateless-service"]}},
            {"module": "web-channel"}, {"module": "relational-datastore"}, {"module": "event-publisher"}]},
        "parameters": {"slug": "asm", "product_name": "Assembled Portal", "owner_org": "ORG-PRODUCT",
                       "domain": "Probing", "account": "azure-probe-prod"},
        "overrides": {"SYS-ASM-API": {"service_tier": "Tier 3"}}, "exclude": ["TS-ASM-CACHE"],
    }

    def test_the_chunks_carry_what_a_card_shows(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            data = server.api_chunks({}, None)
            ids = {c["id"] for c in data["chunks"]}
            self.assertIn("api-service", ids)
            self.assertIn("vendor-baseline", ids)
            webhook = next(c for c in data["chunks"] if c["id"] == "webhook-inbound")
            self.assertEqual(webhook["requires"], ["vendor-tenancy"])
            names = {n["name"] for n in webhook["shape"]["nodes"]}
            self.assertIn("Product Webhook Listener", names)
            self.assertTrue(any(n["type"] == "outside" for n in webhook["shape"]["nodes"]))
            self.assertTrue(any(e["to"] for e in webhook["shape"]["edges"]))
            kit = next(c for c in data["chunks"] if c["id"] == "vendor-baseline")
            self.assertTrue(kit["kit"])
            self.assertIn("vendor-tenancy", kit["members"])
            publisher = next(c for c in data["chunks"] if c["id"] == "event-publisher")
            bus = next(p for p in publisher["parameters"] if p["name"] == "bus")
            self.assertEqual(bus["bound"]["Azure"], "TS-AZURE-SERVICEBUS")
            self.assertIn("azure-digital-product", {s["id"] for s in data["shapes"]})
            self.assertIn("Azure", data["landingZones"])
            self.assertIn("systems", data["swatches"])

    def test_a_preview_draws_the_product_and_writes_nothing(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            res = server.api_assemble_preview({}, self.BODY)
            self.assertEqual(res["conflicts"], [])
            self.assertEqual(res["counts"]["byType"]["systems"], 4)
            self.assertIsNotNone(res["graph"])
            drawn = {e["data"]["id"] for e in res["graph"]["elements"] if not e["data"].get("isGroup") and not e["data"].get("source")}
            self.assertIn("SYS-ASM-API", drawn)
            self.assertIn("TS-AZURE-AKS", drawn)
            self.assertNotIn("TS-ASM-CACHE", drawn)
            api = next(p for p in res["produced"] if p["id"] == "SYS-ASM-API")
            self.assertEqual(api["fromChunk"], "api-service")
            self.assertEqual(api["fields"]["service_tier"], "Tier 3")
            self.assertEqual(res["shapeMatch"]["id"], "azure-digital-product")
            self.assertIn("compose:", res["text"])
            self.assertFalse((root / "10_MODEL" / "products" / "PRD-ASM.yaml").exists())
            self.assertNotIn("SYS-ASM-API", model_module.load(root).entities["systems"])

    def test_a_missing_requirement_and_a_missing_answer_are_said_plainly(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            body = dict(self.BODY)
            body["compose"] = {"provider": "Azure", "modules": [{"module": "web-channel"}]}
            with self.assertRaises(server.ApiError) as caught:
                server.api_assemble_preview({}, body)
            self.assertEqual(caught.exception.status, 422)
            self.assertIn("requires api-service", caught.exception.message)
            body["compose"] = {"provider": "Azure", "modules": [
                {"module": "api-service"}, {"module": "operator-role", "with": {"system": "SYS-ASM-API"}}]}
            with self.assertRaises(server.ApiError) as missing:
                server.api_assemble_preview({}, body)
            self.assertIn("chunk needs roles", missing.exception.message)

    def test_a_clash_with_the_model_is_reported_not_written(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            server.api_assemble_create({}, self.BODY)
            again = dict(self.BODY)
            again["id"] = "PRD-ASM-TWO"
            res = server.api_assemble_preview({}, again)
            self.assertIn("SYS-ASM-API", res["conflicts"])
            self.assertIsNone(res["graph"])
            with self.assertRaises(server.ApiError) as caught:
                server.api_assemble_create({}, again)
            self.assertEqual(caught.exception.status, 409)
            self.assertFalse((root / "10_MODEL" / "products" / "PRD-ASM-TWO.yaml").exists())

    def test_create_writes_one_file_that_loads_and_validates(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            res = server.api_assemble_create({}, self.BODY)
            self.assertEqual(res["created"], "PRD-ASM")
            self.assertEqual(res["path"], "10_MODEL/products/PRD-ASM.yaml")
            self.assertIsNone(res["shape"])
            self.assertIn("SYS-ASM-API", res["generated"])
            self.assertEqual(res["errors"], [])
            model = model_module.load(root)
            self.assertEqual(model.get("systems", "SYS-ASM-API")["service_tier"], "Tier 3")
            self.assertNotIn("TS-ASM-CACHE", model.entities["tech_services"])
            text = (root / "10_MODEL" / "products" / "PRD-ASM.yaml").read_text(encoding="utf-8")
            self.assertIn("compose:", text)
            self.assertNotIn("archetype:", text)
            # The product's own architecture view draws it like any other.
            graph = server.api_graph({"view": ["product-architecture"], "p_product": ["PRD-ASM"]}, None)
            self.assertGreaterEqual(graph["counts"]["nodes"], 8)

    def test_create_can_keep_the_choice_as_a_shape(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            body = dict(self.BODY)
            body["saveShape"] = {"id": "assembled-portal", "title": "Assembled portal"}
            res = server.api_assemble_create({}, body)
            self.assertEqual(res["shape"], "assembled-portal")
            self.assertTrue((root / "20_ARCHETYPES" / "assembled-portal.yaml").exists())
            model = model_module.load(root)
            self.assertIn("assembled-portal", model.archetypes)
            product = model.get("products", "PRD-ASM")
            self.assertEqual(product["archetype"], "assembled-portal")
            self.assertEqual({}, dict(model.composed))
            text = (root / "10_MODEL" / "products" / "PRD-ASM.yaml").read_text(encoding="utf-8")
            self.assertIn("archetype: assembled-portal", text)
            self.assertNotIn("compose:", text)
            # A second product on the kept shape is a handful of answers.
            server.api_instantiate({}, {
                "archetype": "assembled-portal", "id": "PRD-ASM-NEXT",
                "values": {"name": "Next Portal", "status": "Planned", "owner_org_id": "ORG-PRODUCT"},
                "parameters": {"slug": "nxt", "product_name": "Next Portal", "owner_org": "ORG-PRODUCT",
                               "domain": "Probing", "account": "azure-probe-prod"},
            })
            self.assertIn("SYS-NXT-API", model_module.load(root).entities["systems"])

    def test_an_assembled_product_opens_back_as_it_was_written(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            server.api_assemble_create({}, self.BODY)
            res = server.api_assemble_open({"id": ["PRD-ASM"]}, None)
            self.assertEqual([m["module"] for m in res["compose"]["modules"]],
                             ["api-service", "web-channel", "relational-datastore", "event-publisher"])
            self.assertEqual(res["compose"]["modules"][0]["with"]["runs_on"],
                             ["public-api-tier.api-gateway", "stateless-service"])
            self.assertEqual(res["compose"]["provider"], "Azure")
            self.assertEqual(res["parameters"]["slug"], "asm")
            self.assertEqual(res["overrides"]["SYS-ASM-API"]["service_tier"], "Tier 3")
            self.assertEqual(res["exclude"], ["TS-ASM-CACHE"])
            self.assertEqual(res["values"]["name"], "Assembled Portal")
            self.assertNotIn("compose", res["values"])
            self.assertNotIn("product_id", res["values"])
            self.assertEqual(res["path"], "10_MODEL/products/PRD-ASM.yaml")
            self.assertIn("SYS-ASM-API", res["generated"])
            self.assertTrue(res["note"] and res["note"][0].startswith("Assembled in the app"))
            # The panel's gallery lists it, so it can be picked to open.
            listed = server.api_chunks({}, None)["assembled"]
            self.assertEqual([x["id"] for x in listed], ["PRD-ASM"])
            self.assertEqual(listed[0]["chunks"], 4)
            self.assertEqual(listed[0]["provider"], "Azure")
            # A product that is not an assembly, and one that is not there.
            plain = next(r["product_id"] for r in model_module.load(root).all_of("products")
                         if r["product_id"] != "PRD-ASM")
            with self.assertRaises(server.ApiError) as refused:
                server.api_assemble_open({"id": [plain]}, None)
            self.assertEqual(refused.exception.status, 422)
            self.assertIn("not assembled from parts", refused.exception.message)
            with self.assertRaises(server.ApiError) as missing:
                server.api_assemble_open({"id": ["PRD-NOPE"]}, None)
            self.assertEqual(missing.exception.status, 404)

    def test_a_reopened_product_is_saved_over_itself(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            server.api_assemble_create({}, self.BODY)
            path = root / "10_MODEL" / "products" / "PRD-ASM.yaml"
            path.write_text("# Why this exists, in our words.\n\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
            # Without `replace` the product clashes with itself; with it, the
            # preview judges it against the rest of the estate.
            self.assertIn("SYS-ASM-API", server.api_assemble_preview({}, self.BODY)["conflicts"])
            again = dict(self.BODY)
            again["replace"] = "PRD-ASM"
            again["overrides"] = {"SYS-ASM-API": {"service_tier": "Tier 2"}}
            again["exclude"] = []
            preview = server.api_assemble_preview({}, again)
            self.assertEqual(preview["conflicts"], [])
            self.assertTrue(preview["replacing"])
            self.assertIsNotNone(preview["graph"])
            res = server.api_assemble_create({}, again)
            self.assertTrue(res["replaced"])
            self.assertEqual(res["removed"], [])
            model = model_module.load(root)
            self.assertEqual(model.get("systems", "SYS-ASM-API")["service_tier"], "Tier 2")
            self.assertIn("TS-ASM-CACHE", model.entities["tech_services"])
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Why this exists, in our words."))
            self.assertEqual(text.count("Assembled in the app"), 1)
            self.assertEqual(len(list((root / "10_MODEL" / "products").glob("PRD-ASM*.yaml"))), 1)
            # A new slug retires what the old one made, and the reply says so.
            renamed = dict(again)
            renamed["parameters"] = dict(again["parameters"], slug="asm2")
            renamed["overrides"] = {}
            res = server.api_assemble_create({}, renamed)
            self.assertIn("SYS-ASM-API", res["removed"])
            self.assertIn("SYS-ASM2-API", res["generated"])
            self.assertNotIn("SYS-ASM-API", model_module.load(root).entities["systems"])
            # Saving over a product that is not an assembly is refused by name.
            plain = next(r["product_id"] for r in model.all_of("products")
                         if not str(r.get("archetype") or "").startswith("compose:"))
            other = dict(self.BODY)
            other["id"] = plain
            other["replace"] = plain
            with self.assertRaises(server.ApiError) as refused:
                server.api_assemble_create({}, other)
            self.assertIn("not assembled from parts", refused.exception.message)

    def test_open_then_save_changes_nothing(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            server.api_assemble_create({}, self.BODY)
            path = root / "10_MODEL" / "products" / "PRD-ASM.yaml"
            before = path.read_text(encoding="utf-8")
            opened = server.api_assemble_open({"id": ["PRD-ASM"]}, None)
            body = {"id": opened["id"], "values": opened["values"], "compose": opened["compose"],
                    "parameters": opened["parameters"], "overrides": opened["overrides"],
                    "exclude": opened["exclude"], "extra": opened["extra"], "replace": opened["id"]}
            res = server.api_assemble_create({}, body)
            self.assertTrue(res["replaced"])
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    SHAPED = {
        "archetype": "azure-digital-product", "id": "PRD-SHAPED",
        "values": {"name": "Shaped Portal", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
                   "criticality": "Medium", "company_domain": "Probing"},
        "parameters": {"slug": "shp", "product_name": "Shaped Portal", "owner_org": "ORG-PRODUCT",
                       "domain": "Probing", "account": "azure-probe-prod"},
    }

    def test_a_product_on_a_shape_opens_and_saves_in_the_shape_s_terms(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            server.api_instantiate({}, self.SHAPED)
            opened = server.api_assemble_open({"id": ["PRD-SHAPED"]}, None)
            self.assertEqual(opened["archetype"], "azure-digital-product")
            self.assertEqual(opened["shape"]["id"], "azure-digital-product")
            self.assertIn("api-service", [m["module"] for m in opened["shape"]["modules"]])
            self.assertEqual(opened["without"], [])
            self.assertEqual(opened["modules"], [])
            self.assertEqual(opened["parameters"]["slug"], "shp")
            self.assertEqual(opened["compose"], {})
            listed = {x["id"]: x for x in server.api_chunks({}, None)["assembled"]}
            self.assertEqual(listed["PRD-SHAPED"]["shape"], "azure-digital-product")
            # A part the shape marks optional, which nothing kept requires.
            chunks = {c["id"]: c for c in server.api_chunks({}, None)["chunks"]}
            aliases = [m["module"] for m in opened["shape"]["modules"]]
            droppable = [a for a in aliases if chunks.get(a, {}).get("optional")
                         and not any(a in chunks.get(o, {}).get("requires", []) for o in aliases if o != a)]
            dropped = droppable[0] if droppable else None
            body = {"id": "PRD-SHAPED", "values": opened["values"], "archetype": "azure-digital-product",
                    "parameters": opened["parameters"], "choose": opened["choose"],
                    "without": [dropped] if dropped else [], "modules": opened["modules"],
                    "overrides": {"SYS-SHP-API": {"service_tier": "Tier 2"}}, "exclude": [], "replace": "PRD-SHAPED"}
            preview = server.api_assemble_preview({}, body)
            self.assertEqual(preview["conflicts"], [])
            self.assertEqual(preview["archetype"], "azure-digital-product")
            self.assertIsNone(preview["shapeMatch"])
            self.assertIsNotNone(preview["graph"])
            self.assertIn("archetype: azure-digital-product", preview["text"])
            self.assertNotIn("compose:", preview["text"])
            # A remark a person wrote beside the data, before the save.
            product_file = root / "10_MODEL" / "products" / "PRD-SHAPED.yaml"
            annotated = product_file.read_text(encoding="utf-8").replace(
                "parameters:\n", "# The answers, as the product team gave them.\nparameters:\n", 1)
            self.assertIn("# The answers, as the product team gave them.", annotated)
            product_file.write_text(annotated, encoding="utf-8")
            res = server.api_assemble_create({}, body)
            self.assertTrue(res["replaced"])
            text = product_file.read_text(encoding="utf-8")
            # The note the New form wrote above the data survives the save,
            # and so does the remark written beside it.
            self.assertTrue(text.startswith("# Created in the app from archetype azure-digital-product."))
            self.assertIn("# The answers, as the product team gave them.\nparameters:\n", text)
            self.assertIn("archetype: azure-digital-product", text)
            self.assertNotIn("compose:", text)
            model = model_module.load(root)
            self.assertEqual(model.get("systems", "SYS-SHP-API")["service_tier"], "Tier 2")
            again = server.api_assemble_open({"id": ["PRD-SHAPED"]}, None)
            self.assertEqual(again["overrides"], {"SYS-SHP-API": {"service_tier": "Tier 2"}})
            self.assertEqual(again["without"], [dropped] if dropped else [])
            if dropped:
                self.assertIn("without:", text)
                self.assertGreater(len(res["removed"]), 0)
            # A product on a shape has no second shape to keep.
            with self.assertRaises(server.ApiError) as refused:
                server.api_assemble_create({}, dict(body, saveShape={"id": "second", "title": "Second"}))
            self.assertEqual(refused.exception.status, 422)

    def test_a_kit_s_member_can_be_done_without_and_the_tenancy_cannot(self) -> None:
        """The panel shows a kit's members as rows; unticking one writes the
        member's alias under `without`, and the engine drops it. The vendor
        tenancy is not optional, so dropping it is refused by name."""
        with Sandbox() as root:
            server = self._server(root)
            res = server.api_instantiate({}, {
                "archetype": "vendor-saas-service", "id": "PRD-KITTEST",
                "values": {"name": "Kit Probe", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
                           "criticality": "Medium", "company_domain": "Probing"},
                "parameters": {"slug": "kt", "product_name": "Kit Probe", "vendor": "Probe Ltd", "owner_org": "ORG-PRODUCT",
                               "domain": "Probing", "upstream_system": "SYS-CORE-LEDGER", "account": "azure-probe-prod"},
            })
            self.assertEqual(res["errors"], [])
            uses = {(str(r["system_id"]), str(r["tech_service_id"]))
                    for r in model_module.load(root).relation_rows("system_uses_tech_service")}
            self.assertIn(("SYS-KT-GATEWAY", "TS-AZURE-KEYVAULT"), uses, "the kit's vault member is in by default")
            opened = server.api_assemble_open({"id": ["PRD-KITTEST"]}, None)
            body = {"id": "PRD-KITTEST", "values": opened["values"], "archetype": "vendor-saas-service",
                    "parameters": opened["parameters"], "choose": opened["choose"], "modules": opened["modules"],
                    "without": ["secrets-management"], "overrides": {}, "exclude": [], "replace": "PRD-KITTEST"}
            saved = server.api_assemble_create({}, body)
            self.assertTrue(saved["replaced"])
            text = (root / "10_MODEL" / "products" / "PRD-KITTEST.yaml").read_text(encoding="utf-8")
            self.assertIn("without: [secrets-management]", text)
            uses = {(str(r["system_id"]), str(r["tech_service_id"]))
                    for r in model_module.load(root).relation_rows("system_uses_tech_service")}
            self.assertNotIn(("SYS-KT-GATEWAY", "TS-AZURE-KEYVAULT"), uses)
            self.assertIn(("SYS-KT-GATEWAY", "TS-AZURE-APIM"), uses, "the rest of the kit stays")
            self.assertEqual(server.api_assemble_open({"id": ["PRD-KITTEST"]}, None)["without"], ["secrets-management"])
            with self.assertRaises(server.ApiError) as refused:
                server.api_assemble_preview({}, dict(body, without=["vendor-tenancy"]))
            self.assertIn("vendor-tenancy", str(refused.exception))

    def test_a_product_on_a_shape_can_be_detached_into_its_own_compose_block(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            server.api_instantiate({}, self.SHAPED)
            opened = server.api_assemble_open({"id": ["PRD-SHAPED"]}, None)
            shape = opened["shape"]
            # What the panel sends when told to let go of the shape: the
            # parts with what the shape bound, and its blocks and patterns.
            body = {"id": "PRD-SHAPED", "values": opened["values"], "parameters": opened["parameters"],
                    "compose": {"provider": shape["provider"], "modules": shape["modules"],
                                "blocks": shape["blocks"], "bind": shape["bind"], "patterns": shape["patterns"]},
                    "overrides": {}, "exclude": [], "replace": "PRD-SHAPED"}
            before = sorted(server.api_assemble_open({"id": ["PRD-SHAPED"]}, None)["generated"])
            res = server.api_assemble_create({}, body)
            self.assertTrue(res["replaced"])
            self.assertEqual(res["removed"], [])
            self.assertEqual(sorted(res["generated"]), before)
            text = (root / "10_MODEL" / "products" / "PRD-SHAPED.yaml").read_text(encoding="utf-8")
            self.assertIn("compose:", text)
            self.assertNotIn("archetype:", text)
            detached = server.api_assemble_open({"id": ["PRD-SHAPED"]}, None)
            self.assertEqual(detached["archetype"], "")
            self.assertEqual([m["module"] for m in detached["compose"]["modules"]],
                             [m["module"] for m in shape["modules"]])


class TestKeptComments(unittest.TestCase):
    """The panel's save keeps what a person wrote beside the data: an
    unchanged key keeps its lines, a changed one keeps the remark above
    it, and mappings merge key by key however deep."""

    OLD = (
        "# A product someone annotated.\n"
        "#\n"
        "# Second paragraph of the note.\n"
        "\n"
        "product_id: PRD-P\n"
        "name: Probe\n"
        "status: Active  # live since March\n"
        "\n"
        "archetype: azure-digital-product\n"
        "parameters:\n"
        "  slug: probe\n"
        "  # the shape's default region is the right one\n"
        "  product_name: Probe\n"
        "\n"
        "# What the shape gets wrong about a live product.\n"
        "overrides:\n"
        "  # Not in the authorization path.\n"
        "  SYS-PROBE-API:\n"
        "    service_tier: Tier 3\n"
        "  # The datastore keeps its old name.\n"
        "  SYS-PROBE-STORE:\n"
        "    name: Probe Datastore\n"
        "\n"
        "# Dropped last year.\n"
        "exclude: [TS-PROBE-WAF]\n"
    )

    def test_an_unchanged_file_comes_back_as_it_was(self) -> None:
        bare = (
            "# A product someone annotated.\n#\n# Second paragraph of the note.\n\n"
            "product_id: PRD-P\nname: Probe\nstatus: Active\narchetype: azure-digital-product\n"
            "parameters:\n  slug: probe\n  product_name: Probe\n"
            "overrides:\n  SYS-PROBE-API:\n    service_tier: Tier 3\n  SYS-PROBE-STORE:\n    name: Probe Datastore\n"
            "exclude: [TS-PROBE-WAF]\n"
        )
        self.assertEqual(keep_comments(bare, self.OLD), self.OLD)

    def test_a_changed_override_keeps_every_other_remark(self) -> None:
        bare = (
            "# A product someone annotated.\n#\n# Second paragraph of the note.\n\n"
            "product_id: PRD-P\nname: Probe\nstatus: Active\narchetype: azure-digital-product\n"
            "parameters:\n  slug: probe\n  product_name: Probe\n"
            "overrides:\n  SYS-PROBE-API:\n    service_tier: Tier 2\n  SYS-PROBE-STORE:\n    name: Probe Datastore\n"
            "exclude: [TS-PROBE-WAF]\n"
        )
        out = keep_comments(bare, self.OLD)
        self.assertIn("status: Active  # live since March\n", out)
        self.assertIn("  # the shape's default region is the right one\n  product_name: Probe\n", out)
        self.assertIn("# What the shape gets wrong about a live product.\noverrides:\n", out)
        self.assertIn("  # Not in the authorization path.\n  SYS-PROBE-API:\n    service_tier: Tier 2\n", out)
        self.assertIn("  # The datastore keeps its old name.\n  SYS-PROBE-STORE:\n    name: Probe Datastore\n", out)
        self.assertIn("\n# Dropped last year.\nexclude: [TS-PROBE-WAF]\n", out)
        self.assertNotIn("Tier 3", out)

    def test_a_removed_key_goes_with_its_remark_and_a_new_one_comes_as_written(self) -> None:
        bare = (
            "# A product someone annotated.\n\n"
            "product_id: PRD-P\nname: Probe\nstatus: Active\narchetype: azure-digital-product\n"
            "parameters:\n  slug: probe\n  product_name: Probe\n"
            "without: [event-publisher]\n"
            "overrides:\n  SYS-PROBE-API:\n    service_tier: Tier 3\n  SYS-PROBE-STORE:\n    name: Probe Datastore\n"
        )
        out = keep_comments(bare, self.OLD)
        self.assertNotIn("exclude", out)
        self.assertNotIn("Dropped last year", out)
        self.assertIn("without: [event-publisher]\n", out)
        self.assertIn("  # Not in the authorization path.\n", out)
        # The header is the new text's: the caller carries the old one over.
        self.assertTrue(out.startswith("# A product someone annotated.\n\nproduct_id: PRD-P\n"))


if __name__ == "__main__":
    unittest.main()
