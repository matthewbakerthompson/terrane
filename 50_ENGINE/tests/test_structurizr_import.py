"""A Structurizr DSL workspace read as a sketch.

The tests hold the cut-down Big Bank workspace in `90_EXAMPLE/quick` to
what it should read as: a person as an actor, the two existing systems as
external systems in the group's domain, the five containers as systems and
a data asset in their software system's domain, the relationships as the
actor using three channels, five interfaces with their technologies as
protocols and one read and write; that a software system with containers
is a boundary and not a box, so a relationship to it is said and left out;
that the views and styles are skipped; and that the sketch draws.
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli  # noqa: E402
from terrane.quick import draw_sketch, sketch_from_structurizr_file  # noqa: E402
from terrane.structurizr_import import sketch_from_structurizr  # noqa: E402
from terrane.structurizr_import import StructurizrError, _tokens, sketch_from_structurizr  # noqa: E402

from _fixture import Sandbox  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[2] / "90_EXAMPLE" / "quick" / "sample.dsl"


class TestRead(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc, cls.notes = sketch_from_structurizr(SAMPLE.read_text(encoding="utf-8"), name="Sample")

    def test_the_elements_and_their_domains(self) -> None:
        self.assertEqual(self.doc["model"]["name"], "Big Bank plc")
        self.assertEqual(self.doc["actors"], [{
            "actor_id": "ACT-CUSTOMER", "name": "Personal Banking Customer",
            "description": "A customer of the bank, with personal bank accounts.", "actor_kind": "Person",
            "internal": "Yes"}])
        by_id = {s["system_id"]: s for s in self.doc["systems"]}
        self.assertEqual(sorted(by_id), ["SYS-API", "SYS-EMAIL", "SYS-MAINFRAME", "SYS-MOBILE", "SYS-SPA", "SYS-WEB"])
        self.assertEqual((by_id["SYS-MAINFRAME"]["hosting"], by_id["SYS-MAINFRAME"]["company_domain"]),
                         ("External", "Big Bank plc"))
        self.assertEqual(by_id["SYS-WEB"]["company_domain"], "Internet Banking System")
        self.assertTrue(by_id["SYS-WEB"]["description"].endswith("Built with Java and Spring MVC."))
        self.assertNotIn("hosting", by_id["SYS-WEB"])
        # The container tagged Database is a data asset; the software system
        # with containers is their boundary and not a box.
        self.assertEqual([d["data_asset_id"] for d in self.doc["data_assets"]], ["DA-DATABASE"])
        self.assertEqual(self.doc["data_assets"][0]["company_domain"], "Internet Banking System")
        self.assertNotIn("SYS-INTERNETBANKING", by_id)

    def test_the_relationships(self) -> None:
        interfaces = {i["interface_id"]: i for i in self.doc["interfaces"]}
        self.assertEqual(set(interfaces), {"INT-WEB-SPA", "INT-SPA-API", "INT-MOBILE-API", "INT-API-MAINFRAME",
                                           "INT-API-EMAIL"})
        self.assertEqual((interfaces["INT-SPA-API"]["name"], interfaces["INT-SPA-API"]["protocol"]),
                         ("Makes API calls to", "JSON/HTTPS"))
        self.assertEqual(interfaces["INT-API-EMAIL"]["protocol"], "SMTP")
        self.assertNotIn("protocol", interfaces["INT-WEB-SPA"])
        relations = self.doc["relations"]
        self.assertEqual(sorted(r["system_id"] for r in relations["actor_uses_system"]),
                         ["SYS-MOBILE", "SYS-SPA", "SYS-WEB"])
        self.assertEqual(relations["actor_uses_system"][0]["interaction"], "Visits bigbank.com/ib using")
        self.assertEqual(relations["system_reads_writes"],
                         [{"system_id": "SYS-API", "data_asset_id": "DA-DATABASE", "operation": "ReadWrite"}])

    def test_the_view_and_the_notes(self) -> None:
        view = self.doc["views"][0]
        self.assertEqual((view["layout"], view["group_by"]), ("TB", "company_domain"))
        self.assertIn("Structurizr", view["description"])
        self.assertIn("a group, or a system with containers, per domain", view["description"])
        self.assertIn("from the workspace", self.notes[0])
        # The e-mail system telling the customer something has no relation here.
        self.assertTrue(any("email -> customer" in n and "left out" in n for n in self.notes), self.notes)
        # Views, styles, the include and the identifiers directive are skipped without a word.
        self.assertFalse(any("could not read" in n for n in self.notes), self.notes)

    def test_the_small_print(self) -> None:
        doc, notes = sketch_from_structurizr(
            'workspace {\n  model {\n    bank = softwareSystem "Bank" {\n      api = container "API"\n'
            '      -> db "Reads"\n      db = container "Store" "" "PostgreSQL"\n    }\n'
            '    user = person "User"\n    user -> bank "Uses"\n  }\n}\n')
        self.assertEqual([d["data_asset_id"] for d in doc["data_assets"]], ["DA-DB"])
        self.assertTrue(any("bank has containers and is drawn as their boundary" in n for n in notes), notes)
        # `-> db` from inside the software system's block is from the system,
        # which is a boundary here, so the relationship is left out and said.
        self.assertEqual(doc.get("interfaces"), None)
        with self.assertRaises(StructurizrError):
            sketch_from_structurizr("// nothing but a comment\n")
        self.assertEqual(_tokens('a -> b "Uses \\"it\\"" "HTTPS" { // tail'),
                         [("a", False), ("->", False), ("b", False), ('Uses "it"', True), ("HTTPS", True), ("{", False)])


class TestWriteAndDraw(unittest.TestCase):
    def test_the_sketch_written_beside_the_workspace_draws(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-dsl-"))
        source = folder / "sample.dsl"
        source.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        sketch, _notes = sketch_from_structurizr_file(source)
        self.assertTrue(sketch.read_text(encoding="utf-8").startswith("# Read from sample.dsl by `terrane draw --from-structurizr`"))
        written, notes = draw_sketch(sketch, folder / "out")
        self.assertEqual([p.name for p in written], ["sample--imported.svg"])
        root = ET.fromstring(written[0].read_text(encoding="utf-8"))
        nodes = {el.get("data-id") for el in root.iter() if el.get("class") == "node"}
        self.assertEqual(nodes, {"ACT-CUSTOMER", "SYS-MAINFRAME", "SYS-EMAIL", "SYS-WEB", "SYS-SPA", "SYS-MOBILE",
                                 "SYS-API", "DA-DATABASE"})
        self.assertEqual(len([el for el in root.iter() if el.get("class") == "edge"]), 9)

    def test_a_relationship_tagged_with_a_connection_kind_is_of_that_kind(self) -> None:
        text = ('workspace {\n  model {\n    a = softwareSystem "Auth"\n    b = softwareSystem "Fraud"\n'
                '    c = softwareSystem "Ledger"\n    a -> b "Score the transaction" "" "api-call"\n'
                '    a -> c "Post the authorization" "MQ" "Legacy,queued-request"\n  }\n}\n')
        doc, _notes = sketch_from_structurizr(text, name="kinds")
        by_target = {i["target_system_id"]: i for i in doc["interfaces"]}
        scored = by_target["SYS-B"]
        self.assertEqual((scored["name"], scored["integration_style"], scored["protocol"], scored["auth_method"]),
                         ("Score the transaction", "Request-response", "HTTPS", "OAuth2"))
        posted = by_target["SYS-C"]
        # The protocol the line said is one the kind carries, so it stays; a styling tag beside it is left alone.
        self.assertEqual((posted["protocol"], posted["integration_style"], posted["auth_method"]),
                         ("MQ", "Request-response", "MutualTLS"))

    def test_the_engines_own_workspace_tags_its_interfaces_with_their_kinds(self) -> None:
        from terrane.connections import kind_of, load_connections
        from terrane.model import load
        from terrane.render_structurizr import _relationship_lines

        repo = Path(__file__).resolve().parents[2]
        model = load(repo)
        lines = _relationship_lines(model, set(model.entities["systems"]))
        self.assertTrue(any('"MQ" "queued-request"' in line for line in lines), lines[:5])
        # The lines read back as a workspace give the connections their kinds.
        text = "workspace {\n  model {\n" + "".join(
            '    %s = softwareSystem "%s"\n' % (sid.replace("-", "_"), sid) for sid in model.entities["systems"]) \
            + "".join("    %s\n" % line for line in lines) + "  }\n}\n"
        doc, _notes = sketch_from_structurizr(text, name="estate")
        kinds = load_connections(repo)
        tagged = sum(1 for i in model.all_of("interfaces") if kind_of(i, kinds))
        back = sum(1 for i in doc["interfaces"] if kind_of(i, kinds))
        self.assertGreaterEqual(back, tagged - 5, (back, tagged))

    def test_the_engines_marks_outrank_the_tags_and_the_groups(self) -> None:
        # Every element the engine writes is a software system with a type
        # tag the reader never read, and a group is a placement: an actor
        # came back as SYS-ACT-APPLICANT in the domain "On-prem".
        text = (
            'workspace "Marked" {\n  model {\n    group "On-prem" {\n'
            '      sys_crm = softwareSystem "CRM" "Case management." "System,Active" {\n'
            '        properties {\n          "aac.type" "systems"\n          "aac.id" "SYS-CRM"\n'
            '          "aac.company_domain" "Servicing"\n          "aac.hosting" "SaaS"\n        }\n      }\n'
            '      act_agent = softwareSystem "Agent" "" "Element" {\n'
            '        properties {\n          "aac.type" "actors"\n          "aac.id" "ACT-AGENT"\n'
            '          "aac.company_domain" ""\n          "aac.actor_kind" "Role"\n        }\n      }\n'
            '      da_profile = softwareSystem "Profile" "" "Data Asset" {\n'
            '        properties {\n          "aac.type" "data_assets"\n          "aac.id" "DA-PROFILE"\n'
            '          "aac.company_domain" "Servicing"\n        }\n      }\n'
            '      sys_plain = softwareSystem "Plain"\n'
            '    }\n'
            '    sys_plain -> sys_crm "Posts cases" "HTTPS" "api-call" {\n'
            '      properties {\n        "aac.interface_id" "INT-PLAIN-CRM"\n        "aac.kind" "api-call"\n'
            '        "aac.auth_method" "HMAC"\n      }\n    }\n'
            '    sys_crm -> da_profile "system reads writes" {\n'
            '      properties {\n        "aac.relation" "system_reads_writes"\n        "aac.operation" "Read"\n      }\n    }\n'
            '    sys_crm -> da_profile "masters" {\n      properties {\n        "aac.field" "source_of_truth"\n      }\n    }\n'
            '    act_agent -> sys_crm "Works cases"\n'
            '  }\n  views {\n    styles {\n      element "System" {\n        background #ffffff\n      }\n    }\n  }\n}\n')
        doc, notes = sketch_from_structurizr(text, name="marked")
        systems = {s["system_id"]: s for s in doc["systems"]}
        self.assertEqual(set(systems), {"SYS-CRM", "SYS-PLAIN"})
        self.assertEqual((systems["SYS-CRM"]["company_domain"], systems["SYS-CRM"]["hosting"]), ("Servicing", "SaaS"))
        # The unmarked box reads as before: a system of the group's domain.
        self.assertEqual(systems["SYS-PLAIN"]["company_domain"], "On-prem")
        agent = doc["actors"][0]
        self.assertEqual((agent["actor_id"], agent["actor_kind"]), ("ACT-AGENT", "Role"))
        self.assertNotIn("company_domain", agent)
        profile = doc["data_assets"][0]
        self.assertEqual((profile["data_asset_id"], profile["source_of_truth"]), ("DA-PROFILE", "SYS-CRM"))
        line = doc["interfaces"][0]
        self.assertEqual((line["interface_id"], line["name"], line["protocol"], line["auth_method"]),
                         ("INT-PLAIN-CRM", "Posts cases", "HTTPS", "HMAC"))
        self.assertEqual(doc["relations"]["system_reads_writes"],
                         [{"system_id": "SYS-CRM", "data_asset_id": "DA-PROFILE", "operation": "Read"}])
        self.assertEqual(doc["relations"]["actor_uses_system"],
                         [{"actor_id": "ACT-AGENT", "system_id": "SYS-CRM", "interaction": "Works cases"}])
        self.assertFalse(any("could not read" in n for n in notes), notes)

    def test_the_engines_own_workspace_reads_back_as_the_estate(self) -> None:
        # Read back unchanged with --correct, the workspace would have added
        # 42 systems and 157 interfaces and "corrected" 60 domains.
        from terrane.join import join_estate
        from terrane.model import load
        from terrane.palette import Palette
        from terrane.query import load_views, resolve
        from terrane.quick import read_any
        from terrane.render_structurizr import render_workspace

        with Sandbox(seed=True) as root:
            model = load(root)
            views = [v for v in load_views(root / "30_VIEWS")
                     if "structurizr" in v.renderers and v.kind not in ("report", "timeline") and not v.parameters]
            self.assertTrue(views)
            graphs = [resolve(model, v) for v in views]
            path = root / "workspace.dsl"
            path.write_text(render_workspace(model, graphs, Palette(model.config.get("palette"))), encoding="utf-8")
            text = path.read_text(encoding="utf-8")
            self.assertIn('"aac.type" "systems"', text)
            self.assertIn('"aac.interface_id" "INT-', text)
            doc, _notes = read_any(path, root)
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="workspace.dsl", correct=True, dry_run=True)
            self.assertEqual(result.changed, {}, result.changes[:12])
            self.assertEqual(result.added, {})
            self.assertEqual(result.rows_added, 0)
            # A reviewer in the tool they know: a label renamed and a line
            # drawn between two systems on the landscape. Read back, one
            # correction and one new interface, nothing else.
            label = 'sys_crm = softwareSystem "Dynamics 365 Customer Service"'
            self.assertEqual(text.count(label), 1)
            edited = text.replace(label, 'sys_crm = softwareSystem "Dynamics 365 Customer Service (reviewed)"')
            closing = "\n    }\n\n    views {"
            self.assertEqual(edited.count(closing), 1)
            edited = edited.replace(closing, '\n        sys_crm -> sys_statements "Requests statements" "HTTPS"' + closing)
            reviewed = root / "reviewed.dsl"
            reviewed.write_text(edited, encoding="utf-8")
            doc, _ = read_any(reviewed, root)
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="reviewed.dsl", correct=True, dry_run=True)
            self.assertEqual(result.changed, {"systems": ["SYS-CRM"]}, result.changes)
            self.assertEqual(result.added, {"interfaces": ["INT-CRM-STATEMENTS"]})
            self.assertEqual(result.rows_added, 0)

    def test_the_command(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-dsl-"))
        source = folder / "sample.dsl"
        source.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["draw", "--from-structurizr", str(source), "--out", str(folder / "out")])
        self.assertEqual(code, 0, text.getvalue())
        self.assertTrue((folder / "sample.yaml").is_file())
        self.assertTrue((folder / "out" / "sample--imported.svg").is_file())


if __name__ == "__main__":
    unittest.main()
