"""Tests for the pattern library: a building block plus the decision.

A pattern is what a review board governs, so the guards here are about the
decision being present and the references being real: every pattern names
blocks that exist, states its cost and its exclusions, and names no estate's
records: who owns it, the decision that approved it and the controls it meets
are the estate's, in its `model.yaml`, and the sample's name controls its
register holds. And the adoption report has to be read off the model rather
than off a list somebody keeps.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import blocks, validate  # noqa: E402
from terrane.archetype import expand, parse_archetype  # noqa: E402
from terrane.answers import ADOPTED_FIELDS, EstateError, adopted_patterns, pattern_adoption  # noqa: E402
from terrane.render_library import render_blocks, render_patterns  # noqa: E402

from _fixture import (  # noqa: E402
    REPO,
    Sandbox,
    seeded_model,
    seeded_root,
    seeded_views,
    setup_shared,
    teardown_shared,
)


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _library():
    components = blocks.load_components(REPO)
    building_blocks = blocks.load_blocks(REPO, components)
    return components, building_blocks, blocks.load_patterns(REPO, building_blocks)


class TestPatternLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.components, cls.blocks, cls.patterns = _library()

    def test_the_library_loads(self) -> None:
        self.assertGreaterEqual(len(self.patterns), 8)

    def test_every_pattern_is_made_of_blocks_that_exist(self) -> None:
        for pattern in self.patterns.values():
            with self.subTest(pattern=pattern.pattern_id):
                self.assertTrue(pattern.blocks)
                for block_id in pattern.blocks:
                    self.assertIn(block_id, self.blocks)

    def test_every_pattern_states_the_decision(self) -> None:
        """Intent, cost and exclusion. A pattern without a stated cost or a
        stated exclusion is a preference, and a review board cannot govern a
        preference."""
        for pattern in self.patterns.values():
            with self.subTest(pattern=pattern.pattern_id):
                for text in (pattern.intent, pattern.consequences, pattern.when_not_to_use):
                    self.assertGreater(len(text.split()), 12)

    def test_status_comes_from_the_vocabulary(self) -> None:
        for pattern in self.patterns.values():
            with self.subTest(pattern=pattern.pattern_id):
                self.assertIn(pattern.status, blocks.PATTERN_STATUS)

    def test_no_pattern_names_a_vendor(self) -> None:
        """Same rule as blocks, for the same reason: the pattern is the
        architecture building block, and naming a product in it is what would
        make a cloud migration a redrawing."""
        vendors = ("AWS", "Azure", "Amazon", "Google", "Microsoft", "S3", "Lambda", "CloudFront")
        for pattern in self.patterns.values():
            text = " ".join([pattern.name, pattern.intent, pattern.consequences,
                             pattern.when_not_to_use])
            for vendor in vendors:
                with self.subTest(pattern=pattern.pattern_id, vendor=vendor):
                    self.assertNotIn(vendor, text)

    def test_a_pattern_naming_an_unknown_block_is_refused(self) -> None:
        pattern = blocks.parse_pattern({
            "pattern_id": "x", "name": "x", "blocks": ["no-such-block"],
            "intent": "i", "consequences": "c", "when_not_to_use": "w",
        })
        with self.assertRaises(blocks.LibraryError):
            blocks.check_pattern(pattern, self.blocks)

    def test_a_pattern_without_the_decision_is_refused(self) -> None:
        for missing in ("intent", "consequences", "when_not_to_use"):
            data = {
                "pattern_id": "x", "name": "x", "blocks": ["public-web-tier"],
                "intent": "i", "consequences": "c", "when_not_to_use": "w",
            }
            del data[missing]
            with self.subTest(missing=missing):
                with self.assertRaises(blocks.LibraryError):
                    blocks.parse_pattern(data)

    def test_a_status_outside_the_vocabulary_is_refused(self) -> None:
        with self.assertRaises(blocks.LibraryError):
            blocks.parse_pattern({
                "pattern_id": "x", "name": "x", "blocks": ["public-web-tier"],
                "status": "Blessed",
                "intent": "i", "consequences": "c", "when_not_to_use": "w",
            })

    def test_a_shipped_pattern_names_no_estates_records(self) -> None:
        """Who owns a pattern, the decision that approved it and the controls
        it meets are one organization's. The shipped patterns named the card
        issuer's, and the health system heard fifty-one warnings about them."""
        for pattern in self.patterns.values():
            with self.subTest(pattern=pattern.pattern_id):
                self.assertEqual(pattern.owner_org_id, "")
                self.assertEqual(pattern.decision_ref, "")
                self.assertEqual(list(pattern.satisfies), [])

    def test_the_controls_a_pattern_satisfies_are_in_the_register(self) -> None:
        model = seeded_model()
        known = {c["control_id"] for c in model.all_of("controls")}
        adopted = adopted_patterns(self.patterns, model.config)
        self.assertTrue(any(p.satisfies for p in adopted.values()))
        for pattern in adopted.values():
            for control_id in pattern.satisfies:
                with self.subTest(pattern=pattern.pattern_id, control=control_id):
                    self.assertIn(control_id, known)

    def test_every_owner_is_an_org_unit_the_model_holds(self) -> None:
        model = seeded_model()
        known = {o["org_unit_id"] for o in model.all_of("org_units")}
        for pattern in adopted_patterns(self.patterns, model.config).values():
            with self.subTest(pattern=pattern.pattern_id):
                self.assertIn(pattern.owner_org_id, known)

    def test_what_an_estate_says_of_a_pattern_is_held_to_three_fields(self) -> None:
        self.assertEqual(
            pattern_adoption({"patterns": {"api-front-door": {"satisfies": "CTL-A; CTL-B"}}}),
            {"api-front-door": {"satisfies": ["CTL-A", "CTL-B"]}},
        )
        for bad in ({"patterns": ["api-front-door"]},
                    {"patterns": {"api-front-door": "ORG-X"}},
                    {"patterns": {"api-front-door": {"owner": "ORG-X"}}}):
            with self.subTest(config=bad):
                with self.assertRaises(EstateError):
                    pattern_adoption(bad)
        self.assertEqual(ADOPTED_FIELDS, ("owner_org_id", "decision_ref", "satisfies"))

    def test_an_estate_naming_a_pattern_the_library_lacks_is_an_error(self) -> None:
        model = seeded_model()
        model.config = dict(model.config)
        model.config["patterns"] = dict(model.config.get("patterns") or {})
        model.config["patterns"]["no-such-pattern"] = {"owner_org_id": "ORG-TECH"}
        found = [f for f in validate.run(model, []).errors if f.code == "pattern.unknown"]
        self.assertTrue(any("no-such-pattern" in f.message for f in found))


class TestProductsApplyPatterns(unittest.TestCase):
    ARCHETYPE = {
        "archetype_id": "shape",
        "applies_to": "products",
        "patterns": ["public-web-entry", "stateless-request-service"],
        "parameters": [{"name": "slug", "required": True}],
        "provides": {"systems": [{
            "system_id": "SYS-{slug|upper}-A", "name": "a", "status": "Active",
            "owner_org_id": "ORG-X", "criticality": "Low",
        }]},
    }

    def test_an_instance_inherits_the_archetype_patterns(self) -> None:
        archetype = parse_archetype(dict(self.ARCHETYPE))
        instance = {"product_id": "PRD-P", "name": "P", "status": "Active",
                    "owner_org_id": "ORG-X", "parameters": {"slug": "p"}}
        out = expand(instance, archetype, "products")
        self.assertEqual(
            out.instance["patterns"], ["public-web-entry", "stateless-request-service"]
        )

    def test_an_instance_can_add_its_own_and_nothing_is_doubled(self) -> None:
        archetype = parse_archetype(dict(self.ARCHETYPE))
        instance = {"product_id": "PRD-P", "name": "P", "status": "Active",
                    "owner_org_id": "ORG-X", "parameters": {"slug": "p"},
                    "patterns": ["event-fanout", "public-web-entry"]}
        out = expand(instance, archetype, "products")
        self.assertEqual(
            out.instance["patterns"],
            ["public-web-entry", "stateless-request-service", "event-fanout"],
        )

    def test_a_product_naming_an_unknown_pattern_fails_the_gates(self) -> None:
        with Sandbox(seed=True) as root:
            path = root / "10_MODEL" / "products" / "PRD-GHOST.yaml"
            path.write_text(
                "product_id: PRD-GHOST\nname: Ghost\nstatus: Active\n"
                "owner_org_id: ORG-TECH\npatterns: [no-such-pattern]\n",
                encoding="utf-8",
            )
            from terrane import model as model_module

            report = validate.run(model_module.load(root))
            codes = {f.code for f in report.errors}
            self.assertIn("pattern.unknown", codes)

    def test_a_broken_pattern_file_fails_the_gates(self) -> None:
        """A library CI does not check is a library that breaks on the day
        somebody needs it."""
        with Sandbox(seed=True) as root:
            path = root / "27_PATTERNS" / "broken.yaml"
            path.write_text(
                "- pattern_id: broken\n  name: Broken\n  blocks: [no-such-block]\n"
                "  intent: i\n  consequences: c\n  when_not_to_use: w\n",
                encoding="utf-8",
            )
            from terrane import model as model_module

            report = validate.run(model_module.load(root))
            self.assertIn("library.invalid", {f.code for f in report.errors})

    def test_the_seeded_estate_applies_patterns_and_the_gates_pass(self) -> None:
        model = seeded_model()
        applied = {
            p for record in model.all_of("products") for p in model.list_of(record, "patterns")
        }
        self.assertTrue(applied)
        report = validate.run(model, seeded_views())
        self.assertEqual(report.errors, [])

    def test_a_product_on_a_deprecated_pattern_warns_and_does_not_fail(self) -> None:
        """A retirement the board has decided is a finding, and the count of
        products still on the pattern is what the retirement looks like."""
        model = seeded_model()
        report = validate.run(model)
        deprecated = [f for f in report.findings if f.code == "pattern.deprecated"]
        self.assertTrue(deprecated)
        self.assertTrue(all(f.severity == "warning" for f in deprecated))

    def test_coverage_names_the_products_on_a_deprecated_pattern(self) -> None:
        root = seeded_root()
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        gaps = {g["key"]: g for g in server_module.api_coverage({}, {})["gaps"]}
        self.assertIn("product.deprecated-pattern", gaps)
        _components, _blocks, patterns = _library()
        retired = {p.pattern_id for p in patterns.values() if p.status == "Deprecated"}
        model = seeded_model()
        for item in gaps["product.deprecated-pattern"]["items"]:
            record = model.get("products", item["id"])
            self.assertTrue(set(model.list_of(record, "patterns")) & retired)


class TestInterfacesApplyPatterns(unittest.TestCase):
    """Three of the method's reference patterns are about how two systems
    talk, so an interface is held to the library the way a product is."""

    def test_an_interface_naming_an_unknown_pattern_fails_the_gates(self) -> None:
        with Sandbox(seed=True) as root:
            path = root / "10_MODEL" / "interfaces" / "INT-GHOST.yaml"
            path.write_text(
                "interface_id: INT-GHOST\nname: Ghost\nstatus: Active\n"
                "source_system_id: SYS-CRM\ntarget_system_id: SYS-CORE-LEDGER\n"
                "patterns: [no-such-pattern]\n",
                encoding="utf-8",
            )
            from terrane import model as model_module

            report = validate.run(model_module.load(root))
            unknown = [f for f in report.errors if f.code == "pattern.unknown"]
            self.assertTrue(unknown)
            self.assertIn("interface INT-GHOST", unknown[0].message)

    def test_an_interface_on_a_deprecated_pattern_warns(self) -> None:
        with Sandbox(seed=True) as root:
            path = root / "10_MODEL" / "interfaces" / "INT-OLD.yaml"
            path.write_text(
                "interface_id: INT-OLD\nname: Old\nstatus: Active\n"
                "source_system_id: SYS-CRM\ntarget_system_id: SYS-CORE-LEDGER\n"
                "patterns: [shared-database-integration]\n",
                encoding="utf-8",
            )
            from terrane import model as model_module

            report = validate.run(model_module.load(root))
            self.assertEqual(report.errors, [])
            codes = [f for f in report.findings
                     if f.code == "pattern.deprecated" and "INT-OLD" in f.message]
            self.assertTrue(codes)

    def test_the_seeded_estate_has_interfaces_on_patterns(self) -> None:
        """The harvested estate's connections each name how they are built;
        an interface inventory with no patterns on it is one the board has
        not seen."""
        model = seeded_model()
        on = [r for r in model.all_of("interfaces") if model.list_of(r, "patterns")]
        self.assertGreaterEqual(len(on), 30)
        _components, _blocks, patterns = _library()
        for record in on:
            for pattern_id in model.list_of(record, "patterns"):
                with self.subTest(interface=record["interface_id"], pattern=pattern_id):
                    self.assertIn(pattern_id, patterns)

    def test_most_patterns_name_the_method_pattern_they_implement(self) -> None:
        _components, _blocks, patterns = _library()
        with_ref = {p.pattern_id: p.method_ref for p in patterns.values() if p.method_ref}
        self.assertGreaterEqual(len(with_ref), 15)
        for pattern_id, ref in with_ref.items():
            with self.subTest(pattern=pattern_id):
                self.assertRegex(ref, r"^PAT-\d{3}$")
        # The deprecated shared database implements nothing the method
        # recommends, and says so by naming none.
        self.assertNotIn("shared-database-integration", with_ref)


class TestRenderedCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.components, cls.blocks, cls.patterns = _library()
        cls.model = seeded_model()

    def test_every_pattern_is_in_the_catalog_with_its_decision(self) -> None:
        text = render_patterns(self.patterns, self.blocks, self.components, self.model)
        for pattern in self.patterns.values():
            with self.subTest(pattern=pattern.pattern_id):
                self.assertIn("## %s" % pattern.name, text)
                self.assertIn("**When not to use it.**", text)
                self.assertIn(pattern.status, text)

    def test_adoption_is_read_off_the_model(self) -> None:
        text = render_patterns(self.patterns, self.blocks, self.components, self.model)
        for record in self.model.all_of("products"):
            for pattern_id in self.model.list_of(record, "patterns"):
                with self.subTest(product=record["product_id"], pattern=pattern_id):
                    self.assertIn("(`%s`)" % record["product_id"], text)
        for record in self.model.all_of("interfaces"):
            for pattern_id in self.model.list_of(record, "patterns"):
                with self.subTest(interface=record["interface_id"], pattern=pattern_id):
                    self.assertIn("(`%s`)" % record["interface_id"], text)
        self.assertIn("**On interfaces.**", text)
        self.assertIn("Nothing in the model yet", text)

    def test_the_estates_owner_and_decision_are_in_the_catalog(self) -> None:
        """Read from the estate's model.yaml, so the sample's catalog says
        what it said when the patterns carried them."""
        text = render_patterns(self.patterns, self.blocks, self.components, self.model)
        for pattern in adopted_patterns(self.patterns, self.model.config).values():
            with self.subTest(pattern=pattern.pattern_id):
                owner = self.model.get("org_units", pattern.owner_org_id)
                self.assertIn("**Owner:** %s" % owner["name"], text)
                self.assertIn("**Decision:** %s" % pattern.decision_ref, text)

    def test_the_method_reference_is_in_the_catalog(self) -> None:
        text = render_patterns(self.patterns, self.blocks, self.components, self.model)
        for pattern in self.patterns.values():
            if pattern.method_ref:
                with self.subTest(pattern=pattern.pattern_id):
                    self.assertIn("**Method:** %s" % pattern.method_ref, text)

    def test_controls_are_named_not_just_numbered(self) -> None:
        text = render_patterns(self.patterns, self.blocks, self.components, self.model)
        for pattern in adopted_patterns(self.patterns, self.model.config).values():
            for control_id in pattern.satisfies:
                control = self.model.get("controls", control_id)
                with self.subTest(control=control_id):
                    self.assertIn(control["name"], text)

    def test_the_block_catalog_resolves_every_block_per_provider(self) -> None:
        text = render_blocks(self.blocks, self.components, self.patterns)
        for block in self.blocks.values():
            with self.subTest(block=block.building_block_id):
                self.assertIn("## %s" % block.name, text)
        self.assertIn("| Component | AWS | Azure |", text)

    def test_rendering_is_deterministic(self) -> None:
        first = render_patterns(self.patterns, self.blocks, self.components, self.model)
        second = render_patterns(self.patterns, self.blocks, self.components, self.model)
        self.assertEqual(first, second)
        self.assertEqual(
            render_blocks(self.blocks, self.components, self.patterns),
            render_blocks(self.blocks, self.components, self.patterns),
        )


class TestLibraryEndpoint(unittest.TestCase):
    def test_the_library_endpoint_carries_patterns_and_adoption(self) -> None:
        root = seeded_root()
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        lib = server_module.api_library(None, None)
        self.assertTrue(lib["patterns"])
        one = lib["patterns"][0]
        for key in ("id", "name", "status", "blocks", "intent", "consequences",
                    "whenNotToUse", "satisfies", "appliedBy", "methodRef"):
            self.assertIn(key, one)
        self.assertTrue(any(p["appliedBy"] for p in lib["patterns"]))
        kinds = {a["kind"] for p in lib["patterns"] for a in p["appliedBy"]}
        self.assertEqual(kinds, {"product", "interface"})
        self.assertTrue(any(p["methodRef"] for p in lib["patterns"]))


if __name__ == "__main__":
    unittest.main()
