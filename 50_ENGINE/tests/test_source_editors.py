"""Tests for the archetype editor and raw entity-file editing.

Both are write paths that can take the whole model down: saving an archetype
re-expands every instance of it, and saving an entity file replaces a file the
loader reads. Everything here is a guard against that, or a check that the
guard says something useful when it fires.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import importer, model as model_module  # noqa: E402
from terrane.schema import ENTITY_TYPES  # noqa: E402

from _fixture import (  # noqa: E402
    EXAMPLE_CSV,
    REPO,
    Sandbox as _Sandbox,
    seeded_root,
    setup_shared,
    teardown_shared,
)


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _server(root: Path):
    sys.path.insert(0, str(root / "50_ENGINE"))
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


def _seeded(root: Path):
    importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
    return _server(root)


#: The CSV export drops `archetype` and `parameters` on purpose -- they are
#: derived, and re-importing them would double the generated entities. So a
#: seeded sandbox contains no instances, and anything that needs one makes it
#: through the endpoint a person would use.
def _instantiate(server, archetype_id: str = "aws-product-onboarding") -> str:
    entity_id = "PRD-PROBE"
    server.api_instantiate(
        None,
        {
            "archetype": archetype_id,
            "id": entity_id,
            "values": {"name": "Probe Product", "status": "Planned",
                       "owner_org_id": "ORG-PRODUCT"},
            "parameters": {
                "slug": "probe",
                "product_name": "Probe",
                "owner_org": "ORG-PRODUCT",
                "domain": "Lending",
                "account": "prod-probe",
            },
        },
    )
    return entity_id


class TestArchetypeEditor(unittest.TestCase):
    def _starter(self, server, archetype_id: str) -> str:
        return (
            server.api_archetype({}, None)["text"]
            .replace("my-archetype", archetype_id)
            .replace("My Archetype", archetype_id.title())
        )

    def test_reading_an_archetype_returns_its_file_verbatim(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            payload = server.api_archetype({"id": ["aws-product-onboarding"]}, None)
            self.assertEqual(
                payload["text"], (root / payload["path"]).read_text(encoding="utf-8-sig")
            )
            self.assertFalse(payload["isNew"])

    def test_instances_are_the_records_that_ask_not_the_ones_produced(self) -> None:
        """Generated entities carry the archetype name too, so a naive filter
        answers "every box this made" when the question was "who asked"."""
        with _Sandbox() as root:
            server = _seeded(root)
            created = _instantiate(server)
            instances = server.api_archetype({"id": ["aws-product-onboarding"]}, None)["instances"]
            self.assertEqual(instances, [created])
            model = model_module.load(root)
            for entity_id in instances:
                located = model.find(entity_id)
                self.assertIsNotNone(located, entity_id)
                self.assertIsNone(located[1].get("archetype_instance"), entity_id)

    def test_the_starter_expands_on_the_first_preview(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            payload = server.api_archetype({}, None)
            self.assertTrue(payload["isNew"])
            preview = server.api_archetype_preview(None, {"text": payload["text"]})
            self.assertGreater(preview["counts"]["entities"], 0)
            self.assertGreater(preview["counts"]["relations"], 0)

    def test_preview_names_every_entity_the_shape_produces(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            text = server.api_archetype({"id": ["aws-product-onboarding"]}, None)["text"]
            preview = server.api_archetype_preview(None, {"text": text})
            self.assertEqual(len(preview["produces"]), preview["counts"]["entities"])
            for produced in preview["produces"]:
                self.assertIn(produced["type"], ENTITY_TYPES)
                self.assertTrue(produced["id"])

    def test_preview_writes_nothing(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            before = sorted(p.name for p in (root / "20_ARCHETYPES").iterdir())
            server.api_archetype_preview(None, {"text": self._starter(server, "ghost")})
            self.assertEqual(
                sorted(p.name for p in (root / "20_ARCHETYPES").iterdir()), before
            )

    def test_malformed_text_is_refused(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            for bad, status in (
                ("::: not yaml", 422),
                ("- a list", 422),
                ("title: no id here", 422),
                ("archetype_id: x\napplies_to: unicorns\n", 422),
            ):
                with self.subTest(text=bad):
                    with self.assertRaises(server.ApiError) as caught:
                        server.api_archetype_preview(None, {"text": bad})
                    self.assertEqual(caught.exception.status, status)

    def test_saving_a_new_archetype_makes_it_instantiable(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            result = server.api_archetype_save(None, {"text": self._starter(server, "probe")})
            self.assertTrue(result["created"])
            self.assertEqual(result["instances"], [])

            model = model_module.load(root)
            self.assertIn("probe", model.archetypes)

    def test_editing_a_shape_regenerates_its_instances(self) -> None:
        """The whole point of an archetype: change the shape, not each copy."""
        with _Sandbox() as root:
            server = _seeded(root)
            _instantiate(server)
            text = server.api_archetype({"id": ["aws-product-onboarding"]}, None)["text"]
            before = len(model_module.load(root).all_of("systems"))

            # Required fields the archetype's own defaults do not supply have
            # to be here, or the save reports the errors -- which it should.
            # A version 3 shape is composed from modules and provides nothing
            # of its own, so the probe goes in as a `provides` block ahead of
            # the modules.
            anchor = "modules:\n  - module: api-service"
            self.assertEqual(text.count(anchor), 1)
            widened = text.replace(
                anchor,
                "provides:\n"
                "  systems:\n"
                '    - system_id: "SYS-{slug|upper}-PROBE"\n'
                '      name: "{product_name} Probe"\n'
                "      status: Planned\n"
                '      owner_org_id: "{owner_org}"\n'
                "      criticality: Low\n\n"
                + anchor,
                1,
            )
            result = server.api_archetype_save(
                None, {"id": "aws-product-onboarding", "text": widened}
            )
            self.assertFalse(result["created"])
            self.assertTrue(result["instances"])
            self.assertEqual(result["errors"], [])

            after = model_module.load(root).all_of("systems")
            self.assertEqual(len(after), before + 1)
            self.assertTrue(any(s["system_id"].endswith("-PROBE") for s in after))

    def test_an_edit_that_would_break_the_load_is_rolled_back(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            _instantiate(server)
            path = root / "20_ARCHETYPES" / "aws-product-onboarding.yaml"
            original = path.read_text(encoding="utf-8-sig")
            # Two entities claiming one id: parses, expands, refuses to load.
            # The API comes from the `api-service` module; a second one
            # provided by the shape itself claims the same id.
            anchor = "modules:\n  - module: api-service"
            self.assertEqual(original.count(anchor), 1)
            broken = original.replace(
                anchor,
                "provides:\n"
                "  systems:\n"
                '    - system_id: "SYS-{slug|upper}-API"\n'
                '      name: "A second thing with the first thing\'s id"\n'
                "      status: Planned\n\n"
                + anchor,
                1,
            )
            with self.assertRaises(server.ApiError) as caught:
                server.api_archetype_save(
                    None, {"id": "aws-product-onboarding", "text": broken}
                )
            self.assertEqual(caught.exception.status, 409)
            self.assertEqual(path.read_text(encoding="utf-8-sig"), original)

    def test_a_duplicate_id_is_refused(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_archetype_save(
                    None, {"text": self._starter(server, "aws-product-onboarding")}
                )
            self.assertEqual(caught.exception.status, 409)

    def test_renaming_in_place_is_refused(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            text = server.api_archetype({"id": ["saas-onboarding"]}, None)["text"]
            with self.assertRaises(server.ApiError) as caught:
                server.api_archetype_save(
                    None,
                    {"id": "saas-onboarding",
                     "text": text.replace("archetype_id: saas-onboarding",
                                          "archetype_id: saas-onboarding-two")},
                )
            self.assertEqual(caught.exception.status, 409)

    def test_deleting_an_archetype_in_use_is_refused(self) -> None:
        """Removing it would silently delete every entity it generates."""
        with _Sandbox() as root:
            server = _seeded(root)
            _instantiate(server)
            with self.assertRaises(server.ApiError) as caught:
                server.api_archetype_delete(None, {"id": "aws-product-onboarding"})
            self.assertEqual(caught.exception.status, 409)
            self.assertIn("PRD-", str(caught.exception))
            self.assertTrue((root / "20_ARCHETYPES" / "aws-product-onboarding.yaml").exists())

    def test_an_unused_archetype_can_be_deleted(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            server.api_archetype_save(None, {"text": self._starter(server, "probe")})
            server.api_archetype_delete(None, {"id": "probe"})
            self.assertFalse((root / "20_ARCHETYPES" / "probe.yaml").exists())
            self.assertNotIn("probe", model_module.load(root).archetypes)

    def test_deleting_an_unknown_archetype_is_a_404(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_archetype_delete(None, {"id": "no-such-shape"})
            self.assertEqual(caught.exception.status, 404)


class TestEntitySourceEditor(unittest.TestCase):
    def test_the_file_comes_back_verbatim(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            payload = server.api_entity_source({"id": ["SYS-AUTH-SWITCH"]}, None)
            self.assertTrue(payload["editable"])
            self.assertIsNone(payload["why"])
            self.assertEqual(
                payload["text"], (root / payload["path"]).read_text(encoding="utf-8-sig")
            )

    def test_a_comment_survives_a_round_trip(self) -> None:
        """The reason a field is what it is often lives in a comment, and a
        form cannot carry one. That is most of why this editor exists."""
        with _Sandbox() as root:
            server = _seeded(root)
            before = server.api_entity_source({"id": ["SYS-AUTH-SWITCH"]}, None)["text"]
            note = "# scheme timeout, not our choice\n"
            server.api_entity_source_save(
                None, {"id": "SYS-AUTH-SWITCH", "text": note + before}
            )
            after = server.api_entity_source({"id": ["SYS-AUTH-SWITCH"]}, None)["text"]
            self.assertTrue(after.startswith(note))

    def test_a_generated_entity_is_read_only_and_says_why(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            _instantiate(server)
            model = model_module.load(root)
            generated = next(
                str(s["system_id"]) for s in model.all_of("systems")
                if s.get("archetype_instance")
            )
            payload = server.api_entity_source({"id": [generated]}, None)
            self.assertFalse(payload["editable"])
            self.assertIn("generated", payload["why"])
            with self.assertRaises(server.ApiError) as caught:
                server.api_entity_source_save(None, {"id": generated, "text": "x: 1"})
            self.assertEqual(caught.exception.status, 409)

    def test_a_file_holding_several_records_is_read_only(self) -> None:
        """Regression in spirit: rewriting a shared file from one entity's
        editor is how the other records in it get lost."""
        with _Sandbox() as root:
            server = _seeded(root)
            shared = str(model_module.load(root).all_of("org_units")[0]["org_unit_id"])
            payload = server.api_entity_source({"id": [shared]}, None)
            self.assertFalse(payload["editable"])
            self.assertIn("several records", payload["why"])
            path = root / payload["path"]
            original = path.read_text(encoding="utf-8-sig")
            with self.assertRaises(server.ApiError):
                server.api_entity_source_save(
                    None, {"id": shared, "text": "org_unit_id: " + shared + "\n"}
                )
            self.assertEqual(path.read_text(encoding="utf-8-sig"), original)

    def test_changing_the_primary_key_is_refused(self) -> None:
        """A rename would leave every reference to it dangling."""
        with _Sandbox() as root:
            server = _seeded(root)
            text = server.api_entity_source({"id": ["SYS-AUTH-SWITCH"]}, None)["text"]
            with self.assertRaises(server.ApiError) as caught:
                server.api_entity_source_save(
                    None,
                    {"id": "SYS-AUTH-SWITCH",
                     "text": text.replace("SYS-AUTH-SWITCH", "SYS-RENAMED")},
                )
            self.assertEqual(caught.exception.status, 409)

    def test_malformed_text_never_reaches_the_disk(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            payload = server.api_entity_source({"id": ["SYS-AUTH-SWITCH"]}, None)
            path = root / payload["path"]
            for bad in ("not: valid: yaml:", "- a list"):
                with self.subTest(text=bad):
                    with self.assertRaises(server.ApiError) as caught:
                        server.api_entity_source_save(
                            None, {"id": "SYS-AUTH-SWITCH", "text": bad}
                        )
                    self.assertEqual(caught.exception.status, 422)
            self.assertEqual(path.read_text(encoding="utf-8-sig"), payload["text"])

    def test_a_bad_reference_is_saved_and_reported_not_refused(self) -> None:
        """A dangling reference is a validation finding, not a load failure.
        Refusing the save would lose the edit; saying nothing would hide it."""
        with _Sandbox() as root:
            server = _seeded(root)
            payload = server.api_entity_source({"id": ["SYS-AUTH-SWITCH"]}, None)
            self.assertIn("owner_org_id:", payload["text"])
            broken = re.sub(
                r"owner_org_id: \S+", "owner_org_id: ORG-DOES-NOT-EXIST", payload["text"]
            )
            result = server.api_entity_source_save(
                None, {"id": "SYS-AUTH-SWITCH", "text": broken}
            )
            self.assertTrue(result["errors"])
            server.api_entity_source_save(
                None, {"id": "SYS-AUTH-SWITCH", "text": payload["text"]}
            )
            self.assertEqual(
                server.api_entity_source({"id": ["SYS-AUTH-SWITCH"]}, None)["text"],
                payload["text"],
            )

    def test_an_id_collision_is_rolled_back(self) -> None:
        """The file parses, the model refuses it, so the file goes back."""
        with _Sandbox() as root:
            server = _seeded(root)
            payload = server.api_entity_source({"id": ["SYS-AUTH-SWITCH"]}, None)
            path = root / payload["path"]
            other = str(model_module.load(root).all_of("capabilities")[0]["capability_id"])
            # An id already used by a different entity type: ids are global.
            clash = payload["text"] + ("\ncmdb_ci_sys_id: %s\n" % other)
            clash = clash.replace("system_id: SYS-AUTH-SWITCH", "system_id: " + other)
            with self.assertRaises(server.ApiError):
                server.api_entity_source_save(None, {"id": "SYS-AUTH-SWITCH", "text": clash})
            self.assertEqual(path.read_text(encoding="utf-8-sig"), payload["text"])

    def test_an_unknown_entity_is_a_404(self) -> None:
        with _Sandbox() as root:
            server = _seeded(root)
            with self.assertRaises(server.ApiError) as caught:
                server.api_entity_source({"id": ["SYS-NOPE"]}, None)
            self.assertEqual(caught.exception.status, 404)

    def test_every_entity_in_the_model_can_be_read(self) -> None:
        """Read-only is fine; a 500 or a stack trace is not."""
        server = _server(seeded_root())
        model = model_module.load(seeded_root())
        for type_name, entity_type in ENTITY_TYPES.items():
            for record in model.all_of(type_name)[:3]:
                entity_id = str(record[entity_type.pk])
                with self.subTest(id=entity_id):
                    payload = server.api_entity_source({"id": [entity_id]}, None)
                    self.assertTrue(payload["text"])
                    if not payload["editable"]:
                        self.assertTrue(payload["why"], entity_id)


if __name__ == "__main__":
    unittest.main()
