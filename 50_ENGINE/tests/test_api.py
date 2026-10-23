"""The package's front door: `terrane.diagrams`.

A sketch goes in as a dict, as YAML text or as a path, and the pictures
come back by name, each one showing itself in a notebook and saving itself
to a file, the notes beside them. The tests hold that the three forms draw
the same bytes, that the door and the command agree, that the faces are
inside the picture so it looks the same anywhere, that the Mermaid comes
when asked, and that a wrong sketch and a wrong type are refused by name.
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

import terrane  # noqa: E402
from terrane import cli  # noqa: E402
from terrane.quick import EXAMPLE, Drawing, Drawings, QuickError  # noqa: E402
from _fixture import REPO, Sandbox  # noqa: E402


def _ids(svg: str, cls: str):
    root = ET.fromstring(svg)
    return {el.get("data-id") for el in root.iter() if el.get("class") == cls}


SKETCH = {
    "model": {"name": "Three boxes"},
    "systems": ["SYS-WEB", "SYS-API", "SYS-LEDGER"],
    "interfaces": [
        {"interface_id": "INT-WEB-API", "source_system_id": "SYS-WEB", "target_system_id": "SYS-API",
         "protocol": "HTTPS"},
        {"interface_id": "INT-API-LEDGER", "source_system_id": "SYS-API", "target_system_id": "SYS-LEDGER",
         "protocol": "MQ"},
    ],
    "views": ["application-landscape"],
}


class TestDraw(unittest.TestCase):
    def test_a_dict_draws_and_the_picture_shows_itself(self) -> None:
        pictures = terrane.diagrams(SKETCH)
        self.assertIsInstance(pictures, Drawings)
        self.assertEqual(list(pictures), ["application-landscape"])
        picture = pictures["application-landscape"]
        self.assertIsInstance(picture, Drawing)
        self.assertEqual((picture.name, picture.kind, picture.mermaid), ("application-landscape", "map", None))
        self.assertEqual(picture._repr_svg_(), picture.svg)
        self.assertTrue(picture.svg.startswith("<svg"), picture.svg[:40])
        self.assertEqual(_ids(picture.svg, "node"), {"SYS-WEB", "SYS-API", "SYS-LEDGER"})
        # The faces travel with the picture.
        self.assertIn("@font-face", picture.svg)
        self.assertIn("data:font/woff2;base64,", picture.svg)
        self.assertTrue(any("ORG-SKETCH" in n for n in pictures.notes), pictures.notes)

    def test_text_path_and_file_draw_the_same_bytes(self) -> None:
        from_path = terrane.diagrams(EXAMPLE)
        from_name = terrane.diagrams(str(EXAMPLE))
        from_text = terrane.diagrams(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(list(from_path), list(from_text))
        self.assertIn("payments-by-hosting", from_path)
        self.assertEqual(from_path["FLOW-AUTH"].kind, "flow")
        for name in from_path:
            self.assertEqual(from_path[name].svg, from_text[name].svg, name)
            self.assertEqual(from_path[name].svg, from_name[name].svg, name)

    def test_the_door_and_the_command_agree(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-api-"))
        with redirect_stdout(io.StringIO()):
            code = cli.main(["draw", str(EXAMPLE), "--out", str(out)])
        self.assertEqual(code, 0)
        pictures = terrane.diagrams(EXAMPLE)
        for name, picture in pictures.items():
            path = out / ("payments--%s.svg" % name)
            self.assertEqual(path.read_text(encoding="utf-8"), picture.svg, name)

    def test_saving(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="aac-api-"))
        pictures = terrane.diagrams(SKETCH, mermaid=True)
        picture = pictures["application-landscape"]
        self.assertIsNotNone(picture.mermaid)
        self.assertIn("SYS-API", picture.mermaid or "")
        one = picture.save(folder / "deep" / "landscape.svg")
        self.assertEqual(one.read_text(encoding="utf-8"), picture.svg)
        written = pictures.save(folder / "all", "three")
        self.assertEqual([p.name for p in written], ["three--application-landscape.svg", "three--application-landscape.mmd"])

    def test_a_repository_draws_the_views_named(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        pictures = terrane.diagrams(repo, views=["system-context", {"use": "product-architecture",
                                                                "with": {"product": "PRD-REWARDS"}}])
        self.assertIn("system-context", pictures)
        self.assertIn("product-architecture--PRD-REWARDS", pictures)
        self.assertIn("FLOW-CARD-AUTH", pictures)
        self.assertEqual(pictures["FLOW-CARD-AUTH"].kind, "flow")
        self.assertIn("SYS-REWARDS-API", pictures["product-architecture--PRD-REWARDS"].svg)
        again = terrane.diagrams(str(repo), views=["system-context"])
        self.assertEqual(again["system-context"].svg, pictures["system-context"].svg)
        with self.assertRaises(QuickError) as caught:
            terrane.diagrams(repo, views=["no-such-view"])
        self.assertIn("system-context", str(caught.exception))
        with self.assertRaises(TypeError):
            terrane.diagrams(SKETCH, views=["system-context"])

    def test_a_repository_with_no_views_named_draws_the_whole_estate(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        pictures = terrane.diagrams(repo)
        self.assertIn("application-landscape", pictures)
        self.assertIn("change-roadmap", pictures)
        self.assertFalse([n for n in pictures if n.startswith("product-architecture--")], "subject views are asked for")
        self.assertGreater(len(pictures), 20)

    def test_a_repository_draws_a_view_written_out_from_python(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        pictures = terrane.diagrams(repo, views=[{
            "view_id": "critical-systems", "title": "The critical systems, by domain", "kind": "diagram",
            "description": "A question of the moment: what is Tier 1, and what does it call.",
            "scope": {"include": [{"type": "systems", "where": {"criticality": ["High"]}}]},
            "group_by": "company_domain", "edges": [{"via": "interfaces"}], "node_label": "name",
            "renderers": ["mermaid"], "style": {"color_by": "type"},
        }, "change-register"])
        self.assertEqual(sorted(pictures), ["FLOW-CARD-AUTH", "FLOW-DISPUTE", "FLOW-LOAN-APPLICATION",
                                            "FLOW-REG-RETURN", "change-register", "critical-systems"])
        picture = pictures["critical-systems"]
        self.assertEqual(picture.kind, "diagram")
        self.assertEqual(picture.title, "The critical systems, by domain")
        self.assertIn("Core Card Ledger", picture.svg)
        self.assertEqual(pictures["change-register"].kind, "report")
        self.assertIn('data-layout="table"', pictures["change-register"].svg)
        with self.assertRaises(QuickError) as caught:
            terrane.diagrams(repo, views=[{"title": "no id"}])
        self.assertIn("view_id", str(caught.exception))

    def test_the_whole_estate_has_its_reports(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        pictures = terrane.diagrams(repo)
        self.assertEqual(pictures["control-coverage"].kind, "report")

    def test_the_door_says_what_it_has(self) -> None:
        views = terrane.views()
        self.assertGreater(len(views), 40)
        context = next(v for v in views if v["view_id"] == "system-context")
        self.assertEqual((context["kind"], context["subject"]), ("diagram", []))
        product = next(v for v in views if v["view_id"] == "product-architecture")
        self.assertEqual(product["subject"], ["product"])
        self.assertTrue(all(isinstance(v["fields"], list) for v in views))
        presets = terrane.presets()
        self.assertEqual(sorted(presets), ["connections", "kits", "landing_zones", "parts", "shapes"])
        api_call = next(k for k in presets["connections"] if k["connection_id"] == "api-call")
        self.assertEqual(api_call["proposes"]["protocol"], "HTTPS")
        self.assertTrue(any(s["archetype_id"] == "azure-digital-product" for s in presets["shapes"]))
        self.assertTrue(all(k["parts"] for k in presets["kits"]))
        self.assertIn("AWS", {p for answers in presets["landing_zones"].values() for p in answers})

    def test_a_dict_sketchs_change_is_named_as_the_sketch_names_itself(self) -> None:
        with Sandbox(seed=True) as root:
            sketch = {"model": {"name": "Merchant onboarding"},
                      "systems": [{"system_id": "SYS-ONBOARDING-NEW", "name": "Onboarding", "company_domain": "Payments"}]}
            picture = terrane.change(sketch, str(root), owner="ORG-PAYMENTS")
            self.assertEqual(picture.title, "What Merchant onboarding adds")
            self.assertIn("The 1 thing Merchant onboarding would add to the estate", picture.svg)
            nameless = {"systems": [{"system_id": "SYS-ONBOARDING-NEW", "name": "Onboarding"}]}
            self.assertEqual(terrane.change(nameless, str(root), owner="ORG-PAYMENTS").title, "What a sketch adds")

    def test_an_estates_own_presets_and_views(self) -> None:
        thurman = REPO / "90_EXAMPLE" / "thurman-health"
        theirs = terrane.presets(thurman)
        kinds = [k["connection_id"] for k in theirs["connections"]]
        # The health system's own kinds after the shipped ones.
        self.assertIn("api-call", kinds)
        self.assertIn("hl7v2-feed", kinds)
        self.assertEqual(kinds.index("api-call") < kinds.index("hl7v2-feed"), True)
        self.assertNotIn("hl7v2-feed", [k["connection_id"] for k in terrane.presets()["connections"]])
        views = terrane.views(thurman)
        self.assertGreater(len(views), 30)
        self.assertIn("system-context", [v["view_id"] for v in views])

    def test_what_the_parts_make_is_knowable_before_the_drawing(self) -> None:
        product = terrane.from_parts("AWS", "Merchant portal", parts=["web-app-baseline", "async-worker"])
        pid = product["products"][0]["product_id"]
        made = terrane.made_by(product)
        self.assertEqual(list(made), [pid])
        api = next(m for m in made[pid] if m["part"] == "api-service")
        self.assertEqual(api["type"], "systems")
        self.assertTrue(api["id"].startswith("SYS-") and api["name"], api)
        self.assertTrue(any(m["type"] == "tech_services" for m in made[pid]), made[pid])
        # The id in hand, a part's system connects to the rest of the estate by a kind, and the line draws.
        sketch = dict(product)
        sketch["systems"] = list(sketch.get("systems") or []) + [
            {"system_id": "SYS-CORE-LEDGER", "name": "Core ledger", "hosting": "On-prem"}]
        sketch["interfaces"] = [terrane.connect(api["id"], "SYS-CORE-LEDGER", "queued-request", name="Post the authorization")]
        pictures = terrane.diagrams(sketch, date="2026-10-18")
        self.assertEqual(pictures.made, made)
        self.assertIn("MQ", pictures["product-architecture--%s" % pid].svg)
        self.assertIn("Core ledger", pictures["product-architecture--%s" % pid].svg)

    def test_a_connection_of_a_kind_from_one_call(self) -> None:
        from terrane.quick import QuickError

        record = terrane.connect("SYS-A", "SYS-B", "API call", name="Score the transaction")
        self.assertEqual(record["interface_id"], "INT-A-B")
        self.assertEqual((record["source_system_id"], record["target_system_id"]), ("SYS-A", "SYS-B"))
        self.assertEqual(record["name"], "Score the transaction")
        self.assertEqual((record["integration_style"], record["protocol"], record["auth_method"]),
                         ("Request-response", "HTTPS", "OAuth2"))
        self.assertEqual(record["patterns"], ["api-front-door"])
        # By id, with a field of one's own over the proposal, and the name the kind's when none is given.
        own = terrane.connect("SYS-A", "SYS-B", "queued-request", protocol="IBM MQ", interface_id="INT-X")
        self.assertEqual((own["interface_id"], own["name"], own["protocol"]), ("INT-X", "Request on a queue", "IBM MQ"))
        with self.assertRaises(QuickError) as caught:
            terrane.connect("SYS-A", "SYS-B", "carrier pigeon")
        self.assertIn("api-call", str(caught.exception))
        # The record is a sketch's interface: it draws, as the line the kind proposes.
        pictures = terrane.diagrams({"model": {"name": "Two"}, "systems": ["SYS-A", "SYS-B"], "interfaces": [record],
                                 "views": [{"view_id": "two", "title": "Two", "kind": "diagram", "layout": "LR",
                                            "scope": {"include": [{"type": "systems"}]},
                                            "edges": [{"via": "interfaces", "label": "protocol"}]}]}, date="2026-10-18")
        self.assertIn("HTTPS", pictures["two"].svg)
        self.assertIn("payments", terrane.examples())
        self.assertIn("views:", terrane.example("payments"))
        with self.assertRaises(QuickError):
            terrane.example("no-such")

    def test_the_door_exports_archimate_and_a_notebook_shows_every_picture(self) -> None:
        import tempfile
        repo = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            path, notes = terrane.export_archimate(repo, Path(tmp) / "estate.xml")
            self.assertTrue(path.is_file())
            self.assertIn("<model", path.read_text(encoding="utf-8")[:200])
            self.assertTrue(any("roadmaps" in n for n in notes))
        pictures = terrane.diagrams(EXAMPLE, date="2026-10-17")
        html = pictures._repr_html_()
        self.assertIn("<h3>", html)
        self.assertIn("<svg", html)
        self.assertEqual(html.count("<h3>"), len(pictures))

    def test_the_notes_say_what_validate_says(self) -> None:
        pictures = terrane.diagrams({"model": {"name": "Dangling"}, "systems": ["SYS-A"],
                                 "interfaces": [{"interface_id": "INT-1", "source_system_id": "SYS-A",
                                                 "target_system_id": "SYS-NOPE"}],
                                 "views": ["application-landscape"]}, date="2026-10-17")
        errors = [n for n in pictures.notes if n.startswith("validate: ERROR")]
        self.assertEqual(len(errors), 1, pictures.notes)
        self.assertIn("ref.dangling", errors[0])
        self.assertIn("SYS-NOPE", errors[0])
        summary = [n for n in pictures.notes if n.startswith("validate: 1 error(s)")]
        self.assertEqual(len(summary), 1, pictures.notes)
        self.assertIn("warning(s) (", summary[0])
        clean = terrane.diagrams(EXAMPLE, date="2026-10-17")
        self.assertFalse([n for n in clean.notes if "ERROR" in n], clean.notes)
        self.assertTrue(any(n.startswith("validate: 0 error(s)") for n in clean.notes), clean.notes)

    def test_a_product_on_a_shape_or_from_parts_in_one_call(self) -> None:
        sketch = terrane.on_shape("azure-digital-product", "Rewards Redemption", domain="Card Issuing",
                              answers={"account": "azure-cards-prod"}, modules=["async-worker"])
        self.assertEqual(sketch["products"][0]["product_id"], "PRD-REWARDS-REDEMPTION")
        self.assertEqual(sketch["products"][0]["archetype"], "azure-digital-product")
        self.assertEqual([v["use"] for v in sketch["views"]], ["product-architecture", "product-parts", "onboarding"])
        pictures = terrane.diagrams(sketch, date="2026-10-17")
        self.assertEqual(sorted(pictures), ["onboarding--PRD-REWARDS-REDEMPTION",
                                            "product-architecture--PRD-REWARDS-REDEMPTION",
                                            "product-parts--PRD-REWARDS-REDEMPTION"])
        self.assertIn("Rewards Redemption", pictures["product-architecture--PRD-REWARDS-REDEMPTION"].svg)
        assembled = terrane.from_parts("AWS", "Merchant portal", parts=["web-app-baseline", "async-worker"],
                                   domain="Payments", extra={"systems": [{"system_id": "SYS-CORE-LEDGER",
                                                                            "name": "Core ledger", "hosting": "On-prem"}]})
        self.assertEqual(assembled["products"][0]["compose"]["provider"], "AWS")
        self.assertEqual(assembled["systems"][0]["system_id"], "SYS-CORE-LEDGER")
        pictures = terrane.diagrams(assembled, date="2026-10-17")
        self.assertEqual(sorted(pictures), ["product-architecture--PRD-MERCHANT-PORTAL",
                                            "product-parts--PRD-MERCHANT-PORTAL"])
        self.assertIn("Merchant portal", pictures["product-parts--PRD-MERCHANT-PORTAL"].svg)

    def test_a_part_with_what_it_requires_in_one_call(self) -> None:
        sketch = terrane.part("mobile-channel")
        compose = sketch["products"][0]["compose"]
        # The requirement comes before the part, and the answers name themselves.
        self.assertEqual([m["module"] for m in compose["modules"]], ["api-service", "mobile-channel"])
        self.assertEqual(compose["provider"], "AWS")
        self.assertEqual(sketch["products"][0]["parameters"]["slug"], "sample")
        pictures = terrane.diagrams(sketch, date="2026-10-17")
        self.assertEqual(sorted(pictures), ["product-architecture--PRD-SAMPLE-MOBILE-CHANNEL",
                                            "product-parts--PRD-SAMPLE-MOBILE-CHANNEL"])
        svg = pictures["product-architecture--PRD-SAMPLE-MOBILE-CHANNEL"].svg
        self.assertIn("Mobile App", svg)
        self.assertIn("SYS-SAMPLE-API", svg)
        # A part that walks a list parameter gets one sample entry, so the
        # role the product creates is drawn as a role.
        roles = terrane.part("operator-role", "Azure", name="Sample role")
        self.assertEqual(roles["products"][0]["parameters"]["roles"][0]["id"], "sample-roles")
        # A part that makes no system has nothing the product views draw,
        # and the notes say so, as the parts page does.
        pictures = terrane.diagrams(roles, date="2026-10-17")
        self.assertEqual(dict(pictures), {})
        self.assertTrue(any("not drawn" in note for note in pictures.notes), pictures.notes)
        with self.assertRaises(QuickError) as caught:
            terrane.part("web-app-baseline")
        self.assertIn("no shipped part 'web-app-baseline'; the parts are", str(caught.exception))

    def test_refused_by_name(self) -> None:
        with self.assertRaises(QuickError) as caught:
            terrane.diagrams({"gadgets": ["G-1"]})
        self.assertIn("gadgets", str(caught.exception))
        with self.assertRaises(QuickError):
            terrane.diagrams("just a line of text")
        with self.assertRaises(TypeError):
            terrane.diagrams(42)
        with self.assertRaises(FileNotFoundError):
            terrane.diagrams("no-such-sketch.yaml")


if __name__ == "__main__":
    unittest.main()
