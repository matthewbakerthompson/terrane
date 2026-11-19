"""Connection kinds: the ways two systems are connected here.

`24_CONNECTIONS/` is read off the estate's interfaces, so these hold it to the
estate: every kind recognizes what it says it does, no interface is of two
kinds, a kind's pattern is one the library has, and the catalog page and the
connect chooser both say what the files say.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import validate  # noqa: E402
from terrane.blocks import LibraryError, load_patterns  # noqa: E402
from terrane.connections import (  # noqa: E402
    DATASTORE_ENDS, data_stores, fits, kind_of, load_connections, overlaps, parse_connection, sorted_by_kind,
)
from terrane.render_library import render_connections  # noqa: E402
from terrane.schema import INTEGRATION_STYLES  # noqa: E402

from _fixture import REPO, Sandbox, seeded_model, setup_shared, teardown_shared  # noqa: E402


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestTheShippedKinds(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.kinds = load_connections(REPO)

    def test_they_load_and_none_overlap(self) -> None:
        self.assertGreaterEqual(len(self.kinds), 10)
        self.assertEqual(overlaps(self.kinds), [])

    def test_every_style_is_one_of_the_three(self) -> None:
        for kind in self.kinds.values():
            self.assertIn(kind.integration_style, INTEGRATION_STYLES)

    def test_every_pattern_is_in_the_library(self) -> None:
        patterns = load_patterns(REPO)
        for kind in self.kinds.values():
            for pattern_id in kind.patterns:
                self.assertIn(pattern_id, patterns, kind.connection_id)

    def test_a_kind_recognizes_what_it_proposes(self) -> None:
        """A new interface made from a kind is counted as that kind."""
        for kind in self.kinds.values():
            with self.subTest(kind=kind.connection_id):
                self.assertEqual(kind_of(kind.defaults(), self.kinds), kind.connection_id)

    def test_most_of_the_seed_is_of_a_kind(self) -> None:
        """Read off the estate: a catalog that recognized little of it would
        be a list of hopes."""
        model = seeded_model()
        interfaces = model.all_of("interfaces")
        by_kind, none = sorted_by_kind(interfaces, self.kinds)
        self.assertEqual(sum(len(v) for v in by_kind.values()) + len(none), len(interfaces))
        self.assertLess(len(none), len(interfaces) / 10)

    def test_no_kind_names_a_vendor_product(self) -> None:
        """Like a block, a kind is the architecture half; the product that
        carries a protocol is the technology service's business."""
        vendors = ("aws", "azure", "amazon", "google", "microsoft", "oracle", "ibm")
        for kind in self.kinds.values():
            said = (kind.connection_id + " " + kind.name + " " + kind.description).lower()
            for vendor in vendors:
                self.assertNotIn(vendor, said.split(), kind.connection_id)


class TestTheGate(unittest.TestCase):
    def _write(self, root: Path, text: str) -> None:
        folder = root / "24_CONNECTIONS"
        for old in folder.glob("*.yaml"):
            old.unlink()
        (folder / "probe.yaml").write_text(text, encoding="utf-8")

    def _codes(self, root: Path):
        from terrane import model as model_module

        return [f.code for f in validate.run(model_module.load(root)).findings if f.code.startswith("connection.")]

    def test_an_overlap_is_an_error(self) -> None:
        with Sandbox() as root:
            self._write(root, "- connection_id: a\n  name: A\n  integration_style: Event\n  protocols: [AMQP]\n"
                              "- connection_id: b\n  name: B\n  integration_style: Event\n  protocols: [amqp, Kafka]\n")
            self.assertIn("connection.overlap", self._codes(root))

    def test_an_unknown_pattern_is_an_error_and_a_deprecated_one_a_warning(self) -> None:
        with Sandbox() as root:
            self._write(root, "- connection_id: a\n  name: A\n  integration_style: Batch\n  protocols: [SQL]\n"
                              "  patterns: [no-such-pattern]\n"
                              "- connection_id: b\n  name: B\n  integration_style: Request-response\n"
                              "  protocols: [JDBC]\n  patterns: [shared-database-integration]\n")
            codes = self._codes(root)
            self.assertIn("connection.unknown_pattern", codes)
            self.assertIn("connection.deprecated_pattern", codes)

    def test_a_malformed_kind_is_refused(self) -> None:
        for data in ({"name": "No id"},
                     {"connection_id": "x", "name": "X", "integration_style": "Smoke signal", "protocols": ["a"]},
                     {"connection_id": "x", "name": "X", "integration_style": "Event"},
                     {"connection_id": "x", "name": "X", "integration_style": "Event", "protocols": ["a"],
                      "datastore": "inside"}):
            with self.subTest(data=data):
                with self.assertRaises(LibraryError):
                    parse_connection(data)

    def test_no_folder_is_an_empty_catalog(self) -> None:
        with Sandbox() as root:
            import shutil

            shutil.rmtree(root / "24_CONNECTIONS")
            self.assertEqual(load_connections(root), {})
            self.assertEqual(self._codes(root), [])


class TestADatabasesWaysInAndOut(unittest.TestCase):
    """`datastore:` on a kind: which end is a data store, a component type
    the library draws as a cylinder, where the kind is a way into one, out
    of one or between two."""

    @classmethod
    def setUpClass(cls) -> None:
        from terrane.blocks import load_components

        cls.kinds = load_connections(REPO)
        cls.stores = data_stores(load_components(REPO))

    def test_a_data_store_is_drawn_as_a_cylinder(self) -> None:
        for kind in ("relational-db", "document-db", "cache", "warehouse", "object-store", "archive"):
            self.assertIn(kind, self.stores)
        for kind in ("etl", "bi", "stream-processing", "service-api", "web-app"):
            self.assertNotIn(kind, self.stores)

    def test_the_ways_in_and_out(self) -> None:
        said = {k.connection_id: k.datastore for k in self.kinds.values() if k.datastore}
        self.assertEqual(said, {"own-datastore": "target", "pipeline-load": "target", "change-data-capture": "source",
                                "database-extract": "source", "database-replica": "both", "database-backup": "both"})
        self.assertTrue(all(k.datastore in DATASTORE_ENDS + ("",) for k in self.kinds.values()))

    def test_what_each_end_calls_for(self) -> None:
        own, cdc, replica = (self.kinds[k] for k in ("own-datastore", "change-data-capture", "database-replica"))
        # Into a store from a service; never from another store, which does
        # not read and write it as its own.
        self.assertEqual([fits(own, a, b) for a, b in ((False, True), (True, True), (True, False))], [True, False, False])
        self.assertEqual([fits(cdc, a, b) for a, b in ((True, False), (True, True), (False, True))], [True, True, False])
        self.assertEqual([fits(replica, a, b) for a, b in ((True, True), (True, False))], [True, False])
        self.assertFalse(fits(self.kinds["api-call"], True, True))

    def test_the_catalog_says_where(self) -> None:
        text = render_connections(self.kinds, load_patterns(REPO), seeded_model())
        self.assertIn("**Where.** Out of a data store, offered first where the source is one.", text)
        self.assertIn("**Where.** From one data store to another, offered first where both ends are.", text)


class TestWhatTheySay(unittest.TestCase):
    def test_the_catalog_counts_every_interface_once(self) -> None:
        model = seeded_model()
        kinds = load_connections(REPO)
        text = render_connections(kinds, load_patterns(REPO), model)
        total = len(model.all_of("interfaces"))
        _by, none = sorted_by_kind(model.all_of("interfaces"), kinds)
        self.assertIn("%d of %d interfaces are of a kind" % (total - len(none), total), text)
        self.assertIn("## Of no kind", text)
        for kind in kinds.values():
            self.assertIn("## %s" % kind.name, text)

    def test_the_chooser_offers_the_kinds_between_two_systems(self) -> None:
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module
        from _fixture import seeded_root

        importlib.reload(server_module)
        server_module.REPO_ROOT = seeded_root()
        model = seeded_model()
        record = model.all_of("interfaces")[0]
        got = server_module.api_connect_options(
            {"from": [record["source_system_id"]], "to": [record["target_system_id"]]}, None)
        calls = [o for o in got["options"] if o["kind"] == "interface"]
        self.assertTrue(calls)
        self.assertEqual(len(calls[0]["kinds"]), len(load_connections(REPO)))
        library = server_module.api_library({}, None)["connections"]
        self.assertEqual(len(library["kinds"]), len(load_connections(REPO)))


if __name__ == "__main__":
    unittest.main()
