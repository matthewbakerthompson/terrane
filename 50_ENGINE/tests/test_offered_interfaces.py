"""What a system offers for others to connect to: an API, a topic, a file
drop, as a record of its own (`offered_interfaces`).

What is checked: the product service part names the service it deploys and
offers its API, every caller the parts make going through it; a connection
through an interface its ends do not offer is refused, and one in another
protocol is said; on a diagram the lines through an interface end at it,
drawn in its owner's boundaries and joined to its owner the traffic's way,
saying once what every line through it would have said, and counted as
part of its owner's box; a map keeps its lines on the boxes; the ArchiMate
export composes the interface in its component and ends the connection's
flow at it, and the reader takes both back, from the engine's file and
from a practice's own; Backstage has the interface as the API and the
connections through it as no API of their own; the engine's own Mermaid
and a hand sketch read back with the interface, its owner and the lines
through it; and an interface nothing offers is said and left out.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import model as model_module, validate  # noqa: E402
from terrane.archimate_import import sketch_from_archimate  # noqa: E402
from terrane.blocks import load_components  # noqa: E402
from terrane.exports import export_backstage  # noqa: E402
from terrane.icons import IconMap  # noqa: E402
from terrane.mermaid_import import sketch_from_mermaid  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.plantuml_import import sketch_from_plantuml  # noqa: E402
from terrane.query import resolve  # noqa: E402
from terrane.quick import materialize  # noqa: E402
from terrane.render_archimate import export_archimate  # noqa: E402
from terrane.render_mermaid import render  # noqa: E402
from terrane.render_plantuml import render_plantuml  # noqa: E402

from _fixture import REPO, seeded_model, seeded_views, setup_shared, teardown_shared  # noqa: E402

WEB = REPO / "80_APP" / "web"
ARCHIMATE = "http://www.opengroup.org/xsd/archimate/3.0/"


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestTheRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = model_module.load(REPO)

    def test_the_service_part_names_the_service_and_offers_its_api(self) -> None:
        service = self.model.get("systems", "SYS-LENDING-API")
        # The id the estate's connections, flows and processes point at stays.
        self.assertEqual(service["name"], "Installment Lending Service")
        api = self.model.get("offered_interfaces", "OI-LENDING-API")
        self.assertEqual((api["name"], api["system_id"], api["module"]),
                         ("Installment Lending API", "SYS-LENDING-API", "api-service"))
        self.assertEqual((api["protocol"], api["integration_style"], api["auth_method"]),
                         ("HTTPS", "Request-response", "OAuth2"))
        # The shape's defaults for what it makes: the product's owner and classification.
        self.assertEqual((api["owner_org_id"], api["data_classification"]), ("ORG-PRODUCT", "Restricted"))
        # The parts' callers go through it; the service's own calls out do not.
        self.assertEqual(self.model.get("interfaces", "INT-LENDING-WEB-API")["offered_interface_id"], "OI-LENDING-API")
        self.assertNotIn("offered_interface_id", self.model.get("interfaces", "INT-LENDING-API-DB"))
        self.assertEqual(self.model.get("interfaces", "INT-LENDING-API-DB")["name"],
                         "Installment Lending Service to Database")

    def test_every_service_the_part_makes_offers_one_api(self) -> None:
        made = sorted(k for k, s in self.model.entities["systems"].items() if s.get("module") == "api-service")
        offered = sorted(r["system_id"] for r in self.model.all_of("offered_interfaces")
                         if r.get("module") == "api-service")
        self.assertEqual(made, offered)
        for system_id in made:
            self.assertTrue(self.model.get("systems", system_id)["name"].endswith(" Service"), system_id)

    def test_the_ledger_queue_has_every_mq_caller(self) -> None:
        through = sorted(r["source_system_id"] for r in self.model.all_of("interfaces")
                         if r.get("offered_interface_id") == "OI-LEDGER-QUEUE")
        self.assertEqual(through, ["SYS-AUTH-SWITCH", "SYS-CARDSVC-API", "SYS-COLLECT-API", "SYS-LENDING-API",
                                   "SYS-PAYMENT-GW", "SYS-REWARDS-WORKER"])

    def test_both_estates_validate(self) -> None:
        for root in (REPO, REPO / "90_EXAMPLE" / "thurman-health"):
            with self.subTest(root=root.name):
                report = validate.run(model_module.load(root))
                self.assertEqual([f.format() for f in report.errors], [])


class TestTheChecks(unittest.TestCase):
    def test_an_interface_its_ends_do_not_offer_is_refused(self) -> None:
        model = seeded_model()
        record = model.get("interfaces", "INT-CRM-LEDGER")
        record["offered_interface_id"] = "OI-IDENTITY-API"
        codes = [f.code for f in validate.run(model).errors]
        self.assertIn("interface.offered_by", codes)

    def test_another_protocol_is_said_and_left(self) -> None:
        model = seeded_model()
        record = model.get("interfaces", "INT-CRM-LEDGER")
        record["offered_interface_id"] = "OI-LEDGER-QUEUE"
        report = validate.run(model)
        self.assertNotIn("interface.offered_by", [f.code for f in report.errors])
        said = [f.message for f in report.warnings if f.code == "interface.unlike_offered"]
        self.assertEqual(said, ["interface INT-CRM-LEDGER says HTTPS and goes through OI-LEDGER-QUEUE, which is MQ"])


class TestImpact(unittest.TestCase):
    def test_what_uses_an_interface_depends_on_it_and_it_on_its_system(self) -> None:
        from terrane import impact

        result = impact.analyze(seeded_model(), "OI-LEDGER-QUEUE", max_distance=1)
        self.assertEqual(sorted(h.entity_id for h in result.downstream),
                         ["SYS-AUTH-SWITCH", "SYS-CARDSVC-API", "SYS-COLLECT-API", "SYS-LENDING-API",
                          "SYS-PAYMENT-GW", "SYS-REWARDS-WORKER"])
        self.assertEqual([(h.entity_id, h.via) for h in result.upstream], [("SYS-CORE-LEDGER", "offered by")])


class TestTheDrawing(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}

    def test_a_diagram_ends_the_lines_at_the_interface_on_its_owner(self) -> None:
        graph = resolve(self.model, self.views["integration-architecture"])
        nodes = {n.key: n for n in graph.nodes}
        queue, ledger = nodes["OI-LEDGER-QUEUE"], nodes["SYS-CORE-LEDGER"]
        self.assertEqual((queue.entity_type, queue.groups), ("offered_interfaces", ledger.groups))
        into = sorted(e.source for e in graph.edges if e.target == "OI-LEDGER-QUEUE")
        self.assertIn("SYS-AUTH-SWITCH", into)
        # Caller, queue, ledger: the joining line runs the traffic's way.
        self.assertIn(("OI-LEDGER-QUEUE", "SYS-CORE-LEDGER", "offers"),
                      {(e.source, e.target, e.kind) for e in graph.edges})
        through = {r["source_system_id"] for r in self.model.all_of("interfaces")
                   if r.get("offered_interface_id") == "OI-LEDGER-QUEUE"}
        self.assertFalse([e for e in graph.edges if e.target == "SYS-CORE-LEDGER" and e.source in through])
        # The queue says MQ once; the lines through it do not say it again.
        self.assertEqual({e.label for e in graph.edges if e.target == "OI-LEDGER-QUEUE"}, {""})
        # The CRM's HTTPS call does not go through the queue and keeps its box and its word.
        self.assertIn(("SYS-CRM", "SYS-CORE-LEDGER", "HTTPS"), {(e.source, e.target, e.label) for e in graph.edges})

    def test_an_interface_is_part_of_its_owner_s_box_in_the_count(self) -> None:
        graph = resolve(self.model, self.views["integration-architecture"])
        boxes = [n for n in graph.nodes if n.entity_type != "offered_interfaces"]
        self.assertLessEqual(len(boxes), 40)
        self.assertGreater(len(graph.nodes), len(boxes))

    def test_a_map_keeps_its_lines_on_the_boxes(self) -> None:
        graph = resolve(self.model, self.views["application-landscape"])
        self.assertFalse([n for n in graph.nodes if n.entity_type == "offered_interfaces"])
        self.assertIn(("SYS-AUTH-SWITCH", "SYS-CORE-LEDGER"), {(e.source, e.target) for e in graph.edges})

    def test_a_wheel_keeps_its_spokes_on_its_hub(self) -> None:
        from terrane.estate import views_of
        from terrane.query import bind

        root = REPO / "90_EXAMPLE" / "thurman-health"
        model = model_module.load(root)
        view = [v for v in views_of(root) if v.view_id == "hub-and-spoke"][0]
        graph = resolve(model, bind(view, {"system": "SYS-INTERFACE-ENGINE"}, model))
        self.assertFalse([n for n in graph.nodes if n.entity_type == "offered_interfaces"])
        self.assertIn(("SYS-EHR", "SYS-INTERFACE-ENGINE"), {(e.source, e.target) for e in graph.edges})

    def test_a_topic_is_drawn_after_its_publisher(self) -> None:
        doc = {
            "model": {"name": "Topics"},
            "org_units": [{"org_unit_id": "ORG-X", "name": "X"}],
            "systems": [{"system_id": "SYS-ORDERS", "name": "Orders", "owner_org_id": "ORG-X"},
                        {"system_id": "SYS-BILLING", "name": "Billing", "owner_org_id": "ORG-X"},
                        {"system_id": "SYS-SHIPPING", "name": "Shipping", "owner_org_id": "ORG-X"}],
            "offered_interfaces": [{"offered_interface_id": "OI-ORDER-EVENTS", "name": "Order events",
                                    "system_id": "SYS-ORDERS", "protocol": "Kafka", "integration_style": "Event"}],
            "interfaces": [
                {"interface_id": "INT-ORDERS-BILLING", "source_system_id": "SYS-ORDERS",
                 "target_system_id": "SYS-BILLING", "offered_interface_id": "OI-ORDER-EVENTS", "protocol": "Kafka"},
                {"interface_id": "INT-ORDERS-SHIPPING", "source_system_id": "SYS-ORDERS",
                 "target_system_id": "SYS-SHIPPING", "offered_interface_id": "OI-ORDER-EVENTS", "protocol": "Kafka"}],
            "views": [{"view_id": "orders", "title": "Orders", "kind": "diagram",
                       "scope": {"include": [{"type": "systems"}]}, "edges": [{"via": "interfaces"}]}],
        }
        root = Path(tempfile.mkdtemp(prefix="aac-offered-")) / "sketch"
        materialize(doc, root)
        model = model_module.load(root)
        self.assertEqual(validate.run(model).errors, [])
        from terrane.query import load_views

        view = [v for v in load_views(root / "30_VIEWS") if v.view_id == "orders"][0]
        graph = resolve(model, view)
        edges = {(e.source, e.target, e.kind) for e in graph.edges}
        self.assertEqual(edges, {("SYS-ORDERS", "OI-ORDER-EVENTS", "offers"),
                                 ("OI-ORDER-EVENTS", "SYS-BILLING", "interface"),
                                 ("OI-ORDER-EVENTS", "SYS-SHIPPING", "interface")})


class TestTheExports(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = seeded_views()
        cls.tmp = Path(tempfile.mkdtemp(prefix="aac-offered-"))

    def test_archimate_composes_the_interface_in_its_component_and_reads_it_back(self) -> None:
        from xml.etree import ElementTree

        path, _notes = export_archimate(self.model, self.views, self.tmp / "model.xml",
                                        Palette(self.model.config.get("palette")), IconMap(WEB), load_components(REPO))
        text = path.read_text(encoding="utf-8")
        root = ElementTree.fromstring(text)
        xsi = "{http://www.w3.org/2001/XMLSchema-instance}type"
        elements = {e.attrib["identifier"]: e.attrib[xsi] for e in root.iter("{%s}element" % ARCHIMATE)}
        self.assertEqual(elements["id-OI-LEDGER-QUEUE"], "ApplicationInterface")
        relationships = {r.attrib["identifier"]: (r.attrib[xsi], r.attrib["source"], r.attrib["target"])
                         for r in root.iter("{%s}relationship" % ARCHIMATE)}
        self.assertIn(("Composition", "id-SYS-CORE-LEDGER", "id-OI-LEDGER-QUEUE"), relationships.values())
        self.assertEqual(relationships["id-INT-AUTH-LEDGER"], ("Flow", "id-SYS-AUTH-SWITCH", "id-OI-LEDGER-QUEUE"))
        doc, _ = sketch_from_archimate(text)
        offered = {r["offered_interface_id"]: r for r in doc["offered_interfaces"]}
        self.assertEqual(offered["OI-LEDGER-QUEUE"]["system_id"], "SYS-CORE-LEDGER")
        back = {r["interface_id"]: r for r in doc["interfaces"]}["INT-AUTH-LEDGER"]
        self.assertEqual((back["source_system_id"], back["target_system_id"], back["offered_interface_id"]),
                         ("SYS-AUTH-SWITCH", "SYS-CORE-LEDGER", "OI-LEDGER-QUEUE"))

    def test_a_practice_s_archimate_interface_is_offered_by_its_component(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       identifier="m1">
  <name xml:lang="en">Payments</name>
  <elements>
    <element identifier="a" xsi:type="ApplicationComponent"><name xml:lang="en">Payments service</name></element>
    <element identifier="i" xsi:type="ApplicationInterface"><name xml:lang="en">Payments API</name></element>
    <element identifier="b" xsi:type="ApplicationComponent"><name xml:lang="en">Checkout</name></element>
    <element identifier="c" xsi:type="ApplicationComponent"><name xml:lang="en">Billing</name></element>
  </elements>
  <relationships>
    <relationship identifier="r1" source="a" target="i" xsi:type="Composition"/>
    <relationship identifier="r2" source="b" target="i" xsi:type="Flow"><name xml:lang="en">Takes payment</name></relationship>
    <relationship identifier="r3" source="i" target="c" xsi:type="Serving"/>
  </relationships>
</model>"""
        doc, notes = sketch_from_archimate(xml)
        self.assertEqual([(r["name"], r["system_id"]) for r in doc["offered_interfaces"]],
                         [("Payments API", "SYS-PAYMENTS-SERVICE")])
        lines = {(r["source_system_id"], r["target_system_id"], r.get("offered_interface_id"))
                 for r in doc["interfaces"]}
        self.assertEqual(lines, {("SYS-CHECKOUT", "SYS-PAYMENTS-SERVICE", "OI-PAYMENTS-API"),
                                 ("SYS-BILLING", "SYS-PAYMENTS-SERVICE", "OI-PAYMENTS-API")})

    def test_backstage_has_the_interface_as_the_api(self) -> None:
        path = export_backstage(self.model, self.tmp / "backstage")[0]
        documents = path.read_text(encoding="utf-8").split("\n---\n")
        api = [d for d in documents if 'name: "oi-lending-api"' in d]
        self.assertEqual(len(api), 1)
        self.assertIn('kind: "API"', api[0])
        self.assertIn('system: "sys-lending-api"', api[0])
        self.assertIn('type: "openapi"', api[0])
        self.assertTrue([d for d in documents if 'name: "oi-ledger-queue"' in d and 'type: "mq"' in d])
        # A connection through it is a use of it, not an API of its own.
        self.assertFalse([d for d in documents if 'name: "int-lending-web-api"' in d])

    def test_the_engine_s_mermaid_reads_back_through_the_interface(self) -> None:
        views = {v.view_id: v for v in self.views}
        text = render(resolve(self.model, views["integration-architecture"]), Palette(None), self.model)
        self.assertIn("OI_LEDGER_QUEUE --- SYS_CORE_LEDGER", text)
        doc, _ = sketch_from_mermaid(text)
        offered = {r["offered_interface_id"]: r["system_id"] for r in doc["offered_interfaces"]}
        self.assertEqual(offered["OI-LEDGER-QUEUE"], "SYS-CORE-LEDGER")
        lines = {(r["source_system_id"], r["target_system_id"], r.get("offered_interface_id"))
                 for r in doc["interfaces"]}
        self.assertIn(("SYS-AUTH-SWITCH", "SYS-CORE-LEDGER", "OI-LEDGER-QUEUE"), lines)

    def test_the_plantuml_marks_the_owner_s_line_and_the_interface(self) -> None:
        views = {v.view_id: v for v in self.views}
        text = render_plantuml(resolve(self.model, views["integration-architecture"]), self.model)
        self.assertIn('Rel(OI_LEDGER_QUEUE, SYS_CORE_LEDGER, "offered by")', text)
        self.assertIn('field="system_id"', text)
        self.assertIn('offered_interface_id="OI-LEDGER-QUEUE"', text)
        doc, _ = sketch_from_plantuml(text)
        back = {r["interface_id"]: r for r in doc["interfaces"]}["INT-AUTH-LEDGER"]
        self.assertEqual((back["target_system_id"], back["offered_interface_id"]),
                         ("SYS-CORE-LEDGER", "OI-LEDGER-QUEUE"))


class TestTheApp(unittest.TestCase):
    """What the server tells the app: a system dropped on an interface
    another system offers is a connection through it, the way the traffic
    runs; a connection between two systems lists what it could go through;
    the panels say what a system offers and what uses an interface; and an
    interface is not moved into a boundary of its own."""

    @classmethod
    def setUpClass(cls) -> None:
        from _fixture import seeded_root

        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = seeded_root()
        cls.server = server_module

    def test_a_system_dropped_on_an_interface_connects_through_it(self) -> None:
        options = self.server.api_connect_options({"from": ["SYS-CRM"], "to": ["OI-CARDSVC-API"]}, None)["options"]
        through = options[0]
        self.assertEqual((through["kind"], through["from"], through["to"], through["door"]["id"]),
                         ("through", "SYS-CRM", "SYS-CARDSVC-API", "OI-CARDSVC-API"))
        self.assertEqual((through["door"]["protocol"], through["exists"]), ("HTTPS", False))
        # The IVR already goes through it, and is said to.
        options = self.server.api_connect_options({"from": ["SYS-IVR"], "to": ["OI-CARDSVC-API"]}, None)["options"]
        self.assertEqual((options[0]["exists"], options[0]["existing"]), (True, ["INT-IVR-CARDSVC"]))

    def test_a_connection_between_two_systems_lists_what_it_could_go_through(self) -> None:
        options = self.server.api_connect_options({"from": ["SYS-CRM"], "to": ["SYS-CORE-LEDGER"]}, None)["options"]
        calls = {(o["from"], o["to"]): o for o in options if o["kind"] == "interface"}
        self.assertEqual([d["id"] for d in calls[("SYS-CRM", "SYS-CORE-LEDGER")]["offered"]], ["OI-LEDGER-QUEUE"])
        self.assertEqual(calls[("SYS-CORE-LEDGER", "SYS-CRM")]["offered"], [])

    def test_the_panels_say_what_is_offered_and_what_uses_it(self) -> None:
        ledger = self.server.api_entity({"id": ["SYS-CORE-LEDGER"]}, None)["related"]
        self.assertIn(("offers", "out", "OI-LEDGER-QUEUE"), {(r["relation"], r["direction"], r["otherId"]) for r in ledger})
        queue = self.server.api_entity({"id": ["OI-LEDGER-QUEUE"]}, None)["related"]
        used = sorted(r["otherId"] for r in queue if r["relation"] == "through")
        self.assertEqual(used, ["SYS-AUTH-SWITCH", "SYS-CARDSVC-API", "SYS-COLLECT-API", "SYS-LENDING-API",
                                "SYS-PAYMENT-GW", "SYS-REWARDS-WORKER"])
        self.assertIn(("offers", "in", "SYS-CORE-LEDGER"), {(r["relation"], r["direction"], r["otherId"]) for r in queue})

    def test_an_interface_moves_with_its_system(self) -> None:
        from terrane import regroup
        from terrane.query import load_views

        model = seeded_model()
        plan = regroup.plan(model, load_views(REPO / "30_VIEWS"), "OI-LEDGER-QUEUE", [("system_category", "Channel")])
        self.assertEqual(plan.changes, [])
        self.assertEqual(plan.blocked, "Core Ledger request queue is drawn on Core Card Ledger, the system that "
                                       "offers it: move the system, and it moves with it.")


class TestHandSketches(unittest.TestCase):
    def test_a_sketch_reads_the_interface_and_the_lines_through_it(self) -> None:
        text = """flowchart LR
  web[Lending web] --> api(Lending API)
  app[Lending app] -->|HTTPS| api
  api --- svc[Lending service]
  class api s_offered_interfaces__default
"""
        doc, _ = sketch_from_mermaid(text)
        self.assertEqual(doc["offered_interfaces"], [{"offered_interface_id": "OI-API", "name": "Lending API",
                                                      "system_id": "SYS-SVC"}])
        lines = {(r["source_system_id"], r["target_system_id"], r.get("offered_interface_id"))
                 for r in doc["interfaces"]}
        self.assertEqual(lines, {("SYS-WEB", "SYS-SVC", "OI-API"), ("SYS-APP", "SYS-SVC", "OI-API")})

    def test_an_interface_nothing_offers_is_said_and_left_out(self) -> None:
        text = """flowchart LR
  web[Web] --> api(Orphan API)
  app[App] --> api
  class api s_offered_interfaces__default
"""
        doc, notes = sketch_from_mermaid(text)
        self.assertNotIn("offered_interfaces", doc)
        self.assertNotIn("interfaces", doc)
        self.assertIn("api: an offered interface no system offers; left out, with its lines", notes)


if __name__ == "__main__":
    unittest.main()
