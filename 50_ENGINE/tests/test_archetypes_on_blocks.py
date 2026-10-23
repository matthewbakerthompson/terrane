"""Tests for archetypes built on building blocks.

The claim is that an archetype can say *what the landing zone provides* and
*what the product gets of its own* by naming blocks, and that a change to a
block then reaches every shape at once. Most of what is checked here is the
resolution: a bound component creates nothing and is what the systems run on,
an unbound one is created per product and resolved to the provider's product,
and the shorthands on a system produce exactly the relations they imply.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import blocks, model as model_module  # noqa: E402
from terrane.archetype import (  # noqa: E402
    LANDING_ZONE_TAG,
    ArchetypeError,
    expand,
    landing_zone_index,
    load_archetypes,
    parse_archetype,
    resolve_kind,
)
from terrane.loader import load_folder, read_data_file  # noqa: E402
from terrane.answers import estate_answers  # noqa: E402
from terrane.modules import load_modules  # noqa: E402

from _fixture import REPO, seeded_model, setup_shared, teardown_shared  # noqa: E402


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


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


SHAPE = {
    "archetype_id": "probe",
    "applies_to": "products",
    "provider": "AWS",
    "parameters": [{"name": "slug", "required": True}, {"name": "account", "default": "prod-x"}],
    "entity_defaults": {
        "all": {"status": "Planned", "company_domain": "Probing"},
        "systems": {"owner_org_id": "ORG-TECH", "criticality": "High",
                    "cloud_account": "{account}", "tags": ["probe"]},
        "tech_services": {"cloud_account": "{account}", "owner_org_id": "ORG-TECH"},
    },
    "blocks": [
        {"block": "public-web-tier", "bind": {"cdn": "TS-AWS-CLOUDFRONT", "load-balancer": "TS-AWS-ALB"}},
        {"block": "stateless-service", "bind": {"container-platform": "TS-AWS-EKS"}},
    ],
    "provides": {"systems": [
        {"system_id": "SYS-{slug|upper}-EDGE", "name": "{name} Edge", "criticality": "Medium",
         "runs_on": ["public-web-tier.cdn", "public-web-tier.waf", "public-web-tier.dns"]},
        {"system_id": "SYS-{slug|upper}-API", "name": "{name} API",
         "runs_on": ["stateless-service"], "uses": ["TS-AWS-SECRETS"]},
    ]},
}


def _instance(**extra) -> dict:
    base = {"product_id": "PRD-P", "name": "Probe", "status": "Planned",
            "owner_org_id": "ORG-TECH", "parameters": {"slug": "probe"}}
    base.update(extra)
    return base


class TestBlockResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()
        cls.shape = parse_archetype(dict(SHAPE))
        cls.out = expand(_instance(), cls.shape, "products", cls.library)

    def _services(self):
        return {r["tech_service_id"]: r for r in self.out.entities["tech_services"]}

    def test_a_bound_component_creates_nothing(self) -> None:
        created = self._services()
        for bound in ("TS-AWS-CLOUDFRONT", "TS-AWS-ALB", "TS-AWS-EKS"):
            self.assertNotIn(bound, created)
        self.assertNotIn("TS-PROBE-CDN", created)

    def test_an_unbound_component_is_created_per_product_and_resolved(self) -> None:
        """The whole claim: the block says a WAF, the provider says what a WAF
        is here, and the product gets one of its own."""
        created = self._services()
        self.assertEqual(
            sorted(created), ["TS-PROBE-CACHE", "TS-PROBE-DNS", "TS-PROBE-OBSERVABILITY", "TS-PROBE-WAF"]
        )
        waf = created["TS-PROBE-WAF"]
        self.assertEqual(waf["component_type"], "waf")
        self.assertEqual(waf["provider"], "AWS")
        self.assertTrue(waf.get("product"))
        self.assertEqual(waf["archetype_instance"], "PRD-P")
        self.assertEqual(waf["name"], "Probe Web application firewall")

    def test_defaults_layer_in_the_stated_order(self) -> None:
        """The component knows what it is, the shape knows where it is, the
        block knows what zone it sits in."""
        created = self._services()
        self.assertEqual(created["TS-PROBE-WAF"]["cloud_account"], "prod-x")
        self.assertEqual(created["TS-PROBE-WAF"]["network_zone"], "Edge")
        self.assertEqual(created["TS-PROBE-CACHE"]["network_zone"], "Private-App")
        self.assertEqual(created["TS-PROBE-WAF"]["service_category"], "Security")

    def test_runs_on_names_a_component_or_a_whole_block(self) -> None:
        rows = {
            (r["system_id"], r["tech_service_id"])
            for r in self.out.relations["system_uses_tech_service"]
        }
        self.assertIn(("SYS-PROBE-EDGE", "TS-AWS-CLOUDFRONT"), rows)
        self.assertIn(("SYS-PROBE-EDGE", "TS-PROBE-WAF"), rows)
        self.assertNotIn(("SYS-PROBE-EDGE", "TS-AWS-ALB"), rows)
        # The whole block, bound and created alike, plus `uses`.
        for service in ("TS-AWS-EKS", "TS-PROBE-CACHE", "TS-PROBE-OBSERVABILITY", "TS-AWS-SECRETS"):
            self.assertIn(("SYS-PROBE-API", service), rows)

    def test_shared_to_shared_connections_are_not_this_products_fact(self) -> None:
        pairs = {
            (r["from_tech_service_id"], r["to_tech_service_id"])
            for r in self.out.relations["tech_service_connects_to"]
        }
        self.assertIn(("TS-PROBE-WAF", "TS-AWS-ALB"), pairs)
        self.assertIn(("TS-AWS-CLOUDFRONT", "TS-PROBE-WAF"), pairs)
        for source, target in pairs:
            self.assertTrue(source.startswith("TS-PROBE") or target.startswith("TS-PROBE"))

    def test_every_provided_system_is_included_in_the_product(self) -> None:
        rows = {r["system_id"] for r in self.out.relations["product_includes_system"]}
        self.assertEqual(rows, {"SYS-PROBE-EDGE", "SYS-PROBE-API"})

    def test_entity_defaults_apply_and_the_template_wins(self) -> None:
        systems = {r["system_id"]: r for r in self.out.entities["systems"]}
        self.assertEqual(systems["SYS-PROBE-API"]["criticality"], "High")
        self.assertEqual(systems["SYS-PROBE-EDGE"]["criticality"], "Medium")
        self.assertEqual(systems["SYS-PROBE-API"]["company_domain"], "Probing")
        self.assertEqual(systems["SYS-PROBE-API"]["cloud_account"], "prod-x")
        self.assertNotIn("runs_on", systems["SYS-PROBE-API"])
        self.assertNotIn("uses", systems["SYS-PROBE-API"])

    def test_a_template_can_take_a_default_away_with_null(self) -> None:
        """A vendor tenancy has no deployment unit of ours, whatever the
        shape's other systems have in common."""
        shape = parse_archetype(dict(SHAPE, provides={"systems": [
            {"system_id": "SYS-{slug|upper}-V", "name": "v", "cloud_account": None},
        ]}))
        out = expand(_instance(), shape, "products", self.library)
        record = out.entities["systems"][0]
        self.assertNotIn("cloud_account", record)
        self.assertEqual(record["criticality"], "High")

    def test_the_preview_can_say_what_each_component_became(self) -> None:
        self.assertEqual(self.out.block_ids["public-web-tier"]["cdn"], "TS-AWS-CLOUDFRONT")
        self.assertEqual(self.out.block_ids["public-web-tier"]["waf"], "TS-PROBE-WAF")


class TestBlockGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()

    def _shape(self, **changes):
        data = dict(SHAPE)
        data.update(changes)
        return parse_archetype(data)

    def test_excluding_a_created_service_drops_what_ran_on_it(self) -> None:
        out = expand(_instance(exclude=["TS-PROBE-WAF"]), self._shape(), "products", self.library)
        self.assertNotIn("TS-PROBE-WAF", {r["tech_service_id"] for r in out.entities["tech_services"]})
        for row in out.relations["system_uses_tech_service"]:
            self.assertNotEqual(row["tech_service_id"], "TS-PROBE-WAF")
        for row in out.relations["tech_service_connects_to"]:
            self.assertNotIn("TS-PROBE-WAF", row.values())

    def test_an_override_reaches_a_created_service(self) -> None:
        out = expand(
            _instance(overrides={"TS-PROBE-CACHE": {"resilience": "Single-AZ"}}),
            self._shape(), "products", self.library,
        )
        cache = next(r for r in out.entities["tech_services"] if r["tech_service_id"] == "TS-PROBE-CACHE")
        self.assertEqual(cache["resilience"], "Single-AZ")

    def test_an_unknown_block_is_refused(self) -> None:
        with self.assertRaises(ArchetypeError):
            expand(_instance(), self._shape(blocks=[{"block": "no-such-block"}]), "products", self.library)

    def test_binding_a_component_the_block_lacks_is_refused(self) -> None:
        with self.assertRaises(ArchetypeError):
            expand(
                _instance(),
                self._shape(blocks=[{"block": "public-web-tier", "bind": {"router": "TS-X"}}]),
                "products", self.library,
            )

    def test_running_on_something_the_shape_is_not_built_on_is_refused(self) -> None:
        provides = {"systems": [{"system_id": "SYS-{slug|upper}-A", "name": "a", "runs_on": ["event-tier"]}]}
        with self.assertRaises(ArchetypeError):
            expand(_instance(), self._shape(provides=provides), "products", self.library)
        provides = {"systems": [{"system_id": "SYS-{slug|upper}-A", "name": "a",
                                 "runs_on": ["public-web-tier.router"]}]}
        with self.assertRaises(ArchetypeError):
            expand(_instance(), self._shape(provides=provides), "products", self.library)

    def test_the_same_component_from_two_blocks_is_refused_unless_bound(self) -> None:
        """Two blocks both providing DNS would create TS-PROBE-DNS twice."""
        shape = self._shape(blocks=[{"block": "public-web-tier"}, {"block": "public-api-tier"}])
        with self.assertRaises(ArchetypeError) as caught:
            expand(_instance(), shape, "products", self.library)
        self.assertIn("twice", str(caught.exception))

    def test_a_block_can_be_used_twice_under_an_alias(self) -> None:
        shape = self._shape(
            blocks=[
                {"block": "stateless-service", "bind": {"container-platform": "TS-AWS-EKS"}},
                {"block": "stateless-service", "as": "batch", "id": "{slug}-batch",
                 "bind": {"container-platform": "TS-AWS-EKS"}},
            ],
            provides={"systems": [{"system_id": "SYS-{slug|upper}-A", "name": "a", "runs_on": ["batch"]}]},
        )
        out = expand(_instance(), shape, "products", self.library)
        created = {r["tech_service_id"] for r in out.entities["tech_services"]}
        self.assertIn("TS-PROBE-CACHE", created)
        self.assertIn("TS-PROBE-BATCH-CACHE", created)

    def test_blocks_need_the_library(self) -> None:
        with self.assertRaises(ArchetypeError):
            expand(_instance(), self._shape(), "products", None)

    def test_a_shape_without_blocks_needs_no_library(self) -> None:
        shape = self._shape(blocks=[], provides={"systems": [
            {"system_id": "SYS-{slug|upper}-A", "name": "a", "uses": ["TS-AWS-EKS"]},
        ]})
        out = expand(_instance(), shape, "products", None)
        self.assertEqual(
            out.relations["system_uses_tech_service"],
            [{"system_id": "SYS-PROBE-A", "tech_service_id": "TS-AWS-EKS", "archetype_instance": "PRD-P"}],
        )

    def test_shorthands_are_only_for_systems(self) -> None:
        shape = self._shape(provides={"data_assets": [
            {"data_asset_id": "DA-{slug|upper}-X", "name": "x", "uses": ["TS-AWS-S3"]},
        ]})
        with self.assertRaises(ArchetypeError):
            expand(_instance(), shape, "products", self.library)


class TestShippedShapes(unittest.TestCase):
    """The six archetypes in the repository, expanded against the seeded estate."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.library = _library()

    def test_every_shape_expands_against_a_stand_in_instance(self) -> None:
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import server

        for archetype in self.model.archetypes.values():
            with self.subTest(archetype=archetype.archetype_id):
                out = expand(
                    server._sample_instance(archetype), archetype, archetype.applies_to, self.library
                )
                self.assertTrue(out.entities.get("systems"))
                self.assertTrue(out.relations.get("product_includes_system"))

    def test_every_bound_service_exists_in_the_estate(self) -> None:
        """A bind to a service that is not there is a dangling reference on
        every instance, and the shape should not be able to say it. A shipped
        shape binds to the landing zone rather than to a service by id, and
        the sample's landing zone answers every kind it binds that way."""
        zone = landing_zone_index(self.model.all_of("tech_services"))
        for archetype in self.model.archetypes.values():
            for entry in archetype.blocks:
                for component, service_id in (entry.get("bind") or {}).items():
                    with self.subTest(archetype=archetype.archetype_id, component=component):
                        if service_id == LANDING_ZONE_TAG:
                            service_id = resolve_kind(component, archetype.provider, zone)[0]
                        self.assertIsNotNone(self.model.get("tech_services", service_id), service_id)

    def test_no_shipped_shape_binds_a_service_by_id(self) -> None:
        """The shapes bound the card issuer's own services by id, and an
        estate building on them had to hold its records under those ids."""
        for archetype in load_archetypes(REPO).values():
            for entry in archetype.blocks:
                for component, service_id in (entry.get("bind") or {}).items():
                    with self.subTest(archetype=archetype.archetype_id, component=component):
                        self.assertEqual(service_id, LANDING_ZONE_TAG)
            self.assertEqual(dict(archetype.bind), {}, archetype.archetype_id)

    def test_the_aws_shape_creates_what_version_one_forgot(self) -> None:
        shape = self.model.archetypes["aws-product-onboarding"]
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import server

        out = expand(server._sample_instance(shape), shape, "products", self.library)
        kinds = {r["component_type"] for r in out.entities.get("tech_services", [])}
        self.assertEqual(kinds, {"waf", "dns", "cache", "backup"})

    def test_the_saas_shape_creates_no_infrastructure(self) -> None:
        shape = self.model.archetypes["saas-onboarding"]
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import server

        out = expand(server._sample_instance(shape), shape, "products", self.library)
        self.assertNotIn("tech_services", out.entities)
        self.assertTrue(out.relations["system_uses_tech_service"])


if __name__ == "__main__":
    unittest.main()
