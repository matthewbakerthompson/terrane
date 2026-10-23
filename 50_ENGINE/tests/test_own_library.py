"""A library of the organization's own, beside the shipped one.

`library_paths` in `10_MODEL/model.yaml` names folders holding the same layer
folders as the shipped library, read after it. A record there stands in for a
shipped one only when it says `replaces:` with its own id; any other id
already taken is an error naming both files. These tests write a small
library of a made-up organization's into a sandbox -- a component type, a
block and a pattern of its own, a connection kind and a part, and its own
version of the API front door -- and hold every loader, the gate, the
catalog and the app to it.
"""

from __future__ import annotations

import json
import sys
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli, validate  # noqa: E402
from terrane.archetype import ArchetypeError, load_archetypes  # noqa: E402
from terrane.blocks import load_blocks, load_components, load_patterns  # noqa: E402
from terrane.build_types import load_build_types  # noqa: E402
from terrane.connections import load_connections  # noqa: E402
from terrane.library import LibraryError, library_roots, own_root, summary  # noqa: E402
from terrane.loader import load_folder  # noqa: E402
from terrane.model import load  # noqa: E402
from terrane.modules import load_modules  # noqa: E402
from terrane.query import load_views  # noqa: E402
from terrane.render_library import render_blocks, render_connections, render_modules, render_patterns  # noqa: E402

from _fixture import REPO, Sandbox  # noqa: E402

#: The example: what an organization adds in its first week of owning a
#: library, one file per layer.
OURS = {name: textwrap.dedent(text) for name, text in {
    "README.md": """\
        # Our library

        Read after the shipped library, as `library_paths` in
        `10_MODEL/model.yaml` names it.
        """,
    "25_COMPONENTS/integration.yaml": """\
        - component_type_id: mainframe-gateway
          name: Mainframe gateway
          category: Integration
          applies_to: tech_services
          description: >
            The one way into the mainframe's transactions from anything that is not the mainframe.
          providers:
            On-prem: CICS Transaction Gateway
        """,
    "26_BLOCKS/integration.yaml": """\
        - building_block_id: mainframe-entry
          name: Mainframe entry
          category: Integration
          description: >
            A gateway in front of the mainframe gateway, so a caller sees an API and never a transaction code.
          provides:
            - component: api-gateway
            - component: mainframe-gateway
          relations:
            - from: api-gateway
              to: mainframe-gateway
        """,
    "27_PATTERNS/ours.yaml": """\
        - pattern_id: mainframe-through-an-api
          name: The mainframe through an API
          status: Candidate
          category: Integration
          blocks: [mainframe-entry]
          intent: >
            Nothing calls a mainframe transaction directly; it calls an API that does.
          consequences: >
            One more hop on every call, and a team that owns the translation.
          when_not_to_use: >
            A batch that already reads the mainframe's own extracts.

        - pattern_id: api-front-door
          replaces: api-front-door
          name: API front door, partner edition
          status: Approved
          category: Edge
          blocks: [public-api-tier]
          intent: >
            Every programmatic entry point sits behind the gateway, and a partner's
            behind the partner portal as well.
          consequences: >
            Two front doors to keep in step for a partner, which is the point.
          when_not_to_use: >
            Calls inside one workload account.
        """,
    "24_CONNECTIONS/streams.yaml": """\
        - connection_id: socket-stream
          name: A socket stream
          description: >
            A long-lived socket a system pushes events down as they happen.
          integration_style: Event
          protocols: [WebSocket]
          auth_methods: [OAuth2]
          frequency: Realtime
          direction: Outbound
          patterns: [api-front-door]
        """,
    "28_MODULES/integration.yaml": """\
        - module_id: mainframe-link
          name: Mainframe link
          category: Integration
          needs: [product_name, slug]
          description: >
            The product's own API onto the mainframe's transactions.
          provides:
            systems:
              - system_id: "SYS-{slug|upper}-MF-LINK"
                name: "{product_name} mainframe link"
                system_category: Integration
        """,
}.items()}

LOADERS = {
    "20_ARCHETYPES": ("archetype_id", load_archetypes),
    "24_CONNECTIONS": ("connection_id", load_connections),
    "25_COMPONENTS": ("component_type_id", load_components),
    "26_BLOCKS": ("building_block_id", load_blocks),
    "27_PATTERNS": ("pattern_id", load_patterns),
    "28_MODULES": ("module_id", load_modules),
    "29_TYPES": ("build_type_id", load_build_types),
}


def write_library(root: Path, name: str = "our-library", files=None) -> Path:
    base = root / name
    for rel, text in (OURS if files is None else files).items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    base.mkdir(parents=True, exist_ok=True)
    return base


def name_libraries(root: Path, *names: str) -> None:
    config = root / "10_MODEL" / "model.yaml"
    text = config.read_text(encoding="utf-8")
    config.write_text(text + "\nlibrary_paths: [%s]\n" % ", ".join(names), encoding="utf-8")


def first_shipped(root: Path, folder: str):
    """The first record of a shipped layer, as data, and where it lives."""
    path, data = load_folder(root / folder)[0]
    return path, dict(data)


class TheShippedLibraryAlone(unittest.TestCase):
    """With no `library_paths` nothing changes: one root, every record from
    the shipped library and none a replacement."""

    def test_one_root_and_nothing_marked(self) -> None:
        with Sandbox() as root:
            self.assertEqual([r.name for r in library_roots(root)], [""])
            for folder, (_key, loader) in LOADERS.items():
                records = loader(root)
                self.assertTrue(records, folder)
                self.assertEqual({(r.library, r.replaced) for r in records.values()}, {("", "")}, folder)

    def test_the_shapes_loader_takes_the_root(self) -> None:
        """Given the folder, as it was before there were two, it would read
        `20_ARCHETYPES/20_ARCHETYPES` and say there are no shapes."""
        with self.assertRaises(ArchetypeError):
            load_archetypes(REPO / "20_ARCHETYPES")

    def test_a_sandbox_leaves_the_organizations_libraries_out(self) -> None:
        """An adopter's `library_paths` would otherwise name folders no
        sandbox copies, and every test would fail to load its model."""
        with Sandbox() as root:
            name_libraries(root, "our-library")
            config = root / "10_MODEL" / "model.yaml"
            from _fixture import _shipped_library_only
            _shipped_library_only(config)
            self.assertNotIn("library_paths:", config.read_text(encoding="utf-8").replace("# library_paths", ""))
            self.assertEqual([r.name for r in library_roots(root)], [""])


class OurLibraryBesideTheShippedOne(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox()
        cls.root = cls.box.__enter__()
        write_library(cls.root)
        name_libraries(cls.root, "our-library")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def test_its_records_come_after_the_shipped_ones(self) -> None:
        patterns = load_patterns(self.root)
        self.assertEqual(list(patterns)[-1], "mainframe-through-an-api")
        self.assertEqual(patterns["mainframe-through-an-api"].library, "our-library")
        self.assertEqual(patterns["mainframe-through-an-api"].replaced, "")
        self.assertEqual(load_connections(self.root)["socket-stream"].library, "our-library")
        self.assertEqual(load_modules(self.root)["mainframe-link"].library, "our-library")

    def test_a_block_of_its_own_may_be_made_of_a_kind_of_its_own(self) -> None:
        blocks = load_blocks(self.root)
        self.assertEqual(
            [p.component for p in blocks["mainframe-entry"].provides], ["api-gateway", "mainframe-gateway"]
        )
        self.assertEqual(load_components(self.root)["mainframe-gateway"].library, "our-library")

    def test_a_replacement_takes_the_shipped_records_place(self) -> None:
        with Sandbox() as root:
            shipped = load_patterns(root)
        ours = load_patterns(self.root)
        pattern = ours["api-front-door"]
        self.assertEqual(pattern.name, "API front door, partner edition")
        self.assertEqual(pattern.library, "our-library")
        self.assertEqual(pattern.replaced, "27_PATTERNS/edge.yaml")
        # Its place in the order, not the end of the list: a catalog that
        # listed it third lists it third still.
        self.assertEqual(list(ours).index("api-front-door"), list(shipped).index("api-front-door"))
        self.assertEqual(len(ours), len(shipped) + 1)

    def test_the_gate_passes_and_the_model_loads(self) -> None:
        model = load(self.root)
        report = validate.run(model, load_views(self.root / "30_VIEWS"))
        self.assertEqual([f.format() for f in report.errors], [])

    def test_the_app_writes_to_the_first_library_named(self) -> None:
        self.assertEqual(own_root(self.root).name, "our-library")

    def test_the_summary_counts_what_it_adds_and_replaces(self) -> None:
        layers = {"pattern": load_patterns(self.root), "part": load_modules(self.root)}
        self.assertEqual(summary(self.root, layers), [("our-library", {"pattern": (1, 1), "part": (1, 0)})])


class AnInventoryImportedBesideIt(unittest.TestCase):
    """The insurer's export through its mapping (AAC-15), into a model that
    names a library of its own: the import writes the model and nothing of
    the library, and the gate says of it what it says without one."""

    def test_the_import_and_the_gate_are_as_without_one(self) -> None:
        from terrane import importer

        sample = REPO / "60_SOURCES" / "inventory"
        with Sandbox() as root:
            write_library(root)
            name_libraries(root, "our-library")
            ours = {p: p.read_bytes() for p in (root / "our-library").rglob("*") if p.is_file()}
            outcome = importer.import_csv(root, sample, load(root), mapping=sample / "mapping.yaml")
            model = load(root)
            report = validate.run(model, load_views(root / "30_VIEWS"))
            self.assertEqual(len(model.all_of("systems")), 10)
            self.assertEqual({f.code for f in report.errors}, {"view.unresolvable"})
            written = {str(p) for p in outcome.written}
            self.assertEqual([f.format() for f in report.findings if f.where in written], [])
            self.assertTrue(all(Path(p).is_relative_to(root / "10_MODEL") for p in written))
            self.assertEqual({p: p.read_bytes() for p in ours}, ours)
            self.assertEqual(load_patterns(root)["api-front-door"].library, "our-library")


class TheCatalogSaysWhatCameFromWhere(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox()
        cls.root = cls.box.__enter__()
        write_library(cls.root)
        name_libraries(cls.root, "our-library")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def test_patterns(self) -> None:
        components = load_components(self.root)
        blocks = load_blocks(self.root, components)
        text = render_patterns(load_patterns(self.root, blocks), blocks, components)
        self.assertIn("Generated from `27_PATTERNS/` and `our-library/27_PATTERNS/`", text)
        self.assertIn("[API front door, partner edition](#api-front-door) *(our-library)*", text)
        self.assertIn("From `our-library/`, in place of the one in `27_PATTERNS/edge.yaml`.", text)
        self.assertIn("From `our-library/`.", text)

    def test_blocks_and_their_kinds(self) -> None:
        components = load_components(self.root)
        blocks = load_blocks(self.root, components)
        text = render_blocks(blocks, components, load_patterns(self.root, blocks))
        self.assertIn("`our-library/26_BLOCKS/`", text)
        self.assertIn("`our-library/25_COMPONENTS/`", text)
        self.assertIn("| Mainframe gateway (`mainframe-gateway`) *(our-library)* |", text)

    def test_parts_and_connections(self) -> None:
        modules = load_modules(self.root)
        text = render_modules(modules, load_archetypes(self.root).values())
        self.assertIn("Generated from `28_MODULES/` and `our-library/28_MODULES/` by `terrane render`; edit those", text)
        self.assertIn("[Mainframe link](#mainframe-link) *(our-library)*", text)
        kinds = render_connections(load_connections(self.root), load_patterns(self.root))
        self.assertIn("[A socket stream](#socket-stream) *(our-library)*", kinds)

    def test_the_index_says_what_each_library_adds_and_replaces(self) -> None:
        layers = {"pattern": load_patterns(self.root), "part": load_modules(self.root)}
        said = cli._libraries_paragraph(summary(self.root, layers))
        self.assertIn("`our-library/` adds 1 pattern and 1 part, and replaces 1 pattern", said)

    def test_the_shipped_catalog_reads_as_it_did(self) -> None:
        with Sandbox() as root:
            components = load_components(root)
            blocks = load_blocks(root, components)
            text = render_patterns(load_patterns(root, blocks), blocks, components)
        self.assertIn("Generated from `27_PATTERNS/` by `terrane render`", text)
        self.assertNotIn("From `", text)


class NoSilentShadow(unittest.TestCase):
    """Every way a second record of an id can arrive without saying so, and
    every way of saying so wrongly, is refused with both files named."""

    def check(self, files, *expected, names=("our-library",)) -> None:
        with Sandbox() as root:
            write_library(root, files=files)
            name_libraries(root, *names)
            with self.assertRaises(LibraryError) as caught:
                load_patterns(root)
            for fragment in expected:
                self.assertIn(fragment, str(caught.exception))

    def ours(self, edit) -> dict:
        return {"27_PATTERNS/ours.yaml": edit(OURS["27_PATTERNS/ours.yaml"])}

    def test_a_duplicate_without_replaces(self) -> None:
        self.check(
            self.ours(lambda t: t.replace("  replaces: api-front-door\n", "")),
            "duplicate pattern 'api-front-door' in 27_PATTERNS/edge.yaml and our-library/27_PATTERNS/ours.yaml",
            "`replaces: api-front-door`",
        )

    def test_replaces_naming_another_id(self) -> None:
        self.check(
            self.ours(lambda t: t.replace("replaces: api-front-door", "replaces: public-web-entry")),
            "our-library/27_PATTERNS/ours.yaml", "says it replaces 'public-web-entry'",
        )

    def test_replaces_naming_nothing(self) -> None:
        self.check(
            self.ours(lambda t: t.replace(
                "  status: Candidate\n", "  status: Candidate\n  replaces: mainframe-through-an-api\n")),
            "replaces nothing",
        )

    def test_two_of_one_id_in_one_library(self) -> None:
        twice = OURS["27_PATTERNS/ours.yaml"]
        self.check(
            {"27_PATTERNS/ours.yaml": twice, "27_PATTERNS/again.yaml": twice.split("\n\n", 1)[1]},
            "never one beside it",
        )

    def test_replaces_in_the_shipped_library_itself(self) -> None:
        with Sandbox() as root:
            path = root / "27_PATTERNS" / "edge.yaml"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "- pattern_id: api-front-door\n", "- pattern_id: api-front-door\n  replaces: api-front-door\n"),
                encoding="utf-8")
            with self.assertRaises(LibraryError) as caught:
                load_patterns(root)
            self.assertIn("replaces nothing", str(caught.exception))

    def test_every_layer_holds_the_rule(self) -> None:
        """The shapes, connection kinds, component types, blocks, patterns,
        parts and build types, each by its own loader: a copy of a shipped
        record that says `replaces` loads as the organization's; one that does
        not is refused naming both files."""
        for folder, (key, loader) in LOADERS.items():
            with self.subTest(folder), Sandbox() as root:
                shipped_path, data = first_shipped(root, folder)
                record_id = str(data[key])
                ours = root / "our-library" / folder / "copy.json"
                ours.parent.mkdir(parents=True)
                ours.write_text(json.dumps(data), encoding="utf-8")
                name_libraries(root, "our-library")
                with self.assertRaises(ValueError) as caught:
                    loader(root)
                self.assertIn(shipped_path.relative_to(root).as_posix(), str(caught.exception))
                self.assertIn("our-library/%s/copy.json" % folder, str(caught.exception))
                data["replaces"] = record_id
                ours.write_text(json.dumps(data), encoding="utf-8")
                record = loader(root)[record_id]
                self.assertEqual(record.library, "our-library")
                self.assertEqual(record.replaced, shipped_path.relative_to(root).as_posix())


class LibraryPathsSayWhatTheyMean(unittest.TestCase):
    """A `library_paths` that would leave the organization's library unread
    is refused: a typo must not look like an empty library."""

    def refused(self, setup, fragment) -> None:
        with Sandbox() as root:
            setup(root)
            with self.assertRaises(LibraryError) as caught:
                library_roots(root)
            self.assertIn(fragment, str(caught.exception))

    def test_a_folder_that_is_not_there(self) -> None:
        self.refused(lambda root: name_libraries(root, "our-libary"), "not a folder in the repository")

    def test_a_folder_outside_the_repository(self) -> None:
        def setup(root):
            (root.parent / "elsewhere").mkdir()
            name_libraries(root, "../elsewhere")
        self.refused(setup, "outside the repository")

    def test_a_folder_named_twice(self) -> None:
        def setup(root):
            write_library(root)
            name_libraries(root, "our-library", "our-library/")
        self.refused(setup, "twice")

    def test_a_layer_under_the_wrong_name(self) -> None:
        def setup(root):
            write_library(root, files={"patterns/ours.yaml": OURS["27_PATTERNS/ours.yaml"]})
            name_libraries(root, "our-library")
        self.refused(setup, "our-library/patterns is not a layer of the library")

    def test_the_model_will_not_load_on_one(self) -> None:
        with Sandbox() as root:
            name_libraries(root, "our-libary")
            with self.assertRaises(ValueError) as caught:
                load(root)
            self.assertIn("our-libary", str(caught.exception))

    def test_libraries_read_in_the_order_named(self) -> None:
        with Sandbox() as root:
            write_library(root)
            later = OURS["27_PATTERNS/ours.yaml"].replace("partner edition", "group edition")
            write_library(root, "group-library", {"27_PATTERNS/ours.yaml": later.split("\n\n", 1)[1]})
            name_libraries(root, "our-library", "group-library")
            pattern = load_patterns(root)["api-front-door"]
            self.assertEqual(pattern.name, "API front door, group edition")
            self.assertEqual(pattern.library, "group-library")
            self.assertEqual(pattern.replaced, "our-library/27_PATTERNS/ours.yaml")
            self.assertEqual(own_root(root).name, "our-library")


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TheAppKnowsWhichLibrary(unittest.TestCase):
    """The Library says where each card came from, and a part or a shape
    saved from the app goes to the organization's library: never into the
    shipped one while the model keeps its own."""

    def test_the_library_marks_its_cards(self) -> None:
        with Sandbox() as root:
            write_library(root)
            name_libraries(root, "our-library")
            lib = _server(root).api_library(None, None)
            self.assertEqual(lib["libraries"], [{
                "name": "our-library",
                "adds": {"connection kind": 1, "component type": 1, "building block": 1, "pattern": 1, "part": 1},
                "replaces": {"pattern": 1},
            }])
            front = next(p for p in lib["patterns"] if p["id"] == "api-front-door")
            self.assertEqual((front["library"], front["replaced"]), ("our-library", "27_PATTERNS/edge.yaml"))
            self.assertEqual(next(m for m in lib["modules"] if m["id"] == "mainframe-link")["library"], "our-library")
            self.assertEqual(next(k for k in lib["connections"]["kinds"] if k["id"] == "socket-stream")["library"],
                             "our-library")

    def test_a_new_part_goes_to_our_library(self) -> None:
        with Sandbox() as root:
            write_library(root, files={})
            name_libraries(root, "our-library")
            server = _server(root)
            text = OURS["28_MODULES/integration.yaml"]
            saved = server.api_module_save(None, {"text": text})
            self.assertEqual(saved["path"], "our-library/28_MODULES/mainframe-link.yaml")
            self.assertEqual(saved["library"], "our-library")
            self.assertFalse((root / "28_MODULES" / "mainframe-link.yaml").exists())
            self.assertEqual(load_modules(root)["mainframe-link"].library, "our-library")

    def test_a_shipped_part_is_replaced_only_by_saying_so(self) -> None:
        with Sandbox() as root:
            write_library(root, files={})
            name_libraries(root, "our-library")
            server = _server(root)
            shipped = (root / "28_MODULES" / "product-parts.yaml").read_text(encoding="utf-8")
            first = "- module_id: api-service" + shipped.split("- module_id: api-service", 1)[1].split("\n\n- ", 1)[0]
            with self.assertRaises(server.ApiError) as caught:
                server.api_module_save(None, {"text": first})
            self.assertEqual(caught.exception.status, 409)
            self.assertIn("`replaces: api-service`", caught.exception.message)
            self.assertIn("the shipped library", caught.exception.message)
            replaced = first.replace("- module_id: api-service\n", "- module_id: api-service\n  replaces: api-service\n")
            saved = server.api_module_save(None, {"text": replaced})
            self.assertEqual(saved["path"], "our-library/28_MODULES/api-service.yaml")
            self.assertEqual(saved["errors"], [])
            self.assertEqual(load_modules(root)["api-service"].replaced, "28_MODULES/product-parts.yaml")
            self.assertEqual((root / "28_MODULES" / "product-parts.yaml").read_text(encoding="utf-8"), shipped)

    def test_a_shipped_shape_is_edited_into_our_library(self) -> None:
        with Sandbox() as root:
            write_library(root, files={})
            name_libraries(root, "our-library")
            server = _server(root)
            shape = server.api_archetype({"id": ["saas-onboarding"]}, None)
            self.assertEqual(shape["path"], "20_ARCHETYPES/saas-onboarding.yaml")
            before = (root / shape["path"]).read_text(encoding="utf-8")
            with self.assertRaises(server.ApiError) as caught:
                server.api_archetype_save(None, {"id": "saas-onboarding", "text": shape["text"]})
            self.assertIn("`replaces: saas-onboarding`", caught.exception.message)
            text = "replaces: saas-onboarding\n" + shape["text"]
            saved = server.api_archetype_save(None, {"id": "saas-onboarding", "text": text})
            self.assertEqual(saved["path"], "our-library/20_ARCHETYPES/saas-onboarding.yaml")
            self.assertEqual((root / "20_ARCHETYPES" / "saas-onboarding.yaml").read_text(encoding="utf-8"), before)
            # The editor opens the version the model reads now: ours.
            self.assertEqual(server.api_archetype({"id": ["saas-onboarding"]}, None)["path"], saved["path"])
            gone = server.api_archetype_delete(None, {"id": "saas-onboarding"})
            self.assertEqual(gone["restored"], "20_ARCHETYPES/saas-onboarding.yaml")

    def test_a_new_shape_starts_in_our_library(self) -> None:
        with Sandbox() as root:
            write_library(root, files={})
            name_libraries(root, "our-library")
            self.assertEqual(_server(root).api_archetype({}, None)["path"],
                             "our-library/20_ARCHETYPES/my-archetype.yaml")

    def test_without_a_library_of_its_own_saves_go_where_they_went(self) -> None:
        with Sandbox() as root:
            server = _server(root)
            text = OURS["28_MODULES/integration.yaml"]
            self.assertEqual(server.api_module_save(None, {"text": text})["path"], "28_MODULES/mainframe-link.yaml")


if __name__ == "__main__":
    unittest.main()
