"""A Visio drawing read as a sketch: a shape per thing by the master it was
dragged from, a connector per connection, a container per domain, a page
per view."""

from __future__ import annotations

import io
import unittest
import zipfile

import terrane
from terrane.quick import check_sketch, read_any
from terrane.visio_import import VisioError, pages, sketch_from_visio

from _fixture import REPO

PATH = REPO / "90_EXAMPLE" / "quick" / "sample.vsdx"
SAMPLE = PATH.read_bytes()


class TestPages(unittest.TestCase):
    def test_two_pages_with_their_shapes_and_connects(self) -> None:
        read = pages(SAMPLE)
        self.assertEqual([name for name, _, _ in read], ["Applications", "Data"])
        shapes = {s.id: s for s in read[0][1]}
        self.assertEqual(shapes["2"].text, "Authorization switch")
        self.assertEqual(shapes["2"].master, "Process")
        self.assertEqual(shapes["4"].master, "Database")
        # The formatting runs inside <Text> are gone, the words kept.
        self.assertEqual(shapes["8"].text, "Card data stays in the PCI zone")
        self.assertIn(("20", "2", "3"), read[0][2])
        # A group's children are placed on the page, not inside the group.
        data = {s.id: s for s in read[1][1]}
        self.assertEqual(data["3"].parent, "2")
        self.assertAlmostEqual(data["3"].x, data["2"].x - data["2"].w / 2 + 1.0)

    def test_what_is_not_visio_is_refused(self) -> None:
        with self.assertRaises(VisioError):
            pages(b"not a zip at all")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", "<w/>")
        with self.assertRaises(VisioError):
            pages(buffer.getvalue())


class TestSketch(unittest.TestCase):
    def test_shapes_become_records_by_their_master(self) -> None:
        doc, notes = sketch_from_visio(SAMPLE, name="Card payments, in Visio")
        check_sketch(doc)
        self.assertEqual(doc["model"]["name"], "Card payments, in Visio")
        # The switch is a Process box: a system, whatever its text says.
        self.assertEqual(sorted(s["system_id"] for s in doc["systems"]),
                         ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING"])
        self.assertEqual([s.get("company_domain") for s in doc["systems"]], ["Payments", "Payments"])
        self.assertEqual([d["data_asset_id"] for d in doc["data_assets"]], ["DA-CARD-LEDGER", "DA-REPORTING-MART"])
        self.assertEqual(doc["data_assets"][0]["company_domain"], "Payments")
        # The mart sits in a group on the second page: the group's text is its domain.
        self.assertEqual(doc["data_assets"][1]["company_domain"], "Data platform")
        self.assertEqual([(a["name"], a["actor_kind"]) for a in doc["actors"]], [("Merchant", "Person")])
        self.assertEqual(doc["capabilities"][0]["name"], "Payment processing")
        self.assertEqual(doc["tech_services"][0]["name"], "Kubernetes cluster")
        # A Document shape is a policy, not a zone, whatever its text says.
        self.assertEqual(doc["policies"][0]["name"], "Card data stays in the PCI zone")
        # A box with no text is decoration, not a thing.
        self.assertFalse(any("Process.9" in str(r) for t in doc for r in (doc[t] if isinstance(doc[t], list) else [])))
        self.assertNotIn("org_units", doc)

    def test_connectors_become_the_connections_the_method_has(self) -> None:
        doc, notes = sketch_from_visio(SAMPLE)
        interfaces = {(i["source_system_id"], i["target_system_id"]): i for i in doc["interfaces"]}
        self.assertEqual(interfaces[("SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING")].get("protocol"), "gRPC")
        relations = doc["relations"]
        # The connector's text rides the relation as the interaction.
        self.assertIn({"actor_id": "ACT-MERCHANT", "system_id": "SYS-AUTHORIZATION-SWITCH",
                       "interaction": "Presents a card"}, relations["actor_uses_system"])
        self.assertIn({"system_id": "SYS-AUTHORIZATION-SWITCH", "capability_id": "CAP-PAYMENT-PROCESSING"},
                      relations["system_realizes_capability"])
        writes = [r for r in relations["system_reads_writes"] if r["system_id"] == "SYS-AUTHORIZATION-SWITCH"]
        self.assertEqual(writes[0]["operation"], "Write")
        self.assertIn({"system_id": "SYS-FRAUD-SCORING", "tech_service_id": "TS-KUBERNETES-CLUSTER"},
                      [{k: r[k] for k in ("system_id", "tech_service_id")} for r in relations["system_uses_tech_service"]])
        self.assertTrue(any("glued at one end only" in n and "loose" in n for n in notes), notes)

    def test_a_page_is_a_view_and_a_thing_on_two_pages_is_one_record(self) -> None:
        doc, notes = sketch_from_visio(SAMPLE)
        self.assertEqual([v["view_id"] for v in doc["views"]], ["applications", "data"])
        self.assertEqual(doc["views"][1]["title"], "Data")
        # A page is a view of what it draws, not of every record of its types.
        self.assertEqual(doc["views"][1]["scope"]["include"],
                         [{"type": "systems", "where": {"id_in": ["SYS-FRAUD-SCORING"]}},
                          {"type": "data_assets", "where": {"id_in": ["DA-CARD-LEDGER", "DA-REPORTING-MART"]}}])
        self.assertNotIn("DA-REPORTING-MART", str(doc["views"][0]["scope"]))
        # The ledger is a Database on one page and a plain box inside a group on the other: one data asset.
        self.assertEqual(len([d for d in doc["data_assets"] if d["data_asset_id"] == "DA-CARD-LEDGER"]), 1)
        self.assertEqual(len([s for s in doc["systems"] if s["system_id"] == "SYS-FRAUD-SCORING"]), 1)
        reads = [r for r in doc["relations"]["system_reads_writes"] if r["system_id"] == "SYS-FRAUD-SCORING"]
        self.assertEqual(reads[0]["operation"], "Read")
        self.assertTrue(notes[0].startswith("read "), notes[0])
        self.assertIn("2 page(s)", notes[0])

    def test_the_door_takes_the_file_by_its_suffix(self) -> None:
        doc, _ = read_any(PATH)
        self.assertIn("systems", doc)
        drawings = terrane.diagrams(str(PATH), date="2026-10-17")
        self.assertEqual(sorted(drawings), ["applications", "data"])
        self.assertIn("Authorization switch", drawings["applications"].svg)
        self.assertNotIn("Reporting mart", drawings["applications"].svg)
        self.assertIn("Reporting mart", drawings["data"].svg)


if __name__ == "__main__":
    unittest.main()
