"""Search over the estate's records (`terrane.search`), and the page's twin
of it (`80_APP/web/search.js`).

The index is the engine's and the scoring is done twice, in Python for
`terrane search` and the MCP server to come, and in the page for the search
box and the command palette, which on the hosted copy has no server to ask.
The two are held to the same answers on every record's name, its first
word, its first letters and a misspelling of it, on both estates, in a real
browser; on a machine with none, that test is skipped and the rest stand.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import search  # noqa: E402
from terrane.draw.browser import Chrome, browser_path  # noqa: E402

from _fixture import REPO  # noqa: E402

THURMAN = REPO / "90_EXAMPLE" / "thurman-health"
SEARCH_JS = REPO / "80_APP" / "web" / "search.js"


def setUpModule():  # noqa: N802
    global INDEXES
    INDEXES = {"card issuer": search.index_of(REPO), "thurman": search.index_of(THURMAN)}


def _first(name: str, query: str, **kw):
    return search.search(INDEXES[name], query, **kw)


class TestTheIndex(unittest.TestCase):

    def test_it_is_plain_json_of_whole_numbers(self) -> None:
        index = INDEXES["card issuer"]
        self.assertEqual(json.loads(json.dumps(index)), index)
        self.assertEqual(index["version"], search.VERSION)
        weights = [w for post in index["terms"].values() for w in post[1::2]]
        self.assertTrue(weights)
        self.assertTrue(all(isinstance(w, int) and w > 0 for w in weights))
        docs = [(d[1], d[0]) for d in index["docs"]]
        self.assertEqual(docs, sorted(docs))

    def test_the_same_index_twice(self) -> None:
        self.assertEqual(json.dumps(search.index_of(REPO), sort_keys=True),
                         json.dumps(INDEXES["card issuer"], sort_keys=True))

    def test_the_app_serves_it(self) -> None:
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import server
        self.assertEqual(server.api_search_index({}, None), INDEXES["card issuer"])
        self.assertIn(("GET", "/api/search/index"), server.ROUTES)
        shim = (REPO / "80_APP" / "web" / "static-shim.js").read_text(encoding="utf-8")
        self.assertIn('"api/search/index.json"', shim)
        html = (REPO / "80_APP" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertLess(html.index('src="search.js"'), html.index('src="app.js"'))


class TestWhatItFinds(unittest.TestCase):

    def test_a_record_named_outright_comes_first(self) -> None:
        """Interfaces are named for the systems they join and have their
        words and more; the record the query names comes ahead of them."""
        for name, query, first in (("card issuer", "core ledger", "SYS-CORE-LEDGER"),
                                   ("card issuer", "card authorization", "FLOW-CARD-AUTH"),
                                   ("card issuer", "siem", "SYS-SIEM"),
                                   ("thurman", "pacs", "SYS-PACS"),
                                   ("thurman", "EHR", "SYS-EHR"),
                                   ("thurman", "fhir server", "SYS-FHIR-SERVER"),
                                   ("thurman", "patient portal", "PRD-PATIENT-PORTAL")):
            with self.subTest(query=query):
                hit = _first(name, query, limit=1)[0]
                self.assertEqual(hit.id, first)
                self.assertTrue(hit.named)

    def test_words_half_typed_and_misspelled(self) -> None:
        typed = _first("card issuer", "led", limit=3)
        self.assertTrue(typed and all("ledger" in h.words for h in typed))
        misspelled = _first("card issuer", "ledgr", limit=3)
        self.assertTrue(misspelled and all("ledger" in h.words for h in misspelled))
        # A whole word wins over the words it starts: "statement" is had whole.
        self.assertIn(_first("card issuer", "statements", limit=1)[0].id, ("DA-STATEMENTS", "SYS-STATEMENTS"))

    def test_a_plural_is_not_the_start_of_other_words(self) -> None:
        """"pacs" read as "pac" found "pace" and "package" on the card
        issuer, which has no PACS; as typed, it finds nothing there."""
        self.assertEqual(_first("card issuer", "pacs"), [])

    def test_a_number_is_whole_or_nothing(self) -> None:
        for hit in _first("card issuer", "01", limit=0):
            self.assertEqual(hit.words, ("01",))

    def test_an_alias_finds_what_says_it_another_way(self) -> None:
        """"RDBMS" is an alias of the relational database kind: it finds the
        typed services by their kind, and a database that only says
        "relational database" after them."""
        hits = _first("card issuer", "rdbms", limit=0)
        self.assertEqual(hits[0].words[0], "rdbms")
        self.assertIn("TS-AWS-RDS", [h.id for h in hits if h.matched])
        widened = [h for h in hits if not h.matched]
        self.assertTrue(widened)
        self.assertTrue(all(h.added > 0 for h in widened))
        self.assertGreater(hits.index(widened[0]), max(hits.index(h) for h in hits if h.matched))

    def test_more_of_the_words_first(self) -> None:
        hits = _first("card issuer", "fraud scoring", limit=0)
        matched = [h.matched for h in hits]
        self.assertEqual(matched, sorted(matched, reverse=True))
        self.assertEqual(hits[0].matched, 2)

    def test_type_limit_and_nothing(self) -> None:
        systems = _first("card issuer", "ledger", type_name="systems", limit=0)
        self.assertTrue(systems)
        self.assertEqual({h.type for h in systems}, {"systems"})
        self.assertEqual(len(_first("card issuer", "ledger", limit=2)), 2)
        self.assertEqual(_first("card issuer", ""), [])
        self.assertEqual(_first("card issuer", "the of and"), [])
        self.assertEqual(_first("card issuer", "zzqx"), [])

    def test_the_command(self) -> None:
        import contextlib
        import io

        from terrane.cli import main
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            code = main(["--root", str(THURMAN), "search", "PACS", "--type", "systems", "--limit", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(said.getvalue().split()[:2], ["SYS-PACS", "systems"])
        self.assertIn("(pacs)", said.getvalue())


def _queries(index) -> list:
    """Every record's name, its first word, its first three letters and its
    longest word misspelled, and words that are properties of every object
    in the page."""
    out = {"", "the", "01", "x", "HL7", "web01", "rdbms", "message broker", "SYS-CORE",
           "constructor", "toString", "hasOwnProperty", "valueOf", "Café"}
    for _id, _type, name, *_rest in index["docs"]:
        out.add(name)
        words = name.split()
        if words:
            out.add(words[0])
            out.add(words[0][:3])
            longest = max(words, key=len)
            if len(longest) > 5:
                out.add(longest[:2] + longest[3:])
    return sorted(out)


@unittest.skipUnless(browser_path(), "no Chrome or Edge on this machine")
class TestTheSearchInThePage(unittest.TestCase):
    """search.js against search.py, on both estates, the first ten of every
    query and every hit of a few."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.browser = Chrome(width=800, height=600).__enter__()
        cls.page = cls.browser.page("about:blank")
        cls.page.evaluate(SEARCH_JS.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.__exit__(None, None, None)

    def _page(self, index, queries, limit):
        self.page.evaluate("window.__index = %s" % json.dumps(index))
        return self.page.evaluate(
            "JSON.stringify(%s.map(function (q) { return TerraneSearch.search(window.__index, q, {limit: %d})"
            ".map(function (h) { return [h.id, h.type, h.name, h.matched, h.named, h.score, h.added, h.words]; }); }))"
            % (json.dumps(queries), limit))

    def test_the_same_answers(self) -> None:
        for name, index in sorted(INDEXES.items()):
            queries = _queries(index)
            with self.subTest(estate=name):
                want = [[[h.id, h.type, h.name, h.matched, h.named, h.score, h.added, list(h.words)]
                         for h in search.search(index, q, limit=10)] for q in queries]
                got = json.loads(self._page(index, queries, 10))
                differ = [q for q, w, g in zip(queries, want, got) if w != g]
                self.assertEqual(differ, [], "%d of %d queries differ" % (len(differ), len(queries)))
                self.assertGreater(sum(len(w) for w in want), len(queries))

    def test_every_hit_of_a_few(self) -> None:
        index = INDEXES["card issuer"]
        queries = ["ledger", "card", "led", "ledgr", "rdbms", "payments", "s"]
        want = [[[h.id, h.type, h.name, h.matched, h.named, h.score, h.added, list(h.words)]
                 for h in search.search(index, q, limit=0)] for q in queries]
        self.assertEqual(json.loads(self._page(index, queries, 0)), want)

    def test_an_index_of_another_version_finds_nothing(self) -> None:
        self.assertEqual(self.page.evaluate(
            "TerraneSearch.search({version: 0, terms: {a: [0, 1]}, docs: [['X', 't', 'a', 1, 'a', 'a']]}, 'a').length"),
            0)


if __name__ == "__main__":
    unittest.main()
