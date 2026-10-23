"""Tests for sketches: a diagram built by hand, written back as a query.

The claim is that an architect can grow a picture from the map and keep it
in the only forms the repository has: a view whose scope is the list of
things chosen, or a module whose templates are those things rewritten in
the vocabulary of the shape that made them. What is checked here is the
writing back: the view resolves to exactly what was chosen, the YAML the
engine writes is YAML the engine reads, the module tokenizes ids and drops
what the shape's defaults already say, and a module written from one
product expands into another.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import blocks, importer, model as model_module  # noqa: E402
from terrane.archetype import expand, parse_archetype  # noqa: E402
from terrane.loader import parse_data_text  # noqa: E402
from terrane.modules import load_modules, parse_module  # noqa: E402
from terrane.query import parse_view, resolve  # noqa: E402
from terrane.sketch import (  # noqa: E402
    SketchError, dump_yaml, guess_slug, module_from_sketch, module_text_from_sketch,
    view_from_sketch, view_text_from_sketch, yaml_text,
)

from _fixture import (  # noqa: E402
    EXAMPLE_CSV, REPO, Sandbox, seeded_model, setup_shared, teardown_shared,
)


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


SCREENING = [
    "SYS-SCREENING-GATEWAY", "SYS-SCREENING-EGRESS", "SYS-SCREENING-VENDOR",
    "INT-SCREENING-GATEWAY-EGRESS", "INT-SCREENING-EGRESS-VENDOR",
]


class TestYamlOut(unittest.TestCase):
    def test_what_is_written_is_what_is_read(self) -> None:
        data = {
            "view_id": "probe", "title": "A title: with punctuation", "count": 3, "flag": True,
            "empty": [], "tags": ["a", "b c"], "nested": {"x": {"y": "z"}},
            "rows": [{"k": "v", "n": ["p", "q"]}, {"k": "w"}],
            "prose": "Two lines\nof text",
            "id": "SYS-{slug|upper}-API",
            "quoted": "yes",
        }
        text = yaml_text(data, ("a header", "", "second"))
        back = parse_data_text(text, "test")
        self.assertEqual(back["view_id"], "probe")
        self.assertEqual(back["title"], data["title"])
        self.assertEqual(back["count"], 3)
        self.assertIs(back["flag"], True)
        self.assertEqual(back["empty"], [])
        self.assertEqual(back["tags"], ["a", "b c"])
        self.assertEqual(back["nested"], {"x": {"y": "z"}})
        self.assertEqual(back["rows"], data["rows"])
        self.assertEqual(back["id"], "SYS-{slug|upper}-API")
        self.assertEqual(back["quoted"], "yes")
        self.assertTrue(text.startswith("# a header\n#\n# second\n\n"))

    def test_a_list_of_mappings_writes_the_dash_form(self) -> None:
        lines = dump_yaml([{"a": 1, "b": [1, 2]}, {"a": 2}])
        self.assertEqual(lines, ["- a: 1", "  b: [1, 2]", "- a: 2"])


class TestSketchAsView(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def test_the_view_draws_exactly_what_was_chosen(self) -> None:
        data = view_from_sketch(self.model, SCREENING, "probe", "Probe")
        graph = resolve(self.model, parse_view(data))
        self.assertEqual(sorted(n.key for n in graph.nodes), sorted(SCREENING))
        self.assertTrue(graph.edges, "the interfaces between the chosen systems are edges")

    def test_the_scope_is_an_explicit_list_per_type(self) -> None:
        data = view_from_sketch(self.model, SCREENING, "probe", "Probe", group_by=["network_zone"],
                                color_by="criticality", layout="TB")
        include = {c["type"]: c["where"]["id_in"] for c in data["scope"]["include"]}
        self.assertEqual(sorted(include), ["interfaces", "systems"])
        self.assertEqual(include["systems"], sorted(s for s in SCREENING if s.startswith("SYS")))
        self.assertEqual(data["group_by"], ["network_zone"])
        self.assertEqual(data["style"], {"color_by": "criticality"})
        self.assertEqual(data["layout"], "TB")
        self.assertEqual(data["kind"], "diagram")

    def test_the_text_is_a_view_the_engine_reads(self) -> None:
        text = view_text_from_sketch(self.model, ids=SCREENING, view_id="probe", title="Probe")
        view = parse_view(parse_data_text(text, "test"))
        self.assertEqual(view.view_id, "probe")
        graph = resolve(self.model, view)
        self.assertEqual(len(graph.nodes), len(SCREENING))

    def test_an_unknown_id_is_refused(self) -> None:
        with self.assertRaises(SketchError):
            view_from_sketch(self.model, ["SYS-NOPE"], "probe", "Probe")

    def test_an_empty_sketch_is_refused(self) -> None:
        with self.assertRaises(SketchError):
            view_from_sketch(self.model, [], "probe", "Probe")


class TestSketchAsModule(unittest.TestCase):
    """Against the repository's own model, where the screening product is a
    real instance with parameters: that is what tokenizing needs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = model_module.load(REPO)
        cls.data, cls.report = module_from_sketch(
            cls.model, SCREENING, "private-vendor-path", "Private vendor path",
            "The gateway, the private path, and the vendor.", category="Network",
        )

    def test_ids_and_names_are_written_as_tokens(self) -> None:
        systems = {s["system_id"]: s for s in self.data["provides"]["systems"]}
        self.assertIn("SYS-{slug|upper}-GATEWAY", systems)
        self.assertIn("SYS-{slug|upper}-VENDOR", systems)
        self.assertIn("{product_name}", systems["SYS-{slug|upper}-GATEWAY"]["name"])
        self.assertEqual(systems["SYS-{slug|upper}-VENDOR"]["provider"], "{vendor}")
        interfaces = {i["interface_id"]: i for i in self.data["provides"]["interfaces"]}
        self.assertEqual(
            interfaces["INT-{slug|upper}-EGRESS-VENDOR"]["target_system_id"], "SYS-{slug|upper}-VENDOR"
        )
        self.assertEqual(self.report["slug"], "screening")
        self.assertEqual(self.report["generatedFrom"], "PRD-SCREENING")

    def test_what_the_shape_defaults_say_is_dropped(self) -> None:
        """`owner_org_id`, `hosting`, `status` and the rest come from the
        shape's entity_defaults, so the part does not repeat them."""
        gateway = next(s for s in self.data["provides"]["systems"]
                       if s["system_id"] == "SYS-{slug|upper}-GATEWAY")
        for field in ("owner_org_id", "hosting", "status", "company_domain", "cloud_account"):
            self.assertNotIn(field, gateway, field)
        # What the part itself overrides on the shape stays: the gateway is
        # deployed with helm where the shape says terraform.
        self.assertEqual(gateway.get("deployment_unit"), "helm")
        self.assertIn("owner_org_id", self.report["dropped"])

    def test_platform_use_and_governance_come_back_as_shorthands(self) -> None:
        systems = {s["system_id"]: s for s in self.data["provides"]["systems"]}
        self.assertIn("TS-AWS-PRIVATELINK", systems["SYS-{slug|upper}-EGRESS"]["uses"])
        self.assertIn("CTL-TPRM-DD", systems["SYS-{slug|upper}-VENDOR"]["controls"])
        self.assertIn("POL-TPRM", systems["SYS-{slug|upper}-VENDOR"]["policies"])
        self.assertGreater(self.report["recovered"], 3)

    def test_the_part_declares_what_it_reads_from_the_shape(self) -> None:
        """The tokenizer wrote `{slug}` and `{product_name}` into the ids,
        so the part reads them from whichever shape composes it; a part
        that did not say so would not load."""
        self.assertIn("slug", self.data.get("needs", []))
        self.assertIn("product_name", self.data.get("needs", []))
        self.assertNotIn("slug", [p["name"] for p in self.data.get("parameters", [])])

    def test_the_part_composes_into_another_product(self) -> None:
        """The whole point: a part drawn from one product becomes the next
        product's part from the library."""
        text, _report = module_text_from_sketch(
            self.model, ids=SCREENING, module_id="private-vendor-path", name="Private vendor path",
            description="The gateway, the private path, and the vendor.",
        )
        listed = parse_data_text(text, "test")
        module = parse_module(listed[0])
        components = blocks.load_components(REPO)
        library = (components, blocks.load_blocks(REPO, components), {module.module_id: module})
        shape = parse_archetype({
            "archetype_id": "probe", "applies_to": "products", "provider": "AWS",
            "parameters": [
                {"name": "slug", "required": True}, {"name": "product_name", "required": True},
                {"name": "vendor", "required": True}, {"name": "owner_org", "default": "ORG-TECH"},
                {"name": "domain", "default": "Probing"}, {"name": "account", "default": "prod-acme"},
                {"name": "region", "default": "eu-west-2"}, {"name": "vendor_region", "default": "eu-west-1"},
                {"name": "classification", "default": "Restricted"}, {"name": "criticality", "default": "High"},
            ],
            "entity_defaults": {
                "all": {"status": "Planned", "company_domain": "{domain}"},
                "systems": {"owner_org_id": "{owner_org}", "hosting": "AWS", "cloud_provider": "AWS",
                            "environment": "Production", "cloud_account": "{account}"},
                "interfaces": {"owner_org_id": "{owner_org}", "protocol": "HTTPS", "direction": "Outbound",
                               "frequency": "Realtime", "integration_style": "Request-response"},
            },
            "modules": ["private-vendor-path"],
        })
        instance = {"product_id": "PRD-ACME", "name": "Acme", "status": "Planned", "owner_org_id": "ORG-TECH",
                    "parameters": {"slug": "acme", "product_name": "Acme Screening", "vendor": "Acme"}}
        out = expand(instance, shape, "products", library)
        systems = {s["system_id"]: s for s in out.entities["systems"]}
        self.assertEqual(sorted(systems), ["SYS-ACME-EGRESS", "SYS-ACME-GATEWAY", "SYS-ACME-VENDOR"])
        self.assertEqual(systems["SYS-ACME-VENDOR"]["provider"], "Acme")
        self.assertIn("Acme Screening", systems["SYS-ACME-GATEWAY"]["name"])
        governed = {(r["system_id"], r["control_id"]) for r in out.relations["system_governed_by_control"]}
        self.assertIn(("SYS-ACME-VENDOR", "CTL-TPRM-DD"), governed)

    def test_a_hand_authored_entity_keeps_its_fields(self) -> None:
        data, report = module_from_sketch(
            self.model, ["SYS-CORE-LEDGER"], "ledger", "Ledger", "The ledger.", slug="core",
        )
        ledger = data["provides"]["systems"][0]
        self.assertEqual(ledger["system_id"], "SYS-{slug|upper}-LEDGER")
        self.assertIn("owner_org_id", ledger)
        self.assertIsNone(report["generatedFrom"])

    def test_a_module_needs_a_description(self) -> None:
        with self.assertRaises(SketchError):
            module_from_sketch(self.model, SCREENING, "x", "X", "   ")

    def test_guessing_the_slug(self) -> None:
        self.assertEqual(guess_slug(SCREENING), "screening")
        self.assertEqual(guess_slug(["SYS-CRM"]), None)
        self.assertEqual(guess_slug(["SYS-LENDING-API", "SYS-CARDSVC-API"]), None)


class TestSketchEndpoints(unittest.TestCase):
    def _server(self, root: Path):
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
        return server_module

    def test_the_view_endpoint_draws_and_writes_nothing(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            before = sorted(p.name for p in (root / "30_VIEWS").iterdir())
            payload = server.api_sketch_view(None, {"ids": SCREENING, "title": "Probe", "id": "probe"})
            self.assertTrue(payload["sketch"])
            self.assertIn("view_id: probe", payload["text"])
            drawn = [e["data"]["id"] for e in payload["elements"] if not e["data"].get("isGroup")
                     and "source" not in e["data"]]
            self.assertEqual(sorted(drawn), sorted(SCREENING))
            self.assertEqual(sorted(p.name for p in (root / "30_VIEWS").iterdir()), before)

    def test_the_view_text_saves_like_any_view(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            payload = server.api_sketch_view(None, {"ids": SCREENING, "title": "Probe", "id": "probe-sketch"})
            saved = server.api_view_save(None, {"text": payload["text"]})
            self.assertTrue(saved["created"])
            self.assertEqual(saved["counts"]["nodes"], len(SCREENING))
            self.assertTrue((root / "30_VIEWS" / "probe-sketch.view.yaml").exists())

    def test_a_module_is_saved_into_the_library_and_loads(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            made = server.api_sketch_module(None, {
                "ids": SCREENING, "module_id": "private-vendor-path", "name": "Private vendor path",
                "description": "The gateway, the private path, and the vendor.", "slug": "screening",
            })
            self.assertEqual(made["report"]["guessedSlug"], "screening")
            self.assertFalse(made["report"]["exists"])
            saved = server.api_module_save(None, {"text": made["text"]})
            self.assertTrue(saved["created"])
            self.assertEqual(saved["errors"], [])
            self.assertIn("private-vendor-path", load_modules(root))
            self.assertIn("private-vendor-path", {m["id"] for m in server.api_library(None, None)["modules"]})

    def test_a_module_that_clashes_with_the_library_is_refused(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            made = server.api_sketch_module(None, {
                "ids": SCREENING, "module_id": "api-outbound", "name": "Clash", "description": "Clash.",
            })
            self.assertTrue(made["report"]["exists"])
            with self.assertRaises(server.ApiError) as caught:
                server.api_module_save(None, {"text": made["text"]})
            self.assertEqual(caught.exception.status, 409)
            self.assertFalse((root / "28_MODULES" / "api-outbound.yaml").exists())

    def test_a_broken_module_leaves_no_file(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            with self.assertRaises(server.ApiError):
                server.api_module_save(None, {"text": "- module_id: broken\n  name: Broken\n"})
            self.assertFalse((root / "28_MODULES" / "broken.yaml").exists())


class TestCreatingIntoAProduct(unittest.TestCase):
    """A new thing made beside generated things belongs to their product: it
    goes under the instance's `extra`, is included in the product, and
    survives a re-expansion because it is in the file that is re-expanded."""

    PARAMS = {"slug": "probe", "product_name": "Probe", "vendor": "Acme", "owner_org": "ORG-PRODUCT",
              "domain": "Probing", "account": "prod-probe", "caller_system": "SYS-AUTH-SWITCH"}

    def _server(self, root: Path):
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
        server_module.api_instantiate(None, {
            "archetype": "saas-onboarding", "id": "PRD-PROBE",
            "values": {"name": "Probe", "status": "Planned", "owner_org_id": "ORG-PRODUCT"},
            "parameters": dict(self.PARAMS),
        })
        return server_module

    def test_a_system_added_to_an_instance_is_part_of_the_product(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            res = server.api_save(None, {
                "type": "systems", "id": "SYS-PROBE-RECON", "instance": "PRD-PROBE",
                "values": {"name": "Probe Reconciliation", "status": "Planned",
                           "owner_org_id": "ORG-PRODUCT", "criticality": "Medium", "tags": ["probe"]},
            })
            self.assertEqual(res["instance"], "PRD-PROBE")
            self.assertTrue(res["path"].endswith("PRD-PROBE.yaml"))
            model = model_module.load(root)
            record = model.entities["systems"]["SYS-PROBE-RECON"]
            self.assertEqual(record["archetype_instance"], "PRD-PROBE")
            included = {(r["product_id"], r["system_id"]) for r in model.relations["product_includes_system"]}
            self.assertIn(("PRD-PROBE", "SYS-PROBE-RECON"), included)
            self.assertFalse((root / "10_MODEL" / "systems" / "SYS-PROBE-RECON.yaml").exists())

    def test_a_second_thing_joins_the_same_block(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            server.api_save(None, {"type": "systems", "id": "SYS-PROBE-ONE", "instance": "PRD-PROBE",
                                   "values": {"name": "One", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
                                              "criticality": "Low"}})
            server.api_save(None, {"type": "systems", "id": "SYS-PROBE-TWO", "instance": "PRD-PROBE",
                                   "values": {"name": "Two", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
                                              "criticality": "Low"}})
            server.api_save(None, {"type": "interfaces", "id": "INT-PROBE-ONE-TWO", "instance": "PRD-PROBE",
                                   "values": {"name": "One to Two", "status": "Planned",
                                              "source_system_id": "SYS-PROBE-ONE",
                                              "target_system_id": "SYS-PROBE-TWO", "protocol": "HTTPS"}})
            text = (root / "10_MODEL" / "products" / "PRD-PROBE.yaml").read_text(encoding="utf-8-sig")
            self.assertEqual(text.count("\nextra:"), 1)
            self.assertEqual(text.count("\n  systems:"), 1)
            self.assertEqual(text.count("\n  interfaces:"), 1)
            model = model_module.load(root)
            self.assertIn("SYS-PROBE-ONE", model.entities["systems"])
            self.assertIn("SYS-PROBE-TWO", model.entities["systems"])
            self.assertEqual(model.entities["interfaces"]["INT-PROBE-ONE-TWO"]["archetype_instance"], "PRD-PROBE")

    def test_only_an_instance_can_be_added_to(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_save(None, {"type": "systems", "id": "SYS-PROBE-X", "instance": "SYS-CORE-LEDGER",
                                       "values": {"name": "X", "status": "Planned", "owner_org_id": "ORG-PRODUCT",
                                                  "criticality": "Low"}})
            self.assertEqual(caught.exception.status, 404)


if __name__ == "__main__":
    unittest.main()
