"""Tests for the levels: the views a record can be the subject of, and the
way between landscape, domain, system and where it runs.

What is checked: a view's subject may be a value of a field rather than a
record, and such a view is drawn once per value the selected records take,
refuses a value no record carries, and names each subject's file by a slug;
a record lists the views about it, about what contains it (a product that
includes it, a parent, a source of truth) and about the domain it carries,
each bound and counted, and a domain word no system carries offers nothing;
a view about one thing goes up through its `up` chain, bound to what the
subject sits in, skipping a level the subject has no value for; the views
about the same subject are listed for the tabs; every shipped view about one
thing has a level above it that is shipped; an `up` naming no view is an
error in an estate's own view; and the server carries all of it in the
record, the drawing and the boundaries, and finds a domain's committed
drawing by its slug.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import levels, model as model_module  # noqa: E402
from terrane.query import (  # noqa: E402
    ViewError, bind, field_values, load_views, parse_view, render_targets, resolve, subject_slug,
)
from terrane.schema import ENTITY_TYPES  # noqa: E402

from _fixture import REPO, Sandbox  # noqa: E402


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


class TestAFieldAsASubject(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox(seed=True)
        cls.root = cls.box.__enter__()
        cls.model = model_module.load(cls.root)
        cls.views = {v.view_id: v for v in load_views(cls.root / "30_VIEWS")}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def test_a_parameter_takes_a_record_or_a_field_not_both(self) -> None:
        view = parse_view({"view_id": "v", "parameters": [{"name": "domain", "field": "company_domain"}],
                           "scope": {"include": [{"type": "systems"}]}})
        self.assertEqual(view.parameters[0].field, "company_domain")
        self.assertIsNone(view.parameters[0].type)
        with self.assertRaises(ViewError):
            parse_view({"view_id": "v", "parameters": [{"name": "d", "type": "systems", "field": "company_domain"}],
                        "scope": {"include": [{"type": "systems"}]}})
        with self.assertRaises(ViewError):
            parse_view({"view_id": "v", "parameters": [{"name": "d", "field": "no_such_field"}],
                        "scope": {"include": [{"type": "systems"}]}})

    def test_the_domain_landscape_is_drawn_once_per_domain_the_systems_name(self) -> None:
        view = self.views["domain-landscape"]
        expected = sorted({str(r["company_domain"]) for r in self.model.all_of("systems")
                           if r.get("company_domain") and r.get("status") in ("Active", "Planned")})
        self.assertGreater(len(expected), 3)
        self.assertEqual([v for _p, v in render_targets(self.model, view)], expected)
        for domain in expected:
            graph = resolve(self.model, bind(view, {"domain": domain}, self.model))
            inside = [n for n in graph.nodes if n.entity_type == "systems" and n.record.get("company_domain") == domain]
            self.assertTrue(inside, domain)

    def test_a_domain_no_record_carries_is_refused(self) -> None:
        with self.assertRaises(ViewError) as caught:
            bind(self.views["domain-landscape"], {"domain": "Nowhere"}, self.model)
        self.assertIn("Nowhere", str(caught.exception))

    def test_a_subjects_file_is_named_by_its_slug(self) -> None:
        self.assertEqual(subject_slug("SYS-AUTH-SWITCH"), "sys-auth-switch")
        self.assertEqual(subject_slug("Risk and Compliance"), "risk-and-compliance")
        # Every subject the shipped views are drawn for by id keeps the name
        # its committed file had, lowered.
        for view in self.views.values():
            param = levels.subject_parameter(view)
            if param is None or not param.type:
                continue
            for _p, value in render_targets(self.model, view):
                self.assertEqual(subject_slug(value), value.lower(), (view.view_id, value))


class TestLevels(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox(seed=True)
        cls.root = cls.box.__enter__()
        cls.model = model_module.load(cls.root)
        cls.views = load_views(cls.root / "30_VIEWS")
        cls.by_id = {v.view_id: v for v in cls.views}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def _system_in_a_product_and_a_domain(self):
        included = {row["system_id"]: row["product_id"] for row in self.model.relation_rows("product_includes_system")}
        for record in self.model.all_of("systems"):
            if record["system_id"] in included and record.get("company_domain") \
                    and record.get("status") in ("Active", "Planned"):
                return record, included[record["system_id"]]
        self.fail("no system in a product and a domain in the seed")

    def test_a_system_lists_its_views_its_products_and_its_domains(self) -> None:
        record, product = self._system_in_a_product_and_a_domain()
        groups = levels.diagrams_of(self.model, self.views, record["system_id"])
        self.assertEqual([g["kind"] for g in groups], ["about", "contains", "field"])
        about, contains, field = groups
        self.assertEqual([i["viewId"] for i in about["items"]],
                         [v.view_id for v in self.views if levels.subject_parameter(v)
                          and levels.subject_parameter(v).type == "systems"])
        for item in about["items"]:
            bound = bind(self.by_id[item["viewId"]], {item["parameter"]: record["system_id"]}, self.model)
            self.assertEqual(item["nodes"], len(resolve(self.model, bound).nodes), item["viewId"])
            self.assertEqual(item["title"], bound.title)
        self.assertEqual((contains["head"], contains["subject"]), ("Its product", product))
        self.assertIn("onboarding", [i["viewId"] for i in contains["items"]])
        self.assertEqual((field["head"], field["name"]), ("Its business domain", record["company_domain"]))
        self.assertEqual([i["viewId"] for i in field["items"]], ["domain-landscape"])

    def test_a_domain_word_no_system_carries_offers_no_landscape(self) -> None:
        systems_domains = set(field_values(self.model, "company_domain", "systems"))
        capability = next((c for c in self.model.all_of("capabilities")
                           if c.get("company_domain") and c["company_domain"] not in systems_domains), None)
        self.assertIsNotNone(capability, "a capability whose domain is a word no system carries")
        groups = levels.diagrams_of(self.model, self.views, capability["capability_id"])
        self.assertNotIn("field", [g["kind"] for g in groups])

    def test_a_parent_is_what_a_capability_sits_in(self) -> None:
        child = next(c for c in self.model.all_of("capabilities") if c.get("parent_capability_id"))
        groups = levels.diagrams_of(self.model, self.views, child["capability_id"])
        parent = [g for g in groups if g["kind"] == "contains"]
        self.assertEqual(parent[0]["head"], "Its parent capability")
        self.assertEqual(parent[0]["subject"], child["parent_capability_id"])

    def test_a_system_goes_up_to_its_domain_then_the_landscape(self) -> None:
        record, _product = self._system_in_a_product_and_a_domain()
        up = levels.way_up(self.model, self.views, self.by_id["system-architecture"], {"system": record["system_id"]})
        self.assertEqual([(lv["viewId"], lv["value"]) for lv in up],
                         [("application-landscape", ""), ("domain-landscape", record["company_domain"])])
        self.assertEqual(up[1]["label"], record["company_domain"])
        self.assertGreater(up[0]["nodes"], up[1]["nodes"])

    def test_a_system_no_domain_names_skips_that_level(self) -> None:
        loose = next(r for r in self.model.all_of("systems") if not r.get("company_domain"))
        up = levels.way_up(self.model, self.views, self.by_id["system-architecture"], {"system": loose["system_id"]})
        self.assertEqual([lv["viewId"] for lv in up], ["application-landscape"])

    def test_the_domain_goes_up_to_the_landscape(self) -> None:
        up = levels.way_up(self.model, self.views, self.by_id["domain-landscape"], {"domain": "Servicing"})
        self.assertEqual([lv["viewId"] for lv in up], ["application-landscape"])

    def test_the_views_about_a_system_are_its_tabs(self) -> None:
        tabs = levels.across(self.views, self.by_id["hub-and-spoke"])
        self.assertEqual([t["viewId"] for t in tabs if t["current"]], ["hub-and-spoke"])
        self.assertIn("system-architecture", [t["viewId"] for t in tabs])
        self.assertTrue(all(t["parameter"] == "system" for t in tabs))
        self.assertEqual(levels.across(self.views, self.by_id["domain-landscape"]), [])

    def test_a_boundary_that_is_a_domain_opens_its_landscape(self) -> None:
        found = levels.boundary_diagrams(self.model, self.views, "company_domain", "Servicing")
        self.assertEqual([(i["viewId"], i["value"]) for i in found], [("domain-landscape", "Servicing")])
        self.assertEqual(levels.boundary_diagrams(self.model, self.views, "cloud_account", "prod-lending"), [])


class TestTheShippedLevels(unittest.TestCase):
    def test_every_view_about_one_thing_has_a_shipped_level_above_it(self) -> None:
        views = load_views(REPO / "30_VIEWS")
        ids = {v.view_id for v in views}
        for view in views:
            if levels.subject_parameter(view) is None:
                continue
            with self.subTest(view=view.view_id):
                self.assertTrue(view.up, "a view about one thing names the level above it")
                self.assertIn(view.up, ids)

    def test_the_second_estate_draws_its_own_domains(self) -> None:
        root = REPO / "90_EXAMPLE" / "thurman-health"
        model = model_module.load(root)
        view = [v for v in load_views(root / "30_VIEWS") if v.view_id == "domain-landscape"][0]
        domains = [v for _p, v in render_targets(model, view)]
        self.assertIn("Oncology", domains)
        self.assertNotIn("Servicing", domains)

    def test_an_up_naming_no_view_is_an_error_in_an_estates_own_view(self) -> None:
        from terrane import validate

        with Sandbox(seed=True) as root:
            path = root / "30_VIEWS" / "system-architecture.view.yaml"
            text = path.read_text(encoding="utf-8").replace("up: domain-landscape", "up: no-such-view")
            path.write_text(text, encoding="utf-8")
            report = validate.run(model_module.load(root), load_views(root / "30_VIEWS"))
            found = [f for f in report.errors if f.code == "view.up"]
            self.assertEqual(len(found), 1, [f.format() for f in report.errors])
            self.assertIn("no-such-view", found[0].message)


class TestTheServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.box = Sandbox(seed=True)
        cls.root = cls.box.__enter__()
        cls.server = _server(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.__exit__(None, None, None)

    def test_a_record_carries_its_diagrams(self) -> None:
        got = self.server.api_entity({"id": ["SYS-CARDSVC-WEB"]}, None)
        kinds = [g["kind"] for g in got["diagrams"]]
        self.assertEqual(kinds[0], "about")
        self.assertIn("field", kinds)

    def test_a_drawing_carries_its_levels_its_tabs_and_its_choices(self) -> None:
        got = self.server.api_graph({"view": ["system-architecture"], "p_system": ["SYS-CARDSVC-WEB"]}, None)
        self.assertEqual([lv["viewId"] for lv in got["up"]], ["application-landscape", "domain-landscape"])
        self.assertTrue(any(t["current"] and t["viewId"] == "system-architecture" for t in got["across"]))
        domain = self.server.api_graph({"view": ["domain-landscape"], "p_domain": ["Servicing"]}, None)
        self.assertEqual(domain["parameters"][0]["field"], "company_domain")
        self.assertIn("Servicing", domain["parameters"][0]["choices"])
        self.assertIsNone(got["parameters"][0]["choices"])

    def test_a_domain_boundary_on_the_landscape_carries_its_landscape(self) -> None:
        got = self.server.api_graph({"view": ["application-landscape"]}, None)
        servicing = [e["data"] for e in got["elements"] if e["data"].get("isGroup") and e["data"].get("stored") == "Servicing"]
        self.assertEqual([d["viewId"] for d in servicing[0]["diagrams"]], ["domain-landscape"])

    def test_a_domains_committed_drawing_is_found_by_its_slug(self) -> None:
        model, views = self.server._load_all()
        domain = next(v for _p, v in render_targets(model, [v for v in views if v.view_id == "domain-landscape"][0])
                      if " " in v)
        view, supplied = self.server._find_view(views, "domain-landscape--" + subject_slug(domain))
        self.assertEqual((view.view_id, supplied), ("domain-landscape", {"domain": domain}))

    def test_the_overview_says_what_each_view_is_about(self) -> None:
        got = self.server.api_overview({}, None)
        about = {v["viewId"]: v.get("subject") for v in got["views"]}
        self.assertEqual(about["system-architecture"]["type"], "systems")
        self.assertEqual(about["domain-landscape"]["field"], "company_domain")
        self.assertIsNone(about["application-landscape"])
        self.assertEqual({v["viewId"]: v.get("up") for v in got["views"]}["domain-landscape"], "application-landscape")


if __name__ == "__main__":
    unittest.main()
