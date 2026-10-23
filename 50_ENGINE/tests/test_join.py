"""A sketch joins the estate: written into a repository as its own records,
nothing already there touched, the estate validated after."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout

import terrane
from terrane import cli
from terrane.join import AdoptError, describe, join_estate
from terrane.model import load
from terrane.quick import read_any

from _fixture import REPO, Sandbox

QUICK = REPO / "90_EXAMPLE" / "quick"


class TestJoin(unittest.TestCase):
    def test_a_read_diagram_becomes_records_of_the_estate_once(self) -> None:
        with Sandbox(seed=True) as root:
            doc, _ = read_any(QUICK / "sample.puml")
            result = join_estate(doc, root, source_name="sample.puml")
            self.assertEqual(sorted(result.added["systems"]),
                             ["SYS-EVENTS", "SYS-FRAUD", "SYS-PORTAL", "SYS-SCHEME", "SYS-SWITCH"])
            # The sample estate has a cardholder and a merchant already: theirs stay, and are said.
            self.assertEqual(result.skipped["actors"], ["ACT-CARDHOLDER", "ACT-MERCHANT"])
            self.assertNotIn("actors", result.added)
            self.assertEqual(result.added["data_assets"], ["DA-LEDGER"])
            self.assertEqual(result.added["org_units"], ["ORG-SKETCH"])  # the placeholder, said
            self.assertTrue(any("ORG-SKETCH stands for the owner" in n for n in result.notes), result.notes)
            path = root / "10_MODEL" / "systems" / "SYS-SWITCH.yaml"
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Adopted from sample.puml by `terrane adopt`."), text[:80])
            self.assertIn("company_domain: Payments", text)
            self.assertGreater(result.rows_added, 0)
            self.assertTrue((root / "10_MODEL" / "relations" / "adopted.yaml").is_file())
            model = load(root)
            self.assertIsNotNone(model.get("systems", "SYS-SWITCH"))
            self.assertEqual(result.errors, 0)
            self.assertGreaterEqual(result.warnings, result.warnings_before)
            # Again: nothing new, everything already here.
            again = join_estate(doc, root, source_name="sample.puml")
            self.assertEqual(again.added, {})
            self.assertEqual(sorted(again.skipped["systems"]), sorted(result.added["systems"]))
            self.assertEqual(again.rows_added, 0)
            self.assertEqual(again.rows_skipped, result.rows_added)
            self.assertIn("nothing to adopt", "\n".join(describe(again)))

    def test_an_owner_of_the_estate_takes_the_placeholders_place(self) -> None:
        with Sandbox(seed=True) as root:
            doc, _ = read_any(QUICK / "sample.puml")
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="sample.puml")
            self.assertNotIn("org_units", result.added)
            self.assertFalse((root / "10_MODEL" / "org_units" / "ORG-SKETCH.yaml").exists())
            text = (root / "10_MODEL" / "systems" / "SYS-SWITCH.yaml").read_text(encoding="utf-8")
            self.assertIn("owner_org_id: ORG-PAYMENTS", text)
            self.assertTrue(any("ORG-PAYMENTS owns" in n for n in result.notes), result.notes)
            with self.assertRaises(AdoptError):
                join_estate(doc, root, owner="ORG-NOBODY")

    def test_what_is_there_already_stays_as_it_is(self) -> None:
        with Sandbox(seed=True) as root:
            before = (root / "10_MODEL" / "systems" / "SYS-CORE-LEDGER.yaml").read_text(encoding="utf-8")
            doc = {"model": {"name": "Two"}, "systems": [{"system_id": "SYS-CORE-LEDGER", "name": "Renamed"},
                                                          {"system_id": "SYS-NEW-THING", "name": "New thing"}],
                   "interfaces": [{"interface_id": "INT-NEW", "source_system_id": "SYS-NEW-THING",
                                   "target_system_id": "SYS-CORE-LEDGER"}]}
            result = join_estate(doc, root, owner="ORG-PAYMENTS")
            self.assertEqual(result.skipped["systems"], ["SYS-CORE-LEDGER"])
            self.assertEqual(result.added["systems"], ["SYS-NEW-THING"])
            self.assertEqual(result.added["interfaces"], ["INT-NEW"])
            self.assertEqual((root / "10_MODEL" / "systems" / "SYS-CORE-LEDGER.yaml").read_text(encoding="utf-8"), before)
            self.assertEqual(result.errors, 0)

    def test_with_correct_a_differing_cell_is_written_into_the_records_own_file(self) -> None:
        with Sandbox(seed=True) as root:
            path = root / "10_MODEL" / "systems" / "SYS-CORE-LEDGER.yaml"
            path.write_text("# Kept: the reason above the record.\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
            before = load(root).get("systems", "SYS-CORE-LEDGER")
            doc = {"model": {"name": "Corrections"},
                   "systems": [{"system_id": "SYS-CORE-LEDGER", "name": "Core Ledger (mainframe)",
                                "tags": "core;mainframe;legacy;batch", "owner_org_id": before["owner_org_id"],
                                "cmdb_ci_class": ""}]}
            # Without `correct`, as before: what is there stays, and is said.
            plain = join_estate(doc, root)
            self.assertEqual(plain.changed, {})
            self.assertEqual(plain.skipped, {"systems": ["SYS-CORE-LEDGER"]})
            dry = terrane.adopt(doc, root, dry_run=True, correct=True)
            self.assertEqual(dry.changed, {"systems": ["SYS-CORE-LEDGER"]})
            self.assertEqual(load(root).get("systems", "SYS-CORE-LEDGER")["name"], before["name"])
            self.assertIn("would correct 1", "\n".join(describe(dry, dry_run=True)))
            result = join_estate(doc, root, correct=True)
            self.assertEqual(result.changed, {"systems": ["SYS-CORE-LEDGER"]})
            self.assertEqual(result.skipped, {})
            self.assertEqual(result.added, {})
            self.assertEqual(result.changes, ["SYS-CORE-LEDGER name: %s -> Core Ledger (mainframe)" % before["name"],
                                              "SYS-CORE-LEDGER tags: core;legacy;mainframe -> batch;core;legacy;mainframe"])
            after = load(root).get("systems", "SYS-CORE-LEDGER")
            self.assertEqual(after["name"], "Core Ledger (mainframe)")
            self.assertEqual(after["tags"], ["core", "mainframe", "legacy", "batch"])
            # The blank cell left the field alone; the file kept its comments.
            self.assertEqual(after["cmdb_ci_class"], before["cmdb_ci_class"])
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Kept: the reason above the record.\n# Imported from systems.csv.\n"), text[:120])
            self.assertEqual(result.errors, 0)
            self.assertIn("corrected 1 (SYS-CORE-LEDGER)", "\n".join(describe(result)))
            # The same cells again: nothing to correct, there as they are.
            again = join_estate(doc, root, correct=True)
            self.assertEqual(again.changed, {})
            self.assertEqual(again.skipped, {"systems": ["SYS-CORE-LEDGER"]})

    def test_with_correct_a_relation_rows_qualifier_takes_the_sketchs(self) -> None:
        with Sandbox(seed=True) as root:
            before = load(root)
            row = next(r for r in before.relation_rows("system_reads_writes")
                       if not r.get("archetype_instance") and r.get("operation") == "Read")
            path = root / "10_MODEL" / "relations" / "imported_relations.yaml"
            head = path.read_text(encoding="utf-8").splitlines()[0]
            doc = {"model": {"name": "Rows"}, "systems": [row["system_id"]], "data_assets": [row["data_asset_id"]],
                   "relations": {"system_reads_writes": [{"system_id": row["system_id"], "data_asset_id": row["data_asset_id"],
                                                          "operation": "ReadWrite"}]}}
            # Without `correct`, as before: the row is recorded already and stays.
            plain = join_estate(doc, root, owner="ORG-PAYMENTS")
            self.assertEqual((plain.rows_corrected, plain.rows_skipped), (0, 1))
            result = join_estate(doc, root, owner="ORG-PAYMENTS", correct=True)
            self.assertEqual((result.rows_corrected, result.rows_skipped, result.rows_added), (1, 0, 0))
            self.assertEqual(result.changes, ["system_reads_writes %s -> %s operation: Read -> ReadWrite"
                                              % (row["system_id"], row["data_asset_id"])])
            after = next(r for r in load(root).relation_rows("system_reads_writes")
                         if r["system_id"] == row["system_id"] and r["data_asset_id"] == row["data_asset_id"])
            self.assertEqual(after["operation"], "ReadWrite")
            self.assertEqual(path.read_text(encoding="utf-8").splitlines()[0], head)
            self.assertIn("corrected 1", "\n".join(describe(result)))
            self.assertEqual(result.errors, 0)
            again = join_estate(doc, root, owner="ORG-PAYMENTS", correct=True)
            self.assertEqual((again.rows_corrected, again.rows_skipped), (0, 1))

    def test_a_row_the_estate_has_among_several_is_recorded_and_corrects_nothing(self) -> None:
        # The review loop walked end to end: the workbook of the pictures
        # came back untouched and "corrected" 43 reference rows, each the
        # second row of a pair into a duplicate of the first; the loader
        # then dropped 36 rows. A row is the triple the loader counts.
        with Sandbox(seed=True) as root:
            before = load(root)
            cap = str(next(iter(before.all_of("capabilities")))["capability_id"])
            cap_two = str([r for r in before.all_of("capabilities")][1]["capability_id"])
            fw = str(next(iter(before.all_of("frameworks")))["framework_id"])
            path = root / "10_MODEL" / "relations" / "refs.yaml"
            text = ("# Two names for one reference, and one for another.\ncapability_references_framework:\n"
                    "  - capability_id: %s\n    framework_id: %s\n    ref: One\n"
                    "  - capability_id: %s\n    framework_id: %s\n    ref: Two\n"
                    "  - capability_id: %s\n    framework_id: %s\n    ref: Alone\n" % (cap, fw, cap, fw, cap_two, fw))
            path.write_text(text, encoding="utf-8")
            start = len(load(root).relation_rows("capability_references_framework"))
            rows = lambda *refs: {"model": {"name": "Refs"}, "capabilities": [cap, cap_two], "frameworks": [fw],  # noqa: E731
                                  "relations": {"capability_references_framework": [
                                      {"capability_id": c, "framework_id": fw, "ref": ref} for c, ref in refs]}}
            # The workbook's own rows back: recorded, nothing corrected, the file as it was.
            back = join_estate(rows((cap, "One"), (cap, "Two"), (cap_two, "Alone")), root, correct=True)
            self.assertEqual((back.rows_corrected, back.rows_skipped, back.rows_added), (0, 3, 0))
            self.assertEqual(back.changes, [])
            self.assertEqual(path.read_text(encoding="utf-8"), text)
            # A third name for the pair with two: no one row to correct; said, and left.
            third = join_estate(rows((cap, "Three")), root, correct=True)
            self.assertEqual((third.rows_corrected, third.rows_skipped), (0, 1))
            self.assertTrue(any("2 rows here and none with ref 'Three'" in n for n in third.notes), third.notes)
            self.assertEqual(path.read_text(encoding="utf-8"), text)
            # Two sketch rows for the pair with one: which corrects it is not the tool's to pick.
            two = join_estate(rows((cap_two, "Either"), (cap_two, "Or")), root, correct=True)
            self.assertEqual((two.rows_corrected, two.rows_skipped), (0, 2))
            self.assertTrue(any("the sketch has 2 rows for the pair" in n for n in two.notes), two.notes)
            self.assertEqual(path.read_text(encoding="utf-8"), text)
            # One sketch row for the pair with one: corrected, as before.
            one = join_estate(rows((cap_two, "Renamed")), root, correct=True)
            self.assertEqual((one.rows_corrected, one.rows_skipped), (1, 0))
            self.assertIn("ref: Renamed", path.read_text(encoding="utf-8"))
            # Corrected in place: the count holds, and nothing became a duplicate to drop.
            self.assertEqual(len(load(root).relation_rows("capability_references_framework")), start)

    def test_a_correction_to_what_a_shape_made_goes_under_the_products_overrides(self) -> None:
        # The second estate's reviewer renamed a system a shape made, and
        # the dry run said the correction goes under the product's
        # overrides and left it: the method's answer, named and not taken.
        from terrane.join import estate_copy

        root = estate_copy(REPO, Path(tempfile.mkdtemp(prefix="aac-over-")))
        product = root / "10_MODEL" / "products" / "PRD-CARD-SERVICING.yaml"
        before = product.read_text(encoding="utf-8")
        doc = {"model": {"name": "r"},
               "systems": [{"system_id": "SYS-CARDSVC-API", "name": "Card Servicing API (reviewed)"}],
               "interfaces": [{"interface_id": "INT-CARDSVC-API-STORE", "protocol": "gRPC"}]}
        dry = join_estate(doc, root, owner="ORG-DIGITAL", correct=True, dry_run=True)
        self.assertEqual(dry.changed, {"systems": ["SYS-CARDSVC-API"], "interfaces": ["INT-CARDSVC-API-STORE"]})
        self.assertEqual(product.read_text(encoding="utf-8"), before)
        result = join_estate(doc, root, owner="ORG-DIGITAL", correct=True)
        self.assertEqual(result.changed, dry.changed)
        self.assertEqual([p.resolve() for p in result.written], [product.resolve()])
        self.assertIn("SYS-CARDSVC-API name: Card Servicing Service -> Card Servicing API (reviewed), under the overrides "
                      "of PRD-CARD-SERVICING", result.changes)
        self.assertEqual(result.errors, 0)
        after = load(root)
        self.assertEqual(after.get("systems", "SYS-CARDSVC-API")["name"], "Card Servicing API (reviewed)")
        self.assertEqual(after.get("interfaces", "INT-CARDSVC-API-STORE")["protocol"], "gRPC")
        text = product.read_text(encoding="utf-8")
        # The file is otherwise as it was: its comments, its patterns, the
        # other overrides and the comment inside them, the entry's other fields.
        self.assertIn("# Not in the servicing path", text)
        self.assertIn("patterns: [stateless-request-service, event-fanout, strangler-facade, observed-service]", text)
        self.assertIn("  SYS-CARDSVC-API:\n    description: The service behind the Card Servicing API, backing the "
                      "channel.\n    service_tier: Tier 1\n", text)
        self.assertIn("  INT-CARDSVC-API-STORE:\n    name: Card Servicing Service to Datastore\n    protocol: gRPC\n",
                      text)
        self.assertEqual(text.count("SYS-CARDSVC-API:"), 1)
        self.assertEqual(text.count("overrides:"), 1)
        # Again: nothing left to correct. And a product with no overrides
        # block gets one.
        self.assertEqual(join_estate(doc, root, owner="ORG-DIGITAL", correct=True).changed, {})
        bare = [p for p in sorted((root / "10_MODEL" / "products").glob("*.yaml"))
                if "archetype:" in p.read_text(encoding="utf-8") and "overrides:" not in p.read_text(encoding="utf-8")]
        self.assertTrue(bare, "every product on a shape has overrides; the branch that adds the block is untested")
        held = bare[0].read_text(encoding="utf-8")
        product_id = next(r["product_id"] for r in after.all_of("products") if Path(r["_source_file"]).resolve() == bare[0].resolve())
        made = next(r for r in after.all_of("systems") if r.get("archetype_instance") == product_id)
        one = {"model": {"name": "r"}, "systems": [{"system_id": made["system_id"], "name": "Renamed by review"}]}
        self.assertEqual(join_estate(one, root, owner="ORG-DIGITAL", correct=True).changed, {"systems": [made["system_id"]]})
        self.assertEqual(load(root).get("systems", made["system_id"])["name"], "Renamed by review")
        self.assertTrue(bare[0].read_text(encoding="utf-8").startswith(held.rstrip("\n") + "\n"), bare[0].name)


        with Sandbox(seed=True) as root:
            path = root / "10_MODEL" / "actors" / "pair.yaml"
            path.write_text("# Two actors, with a reason.\n- actor_id: ACT-ONE\n  name: One\n  description: >\n"
                            "    Two lines,\n    folded.\n  status: Active\n  actor_kind: Person\n\n"
                            "# The second.\n- actor_id: ACT-TWO\n  name: Two\n  status: Active\n  actor_kind: Role\n",
                            encoding="utf-8")
            doc = {"model": {"name": "c"}, "actors": [{"actor_id": "ACT-ONE", "name": "First",
                                                        "description": "One line now.", "company_domain": "Servicing"}]}
            result = join_estate(doc, root, owner="ORG-DIGITAL", correct=True)
            self.assertEqual(result.changed, {"actors": ["ACT-ONE"]})
            self.assertEqual(path.read_text(encoding="utf-8"),
                             "# Two actors, with a reason.\n- actor_id: ACT-ONE\n  name: First\n  description: One line now.\n"
                             "  status: Active\n  actor_kind: Person\n  company_domain: Servicing\n\n"
                             "# The second.\n- actor_id: ACT-TWO\n  name: Two\n  status: Active\n  actor_kind: Role\n")
            model = load(root)
            self.assertEqual(model.get("actors", "ACT-TWO")["name"], "Two")
            self.assertEqual(model.get("actors", "ACT-ONE")["company_domain"], "Servicing")

    def test_a_page_of_the_estates_own_view_on_a_subject_is_not_a_view_to_add(self) -> None:
        with Sandbox(seed=True) as root:
            doc = {"model": {"name": "pages"}, "systems": ["SYS-CORE-LEDGER"],
                   "views": [{"view_id": "system-context--SYS-CORE-LEDGER", "title": "A page", "kind": "diagram",
                              "layout": "LR", "scope": {"include": [{"type": "systems", "where": {"id_in": ["SYS-CORE-LEDGER"]}}]},
                              "edges": []},
                             {"view_id": "a-new-page", "title": "New", "kind": "diagram", "layout": "LR",
                              "scope": {"include": [{"type": "systems", "where": {"id_in": ["SYS-CORE-LEDGER"]}}]},
                              "edges": []}]}
            result = join_estate(doc, root, owner="ORG-PAYMENTS")
            self.assertEqual(result.views_skipped, ["system-context--SYS-CORE-LEDGER"])
            self.assertEqual(result.views_added, ["a-new-page"])
            self.assertIn("system-context--SYS-CORE-LEDGER: a page of this repository's own system-context view on a "
                          "subject; not added as a view", result.notes)

    def test_a_workbook_of_the_pictures_comes_back_corrected(self) -> None:
        from terrane.excel_import import sheets
        from terrane.render_excel import workbook_bytes

        with Sandbox(seed=True) as root:
            out = root / "pictures.xlsx"
            terrane.diagrams(str(root), views=["system-context"], date="2026-10-17").excel(out)
            # The reviewer changes one cell: a system's name.
            book = sheets(out.read_bytes())
            target = None
            for name, rows in book:
                if name == "systems":
                    column = rows[0].index("name")
                    target = rows[1][0]
                    rows[1][column] = rows[1][column] + " (reviewed)"
            out.write_bytes(workbook_bytes(book))
            doc, _ = read_any(out)
            result = join_estate(doc, root, source_name="pictures.xlsx", correct=True)
            self.assertEqual(result.changed, {"systems": [target]})
            self.assertEqual(result.added, {})
            self.assertEqual(result.rows_added, 0)
            self.assertEqual(result.views_added, [])
            self.assertEqual(result.errors, 0)
            self.assertTrue(load(root).get("systems", target)["name"].endswith(" (reviewed)"))

    def test_a_view_the_sketch_wrote_out_joins_the_views(self) -> None:
        with Sandbox(seed=True) as root:
            doc, _ = read_any(QUICK / "payments.yaml")
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="payments.yaml")
            self.assertEqual(result.views_added, ["payments-by-hosting"])
            self.assertTrue((root / "30_VIEWS" / "payments-by-hosting.view.yaml").is_file())
            again = join_estate(doc, root, owner="ORG-PAYMENTS")
            self.assertEqual(again.views_skipped, ["payments-by-hosting"])

    def test_a_dry_run_writes_nothing_and_says_what_it_would(self) -> None:
        with Sandbox(seed=True) as root:
            doc, _ = read_any(QUICK / "sample.drawio")
            result = join_estate(doc, root, dry_run=True)
            self.assertTrue(result.added["systems"])
            self.assertFalse(any(p.exists() for p in result.written))
            lines = describe(result, dry_run=True)
            self.assertTrue(any("would adopt" in line for line in lines), lines)
            self.assertIsNone(load(root).get("systems", "SYS-AUTHORIZATION-SWITCH"))

    def test_with_correct_the_change_picture_shows_what_would_be_corrected(self) -> None:
        from terrane.diff_picture import CHANGED_WIDTH
        from terrane.join import change_picture

        with Sandbox(seed=True) as root:
            doc = {"model": {"name": "Corrections"},
                   "systems": [{"system_id": "SYS-CORE-LEDGER", "name": "Core Ledger (mainframe)"},
                               {"system_id": "SYS-NEW-THING", "name": "New thing"}],
                   "interfaces": [{"interface_id": "INT-NEW", "source_system_id": "SYS-NEW-THING",
                                   "target_system_id": "SYS-CORE-LEDGER"}]}
            picture = change_picture(doc, root, owner="ORG-PAYMENTS", source_name="fixes.yaml", correct=True)
            self.assertEqual(picture.title, "What fixes.yaml adds and corrects")
            self.assertIn("New thing", picture.svg)
            self.assertIn("Core Ledger (mainframe)", picture.svg)
            # The ledger is the estate's hub; corrected, it brings no neighbors: two boxes, not two hundred.
            self.assertIn("2 nodes", picture.svg)
            self.assertTrue('stroke-width="3"' in picture.svg or 'stroke-width="%s"' % CHANGED_WIDTH in picture.svg,
                            "no heavy border on the picture")
            # Nothing was written: the picture is drawn on a copy.
            self.assertEqual(load(root).get("systems", "SYS-CORE-LEDGER")["name"], "Core Card Ledger")
            # A file that only corrects shows the corrections; without `correct` it has nothing to show.
            only = {"model": {"name": "c"}, "systems": [{"system_id": "SYS-CORE-LEDGER", "name": "Core Ledger (mainframe)"}]}
            self.assertEqual(change_picture(only, root, owner="ORG-PAYMENTS", source_name="fixes.yaml", correct=True).title,
                             "What fixes.yaml corrects")
            with self.assertRaises(AdoptError):
                change_picture(only, root, owner="ORG-PAYMENTS", source_name="fixes.yaml")

    def test_a_corrected_connection_is_a_heavy_line_between_its_ends(self) -> None:
        # The review loop's reviewer changed one connection's kind and the
        # picture of the change showed nothing: an interface is a line, not
        # a box, and nothing kept its ends.
        import xml.etree.ElementTree as ET

        from terrane.join import change_picture

        svg = "{http://www.w3.org/2000/svg}"

        def parts(picture):
            tree = ET.fromstring(picture.svg)
            nodes = {el.get("data-id"): el for el in tree.iter(svg + "g") if el.get("class") == "node"}
            edges = [el for el in tree.iter(svg + "g") if el.get("class") == "edge"]
            return nodes, edges

        with Sandbox(seed=True) as root:
            doc = {"model": {"name": "c"}, "interfaces": [{"interface_id": "INT-AUTH-LEDGER", "protocol": "gRPC"}]}
            picture = change_picture(doc, root, owner="ORG-PAYMENTS", source_name="fixes.yaml", correct=True)
            self.assertEqual(picture.title, "What fixes.yaml corrects")
            self.assertIn("The 1 connection it would correct, as a heavy line, and what is there already, faded.",
                          picture.svg)
            nodes, edges = parts(picture)
            # The line ends at the ledger's request queue, which it goes
            # through, drawn on the ledger as every diagram draws it.
            self.assertEqual(set(nodes), {"SYS-AUTH-SWITCH", "OI-LEDGER-QUEUE", "SYS-CORE-LEDGER"})
            self.assertTrue(all(el.get("opacity") == "0.55" for el in nodes.values()))
            heavy = [el for el in edges if 'stroke-width="3"' in ET.tostring(el, encoding="unicode")]
            self.assertEqual(len(heavy), 1)
            self.assertIsNone(heavy[0].get("opacity"))
            self.assertEqual(load(root).get("interfaces", "INT-AUTH-LEDGER")["protocol"], "MQ")
            # A new line between two things already here is a picture too: its
            # ends faded, the line in full, the other lines faded.
            new = {"model": {"name": "n"}, "interfaces": [{"interface_id": "INT-IDENTITY-LEDGER-NEW", "name": "Identity to ledger",
                                                           "source_system_id": "SYS-IDENTITY-SVC",
                                                           "target_system_id": "SYS-CORE-LEDGER", "protocol": "HTTPS"}]}
            picture = change_picture(new, root, owner="ORG-PAYMENTS", source_name="line.yaml")
            self.assertEqual(picture.title, "What line.yaml adds")
            self.assertIn("The 1 connection line.yaml would add to the estate, and what is there already, faded.",
                          picture.svg)
            nodes, edges = parts(picture)
            self.assertEqual(set(nodes), {"SYS-IDENTITY-SVC", "SYS-CORE-LEDGER"})
            full = [el for el in edges if el.get("opacity") is None]
            self.assertEqual(len(full), 1)
            self.assertEqual(len(edges), 1)

    def test_the_change_picture_of_an_estate_in_a_subfolder_draws_with_its_libraries(self) -> None:
        # The second estate names the repository's library two folders up
        # and its own beside it; a scratch copy of its own folders alone
        # did not load, and the picture was an error.
        from terrane.join import change_picture, estate_copy

        second = REPO / "90_EXAMPLE" / "thurman-health"
        tmp = Path(tempfile.mkdtemp(prefix="aac-copy-"))
        place = estate_copy(second, tmp)
        self.assertEqual(place, tmp / "90_EXAMPLE" / "thurman-health")
        self.assertTrue((tmp / "24_CONNECTIONS").is_dir())
        self.assertTrue((place / "library").is_dir())
        self.assertEqual(len(load(place).all_of("systems")), len(load(second).all_of("systems")))
        doc = {"model": {"name": "r"},
               "systems": [{"system_id": "SYS-EHR", "name": "Enterprise EHR (reviewed)"},
                           {"system_id": "SYS-REVIEW-PORTAL", "name": "Review portal"}],
               "interfaces": [{"interface_id": "INT-PORTAL-EHR", "source_system_id": "SYS-REVIEW-PORTAL",
                               "target_system_id": "SYS-EHR", "protocol": "HL7v2"}]}
        picture = change_picture(doc, second, source_name="review.xlsx", correct=True)
        self.assertEqual(picture.title, "What review.xlsx adds and corrects")
        self.assertIn("Enterprise EHR (reviewed)", picture.svg)
        self.assertIn("2 nodes", picture.svg)
        self.assertEqual(load(second).get("systems", "SYS-EHR")["name"], "Enterprise EHR")

    def test_a_product_from_parts_is_adopted_with_what_its_parts_ask_answered(self) -> None:
        # `terrane adopt from-parts.yaml` failed after writing: the drawing
        # answers what the parts ask for and says so, and the record
        # written carried none of the answers, so the estate did not load.
        with Sandbox(seed=True) as root:
            doc, _ = read_any(QUICK / "from-parts.yaml")
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="from-parts.yaml")
            self.assertEqual(result.added.get("products"), ["PRD-PORTAL"])
            self.assertEqual(result.errors, 0)
            self.assertTrue(any(n.startswith("PRD-PORTAL: the parts asked for what the sketch did not say; answered ")
                                for n in result.notes), result.notes)
            after = load(root)
            written = (root / "10_MODEL" / "products" / "PRD-PORTAL.yaml").read_text(encoding="utf-8")
            self.assertIn("product_name: Merchant portal", written)
            made = [s["system_id"] for s in after.all_of("systems") if s.get("archetype_instance") == "PRD-PORTAL"]
            self.assertGreaterEqual(len(made), 2, made)

    def test_what_a_new_products_parts_make_is_new_too(self) -> None:
        # A product from a kit, drawn as a change: the adopter adds the
        # product alone and the render makes its systems, which the picture
        # faded as if the estate had them.
        import xml.etree.ElementTree as ET

        from terrane.join import change_picture

        with Sandbox(seed=True) as root:
            doc, _ = read_any(QUICK / "from-parts.yaml")
            picture = change_picture(doc, root, owner="ORG-PAYMENTS", source_name="from-parts.yaml")
            self.assertEqual(picture.title, "What from-parts.yaml adds")
            svg = "{http://www.w3.org/2000/svg}"
            tree = ET.fromstring(picture.svg)
            nodes = {el.get("data-id"): el for el in tree.iter(svg + "g") if el.get("class") == "node"}
            self.assertIsNone(nodes["PRD-PORTAL"].get("opacity"))
            made = [i for i, el in nodes.items() if i.startswith("SYS-") and el.get("opacity") is None]
            self.assertGreaterEqual(len(made), 2, sorted(nodes))
            # The platform services the parts run on are the estate's own: there, faded.
            faded = [i for i, el in nodes.items() if el.get("opacity") == "0.55"]
            self.assertTrue(faded, sorted(nodes))
            self.assertIn("it makes, the things drawn in full", picture.svg)
            edges = [el for el in tree.iter(svg + "g") if el.get("class") == "edge"]
            self.assertTrue(any(el.get("opacity") is None for el in edges), "no line the parts made is drawn in full")
            self.assertIsNone(load(root).get("products", "PRD-PORTAL"))

    def test_the_change_is_a_picture_of_the_new_among_the_faded(self) -> None:
        from terrane.join import change_picture
        with Sandbox(seed=True) as root:
            doc, _ = read_any(QUICK / "sample.puml")
            picture = change_picture(doc, root, owner="ORG-PAYMENTS", source_name="sample.puml")
            self.assertEqual((picture.kind, picture.title), ("diagram", "What sample.puml adds"))
            self.assertIn("Authorization switch", picture.svg)
            # The estate's own cardholder and merchant, reached by use, are there and faded.
            self.assertIn("Cardholder", picture.svg)
            self.assertIn('opacity="0.55"', picture.svg)
            # Nothing was written to the estate itself.
            self.assertIsNone(load(root).get("systems", "SYS-SWITCH"))
            join_estate(doc, root, owner="ORG-PAYMENTS")
            with self.assertRaises(AdoptError) as caught:
                change_picture(doc, root, owner="ORG-PAYMENTS", source_name="sample.puml")
            self.assertIn("nothing to show", str(caught.exception))

    def test_the_picture_from_the_command_and_the_door(self) -> None:
        with Sandbox(seed=True) as root:
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["--root", str(root), "adopt", str(QUICK / "sample.drawio"), "--owner",
                                 "ORG-PAYMENTS", "--dry-run", "--picture", str(root / "change.svg")])
            self.assertEqual(code, 0, out.getvalue())
            self.assertTrue((root / "change.svg").is_file())
            self.assertIn("would adopt", out.getvalue())
            picture = terrane.change(QUICK / "sample.drawio", root, owner="ORG-PAYMENTS")
            self.assertIn("Fraud scoring", picture.svg)

    def test_the_command_and_the_door(self) -> None:
        with Sandbox(seed=True) as root:
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["--root", str(root), "adopt", str(QUICK / "sample.archimate"), "--owner",
                                 "ORG-PAYMENTS"])
            self.assertEqual(code, 0, out.getvalue())
            self.assertIn("adopted", out.getvalue())
            self.assertIn("validate:", out.getvalue())
            self.assertIsNotNone(load(root).get("systems", "SYS-AUTHORIZATION-SWITCH"))
            result = terrane.adopt({"systems": ["SYS-FROM-PYTHON"]}, root, owner="ORG-PAYMENTS")
            self.assertEqual(result.added["systems"], ["SYS-FROM-PYTHON"])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["--root", str(root), "adopt", str(QUICK / "sample.puml"), "--owner",
                                           "ORG-NOBODY"]), 1)


if __name__ == "__main__":
    unittest.main()
