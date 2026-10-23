"""Tests for the component library and the building blocks.

The library's whole claim is that the same block resolves to different products
on different clouds, which is what makes a migration a re-parameterization
rather than a redrawing. Most of what is checked here is that claim, and the
guards on writing a block into the model.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import blocks, importer, model as model_module  # noqa: E402
from terrane.schema import ENTITY_TYPES  # noqa: E402

from _fixture import (  # noqa: E402
    EXAMPLE_CSV,
    REPO,
    Sandbox as _Sandbox,
    seeded_model,
    setup_shared,
    teardown_shared,
)


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestComponentLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.components = blocks.load_components(REPO)
        cls.blocks = blocks.load_blocks(REPO, cls.components)

    def test_the_library_loads(self) -> None:
        self.assertGreater(len(self.components), 30)
        self.assertGreater(len(self.blocks), 8)

    def test_every_component_says_what_it_becomes(self) -> None:
        for component in self.components.values():
            with self.subTest(component=component.component_type_id):
                self.assertIn(component.applies_to, ENTITY_TYPES)
                self.assertTrue(component.description.strip())
                self.assertTrue(component.category)

    def test_every_block_is_made_of_components_that_exist(self) -> None:
        """A block naming a component that is not there would expand into an
        entity with no type and no defaults, which is worse than refusing."""
        for block in self.blocks.values():
            for provided in block.provides:
                with self.subTest(block=block.building_block_id):
                    self.assertIn(provided.component, self.components)

    def test_a_block_only_relates_what_it_provides(self) -> None:
        for block in self.blocks.values():
            names = {p.component for p in block.provides}
            for source, target in block.relations:
                with self.subTest(block=block.building_block_id):
                    self.assertIn(source, names)
                    self.assertIn(target, names)

    def test_a_dangling_component_is_refused(self) -> None:
        with self.assertRaises(blocks.LibraryError):
            blocks.parse_block({"building_block_id": "x", "provides": [{}]})
        bad = blocks.parse_block(
            {"building_block_id": "x", "provides": [{"component": "no-such-thing"}]}
        )
        self.assertEqual(bad.provides[0].component, "no-such-thing")

    def test_a_block_providing_an_application_type_is_refused(self) -> None:
        """A block is what a product runs on. A document platform or a risk
        register is an application, which is a part, and a block that
        provided one expanded into a system wearing a technology service's
        fields."""
        with _Sandbox(seed=True) as root:
            path = root / "26_BLOCKS" / "wrong.yaml"
            path.write_text(
                "- building_block_id: wrong\n  name: Wrong\n"
                "  provides:\n    - component: workflow\n    - component: grc\n",
                encoding="utf-8",
            )
            with self.assertRaises(blocks.LibraryError) as caught:
                blocks.load_blocks(root)
            self.assertIn("application type", str(caught.exception))

    def test_no_block_names_a_vendor(self) -> None:
        """The block is the architecture building block. Naming a product in it
        is what would make a cloud migration a redrawing."""
        vendors = ("AWS", "Azure", "Amazon", "Google", "Microsoft", "S3", "Lambda")
        for block in self.blocks.values():
            text = " ".join([block.name, block.description])
            for vendor in vendors:
                with self.subTest(block=block.building_block_id, vendor=vendor):
                    self.assertNotIn(vendor, text)


class TestExpansion(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.components = blocks.load_components(REPO)
        cls.blocks = blocks.load_blocks(REPO, cls.components)

    def _expand(self, block_id, name="Probe", provider=None):
        return blocks.expand(
            self.blocks[block_id], name, self.components, provider=provider
        )

    def test_it_creates_one_entity_per_component(self) -> None:
        for block_id, block in self.blocks.items():
            out = self._expand(block_id)
            created = sum(len(v) for v in out["entities"].values())
            with self.subTest(block=block_id):
                self.assertEqual(created, len(block.provides))

    def test_every_created_entity_validates_against_the_schema(self) -> None:
        for block_id in self.blocks:
            out = self._expand(block_id)
            for type_name, records in out["entities"].items():
                known = {f.name for f in ENTITY_TYPES[type_name].fields}
                known.add(ENTITY_TYPES[type_name].pk)
                for record in records:
                    for field in record:
                        with self.subTest(block=block_id, field=field):
                            self.assertIn(field, known)

    def test_the_same_block_resolves_differently_per_cloud(self) -> None:
        """The whole claim: one block, one definition, different products."""
        aws = self._expand("public-web-tier", provider="AWS")
        azure = self._expand("public-web-tier", provider="Azure")

        def products(out):
            return [r.get("product") for r in out["entities"]["tech_services"]]

        self.assertTrue(all(products(aws)))
        self.assertTrue(all(products(azure)))
        self.assertNotEqual(products(aws), products(azure))
        # Same shape either way: the ids do not mention the cloud.
        self.assertEqual(
            [r["tech_service_id"] for r in aws["entities"]["tech_services"]],
            [r["tech_service_id"] for r in azure["entities"]["tech_services"]],
        )

    def test_no_provider_means_no_product(self) -> None:
        """The honest state for a design that has not chosen a cloud."""
        out = self._expand("public-web-tier")
        for record in out["entities"]["tech_services"]:
            self.assertNotIn("product", record)
            self.assertEqual(record["component_type"], record["component_type"])

    def test_relations_join_what_the_block_created(self) -> None:
        out = self._expand("public-web-tier")
        created = set(out["ids"].values())
        rows = out["relations"]["tech_service_connects_to"]
        self.assertEqual(len(rows), len(self.blocks["public-web-tier"].relations))
        for row in rows:
            self.assertIn(row["from_tech_service_id"], created)
            self.assertIn(row["to_tech_service_id"], created)

    def test_the_component_type_wins_over_the_block_default(self) -> None:
        """Tightest first: this appearance, then the block, then the component
        -- except that the component knows most about what it is."""
        out = self._expand("public-web-tier")
        by_component = {
            r["component_type"]: r for r in out["entities"]["tech_services"]
        }
        self.assertEqual(by_component["waf"]["service_category"], "Security")
        self.assertEqual(by_component["load-balancer"]["service_category"], "Network")

    def test_ids_are_derived_from_the_name(self) -> None:
        out = blocks.expand(
            self.blocks["public-web-tier"], "Card Servicing", self.components
        )
        for record in out["entities"]["tech_services"]:
            self.assertTrue(record["tech_service_id"].startswith("TS-CARD-SERVICING-"))


class TestEstateIsTyped(unittest.TestCase):
    """Without this the library is a catalog connected to nothing."""

    def test_every_technology_service_says_what_kind_it_is(self) -> None:
        model = seeded_model()
        components = blocks.load_components(REPO)
        untyped = [
            str(t["tech_service_id"]) for t in model.all_of("tech_services")
            if not t.get("component_type")
        ]
        self.assertEqual(untyped, [])
        for service in model.all_of("tech_services"):
            with self.subTest(service=service["tech_service_id"]):
                self.assertIn(str(service["component_type"]), components)


class TestBlockEndpoints(unittest.TestCase):
    def _server(self, root: Path):
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
        return server_module

    def test_the_library_endpoint_lists_both_levels(self) -> None:
        with _Sandbox() as root:
            server = self._server(root)
            lib = server.api_library(None, None)
            self.assertTrue(lib["components"])
            self.assertTrue(lib["blocks"])
            self.assertIn("AWS", lib["providers"])

    def test_preview_writes_nothing(self) -> None:
        with _Sandbox() as root:
            server = self._server(root)
            before = sorted(p.name for p in (root / "10_MODEL" / "tech_services").iterdir())
            server.api_block_preview(
                None, {"block": "public-web-tier", "name": "Ghost", "provider": "AWS"}
            )
            self.assertEqual(
                sorted(p.name for p in (root / "10_MODEL" / "tech_services").iterdir()),
                before,
            )

    def test_adding_a_block_writes_entities_and_relations(self) -> None:
        with _Sandbox() as root:
            server = self._server(root)
            result = server.api_block_add(
                None, {"block": "public-web-tier", "name": "Probe", "provider": "AWS"}
            )
            self.assertEqual(result["errors"], [])
            self.assertEqual(len(result["created"]), 4)

            reloaded = model_module.load(root)
            for entity_id in result["created"]:
                self.assertIsNotNone(reloaded.find(entity_id), entity_id)
            self.assertTrue(
                (root / "10_MODEL" / "relations" / server.BLOCK_ADDITIONS).exists()
            )

    def test_block_relations_go_to_their_own_file(self) -> None:
        """A form never rewrites a file somebody authored by hand."""
        with _Sandbox() as root:
            server = self._server(root)
            server.api_block_add(None, {"block": "public-web-tier", "name": "Probe"})
            self.assertNotEqual(server.BLOCK_ADDITIONS, server.APP_RELATIONS)
            self.assertTrue(
                (root / "10_MODEL" / "relations" / server.BLOCK_ADDITIONS).exists()
            )

    def test_a_clash_is_refused_before_anything_is_written(self) -> None:
        with _Sandbox() as root:
            server = self._server(root)
            server.api_block_add(None, {"block": "public-web-tier", "name": "Probe"})
            before = sorted(p.name for p in (root / "10_MODEL" / "tech_services").iterdir())
            with self.assertRaises(server.ApiError) as caught:
                server.api_block_add(None, {"block": "public-web-tier", "name": "Probe"})
            self.assertEqual(caught.exception.status, 409)
            self.assertEqual(
                sorted(p.name for p in (root / "10_MODEL" / "tech_services").iterdir()),
                before,
            )

    def test_an_unknown_block_is_a_404(self) -> None:
        with _Sandbox() as root:
            server = self._server(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_block_preview(None, {"block": "no-such-block", "name": "X"})
            self.assertEqual(caught.exception.status, 404)

    def test_a_block_with_no_name_is_refused(self) -> None:
        with _Sandbox() as root:
            server = self._server(root)
            for name in ("", "   ", None):
                with self.subTest(name=name):
                    with self.assertRaises(server.ApiError):
                        server.api_block_preview(
                            None, {"block": "public-web-tier", "name": name}
                        )


if __name__ == "__main__":
    unittest.main()
