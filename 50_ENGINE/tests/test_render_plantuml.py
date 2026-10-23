"""The C4-PlantUML export: every view as the macros the reader takes back,
the method's colors as element tags, so a diagram exported and read again
is the sketch it came from."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import terrane
from terrane.join import join_estate
from terrane.plantuml_import import sketch_from_plantuml
from terrane.query import resolve
from terrane.quick import check_sketch, read_any
from terrane.render_plantuml import alias, export_plantuml, render_plantuml

from _fixture import REPO, Sandbox, seeded_model, seeded_views, setup_shared, teardown_shared

VISIO = REPO / "90_EXAMPLE" / "quick" / "sample.vsdx"


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


class TestRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}

    def test_the_context_is_persons_systems_boundaries_and_rels(self) -> None:
        view = self.views["system-context"]
        text = render_plantuml(resolve(self.model, view), self.model, title=view.title)
        self.assertTrue(text.startswith("@startuml\n"))
        self.assertIn("!include <C4/C4_Deployment>", text)
        self.assertIn("title System Context", text)
        self.assertIn('AddElementTag("actors", $bgColor="#', text)
        self.assertIn('AddElementTag("systems", $bgColor="#', text)
        # An external actor is a Person_Ext in its boundary; a system is a System, tagged.
        self.assertIn('Boundary(b_Person, "Person") {', text)
        self.assertIn('Person_Ext(ACT_CARDHOLDER, "Cardholder", "', text)
        self.assertIn('$tags="systems")', text)
        self.assertIn("Rel(ACT_CARDHOLDER, SYS_", text)
        self.assertTrue(text.rstrip().endswith("SHOW_LEGEND()\n@enduml"))
        # No hyphen survives in an alias; the reader turns the underscores back.
        self.assertEqual(alias("SYS-AUTH-SWITCH"), "SYS_AUTH_SWITCH")
        self.assertEqual(alias("9lives"), "n_9lives")

    def test_a_type_c4_has_no_word_for_is_a_tagged_system_that_reads_back_as_itself(self) -> None:
        view = self.views["capability-map"]
        text = render_plantuml(resolve(self.model, view), self.model, title=view.title)
        self.assertIn('$tags="capabilities")', text)
        self.assertNotIn("Deployment_Node(", text)
        doc, notes = sketch_from_plantuml(text, name="back")
        check_sketch(doc)
        self.assertNotIn("systems", doc)
        self.assertIn("CAP-STRAT-01", [c["capability_id"] for c in doc["capabilities"]])
        # The boundary is the map's grouping; the domain comes back as the record's own.
        first = doc["capabilities"][0]
        self.assertEqual(first.get("company_domain", ""),
                         str(self.model.get("capabilities", first["capability_id"]).get("company_domain") or ""))

    def test_the_estates_own_page_reads_back_as_the_estate(self) -> None:
        # Read back unchanged with --correct, the context page "would
        # correct" seven systems and eight actors: the boundary taken for
        # the domain, System_Ext for External, every Person a person, and
        # the "Built with" sentence for the description.
        with Sandbox(seed=True) as root:
            out = Path(tempfile.mkdtemp(prefix="aac-puml-"))
            written, _notes = terrane.export_plantuml(str(root), out, views=["system-context", "application-landscape",
                                                                            "data-landscape", "framework-landscape",
                                                                            "restricted-data-governance",
                                                                            "network-topology"])
            text = "".join(page.read_text(encoding="utf-8") for page in written)
            self.assertIn("' aac SYS_CRM: company_domain=", text)
            self.assertIn('hosting="SaaS"', text)
            for page in written:
                doc, _ = read_any(page, root)
                result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name=page.name, correct=True, dry_run=True)
                self.assertEqual(result.changed, {}, (page.name, result.changes))
                # The landscape's lines come back as the estate's own interfaces, not as new ones.
                self.assertEqual(result.added, {}, (page.name, result.added))
                self.assertEqual(result.rows_added, 0, page.name)
            self.assertIn("' aac rel: source=", text)
            # A reviewer in the tool they know: a label renamed and a line
            # drawn between two systems on the landscape. Read back, one
            # correction and one new interface, nothing else.
            import re

            landscape = next(p for p in written if p.name == "application-landscape.puml")
            page_text = landscape.read_text(encoding="utf-8")
            edited, renamed = re.subn(r'(System(?:_Ext)?\(SYS_CRM, "Dynamics 365 Customer Service)"', r'\1 (reviewed)"',
                                      page_text)
            self.assertEqual(renamed, 1)
            edited = edited.replace("\nSHOW_LEGEND()",
                                    '\nRel(SYS_CRM, SYS_STATEMENTS, "Requests statements", "HTTPS")\n\nSHOW_LEGEND()')
            reviewed = landscape.parent / "reviewed.puml"
            reviewed.write_text(edited, encoding="utf-8")
            doc, _ = read_any(reviewed, root)
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="reviewed.puml", correct=True, dry_run=True)
            self.assertEqual(result.changed, {"systems": ["SYS-CRM"]}, result.changes)
            self.assertEqual(result.added, {"interfaces": ["INT-CRM-STATEMENTS"]})
            self.assertEqual(result.rows_added, 0)

    def test_an_interface_is_a_rel_with_its_name_and_protocol(self) -> None:
        view = self.views["application-landscape"]
        text = render_plantuml(resolve(self.model, view), self.model, title=view.title)
        # An interface of a kind carries the kind as its Rel's tag, and the legend names it.
        self.assertIn('Rel(SYS_AUTH_SWITCH, SYS_CORE_LEDGER, "Authorization Switch to Core Ledger", "MQ", '
                      '$tags="queued-request")', text)
        self.assertIn('AddRelTag("queued-request", $legendText="Request on a queue")', text)
        doc, _notes = sketch_from_plantuml(text, name="back")
        interfaces = {(i["source_system_id"], i["target_system_id"]): i for i in doc["interfaces"]}
        self.assertEqual(interfaces[("SYS-AUTH-SWITCH", "SYS-CORE-LEDGER")]["protocol"], "MQ")
        self.assertEqual(interfaces[("SYS-AUTH-SWITCH", "SYS-CORE-LEDGER")]["name"],
                         "Authorization Switch to Core Ledger")
        # Read back, the tag is the kind: the style the export's Rel could not say comes with it.
        from terrane.connections import kind_of, load_connections

        kinds = load_connections(self.model.root)
        self.assertEqual(kind_of(interfaces[("SYS-AUTH-SWITCH", "SYS-CORE-LEDGER")], kinds), "queued-request")
        tagged = [i for i in self.model.all_of("interfaces") if kind_of(i, kinds)]
        back = [i for i in doc["interfaces"] if kind_of(i, kinds)]
        self.assertTrue(len(back) >= len(tagged) // 2, (len(back), len(tagged)))

    def test_a_technology_service_is_a_deployment_node(self) -> None:
        view = self.views["product-architecture"]
        from terrane.query import bind
        bound = bind(view, {"product": "PRD-MERCHANT-PORTAL"}, self.model)
        text = render_plantuml(resolve(self.model, bound), self.model, title=bound.title)
        self.assertIn('Deployment_Node(', text)
        self.assertIn('$tags="tech_services") {', text)


class TestExport(unittest.TestCase):
    def test_an_estates_own_kinds_tag_its_rels_and_come_back(self) -> None:
        from collections import Counter

        from terrane.connections import kind_of, load_connections
        from terrane.quick import read_any

        thurman = REPO / "90_EXAMPLE" / "thurman-health"
        out = Path(tempfile.mkdtemp(prefix="aac-puml-")) / "puml"
        written, _notes = terrane.export_plantuml(thurman, out, views=["application-landscape"])
        text = Path(written[0]).read_text(encoding="utf-8")
        self.assertIn('AddRelTag("hl7v2-feed", $legendText="HL7 v2 feed")', text)
        self.assertGreater(text.count('$tags="hl7v2-feed"'), 10)
        # Read back for the estate, the HL7 feeds are HL7 feeds. Read alone,
        # the shipped catalog has no such kind to propose from, and the
        # feeds are HL7 feeds still: the record's own fields travel under
        # each Rel, so the page needs no library to come back as itself.
        theirs, _ = read_any(Path(written[0]), root=thurman)
        kinds = load_connections(thurman)
        feeds = Counter(kind_of(i, kinds) for i in theirs["interfaces"])["hl7v2-feed"]
        self.assertGreater(feeds, 10)
        alone, _ = read_any(Path(written[0]))
        self.assertEqual(Counter(kind_of(i, kinds) for i in alone["interfaces"])["hl7v2-feed"], feeds)

    def test_named_views_are_written_and_a_stale_file_goes(self) -> None:
        """A page an earlier export wrote goes; a `.puml` of the reader's own
        in the same folder stays, where the sweep once took it too."""
        out = Path(tempfile.mkdtemp(prefix="aac-puml-"))
        stale = out / "gone.puml"
        stale.write_text("@startuml\n' Gone\n' Generated from the model by `terrane export plantuml`. "
                         "Edit the model, not the diagram.\n@enduml\n", encoding="utf-8")
        mine = out / "mine.puml"
        mine.write_text("@startuml\n' Mine\nAlice -> Bob\n@enduml\n", encoding="utf-8")
        sketched = out / "sketched.puml"
        sketched.write_text("@startuml\n' Sketched\n' Generated from the model by `terrane draw`. "
                            "Edit the model, not the diagram.\n@enduml\n", encoding="utf-8")
        written, notes = terrane.export_plantuml(REPO, out, views=["system-context", "capability-map"])
        self.assertEqual(sorted(p.name for p in written), ["capability-map.puml", "system-context.puml"])
        self.assertFalse(stale.exists())
        self.assertTrue(mine.exists())
        self.assertTrue(sketched.exists())
        self.assertEqual(notes, [])
        for path in written:
            doc, _ = sketch_from_plantuml(path.read_text(encoding="utf-8"))
            check_sketch(doc)

    def test_a_sketch_carries_its_plantuml_and_saves_it_when_asked(self) -> None:
        drawings = terrane.diagrams(str(VISIO), date="2026-10-17")
        text = drawings["applications"].plantuml
        self.assertIsNotNone(text)
        self.assertIn("Generated from the model by `terrane draw`", text)
        doc, _ = sketch_from_plantuml(text, name="back")
        self.assertEqual(sorted(s["system_id"] for s in doc["systems"]),
                         ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING"])
        self.assertEqual([s.get("company_domain") for s in doc["systems"]], ["Payments", "Payments"])
        self.assertEqual(doc["policies"][0]["policy_id"], "POL-CARD-DATA-STAYS-IN-THE-PCI-ZONE")
        folder = Path(tempfile.mkdtemp(prefix="aac-puml-"))
        names = sorted(p.name for p in drawings.save(folder, "visio", plantuml=True))
        self.assertIn("visio--applications.puml", names)
        self.assertNotIn("visio--applications.mmd", names)
        names = sorted(p.name for p in drawings.save(folder, "again"))
        self.assertNotIn("again--applications.puml", names)


if __name__ == "__main__":
    unittest.main()
