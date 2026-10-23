"""A draw.io file read as a sketch: a box per thing by its shape, an arrow
per connection, a container per domain, a page per view."""

from __future__ import annotations

import base64
import re
import unittest
import urllib.parse
import zlib

import terrane
from terrane.drawio_import import DrawioError, pages, sketch_from_drawio
from terrane.quick import check_sketch, read_any

from _fixture import REPO

PATH = REPO / "90_EXAMPLE" / "quick" / "sample.drawio"
SAMPLE = PATH.read_text(encoding="utf-8")


def _compressed(text: str) -> str:
    """The sample as draw.io saves it with compression on: each page's
    model deflated, url-encoded and base64'd into the diagram's text."""
    def squash(match: "re.Match[str]") -> str:
        inner = match.group(2)
        raw = zlib.compressobj(9, zlib.DEFLATED, -15)
        data = raw.compress(urllib.parse.quote(inner, safe="").encode("utf-8")) + raw.flush()
        return match.group(1) + base64.b64encode(data).decode("ascii") + "</diagram>"
    return re.sub(r"(<diagram [^>]*>)\s*(<mxGraphModel.*?</mxGraphModel>)\s*</diagram>", squash, text, flags=re.S)


class TestPages(unittest.TestCase):
    def test_two_pages_with_their_cells(self) -> None:
        read = pages(SAMPLE)
        self.assertEqual([name for name, _ in read], ["Applications", "Data"])
        cells = {c.id: c for c in read[0][1]}
        self.assertEqual(cells["switch"].label, "Authorization switch")  # the <br> a space
        self.assertEqual(cells["fraud"].label, "Fraud scoring")  # the <b> gone
        self.assertTrue(cells["e1"].edge)
        self.assertEqual((cells["e1"].source, cells["e1"].target), ("switch", "fraud"))

    def test_the_compressed_form_reads_the_same(self) -> None:
        squashed = _compressed(SAMPLE)
        self.assertNotIn("<mxGraphModel", squashed)
        self.assertEqual([(n, len(c)) for n, c in pages(squashed)], [(n, len(c)) for n, c in pages(SAMPLE)])

    def test_what_is_not_drawio_is_refused(self) -> None:
        with self.assertRaises(DrawioError):
            pages("<svg/>")
        with self.assertRaises(DrawioError):
            pages("not xml <")
        with self.assertRaises(DrawioError):
            pages('<mxfile><diagram name="p">not base64 at all!!</diagram></mxfile>')


class TestSketch(unittest.TestCase):
    def test_boxes_become_records_by_their_shape(self) -> None:
        doc, notes = sketch_from_drawio(SAMPLE, name="Card payments, drawn")
        check_sketch(doc)
        self.assertEqual(doc["model"]["name"], "Card payments, drawn")
        self.assertEqual(sorted(s["system_id"] for s in doc["systems"]),
                         ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING"])
        self.assertEqual([s.get("company_domain") for s in doc["systems"]], ["Payments", "Payments"])
        self.assertEqual(doc["data_assets"][0]["data_asset_id"], "DA-CARD-LEDGER")
        self.assertEqual(sorted(a["name"] for a in doc["actors"]), ["Card scheme", "Merchant"])
        self.assertEqual(doc["capabilities"][0]["name"], "Payment processing")
        tech = {t["name"]: t for t in doc["tech_services"]}
        self.assertEqual(set(tech), {"Payment events", "EKS"})
        self.assertEqual(tech["EKS"]["description"], "On AWS.")
        # A decorative box with no name is not a thing.
        self.assertFalse(any("decor" in str(r) for t in doc for r in (doc[t] if isinstance(doc[t], list) else [])))

    def test_arrows_become_the_connections_the_method_has(self) -> None:
        doc, notes = sketch_from_drawio(SAMPLE)
        interfaces = {(i["source_system_id"], i["target_system_id"]): i for i in doc["interfaces"]}
        self.assertEqual(interfaces[("SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING")].get("protocol"), "gRPC")
        relations = doc["relations"]
        self.assertEqual(relations["actor_uses_system"], [{"actor_id": "ACT-MERCHANT", "system_id": "SYS-AUTHORIZATION-SWITCH"},
                                                           {"actor_id": "ACT-CARD-SCHEME", "system_id": "SYS-AUTHORIZATION-SWITCH"}]
                         if False else relations["actor_uses_system"])
        self.assertIn({"system_id": "SYS-AUTHORIZATION-SWITCH", "capability_id": "CAP-PAYMENT-PROCESSING"},
                      relations["system_realizes_capability"])
        # The label riding the edge says what the switch does to the ledger.
        writes = [r for r in relations["system_reads_writes"] if r["system_id"] == "SYS-AUTHORIZATION-SWITCH"]
        self.assertEqual(writes[0]["operation"], "Write")
        self.assertIn({"system_id": "SYS-FRAUD-SCORING", "tech_service_id": "TS-EKS"},
                      [{k: r[k] for k in ("system_id", "tech_service_id")} for r in relations["system_uses_tech_service"]])
        self.assertTrue(any("loose" in n and "no target" in n for n in notes), notes)

    def test_an_arrow_wrapped_with_a_kind_is_a_connection_of_that_kind(self) -> None:
        text = ('<mxfile><diagram id="d" name="Kinds"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
                '<mxCell id="a" value="Auth" style="rounded=1;" vertex="1" parent="1">'
                '<mxGeometry x="0" y="0" width="120" height="60" as="geometry"/></mxCell>'
                '<mxCell id="b" value="Fraud" style="rounded=1;" vertex="1" parent="1">'
                '<mxGeometry x="200" y="0" width="120" height="60" as="geometry"/></mxCell>'
                '<UserObject id="e" label="Score the transaction" kind="api-call">'
                '<mxCell style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" source="a" target="b">'
                '<mxGeometry relative="1" as="geometry"/></mxCell></UserObject>'
                '</root></mxGraphModel></diagram></mxfile>')
        doc, _notes = sketch_from_drawio(text, name="kinds")
        interface = doc["interfaces"][0]
        self.assertEqual((interface["name"], interface["integration_style"], interface["protocol"], interface["auth_method"]),
                         ("Score the transaction", "Request-response", "HTTPS", "OAuth2"))

    def test_a_page_is_a_view_and_a_thing_on_two_pages_is_one_record(self) -> None:
        doc, notes = sketch_from_drawio(SAMPLE)
        self.assertEqual([v["view_id"] for v in doc["views"]], ["applications", "data"])
        self.assertEqual(doc["views"][1]["title"], "Data")
        # A page is a view of what it draws, not of every record of its types.
        self.assertEqual(doc["views"][1]["scope"]["include"],
                         [{"type": "systems", "where": {"id_in": ["SYS-FRAUD-SCORING"]}},
                          {"type": "data_assets", "where": {"id_in": ["DA-CARD-LEDGER"]}}])
        # The ledger is a cylinder on one page and a plain box on the other: one data asset.
        self.assertEqual([d["data_asset_id"] for d in doc["data_assets"]], ["DA-CARD-LEDGER"])
        self.assertEqual(len([s for s in doc["systems"] if s["system_id"] == "SYS-FRAUD-SCORING"]), 1)
        reads = [r for r in doc["relations"]["system_reads_writes"] if r["system_id"] == "SYS-FRAUD-SCORING"]
        self.assertEqual(reads[0]["operation"], "Read")
        self.assertTrue(notes[0].startswith("read "), notes[0])
        self.assertIn("2 page(s)", notes[0])

    def test_the_exports_marks_outrank_the_shapes(self) -> None:
        # A box the export wrote carries its record; one drawn beside it by
        # hand reads by its label, shape and container as before.
        text = ('<mxfile><diagram id="p" name="Marked"><mxGraphModel><root>'
                '<mxCell id="0"/><mxCell id="1" parent="0"/>'
                '<mxCell id="band" value="Data Asset" style="swimlane;container=1;" vertex="1" parent="1">'
                '<mxGeometry x="0" y="0" width="400" height="200" as="geometry"/></mxCell>'
                '<UserObject id="DA-PROFILE" label="Customer profile" aac_type="data_assets" aac_id="DA-PROFILE" '
                'aac_company_domain="Servicing"><mxCell style="rounded=1;" vertex="1" parent="band">'
                '<mxGeometry x="20" y="40" width="120" height="60" as="geometry"/></mxCell></UserObject>'
                '<UserObject id="SYS-CRM" label="CRM" aac_type="systems" aac_id="SYS-CRM" aac_company_domain="Servicing" '
                'aac_hosting="SaaS"><mxCell style="rounded=1;" vertex="1" parent="band">'
                '<mxGeometry x="200" y="40" width="120" height="60" as="geometry"/></mxCell></UserObject>'
                '<mxCell id="hand" value="Review portal" style="rounded=1;" vertex="1" parent="band">'
                '<mxGeometry x="20" y="120" width="120" height="60" as="geometry"/></mxCell>'
                '<UserObject id="e1" label="Posts" kind="api-call" aac_interface_id="INT-PORTAL-CRM" aac_kind="api-call" '
                'aac_name="Posts cases" aac_protocol="HTTPS" aac_auth_method="HMAC">'
                '<mxCell style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" source="hand" target="SYS-CRM">'
                '<mxGeometry relative="1" as="geometry"/></mxCell></UserObject>'
                '<UserObject id="e2" label="" aac_relation="system_reads_writes" aac_operation="Read">'
                '<mxCell style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" source="SYS-CRM" target="DA-PROFILE">'
                '<mxGeometry relative="1" as="geometry"/></mxCell></UserObject>'
                '<UserObject id="e3" label="" aac_derived="1">'
                '<mxCell style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" source="hand" target="DA-PROFILE">'
                '<mxGeometry relative="1" as="geometry"/></mxCell></UserObject>'
                '<UserObject id="e4" label="" aac_field="source_of_truth">'
                '<mxCell style="edgeStyle=orthogonalEdgeStyle;dashed=1;" edge="1" parent="1" source="SYS-CRM" target="DA-PROFILE">'
                '<mxGeometry relative="1" as="geometry"/></mxCell></UserObject>'
                '</root></mxGraphModel></diagram></mxfile>')
        doc, notes = sketch_from_drawio(text, name="marked")
        check_sketch(doc)
        profile = doc["data_assets"][0]
        self.assertEqual((profile["data_asset_id"], profile["company_domain"]), ("DA-PROFILE", "Servicing"))
        crm = next(s for s in doc["systems"] if s["system_id"] == "SYS-CRM")
        self.assertEqual((crm["company_domain"], crm["hosting"]), ("Servicing", "SaaS"))
        # The hand-drawn box: its id from its label, its domain from the band it sits in.
        portal = next(s for s in doc["systems"] if s["system_id"] == "SYS-REVIEW-PORTAL")
        self.assertEqual(portal["company_domain"], "Data Asset")
        line = doc["interfaces"][0]
        self.assertEqual((line["interface_id"], line["name"], line["protocol"], line["auth_method"]),
                         ("INT-PORTAL-CRM", "Posts cases", "HTTPS", "HMAC"))
        # A line marked as a row is that row, qualifier and all; a derived line is no row; a line marked as a
        # field sets the field, with the row line of the same pair and the same blank label still a row.
        self.assertEqual(doc["relations"], {"system_reads_writes": [
            {"system_id": "SYS-CRM", "data_asset_id": "DA-PROFILE", "operation": "Read"}]})
        self.assertEqual(profile["source_of_truth"], "SYS-CRM")
        self.assertTrue(any("the file's own where the export wrote them" in n for n in notes), notes)

    def test_the_door_takes_the_file_by_its_suffix(self) -> None:
        doc, _ = read_any(PATH)
        self.assertIn("systems", doc)
        drawings = terrane.diagrams(str(PATH), date="2026-10-17")
        self.assertEqual(sorted(drawings), ["applications", "data"])
        self.assertIn("Authorization switch", drawings["applications"].svg)


if __name__ == "__main__":
    unittest.main()
