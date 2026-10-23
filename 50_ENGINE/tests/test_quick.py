"""One file, drawn: the quick door holds what the repository holds.

A sketch is a small model and the views it wants in one file. The tests
hold that the example draws every view it names and its flow, that a bare
sketch of ids gets the defaults a drawing needs and is told so, that a
shipped view is usable by name and a written one by its id, that a view
with a subject binds, that a wrong name is refused with the shipped names
in the message, and that the pictures are the same bytes twice.
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
from terrane.quick import EXAMPLE, QuickError, draw_sketch, fill_defaults, read_sketch  # noqa: E402

from _fixture import REPO  # noqa: E402


def _ids(svg: str, cls: str):
    root = ET.fromstring(svg)
    return {el.get("data-id") for el in root.iter() if el.get("class") == cls}


class TestExample(unittest.TestCase):
    def test_the_example_draws_its_views_and_its_flow(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-quick-"))
        written, notes = draw_sketch(EXAMPLE, out, mermaid=True)
        names = sorted(p.name for p in written)
        self.assertIn("payments--system-context.svg", names)
        self.assertIn("payments--application-landscape.svg", names)
        self.assertIn("payments--payments-by-hosting.svg", names)
        self.assertIn("payments--FLOW-AUTH.svg", names)
        self.assertIn("payments--payments-by-hosting.mmd", names)
        hosting = (out / "payments--payments-by-hosting.svg").read_text(encoding="utf-8")
        self.assertEqual(_ids(hosting, "node"), {"SYS-MOBILE", "SYS-AUTH", "SYS-FRAUD", "SYS-LEDGER", "SYS-STATEMENTS"})
        self.assertIn("ORG-SKETCH", " ".join(notes))
        self.assertFalse(any("not drawn" in n for n in notes), notes)
        context = (out / "payments--system-context.svg").read_text(encoding="utf-8")
        self.assertTrue({"ACT-CARDHOLDER", "ACT-MERCHANT"} <= _ids(context, "node"))

    def test_same_bytes_twice(self) -> None:
        a, b = Path(tempfile.mkdtemp(prefix="aac-quick-")), Path(tempfile.mkdtemp(prefix="aac-quick-"))
        draw_sketch(EXAMPLE, a)
        draw_sketch(EXAMPLE, b)
        for path in sorted(a.glob("*.svg")):
            self.assertEqual(path.read_bytes(), (b / path.name).read_bytes(), path.name)

    def test_the_command_prints_what_it_drew_and_the_example(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-quick-"))
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["draw", str(EXAMPLE), "--out", str(out)])
        self.assertEqual(code, 0, text.getvalue())
        self.assertIn("file(s) drawn", text.getvalue())
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["draw", "--example"])
        self.assertEqual(code, 0)
        self.assertEqual(text.getvalue(), EXAMPLE.read_text(encoding="utf-8"))
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["draw", "--views"])
        self.assertEqual(code, 0)
        listing = text.getvalue()
        self.assertIn("system-context", listing)
        self.assertIn("product-architecture", listing)
        self.assertIn("product ", listing.split("product-architecture", 1)[1][:40])
        # The fields a view reads are listed, so a sketch knows what to set.
        landscape = listing.split("application-landscape", 1)[1].split("\n", 1)[0]
        self.assertIn("company_domain, criticality", landscape)
        self.assertNotIn("id_in", listing)


class TestPresets(unittest.TestCase):
    """A product on a shipped shape, or assembled from the library's parts,
    from one file: the landing zones stand in, the asks are answered and
    said, and the pictures hold what the shape or the parts made."""

    def test_a_product_on_a_shipped_shape(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-quick-"))
        written, notes = draw_sketch(EXAMPLE.parent / "on-a-shape.yaml", out)
        self.assertEqual(sorted(p.name for p in written),
                         ["on-a-shape--onboarding--PRD-REWARDS.svg", "on-a-shape--product-architecture--PRD-REWARDS.svg",
                          "on-a-shape--product-parts--PRD-REWARDS.svg"])
        nodes = _ids((out / "on-a-shape--product-architecture--PRD-REWARDS.svg").read_text(encoding="utf-8"), "node")
        # The shape's systems, the part the file added, the data, and the
        # landing zone's bus the event publisher is bound to.
        self.assertTrue({"SYS-REWARDS-API", "SYS-REWARDS-WEB", "SYS-REWARDS-WORKER", "SYS-REWARDS-EVENTS",
                         "DA-REWARDS-OPERATIONAL", "TS-AZURE-SERVICEBUS"} <= nodes, nodes)
        joined = " | ".join(notes)
        self.assertIn("landing zones stand in", joined)
        self.assertIn("the shape asked for", joined)
        self.assertIn("slug=rewards", joined)
        self.assertIn("owner_org=ORG-SKETCH", joined)
        self.assertIn("domain=Card Issuing", joined)
        # The steward the shape's data asset names is not the sketch's: it stands in, and nothing dangles.
        self.assertIn("ORG-DATAENG named by what the shape made and not in the sketch; stands in as org unit", joined)
        self.assertFalse(any(n.startswith("validate: ERROR") for n in notes), notes)
        self.assertNotIn("account=", joined, "the sketch said the account; it is not an answer")
        self.assertFalse(any("not drawn" in n for n in notes), notes)

    def test_a_product_from_parts(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-quick-"))
        written, notes = draw_sketch(EXAMPLE.parent / "from-parts.yaml", out)
        self.assertEqual(sorted(p.name for p in written),
                         ["from-parts--product-architecture--PRD-PORTAL.svg", "from-parts--product-parts--PRD-PORTAL.svg"])
        nodes = _ids((out / "from-parts--product-parts--PRD-PORTAL.svg").read_text(encoding="utf-8"), "node")
        self.assertTrue({"SYS-PORTAL-API", "SYS-PORTAL-WEB", "SYS-PORTAL-EDGE", "SYS-PORTAL-DB", "SYS-PORTAL-WORKER",
                         "DA-PORTAL-OPERATIONAL", "TS-AWS-MSK"} <= nodes, nodes)
        joined = " | ".join(notes)
        self.assertIn("the parts asked for", joined)
        self.assertIn("product_name=Merchant portal", joined)
        self.assertIn("slug=portal", joined)
        self.assertIn("ORG-DATAENG named by what the shape made and not in the sketch; stands in as org unit", joined)
        self.assertFalse(any(n.startswith("validate: ERROR") for n in notes), notes)

    def test_a_sketch_with_its_own_tech_services_keeps_them(self) -> None:
        path = Path(tempfile.mkdtemp(prefix="aac-quick-")) / "mine.yaml"
        path.write_text(
            "tech_services:\n  - tech_service_id: TS-MINE\n    name: My platform\n"
            "products:\n  - product_id: PRD-X\n    name: X\n"
            "    compose:\n      provider: AWS\n      modules: [{module: web-app-baseline}]\n"
            "views:\n  - use: product-parts\n    with: {product: PRD-X}\n", encoding="utf-8")
        written, notes = draw_sketch(path)
        self.assertEqual([p.name for p in written], ["mine--product-parts--PRD-X.svg"])
        # The sketch's own service is kept, and the shipped landing zones
        # stand in beside it for every kind it does not answer.
        self.assertTrue(any("shipped landing zones stand in" in n for n in notes), notes)

    def test_a_sketch_names_its_own_landing_zone_in_a_few_words(self) -> None:
        path = Path(tempfile.mkdtemp(prefix="aac-quick-")) / "zone.yaml"
        path.write_text(
            "landing_zone:\n  provider: Azure\n  services:\n    message-queue: Our Service Bus\n"
            "    secrets-manager: Our Vault\n"
            "products:\n  - product_id: PRD-R\n    name: R\n    archetype: azure-digital-product\n"
            "    parameters: {account: azure-x}\n"
            "views:\n  - use: product-architecture\n    with: {product: PRD-R}\n", encoding="utf-8")
        written, notes = draw_sketch(path)
        nodes = _ids(written[0].read_text(encoding="utf-8"), "node")
        # The shape's bus is the sketch's own; the rest of the zone stands in.
        self.assertIn("TS-AZURE-OUR-SERVICE-BUS", nodes)
        self.assertNotIn("TS-AZURE-SERVICEBUS", nodes)
        self.assertIn("TS-AZURE-AKS", nodes)
        joined = " | ".join(notes)
        self.assertIn("landing zone on Azure: 2 service(s) from the sketch", joined)
        self.assertIn("answers 2 kind(s); the shipped landing zones stand in for the rest", joined)
        # A kind the library does not know is refused with the kinds it does.
        path.write_text("landing_zone:\n  provider: AWS\n  services:\n    teapot: Kettle\n"
                        "systems: [SYS-A]\nviews: [application-landscape]\n", encoding="utf-8")
        with self.assertRaises(QuickError) as caught:
            draw_sketch(path)
        self.assertIn("'teapot' is not a kind", str(caught.exception))
        self.assertIn("message-queue", str(caught.exception))
        path.write_text("landing_zone: AWS\nsystems: [SYS-A]\n", encoding="utf-8")
        with self.assertRaises(QuickError):
            draw_sketch(path)

    def test_the_library_is_listed_and_the_examples_are_named(self) -> None:
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["draw", "--library"])
        self.assertEqual(code, 0)
        listing = text.getvalue()
        self.assertIn("azure-digital-product", listing)
        self.assertIn("slug*", listing)
        self.assertIn("web-app-baseline", listing)
        self.assertIn("api-service, web-channel, public-web-entry, relational-datastore", listing)
        self.assertIn("event-service-baseline", listing)
        self.assertIn("source_system*", listing)
        self.assertNotIn("[", listing, "a list default is not a column")
        self.assertIn("landing zone kind", listing)
        self.assertIn("Azure API Management", listing)
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["draw", "--example", "from-parts"])
        self.assertEqual(code, 0)
        self.assertEqual(text.getvalue(), (EXAMPLE.parent / "from-parts.yaml").read_text(encoding="utf-8"))
        text = io.StringIO()
        with redirect_stdout(text):
            code = cli.main(["draw", "--example", "no-such"])
        self.assertEqual(code, 1)
        self.assertIn("from-parts, on-a-shape, payments", text.getvalue())


class TestDefaults(unittest.TestCase):
    def _write(self, text: str) -> Path:
        path = Path(tempfile.mkdtemp(prefix="aac-quick-")) / "sketch.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_sketch_of_ids_is_enough(self) -> None:
        path = self._write(
            "systems:\n  - SYS-A\n  - SYS-B\n"
            "interfaces:\n  - interface_id: INT-AB\n    source_system_id: SYS-A\n    target_system_id: SYS-B\n"
            "    protocol: HTTPS\n"
            "views: [application-landscape]\n")
        doc = read_sketch(path)
        entities, notes = fill_defaults(doc)
        system = entities["systems"][0]
        self.assertEqual((system["name"], system["status"], system["criticality"], system["owner_org_id"]),
                         ("SYS-A", "Active", "Medium", "ORG-SKETCH"))
        self.assertEqual(entities["interfaces"][0]["name"], "SYS-A to SYS-B")
        self.assertTrue(any("ORG-SKETCH" in n for n in notes))
        written, notes = draw_sketch(path)
        self.assertEqual([p.name for p in written], ["sketch--application-landscape.svg"])
        self.assertEqual(_ids(written[0].read_text(encoding="utf-8"), "node"), {"SYS-A", "SYS-B"})

    def test_a_view_with_a_subject_binds(self) -> None:
        path = self._write(
            "org_units:\n  - org_unit_id: ORG-X\n    name: X\n"
            "products:\n  - product_id: PRD-X\n    name: X\n    owner_org_id: ORG-X\n"
            "systems:\n  - system_id: SYS-X\n    name: X api\n    owner_org_id: ORG-X\n    criticality: High\n"
            "relations:\n  product_includes_system:\n    - product_id: PRD-X\n      system_id: SYS-X\n"
            "views:\n  - use: product-architecture\n    with: {product: PRD-X}\n")
        written, notes = draw_sketch(path)
        self.assertEqual([p.name for p in written], ["sketch--product-architecture--PRD-X.svg"])
        self.assertIn("SYS-X", _ids(written[0].read_text(encoding="utf-8"), "node"))

    def test_a_wrong_view_name_is_refused_with_the_shipped_names(self) -> None:
        path = self._write("systems: [SYS-A]\nviews: [no-such-view]\n")
        with self.assertRaises(QuickError) as caught:
            draw_sketch(path)
        self.assertIn("no shipped view called 'no-such-view'", str(caught.exception))
        self.assertIn("system-context", str(caught.exception))

    def test_a_key_the_sketch_does_not_take_is_refused(self) -> None:
        path = self._write("gadgets: [G-1]\n")
        with self.assertRaises(QuickError) as caught:
            read_sketch(path)
        self.assertIn("gadgets", str(caught.exception))

    def test_a_view_that_selects_nothing_is_refused_with_the_reason(self) -> None:
        path = self._write("systems: [SYS-A]\nviews: [system-context]\n")
        written, notes = draw_sketch(path)
        self.assertEqual(written, [])
        self.assertTrue(any("system-context: not drawn" in n and "selected no entities" in n for n in notes), notes)


class TestReadingForAnEstate(unittest.TestCase):
    def test_a_drawing_read_for_an_estate_is_read_with_its_own_kinds(self) -> None:
        import io
        from contextlib import redirect_stdout

        from terrane import cli
        from terrane.quick import read_any

        thurman = REPO / "90_EXAMPLE" / "thurman-health"
        folder = Path(tempfile.mkdtemp(prefix="aac-kinds-"))
        source = folder / "feeds.mmd"
        source.write_text("flowchart LR\n  ehr[EHR] -->|HL7 v2 feed| lab[Lab system]\n", encoding="utf-8")
        # Drawn alone, the words are a name: the shipped kinds have no HL7 feed.
        plain, _notes = read_any(source)
        self.assertEqual(plain["interfaces"][0].get("name"), "HL7 v2 feed")
        self.assertNotIn("integration_style", plain["interfaces"][0])
        # Read for the health system, whose library names the kind, the arrow is of that kind.
        theirs, notes = read_any(source, root=thurman)
        self.assertEqual((theirs["interfaces"][0]["integration_style"], theirs["interfaces"][0]["protocol"]),
                         ("Event", "MLLP"))
        self.assertTrue(any("of the kind hl7v2-feed" in n for n in notes), notes)
        # And so by the command, which reads for the estate it adopts into.
        with redirect_stdout(io.StringIO()) as out:
            code = cli.main(["--root", str(thurman), "adopt", str(source), "--dry-run"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("of the kind hl7v2-feed", out.getvalue())


class TestLibraryListing(unittest.TestCase):
    def test_with_a_root_the_listing_is_the_estates(self) -> None:
        import io
        from contextlib import redirect_stdout

        from terrane import cli

        thurman = REPO / "90_EXAMPLE" / "thurman-health"
        with redirect_stdout(io.StringIO()) as out:
            code = cli.main(["--root", str(thurman), "draw", "--library"])
        self.assertEqual(code, 0)
        self.assertIn("hl7v2-feed", out.getvalue())
        with redirect_stdout(io.StringIO()) as plain:
            cli.main(["draw", "--library"])
        self.assertNotIn("hl7v2-feed", plain.getvalue())

    def test_the_listing_names_the_connection_kinds_and_what_each_proposes(self) -> None:
        from terrane.quick import shipped_library_text

        text = shipped_library_text()
        self.assertIn("connection kind", text)
        line = next(l for l in text.splitlines() if l.startswith("api-call"))
        self.assertIn("Request-response", line)
        self.assertIn("HTTPS, OAuth2, Realtime, Outbound", line)


if __name__ == "__main__":
    unittest.main()
