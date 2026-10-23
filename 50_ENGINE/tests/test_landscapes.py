"""Tests for the frameworks: where a capability is placed, the landscape
drawn from that, and the grid of every framework against every domain.

What is checked: every placement is a path in its framework's own terms,
written by the importer from the business layer's words; one landscape
view, bound per framework, draws exactly the capabilities placed in it,
nested by the first two levels of the path (`relation@target#n`), with
BIAN opening on its business areas and ITIL on its groups of practices; a
path level that is not a number from one, a key that names no relation, or
a relation with nothing to group by is refused; binding fills the token in
the scope's keys and the grouping as well as in the values; the whole map
carries each capability's frameworks for the app's lens; and the frameworks
report is the grid, its marks the domains' alignment rows and its counts
the capabilities placed under each domain.
"""

from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from terrane.blocks import load_components  # noqa: E402
from terrane.icons import IconMap, web_dir  # noqa: E402
from terrane.matrix import matrix_of  # noqa: E402
from terrane.palette import Palette  # noqa: E402
from terrane.payload import graph_payload  # noqa: E402
from terrane.query import PATH_SEPARATOR, ViewError, bind, parse_view, render_targets, resolve  # noqa: E402
from terrane.draw.table import render_table_svg  # noqa: E402
from terrane.render_mermaid import render_table  # noqa: E402

import import_business_layer as business  # noqa: E402

from _fixture import REPO, seeded_model, seeded_root, seeded_views, setup_shared, teardown_shared  # noqa: E402

REFERENCES = "capability_references_framework"


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _placements(model, framework_id):
    out = {}
    for row in model.relation_rows(REFERENCES):
        if row.get("framework_id") == framework_id:
            out.setdefault(str(row["capability_id"]), []).append(str(row["ref"]))
    return out


def _probe(group_by, where=None):
    return parse_view({
        "view_id": "probe", "kind": "map", "group_by": group_by,
        "scope": {"include": [{"type": "capabilities", "where": where or {"capability_level": ["L1"]}}]},
        "edges": [],
    })


class TestPlacements(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def test_a_framework_with_levels_is_placed_by_path(self) -> None:
        """BIAN's area, domain and service domain; ITIL's group and practice;
        CRI's function and statement. None stands alone: a term the
        importer could not place would be drawn under its own name, outside
        any area, and nobody would know why."""
        depth = {"FW-BIAN": 3, "FW-ITIL": 2, "FW-CRI": 2}
        for framework_id, levels in depth.items():
            with self.subTest(framework=framework_id):
                refs = [r for rs in _placements(self.model, framework_id).values() for r in rs]
                self.assertTrue(refs)
                for ref in refs:
                    self.assertEqual(len(ref.split(PATH_SEPARATOR)), levels, ref)

    def test_the_importer_writes_the_path_from_the_layers_words(self) -> None:
        places = {"Customer Offer": ("Sales and Service", "Sales")}
        self.assertEqual(business.term_path("FW-BIAN", "Customer Offer", {}, places),
                         "Sales and Service > Sales > Customer Offer")
        # A service domain the tally never saw takes the capability's own
        # place, when the capability names exactly one.
        record = {"bian_business_area": "Operations and Execution", "bian_business_domain": "Payments"}
        self.assertEqual(business.term_path("FW-BIAN", "Payment Order", record, {}),
                         "Operations and Execution > Payments > Payment Order")
        # Two places and no tally: no guess.
        record = {"bian_business_area": "A; B", "bian_business_domain": "C; D"}
        self.assertEqual(business.term_path("FW-BIAN", "Payment Order", record, {}), "Payment Order")
        self.assertEqual(business.term_path("FW-ITIL", "Incident Management", {}, {}),
                         "Service management > Incident Management")
        self.assertEqual(business.term_path("FW-CRI", "pr.ds-01", {}, {}), "Protect > pr.ds-01")
        self.assertEqual(business.term_path("FW-DMBOK", "Data Quality", {}, {}), "Data Quality")
        # A path already written passes through, so a second import is a no-op.
        self.assertEqual(business.term_path("FW-ITIL", "Service management > Incident Management", {}, {}),
                         "Service management > Incident Management")

    def test_a_level_two_capability_is_placed_where_its_parent_says(self) -> None:
        capabilities = [
            {"capability_id": "CAP-A", "parent_capability_id": "",
             "bian_business_area": "Sales and Service", "bian_business_domain": "Sales"},
            {"capability_id": "CAP-A-01", "parent_capability_id": "CAP-A"},
        ]
        rows = business.place_references(
            [{"capability_id": "CAP-A-01", "framework_id": "FW-BIAN", "ref": "Product Matching"}], capabilities)
        self.assertEqual(rows[0]["ref"], "Sales and Service > Sales > Product Matching")

    def test_the_most_common_place_wins_for_a_service_domain(self) -> None:
        rows = [
            {"bian_business_area": "Risk and Compliance", "bian_business_domain": "Models",
             "bian_service_domains": "Underwriting"},
            {"bian_business_area": "Sales and Service", "bian_business_domain": "Sales",
             "bian_service_domains": "Underwriting"},
            {"bian_business_area": "Risk and Compliance", "bian_business_domain": "Models",
             "bian_service_domains": "Underwriting; Credit Risk Models"},
        ]
        places = business.bian_places(rows)
        self.assertEqual(places["Underwriting"], ("Risk and Compliance", "Models"))


class TestTheLandscape(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}
        cls.view = cls.views["framework-landscape"]

    def _bound(self, framework_id):
        return resolve(self.model, bind(self.view, {"framework": framework_id}, self.model))

    def test_it_is_drawn_once_for_every_framework_something_is_placed_in(self) -> None:
        placed = {str(r["framework_id"]) for r in self.model.relation_rows(REFERENCES)}
        self.assertEqual({value for _p, value in render_targets(self.model, self.view)}, placed)
        # Frameworks that are only followed, never placed in, have no landscape.
        frameworks = {f["framework_id"] for f in self.model.all_of("frameworks")}
        self.assertTrue(frameworks - placed)

    def test_exactly_the_placed_capabilities_are_on_it(self) -> None:
        for framework_id in sorted({str(r["framework_id"]) for r in self.model.relation_rows(REFERENCES)}):
            with self.subTest(framework=framework_id):
                graph = self._bound(framework_id)
                self.assertEqual(graph.view.kind, "map")
                self.assertFalse(graph.edges)
                self.assertTrue(all(n.entity_type == "capabilities" for n in graph.nodes))
                self.assertEqual({n.key for n in graph.nodes}, set(_placements(self.model, framework_id)))

    def test_a_capability_nests_by_its_first_placement(self) -> None:
        for framework_id in ("FW-BIAN", "FW-ITIL", "FW-CRI", "FW-APQC"):
            with self.subTest(framework=framework_id):
                refs = _placements(self.model, framework_id)
                for node in self._bound(framework_id).nodes:
                    parts = [p.strip() for p in sorted(refs[node.key])[0].split(PATH_SEPARATOR)]
                    self.assertEqual(node.groups, tuple(parts[:2]), node.key)
        # Some capability sits in two places in BIAN, and is drawn once.
        twice = [c for c, r in _placements(self.model, "FW-BIAN").items() if len(r) > 1]
        self.assertTrue(twice)
        keys = [n.key for n in self._bound("FW-BIAN").nodes]
        self.assertEqual(len(keys), len(set(keys)))

    def test_bian_opens_on_its_areas_and_itil_on_its_groups(self) -> None:
        areas = {n.groups[0] for n in self._bound("FW-BIAN").nodes}
        self.assertEqual(areas, {"Business Support", "Operations and Execution", "Reference Data",
                                 "Risk and Compliance", "Sales and Service"})
        groups = {n.groups[0] for n in self._bound("FW-ITIL").nodes}
        self.assertEqual(groups, set(business.ITIL_GROUPS))
        # A framework of one level nests one deep, not under an empty box.
        self.assertTrue(all(len(n.groups) == 1 for n in self._bound("FW-APQC").nodes))

    def test_binding_fills_the_keys_and_the_grouping(self) -> None:
        bound = bind(self.view, {"framework": "FW-ITIL"}, self.model)
        self.assertEqual(list(bound.group_by), [REFERENCES + "@FW-ITIL#1", REFERENCES + "@FW-ITIL#2"])
        where = bound.scope["include"][0]["where"]
        self.assertEqual(list(where), [REFERENCES + "@FW-ITIL"])
        self.assertNotIn("{framework}", repr(bound))

    def test_a_path_level_is_a_number_from_one(self) -> None:
        for key in (REFERENCES + "@FW-ITIL#0", REFERENCES + "@FW-ITIL#two"):
            with self.subTest(key=key):
                with self.assertRaises(ViewError):
                    resolve(self.model, _probe([key]))
        # Past the end of the path is nothing, which the grouping drops.
        graph = resolve(self.model, _probe([REFERENCES + "@FW-DMBOK#3"],
                                           {REFERENCES + "@FW-DMBOK": {"exists": True}}))
        self.assertTrue(graph.nodes)
        self.assertTrue(all(n.groups == () for n in graph.nodes))

    def test_the_filter_reads_the_relation_too(self) -> None:
        graph = resolve(self.model, _probe([REFERENCES + "@FW-DMBOK"],
                                           {REFERENCES + "@FW-DMBOK": ["Data Governance"]}))
        self.assertEqual({n.groups for n in graph.nodes}, {("Data Governance",)})
        graph = resolve(self.model, _probe([], {"capability_level": ["L1"],
                                                REFERENCES + "@FW-DMBOK": {"exists": False}}))
        self.assertTrue(graph.nodes)
        self.assertFalse(set(_placements(self.model, "FW-DMBOK")) & {n.key for n in graph.nodes})

    def test_a_key_that_names_no_relation_is_refused(self) -> None:
        for key in ("no_such_relation@FW-ITIL", "system_realizes_capability@SYS-X"):
            with self.subTest(key=key):
                with self.assertRaises(ViewError):
                    resolve(self.model, _probe([key]))


def _payload(model, view):
    root = seeded_root()
    web = web_dir(root)
    icons = IconMap(web if web else REPO / "80_APP" / "web")
    return graph_payload(model, view, Palette(model.config.get("palette")), icons, load_components(root))


class TestTheWholeMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}

    def test_every_working_capability_is_on_one_page(self) -> None:
        graph = resolve(self.model, self.views["capability-map"])
        level_one = {c["capability_id"] for c in self.model.all_of("capabilities") if c.get("capability_level") == "L1"}
        self.assertEqual({n.key for n in graph.nodes}, level_one)
        self.assertTrue(all(len(n.groups) == 2 for n in graph.nodes))

    def test_each_tile_carries_the_frameworks_it_is_placed_in(self) -> None:
        payload = _payload(self.model, self.views["capability-map"])
        nodes = {e["data"]["id"]: e["data"] for e in payload["elements"] if not e["data"].get("isGroup")
                 and "source" not in e["data"]}
        placed = {}
        for row in self.model.relation_rows(REFERENCES):
            if row["capability_id"] in nodes:
                placed.setdefault(row["capability_id"], set()).add(row["framework_id"])
        self.assertTrue(placed)
        for key, data in nodes.items():
            self.assertEqual(set(data.get("marks") or ()), placed.get(key, set()), key)
        keys = payload["marks"]["keys"]
        self.assertEqual(payload["marks"]["relation"], REFERENCES)
        self.assertEqual([k["count"] for k in keys], sorted((k["count"] for k in keys), reverse=True))
        self.assertEqual({k["key"] for k in keys}, set().union(*placed.values()))
        self.assertTrue(all(k["label"] != k["key"] for k in keys))

    def test_a_view_without_marks_carries_none(self) -> None:
        payload = _payload(self.model, self.views["value-streams"])
        self.assertIsNone(payload["marks"])
        self.assertIsNone(payload["matrix"])


class TestTheGrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.views = {v.view_id: v for v in seeded_views()}
        cls.graph = resolve(cls.model, cls.views["frameworks"])
        cls.grid = matrix_of(cls.graph)

    def test_the_rows_are_the_domains_by_tier_and_the_columns_every_framework(self) -> None:
        domains = {c["capability_id"] for c in self.model.all_of("capabilities") if c.get("capability_level") == "L0"}
        rows = [r.key for g in self.grid.groups for r in g.rows]
        self.assertEqual(sorted(rows), sorted(domains))
        # The tiers in the order the whole map bands them, not alphabetically.
        self.assertEqual([g.name for g in self.grid.groups], ["Direct", "Core", "Enable"])
        frameworks = {f["framework_id"] for f in self.model.all_of("frameworks")}
        self.assertEqual({c.key for c in self.grid.columns}, frameworks)
        totals = [c.total for c in self.grid.columns]
        self.assertEqual(totals, sorted(totals, reverse=True))

    def test_a_mark_is_the_domains_own_alignment(self) -> None:
        aligned = {(r["capability_id"], r["framework_id"]): r["alignment"]
                   for r in self.model.relation_rows("capability_aligns_to_framework")}
        rows = {r.key for g in self.grid.groups for r in g.rows}
        marks = {key: cell.mark for key, cell in self.grid.cells.items() if cell.mark}
        self.assertTrue(marks)
        # Following a framework is said at the domain, so every row says one
        # and nothing below the domains does.
        self.assertTrue(all(c in rows for c, _f in aligned))
        self.assertEqual(marks, aligned)

    def test_a_count_is_the_capabilities_placed_under_the_domain(self) -> None:
        caps = {c["capability_id"]: c for c in self.model.all_of("capabilities")}

        def domain_of(key):
            seen = set()
            while key and key not in seen:
                seen.add(key)
                if caps.get(key, {}).get("capability_level") == "L0":
                    return key
                key = str(caps.get(key, {}).get("parent_capability_id") or "")
            return None

        expected = {}
        for row in self.model.relation_rows(REFERENCES):
            domain = domain_of(str(row["capability_id"]))
            if domain:
                expected.setdefault((domain, row["framework_id"]), set()).add(row["capability_id"])
        counts = {key: cell.count for key, cell in self.grid.cells.items() if cell.count}
        self.assertEqual(counts, {key: len(v) for key, v in expected.items()})

    def test_the_report_carries_the_grid_and_its_key(self) -> None:
        payload = _payload(self.model, self.views["frameworks"])
        grid = payload["matrix"]
        self.assertEqual(grid["mark"], "capability_aligns_to_framework")
        self.assertEqual(grid["count"], REFERENCES)
        self.assertEqual(set(grid["marks"]), {"Governed by", "Aligned to", "Informed by"})
        self.assertEqual(len(grid["cells"]), len(self.grid.cells))

    def test_the_markdown_and_the_drawing_are_the_same_grid(self) -> None:
        rows = [r for g in self.grid.groups for r in g.rows]
        markdown = render_table(self.graph)
        head = "| | " + " | ".join(c.label for c in self.grid.columns) + " | Placed |"
        self.assertIn(head, markdown)
        for row in rows:
            self.assertEqual(sum(1 for line in markdown.splitlines() if line.startswith("| %s |" % row.label)), 1)
        svg = ET.fromstring(render_table_svg(self.graph))
        drawn = [g.get("data-row") for g in svg.iter("{http://www.w3.org/2000/svg}g") if g.get("data-row")]
        self.assertEqual(drawn, [r.key for r in rows])
        # The key names what the grid holds, strongest first.
        said = [t.text for t in svg.iter("{http://www.w3.org/2000/svg}text")]
        at = [said.index(mark) for mark in ("Governed by", "Aligned to", "Informed by")]
        self.assertEqual(at, sorted(at))


if __name__ == "__main__":
    unittest.main()
