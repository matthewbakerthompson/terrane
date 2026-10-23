"""The draw.io export: every picture as a page, each box where the engine
put it, in the styles the reader takes back, so a page exported and read
again is the sketch it came from."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

import terrane
from terrane.drawio_import import pages, sketch_from_drawio
from terrane.draw.svg import Scene, SceneBoundary, SceneEdge, SceneNode
from terrane.join import join_estate
from terrane.quick import check_sketch, read_any
from terrane.render_drawio import _along, boundary_style, diagram_xml, edge_style, node_style, render_drawio

from _fixture import REPO, Sandbox

VISIO = REPO / "90_EXAMPLE" / "quick" / "sample.vsdx"


def _node(node_id: str, type_name: str, shape: str, x: float, y: float, parent=None, **extra) -> SceneNode:
    fields = dict(id=node_id, shape=shape, x=x, y=y, w=120, h=40, fill="#c7d6ff", stroke="#4338ca", width=1.4,
                  dash="solid", label=node_id.title(), ink="#0f172a", tech="", faded=False, type=type_name,
                  parent=parent)
    fields.update(extra)
    return SceneNode(**fields)


class TestStyles(unittest.TestCase):
    def test_a_box_is_styled_by_its_type_where_the_reader_knows_it(self) -> None:
        self.assertTrue(node_style(_node("a", "data_assets", "barrel", 0, 0)).startswith("shape=cylinder3;"))
        self.assertTrue(node_style(_node("a", "actors", "ellipse", 0, 0)).startswith("ellipse;"))
        self.assertTrue(node_style(_node("a", "policies", "cut-rectangle", 0, 0)).startswith("shape=document;"))
        self.assertTrue(node_style(_node("a", "controls", "octagon", 0, 0)).startswith("shape=mxgraph.basic.octagon2;"))
        # A type the reader does not know is drawn by the painter's shape.
        self.assertTrue(node_style(_node("a", "work_packages", "round-diamond", 0, 0)).startswith("rhombus;rounded=1;"))
        self.assertTrue(node_style(_node("a", "systems", "round-rectangle", 0, 0)).startswith("rounded=1;"))
        style = node_style(_node("a", "systems", "round-rectangle", 0, 0, faded=True, dash="dashed"))
        self.assertIn("fillColor=#c7d6ff;strokeColor=#4338ca;fontColor=#0f172a;strokeWidth=1.4;", style)
        self.assertIn("dashed=1;", style)
        self.assertIn("opacity=55;", style)

    def test_a_line_follows_its_bends_or_runs_straight_or_curves(self) -> None:
        bent = SceneEdge("e", "a", "b", [(0, 0), (40, 0), (40, 30)], False, "solid", "", None, None)
        self.assertIn("edgeStyle=orthogonalEdgeStyle;", edge_style(bent, True))
        straight = SceneEdge("e", "a", "b", [(0, 0), (40, 30)], False, "dotted", "", None, None)
        self.assertNotIn("edgeStyle", edge_style(straight, True))
        self.assertIn("dashed=1;dashPattern=1 2;", edge_style(straight, True))
        curved = SceneEdge("e", "a", "b", [(0, 0), (20, 40), (40, 0)], True, "solid", "", None, None)
        self.assertIn("curved=1;", edge_style(curved, False))
        self.assertIn("opacity=45;", edge_style(curved, False))
        self.assertIn("strokeWidth=1.3;", edge_style(curved, False))

    def test_a_boundary_is_a_container_the_reader_takes_for_a_domain(self) -> None:
        b = SceneBoundary("grp::Payments", (0, 0, 300, 200), "#f3f5fb", "#8f9bb5", 1.0, "dashed", ["Payments"],
                          "#3b4a6b", 1, None)
        self.assertIn("container=1;", boundary_style(b))
        self.assertIn("dashed=1;", boundary_style(b))


class TestPage(unittest.TestCase):
    def test_boxes_sit_in_their_boundaries_in_the_boundarys_own_coordinates(self) -> None:
        boundary = SceneBoundary("grp::Payments", (100, 100, 400, 300), "#f3f5fb", "#8f9bb5", 1.0, "solid",
                                 ["Payments"], "#3b4a6b", 1, None)
        inside = _node("SYS-A", "systems", "round-rectangle", 200, 150, parent="grp::Payments")
        outside = _node("SYS-B", "systems", "round-rectangle", 600, 150, tech="Azure")
        edge = SceneEdge("e0", "SYS-A", "SYS-B", [(260, 150), (400, 150), (400, 170), (540, 170)], False, "solid",
                         "HTTPS", (400, 160), (380, 152, 420, 168))
        scene = Scene((100, 100, 660, 300), [boundary], [edge], [inside, outside], True, "dagre")
        xml = diagram_xml(scene)
        root = ET.fromstring(xml)
        cells = {c.get("id"): c for c in root.iter("mxCell") if c.get("id")}
        # The drawing's corner sits a margin in from the page's.
        self.assertEqual(cells["grp::Payments"].find("mxGeometry").attrib["x"], "20")
        self.assertEqual(cells["SYS-A"].get("parent"), "grp::Payments")
        self.assertEqual(cells["SYS-A"].find("mxGeometry").attrib, {"x": "40", "y": "30", "width": "120", "height": "40",
                                                                   "as": "geometry"})
        # A box with a technology line is a UserObject, the line its tooltip.
        objects = {o.get("id"): o for o in root.iter("UserObject")}
        self.assertEqual(objects["SYS-B"].get("tooltip"), "Azure")
        self.assertEqual(objects["SYS-B"].get("label"), "Sys-B")
        self.assertEqual(cells["e0"].get("value"), "HTTPS")
        geometry = cells["e0"].find("mxGeometry")
        points = [(p.get("x"), p.get("y")) for p in geometry.find("Array").iter("mxPoint")]
        self.assertEqual(points, [("320", "70"), ("320", "90")])
        # The label sits where the engine put it, half way along the line
        # on the upright run, said as draw.io says it: the share along the
        # line, and the rest as an offset.
        self.assertEqual(geometry.get("x"), "0")
        offset = geometry.find("mxPoint[@as='offset']")
        self.assertEqual((offset.get("x"), offset.get("y")), ("0", "0"))
        self.assertEqual(_along([(0, 0), (100, 0), (100, 50)], (50, -10)), (1 / 3, (50.0, 0.0)))
        self.assertEqual(root.get("pageWidth"), "600")

    def test_the_file_is_the_same_bytes_twice(self) -> None:
        drawings = terrane.diagrams(str(VISIO), date="2026-10-17")
        pages_ = [(name, d.title, d.scene) for name, d in drawings.items() if d.scene is not None]
        self.assertEqual(render_drawio(pages_), render_drawio(pages_))
        self.assertNotIn("modified=", render_drawio(pages_))


class TestRoundTrip(unittest.TestCase):
    def test_a_connection_of_a_kind_keeps_its_kind_through_the_file(self) -> None:
        from terrane.connections import kind_of, load_connections
        from terrane.shipped import shipped_root

        link = terrane.connect("SYS-A", "SYS-B", "queued-request", name="Post the authorization")
        sketch = {"model": {"name": "Two"},
                  "systems": [{"system_id": "SYS-A", "name": "A"}, {"system_id": "SYS-B", "name": "B"}],
                  "interfaces": [link],
                  "views": [{"view_id": "two", "title": "Two", "kind": "diagram", "layout": "LR",
                             "scope": {"include": [{"type": "systems"}]},
                             "edges": [{"via": "interfaces", "label": "protocol"}]}]}
        drawings = terrane.diagrams(sketch, date="2026-10-17")
        out = Path(tempfile.mkdtemp(prefix="aac-drawio-")) / "two.drawio"
        drawings.drawio(out)
        text = out.read_text(encoding="utf-8")
        self.assertIn('kind="queued-request"', text)
        doc, _notes = sketch_from_drawio(text, name="back")
        back = doc["interfaces"][0]
        self.assertEqual(kind_of(back, load_connections(shipped_root())), "queued-request")
        self.assertEqual((back["integration_style"], back["protocol"]), ("Request-response", "MQ"))

    def test_an_estates_own_kinds_ride_its_lines_and_come_back(self) -> None:
        from collections import Counter

        from terrane.connections import kind_of, load_connections
        from terrane.quick import read_any

        thurman = REPO / "90_EXAMPLE" / "thurman-health"
        out = Path(tempfile.mkdtemp(prefix="aac-drawio-")) / "thurman.drawio"
        path, _notes = terrane.export_drawio(thurman, out, views=["application-landscape"])
        text = Path(path).read_text(encoding="utf-8")
        self.assertGreater(text.count('kind="hl7v2-feed"'), 10)
        theirs, _ = read_any(Path(path), root=thurman)
        kinds = load_connections(thurman)
        self.assertGreater(Counter(kind_of(i, kinds) for i in theirs["interfaces"])["hl7v2-feed"], 10)

    def test_a_sketch_exported_and_read_again_is_the_sketch(self) -> None:
        drawings = terrane.diagrams(str(VISIO), date="2026-10-17")
        out = Path(tempfile.mkdtemp(prefix="aac-drawio-")) / "visio.drawio"
        drawings.drawio(out)
        text = out.read_text(encoding="utf-8")
        self.assertEqual([name for name, _ in pages(text)], ["Applications", "Data"])
        doc, notes = sketch_from_drawio(text, name="back")
        check_sketch(doc)
        self.assertEqual(sorted(s["system_id"] for s in doc["systems"]),
                         ["SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING"])
        self.assertEqual([s.get("company_domain") for s in doc["systems"]], ["Payments", "Payments"])
        self.assertEqual(sorted(d["data_asset_id"] for d in doc["data_assets"]), ["DA-CARD-LEDGER", "DA-REPORTING-MART"])
        self.assertEqual(doc["actors"][0]["actor_id"], "ACT-MERCHANT")
        self.assertEqual(doc["capabilities"][0]["capability_id"], "CAP-PAYMENT-PROCESSING")
        self.assertEqual(doc["tech_services"][0]["tech_service_id"], "TS-KUBERNETES-CLUSTER")
        self.assertEqual(doc["policies"][0]["policy_id"], "POL-CARD-DATA-STAYS-IN-THE-PCI-ZONE")
        interfaces = {(i["source_system_id"], i["target_system_id"]): i for i in doc["interfaces"]}
        self.assertEqual(interfaces[("SYS-AUTHORIZATION-SWITCH", "SYS-FRAUD-SCORING")].get("protocol"), "gRPC")
        self.assertEqual({k: len(v) for k, v in doc["relations"].items()},
                         {"system_reads_writes": 2, "actor_uses_system": 1, "system_realizes_capability": 1,
                          "system_uses_tech_service": 1, "data_subject_to_policy": 1})

    def test_the_estates_own_export_reads_back_as_the_estate(self) -> None:
        # Read back unchanged with --correct, the export would have added
        # 168 systems and 150 interfaces and "corrected" a data asset's
        # domain to "Data Asset": ids off the labels, types off the shapes,
        # domains off the bands. The boxes and lines carry the records now.
        with Sandbox(seed=True) as root:
            out = Path(tempfile.mkdtemp(prefix="aac-drawio-")) / "estate.drawio"
            path, _notes = terrane.export_drawio(str(root), out, views=["system-context", "application-landscape",
                                                                    "capability-map", "data-landscape",
                                                                    "framework-landscape"])
            text = path.read_text(encoding="utf-8")
            self.assertIn('aac_type="systems"', text)
            self.assertIn('aac_interface_id="INT-', text)
            doc, notes = read_any(path, root)
            self.assertTrue(any("the file's own where the export wrote them" in n for n in notes), notes)
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="estate.drawio", correct=True,
                                 dry_run=True)
            self.assertEqual(result.changed, {}, result.changes)
            self.assertEqual(result.added, {})
            self.assertEqual(result.rows_added, 0)
            # A reviewer in the tool they know: a label renamed and a line
            # drawn between two systems on the landscape. Read back, one
            # correction and one new interface, nothing else.
            self.assertIn('label="Dynamics 365 Customer Service"', text)
            edited = text.replace('label="Dynamics 365 Customer Service"', 'label="Dynamics 365 Customer Service (reviewed)"')
            at = edited.index('<diagram id="application-landscape"')
            end = edited.index("</root>", at)
            line = ('<mxCell id="hand-1" value="Requests statements" style="edgeStyle=orthogonalEdgeStyle;" edge="1" '
                    'parent="1" source="SYS-CRM" target="SYS-STATEMENTS"><mxGeometry relative="1" as="geometry"/></mxCell>')
            reviewed = out.parent / "reviewed.drawio"
            reviewed.write_text(edited[:end] + line + edited[end:], encoding="utf-8")
            doc, _ = read_any(reviewed, root)
            result = join_estate(doc, root, owner="ORG-PAYMENTS", source_name="reviewed.drawio", correct=True,
                                 dry_run=True)
            self.assertEqual(result.changed, {"systems": ["SYS-CRM"]}, result.changes)
            self.assertEqual(result.added, {"interfaces": ["INT-CRM-STATEMENTS"]})
            self.assertEqual(result.rows_added, 0)

    def test_the_estate_exports_named_views_a_tile_map_among_them(self) -> None:
        out = Path(tempfile.mkdtemp(prefix="aac-drawio-")) / "estate.drawio"
        path, notes = terrane.export_drawio(REPO, out, views=["system-context", "capability-map"])
        text = path.read_text(encoding="utf-8")
        # Pages come in the order the views are loaded, by id.
        names = [name for name, _ in pages(text)]
        self.assertEqual(names, ["Capability Map", "System Context"])
        root = ET.fromstring(text)
        diagrams = list(root.iter("diagram"))
        self.assertEqual([d.get("id") for d in diagrams], ["capability-map", "system-context"])
        # The context has lines; the map, with nothing connected, has its tiles in their bands and none.
        self.assertGreater(len([c for c in diagrams[1].iter("mxCell") if c.get("edge") == "1"]), 0)
        self.assertEqual(len([c for c in diagrams[0].iter("mxCell") if c.get("edge") == "1"]), 0)
        self.assertGreater(len([c for c in diagrams[0].iter("mxCell") if "container=1" in (c.get("style") or "")]), 0)
        self.assertFalse(any("left out" in n for n in notes), notes)


if __name__ == "__main__":
    unittest.main()
