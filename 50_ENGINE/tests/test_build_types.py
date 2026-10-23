"""Tests for build types: the kinds of thing the organization builds and the
standard build of each.

What is checked: the shipped types load and name real parts and shapes; a
type that names a part the library lacks, lists a part twice, or maps a shape
that does not compose a required part is a problem; a product's parts are
read off its expansion by id; the conformance of a product to its type says
what is missing, dropped and unlisted, with a kit counted by its members;
validate carries the deviations as warnings and an unknown type as an error;
and the catalog renders each type with the products on it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import model as model_module, validate  # noqa: E402
from terrane.build_types import (  # noqa: E402
    BuildTypeError,
    check_build_types,
    conformance,
    load_build_types,
    parse_build_type,
    shape_for,
)
from terrane.modules import load_modules  # noqa: E402
from terrane.render_library import render_build_types  # noqa: E402

from _fixture import REPO  # noqa: E402

_MODEL = None


def shipped_model():
    """The repository's own model, read once and never written."""
    global _MODEL
    if _MODEL is None:
        _MODEL = model_module.load(REPO)
    return _MODEL


class TestLibrary(unittest.TestCase):
    def test_the_shipped_types_name_real_parts_and_shapes(self) -> None:
        types = load_build_types(REPO)
        modules = load_modules(REPO)
        self.assertIn("digital-product", types)
        self.assertEqual(check_build_types(types, modules, shipped_model().archetypes.values()), [])
        self.assertEqual(types["digital-product"].shapes["AWS"], "aws-product-onboarding")

    def test_a_type_needs_an_id_and_a_name(self) -> None:
        with self.assertRaises(BuildTypeError):
            parse_build_type({"name": "Nameless"})
        with self.assertRaises(BuildTypeError):
            parse_build_type({"build_type_id": "x"})

    def test_a_part_the_library_lacks_is_a_problem(self) -> None:
        build_type = parse_build_type({"build_type_id": "x", "name": "X", "requires": ["no-such-part"]})
        problems = check_build_types({"x": build_type}, load_modules(REPO), [])
        self.assertTrue(any("no-such-part" in problem for problem, _where in problems))

    def test_a_part_is_required_or_offered_not_both(self) -> None:
        build_type = parse_build_type(
            {"build_type_id": "x", "name": "X", "requires": ["api-service"], "offers": ["api-service"]}
        )
        problems = check_build_types({"x": build_type}, load_modules(REPO), [])
        self.assertTrue(any("one or the other" in problem for problem, _where in problems))

    def test_a_mapped_shape_must_compose_every_required_part(self) -> None:
        build_type = parse_build_type(
            {"build_type_id": "x", "name": "X", "requires": ["sso-federation"],
             "shapes": {"Azure": "vendor-saas-service"}}
        )
        problems = check_build_types({"x": build_type}, load_modules(REPO), shipped_model().archetypes.values())
        self.assertTrue(any("does not compose" in problem for problem, _where in problems))

    def test_a_shape_on_another_provider_is_a_problem(self) -> None:
        build_type = parse_build_type(
            {"build_type_id": "x", "name": "X", "shapes": {"AWS": "azure-digital-product"}}
        )
        problems = check_build_types({"x": build_type}, load_modules(REPO), shipped_model().archetypes.values())
        self.assertTrue(any("but the shape is on Azure" in problem for problem, _where in problems))

    def test_the_shape_for_a_provider_falls_back_to_any(self) -> None:
        types = load_build_types(REPO)
        self.assertEqual(shape_for(types["data-product"], "GCP"), "batch-data-product-gcp")
        self.assertEqual(shape_for(types["data-product"], "AWS"), "batch-data-product")
        self.assertEqual(shape_for(types["shared-hub"], "AWS"), "")


class TestConformance(unittest.TestCase):
    def test_what_a_product_has_is_read_off_its_expansion(self) -> None:
        parts = shipped_model().parts
        self.assertIn("api-service", parts["PRD-INSTALLMENT-LENDING"])
        self.assertIn("web-channel", parts["PRD-INSTALLMENT-LENDING"])
        # A kit arrives as its members.
        self.assertIn("vendor-tenancy", parts["PRD-SCREENING"])
        self.assertNotIn("event-publisher", parts["PRD-COLLECTIONS-WORKSPACE"])

    def test_missing_dropped_and_unlisted(self) -> None:
        types = load_build_types(REPO)
        modules = load_modules(REPO)
        c = conformance(types["digital-product"], ["api-service", "network-hub"], modules)
        self.assertEqual(c.missing, [])
        self.assertEqual(c.dropped, ["web-channel", "relational-datastore"])
        self.assertEqual(c.unlisted, ["network-hub"])
        self.assertFalse(c.clean)
        full = conformance(
            types["digital-product"], ["api-service", "web-channel", "relational-datastore", "event-publisher"], modules
        )
        self.assertTrue(full.clean)

    def test_a_kit_counts_by_its_members(self) -> None:
        types = load_build_types(REPO)
        modules = load_modules(REPO)
        self.assertEqual(conformance(types["bought-saas"], ["vendor-tenancy"], modules).missing, ["vendor-baseline"])
        whole = conformance(types["bought-saas"], ["vendor-tenancy", "api-outbound", "secrets-management"], modules)
        self.assertEqual(whole.missing, [])
        self.assertEqual(whole.unlisted, [])

    def test_validate_says_where_a_product_departs_from_its_type(self) -> None:
        report = validate.run(shipped_model())
        codes = {f.code for f in report.findings}
        self.assertNotIn("types.invalid", codes)
        self.assertNotIn("types.unknown", codes)
        # The lending product adds an integration hub of its own, which a
        # digital product neither includes nor offers: the one deviation the
        # shipped estate carries, on purpose.
        unlisted = [f for f in report.findings if f.code == "types.unlisted_part"]
        self.assertTrue(any("PRD-INSTALLMENT-LENDING" in f.message and "integration-hub" in f.message
                            for f in unlisted))
        self.assertTrue(all(f.severity == "warning" for f in unlisted))
        self.assertEqual([f for f in report.findings if f.code == "types.deviation"], [])

    def test_an_unknown_type_on_a_product_is_an_error(self) -> None:
        model = model_module.load(REPO)
        model.entities["products"]["PRD-IDENTITY"]["build_type"] = "no-such-type"
        report = validate.run(model)
        self.assertTrue(any(f.code == "types.unknown" and f.severity == "error" for f in report.findings))

    def test_the_catalog_renders_each_type_with_its_products(self) -> None:
        model = shipped_model()
        text = render_build_types(load_build_types(REPO), load_modules(REPO), model.archetypes.values(), model)
        self.assertIn("Customer-facing digital product", text)
        self.assertIn("PRD-INSTALLMENT-LENDING", text)
        self.assertIn("with integration-hub", text)


if __name__ == "__main__":
    unittest.main()
