"""The estate exported as an ArchiMate exchange file, and read back by the
reader as the same model."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

import terrane
from terrane.archimate_import import parse, sketch_from_archimate
from terrane.blocks import load_components
from terrane.icons import IconMap
from terrane.join import join_estate
from terrane.palette import Palette
from terrane.quick import read_any
from terrane.render_archimate import ELEMENT_TYPES, export_archimate, gather

from _fixture import REPO, Sandbox, seeded_model, seeded_views

WEB = REPO / "80_APP" / "web"


class TestExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = seeded_views()
        cls.tmp = Path(tempfile.mkdtemp(prefix="aac-archimate-"))
        cls.path, cls.notes = export_archimate(cls.model, cls.views, cls.tmp / "model.xml",
                                               Palette(cls.model.config.get("palette")), IconMap(WEB),
                                               load_components(REPO))
        cls.text = cls.path.read_text(encoding="utf-8")

    def test_every_record_is_an_element_of_its_type_once(self) -> None:
        root = ElementTree.fromstring(self.text)
        elements = {e.attrib["identifier"]: e for e in root.iter("{%s}element" % "http://www.opengroup.org/xsd/archimate/3.0/")}
        for type_name, kind in ELEMENT_TYPES.items():
            for entity_id, record in self.model.entities.get(type_name, {}).items():
                element = elements.get("id-" + entity_id)
                self.assertIsNotNone(element, entity_id)
                xsi = element.attrib["{http://www.w3.org/2001/XMLSchema-instance}type"]
                if type_name == "actors":
                    self.assertIn(xsi, ("BusinessActor", "BusinessRole"), entity_id)
                elif type_name == "tech_services":
                    self.assertIn(xsi, ("Node", "SystemSoftware", "CommunicationNetwork"), entity_id)
                else:
                    self.assertEqual(xsi, kind, entity_id)
        self.assertEqual(len(elements), sum(len(self.model.entities.get(t, {})) for t in ELEMENT_TYPES))
        self.assertTrue(any("roadmaps" in n for n in self.notes), self.notes)

    def test_relationships_carry_the_kinds_the_reader_maps_back(self) -> None:
        exported = gather(self.model)
        kinds = {r[1] for r in exported.relationships}
        self.assertEqual(kinds, {"Flow", "Serving", "Access", "Realization", "Aggregation", "Composition",
                                 "Association"})
        interfaces = [r for r in exported.relationships if r[1] == "Flow"]
        self.assertEqual(len(interfaces), len(self.model.entities["interfaces"]))
        access = [r for r in exported.relationships if r[1] == "Access"]
        self.assertTrue(all(r[5] in ("Read", "Write", "ReadWrite") for r in access))
        # Use is a serving the other way round: the system serves the actor.
        serving = {(r[2], r[3]) for r in exported.relationships if r[1] == "Serving"}
        row = self.model.relations["actor_uses_system"][0]
        self.assertIn(("id-" + row["system_id"], "id-" + row["actor_id"]), serving)

    def test_the_views_are_in_the_file_with_the_engines_layout(self) -> None:
        model = parse(self.text)
        names = [v.name for v in model.views]
        self.assertIn("System Context", names)
        self.assertIn("Application Landscape", names)
        self.assertNotIn("Change Register", names)  # a report is a table
        context = next(v for v in model.views if v.name == "System Context")
        self.assertGreater(len(context.elements), 10)
        self.assertTrue(context.relationships)
        root = ElementTree.fromstring(self.text)
        ns = "{http://www.opengroup.org/xsd/archimate/3.0/}"
        view = next(v for v in root.iter(ns + "view") if v.find(ns + "name").text == "System Context")
        nodes = list(view.iter(ns + "node"))
        self.assertTrue(all(int(n.attrib["w"]) > 0 and int(n.attrib["h"]) > 0 for n in nodes))
        self.assertTrue(all(int(n.attrib["x"]) >= 0 and int(n.attrib["y"]) >= 0 for n in nodes))
        # A boundary is a container node with its children inside it.
        containers = [n for n in nodes if n.attrib["{http://www.w3.org/2001/XMLSchema-instance}type"] == "Container"]
        self.assertTrue(containers)
        self.assertTrue(all(len(list(c.iter(ns + "node"))) > 1 for c in containers))

    def test_read_back_it_is_the_same_model(self) -> None:
        doc, notes = sketch_from_archimate(self.text)
        systems = {s["system_id"] for s in doc["systems"]}
        self.assertEqual(systems, set(self.model.entities["systems"]))
        self.assertEqual({a["actor_id"] for a in doc["actors"]}, set(self.model.entities["actors"]))
        # An org unit is a business actor in ArchiMate; its exported id says it is an org unit here.
        self.assertEqual({o["org_unit_id"] for o in doc["org_units"]}, set(self.model.entities["org_units"]))
        self.assertEqual({d["data_asset_id"] for d in doc["data_assets"]}, set(self.model.entities["data_assets"]))
        self.assertEqual({c["capability_id"] for c in doc["capabilities"]}, set(self.model.entities["capabilities"]))
        interfaces = {(i["source_system_id"], i["target_system_id"]) for i in doc["interfaces"]}
        wanted = {(r["source_system_id"], r["target_system_id"]) for r in self.model.entities["interfaces"].values()}
        self.assertEqual(interfaces, wanted)
        uses = {(r["actor_id"], r["system_id"]) for r in doc["relations"]["actor_uses_system"]}
        self.assertEqual(uses, {(r["actor_id"], r["system_id"]) for r in self.model.relations["actor_uses_system"]})
        realizes = {(r["system_id"], r["capability_id"]) for r in doc["relations"]["system_realizes_capability"]}
        self.assertEqual(realizes, {(r["system_id"], r["capability_id"])
                                    for r in self.model.relations["system_realizes_capability"]})
        parents = {c["capability_id"]: c.get("parent_capability_id") for c in doc["capabilities"]}
        for entity_id, record in self.model.entities["capabilities"].items():
            if record.get("parent_capability_id"):
                self.assertEqual(parents[entity_id], record["parent_capability_id"], entity_id)
        # Every picture view came back as a view of the sketch, the whole model last.
        self.assertGreater(len(doc["views"]), 30)
        self.assertEqual(doc["views"][-1]["view_id"], "whole-model")
        self.assertIn("system-context", [v["view_id"] for v in doc["views"]])

    def test_a_flow_carries_its_protocol_and_its_kind_as_properties_and_comes_back_as_the_connection(self) -> None:
        from terrane.connections import kind_of, load_connections

        self.assertIn('<propertyDefinition identifier="propid-connection-kind" type="string">', self.text)
        self.assertIn('<propertyDefinition identifier="propid-protocol" type="string">', self.text)
        self.assertIn('<value xml:lang="en">queued-request</value>', self.text)
        doc, _notes = sketch_from_archimate(self.text)
        interfaces = {(i["source_system_id"], i["target_system_id"]): i for i in doc["interfaces"]}
        back = interfaces[("SYS-AUTH-SWITCH", "SYS-CORE-LEDGER")]
        # The protocol is a field again, not a bracket in the name, and the kind gives the style.
        self.assertEqual((back["name"], back["protocol"]), ("Authorization Switch to Core Ledger", "MQ"))
        self.assertEqual(kind_of(back, load_connections(self.model.root)), "queued-request")
        kinds = load_connections(self.model.root)
        tagged = sum(1 for i in self.model.all_of("interfaces") if kind_of(i, kinds))
        returned = sum(1 for i in doc["interfaces"] if kind_of(i, kinds))
        self.assertGreaterEqual(returned, tagged - 2, (returned, tagged))

    def test_the_estates_own_export_reads_back_as_the_estate(self) -> None:
        # Read back unchanged with --correct, the export "would correct" 48
        # systems, 160 capabilities, 149 processes and every control, their
        # domains read off the type groupings, and add all 115 interfaces
        # anew, a flow carrying no id. The records ride as properties now.
        self.assertIn('<propertyDefinition identifier="propid-company-domain" type="string">', self.text)
        self.assertIn('<value xml:lang="en">INT-AUTH-LEDGER</value>', self.text)
        with Sandbox(seed=True) as root:
            out = Path(tempfile.mkdtemp(prefix="aac-archimate-")) / "estate.xml"
            path, _notes = terrane.export_archimate(str(root), out)
            doc, notes = read_any(path, root)
            self.assertTrue(any("the model's own, which the engine wrote" in n for n in notes), notes)
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="estate.xml", correct=True, dry_run=True)
            self.assertEqual(result.changed, {}, result.changes[:12])
            self.assertEqual(result.added, {})
            self.assertEqual(result.rows_added, 0)
            # A reviewer in the tool they know: a label renamed and a line
            # drawn between two systems on the landscape. Read back, one
            # correction and one new interface, nothing else.
            xml = path.read_text(encoding="utf-8")
            name = '<name xml:lang="en">Dynamics 365 Customer Service</name>'
            self.assertEqual(xml.count(name), 1)
            edited = xml.replace(name, '<name xml:lang="en">Dynamics 365 Customer Service (reviewed)</name>')
            flow = ('    <relationship identifier="id-hand-1" source="id-SYS-CRM" target="id-SYS-STATEMENTS" xsi:type="Flow">'
                    '<name xml:lang="en">Requests statements</name></relationship>\n  </relationships>')
            edited = edited.replace("  </relationships>", flow, 1)
            reviewed = path.parent / "reviewed.xml"
            reviewed.write_text(edited, encoding="utf-8")
            doc, _ = read_any(reviewed, root)
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="reviewed.xml", correct=True, dry_run=True)
            self.assertEqual(result.changed, {"systems": ["SYS-CRM"]}, result.changes)
            self.assertEqual(result.added, {"interfaces": ["INT-CRM-STATEMENTS"]})
            self.assertEqual(result.rows_added, 0)

    def test_the_same_model_is_the_same_bytes(self) -> None:
        again, _ = export_archimate(self.model, self.views, self.tmp / "again.xml",
                                    Palette(self.model.config.get("palette")), IconMap(WEB), load_components(REPO))
        self.assertEqual(again.read_text(encoding="utf-8"), self.text)


if __name__ == "__main__":
    unittest.main()
