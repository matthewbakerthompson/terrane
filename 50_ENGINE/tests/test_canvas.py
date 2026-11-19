"""Tests for the canvas's endpoints: New diagram, drawn by placing things.

What is checked: the picker is offered the library's parts for the boxes a
diagram draws, the views that box what they draw, Network Topology's
accounts and zones and the systems; a part is found by what each cloud
calls it, and one dropped into an account of a cloud is that cloud's
product, the person's choice of its products kept; a part placed is a record with the
part's defaults and the fields of every boundary it was dropped into, its
id made from the name it was given, a name already taken numbered rather
than reused, and what the kind of record needs and the drop did not say
listed rather than guessed; a diagram is written the first time something
is on it, with an id from its title that no view has, and rewritten by
value after, a line someone added by hand kept; one placing a view that is
not here is refused with nothing written; a drawing of placed views draws
through the preview the canvas uses; and the overview says which diagrams
open on the canvas.

A kit (V17): the picker offers every kit beside the parts, each with the
systems it makes and what it asks; dropped into an account it lands there,
offered the owner every system there names and the domain its records
agree on, and says what each system runs on there, the services a zone's
systems share said once; with nowhere to land it waits and says for what;
what the shapes' vocabulary asks goes to the product; and Place is
Assemble's own create, one product that loads, its id numbered when taken.

Add on shelves (V18): the kinds come shelf by shelf, each under its group,
the groups in the library's order; a kind says the kits that make one and
as what; a maker's list of products is three products, not two; and every
kind the library ships has an icon of its own that the icons file draws.

The rest of the estate (V19): the estate's data, actors and teams come with
what a line would join each to, most sensitive data first; a building block
dropped into an account lands there, owned as most of its services are,
its services in the order its lines run, each the cloud's usual product;
placed, they are written with the account's fields and their lines, and the
same name again is refused rather than written twice.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.blocks import offered  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402

from _fixture import REPO, Sandbox  # noqa: E402

INTO = [
    {"field": "cloud_provider", "value": "AWS"},
    {"field": "cloud_account", "value": "prod-lending"},
    {"field": "region", "value": "eu-west-2"},
    {"field": "availability_zone", "value": "eu-west-2a"},
]


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


KIT_INTO = INTO[:3]


class TestAKitOnTheCanvas(unittest.TestCase):
    """A sandbox of its own: the tests above add a system with no owner to
    prod-lending, and what a kit offers is read off what is there."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sandbox = Sandbox(seed=True)
        cls.root = cls.sandbox.__enter__()
        cls.server = _server(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sandbox.__exit__(None, None, None)

    def _assistant(self, **body):
        ask = {"kit": "ai-assistant-baseline", "into": KIT_INTO, "name": "Lending assistant",
               "with": {"sources": ["SYS-LENDING-API", "SYS-CORE-LEDGER"]}}
        ask.update(body)
        return self.server.api_canvas_kit({}, ask)

    def test_the_picker_offers_the_kits_beside_the_parts(self) -> None:
        got = self.server.api_canvas_parts({}, {})
        kits = {k["id"]: k for k in got["kits"]}
        self.assertEqual(got["counts"]["kits"], len(kits))
        self.assertGreaterEqual(len(kits), 11)
        assistant = kits["ai-assistant-baseline"]
        self.assertEqual([s["name"] for s in assistant["systems"]],
                         ["Service", "Chat", "Inference service", "Document ingestion", "Retrieval index",
                          "Conversation history"])
        # A line made for each source is the product's line to it, not a part.
        self.assertEqual([(a["ask"], a["names"], a["list"]) for a in assistant["asks"]],
                         [("Answers from", "systems", True)])
        # A token in a name is said by what it is asked as.
        self.assertIn("Partner adapter", [s["name"] for s in kits["adapter-baseline"]["systems"]])

    def test_a_kit_dropped_in_an_account_lands_there(self) -> None:
        got = self._assistant()
        self.assertEqual((got["id"], got["lands"], got["dropped"], got["missing"]),
                         ("PRD-LENDING-ASSISTANT", "AWS|prod-lending|eu-west-2", True, []))
        self.assertEqual((got["owner"], got["ownerWhy"], got["domain"]),
                         ("ORG-PRODUCT", "As every system already in prod-lending.", "Lending"))
        app, data = got["makes"]
        self.assertEqual((app["words"], app["placed"], app["shared"]),
                         ("app", True, ["Amazon EKS", "Amazon CloudWatch"]))
        said = {s["part"]: [("its own " if u["own"] else "") + u["name"] for u in s["adds"]]
                for g in got["makes"] for s in g["systems"]}
        self.assertEqual(said["Inference service"], ["Amazon Bedrock", "Amazon Bedrock Guardrails"])
        self.assertEqual(said["Service"], ["its own Amazon ElastiCache"])
        self.assertEqual(said["Chat"], ["Microsoft Entra ID"])
        self.assertEqual((data["words"], [s["part"] for s in data["systems"]]),
                         ("data", ["Retrieval index", "Conversation history"]))
        self.assertIn("Amazon RDS for PostgreSQL", said["Conversation history"])
        # The account is still the one it was dropped in once it is sent back.
        again = self._assistant(lands=got["lands"], name="Lending helper")
        self.assertTrue(again["dropped"])
        made = got["assembly"]
        self.assertEqual(made["compose"], {"provider": "AWS", "modules": [
            {"module": "ai-assistant-baseline", "with": {"sources": ["SYS-LENDING-API", "SYS-CORE-LEDGER"]}}]})
        self.assertEqual({k: made["parameters"][k] for k in ("slug", "account", "region", "owner_org", "domain")},
                         {"slug": "lending-assistant", "account": "prod-lending", "region": "eu-west-2",
                          "owner_org": "ORG-PRODUCT", "domain": "Lending"})
        self.assertEqual(made["buildType"], "ai-assistant")

    def test_a_kit_with_nowhere_to_land_waits_and_says_for_what(self) -> None:
        got = self._assistant(into=[])
        self.assertEqual((got["lands"], got["missing"], got["assembly"], got["makes"]),
                         ("", ["where it lands", "who owns it"], None, []))
        # Where a product can land is where its systems land: an account's
        # subnets, region by region; not a "global" its records say.
        subnets = {(r["cloud_account"], r["region"]) for r in self.server._load_all()[0].all_of("tech_services")
                   if r.get("component_type") == "subnet"}
        self.assertTrue(got["landsOptions"])
        self.assertTrue(all((o["account"], o["region"]) in subnets for o in got["landsOptions"]))

    def test_what_the_shapes_ask_goes_to_the_product(self) -> None:
        got = self.server.api_canvas_kit({}, {"kit": "vendor-baseline", "into": KIT_INTO, "name": "Bureau feed",
                                              "with": {"vendor": "Experian", "caller_system": "SYS-LENDING-API"}})
        self.assertEqual(got["missing"], [])
        made = got["assembly"]
        self.assertEqual(made["compose"]["modules"], [{"module": "vendor-baseline"}])
        self.assertEqual({k: made["parameters"].get(k) for k in ("vendor", "vendor_region", "caller_system")},
                         {"vendor": "Experian", "vendor_region": "eu-west-1", "caller_system": "SYS-LENDING-API"})
        waiting = self.server.api_canvas_kit({}, {"kit": "vendor-baseline", "into": KIT_INTO, "name": "Bureau feed"})
        self.assertEqual(waiting["missing"], ["Vendor", "Called in line by"])
        with self.assertRaises(self.server.ApiError):
            self._assistant(**{"with": {"sources": ["SYS-NO-SUCH"]}})
        with self.assertRaises(self.server.ApiError):
            self._assistant(owner="ORG-NO-SUCH")
        with self.assertRaises(self.server.ApiError):
            self.server.api_canvas_kit({}, {"kit": "api-service"})

    def _block(self, **body):
        ask = {"block": "public-web-tier", "into": KIT_INTO, "name": "Lending portal"}
        ask.update(body)
        return self.server.api_canvas_block({}, ask)

    def test_a_block_dropped_lands_where_it_was_dropped(self) -> None:
        got = self._block()
        self.assertEqual((got["lands"], got["dropped"], got["missing"], got["clashes"]),
                         ("AWS|prod-lending|eu-west-2", True, [], []))
        # Owned as most of the account's services are, and said how many.
        self.assertEqual(got["owner"], "ORG-TECH")
        self.assertRegex(got["ownerWhy"], r"^As \d+ of the \d+ services already in prod-lending are\.$")
        # In the order its lines run: what a request meets first, first.
        self.assertEqual([(m["kind"], m["product"]) for m in got["makes"]], [
            ("DNS", "Amazon Route 53"), ("Content delivery network", "Amazon CloudFront"),
            ("Web application firewall", "AWS WAF"), ("Load balancer", "Application Load Balancer")])
        self.assertEqual([m["name"] for m in got["makes"]][0], "Lending portal DNS")
        self.assertTrue(got["chain"])
        self.assertEqual(len(got["lines"]), 3)
        # A provider's answer of a choice is its first product, not the
        # whole answer.
        tier = self._block(block="event-tier")
        self.assertIn(("Event stream", "Amazon Kinesis"), [(m["kind"], m["product"]) for m in tier["makes"]])
        # Clicked rather than dropped, it waits for an account and an owner,
        # and says what it would make without a cloud's products.
        loose = self._block(into=[])
        self.assertEqual((loose["lands"], loose["missing"]), ("", ["where it lands", "who owns it"]))
        self.assertEqual([m["product"] for m in loose["makes"]], ["", "", "", ""])
        with self.assertRaises(self.server.ApiError):
            self._block(block="no-such-block")

    def test_a_block_placed_is_written_with_its_account_and_lines(self) -> None:
        got = self._block(name="Onboarding edge", place=True)
        self.assertEqual(got["placed"], ["TS-ONBOARDING-EDGE-DNS", "TS-ONBOARDING-EDGE-CDN", "TS-ONBOARDING-EDGE-WAF",
                                         "TS-ONBOARDING-EDGE-LOAD-BALANCER"])
        cdn = read_data_file(self.root / [p for p in got["paths"] if p.endswith("TS-ONBOARDING-EDGE-CDN.yaml")][0])
        self.assertEqual({k: cdn.get(k) for k in ("cloud_provider", "cloud_account", "region", "owner_org_id", "product")},
                         {"cloud_provider": "AWS", "cloud_account": "prod-lending", "region": "eu-west-2",
                          "owner_org_id": "ORG-TECH", "product": "Amazon CloudFront"})
        model = self.server._load_all()[0]
        joined = {(r["from_tech_service_id"], r["to_tech_service_id"]) for r in model.relation_rows("tech_service_connects_to")}
        self.assertTrue({("TS-ONBOARDING-EDGE-DNS", "TS-ONBOARDING-EDGE-CDN"),
                         ("TS-ONBOARDING-EDGE-WAF", "TS-ONBOARDING-EDGE-LOAD-BALANCER")} <= joined)
        # The same name again is in the estate already: said, and not written.
        again = self._block(name="Onboarding edge")
        self.assertEqual(len(again["clashes"]), 4)
        with self.assertRaises(self.server.ApiError):
            self._block(name="Onboarding edge", place=True)

    def test_place_is_assembles_own_create(self) -> None:
        got = self._assistant(name="Lending desk assistant")
        out = self.server.api_assemble_create({}, got["assembly"])
        self.assertEqual((out["created"], out["errors"]), ("PRD-LENDING-DESK-ASSISTANT", []))
        record = read_data_file(self.root / out["path"])
        self.assertEqual((record["owner_org_id"], record["company_domain"], record["compose"]["provider"]),
                         ("ORG-PRODUCT", "Lending", "AWS"))
        systems = [s["id"] for g in got["makes"] for s in g["systems"]]
        self.assertEqual(len(systems), 6)
        self.assertTrue(set(systems) <= set(out["generated"]))
        # The same name again is numbered, and says what it stands in for.
        again = self._assistant(name="Lending desk assistant")
        self.assertEqual((again["id"], again["taken"]), ("PRD-LENDING-DESK-ASSISTANT-2", "PRD-LENDING-DESK-ASSISTANT"))
        self.assertEqual(again["assembly"]["parameters"]["slug"], "lending-desk-assistant-2")


class TestCanvas(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sandbox = Sandbox(seed=True)
        cls.root = cls.sandbox.__enter__()
        cls.server = _server(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sandbox.__exit__(None, None, None)

    def test_the_picker_offers_parts_views_accounts_zones_and_systems(self) -> None:
        got = self.server.api_canvas_parts({}, {})
        self.assertEqual({p["type"] for p in got["parts"]}, {"systems", "tech_services"})
        self.assertEqual(got["parts"][0]["type"], "systems")
        self.assertEqual(got["network"], "network-topology")
        network = [v for v in got["views"] if v["id"] == "network-topology"][0]
        self.assertEqual(network["fold"]["field"], "cloud_account")
        labels = [v["label"] for v in network["fold"]["values"]]
        self.assertIn("AWS · prod-lending", labels)
        # The on-prem parts have no account, and are left out by their cloud.
        self.assertEqual(labels[-1], "On-prem")
        self.assertIn("prod-lending", [a["value"] for a in got["accounts"]])
        self.assertIn("Private-App", [z["value"] for z in got["zones"]])
        self.assertEqual(got["counts"]["systems"], len(got["systems"]))
        # A view that tables what it shows, or is about one subject, is not
        # a boundary to place.
        self.assertTrue(all(not v["id"].startswith("product-") or v["nodes"] for v in got["views"]))

    def test_a_part_is_found_by_what_each_cloud_calls_it(self) -> None:
        parts = {p["id"]: p for p in self.server.api_canvas_parts({}, {})["parts"]}
        self.assertEqual({c: parts["vm"]["products"][c] for c in ("AWS", "Azure", "GCP")},
                         {"AWS": ["Amazon EC2"], "Azure": ["Azure Virtual Machines"], "GCP": ["Compute Engine"]})
        # A choice is split at "or"; a pair joined by "and" is one answer;
        # an aside is no part of a name, though the whole answer is sent too.
        self.assertEqual(parts["container-platform"]["products"]["AWS"], ["Amazon EKS", "ECS"])
        self.assertEqual(offered("AWS Cost Explorer and Budgets"), ["AWS Cost Explorer and Budgets"])
        self.assertEqual(offered("Gemini Enterprise (formerly Agentspace)"), ["Gemini Enterprise"])
        self.assertEqual(offered("MinIO or a NAS"), ["MinIO", "NAS"])
        self.assertIn("formerly", " ".join(parts["ai-assistant"]["providers"].values()))
        # A list of choices is split at its commas too: split at "or" alone,
        # "ADP, Workday Payroll" was one product. A comma in an answer of no
        # choice, or inside brackets, is the answer's own.
        self.assertEqual(parts["payroll"]["products"]["SaaS"], ["ADP", "Workday Payroll", "UKG Pro"])
        self.assertEqual(offered("Amazon EC2 P and G instances, AWS Trainium and Inferentia"),
                         ["Amazon EC2 P and G instances, AWS Trainium and Inferentia"])
        self.assertEqual(offered("Gemini (Pro, Flash), Gemma, Imagen or Veo"), ["Gemini (Pro, Flash), Gemma, Imagen", "Veo"])

    def test_the_kinds_come_shelf_by_shelf_under_their_headings(self) -> None:
        """Add (V18) lists what the server sends in the order it sends it."""
        parts = self.server.api_canvas_parts({}, {})["parts"]
        shelves, headings = [], {}
        for p in parts:
            if p["shelf"] not in shelves:
                shelves.append(p["shelf"])
            said = headings.setdefault(p["shelf"], [])
            if p["group"] not in said:
                said.append(p["group"])
            # A heading comes once: a shelf's kinds under one are together.
            self.assertEqual(said[-1], p["group"], p["id"])
        self.assertEqual(shelves, ["parts", "business", "cloud"])
        self.assertEqual(headings["parts"], ["Front ends", "Services and workers", "AI", "Platforms"])
        # The assistant, written with the AI kinds whose file is read first,
        # does not put Work and collaboration ahead of Finance.
        self.assertEqual(headings["business"], ["Finance", "People", "Customers and sales", "Customer service",
                                                "Operations and supply chain", "Risk and legal",
                                                "Work and collaboration", "Industry"])
        by = {p["id"]: p for p in parts}
        self.assertEqual((by["ai-assistant"]["shelf"], by["ai-assistant"]["group"]), ("business", "Work and collaboration"))
        # A kind of no group is listed under its category.
        self.assertEqual((by["relational-db"]["shelf"], by["relational-db"]["group"]), ("cloud", "Data"))
        self.assertTrue(all(p["shelf"] == ("cloud" if p["type"] == "tech_services" else
                                           "parts" if p["category"] == "Application" else "business") for p in parts))
        self.assertIn("RDBMS", by["relational-db"]["aliases"])

    def test_a_kind_says_the_kits_that_make_one(self) -> None:
        by = {p["id"]: p for p in self.server.api_canvas_parts({}, {})["parts"]}
        self.assertEqual(by["background-worker"]["kits"],
                         [{"id": "event-service-baseline", "name": "Event-driven service", "as": "Async worker"}])
        # One kit making two of a kind says both.
        self.assertEqual([k["as"] for k in by["event-processor"]["kits"]], ["Event consumer", "Event publisher"])
        self.assertEqual(by["payroll"]["kits"], [])

    def test_the_estates_data_actors_and_teams_say_what_they_join(self) -> None:
        """Add (V19) lists them in the order sent, each with what a line on the
        diagram would join it to."""
        got = self.server.api_canvas_parts({}, {})
        data = {d["id"]: d for d in got["data"]}
        self.assertEqual((got["counts"]["data"], got["counts"]["actors"], got["counts"]["teams"]),
                         (len(got["data"]), len(got["actors"]), len(got["teams"])))
        # Most sensitive first, as the schema lists them least sensitive first.
        order = ["Restricted", "Confidential", "Internal", "Public"]
        ranks = [order.index(d["classification"]) for d in got["data"] if d["classification"] in order]
        self.assertEqual(ranks, sorted(ranks))
        card = data["DA-CARD-ACCOUNT"]
        self.assertEqual((card["master"], card["writers"], card["readers"]), ("Core Card Ledger", ["Core Card Ledger"], 10))
        # Outside the company first, and what each uses.
        self.assertEqual([a["internal"] for a in got["actors"]], sorted(a["internal"] for a in got["actors"]))
        cardholder = [a for a in got["actors"] if a["id"] == "ACT-CARDHOLDER"][0]
        self.assertTrue(cardholder["uses"])
        # The units at the top first, and what each owns, most first.
        self.assertEqual(got["teams"][0]["parent"], "")
        tech = [t for t in got["teams"] if t["id"] == "ORG-TECH"][0]
        self.assertEqual([n for _kind, n in tech["owns"]], sorted((n for _kind, n in tech["owns"]), reverse=True))
        blocks = {b["id"]: b for b in got["blocks"]}
        self.assertEqual(got["counts"]["blocks"], len(blocks))
        self.assertEqual([s["name"] for s in blocks["public-web-tier"]["services"]],
                         ["DNS", "Content delivery network", "Web application firewall", "Load balancer"])

    def test_every_kind_has_an_icon_of_its_own(self) -> None:
        from terrane.blocks import load_components

        text = (REPO / "80_APP" / "web" / "canvas" / "kind-icons.js").read_text(encoding="utf-8")
        table = json.loads(text[text.index("= {") + 2:text.rindex(";")])
        kinds = {k: c for k, c in load_components(REPO).items() if not c.replaced}
        self.assertEqual(set(table["kinds"]), set(kinds))
        named = list(table["kinds"].values())
        self.assertEqual(len(named), len(set(named)), "two kinds share an icon")
        # A kind an organization adds is drawn with its category's.
        self.assertTrue({c.category for c in kinds.values()} <= set(table["categories"]))
        self.assertTrue(set(named) | set(table["categories"].values()) <= set(table["icons"]))
        self.assertTrue(all(v.startswith("<") and "script" not in v for v in table["icons"].values()))

    def test_a_part_dropped_into_an_account_is_that_clouds_product(self) -> None:
        made = self.server.api_canvas_record({}, {"part": "vm", "into": INTO})
        self.assertEqual((made["name"], made["product"]), ("Amazon EC2", "Amazon EC2"))
        record = read_data_file(self.root / made["path"])
        self.assertEqual((record.get("product"), record.get("cloud_provider")), ("Amazon EC2", "AWS"))
        # The person's choice of the cloud's products is kept, and a name of
        # their own with it; one that is not this cloud's is the usual one.
        chosen = self.server.api_canvas_record({}, {"part": "container-platform", "into": INTO, "product": "ECS",
                                                    "name": "Lending batch cluster"})
        self.assertEqual((chosen["name"], chosen["product"]), ("Lending batch cluster", "ECS"))
        wrong = self.server.api_canvas_record({}, {"part": "container-platform", "into": INTO, "product": "Cloud Run"})
        self.assertEqual(wrong["product"], "Amazon EKS")
        # In no cloud's account it is the part, and no product is claimed.
        loose = self.server.api_canvas_record({}, {"part": "vm", "into": []})
        self.assertEqual((loose["name"], loose["product"]), ("Virtual machine", ""))
        self.assertIsNone(read_data_file(self.root / loose["path"]).get("product"))

    def test_a_part_is_a_record_named_and_placed_where_it_was_dropped(self) -> None:
        made = self.server.api_canvas_record({}, {"part": "web-app", "into": INTO, "name": "Lending portal"})
        self.assertEqual((made["id"], made["type"], made["name"]), ("SYS-LENDING-PORTAL", "systems", "Lending portal"))
        self.assertEqual(made["missing"], ["owner_org_id", "criticality"])
        record = read_data_file(self.root / made["path"])
        self.assertEqual({k: record.get(k) for k in ("status", "component_type", "network_zone", "cloud_account",
                                                       "region", "availability_zone", "owner_org_id")},
                         {"status": "Planned", "component_type": "web-app", "network_zone": "Private-App",
                          "cloud_account": "prod-lending", "region": "eu-west-2",
                          "availability_zone": "eu-west-2a", "owner_org_id": None})
        again = self.server.api_canvas_record({}, {"part": "web-app", "into": [], "name": "Lending portal"})
        self.assertEqual((again["id"], again["name"]), ("SYS-LENDING-PORTAL-2", "Lending portal 2"))
        with self.assertRaises(self.server.ApiError):
            self.server.api_canvas_record({}, {"part": "no-such-part"})

    def test_a_diagram_is_written_as_it_is_drawn(self) -> None:
        data = {"title": "Lending onboarding", "category": "Application", "kind": "diagram",
                "places": [{"view": "network-topology", "leave_out": {"cloud_account": ["prod-riskops"]}}],
                "scope": {"pin": ["SYS-LENDING-API"]}, "edges": [{"via": "interfaces"}]}
        first = self.server.api_canvas_save({}, {"id": None, "data": dict(data)})
        self.assertEqual((first["id"], first["created"]), ("lending-onboarding", True))
        path = self.root / first["path"]
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("view_id: lending-onboarding\ntitle: Lending onboarding\n"))
        self.assertIn("places:\n  - view: network-topology\n", text)
        # A second new diagram of the same title is given an id of its own.
        other = self.server.api_canvas_save({}, {"id": None, "data": dict(data)})
        self.assertEqual(other["id"], "lending-onboarding-2")
        # A line added by hand survives the next save.
        path.write_text(text.replace("kind: diagram\n", "kind: diagram\n# drawn for the lending review\n"),
                        encoding="utf-8")
        later = dict(data, title="Lending onboarding, AWS")
        self.server.api_canvas_save({}, {"id": "lending-onboarding", "data": later})
        text = path.read_text(encoding="utf-8")
        self.assertIn("# drawn for the lending review", text)
        self.assertIn('title: "Lending onboarding, AWS"', text)
        # Drawn through the preview the canvas uses: the placed view's
        # boundaries, its parts and the pin, the account left out gone.
        payload = self.server.api_view_preview({}, {"id": "lending-onboarding", "data": dict(later, view_id="lending-onboarding")})
        groups = [e["data"]["value"] for e in payload["elements"] if e["data"].get("isGroup")]
        self.assertIn("prod-lending", groups)
        self.assertNotIn("prod-riskops", groups)
        drawn = [e["data"]["id"] for e in payload["elements"] if not e["data"].get("isGroup") and not e["data"].get("source")]
        self.assertIn("SYS-LENDING-API", drawn)
        # The overview says it opens on the canvas, and Network Topology does not.
        listed = {v["viewId"]: v for v in self.server.api_overview({}, {})["views"]}
        self.assertTrue(listed["lending-onboarding"]["canvas"])
        self.assertFalse(listed["network-topology"]["canvas"])

    def test_a_diagram_placing_a_view_not_here_is_refused(self) -> None:
        data = {"title": "Nowhere", "kind": "diagram", "places": [{"view": "no-such-view"}]}
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_canvas_save({}, {"id": None, "data": data})
        self.assertIn("places no-such-view, which is not a view here", str(caught.exception))
        self.assertFalse((self.root / "30_VIEWS" / "nowhere.view.yaml").exists())


if __name__ == "__main__":
    unittest.main()
