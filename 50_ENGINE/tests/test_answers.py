"""The library names no estate's records; the estate answers what it asks.

A second estate built on the shipped shapes and parts had to hold eighteen
records under the sample's ids, because the parts gave the private egress to
`ORG-TECH`, sent the audit trail to `SYS-SIEM` and governed a vendor with
`CTL-TPRM-DD`, and the shapes bound the sample's Key Vault by id. These hold
the three ways that is answered instead (`terrane/answers.py`): a kind the landing
zone answers, where a technology service was named; a parameter marked
`estate`, answered once in `model.yaml`, where anything else was; and the
check that the shipped library names no record the sample holds, so the next
one is caught by the suite rather than by the next estate.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.archetype import (  # noqa: E402
    ArchetypeError,
    expand,
    has_landing_zone,
    landing_zone_gaps,
    landing_zone_index,
    load_archetypes,
)
from terrane.blocks import load_blocks, load_components  # noqa: E402
from terrane.answers import EstateError, estate_answers  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402
from terrane.modules import load_modules  # noqa: E402
from terrane.schema import ENTITY_TYPES  # noqa: E402

from _fixture import REPO, seeded_model, setup_shared, teardown_shared  # noqa: E402

#: The shipped library's layers.
LAYERS = (
    "20_ARCHETYPES", "24_CONNECTIONS", "25_COMPONENTS", "26_BLOCKS", "27_PATTERNS",
    "28_MODULES", "29_TYPES",
)

#: Keys whose values are prose. A description may say "e.g. ORG-DIGITAL" to
#: show what an id looks like; a value the engine reads may not name one.
PROSE = {"description", "name", "title", "intent", "consequences", "when_not_to_use"}

_ID = re.compile(r"(?<![A-Za-z0-9{|-])[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?![A-Za-z0-9}-])")


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _values(data, key=""):
    """Every string the engine would read, with the key it sits under."""
    if isinstance(data, dict):
        for k, v in data.items():
            if str(k) in PROSE:
                continue
            yield from _values(v, str(k))
    elif isinstance(data, list):
        for item in data:
            yield from _values(item, key)
    elif isinstance(data, str):
        yield key, data


class TheLibraryNamesNoSampleRecord(unittest.TestCase):
    def test_no_shipped_library_value_names_a_record_the_sample_holds(self) -> None:
        model = seeded_model()
        held = {str(record[spec.pk]) for name, spec in ENTITY_TYPES.items()
                for record in model.all_of(name)}
        self.assertIn("ORG-TECH", held)  # the measure is the sample's records
        found = []
        for layer in LAYERS:
            for path in sorted((REPO / layer).glob("*.yaml")):
                data = read_data_file(path)
                for key, value in _values(data):
                    for named in _ID.findall(value):
                        if named in held:
                            found.append("%s/%s: %s: %s" % (layer, path.name, key, named))
        self.assertEqual(found, [], "name a kind the landing zone answers, or ask the estate")


class _Expanding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.components = load_components(REPO)
        cls.blocks = load_blocks(REPO, cls.components)
        cls.modules = load_modules(REPO)
        cls.shapes = load_archetypes(REPO)
        cls.model = seeded_model()
        cls.zone = landing_zone_index(cls.model.all_of("tech_services"))
        cls.answers = estate_answers(read_data_file(REPO / "10_MODEL" / "model.yaml"))

    def expand(self, instance, shape_id, answers=None, zone=None):
        library = (
            self.components, self.blocks, self.modules,
            self.zone if zone is None else zone,
            self.answers if answers is None else answers,
        )
        return expand(dict(instance), self.shapes[shape_id], "products", library)

    @staticmethod
    def one(expansion, type_name, entity_id):
        pk = ENTITY_TYPES[type_name].pk
        return next(r for r in expansion.entities.get(type_name, []) if r[pk] == entity_id)


VENDOR = {
    "product_id": "PRD-T", "name": "T", "status": "Planned",
    "archetype": "vendor-saas-service",
    "parameters": {
        "slug": "t", "product_name": "T", "vendor": "V", "owner_org": "ORG-DIGITAL",
        "domain": "D", "upstream_system": "SYS-CRM", "account": "azure-x",
    },
    "choose": {"reach": "private-egress"},
    "modules": [{"module": "audit-forwarding"}],
}


class TheEstateAnswers(_Expanding):
    def test_a_part_takes_the_estates_answer(self) -> None:
        made = self.expand(VENDOR, "vendor-saas-service")
        self.assertEqual(self.one(made, "systems", "SYS-T-EGRESS")["owner_org_id"], "ORG-TECH")
        audit = self.one(made, "interfaces", "INT-T-VENDOR-AUDIT")
        self.assertEqual((audit["target_system_id"], audit["owner_org_id"]), ("SYS-SIEM", "ORG-INFOSEC"))
        governed = {(r["system_id"], r["control_id"])
                    for r in made.relations.get("system_governed_by_control", [])}
        self.assertIn(("SYS-T-VENDOR", "CTL-TPRM-DD"), governed)

    def test_another_estates_answer_is_its_own(self) -> None:
        answers = dict(self.answers, platform_org="ORG-OURS", siem_system="SYS-OURS-SOC",
                       vendor_controls=["CTL-OURS"])
        made = self.expand(VENDOR, "vendor-saas-service", answers=answers)
        self.assertEqual(self.one(made, "systems", "SYS-T-EGRESS")["owner_org_id"], "ORG-OURS")
        self.assertEqual(self.one(made, "interfaces", "INT-T-VENDOR-AUDIT")["target_system_id"], "SYS-OURS-SOC")
        governed = {r["control_id"] for r in made.relations.get("system_governed_by_control", [])}
        self.assertEqual(governed, {"CTL-OURS"})

    def test_the_product_still_says_otherwise_for_itself(self) -> None:
        instance = dict(VENDOR, modules=[{"module": "audit-forwarding", "with": {"siem_system": "SYS-MINE"}}])
        made = self.expand(instance, "vendor-saas-service")
        self.assertEqual(self.one(made, "interfaces", "INT-T-VENDOR-AUDIT")["target_system_id"], "SYS-MINE")

    def test_a_list_with_a_default_is_empty_unanswered(self) -> None:
        answers = {k: v for k, v in self.answers.items() if not k.startswith("vendor_")}
        made = self.expand(VENDOR, "vendor-saas-service", answers=answers)
        governed = {r["system_id"] for r in made.relations.get("system_governed_by_control", [])}
        self.assertNotIn("SYS-T-VENDOR", governed)

    def test_an_unanswered_question_is_refused_with_where_to_answer_it(self) -> None:
        answers = {k: v for k, v in self.answers.items() if k != "platform_org"}
        with self.assertRaises(ArchetypeError) as caught:
            self.expand(VENDOR, "vendor-saas-service", answers=answers)
        self.assertIn("asks the estate for 'platform_org'", str(caught.exception))
        self.assertIn("`answers` in model.yaml", str(caught.exception))

    def test_a_shape_asks_the_estate_too(self) -> None:
        instance = {
            "product_id": "PRD-D", "name": "D", "status": "Active", "archetype": "batch-data-product",
            "parameters": {"slug": "d", "product_name": "D", "owner_org": "ORG-DATAENG", "domain": "X"},
        }
        made = self.expand(instance, "batch-data-product")
        self.assertEqual(self.one(made, "interfaces", "INT-D-INGEST")["source_system_id"], "SYS-DATA-INGEST")
        with self.assertRaises(ArchetypeError) as caught:
            self.expand(instance, "batch-data-product", answers={})
        self.assertIn("asks the estate for", str(caught.exception))

    def test_answers_are_a_mapping(self) -> None:
        with self.assertRaises(EstateError):
            estate_answers({"answers": ["platform_org"]})
        self.assertEqual(estate_answers({}), {})


class TheLandingZoneAnswersByKind(_Expanding):
    PORTAL = {
        "product_id": "PRD-P", "name": "P", "status": "Planned", "archetype": "azure-digital-product",
        "parameters": {"slug": "p", "product_name": "P", "owner_org": "ORG-DIGITAL",
                       "domain": "D", "account": "azure-x"},
    }

    def uses(self, made):
        return {(r["system_id"], r["tech_service_id"])
                for r in made.relations.get("system_uses_tech_service", [])}

    def test_a_block_bound_to_the_landing_zone_lands_on_its_service(self) -> None:
        made = self.expand(self.PORTAL, "azure-digital-product")
        self.assertIn(("SYS-P-API", "TS-AZURE-APIM"), self.uses(made))
        self.assertIn(("SYS-P-API", "TS-AZURE-KEYVAULT"), self.uses(made))
        self.assertIn(("SYS-P-WEB", "TS-ENTRA-ID"), self.uses(made))

    def test_whatever_the_estate_calls_it(self) -> None:
        zone = {key: list(ids) for key, ids in self.zone.items()}
        zone[("Azure", "api-gateway")] = ["TS-OUR-GATEWAY"]
        zone[("", "identity-provider")] = ["TS-OUR-IDP"]
        made = self.expand(self.PORTAL, "azure-digital-product", zone=zone)
        self.assertIn(("SYS-P-API", "TS-OUR-GATEWAY"), self.uses(made))
        self.assertIn(("SYS-P-WEB", "TS-OUR-IDP"), self.uses(made))
        self.assertNotIn("TS-AZURE-APIM", {s for _sys, s in self.uses(made)})

    def test_a_kind_the_zone_lacks_is_refused_by_kind(self) -> None:
        zone = {key: ids for key, ids in self.zone.items() if key != ("Azure", "api-gateway")}
        with self.assertRaises(ArchetypeError) as caught:
            self.expand(self.PORTAL, "azure-digital-product", zone=zone)
        self.assertIn("api-gateway", str(caught.exception))
        self.assertIn("landing-zone", str(caught.exception))

    def test_two_of_a_kind_used_by_kind_is_refused(self) -> None:
        zone = dict(self.zone)
        zone[("Azure", "secrets-manager")] = ["TS-A", "TS-B"]
        with self.assertRaises(ArchetypeError) as caught:
            self.expand(self.PORTAL, "azure-digital-product", zone=zone)
        self.assertIn("TS-A and TS-B", str(caught.exception))


class AProviderWithNoLandingZone(_Expanding):
    def test_a_neutral_service_is_no_landing_zone_on_a_cloud(self) -> None:
        zone = {("", "identity-provider"): ["TS-IDP"], ("Azure", "kms"): ["TS-KV"]}
        self.assertTrue(has_landing_zone("Azure", zone))
        self.assertFalse(has_landing_zone("AWS", zone))
        self.assertTrue(has_landing_zone("", zone))

    def test_has_no_gaps_only_a_wait(self) -> None:
        """The health system, all Azure, heard twenty-two gaps about AWS and
        Google Cloud, on top of the one wait per shape that says it all."""
        self.assertEqual(landing_zone_gaps(self.modules, self.shapes.values(), self.zone), [])
        azure_only = {key: ids for key, ids in self.zone.items()
                      if key[0] in ("", "Azure") and key[1] != "foundation-model-service"}
        gaps = landing_zone_gaps(self.modules, self.shapes.values(), azure_only)
        self.assertEqual([(g.provider, g.kind) for g in gaps], [("Azure", "foundation-model-service")])


if __name__ == "__main__":
    unittest.main()
