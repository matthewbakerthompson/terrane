"""The engine's matcher (`terrane.match`): whether a name from somewhere else
is a record here.

The cases are the ones the old `difflib` pass got wrong (two servers a
number apart, two words in the other order, an abbreviation); the eight
records the business layer names its own way, which
`60_SOURCES/business_layer/aliases.yaml` pairs with this estate's; the
sample CMDB export, junk rows and all; and the CMDB pass rebuilt on it.
Where the matcher cannot tell, the test says so rather than pinning a guess.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cmdb, match  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402

from _fixture import REPO, seeded_model, teardown_shared  # noqa: E402


def tearDownModule():  # noqa: N802
    teardown_shared()


class TestWords(unittest.TestCase):
    def test_a_name_is_read_as_words(self) -> None:
        self.assertEqual(match.tokens("CardServicingAPI"), ["card", "servicing", "api"])
        self.assertEqual(match.tokens("prd-lon-web-01"), ["prd", "lon", "web", "01"])
        self.assertEqual(match.tokens("Statements of the Month"), ["statement", "month"])
        self.assertEqual(match.tokens("Access"), ["access"])

    def test_words_as_written_and_as_matched(self) -> None:
        self.assertEqual(match.words("Statements of the Month"), ["statements", "month"])
        self.assertEqual(match.singular("statements"), "statement")
        self.assertEqual(match.singular("access"), "access")

    def test_a_shared_word_is_said_as_the_name_writes_it(self) -> None:
        """An HL7 engine's reasons read "7, engine, hl" while the pieces of
        HL7 were said apart."""
        matcher = match.Matcher([("SYS-INTERFACE-ENGINE", "HL7 Interface Engine")])
        self.assertEqual(matcher.rank("HL7 engine", limit=1)[0].reasons, ("engine", "hl7"))

    def test_normalize_is_the_cmdbs_old_one(self) -> None:
        self.assertIs(cmdb.normalize_name, match.normalize)
        self.assertEqual(match.normalize("Collections Workspace Web App"), "collections workspace web")

    def test_jaro_winkler(self) -> None:
        self.assertEqual(match.jaro_winkler("martha", "martha"), 1.0)
        self.assertAlmostEqual(match.jaro_winkler("martha", "marhta"), 0.961, places=3)
        self.assertEqual(match.jaro_winkler("", "x"), 0.0)


class TestWhatDifflibGotWrong(unittest.TestCase):
    def test_two_servers_a_number_apart_are_not_one(self) -> None:
        m = match.Matcher([("A", "prd-lon-web-02"), ("B", "prd-lon-web-1")])
        self.assertEqual([c.id for c in m.rank("prd-lon-web-01")], ["B"])
        held = [c for c in m.rank("prd-lon-web-01", floor=-1) if c.id == "A"][0]
        self.assertEqual((held.score, held.reasons), (0.0, ("number differs",)))

    def test_two_words_in_the_other_order_are_one(self) -> None:
        got = match.Matcher([("A", "ERP (SAP)"), ("B", "SAP Concur")]).rank("SAP ERP")
        self.assertEqual(got[0].id, "A")
        self.assertGreaterEqual(got[0].score, 0.95)
        self.assertEqual(got[0].reasons, ("erp", "sap"))

    def test_an_abbreviation_puts_the_whole_word_first(self) -> None:
        got = match.Matcher([("D", "Ledger"), ("C", "General Ledger")]).rank("Gen Ledger")
        self.assertEqual([c.id for c in got], ["C", "D"])
        self.assertIn("gen~general", got[0].reasons)

    def test_an_exact_name_scores_one_and_an_id_counts_only_when_shared(self) -> None:
        m = match.Matcher([("SYS-AUTH-SWITCH", "Authorization Switch"), ("SYS-CARDSVC-API", "Card Servicing Service"),
                           ("SYS-CARDSVC-WEB", "Card Servicing Web")])
        self.assertEqual(m.rank("Authorization Switch")[0].score, 1.0)
        api = m.rank("Card Servicing API")
        self.assertEqual(api[0].id, "SYS-CARDSVC-API")
        self.assertIn("api", api[0].reasons)

    def test_the_same_answer_whatever_order_the_records_come_in(self) -> None:
        records = [(s["system_id"], s.get("name") or "") for s in seeded_model().all_of("systems")]
        forward, backward = match.Matcher(records), match.Matcher(list(reversed(records)))
        for name in ("Card Servicing", "Collections platform", "Enterprise data platform", "Gen Ledger"):
            with self.subTest(name=name):
                self.assertEqual(forward.rank(name, limit=8), backward.rank(name, limit=8))
                self.assertEqual(forward.rank(name, limit=8), forward.rank(name, limit=8))


#: The business layer's names for the records aliases.yaml pairs with this
#: estate's, from its own systems.csv and data_assets.csv, which live in its
#: repository and not in this one.
BUSINESS_NAMES = {
    "SYS-CORE": "Core card platform",
    "SYS-STMT": "Statement composition and delivery",
    "SYS-DISPUTE": "Dispute and chargeback management",
    "SYS-COLLECT": "Collections platform",
    "SYS-DW": "Enterprise data platform",
    "SYS-WEB": "Cardholder web servicing",
    "DA-CARDHOLDER": "Cardholder master record",
    "DA-TXN-LEDGER": "Transaction ledger",
    # Roles the layer named for a product the estate already had, when its
    # lending, merchant and compliance processes were drawn (2026-11-18).
    "SYS-AUTH": "Authorization switch",
    "SYS-REDEEM": "Rewards redemption service",
    "SYS-SCREENING": "Sanctions screening service",
    "SYS-IDV": "Identity document verification",
    "SYS-AFFORD": "Open banking affordability",
    "SYS-POS-FIN": "Point-of-sale financing service",
    "SYS-INSTALL": "Installment lending service",
    "SYS-LENDPERF": "Lending portfolio performance",
    "SYS-CARDSVC": "Card servicing service",
    "SYS-MERCH-PORTAL": "Merchant portal",
    "SYS-REG-RPT": "Regulatory reporting engine",
}


class TestTheBusinessLayersNames(unittest.TestCase):
    """Measured on the eight: five found first; two second, each behind a
    sibling the name fits as well (the dispute platform's integration
    gateway, named after it; three Collections Workspace systems a
    thousandth apart); and "Cardholder master record", which shares no
    word with "Customer profile", seventh. The eleven named for a product
    come back nine first and two second, each behind a part of the same
    product: the lending performance pipeline ahead of its semantic layer,
    the merchant portal's service ahead of its web front end. The floors
    below are those."""

    @classmethod
    def setUpClass(cls) -> None:
        aliases = read_data_file(REPO / "60_SOURCES" / "business_layer" / "aliases.yaml")
        cls.pairs = dict(aliases["systems"], **aliases["data_assets"])
        model = seeded_model()
        cls.systems = match.Matcher((s["system_id"], s.get("name") or "") for s in model.all_of("systems"))
        cls.assets = match.Matcher((a["data_asset_id"], a.get("name") or "") for a in model.all_of("data_assets"))

    def _rank(self, theirs: str) -> int:
        m = self.systems if theirs.startswith("SYS-") else self.assets
        ids = [c.id for c in m.rank(BUSINESS_NAMES[theirs], limit=10)]
        return ids.index(self.pairs[theirs]) + 1 if self.pairs[theirs] in ids else 99

    def test_every_pair_the_aliases_name_is_here(self) -> None:
        self.assertEqual(sorted(self.pairs), sorted(BUSINESS_NAMES))

    def test_five_are_found_first(self) -> None:
        for theirs in ("SYS-CORE", "SYS-STMT", "SYS-DW", "SYS-WEB", "DA-TXN-LEDGER"):
            with self.subTest(theirs=theirs):
                self.assertEqual(self._rank(theirs), 1)

    def test_the_two_beside_a_sibling_are_in_the_first_three(self) -> None:
        for theirs in ("SYS-DISPUTE", "SYS-COLLECT"):
            with self.subTest(theirs=theirs):
                self.assertLessEqual(self._rank(theirs), 3)

    def test_a_role_named_for_a_product_finds_the_product(self) -> None:
        for theirs in ("SYS-AUTH", "SYS-REDEEM", "SYS-SCREENING", "SYS-IDV", "SYS-AFFORD", "SYS-POS-FIN",
                       "SYS-INSTALL", "SYS-CARDSVC", "SYS-REG-RPT"):
            with self.subTest(theirs=theirs):
                self.assertEqual(self._rank(theirs), 1)
        for theirs in ("SYS-LENDPERF", "SYS-MERCH-PORTAL"):
            with self.subTest(theirs=theirs):
                self.assertLessEqual(self._rank(theirs), 2)


class TestTheSampleCmdbExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()
        cls.rows = cmdb.read_ci_export(REPO / "60_SOURCES" / "servicenow" / "sample_cmdb_ci_export.csv")
        cls.field_sot = cmdb.load_field_sot(REPO / "60_SOURCES" / "servicenow" / "field_sot.yaml")
        systems = cls.model.all_of("systems")
        cls.linked = {s["cmdb_ci_sys_id"]: s["system_id"] for s in systems if s.get("cmdb_ci_sys_id")}
        cls.matcher = match.Matcher((s["system_id"], s.get("name") or "") for s in systems)

    def test_six_of_the_eight_linked_cis_find_their_system_first_by_name(self) -> None:
        # Servicing CRM is Dynamics 365 Customer Service, a name it shares
        # nothing with; Dispute Management Platform is Pega Smart Dispute,
        # and its integration gateway carries the CI's name whole.
        found = {ci["name"]: self.matcher.rank(ci["name"], limit=1)[0].id == self.linked[ci["sys_id"]]
                 for ci in self.rows if ci["sys_id"] in self.linked}
        self.assertEqual(len(found), 8)
        self.assertEqual(sorted(n for n, ok in found.items() if not ok),
                         ["Dispute Management Platform", "Servicing CRM"])

    def test_no_junk_row_comes_near_the_threshold(self) -> None:
        for name in ("APP-4471", "SharePoint Team Site - Finance", "PRINTSRV07",
                     "Legacy Reporting Tool (decommissioned)", "Test Copy of Core Card Ledger"):
            with self.subTest(name=name):
                best = self.matcher.rank(name, limit=1)
                self.assertTrue(not best or best[0].score < cmdb.FUZZY_THRESHOLD, best)

    def test_the_pass_offers_the_one_misspelled_name_and_applies_nothing(self) -> None:
        result = cmdb.reconcile(self.model, self.rows, self.field_sot)
        offered = [(r.system_id, r.cmdb_name, r.confidence) for r in result.rows if r.category == "CANDIDATE_MATCH"]
        self.assertEqual(offered, [("SYS-CARDSVC-STORE", "Card Servicing Datastor", "fuzzy-0.92")])
        only = {r.cmdb_name for r in result.rows if r.category == "CMDB_ONLY"}
        self.assertIn("Test Copy of Core Card Ledger", only)

    def test_a_system_that_has_a_record_is_not_offered_another(self) -> None:
        # The copy scores 0.741 against the ledger, which has its sys_id
        # already; were the threshold low enough to reach it, the pass would
        # still not offer it.
        low = cmdb.FUZZY_THRESHOLD
        try:
            cmdb.FUZZY_THRESHOLD = 0.7
            result = cmdb.reconcile(self.model, self.rows, self.field_sot)
        finally:
            cmdb.FUZZY_THRESHOLD = low
        offered = {(r.system_id, r.cmdb_name) for r in result.rows if r.category == "CANDIDATE_MATCH"}
        self.assertNotIn(("SYS-CORE-LEDGER", "Test Copy of Core Card Ledger"), offered)


class TestTheKindsARecordMayBe(unittest.TestCase):
    """`suggest_types`: the library's kinds a record may be, by their own
    words and their aliases. Measured on what is built, hiding each typed
    record's kind and asking for it back: the card issuer's 137 technology
    services, 81% first and 93% in the first three; Thurman Health's 43,
    88% and 95%. The networks made once per account (2026-11-04) took the
    first from 84% and 91%: "Risk Virtual Network" reads as governance, risk
    and compliance, and "Cards Virtual Network" as a web front end; and the
    AI assistant's vector databases read as search first, which OpenSearch
    and AI Search also are. The fifty kinds the library gained the same day
    took the card issuer's to 80% and Thurman Health's to 86% first, the
    first three held: once an event processor and an integration adapter
    are kinds, "event" and "integration" say less about which kind a thing
    is, and Azure Event Hubs reads as DNS on "domain" before the event
    stream it is, BigQuery as enterprise search on "semantic" before the
    warehouse. Systems are harder: since the library's parts say the kind
    of what they make, chosen by hand, the card issuer's 34 typed systems
    came back 47% and 56%, Thurman Health's 19 53% and 58%; a part's
    "Service" reads as DNS on "domain". The worker, the event publisher
    and the rest say a kind since the library has one for them, and each
    of the seven systems that gave the estates comes back first: 40 and 20
    typed systems, 55% and 62%, 55% and 60%. The floors are those."""

    @classmethod
    def setUpClass(cls) -> None:
        from terrane import model as model_module
        from terrane.blocks import load_components

        cls.estates = {}
        for name, root in (("card issuer", REPO), ("thurman", REPO / "90_EXAMPLE" / "thurman-health")):
            cls.estates[name] = (load_components(root), model_module.load(root))

    def _rates(self, name: str, type_name: str):
        library, model = self.estates[name]
        ranker = match.TypeRanker(library, type_name)
        typed = [r for r in model.all_of(type_name) if r.get("component_type")]
        got = [[s.component_type_id for s in ranker.rank(r)] for r in typed]
        first = sum(1 for r, g in zip(typed, got) if g[:1] == [r["component_type"]]) / len(typed)
        three = sum(1 for r, g in zip(typed, got) if r["component_type"] in g) / len(typed)
        return len(typed), first, three

    def test_the_floors_on_both_estates(self) -> None:
        for name, type_name, count, first, three in (("card issuer", "tech_services", 137, 0.80, 0.94),
                                                     ("card issuer", "systems", 40, 0.55, 0.62),
                                                     ("thurman", "tech_services", 43, 0.86, 0.95),
                                                     ("thurman", "systems", 20, 0.55, 0.60)):
            with self.subTest(estate=name, type=type_name):
                n, f, t = self._rates(name, type_name)
                self.assertEqual(n, count)
                self.assertGreaterEqual(f, first)
                self.assertGreaterEqual(t, three)

    #: Who sells a kind: an alias that named one would make the library's
    #: words a choice of vendor. "Subnetwork" is Google Cloud's name and
    #: plain English both, and stays.
    VENDORS = {"amazon", "aws", "azure", "microsoft", "google", "gcp", "oracle", "ibm", "sap", "salesforce",
               "servicenow", "atlassian", "hashicorp", "cloudflare", "akamai", "okta", "cyberark", "crowdstrike",
               "datadog", "splunk", "snowflake", "databricks", "confluent", "mulesoft", "workday", "docusign"}

    def test_every_kind_has_aliases_and_none_names_a_vendor(self) -> None:
        library, _model = self.estates["card issuer"]
        for kind in library.values():
            with self.subTest(kind=kind.component_type_id):
                self.assertTrue(kind.aliases)
                said = {w for a in kind.aliases for w in match.tokens(a)}
                self.assertFalse(said & self.VENDORS, "an alias names a vendor")

    def test_an_alias_finds_its_kind_and_the_words_say_why(self) -> None:
        library, _model = self.estates["card issuer"]
        got = match.suggest_types({"name": "Payments message broker"}, "tech_services", library)
        self.assertEqual(got[0].component_type_id, "message-queue")
        self.assertIn("broker", got[0].words)

    def test_a_kind_added_to_the_library_is_in_the_next_suggestion(self) -> None:
        library, _model = self.estates["card issuer"]
        record = {"name": "Quantum ledger notary"}
        self.assertNotIn("notary", [s.component_type_id for s in match.suggest_types(record, "systems", library)])
        kind = library["erp"]._replace(component_type_id="notary", name="Notary", aliases=("quantum ledger notary",),
                                       description="Notarizes.", providers={})
        grown = dict(library, notary=kind)
        self.assertEqual(match.suggest_types(record, "systems", grown)[0].component_type_id, "notary")

    def test_the_words_shown_are_ones_that_mean_something(self) -> None:
        library, model = self.estates["card issuer"]
        ranker = match.TypeRanker(library, "systems")
        shown = {w for record in model.all_of("systems") for s in ranker.rank(record) for w in s.words}
        self.assertFalse(shown & match.EVERYDAY)
        self.assertFalse([w for w in shown if len(w) < 2])

    def test_nothing_offered_under_the_floor_and_the_same_answer_twice(self) -> None:
        library, model = self.estates["card issuer"]
        ranker = match.TypeRanker(library, "systems")
        for record in model.all_of("systems"):
            got = ranker.rank(record)
            self.assertTrue(all(s.score >= match.TYPE_FLOOR for s in got))
            self.assertEqual(got, match.TypeRanker(library, "systems").rank(record))

    def test_the_library_refuses_aliases_that_are_not_a_list_of_words(self) -> None:
        from terrane.blocks import LibraryError, parse_component

        with self.assertRaises(LibraryError):
            parse_component({"component_type_id": "x", "aliases": "broker"})
        self.assertEqual(parse_component({"component_type_id": "x", "aliases": [" broker "]}).aliases, ("broker",))

    def test_the_groups_and_what_is_ticked_on_both_estates(self) -> None:
        library, model = self.estates["card issuer"]
        groups = dict(match.kind_groups(model, library))
        self.assertEqual(sorted(groups), ["systems"])
        # Ten more since the business layer harvested its lending, merchant
        # and deposit systems (2026-11-18), untyped like the rest it brought.
        self.assertEqual(sum(len(rows) for rows in groups["systems"].values()), 58)
        sure = sorted(r["system_id"] for rows in groups["systems"].values() for r, got in rows if got and match.sure(got[0]))
        self.assertIn("SYS-CORE-LEDGER", sure)
        self.assertIn("SYS-GRC", sure)
        # The kinds the library gained on 2026-11-04 are what six of them
        # are: the estate's fraud detection, its KYC and identity checks,
        # its loan origination and its treasury. Of the ten harvested later
        # only the dealer loan origination system is sure; the loan
        # servicing platform reads as loan origination on "loan" alone, the
        # acquiring platform as payment processing on "acquiring", guesses.
        self.assertTrue({"SYS-FRAUD-DETECT", "SYS-KYC", "SYS-IDV-GATEWAY", "SYS-IDV-WEBHOOKS", "SYS-ORIG-DECISION",
                         "SYS-TREASURY", "SYS-LOS"} <= set(sure))
        self.assertNotIn("SYS-LOAN-SVC", sure)
        self.assertEqual(len(sure), 22)
        # One word is a guess, never ticked: the payment gateway reads as
        # payment processing on "payment" alone. The event publishers that
        # read as DNS on "domain" say their kind now. Two words are not
        # sure either: application fraud screening as fraud detection.
        paying = {r["system_id"]: got for r, got in groups["systems"]["payment-processing"]}
        self.assertEqual(paying["SYS-PAYMENT-GW"][0].words, ("payment",))
        self.assertFalse(match.sure(paying["SYS-PAYMENT-GW"][0]))
        self.assertNotIn("dns", groups["systems"])
        fraud = {r["system_id"]: got for r, got in groups["systems"]["fraud-detection"]}
        self.assertFalse(match.sure(fraud["SYS-APPFRAUD"][0]))
        # Three words under a quarter is not sure either.
        self.assertFalse(match.sure(match.TypeSuggestion("low-code", "Low-code platform", 0.249, ("a", "b", "c"))))
        self.assertTrue(match.sure(match.TypeSuggestion("crm", "CRM", 0.25, ("a", "b", "c"))))
        library, model = self.estates["thurman"]
        groups = dict(match.kind_groups(model, library))
        self.assertEqual(sum(len(rows) for rows in groups["systems"].values()), 11)

    def test_terrane_needs_types_prints_them_and_writes_nothing(self) -> None:
        import contextlib
        import io

        from terrane import cli

        root = REPO / "90_EXAMPLE" / "thurman-health"
        before = sorted((p, p.stat().st_mtime_ns) for p in (root / "10_MODEL").rglob("*.yaml"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["--root", str(root), "needs", "--types"])
        self.assertEqual(code, 0)
        said = out.getvalue()
        self.assertIn("have no component_type", said)
        self.assertIn("nothing is set", said)
        self.assertEqual(before, sorted((p, p.stat().st_mtime_ns) for p in (root / "10_MODEL").rglob("*.yaml")))


class TestWhatIsThisLine(unittest.TestCase):
    """`rank_connections` (V15): the ways two records may be joined,
    ordered by what the estate does, each with its reason, the likeliest
    marked, and nothing chosen."""

    @classmethod
    def setUpClass(cls) -> None:
        from terrane import model as model_module
        from terrane.connections import load_connections

        cls.model = model_module.load(REPO)
        cls.kinds = load_connections(REPO)
        cls.payload = [{"id": k.connection_id, "name": k.name} for k in cls.kinds.values()]

    def calls(self, a: str, b: str):
        return match.rank_connections(self.model, [
            {"kind": "interface", "from": a, "to": b, "exists": False, "kinds": self.payload},
            {"kind": "interface", "from": b, "to": a, "exists": False, "kinds": self.payload}], self.kinds)

    def test_a_call_leans_the_way_the_two_do(self) -> None:
        # The ledger is a hub, called 8 times and calling 11: counted raw it
        # came out calling the web front end; leaning, the front end calls it.
        got = self.calls("SYS-CORE-LEDGER", "SYS-CARDSVC-WEB")
        self.assertEqual((got[0]["from"], got[0]["to"], got[0].get("likeliest")),
                         ("SYS-CARDSVC-WEB", "SYS-CORE-LEDGER", True))
        self.assertEqual(got[0]["reason"], "Core Card Ledger is called 8 times in the estate, by a request on a queue; "
                         "the estate has 6 of those among its %d interfaces." % len(self.model.all_of("interfaces")))
        self.assertEqual(got[0]["likelyKind"], "queued-request")
        self.assertEqual(got[1]["reason"], "Core Card Ledger calls 11 other systems in the estate.")
        self.assertNotIn("likeliest", got[1])
        # The kinds in the order the estate uses them, the API call first.
        self.assertEqual(got[0]["kinds"][0]["id"], "api-call")
        self.assertEqual(self.calls("SYS-APPFRAUD", "SYS-LENDING-WEB")[0]["to"], "SYS-APPFRAUD")

    def test_into_a_database_as_the_estate_goes_into_one(self) -> None:
        got = self.calls("SYS-LENDING-WEB", "SYS-LENDING-DB")
        into = got[0]
        self.assertEqual((into["to"], into["store"], into.get("likeliest"), into["likelyKind"]),
                         ("SYS-LENDING-DB", "to", True, "own-datastore"))
        self.assertEqual(into["reason"], "Installment Lending Database is a relational database; the estate makes "
                         "its 6 connections into one by its own datastore.")
        self.assertEqual([k["id"] for k in into["kinds"][:2]], ["own-datastore", "pipeline-load"])
        # The web front end is of the database's own product: no shared
        # database said.
        self.assertNotIn("shared", into)

    def test_out_of_a_database_by_the_librarys_ways_out(self) -> None:
        # The estate has no connection out of a relational database, so the
        # library's ways out lead and no kind is the likeliest. It proposed
        # an API call, which a database makes to nobody.
        out = [o for o in self.calls("SYS-LENDING-WEB", "SYS-LENDING-DB") if o["from"] == "SYS-LENDING-DB"][0]
        self.assertEqual((out["store"], out["likelyKind"]), ("from", None))
        self.assertEqual([k["id"] for k in out["kinds"][:2]], ["change-data-capture", "database-extract"])
        self.assertEqual(out["reason"], "Installment Lending Database is a relational database, and the estate has "
                         "no connection out of one yet: a change data capture feed or a scheduled extract.")

    def test_reaching_into_another_products_database_is_the_shared_one(self) -> None:
        got = self.calls("SYS-LENDPERF-PIPELINE", "SYS-LENDING-DB")
        shared = [o for o in got if o["to"] == "SYS-LENDING-DB"][0]
        self.assertTrue(shared["shared"])
        self.assertTrue(shared["reason"].endswith(
            "It is already Installment Lending Service's own datastore; a second system reaching into it is the "
            "shared database the library deprecates."))
        # Never the likeliest: what the pipeline wants it takes out.
        self.assertEqual((got[0]["from"], got[0].get("likeliest")), ("SYS-LENDING-DB", True))
        self.assertEqual(got[-1], shared)

    def test_between_two_databases(self) -> None:
        got = self.calls("SYS-LENDING-DB", "SYS-REWARDS-STORE")[0]
        self.assertEqual(got["store"], "both")
        self.assertEqual([k["id"] for k in got["kinds"][:2]], ["database-replica", "database-backup"])
        self.assertNotIn("own-datastore", [k["id"] for k in got["kinds"][:4]])
        self.assertIn("no connection from one relational database to another yet", got["reason"])

    def test_thurman_healths_stores_go_as_the_estate_does(self) -> None:
        from terrane import model as model_module
        from terrane.connections import load_connections

        root = REPO / "90_EXAMPLE" / "thurman-health"
        model, kinds = model_module.load(root), load_connections(root)
        payload = [{"id": k.connection_id, "name": k.name} for k in kinds.values()]
        got = match.rank_connections(model, [
            {"kind": "interface", "from": "SYS-VNA", "to": "SYS-PACS", "exists": False, "kinds": payload}], kinds)[0]
        self.assertEqual((got["store"], got["likelyKind"], got["reason"]), (
            "from", "dicom-transfer", "Vendor Neutral Archive is archive storage; the estate makes its only "
            "connection out of archive storage by a DICOM transfer."))

    def test_a_kind_said_with_its_article(self) -> None:
        self.assertEqual([match._a(w) for w in ("API call", "HL7 v2 feed", "DICOM transfer", "its own datastore",
                                                "archive storage", "request on a queue")],
                         ["an API call", "an HL7 v2 feed", "a DICOM transfer", "its own datastore",
                          "archive storage", "a request on a queue"])

    def test_two_that_lean_alike_have_no_likeliest(self) -> None:
        got = self.calls("SYS-NOWHERE-A", "SYS-NOWHERE-B")
        self.assertFalse([o for o in got if o.get("likeliest")])
        self.assertEqual(got[0]["reason"], "SYS-NOWHERE-A calls nothing in the estate.")

    def test_a_relation_a_field_and_what_is_made(self) -> None:
        rows = self.model.relation_rows("system_realizes_capability")
        ledger = sum(1 for r in rows if r.get("system_id") == "SYS-CORE-LEDGER")
        got = match.rank_connections(self.model, [
            {"kind": "interface", "from": "SYS-CORE-LEDGER", "to": "SYS-CRM", "exists": True, "kinds": []},
            {"kind": "field", "field": "owner_org_id", "from": "SYS-CORE-LEDGER", "to": "ORG-X", "exists": False},
            {"kind": "relation", "relation": "system_realizes_capability", "from": "SYS-CORE-LEDGER", "to": "CAP-PAY",
             "exists": False},
        ], self.kinds)
        # What is made already keeps its place after what is not.
        self.assertTrue(got[-1]["exists"])
        realizes = [o for o in got if o["kind"] == "relation"][0]
        self.assertEqual(realizes["reason"], "%d like it in the estate%s." % (
            len(rows), ", %d of them Core Card Ledger's" % ledger if ledger else ""))
        owner = [o for o in got if o["kind"] == "field"][0]
        systems = self.model.all_of("systems")
        self.assertEqual(owner["reason"], "%d of the estate's %d systems say it." % (
            sum(1 for s in systems if s.get("owner_org_id")), len(systems)))



class TestNamesThatReadAlike(unittest.TestCase):
    """`alike_pairs` (V15): records of one type named alike, each read for
    why it is probably two things. Round F found every pair on both estates
    two things, which is why it is a list and not a warning."""

    @classmethod
    def setUpClass(cls) -> None:
        from terrane import model as model_module

        cls.issuer = model_module.load(REPO)
        cls.thurman = model_module.load(REPO / "90_EXAMPLE" / "thurman-health")
        cls.groups = match.alike_groups(cls.issuer)

    def pair(self, a: str, b: str) -> dict:
        got = [p for g in self.groups for p in g["pairs"] if {p["a"]["id"], p["b"]["id"]} == {a, b}]
        self.assertEqual(len(got), 1, (a, b))
        return got[0]

    def test_the_card_issuers_ten_in_four_readings(self) -> None:
        # Twelve until the Azure subscriptions had networks (2026-11-04):
        # with seventeen more subnets, NAT gateways and networks, "subnet"
        # weighs less, and the lending subnets A and B fell under the floor.
        # Ten since the capability map gained thirty-six records
        # (2026-11-18): the map's common words weigh less again, and Rewards
        # Earn & Accrual reads like the level-1 it sits under, 0.856 where it
        # was 0.846, just under the floor. The same
        # reading caught an interface drawn twice that day, the
        # authorization switch to fraud detection, before it was committed.
        self.assertEqual([(g["reading"], len(g["pairs"])) for g in self.groups],
                         [("cloud", 3), ("ends", 3), ("copy", 2), ("elsewhere", 2)])
        self.pair("CAP-BILL-04-01", "CAP-BILL-04")
        for g in self.groups:
            scores = [p["score"] for p in g["pairs"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertTrue(all(s >= match.ALIKE for s in scores))

    def test_a_letter_or_a_recovery_copy(self) -> None:
        a, b = (self.issuer.get("tech_services", i) for i in ("TS-NET-SUB-LEND-PUB-A", "TS-NET-SUB-LEND-PUB-B"))
        self.assertEqual(match._reading(self.issuer, "tech_services", a, b), {"reading": "copy", "copy": "letter"})
        dr = self.pair("TS-GCPNET-SUB-LEND-APP", "TS-GCPNET-SUB-LEND-APP-DR")
        self.assertEqual((dr["reading"], dr["copy"]), ("copy", "recovery"))
        self.assertEqual(dr["reasons"], ["app", "lending", "subnetwork"])

    def test_another_account(self) -> None:
        # A network made once per account names its parts for the network.
        a, b = (self.issuer.get("tech_services", i) for i in ("TS-NET-SUB-AZ-CARDS-APP", "TS-NET-SUB-AZ-RISK-APP"))
        self.assertEqual(match._reading(self.issuer, "tech_services", a, b),
                         {"reading": "account", "accounts": ["azure-cards-prod", "azure-risk-prod"]})

    def test_another_cloud(self) -> None:
        secrets = self.pair("TS-AWS-SECRETS", "TS-GCP-SECRET-MANAGER")
        self.assertEqual((secrets["reading"], secrets["clouds"]), ("cloud", ["AWS", "GCP"]))
        # Subnet A and the subnetwork read alike across the clouds, and the
        # cloud is said before the letter that also tells them apart.
        self.assertEqual(self.pair("TS-NET-SUB-LEND-APP-A", "TS-GCPNET-SUB-LEND-APP")["reading"], "cloud")

    def test_an_interfaces_two_ends(self) -> None:
        back = self.pair("INT-COLLECT-DIALER", "INT-DIALER-COLLECT")
        self.assertEqual((back["reading"], back["back"]), ("ends", True))
        self.assertEqual(back["a"]["name"], "Collections Platform to Outbound Contact Platform")
        one = self.pair("INT-BUREAU-GW-BUREAU", "INT-BUREAU-GW-CRM")
        self.assertEqual((one["reading"], one["back"], one["shared"]), ("ends", False, "SYS-BUREAU-GW"))

    def test_elsewhere_on_the_map(self) -> None:
        caps = self.pair("CAP-ORIG-01", "CAP-PAY-03")
        self.assertEqual((caps["reading"], caps["place"], caps["places"]),
                         ("elsewhere", "company_domain", ["Originations", "Servicing"]))
        # Thurman Health's one: two value streams' Treat, named for its stream.
        [group] = match.alike_groups(self.thurman)
        [treat] = group["pairs"]
        self.assertEqual((group["reading"], treat["place"], treat["a"]["name"], treat["b"]["name"]),
                         ("elsewhere", "value_stream_id", "Treat", "Treat"))
        self.assertEqual(len(set(treat["places"])), 2)

    def test_the_same_on_every_run(self) -> None:
        self.assertEqual(match.alike_groups(self.issuer), self.groups)

    def test_no_pair_left_unweighed_could_have_reached_the_floor(self) -> None:
        # Every two of Thurman Health's records scored in full, both ways
        # round, at a floor low enough to find 105 pairs: the pass that skips
        # names sharing no word, and Jaro-Winkler where it cannot lift the
        # sum, finds the same pairs at the same scores.
        from terrane.schema import ENTITY_TYPES

        floor, full = 0.5, {}
        for type_name, spec in ENTITY_TYPES.items():
            records = {str(r.get(spec.pk)): r for r in self.thurman.all_of(type_name) if r.get(spec.pk) and r.get("name")}
            ids = sorted(records)
            matcher = match.Matcher((i, str(records[i]["name"])) for i in ids)
            for x in ids:
                for k, y in enumerate(ids):
                    got = matcher.score(str(records[x]["name"]), k) if x != y else None
                    if got is not None and got.score >= floor:
                        key = (type_name,) + tuple(sorted((x, y)))
                        full[key] = max(full.get(key, 0.0), got.score)
        fast = {(p["type"],) + tuple(sorted((p["a"]["id"], p["b"]["id"]))): p["score"]
                for p in match.alike_pairs(self.thurman, floor)}
        self.assertEqual(len(full), 105)
        self.assertEqual(fast, full)

    def test_nothing_pairs_a_record_with_another_type(self) -> None:
        from terrane.schema import ENTITY_TYPES

        for g in self.groups:
            for p in g["pairs"]:
                found_a, found_b = self.issuer.find(p["a"]["id"]), self.issuer.find(p["b"]["id"])
                self.assertEqual((found_a[0], found_b[0]), (p["type"], p["type"]))
                self.assertIn(p["type"], ENTITY_TYPES)


if __name__ == "__main__":
    unittest.main()
