"""Search over the estate's records: an index built once, a query scored
against it by adding up its weights.

The index is a plain dictionary, so it travels as JSON: the app's search box
and the command palette score a query in the page with the same arithmetic
as `search` here (`80_APP/web/search.js`), and a test holds the two to the
same answers. Every weight is a whole number, worked out here once, and the
page only adds and compares them, so the two cannot differ in a last digit
the way two languages' floating point sums can.

What a record is found by, and how much each counts:

    name 3, id 2, tags 2, kind 1.5, description 1, domain 1, type 1

times how rare the word is across the estate, `sqrt(N/df)` as the name
matcher weighs it (`terrane.match`), and a hundred, rounded. A word in two
places counts where it counts most. A query's word finds a record's word
whole (all of it, a plural as its singular), as the start of one as it is
typed (seven tenths: "led" finds "ledger" while it is typed, and "pacs" is
not the start of "package") or, when neither finds anything, as a near spelling (half:
"ledgr" finds "ledger"); a library alias in the query adds the words of the
kind it names, at half (an "RDBMS" finds what says "relational database"),
counted apart. A record that has more of the query's words is ahead of one
that has fewer; then one the query names outright, its words all of the
record's name or of its id past the type ("pacs" is SYS-PACS, whose name
is "Picture Archiving and Communication System", and not the interfaces
named for it); then the larger sum, the shorter name, the larger sum of
the added words, and the id.

    index = build(model, load_components(root))
    search(index, "core ledger")  # [Hit("SYS-CORE-LEDGER", "systems", ...)]
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, NamedTuple, Optional, Sequence, Set, Tuple

from .match import LITTLE, singular, tokens, words
from .schema import ENTITY_TYPES

#: The index's shape; the page reads only an index of this version.
VERSION = 1
#: How much a word counts by where the record has it.
FIELDS = (("name", 3.0), ("id", 2.0), ("tags", 2.0), ("kind", 1.5),
          ("description", 1.0), ("domain", 1.0), ("type", 1.0))
#: How much of a word's weight a query's word gets, in tenths: the whole
#: word, its start, a near spelling, and a word an alias added.
WHOLE, START, NEAR, ADDED = 10, 7, 5, 5
#: The shortest query word read for a near spelling: under four letters
#: nearly any word is near.
NEAR_FROM = 4


class Hit(NamedTuple):
    """A record a query found, how well, and by which of its words."""
    id: str
    type: str
    name: str
    matched: int
    named: bool
    score: int
    added: int
    words: Tuple[str, ...]


def _texts(record: Mapping[str, Any], type_name: str, kinds: Mapping[str, Any]) -> Dict[str, str]:
    entity = ENTITY_TYPES[type_name]
    tags = record.get("tags")
    kind = kinds.get(str(record.get("component_type") or ""))
    return {
        "name": str(record.get("name") or ""),
        "id": str(record.get(entity.pk) or ""),
        "tags": " ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags or ""),
        "kind": " ".join([kind.name] + list(getattr(kind, "aliases", ()) or ())) if kind else "",
        "description": str(record.get("description") or ""),
        "domain": " ".join(str(record.get(f) or "") for f in ("company_domain", "company_subdomain")),
        "type": entity.label,
    }


def build(model: Any, library: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """The index of every record in `model`, read with the library's kinds
    (`terrane.blocks.load_components`) for what a typed record is and for
    the aliases a query is widened by."""
    kinds = dict(library or {})
    docs: List[Tuple[str, str, str, int, str, str]] = []
    places: List[Dict[str, float]] = []
    for type_name in sorted(ENTITY_TYPES):
        pk = ENTITY_TYPES[type_name].pk
        for record in sorted(model.all_of(type_name), key=lambda r: str(r.get(pk))):
            texts = _texts(record, type_name, kinds)
            best: Dict[str, float] = {}
            for field, factor in FIELDS:
                for word in tokens(texts[field]):
                    if factor > best.get(word, 0.0):
                        best[word] = factor
            docs.append((texts["id"], type_name, texts["name"], len(tokens(texts["name"])),
                         _key(tokens(texts["name"])), _key(tokens(" ".join(texts["id"].split("-")[1:])))))
            places.append(best)
    n = len(docs) or 1
    df: Dict[str, int] = {}
    for best in places:
        for word in best:
            df[word] = df.get(word, 0) + 1
    terms: Dict[str, List[int]] = {}
    for k, best in enumerate(places):
        for word in sorted(best):
            terms.setdefault(word, []).extend([k, int(round(best[word] * math.sqrt(n / df[word]) * 100))])
    expand: Set[Tuple[Tuple[str, ...], Tuple[str, ...]]] = set()
    for kind in kinds.values():
        named = tuple(tokens(kind.name))
        for alias in getattr(kind, "aliases", ()) or ():
            said = tuple(tokens(alias))
            if said and named and said != named:
                expand.add((said, named))
    return {
        "version": VERSION,
        "little": sorted(LITTLE),
        "docs": [list(d) for d in docs],
        "terms": {w: terms[w] for w in sorted(terms)},
        "expand": [[list(a), list(b)] for a, b in sorted(expand)],
    }


def _key(words: Iterable[str]) -> str:
    # What a record is called, as a set: its words once each, in order.
    return " ".join(sorted(set(words)))


def _grams(word: str) -> Set[str]:
    text = " %s " % word
    return {text[i:i + 3] for i in range(len(text) - 2)}


def _near(a: Set[str], b: Set[str]) -> bool:
    # Dice over three-letter pieces at a half or more, in whole numbers.
    return 4 * len(a & b) >= len(a) + len(b)


def _words(index: Mapping[str, Any], query: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """The query's own words, once each in order, each as it is matched and
    as it was typed, and the words its aliases add."""
    own: List[Tuple[str, str]] = []
    have: Set[str] = set()
    for typed in words(query):
        w = singular(typed)
        if w not in have:
            have.add(w)
            own.append((w, typed))
    added: List[str] = []
    for said, named in index.get("expand") or ():
        if all(w in have for w in said):
            for w in named:
                if w not in have and w not in added:
                    added.append(w)
    return own, added


def search(index: Mapping[str, Any], query: str, limit: int = 10,
           type_name: Optional[str] = None) -> List[Hit]:
    """The records `query` finds, best first, at most `limit` (none when
    `limit` is 0 or less), and only of `type_name` when it is given."""
    terms: Mapping[str, Sequence[int]] = index.get("terms") or {}
    docs = index.get("docs") or []
    own, added = _words(index, query)
    vocab = sorted(terms)
    score: Dict[int, int] = {}
    extra: Dict[int, int] = {}
    matched: Dict[int, int] = {}
    said: Dict[int, List[str]] = {}

    def take(best: Dict[int, Tuple[int, str]], own_word: bool, w: str = "", typed: str = "") -> None:
        for k in sorted(best):
            value, word = best[k]
            # A word had whole is said as it was typed: "rdbms", not "rdbm".
            word = typed if word == w and typed else word
            score.setdefault(k, 0)
            if own_word:
                score[k] += value
                matched[k] = matched.get(k, 0) + 1
            else:
                extra[k] = extra.get(k, 0) + value
            if word not in said.setdefault(k, []):
                said[k].append(word)

    def offer(best: Dict[int, Tuple[int, str]], word: str, share: int) -> None:
        post = terms[word]
        for i in range(0, len(post), 2):
            k, value = post[i], share * post[i + 1]
            held = best.get(k)
            # The larger counts; between two equal, the word first in order,
            # so the page, which may meet them the other way round, says the same.
            if held is None or value > held[0] or (value == held[0] and word < held[1]):
                best[k] = (value, word)

    for w, typed in own:
        best: Dict[int, Tuple[int, str]] = {}
        if w in terms:
            offer(best, w, WHOLE)
        # A number is whole or nothing: "01" is not the start of "010".
        for t in vocab if not w.isdigit() else ():
            if t != w and t.startswith(typed):
                offer(best, t, START)
        if not best and len(w) >= NEAR_FROM and not w.isdigit():
            mine = _grams(w)
            for t in vocab:
                if _near(mine, _grams(t)):
                    offer(best, t, NEAR)
        take(best, True, w, typed)
    for w in added:
        best = {}
        if w in terms:
            offer(best, w, ADDED)
        take(best, False)

    key = _key(w for w, _typed in own)
    found = sorted((-matched.get(k, 0), 0 if key and key in (docs[k][4], docs[k][5]) else 1,
                    -score[k], docs[k][3], -extra.get(k, 0), docs[k][0], docs[k][1], k)
                   for k in score if type_name is None or docs[k][1] == type_name)
    hits = [Hit(docs[k][0], docs[k][1], docs[k][2], -m, not n, -s, -e, tuple(said[k]))
            for m, n, s, _z, e, _i, _t, k in found]
    return hits[:limit] if limit > 0 else hits


def index_of(root: Any) -> Dict[str, Any]:
    """The index of the estate at `root`."""
    from pathlib import Path

    from . import model as model_module
    from .blocks import load_components
    root = Path(root)
    return build(model_module.load(root), load_components(root))


def describe(hits: Iterable[Hit]) -> List[str]:
    """One line a hit: its id, type, name and the words it was found by."""
    return ["%-28s %-18s %s  (%s)" % (h.id, h.type, h.name, ", ".join(h.words)) for h in hits]
