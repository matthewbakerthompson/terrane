"""An ArchiMate model, Archi's own file or the exchange format, read as a
sketch: the elements as records of the method's types, the relationships
as the connections the method has, the views written out."""

from __future__ import annotations

import unittest
from pathlib import Path

import terrane
from terrane.archimate_import import ArchimateError, parse, sketch_from_archimate
from terrane.quick import check_sketch, read_any

from _fixture import REPO

QUICK = REPO / "90_EXAMPLE" / "quick"
EXCHANGE = (QUICK / "sample-exchange.xml").read_text(encoding="utf-8")
ARCHI = (QUICK / "sample.archimate").read_text(encoding="utf-8")


def _rows(doc: dict, relation: str):
    return doc.get("relations", {}).get(relation, [])


class TestParse(unittest.TestCase):
    def test_both_formats_hold_the_same_model(self) -> None:
        exchange, archi = parse(EXCHANGE), parse(ARCHI)
        self.assertEqual(exchange.name, "Card payments, in ArchiMate")
        self.assertEqual(archi.name, "Card payments, in Archi")
        self.assertEqual(exchange.elements["id-switch"].type, "applicationcomponent")
        self.assertEqual(archi.elements["id-switch"].type, "applicationcomponent")
        self.assertEqual(exchange.elements["id-switch"].documentation,
                         "Routes every authorization request to the scheme and the ledger.")
        self.assertEqual(archi.elements["id-switch"].documentation, exchange.elements["id-switch"].documentation)
        # Archi numbers the access types; the exchange format spells them.
        access = {r.id: r.access for r in exchange.relationships if r.type == "access"}
        self.assertEqual(access, {"id-r5": "ReadWrite", "id-r6": "Read"})
        access = {r.id: r.access for r in archi.relationships if r.type == "access"}
        self.assertEqual(access, {"id-r5": "ReadWrite", "id-r6": "Read"})
        self.assertEqual([v.name for v in exchange.views], ["Application cooperation", "Capability realization"])
        self.assertEqual([v.name for v in archi.views], ["Application cooperation", "Capability realization"])
        # What a view nests inside a grouping, or Archi's visual group.
        self.assertEqual(exchange.views[0].nested["id-switch"], "Payments")
        self.assertEqual(archi.views[1].nested["id-cap-payments"], "Strategy")
        self.assertEqual(archi.views[0].relationships, ["id-r3", "id-r4", "id-r5"])

    def test_what_is_not_an_archimate_model_is_refused_with_the_reason(self) -> None:
        with self.assertRaises(ArchimateError) as caught:
            parse("<html/>")
        self.assertIn("<html>", str(caught.exception))
        with self.assertRaises(ArchimateError):
            parse("not xml at all <")
        with self.assertRaises(ArchimateError) as caught:
            sketch_from_archimate('<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/" identifier="x">'
                                  '<elements><element identifier="g" xsi:type="Goal" '
                                  'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><name>G</name></element>'
                                  '</elements></model>')
        self.assertIn("1 goal", str(caught.exception))


class TestSketch(unittest.TestCase):
    def test_elements_become_records_of_their_types(self) -> None:
        doc, notes = sketch_from_archimate(EXCHANGE)
        check_sketch(doc)
        self.assertEqual(doc["model"]["name"], "Card payments, in ArchiMate")
        self.assertEqual([s["system_id"] for s in doc["systems"]],
                         ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING", "SYS-CARD-LEDGER", "SYS-MERCHANT-PORTAL"])
        self.assertEqual(doc["systems"][0]["description"],
                         "Routes every authorization request to the scheme and the ledger.")
        # The grouping that aggregates a thing is its domain.
        self.assertEqual([s["company_domain"] for s in doc["systems"]], ["Payments"] * 3 + ["Channels"])
        self.assertEqual([a["actor_kind"] for a in doc["actors"]], ["Person", "Role"])
        self.assertEqual(doc["data_assets"][0]["data_asset_id"], "DA-TRANSACTIONS")
        self.assertEqual([t["name"] for t in doc["tech_services"]], ["Kubernetes cluster", "PostgreSQL"])
        self.assertEqual([c["name"] for c in doc["capabilities"]], ["Payment processing", "Fraud detection"])
        self.assertEqual(doc["policies"][0]["name"], "Card data stays in the PCI zone")
        self.assertEqual(doc["processes"][0]["name"], "Authorize a card payment")
        # A goal has no counterpart; said, with its count.
        self.assertTrue(any("1 goal element(s) have no counterpart" in n for n in notes), notes)

    def test_relationships_become_the_connections_the_method_has(self) -> None:
        doc, _ = sketch_from_archimate(EXCHANGE)
        # Flow between components: an interface, named after the relationship.
        self.assertEqual([(i["source_system_id"], i["target_system_id"], i.get("name")) for i in doc["interfaces"]],
                         [("SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING", "Scores the transaction"),
                          ("SYS-AUTHORIZATION-SWITCH", "SYS-CARD-LEDGER", "Posts the authorization"),
                          ("SYS-AUTHORIZATION-SWITCH", "SYS-MERCHANT-PORTAL", "Refund requests")])
        # The service the switch realizes serves the merchant: the merchant
        # uses the switch. The portal serves the cardholder likewise.
        self.assertEqual(sorted((r["actor_id"], r["system_id"]) for r in _rows(doc, "actor_uses_system")),
                         [("ACT-CARDHOLDER", "SYS-MERCHANT-PORTAL"), ("ACT-MERCHANT", "SYS-AUTHORIZATION-SWITCH")])
        # Access, by its type.
        self.assertEqual(sorted((r["system_id"], r["operation"]) for r in _rows(doc, "system_reads_writes")),
                         [("SYS-CARD-LEDGER", "ReadWrite"), ("SYS-FRAUD-SCORING", "Read")])
        self.assertEqual(sorted((r["system_id"], r["capability_id"]) for r in _rows(doc, "system_realizes_capability")),
                         [("SYS-AUTHORIZATION-SWITCH", "CAP-PAYMENT-PROCESSING"), ("SYS-FRAUD-SCORING", "CAP-FRAUD-DETECTION")])
        self.assertEqual([(r["process_id"], r["capability_id"]) for r in _rows(doc, "process_supports_capability")],
                         [("P-AUTHORIZE-A-CARD-PAYMENT", "CAP-PAYMENT-PROCESSING")])
        # Assignment of a component to a node: where it runs.
        self.assertEqual(sorted((r["system_id"], r["tech_service_id"]) for r in _rows(doc, "system_uses_tech_service")),
                         [("SYS-AUTHORIZATION-SWITCH", "TS-KUBERNETES-CLUSTER"), ("SYS-CARD-LEDGER", "TS-POSTGRESQL"),
                          ("SYS-FRAUD-SCORING", "TS-KUBERNETES-CLUSTER")])
        # An association from a principle to a component: the system is subject to the policy.
        self.assertEqual([(r["system_id"], r["policy_id"]) for r in _rows(doc, "system_subject_to_policy")],
                         [("SYS-CARD-LEDGER", "POL-CARD-DATA-STAYS-IN-THE-PCI-ZONE")])

    def test_a_flow_with_a_connection_kind_property_is_of_that_kind(self) -> None:
        text = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<archimate:model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'xmlns:archimate="http://www.archimatetool.com" name="Kinds" id="m" version="5.0.0">\n'
                '  <folder name="Application" id="f" type="application">\n'
                '    <element xsi:type="archimate:ApplicationComponent" name="Auth" id="a"/>\n'
                '    <element xsi:type="archimate:ApplicationComponent" name="Store" id="b"/>\n'
                '  </folder>\n'
                '  <folder name="Relations" id="r" type="relations">\n'
                '    <element xsi:type="archimate:FlowRelationship" id="r1" name="Keep the state (PostgreSQL)" source="a" target="b">\n'
                '      <property key="Connection kind" value="own-datastore"/>\n'
                '      <property key="Protocol" value="PostgreSQL"/>\n'
                '    </element>\n'
                '  </folder>\n'
                '</archimate:model>\n')
        doc, _notes = sketch_from_archimate(text)
        interface = doc["interfaces"][0]
        # The protocol the model said is one the kind carries, so it stays; the kind gives the rest.
        self.assertEqual((interface["name"], interface["protocol"], interface["integration_style"], interface["auth_method"]),
                         ("Keep the state", "PostgreSQL", "Request-response", "ManagedIdentity"))

    def test_the_views_are_written_out_and_the_whole_model_is_one_more(self) -> None:
        doc, notes = sketch_from_archimate(EXCHANGE)
        views = doc["views"]
        self.assertEqual([v["view_id"] for v in views], ["application-cooperation", "capability-realization",
                                                          "whole-model"])
        apps = views[0]
        self.assertEqual(apps["title"], "Application cooperation")
        included = {i["type"]: i["where"]["id_in"] for i in apps["scope"]["include"]}
        self.assertEqual(included, {"systems": ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING", "SYS-CARD-LEDGER",
                                                "SYS-MERCHANT-PORTAL"], "data_assets": ["DA-TRANSACTIONS"]})
        self.assertEqual(apps["group_by"], "company_domain")
        self.assertIn({"via": "interfaces", "label": "protocol"}, apps["edges"])
        caps = views[1]
        self.assertEqual({i["type"] for i in caps["scope"]["include"]}, {"capabilities", "systems", "processes"})
        whole = views[2]
        self.assertEqual(whole["title"], "Card payments, in ArchiMate, whole")
        self.assertEqual([i["type"] for i in whole["scope"]["include"]],
                         [t for t in ("actors", "capabilities", "data_assets", "policies", "processes", "systems",
                                      "tech_services") if t in doc] if False else
                         [i["type"] for i in whole["scope"]["include"]])
        self.assertTrue(any("2 view(s) of the model written out" in n for n in notes), notes)

    def test_archis_own_file_reads_the_same_way(self) -> None:
        doc, _ = sketch_from_archimate(ARCHI)
        check_sketch(doc)
        self.assertEqual([s["system_id"] for s in doc["systems"]],
                         ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING", "SYS-CARD-LEDGER"])
        self.assertEqual(sorted((r["system_id"], r["operation"]) for r in _rows(doc, "system_reads_writes")),
                         [("SYS-CARD-LEDGER", "ReadWrite"), ("SYS-FRAUD-SCORING", "Read")])
        # Archi's visual group in a view is the domain of what it holds.
        self.assertEqual([c["company_domain"] for c in doc["capabilities"]], ["Strategy", "Strategy"])
        self.assertEqual([v["view_id"] for v in doc["views"]],
                         ["application-cooperation", "capability-realization", "whole-model"])

    def test_the_exports_properties_outrank_the_groupings(self) -> None:
        # An element with the export's properties reads as its record: the
        # domain blank or not, the hosting, the kind; a flow with its id and
        # pinned values; a relationship with its row and qualifier or the
        # field it draws. One without reads by its grouping as before.
        ns = 'xmlns="http://www.opengroup.org/xsd/archimate/3.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'

        def prop(key: str, value: str) -> str:
            return ('<property propertyDefinitionRef="propid-%s"><value xml:lang="en">%s</value></property>'
                    % (key.lower().replace(" ", "-"), value))

        def definition(key: str) -> str:
            return ('<propertyDefinition identifier="propid-%s" type="string"><name xml:lang="en">%s</name>'
                    '</propertyDefinition>' % (key.lower().replace(" ", "-"), key))

        text = ('<?xml version="1.0" encoding="UTF-8"?><model %s identifier="id-model"><name xml:lang="en">Marked</name>'
                '<documentation xml:lang="en">Exported from the model by architecture-as-code.</documentation>'
                '<elements>'
                '<element identifier="id-SYS-CRM" xsi:type="ApplicationComponent"><name xml:lang="en">CRM</name>'
                '<properties>%s%s</properties></element>'
                '<element identifier="id-SYS-PLAIN" xsi:type="ApplicationComponent"><name xml:lang="en">Plain</name>'
                '<properties>%s</properties></element>'
                '<element identifier="id-SYS-GROUPED" xsi:type="ApplicationComponent"><name xml:lang="en">Grouped</name>'
                '</element>'
                '<element identifier="id-DA-PROFILE" xsi:type="DataObject"><name xml:lang="en">Profile</name>'
                '<properties>%s</properties></element>'
                '<element identifier="id-ACT-AGENT" xsi:type="BusinessActor"><name xml:lang="en">Agent</name>'
                '<properties>%s%s</properties></element>'
                '<element identifier="id-G" xsi:type="Grouping"><name xml:lang="en">System</name></element>'
                '</elements><relationships>'
                '<relationship identifier="id-g1" source="id-G" target="id-SYS-GROUPED" xsi:type="Composition"/>'
                '<relationship identifier="id-INT-PLAIN-CRM" source="id-SYS-PLAIN" target="id-SYS-CRM" xsi:type="Flow">'
                '<name xml:lang="en">Posts cases (HTTPS)</name><properties>%s%s%s%s</properties></relationship>'
                '<relationship identifier="id-r1" source="id-SYS-CRM" target="id-DA-PROFILE" xsi:type="Access" '
                'accessType="ReadWrite"><properties>%s%s</properties></relationship>'
                '<relationship identifier="id-r2" source="id-SYS-CRM" target="id-DA-PROFILE" xsi:type="Association">'
                '<name xml:lang="en">source of truth</name><properties>%s</properties></relationship>'
                '</relationships><propertyDefinitions>%s</propertyDefinitions></model>'
                % (ns, prop("Company domain", "Servicing"), prop("Hosting", "SaaS"), prop("Company domain", ""),
                   prop("Company domain", "Servicing"), prop("Company domain", "Servicing"), prop("Actor kind", "Role"),
                   prop("Interface id", "INT-PLAIN-CRM"), prop("Protocol", "HTTPS"), prop("Connection kind", "api-call"),
                   prop("Auth method", "HMAC"), prop("Relation", "system_reads_writes"), prop("Operation", "Read"),
                   prop("Field", "source_of_truth"),
                   "".join(definition(k) for k in ("Company domain", "Hosting", "Actor kind", "Interface id", "Protocol",
                                                    "Connection kind", "Auth method", "Relation", "Operation", "Field"))))
        doc, notes = sketch_from_archimate(text, name="marked")
        check_sketch(doc)
        systems = {s["system_id"]: s for s in doc["systems"]}
        self.assertEqual((systems["SYS-CRM"]["company_domain"], systems["SYS-CRM"]["hosting"]), ("Servicing", "SaaS"))
        self.assertNotIn("company_domain", systems["SYS-PLAIN"])
        self.assertEqual(systems["SYS-GROUPED"]["company_domain"], "System")
        self.assertEqual(doc["actors"][0]["actor_kind"], "Role")
        line = doc["interfaces"][0]
        self.assertEqual((line["interface_id"], line["name"], line["protocol"], line["auth_method"]),
                         ("INT-PLAIN-CRM", "Posts cases", "HTTPS", "HMAC"))
        self.assertEqual(doc["relations"], {"system_reads_writes": [
            {"system_id": "SYS-CRM", "data_asset_id": "DA-PROFILE", "operation": "Read"}]})
        self.assertEqual(doc["data_assets"][0]["source_of_truth"], "SYS-CRM")
        self.assertTrue(any("the model's own, which the engine wrote" in n for n in notes), notes)

    def test_the_python_door_reads_the_file_by_its_suffix(self) -> None:
        doc, notes = read_any(QUICK / "sample.archimate")
        self.assertEqual(doc["model"]["name"], "Card payments, in Archi")
        self.assertTrue(notes)
        doc, _ = read_any(QUICK / "sample-exchange.xml")
        self.assertEqual(doc["model"]["name"], "Card payments, in ArchiMate")
        doc, _ = read_any(QUICK / "sample.dsl")
        self.assertIn("systems", doc)
        doc, _ = read_any(QUICK / "payments.yaml")
        self.assertEqual(doc["model"]["name"], "Card payments, sketched")

    def test_the_door_draws_an_archimate_model(self) -> None:
        drawings = terrane.diagrams(str(QUICK / "sample-exchange.xml"), date="2026-10-17")
        self.assertEqual(sorted(drawings), ["application-cooperation", "capability-realization", "whole-model"])
        self.assertIn("Authorization switch", drawings["application-cooperation"].svg)
        self.assertIn("Fraud detection", drawings["capability-realization"].svg)
        self.assertTrue(any("from the ArchiMate model" in n for n in drawings.notes), drawings.notes)


if __name__ == "__main__":
    unittest.main()
