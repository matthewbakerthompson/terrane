"""Every shape and every kit has a picture, and the catalog shows it.

A shape is made from a sample instance and a kit is assembled on each
landing zone, over a scratch copy of the model that the model never sees,
and drawn by the product architecture view the way a real product is. The
tests hold the things a picture of a preset must get right without eyes: one
for every shape, one per landing zone for every kit, the sample's own parts
in it and nothing of the real estate's under its name, the model untouched,
the same bytes twice, the catalog pages pointing at them, and a reason in
the page where a picture could not be made.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.archetype import landing_providers  # noqa: E402
from terrane.blocks import load_blocks, load_components  # noqa: E402
from terrane.icons import IconMap, web_dir  # noqa: E402
from terrane.modules import load_modules  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.pictures import (Pictures, _reason, render_pictures, requires_of, sample_assembly,  # noqa: E402
                          sample_instance, sample_part)
from terrane.render_library import render_modules, render_shapes  # noqa: E402

from _fixture import REPO, seeded_model, seeded_root, seeded_views, setup_shared, teardown_shared  # noqa: E402


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestPictures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = seeded_root()
        cls.model = seeded_model()
        cls.views = seeded_views()
        cls.components = load_components(cls.root)
        cls.blocks = load_blocks(cls.root, cls.components)
        cls.modules = load_modules(cls.root)
        cls.shapes = list(cls.model.archetypes.values())
        cls.palette = Palette(cls.model.config.get("palette"))
        web = web_dir(cls.root)
        cls.icons = IconMap(web if web else REPO / "80_APP" / "web")
        cls.out = Path(tempfile.mkdtemp(prefix="aac-pictures-"))
        cls.before = {t: set(v) for t, v in cls.model.entities.items()}
        cls.pictures = render_pictures(cls.model, cls.views, cls.shapes, cls.modules, cls.palette, cls.icons,
                                       cls.components, cls.blocks, cls.out, "Test", cls.root)

    def test_every_shape_and_every_kit_is_pictured(self) -> None:
        self.assertEqual(set(self.pictures.shapes), {a.archetype_id for a in self.shapes})
        kits = {m.module_id for m in self.modules.values() if m.is_kit}
        self.assertEqual(set(self.pictures.kits), kits)
        providers = landing_providers(self.shapes)
        for kit_id, drawn in self.pictures.kits.items():
            self.assertEqual(list(drawn), providers, kit_id)
        # Every part that is not a kit has one picture, on the first landing
        # zone, or a note saying the product view found nothing to draw (a
        # part that makes only a network, or only relations); never both,
        # and never any other reason.
        parts = {m.module_id for m in self.modules.values() if not m.is_kit}
        noted = {k.split("|", 1)[0] for k in self.pictures.notes}
        self.assertEqual(set(self.pictures.parts) | noted, parts)
        self.assertEqual(set(self.pictures.parts) & noted, set())
        for key, reason in self.pictures.notes.items():
            self.assertTrue(reason.endswith("selected no entities"), (key, reason))
        self.assertEqual(len(self.pictures.written),
                         len(self.shapes) + len(kits) * len(providers) + len(self.pictures.parts) + len(self.blocks) + 2)

    def test_a_part_is_pictured_with_what_it_requires(self) -> None:
        """The mobile channel requires the product API: its picture holds
        the channel's own system and the API it calls, both the sample's."""
        part = self.modules["mobile-channel"]
        self.assertIn("api-service", part.requires)
        text = (self.out / "part--mobile-channel.svg").read_text(encoding="utf-8")
        root = ET.fromstring(text)
        systems = {el.get("data-id") for el in root.iter()
                   if el.get("class") == "node" and el.get("data-type") == "systems"}
        self.assertIn("SYS-SAMPLE-MOBILE", systems)
        self.assertIn("SYS-SAMPLE-API", systems)
        self.assertIn("with what it requires", text)

    def test_the_picture_is_of_the_sample(self) -> None:
        """The systems drawn are the sample's own, named from its placeholder
        slug, plus the shared systems of the estate its parts reach (the
        audit destination, the ingestion hub): neighbors, as on any
        product's picture, never another product's parts."""
        estate_systems = set(self.model.entities["systems"])
        for archetype in self.shapes:
            with self.subTest(shape=archetype.archetype_id):
                text = (self.out / ("shape--%s.svg" % archetype.archetype_id)).read_text(encoding="utf-8")
                root = ET.fromstring(text)
                systems = {el.get("data-id") for el in root.iter()
                           if el.get("class") == "node" and el.get("data-type") == "systems"}
                own = {s for s in systems if s.startswith("SYS-SAMPLE")}
                self.assertTrue(own, "no sample systems drawn: %s" % sorted(systems))
                self.assertEqual(systems - own - estate_systems, set())
                self.assertIn("as the shape makes it", text)

    def test_the_model_is_untouched(self) -> None:
        after = {t: set(v) for t, v in self.model.entities.items()}
        self.assertEqual(after, self.before)
        self.assertFalse(any(k.startswith("SAMPLE-") for k in self.model.entities["products"]))

    def test_same_bytes_twice(self) -> None:
        again = Path(tempfile.mkdtemp(prefix="aac-pictures-"))
        render_pictures(self.model, self.views, self.shapes, self.modules, self.palette, self.icons,
                        self.components, self.blocks, again, "Test", self.root)
        for path in self.pictures.written:
            self.assertEqual(path.read_bytes(), (again / path.name).read_bytes(), path.name)

    def test_a_stale_picture_goes(self) -> None:
        stale = self.out / "shape--gone.svg"
        stale.write_text("<svg/>", encoding="utf-8")
        render_pictures(self.model, self.views, self.shapes, self.modules, self.palette, self.icons,
                        self.components, self.blocks, self.out, "Test", self.root)
        self.assertFalse(stale.exists())

    def test_every_block_is_pictured_and_the_library_mapped(self) -> None:
        self.assertEqual(set(self.pictures.blocks), set(self.blocks))
        for block_id, path in self.pictures.blocks.items():
            text = (self.out / Path(path).name).read_text(encoding="utf-8")
            root = ET.fromstring(text)
            nodes = {el.get("data-id") for el in root.iter() if el.get("class") == "node"}
            self.assertEqual(nodes, {p.component for p in self.blocks[block_id].provides}, block_id)
            edges = [el for el in root.iter() if el.get("class") == "edge"]
            self.assertEqual(len(edges), len(self.blocks[block_id].relations), block_id)
        self.assertEqual(set(self.pictures.maps), {"kits", "parts"})
        kits = ET.fromstring((self.out / "kits-map.svg").read_text(encoding="utf-8"))
        kit_nodes = {el.get("data-id") for el in kits.iter() if el.get("class") == "node"
                     and el.get("data-type") == "products"}
        self.assertEqual(kit_nodes, {"kit::" + m.module_id for m in self.modules.values() if m.is_kit})
        parts = ET.fromstring((self.out / "parts-map.svg").read_text(encoding="utf-8"))
        part_nodes = {el.get("data-id") for el in parts.iter() if el.get("class") == "node"
                      and el.get("data-type") == "systems"}
        self.assertEqual(part_nodes, {"part::" + m.module_id for m in self.modules.values() if not m.is_kit})
        from terrane.render_library import render_blocks
        blocks_md = render_blocks(self.blocks, self.components, None, self.pictures)
        for block_id in self.blocks:
            self.assertIn("](svg/block--%s.svg)" % block_id, blocks_md)
        modules_md = render_modules(self.modules, self.shapes, self.model, None, self.pictures)
        self.assertIn("](svg/kits-map.svg)", modules_md)
        self.assertIn("](svg/parts-map.svg)", modules_md)

    def test_the_catalog_points_at_the_pictures(self) -> None:
        shapes_md = render_shapes(self.shapes, self.modules, self.model, self.pictures)
        for archetype in self.shapes:
            self.assertIn("](svg/shape--%s.svg)" % archetype.archetype_id, shapes_md)
        modules_md = render_modules(self.modules, self.shapes, self.model, None, self.pictures)
        for kit_id, drawn in self.pictures.kits.items():
            for path in drawn.values():
                self.assertIn("](%s)" % path, modules_md)
        for part_id, path in self.pictures.parts.items():
            self.assertIn("](%s)" % path, modules_md)
        self.assertIn("Mobile channel, with what it requires", modules_md)
        # Without pictures the pages read as before.
        self.assertNotIn("](svg/", render_shapes(self.shapes, self.modules, self.model))

    def test_a_kit_that_cannot_be_made_says_why(self) -> None:
        """A kit or a shape that cannot be made gets the reason on its page,
        trimmed of the sample's own name, not a picture of something else."""
        kit = next(m for m in self.modules.values() if m.is_kit)
        shape = self.shapes[0]
        notes = {
            "%s|AWS" % kit.module_id: _reason(
                "SAMPLE-KIT-X-AWS: archetype compose:SAMPLE-KIT-X-AWS requires parameter 'partner'.",
                "SAMPLE-KIT-X-AWS"),
            shape.archetype_id: _reason("SAMPLE-X: no landing zone answers for kind queue.", "SAMPLE-X"),
        }
        self.assertEqual(notes["%s|AWS" % kit.module_id], "requires parameter 'partner'")
        pictures = Pictures({}, {}, notes, [])
        page = render_modules(self.modules, self.shapes, self.model, None, pictures)
        self.assertIn("**No picture on** AWS: requires parameter 'partner'.", page)
        self.assertNotIn("](svg/kit--%s" % kit.module_id, page)
        shapes_page = render_shapes(self.shapes, self.modules, self.model, pictures)
        self.assertIn("**No picture.** no landing zone answers for kind queue.", shapes_page)


class TestSamples(unittest.TestCase):
    def test_sample_instance_names_its_placeholders(self) -> None:
        model = seeded_model()
        archetype = next(iter(model.archetypes.values()))
        instance = sample_instance(archetype)
        self.assertTrue(instance["product_id"].startswith("SAMPLE-"))
        for parameter in archetype.parameters:
            if parameter.required and parameter.default is None:
                self.assertEqual(instance["parameters"][parameter.name], "sample-" + parameter.name)

    def test_sample_assembly_answers_what_the_parts_require(self) -> None:
        model = seeded_model()
        modules = load_modules(seeded_root())
        for kit in (m for m in modules.values() if m.is_kit):
            record = sample_assembly(kit, "AWS", model, modules)
            self.assertEqual(record["compose"], {"modules": [{"module": kit.module_id}], "provider": "AWS"})
            for member_id in kit.modules and [e["module"] for e in kit.modules] or []:
                for parameter in modules[member_id].parameters:
                    if parameter.required and parameter.default is None and not parameter.component:
                        self.assertIn(parameter.name, record["parameters"], (kit.module_id, parameter.name))

    def test_sample_part_composes_what_it_requires_first(self) -> None:
        model = seeded_model()
        modules = load_modules(seeded_root())
        part = modules["mobile-channel"]
        self.assertEqual(requires_of(part, modules), ["api-service", "mobile-channel"])
        record = sample_part(part, "AWS", model, modules)
        self.assertEqual(record["compose"], {"modules": [{"module": "api-service"}, {"module": "mobile-channel"}],
                                             "provider": "AWS"})
        self.assertEqual(record["product_id"], "SAMPLE-PART-MOBILE-CHANNEL-AWS")
        # A part that requires nothing is composed alone; a requirement's own
        # requirements come before it.
        alone = next(m for m in modules.values() if not m.is_kit and not m.requires)
        self.assertEqual(requires_of(alone, modules), [alone.module_id])


if __name__ == "__main__":
    unittest.main()
