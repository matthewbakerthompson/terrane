"""A C4-PlantUML diagram read as a sketch: brought to the form the C4
reader takes, then read as a Mermaid C4 diagram is."""

from __future__ import annotations

import unittest

import terrane
from terrane.plantuml_import import PlantumlError, sketch_from_plantuml, to_mermaid
from terrane.quick import check_sketch, read_any

from _fixture import REPO

SAMPLE = (REPO / "90_EXAMPLE" / "quick" / "sample.puml").read_text(encoding="utf-8")


class TestToMermaid(unittest.TestCase):
    def test_the_directives_go_and_the_include_names_the_kind(self) -> None:
        mermaid, notes = to_mermaid(SAMPLE)
        lines = mermaid.splitlines()
        self.assertEqual(lines[0], "C4Container")
        self.assertEqual(notes, [])
        text = "\n".join(lines)
        for gone in ("@startuml", "!include", "LAYOUT_WITH_LEGEND", "AddElementTag", "SHOW_LEGEND", "Lay_R",
                     "block comment", "' A C4"):
            self.assertNotIn(gone, text)
        self.assertIn("title Card payments, in C4-PlantUML", text)

    def test_named_arguments_take_their_slots_and_tags_go(self) -> None:
        mermaid, _ = to_mermaid(SAMPLE)
        self.assertIn('Person_Ext(merchant, "Merchant", "Presents a card for payment.")', mermaid)
        self.assertIn('Container(portal, "Merchant portal", "React", "Where a merchant sees settlements.")', mermaid)
        self.assertIn('Container(fraud, "Fraud scoring", "Python", "Scores a transaction in under 50 ms.")', mermaid)
        self.assertIn('Rel(portal, ledger, "Reads", "JDBC")', mermaid)

    def test_a_statement_over_two_lines_is_one_and_an_index_is_dropped(self) -> None:
        mermaid, _ = to_mermaid(SAMPLE)
        self.assertIn('Rel_D(switch, events, "Publishes", "Kafka")', mermaid)
        mermaid, _ = to_mermaid('@startuml\n!include C4_Dynamic.puml\nSystem(a, "A")\nSystem(b, "B")\n'
                                'RelIndex(1, a, b, "Calls")\n@enduml\n')
        self.assertEqual(mermaid.splitlines()[0], "C4Dynamic")
        self.assertIn('Rel(a, b, "Calls")', mermaid)

    def test_legends_and_notes_are_skipped(self) -> None:
        mermaid, _ = to_mermaid('@startuml\n!include C4_Context.puml\nlegend right\n  Person(x, "no")\nendlegend\n'
                                'note as N1\n  Rel(x, y)\nend note\nSystem(a, "A")\n@enduml\n')
        self.assertNotIn("Person(x", mermaid)
        self.assertNotIn("Rel(x", mermaid)
        self.assertIn('System(a, "A")', mermaid)


class TestSketch(unittest.TestCase):
    def test_the_sample_reads_as_the_mermaid_c4_would(self) -> None:
        doc, notes = sketch_from_plantuml(SAMPLE)
        check_sketch(doc)
        self.assertEqual(doc["model"]["name"], "Card payments, in C4-PlantUML")
        self.assertEqual([a["actor_id"] for a in doc["actors"]], ["ACT-CARDHOLDER", "ACT-MERCHANT"])
        self.assertEqual([s["system_id"] for s in doc["systems"]],
                         ["SYS-SCHEME", "SYS-SWITCH", "SYS-FRAUD", "SYS-EVENTS", "SYS-PORTAL"])
        self.assertEqual(doc["systems"][0]["hosting"], "External")
        self.assertEqual([s.get("company_domain") for s in doc["systems"]],
                         [None, "Payments", "Payments", "Payments", None])
        self.assertEqual(doc["data_assets"][0]["data_asset_id"], "DA-LEDGER")
        self.assertIn("Built with Java, Kubernetes.", doc["systems"][1]["description"])
        self.assertIn("A queue.", doc["systems"][3]["description"])
        interfaces = {(i["source_system_id"], i["target_system_id"]): i for i in doc["interfaces"]}
        self.assertEqual(interfaces[("SYS-SWITCH", "SYS-FRAUD")]["protocol"], "gRPC")
        # Rel_Back(switch, scheme): the scheme is the one acting on the switch.
        self.assertIn(("SYS-SCHEME", "SYS-SWITCH"), interfaces)
        self.assertEqual(interfaces[("SYS-SWITCH", "SYS-EVENTS")]["name"], "Publishes")
        reads = sorted((r["system_id"], r["operation"]) for r in doc["relations"]["system_reads_writes"])
        self.assertEqual(reads, [("SYS-PORTAL", "Read"), ("SYS-SWITCH", "ReadWrite")])  # "Posts" says neither, so both
        self.assertTrue(any("from the PlantUML" in n for n in notes), notes)

    def test_a_rel_tagged_with_a_connection_kind_is_of_that_kind(self) -> None:
        text = ('@startuml\n!include <C4/C4_Context>\nSystem(a, "Auth")\nSystem(b, "Fraud")\nSystem(c, "Ledger")\n'
                'Rel(a, b, "Score", $tags="api-call")\nRel(a, c, "Post", "MQ", $tags="carrier-pigeon")\n'
                'Rel(b, c, "Keep", "PostgreSQL", $tags="own-datastore")\n@enduml\n')
        doc, notes = sketch_from_plantuml(text, name="tags")
        by_ends = {(i["source_system_id"], i["target_system_id"]): i for i in doc["interfaces"]}
        scored = by_ends[("SYS-A", "SYS-B")]
        self.assertEqual((scored["name"], scored["integration_style"], scored["protocol"], scored["auth_method"]),
                         ("Score", "Request-response", "HTTPS", "OAuth2"))
        # A tag naming no kind is a styling tag, left alone without a word; the protocol still says its kind.
        posted = by_ends[("SYS-A", "SYS-C")]
        self.assertEqual((posted["protocol"], posted["integration_style"]), ("MQ", "Request-response"))
        self.assertNotIn("auth_method", posted)
        self.assertFalse(any("carrier-pigeon" in n for n in notes), notes)
        # A protocol the Rel said that the kind carries stays; the proposal's first is for a Rel that said none.
        kept = next(i for i in doc["interfaces"] if i["source_system_id"] == "SYS-B")
        self.assertEqual((kept["protocol"], kept["integration_style"]), ("PostgreSQL", "Request-response"))

    def test_the_exports_marks_outrank_the_picture(self) -> None:
        text = ('@startuml\n!include C4_Context.puml\nBoundary(b, "Role") {\n'
                '  Person(ACT_AGENT, "Agent", "Takes the calls.")\n'
                "  ' aac ACT_AGENT: company_domain=\"Servicing\"; actor_kind=\"Role\"; internal=\"Yes\"\n"
                '  System_Ext(SYS_CRM, "CRM", "Case management. Built with Microsoft.")\n'
                "  ' aac SYS_CRM: company_domain=\"Servicing\"; hosting=\"SaaS\"; technology=\"Microsoft\"\n"
                '  System(SYS_PLAIN, "Plain", "Nothing said under it.")\n'
                '}\nRel(ACT_AGENT, SYS_CRM, "Works cases")\n'
                'Rel(SYS_PLAIN, SYS_CRM, "Posts cases", "HTTPS")\n'
                "' aac rel: source=\"SYS_PLAIN\"; target=\"SYS_CRM\"; label=\"Posts cases\"; interface_id=\"INT-CASES\"; "
                "kind=\"api-call\"; auth_method=\"HMAC\"; patterns=\"api-front-door;observed-service\"\n"
                'Rel(SYS_CRM, SYS_PLAIN, "Replies")\n@enduml\n')
        doc, notes = sketch_from_plantuml(text, name="marked")
        agent = next(a for a in doc["actors"] if a["actor_id"] == "ACT-AGENT")
        self.assertEqual((agent["company_domain"], agent["actor_kind"], agent["internal"]), ("Servicing", "Role", "Yes"))
        crm = next(s for s in doc["systems"] if s["system_id"] == "SYS-CRM")
        self.assertEqual((crm["company_domain"], crm["hosting"], crm["description"]),
                         ("Servicing", "SaaS", "Case management."))
        # An element with nothing under it reads as the picture says: the boundary is its domain.
        plain = next(s for s in doc["systems"] if s["system_id"] == "SYS-PLAIN")
        self.assertEqual(plain["company_domain"], "Role")
        # A Rel with an id under it is that interface; one without is minted from its ends.
        self.assertEqual([i["interface_id"] for i in doc["interfaces"]], ["INT-CASES", "INT-CRM-PLAIN"])
        # The record's own values stand over the kind's proposal (api-call proposes OAuth2).
        cases = doc["interfaces"][0]
        self.assertEqual((cases["auth_method"], cases["patterns"], cases["protocol"]),
                         ("HMAC", ["api-front-door", "observed-service"], "HTTPS"))
        self.assertFalse(any("aac" in n for n in notes), notes)

    def test_a_rel_re_tagged_by_hand_takes_the_new_kinds_proposal(self) -> None:
        text = ('@startuml\n!include C4_Context.puml\nSystem(SYS_A, "A")\nSystem(SYS_B, "B")\n'
                'Rel(SYS_A, SYS_B, "Posts journals", "MQ", $tags="api-call")\n'
                "' aac rel: source=\"SYS_A\"; target=\"SYS_B\"; label=\"Posts journals\"; interface_id=\"INT-J\"; "
                "kind=\"queued-request\"; auth_method=\"IAM\"\n@enduml\n")
        doc, _notes = sketch_from_plantuml(text, name="retagged")
        journals = doc["interfaces"][0]
        # The tag says api-call where the record was queued-request: the new kind proposes, the pins do not hold.
        self.assertEqual(journals["interface_id"], "INT-J")
        self.assertEqual(journals["integration_style"], "Request-response")
        self.assertNotEqual(journals.get("auth_method"), "IAM")

    def test_what_is_not_c4_plantuml_is_refused(self) -> None:
        with self.assertRaises(PlantumlError):
            sketch_from_plantuml("flowchart LR\n  A --> B\n")
        with self.assertRaises(PlantumlError):
            sketch_from_plantuml("@startuml\nskinparam monochrome true\n@enduml\n")

    def test_the_door_takes_the_file_by_its_suffix(self) -> None:
        doc, notes = read_any(REPO / "90_EXAMPLE" / "quick" / "sample.puml")
        self.assertEqual(doc["model"]["name"], "Card payments, in C4-PlantUML")
        drawings = terrane.diagrams(str(REPO / "90_EXAMPLE" / "quick" / "sample.puml"), date="2026-10-17")
        self.assertIn("imported", drawings)
        self.assertIn("Authorization switch", drawings["imported"].svg)


if __name__ == "__main__":
    unittest.main()
