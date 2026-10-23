"""A Mermaid flowchart read as a sketch.

The on-ramp for the diagrams people already have: nodes become things of
the kind their shape hints at, arrows the relation two such things have
here, subgraphs the domain. The tests hold the sample in `90_EXAMPLE/quick`
to what it should read as -- four systems, a data asset, an actor, a
capability, the connections as interfaces, reads and writes, uses and
realizes, the domains from the subgraphs, the inline and bar label
spellings, chains and `&` groups -- that the sketch it writes draws, that
styling lines are skipped, and that a file with no header is refused with
its line.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.mermaid_import import MermaidError, sketch_from_mermaid  # noqa: E402
from terrane.quick import draw_sketch, sketch_from_mermaid_file  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[2] / "90_EXAMPLE" / "quick" / "sample.mmd"
C4 = SAMPLE.with_name("sample-c4.mmd")
SEQUENCE = SAMPLE.with_name("sample-sequence.mmd")
MARKDOWN = SAMPLE.with_name("sample.md")


class TestRead(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc, cls.notes = sketch_from_mermaid(SAMPLE.read_text(encoding="utf-8"), name="Sample")

    def test_the_things_and_their_kinds(self) -> None:
        self.assertEqual([s["system_id"] for s in self.doc["systems"]], ["SYS-WEB", "SYS-MOBILE", "SYS-API", "SYS-BUS"])
        # The subgraph is the domain of everything in it, whatever its kind.
        self.assertEqual(self.doc["data_assets"],
                         [{"data_asset_id": "DA-LEDGER", "name": "Ledger", "company_domain": "Core banking"}])
        self.assertEqual(self.doc["actors"], [{"actor_id": "ACT-CUST", "name": "Customer"}])
        self.assertEqual(self.doc["capabilities"],
                         [{"capability_id": "CAP-FRAUD", "name": "Fraud scoring", "company_domain": "Core banking"}])
        by_id = {s["system_id"]: s for s in self.doc["systems"]}
        self.assertEqual(by_id["SYS-WEB"]["name"], "Web portal")
        self.assertEqual(by_id["SYS-WEB"]["company_domain"], "Channels")
        self.assertEqual(by_id["SYS-API"]["company_domain"], "Core banking")
        self.assertNotIn("company_domain", by_id["SYS-BUS"])

    def test_the_connections_and_both_label_spellings(self) -> None:
        interfaces = {i["interface_id"]: i for i in self.doc["interfaces"]}
        self.assertEqual(set(interfaces), {"INT-WEB-API", "INT-MOBILE-API", "INT-API-BUS"})
        self.assertEqual(interfaces["INT-WEB-API"]["protocol"], "HTTPS")
        self.assertEqual(interfaces["INT-API-BUS"]["protocol"], "events")
        relations = self.doc["relations"]
        self.assertEqual(relations["system_reads_writes"],
                         [{"system_id": "SYS-API", "data_asset_id": "DA-LEDGER", "operation": "ReadWrite"}])
        self.assertEqual(relations["system_realizes_capability"], [{"system_id": "SYS-API", "capability_id": "CAP-FRAUD"}])
        self.assertEqual(sorted(r["system_id"] for r in relations["actor_uses_system"]), ["SYS-MOBILE", "SYS-WEB"])
        self.assertTrue(all(r["interaction"] == "uses" for r in relations["actor_uses_system"]))

    def test_the_view_and_the_notes(self) -> None:
        view = self.doc["views"][0]
        self.assertEqual((view["view_id"], view["layout"], view["group_by"]), ("imported", "LR", "company_domain"))
        self.assertEqual(sorted(e["via"] for e in view["edges"]),
                         sorted(["interfaces", "system_reads_writes", "actor_uses_system", "system_realizes_capability"]))
        self.assertIn("7 connection(s)", self.notes[0])
        # Styling and interaction lines are skipped without a word.
        self.assertFalse(any("left out" in n for n in self.notes), self.notes)
        # A label with no field to go to is said, not dropped in silence.
        self.assertTrue(any("gRPC" in n and "not kept" in n for n in self.notes), self.notes)

    def test_words_on_an_arrow_are_the_name_and_a_code_the_protocol(self) -> None:
        text = ("flowchart LR\n  auth[Authorization switch] -->|Posts the authorization| ledger[Card ledger]\n"
                "  auth -->|gRPC| fraud[Fraud scoring]\n  auth <-->|ISO 8583| scheme[Card scheme]\n")
        doc, _notes = sketch_from_mermaid(text, name="words")
        by_target = {i["target_system_id"]: i for i in doc["interfaces"] if i["source_system_id"] == "SYS-AUTH"}
        self.assertEqual(by_target["SYS-LEDGER"].get("name"), "Posts the authorization")
        self.assertNotIn("protocol", by_target["SYS-LEDGER"])
        self.assertEqual(by_target["SYS-FRAUD"].get("protocol"), "gRPC")
        self.assertNotIn("name", by_target["SYS-FRAUD"])
        # A code with a space and digits is a code still, both ways round the two-headed arrow.
        self.assertEqual(by_target["SYS-SCHEME"].get("protocol"), "ISO 8583")
        back = next(i for i in doc["interfaces"] if i["source_system_id"] == "SYS-SCHEME")
        self.assertEqual(back.get("protocol"), "ISO 8583")

    def test_an_arrow_that_names_a_connection_kind_is_of_that_kind(self) -> None:
        text = ("flowchart LR\n"
                "  auth[Authorization switch] -->|API call| fraud[Fraud scoring]\n"
                "  auth -->|MQ| ledger[Card ledger]\n"
                "  auth -->|Scores| other[Other]\n")
        doc, notes = sketch_from_mermaid(text, name="kinds")
        by_target = {i["target_system_id"]: i for i in doc["interfaces"]}
        named = by_target["SYS-FRAUD"]
        # The kind's proposal: its style, first protocol and authentication; the words that named the kind
        # stay as the connection's name, as in every reader.
        self.assertEqual((named["integration_style"], named["protocol"], named["auth_method"]),
                         ("Request-response", "HTTPS", "OAuth2"))
        self.assertEqual(named["patterns"], ["api-front-door"])
        self.assertEqual(named["name"], "API call")
        # A protocol one kind alone carries gives its style, and stays the protocol it said.
        queued = by_target["SYS-LEDGER"]
        self.assertEqual((queued["protocol"], queued["integration_style"]), ("MQ", "Request-response"))
        self.assertNotIn("auth_method", queued)
        # A single word that names no kind is a code, so a protocol, as before.
        self.assertEqual(by_target["SYS-OTHER"].get("protocol"), "Scores")
        self.assertNotIn("integration_style", by_target["SYS-OTHER"])
        self.assertIn("1 connection(s) of the kind api-call, from the words on the arrows; proposed as the kind "
                      "proposes, Request-response over HTTPS", notes)
        self.assertIn("1 arrow(s) saying a protocol only the kind queued-request carries; read as Request-response", notes)

    def test_a_hop_whose_words_name_a_connection_kind_is_of_that_kind(self) -> None:
        text = ("sequenceDiagram\n  title Kinds\n  participant a as Auth\n  participant b as Fraud\n"
                "  a->>b: API call\n  a-)b: Return the scores\n")
        doc, notes = sketch_from_mermaid(text, name="kinds")
        self.assertEqual(len(doc["interfaces"]), 2)
        named = next(i for i in doc["interfaces"] if "auth_method" in i)
        # The words named the kind outright: its whole proposal, the arrow's style yielding to the kind's.
        self.assertEqual((named["integration_style"], named["protocol"], named["auth_method"]),
                         ("Request-response", "HTTPS", "OAuth2"))
        self.assertNotIn("name", named)
        other = next(i for i in doc["interfaces"] if "auth_method" not in i)
        self.assertEqual((other["name"], other["integration_style"]), ("Return the scores", "Event"))
        self.assertIn("1 hop(s) of the kind api-call, from the words on the arrows; proposed as the kind proposes, "
                      "Request-response over HTTPS", notes)

    def test_direction_and_refusals(self) -> None:
        doc, _ = sketch_from_mermaid("graph TD\n  a --> b\n")
        self.assertEqual(doc["views"][0]["layout"], "TB")
        self.assertNotIn("group_by", doc["views"][0])
        with self.assertRaises(MermaidError) as caught:
            sketch_from_mermaid("classDiagram\n  A <|-- B\n")
        self.assertIn("line 1", str(caught.exception))
        with self.assertRaises(MermaidError):
            sketch_from_mermaid("%% only a comment\n")

    def test_what_cannot_be_read_is_said(self) -> None:
        _doc, notes = sketch_from_mermaid("flowchart LR\n  a --> b\n  ???\n")
        self.assertTrue(any("line 3" in n and "left out" in n for n in notes), notes)


class TestC4(unittest.TestCase):
    """A C4 container diagram: a person an actor, a container a system, a
    database a data asset, the boundary the domain, a Rel the connection
    with its technology as the protocol, Rel_Back the other way round."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.doc, cls.notes = sketch_from_mermaid(C4.read_text(encoding="utf-8"), name="Sample")

    def test_the_elements_and_what_each_carries(self) -> None:
        self.assertEqual(self.doc["model"]["name"], "Internet banking, as a team drew it")
        self.assertEqual(self.doc["actors"], [{
            "actor_id": "ACT-CUSTOMER", "name": "Personal Banking Customer",
            "description": "A customer of the bank, with personal bank accounts.", "actor_kind": "Person",
            "internal": "Yes"}])
        self.assertEqual([s["system_id"] for s in self.doc["systems"]],
                         ["SYS-WEB", "SYS-SPA", "SYS-MOBILE", "SYS-API", "SYS-EMAIL", "SYS-MAINFRAME"])
        by_id = {s["system_id"]: s for s in self.doc["systems"]}
        self.assertEqual(by_id["SYS-WEB"]["company_domain"], "Internet Banking")
        self.assertTrue(by_id["SYS-WEB"]["description"].endswith("Built with Java, Spring MVC."))
        # A System takes no technology: its third argument is the description.
        self.assertEqual(by_id["SYS-EMAIL"]["description"], "The internal Microsoft Exchange system.")
        self.assertEqual(by_id["SYS-EMAIL"]["hosting"], "External")
        self.assertNotIn("company_domain", by_id["SYS-EMAIL"])
        self.assertEqual(self.doc["data_assets"], [{
            "data_asset_id": "DA-DB", "name": "Database",
            "description": "Stores user registration information, hashed auth credentials, access logs, etc. "
                           "Built with SQL Database.",
            "company_domain": "Internet Banking"}])

    def test_the_relations(self) -> None:
        interfaces = {i["interface_id"]: i for i in self.doc["interfaces"]}
        self.assertEqual(set(interfaces), {"INT-WEB-SPA", "INT-SPA-API", "INT-MOBILE-API", "INT-API-EMAIL",
                                           "INT-API-MAINFRAME"})
        self.assertEqual(interfaces["INT-WEB-SPA"]["name"], "Delivers")
        self.assertNotIn("protocol", interfaces["INT-WEB-SPA"])
        self.assertEqual((interfaces["INT-SPA-API"]["name"], interfaces["INT-SPA-API"]["protocol"]),
                         ("Uses", "async, JSON/HTTPS"))
        self.assertEqual(interfaces["INT-API-EMAIL"]["protocol"], "sync, SMTP")
        relations = self.doc["relations"]
        self.assertEqual(len(relations["actor_uses_system"]), 3)
        self.assertTrue(all(r["interaction"] == "Uses" for r in relations["actor_uses_system"]))
        # Rel_Back(db, api, ...) is the API acting on the database.
        self.assertEqual(relations["system_reads_writes"],
                         [{"system_id": "SYS-API", "data_asset_id": "DA-DB", "operation": "ReadWrite"}])

    def test_the_view_and_the_notes(self) -> None:
        view = self.doc["views"][0]
        self.assertEqual((view["layout"], view["group_by"]), ("TB", "company_domain"))
        self.assertIn("C4Container", view["description"])
        self.assertIn("9 connection(s)", self.notes[0])
        # The Update... styling statements are skipped without a word.
        self.assertFalse(any("left out" in n for n in self.notes), self.notes)

    def test_the_small_print(self) -> None:
        doc, notes = sketch_from_mermaid(
            "C4Context\n  Person_Ext(p, \"Partner\")\n  SystemDb(d, \"Store\")\n  System(s, \"Service\")\n"
            "  Rel(s, d, \"Reads from\")\n  Rel(s, d, \"Writes to\", \"JDBC\")\n  BiRel(s, t, \"Syncs\")\n"
            "  Rel(p, s, \"Calls\")\n")
        self.assertEqual(doc["actors"][0]["internal"], "No")
        self.assertEqual([r["operation"] for r in doc["relations"]["system_reads_writes"]], ["Read", "Write"])
        # BiRel is two interfaces; an end no statement declared is said and read as a system.
        self.assertEqual({i["interface_id"] for i in doc["interfaces"]}, {"INT-S-T", "INT-T-S"})
        self.assertTrue(any("no statement declared" in n and "'t'" in n for n in notes), notes)
        self.assertEqual(doc["relations"]["actor_uses_system"][0]["interaction"], "Calls")

    def test_the_sketch_draws(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-c4-"))
        source = folder / "sample-c4.mmd"
        source.write_text(C4.read_text(encoding="utf-8"), encoding="utf-8")
        sketch, _notes = sketch_from_mermaid_file(source)
        written, notes = draw_sketch(sketch, folder / "out")
        self.assertEqual([p.name for p in written], ["sample-c4--imported.svg"])
        root = ET.fromstring(written[0].read_text(encoding="utf-8"))
        nodes = {el.get("data-id") for el in root.iter() if el.get("class") == "node"}
        self.assertEqual(len(nodes), 8, nodes)
        self.assertEqual(len([el for el in root.iter() if el.get("class") == "edge"]), 9)


class TestSequence(unittest.TestCase):
    """A sequence diagram is a flow: participants as systems, an actor as
    the actor that starts it, each message between systems a step, the
    dotted reply the step's request-response, an open arrow an event."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.doc, cls.notes = sketch_from_mermaid(SEQUENCE.read_text(encoding="utf-8"), name="Sample")

    def test_the_participants(self) -> None:
        self.assertEqual(self.doc["actors"], [{"actor_id": "ACT-MERCHANT", "name": "Merchant", "actor_kind": "Person"}])
        self.assertEqual([(s["system_id"], s["name"]) for s in self.doc["systems"]],
                         [("SYS-AUTH", "Authorization switch"), ("SYS-FRAUD", "Fraud scoring"), ("SYS-LEDGER", "Card ledger")])

    def test_the_steps_and_their_styles(self) -> None:
        interfaces = {i["interface_id"]: i for i in self.doc["interfaces"]}
        self.assertEqual(list(interfaces), ["INT-AUTH-FRAUD", "INT-AUTH-LEDGER", "INT-AUTH-LEDGER-2"])
        self.assertEqual((interfaces["INT-AUTH-FRAUD"]["name"], interfaces["INT-AUTH-FRAUD"]["integration_style"]),
                         ("Score the transaction", "Request-response"))
        self.assertEqual(interfaces["INT-AUTH-LEDGER-2"]["integration_style"], "Event")
        steps = self.doc["relations"]["flow_step"]
        self.assertEqual([(s["interface_id"], s["sequence"]) for s in steps],
                         [("INT-AUTH-FRAUD", 10), ("INT-AUTH-LEDGER", 20), ("INT-AUTH-LEDGER-2", 30)])
        self.assertTrue(all(s["flow_id"] == "FLOW-CARD-AUTHORIZATION-AS-DRAWN" for s in steps))

    def test_the_flow_and_what_the_actor_did(self) -> None:
        flow = self.doc["flows"][0]
        self.assertEqual(flow["name"], "Card authorization, as drawn")
        self.assertEqual(flow["trigger"], "Presents a transaction")
        self.assertEqual(flow["target_latency"], "under 500ms end to end")
        self.assertIn("circuit breaker", flow["description"])
        self.assertEqual(self.doc["relations"]["actor_uses_system"],
                         [{"actor_id": "ACT-MERCHANT", "system_id": "SYS-AUTH", "interaction": "Presents a transaction"}])
        self.assertEqual(self.doc["views"], ["system-context", "application-landscape"])
        self.assertIn("3 step(s)", self.notes[0])
        # The block keywords, the activations, autonumber and the decline
        # shown to the merchant are read through without a word.
        self.assertEqual(len(self.notes), 1, self.notes)

    def test_the_flow_draws_as_a_sequence_diagram(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-seq-"))
        source = folder / "sample-sequence.mmd"
        source.write_text(SEQUENCE.read_text(encoding="utf-8"), encoding="utf-8")
        sketch, _notes = sketch_from_mermaid_file(source)
        written, notes = draw_sketch(sketch, folder / "out")
        names = [p.name for p in written]
        self.assertIn("sample-sequence--FLOW-CARD-AUTHORIZATION-AS-DRAWN.svg", names)
        self.assertIn("sample-sequence--system-context.svg", names)
        svg = (folder / "out" / "sample-sequence--FLOW-CARD-AUTHORIZATION-AS-DRAWN.svg").read_text(encoding="utf-8")
        for word in ("Merchant", "Fraud scoring", "Score the transaction", "under 500ms end to end"):
            self.assertIn(word, svg)

    def test_the_small_print(self) -> None:
        doc, notes = sketch_from_mermaid("sequenceDiagram\n  a->>b: one\n  b-->>c: stray\n  a->b: two\n")
        self.assertEqual(len(doc["relations"]["flow_step"]), 3)
        self.assertEqual(doc["flows"][0]["flow_id"], "FLOW-IMPORTED")
        self.assertTrue(any("answers no step before it" in n for n in notes), notes)
        _doc, notes = sketch_from_mermaid("sequenceDiagram\n  actor p as P\n  participant s as S\n  p->>s: asks\n")
        self.assertTrue(any("no steps" in n for n in notes), notes)


class TestMarkdown(unittest.TestCase):
    """Mermaid blocks inside Markdown, read together: the records merged by
    id, one view per block named after its heading, the flow from the
    sequence diagram, a block that cannot be read said and left out."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.doc, cls.notes = sketch_from_mermaid(MARKDOWN.read_text(encoding="utf-8"), name="Sample")

    def test_the_records_are_merged_by_id(self) -> None:
        self.assertEqual(self.doc["model"]["name"], "Card payments, as the team documented it")
        systems = {s["system_id"]: s for s in self.doc["systems"]}
        # The switch is drawn in the flowchart and named in the sequence
        # diagram: one record, with the flowchart's domain kept.
        self.assertEqual(sorted(systems), ["SYS-AUTH", "SYS-FRAUD", "SYS-MOBILE", "SYS-STATEMENTS"])
        self.assertEqual(systems["SYS-AUTH"]["company_domain"], "Core banking")
        self.assertNotIn("company_domain", systems["SYS-FRAUD"])
        self.assertEqual([d["data_asset_id"] for d in self.doc["data_assets"]], ["DA-LEDGER"])
        self.assertEqual([a["actor_id"] for a in self.doc["actors"]], ["ACT-MERCHANT"])

    def test_the_views_the_flow_and_the_notes(self) -> None:
        views = self.doc["views"]
        self.assertEqual([v["view_id"] for v in views if isinstance(v, dict)], ["imported-1"])
        self.assertEqual(views[0]["title"], "Where things run")
        # A block's view draws what the block drew: fraud scoring is named
        # only in the sequence diagram, so the flowchart's view leaves it out.
        self.assertEqual({inc["type"]: set(inc["where"]["id_in"]) for inc in views[0]["scope"]["include"]},
                         {"systems": {"SYS-MOBILE", "SYS-AUTH", "SYS-STATEMENTS"}, "data_assets": {"DA-LEDGER"}})
        self.assertEqual([v for v in views if isinstance(v, str)], ["system-context", "application-landscape"])
        self.assertEqual(self.doc["flows"][0]["flow_id"], "FLOW-HOW-AN-AUTHORIZATION-GOES")
        self.assertEqual(self.doc["flows"][0]["target_latency"], "under 500ms end to end")
        interfaces = {i["interface_id"] for i in self.doc["interfaces"]}
        self.assertEqual(interfaces, {"INT-MOBILE-STATEMENTS", "INT-AUTH-FRAUD"})
        # The ledger is a cylinder in the flowchart, so it is a data asset in
        # the sequence diagram too: the arrows at it are reads and writes,
        # not interfaces, and the flow has the one step between systems.
        self.assertEqual(len(self.doc["relations"]["system_reads_writes"]), 2)
        self.assertEqual([s["interface_id"] for s in self.doc["relations"]["flow_step"]], ["INT-AUTH-FRAUD"])
        self.assertTrue(any(n.startswith("block 3") and "left out" in n for n in self.notes), self.notes)
        self.assertTrue(any(n.startswith("block 1:") for n in self.notes) and
                        any(n.startswith("block 2:") for n in self.notes), self.notes)

    def test_a_markdown_file_with_no_block_is_refused(self) -> None:
        with self.assertRaises(MermaidError):
            sketch_from_mermaid("# Notes\n\nNo diagram here, only ```python\nprint(1)\n```\n")

    def test_the_sketch_draws_every_view_and_the_flow(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-md-"))
        source = folder / "sample.md"
        source.write_text(MARKDOWN.read_text(encoding="utf-8"), encoding="utf-8")
        sketch, _notes = sketch_from_mermaid_file(source)
        written, notes = draw_sketch(sketch, folder / "out")
        names = sorted(p.name for p in written)
        self.assertIn("sample--imported-1.svg", names)
        self.assertIn("sample--system-context.svg", names)
        self.assertIn("sample--FLOW-HOW-AN-AUTHORIZATION-GOES.svg", names)


class TestWriteAndDraw(unittest.TestCase):
    def test_the_sketch_written_beside_the_flowchart_draws(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-mm-"))
        source = folder / "sample.mmd"
        source.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        sketch, notes = sketch_from_mermaid_file(source)
        self.assertEqual(sketch, folder / "sample.yaml")
        text = sketch.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Read from sample.mmd"), text[:80])
        self.assertNotIn("# #", text)
        written, draw_notes = draw_sketch(sketch, folder / "out")
        self.assertEqual([p.name for p in written], ["sample--imported.svg"])
        root = ET.fromstring(written[0].read_text(encoding="utf-8"))
        nodes = {el.get("data-id") for el in root.iter() if el.get("class") == "node"}
        self.assertEqual(nodes, {"SYS-WEB", "SYS-MOBILE", "SYS-API", "SYS-BUS", "DA-LEDGER", "ACT-CUST", "CAP-FRAUD"})
        edges = [el for el in root.iter() if el.get("class") == "edge"]
        self.assertEqual(len(edges), 7)


if __name__ == "__main__":
    unittest.main()
