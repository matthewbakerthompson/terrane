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
}


class TestTheBusinessLayersNames(unittest.TestCase):
    """Measured on the eight: five found first; two second, each behind a
    sibling the name fits as well (the dispute platform's integration
    gateway, named after it; three Collections Workspace systems a
    thousandth apart); and "Cardholder master record", which shares no
    word with "Customer profile", seventh. The floors below are those."""

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
    record's kind and asking for it back: the card issuer's 106 technology
    services, 84% first and 92% in the first three; Thurman Health's 22,
    91% and 91%; its ten typed systems, 60% and 60%. The floors are those."""

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
        for name, type_name, count, first, three in (("card issuer", "tech_services", 106, 0.83, 0.92),
                                                     ("thurman", "tech_services", 22, 0.90, 0.90),
                                                     ("thurman", "systems", 10, 0.60, 0.60)):
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


if __name__ == "__main__":
    unittest.main()
