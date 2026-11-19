"""Names that mean the same thing: the engine's matcher.

Whether a name from somewhere else is a record here. The CMDB's last pass
(`terrane.cmdb`) asks it of a CI's name, and asked it of one `difflib`
ratio, which scored `prd-lon-web-01` against `prd-lon-web-02` at 0.93 and
"SAP ERP" against "ERP (SAP)" at 0.38; a drawing being adopted and a draft
the app is about to make are to ask it next, where today they match by id
or not at all. One answer for all of them, from the standard library alone.

A name is read as words: lower case, a run of letters or of digits, an
identifier split where it changes case or between letters and digits,
little words dropped and a plural's `s` taken off. Two names are scored
three ways and the three added: how much of their words they share, each
word weighted by how rare it is among the records (the square root of how
many records there are over how many use it); Jaro-Winkler over their words
in order; and the cosine of their three-letter pieces. A record's id says
what it is too (`SYS-CRM`, `SYS-CARDSVC-API`), so its words past the type's
prefix count when the name shares them, and not against it when it does
not: an exact name scores one. A word one name abbreviates (`gen`,
`general`) counts most of a shared one. Names that both carry numbers and
not the same ones are not the same thing, whatever else they share. A
description is not read: on the estate's own pairs it lowered every score
and changed no rank.

Every score is a sum of the four operations and square roots, added with
`math.fsum` in a fixed order and rounded to three places before it is
compared, and the results are ordered by score, then id: the same numbers
in the same order on every platform. A score always comes with its reasons,
and nothing here acts on one: a person takes a suggestion.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Mapping, NamedTuple, Optional, Sequence, Set, Tuple

#: Words too common in names to say anything.
LITTLE = frozenset(("a", "an", "and", "the", "of", "for", "to", "in", "on", "with", "by", "from", "at", "or"))
#: The words a CMDB tacks on the end of a name and a model leaves off.
NOISE = (" system", " service", " application", " app", " platform", " prod")
#: The share of its weight a word gets when the other name abbreviates it.
ABBREVIATED = 0.8
#: How the three name scores are added.
WEIGHTS = (0.6, 0.2, 0.2)


class Candidate(NamedTuple):
    """A record a name may mean, how likely, and why: the words the two
    share, or that a number differs."""
    id: str
    name: str
    score: float
    reasons: Tuple[str, ...]


def normalize(value: str) -> str:
    """A name for matching exactly: lower case, runs of anything but a
    letter or digit as one space, and a trailing word a CMDB adds and the
    model does not ("system", "app", "prod" and the like) left off."""
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    for noise in NOISE:
        if text.endswith(noise):
            text = text[: -len(noise)]
    return " ".join(text.split())


def singular(word: str) -> str:
    """A plural's s off, not that of a word that ends in two ("access")."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _split(value: str) -> str:
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", str(value or "")).lower()


def words(value: str) -> List[str]:
    """A name's words as written, in order: an identifier split where it
    changes case or between letters and digits, little words dropped."""
    return [w for w in re.findall(r"[a-z]+|[0-9]+", _split(value)) if w not in LITTLE]


def tokens(value: str) -> List[str]:
    """A name's words as they are matched: `words`, plurals singular."""
    return [singular(w) for w in words(value)]


def _as_written(name: str, said: Sequence[str]) -> Tuple[str, ...]:
    """The words two names share as the name writes them: "hl7" where both
    its pieces are shared, which read "7, engine, hl" for an HL7 engine."""
    plain = {s for s in said if "~" not in s}
    out = list(said)
    for written in sorted(set(re.findall(r"[a-z0-9]+", _split(name)))):
        pieces = tokens(written)
        if len(pieces) > 1 and all(p in plain for p in pieces):
            out = [s for s in out if s not in pieces] + [written]
    return tuple(sorted(set(out)))


def _numbers(words: Sequence[str]) -> Set[str]:
    return {w.lstrip("0") or "0" for w in words if w.isdigit()}


def _grams(words: Sequence[str]) -> Dict[str, int]:
    text = " %s " % " ".join(words)
    out: Dict[str, int] = {}
    for i in range(len(text) - 2):
        g = text[i:i + 3]
        out[g] = out.get(g, 0) + 1
    return out


def _cosine(a: Dict[str, int], b: Dict[str, int]) -> float:
    if not a or not b:
        return 0.0
    dot = math.fsum(sorted(a[g] * b[g] for g in a if g in b))
    na = math.sqrt(math.fsum(sorted(v * v for v in a.values())))
    nb = math.sqrt(math.fsum(sorted(v * v for v in b.values())))
    return dot / (na * nb)


def jaro_winkler(a: str, b: str) -> float:
    """Jaro-Winkler similarity, 0 to 1, with the usual prefix scale of 0.1
    over at most four characters."""
    if a == b:
        return 1.0 if a else 0.0
    if not a or not b:
        return 0.0
    reach = max(max(len(a), len(b)) // 2 - 1, 0)
    used = [False] * len(b)
    hits_a: List[str] = []
    for i, ch in enumerate(a):
        for j in range(max(0, i - reach), min(len(b), i + reach + 1)):
            if not used[j] and b[j] == ch:
                used[j] = True
                hits_a.append(ch)
                break
    if not hits_a:
        return 0.0
    hits_b = [b[j] for j in range(len(b)) if used[j]]
    m = len(hits_a)
    half = sum(1 for x, y in zip(hits_a, hits_b) if x != y) / 2
    jaro = (m / len(a) + m / len(b) + (m - half) / m) / 3
    prefix = 0
    for x, y in zip(a[:4], b[:4]):
        if x != y:
            break
        prefix += 1
    return jaro + prefix * 0.1 * (1 - jaro)


def _agree(x: str, y: str) -> float:
    if x == y:
        return 1.0
    short, long_ = (x, y) if len(x) <= len(y) else (y, x)
    if len(short) >= 3 and long_.startswith(short) and not short.isdigit():
        return ABBREVIATED
    return 0.0


class Matcher:
    """The records a name might mean, read once: each one's words and
    their weights, its three-letter pieces, and an index of the pieces for
    narrowing a search to the records worth scoring.

        m = Matcher([("SYS-CORE-LEDGER", "Core Card Ledger")])
        m.rank("Core card platform")  # [Candidate("SYS-CORE-LEDGER", ..., ("card", "core"))]
    """

    def __init__(self, records: Iterable[Tuple[str, str]]) -> None:
        self.records = [(str(i), str(n or "")) for i, n in records]
        self.words = [tokens(n) for _i, n in self.records]
        # The words its id adds past the type's prefix ("SYS-CARDSVC-API"
        # adds cardsvc and api): shared as its name's are, and weighed only
        # when shared, so "Authorization Switch" is all of SYS-AUTH-SWITCH.
        self.extras = [[x for x in tokens(" ".join(i.split("-")[1:])) if x not in w]
                       for (i, _n), w in zip(self.records, self.words)]
        self.grams = [_grams(w) for w in self.words]
        self.index: Dict[str, Set[int]] = {}
        for k, grams in enumerate(self.grams):
            for g in grams:
                self.index.setdefault(g, set()).add(k)
        for k, extra in enumerate(self.extras):
            for g in _grams(extra):
                self.index.setdefault(g, set()).add(k)
        n = len(self.records) or 1
        self._weight = self._weights([set(w) | set(x) for w, x in zip(self.words, self.extras)], n)

    @staticmethod
    def _weights(sets: Sequence[Set[str]], n: int) -> Dict[str, float]:
        df: Dict[str, int] = {}
        for words in sets:
            for w in words:
                df[w] = df.get(w, 0) + 1
        return {w: math.sqrt(n / c) for w, c in df.items()}

    def _w(self, word: str, table: Dict[str, float]) -> float:
        # A word no record uses is as rare as a word can be.
        return table.get(word, math.sqrt(len(self.records) or 1))

    def _shared(self, q: Sequence[str], c: Sequence[str], extra: Sequence[str],
                table: Dict[str, float]) -> Tuple[float, List[str]]:
        """How much of their words two names share, weighted, 0 to 1 (as
        Dice counts it), and the words they share; `extra` are words the
        record's id adds, counted only when one is shared."""
        left = sorted(set(c)) + sorted(set(extra) - set(c))
        named = len(set(c))
        got: List[float] = []
        said: List[str] = []
        took: List[float] = []
        for w in sorted(set(q)):
            best, at = 0.0, -1
            for k, v in enumerate(left):
                a = _agree(w, v)
                if a > best:
                    best, at = a, k
            if at >= 0:
                got.append(best * (self._w(w, table) + self._w(left[at], table)))
                said.append(w if w == left[at] else "%s~%s" % (w, left[at]))
                if at >= named:
                    took.append(self._w(left[at], table))
                else:
                    named -= 1
                del left[at]
        total = math.fsum(sorted([self._w(w, table) for w in set(q)] + [self._w(w, table) for w in set(c)] + took))
        return (math.fsum(sorted(got)) / total if total else 0.0), said

    def score(self, name: str, k: int) -> Candidate:
        """One record against a name."""
        rid, rname = self.records[k]
        q, c = tokens(name), self.words[k]
        nq, nc = _numbers(q), _numbers(c)
        if nq and nc and nq != nc:
            return Candidate(rid, rname, 0.0, ("number differs",))
        shared, said = self._shared(q, c, self.extras[k], self._weight)
        jw = jaro_winkler(" ".join(sorted(q)), " ".join(sorted(c)))
        cos = _cosine(_grams(q), self.grams[k])
        value = math.fsum([WEIGHTS[0] * shared, WEIGHTS[1] * jw, WEIGHTS[2] * cos])
        return Candidate(rid, rname, round(value, 3), _as_written(name, said))

    def reaches(self, name: str, k: int, floor: float) -> Optional[Candidate]:
        """`score`, where it is `floor` or more, and None where it is not:
        the words the two share and their pieces are weighed first, and
        Jaro-Winkler, the dearest of the three and at most one, only where
        those two leave the sum within reach. Looking for names that read
        alike among every two records of a type scored 68,000 pairs in full
        on the card issuer, four and a half seconds."""
        q = tokens(name)
        shared, _said = self._shared(q, self.words[k], self.extras[k], self._weight)
        cos = _cosine(_grams(q), self.grams[k])
        if math.fsum([WEIGHTS[0] * shared, WEIGHTS[1], WEIGHTS[2] * cos]) < floor - 0.001:
            return None
        got = self.score(name, k)
        return got if got.score >= floor else None

    def rank(self, name: str, limit: int = 5, floor: float = 0.0,
             among: Optional[Set[str]] = None) -> List[Candidate]:
        """The records `name` most likely means, best first, each over
        `floor`, at most `limit`; `among` keeps to those ids. Narrowed first
        to the records sharing a three-letter piece of the name or its id."""
        near: Set[int] = set()
        for g in _grams(tokens(name)):
            near |= self.index.get(g, set())
        out = [self.score(name, k) for k in sorted(near)
               if among is None or self.records[k][0] in among]
        out = [c for c in out if c.score > floor]
        out.sort(key=lambda c: (-c.score, c.id))
        return out[:limit]


class TypeSuggestion(NamedTuple):
    """A kind of the library a record may be, how likely, and the words of
    the record the kind is also described by."""
    component_type_id: str
    name: str
    score: float
    words: Tuple[str, ...]


#: What a record says besides its name, read for its kind.
RECORD_FIELDS = ("description", "service_category", "service_name", "product", "provider")
#: What a match on what a kind or a record is called counts, against one on
#: what either merely says: measured on both estates, doubling both put the
#: right kind first for 84% of the card issuer's technology services, where
#: weighing all words alike put it first for 72%.
CALLED = 2.0
#: Under this a kind is not offered: the weakest guesses share one stray
#: word with it ("production" with a coding assistant), and an honest
#: nothing reads better than one of them. No right first answer on the two
#: estates' typed technology services scores under 0.149.
TYPE_FLOOR = 0.12


#: Everyday words a description is full of and a kind is not told by.
#: Dropped, they moved no rate on either estate, and the words a person is
#: shown are the ones that mean something: an integration gateway was a
#: hybrid link on "back, circuit, them".
EVERYDAY = frozenset("""
it its this that these those them they their there then than so as is are be been being was were has have had do does
did not no nor all any each every some more most other others such only own same too very can will just should now
also into onto over under out up down off again further once here when where why how what which who whom whose while
one two both either neither per via whether because if else yet still even much many few lot lots way ways thing things
used use uses using make makes made get gets got set sets back behind before after between through during against
about above below across along around
""".split())


def _type_words(text: str) -> Set[str]:
    # A letter alone is no word: "B" in a subnet's name met "A/B testing".
    return {w for w in tokens(text) if len(w) > 1 and w not in EVERYDAY}


class TypeRanker:
    """The library's kinds, read once: what each is called (its name, its
    id and its aliases) and what it says (its category, description and
    providers), each word weighed by the square root of how many kinds
    there are over how many use it, and a word it is called by counted
    double. A record is read the same way, its name counted double, and
    scored against each kind by the cosine of the two. Every kind is
    ranked, not only those that apply to the record's type: a system is
    often a database or an integration engine, and Thurman Health's are
    typed so; a kind that applies to the record's type goes first on a tie."""

    def __init__(self, library: Mapping[str, Any], type_name: str = "") -> None:
        self.type_name = type_name
        kinds = sorted(library.values(), key=lambda c: c.component_type_id)
        read = []
        for c in kinds:
            called = _type_words(" ".join([c.name, c.component_type_id.replace("-", " ")]
                                          + list(getattr(c, "aliases", ()) or ())))
            said = _type_words(" ".join([c.category, c.description] + list(c.providers.values()))) - called
            read.append((c, called, said))
        df: Dict[str, int] = {}
        for _c, called, said in read:
            for w in called | said:
                df[w] = df.get(w, 0) + 1
        n = len(read) or 1
        self.weight = {w: math.sqrt(n / d) for w, d in df.items()}
        self.kinds = []
        for c, called, said in read:
            vector = {w: self.weight[w] * CALLED for w in called}
            vector.update({w: self.weight[w] for w in said})
            norm = math.sqrt(math.fsum(sorted(x * x for x in vector.values())))
            self.kinds.append((c.component_type_id, c.name, c.applies_to, vector, norm))

    def rank(self, record: Mapping[str, Any], limit: int = 3) -> List[TypeSuggestion]:
        """The kinds `record` most likely is, best first, at most `limit`.
        A word no kind uses says nothing and is left out."""
        name = {w for w in _type_words(str(record.get("name") or "")) if w in self.weight}
        rest = {w for w in _type_words(" ".join(str(record.get(f) or "") for f in RECORD_FIELDS))
                if w in self.weight} - name
        query = {w: self.weight[w] * CALLED for w in name}
        query.update({w: self.weight[w] for w in rest})
        if not query:
            return []
        qn = math.sqrt(math.fsum(sorted(x * x for x in query.values())))
        out = []
        for kid, kname, applies, vector, norm in self.kinds:
            shared = sorted(w for w in query if w in vector)
            if not shared:
                continue
            value = math.fsum(sorted(query[w] * vector[w] for w in shared)) / (qn * norm)
            if round(value, 3) < TYPE_FLOOR:
                continue
            out.append((round(value, 3), applies != self.type_name, kid, TypeSuggestion(kid, kname, round(value, 3),
                                                                                       tuple(shared))))
        out.sort(key=lambda t: (-t[0], t[1], t[2]))
        return [s for _v, _a, _k, s in out[:limit]]


def suggest_types(record: Mapping[str, Any], type_name: str, library: Mapping[str, Any],
                  limit: int = 3) -> List[TypeSuggestion]:
    """The library's kinds a record of `type_name` most likely is, best
    first, with the words that matched; nothing is set (`TypeRanker`)."""
    return TypeRanker(library, type_name).rank(record, limit)


#: The kinds of record a `component_type` is set on, and how each is said.
TYPED = (("systems", "systems"), ("tech_services", "technology services"))
#: A suggestion ticked to set before a person looks at it (V15): its kind
#: matched three of the record's words or more, at a score of a quarter or
#: more. One word is a guess: application fraud screening reads as GRC on
#: "risk" alone, and three event publishers as DNS on "domain". Of the 18
#: records on both estates matching three words or more, the three under a
#: quarter were right twice and wrong once (a risk-model platform read as
#: low-code), and the fifteen over it right but for one (transaction fraud
#: detection read as stream processing).
SURE_WORDS = 3
SURE_SCORE = 0.25


def sure(suggestion: TypeSuggestion) -> bool:
    """Whether a suggestion is ticked to set before a person looks at it
    (`SURE_WORDS`, `SURE_SCORE`)."""
    return len(suggestion.words) >= SURE_WORDS and suggestion.score >= SURE_SCORE


def kind_groups(model: Any, library: Mapping[str, Any]
                ) -> List[Tuple[str, Dict[str, List[Tuple[Mapping[str, Any], List[TypeSuggestion]]]]]]:
    """Each type a `component_type` is set on that has records with none,
    those records grouped by the kind each most likely is (blank where the
    library says nothing), each with its suggestions. Nothing is set: `terrane
    needs --types` prints them and Checks lists them."""
    out = []
    for type_name, _words in TYPED:
        bare = [r for r in model.all_of(type_name) if not r.get("component_type")]
        if not bare:
            continue
        ranker = TypeRanker(library, type_name)
        groups: Dict[str, List[Tuple[Mapping[str, Any], List[TypeSuggestion]]]] = {}
        for record in bare:
            got = ranker.rank(record)
            groups.setdefault(got[0].component_type_id if got else "", []).append((record, got))
        out.append((type_name, groups))
    return out


def _times(n: int) -> str:
    return {1: "once", 2: "twice"}.get(n, "%d times" % n)


def _kind_word(name: str) -> str:
    """A connection kind's name inside a sentence: "an API call", its
    abbreviation kept as it is."""
    first = name.split(" ")[0]
    return name if first == first.upper() else name[:1].lower() + name[1:]


#: The last words of a type's name that make it a mass noun, which takes no
#: article: "archive storage", "master data management".
MASS = ("storage", "management")


def _a(words: str) -> str:
    """A kind or a type inside a sentence with its article: "an API call",
    "an HL7 v2 feed", "a relational database", and "its own datastore" and
    "archive storage" as they are (it read "by an its own datastore")."""
    first = words.split(" ")[0]
    if first.lower() in ("its", "their", "the") or words.split(" ")[-1].lower() in MASS:
        return words
    if first.isupper() and len(first) > 1:
        # An abbreviation is said letter by letter: an HL7 feed, a DICOM one.
        return ("an " if first[:1] in "AEFHILMNORSX" else "a ") + words
    return ("an " if words[:1].lower() in "aeiou" else "a ") + words


def _either(items: Sequence[str]) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " or " + items[-1]


#: The pattern a second system reaching into a database's store is: two
#: systems integrating through one database, deprecated in the library.
SHARED_DATABASE = "shared-database-integration"


def rank_connections(model: Any, options: List[Dict[str, Any]], kinds: Mapping[str, Any],
                     library: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """What is this line? (V15): the ways the metamodel lets two records
    be joined, those not made yet ordered by what the estate does, each with
    its reason, and the first marked likeliest where it stands above the
    second. First, how often the estate makes that link between those two
    types: every interface, a relation's rows, the records of the holder's
    type that set the field. Then, for the same link, the two records
    themselves: for a call, which way each leans, the caller toward calling
    and the one called toward being called; for a relation, its rows from
    the one and to the other. A call's kinds come in the order the estate uses them,
    the likeliest named: what the one called is called by, or what the
    caller calls by, or what the estate calls by most. A connection through
    an offered interface keeps its place first, and nothing is chosen.

    A call into or out of a data store (a component type the library draws
    as a cylinder, `connections.data_stores`) is said by what the estate
    does with that kind of store: the kinds the estate goes into it, or out
    of it, by first, the likeliest named, then the library's ways in or out
    (`datastore:` on a kind), then the rest. Out of a database the
    estate had the chooser propose an API call, which a database makes to
    nobody. A system reaching into a database that another product's
    service already reads and writes as its own is the shared database the
    library deprecates: said so, and put last. `library` is the component
    types, read from the estate when not given."""
    from .connections import data_stores, fits, kind_of
    from .library import LibraryError
    from .schema import RELATION_TYPES

    if library is None:
        try:
            from .blocks import load_components
            library = load_components(model.root)
        except LibraryError:
            library = {}
    stores = data_stores(library)
    systems = {str(s.get("system_id")): s for s in model.all_of("systems")}
    products: Dict[str, Set[str]] = {}
    for row in model.relation_rows("product_includes_system"):
        products.setdefault(str(row.get("system_id")), set()).add(str(row.get("product_id")))
    order = {k: i for i, k in enumerate(kinds)}

    def store_of(system_id: str) -> str:
        kind = str((systems.get(system_id) or {}).get("component_type") or "")
        return kind if kind in stores else ""

    def type_name(type_id: str) -> str:
        found = library.get(type_id)
        return _kind_word(str(found.name if found is not None else type_id))

    def deprecated() -> bool:
        try:
            from .blocks import load_patterns
            pattern = load_patterns(model.root).get(SHARED_DATABASE)
        except LibraryError:
            return False
        return pattern is not None and pattern.status == "Deprecated"

    def name_of(entity_id: str) -> str:
        found = model.find(entity_id)
        return str((found[1].get("name") if found else "") or entity_id)

    interfaces = model.all_of("interfaces")
    kind_ids = {str(r.get("interface_id")): kind_of(r, kinds) for r in interfaces}
    used: Dict[str, int] = {}
    for k in kind_ids.values():
        if k:
            used[k] = used.get(k, 0) + 1

    def through_store(o: Dict[str, Any]) -> int:
        """A call into, out of or between data stores: its reason, its
        kinds and the likeliest from what the estate does with that kind
        of store; how wide the link is, -1 for the shared database."""
        s_from, s_to = store_of(o["from"]), store_of(o["to"])
        o["store"] = "both" if s_from and s_to else ("from" if s_from else "to")
        if o["store"] == "to":
            seen = [r for r in interfaces if store_of(str(r.get("target_system_id"))) == s_to]
        elif o["store"] == "from":
            seen = [r for r in interfaces if store_of(str(r.get("source_system_id"))) == s_from]
        else:
            seen = [r for r in interfaces if store_of(str(r.get("source_system_id"))) == s_from
                    and store_of(str(r.get("target_system_id"))) == s_to]
        by: Dict[str, int] = {}
        for r in seen:
            k = kind_ids.get(str(r.get("interface_id")))
            if k:
                by[k] = by.get(k, 0) + 1
        fit = {k for k, spec in kinds.items() if fits(spec, bool(s_from), bool(s_to))}

        def placed(payload: Dict[str, Any]) -> Tuple[int, int, int, int, int, str]:
            # What the estate does first; then the library's ways in or out,
            # one between two stores before one that needs either, in the
            # catalog's order; then the rest as the estate uses them.
            kid = payload["id"]
            mine = kid in fit
            return (-by.get(kid, 0), 0 if mine else 1, 0 if mine and kinds[kid].datastore == "both" else 1,
                    order.get(kid, len(order)) if mine else 0, 0 if mine else -used.get(kid, 0),
                    str(payload.get("name") or "").lower())
        o["kinds"] = sorted(o.get("kinds") or [], key=placed)
        # Its ways in or out, for the chips: what the estate does there,
        # then the library's.
        o["ways"] = [p["id"] for p in o["kinds"] if p["id"] in by or p["id"] in fit]
        likely = sorted(by, key=lambda k: (-by[k], order.get(k, len(order))))
        o["likelyKind"] = likely[0] if likely else None
        if o["store"] == "both":
            head = "%s and %s are both data stores" % (name_of(o["from"]), name_of(o["to"]))
            same = s_from == s_to and type_name(s_from).split(" ")[-1].lower() not in MASS
            span = ("from one %s to another" % type_name(s_from) if same
                    else "from %s to %s" % (_a(type_name(s_from)), _a(type_name(s_to))))
        else:
            store, of = (o["to"], s_to) if o["store"] == "to" else (o["from"], s_from)
            head = "%s is %s" % (name_of(store), _a(type_name(of)))
            # "into one", but "into archive storage": a mass noun has no one.
            mass = type_name(of).split(" ")[-1].lower() in MASS
            span = ("into " if o["store"] == "to" else "out of ") + (type_name(of) if mass else "one")
        if likely:
            top, total = likely[0], len(seen)
            count = ("its only connection" if total == 1 else "its %d connections" % total) if by[top] == total \
                else "%d of its %d connections" % (by[top], total)
            o["reason"] = "%s; the estate makes %s %s by %s." % (
                head, count, span, _a(_kind_word(kinds[top].name)) if top in kinds else top)
        else:
            ways = [_a(_kind_word(p["name"])) for p in o["kinds"] if p["id"] in fit]
            o["reason"] = "%s, and the estate has no connection %s yet%s." % (
                head, span, ": " + _either(ways) if ways else "")
        if o["store"] != "to":
            return len(interfaces)
        # Reaching into a store a service of another product already reads
        # and writes as its own: two systems integrating through one
        # database. Systems of the store's own product share it.
        owners = sorted({str(r.get("source_system_id")) for r in interfaces
                         if str(r.get("target_system_id")) == o["to"]
                         and kind_ids.get(str(r.get("interface_id"))) in kinds
                         and kinds[kind_ids[str(r.get("interface_id"))]].datastore == "target"
                         and kinds[kind_ids[str(r.get("interface_id"))]].integration_style == "Request-response"}
                        - {o["from"]})
        if not owners or products.get(o["from"], set()) & products.get(o["to"], set()):
            return len(interfaces)
        o["shared"] = True
        named = [name_of(s) for s in owners]
        o["reason"] += " It is already %s; a second system reaching into it is %s." % (
            "%s's own datastore" % named[0] if len(named) == 1 else "the datastore of " + " and ".join(named),
            "the shared database the library deprecates" if deprecated() else "a shared database")
        return -1

    ranked: List[Tuple[Tuple[int, int, int], Dict[str, Any]]] = []
    first: List[Dict[str, Any]] = []
    kept: List[Dict[str, Any]] = []
    for index, option in enumerate(options):
        o = dict(option)
        # A connection through an offered interface is what the person
        # dropped the system on: it keeps its place first, made or not.
        if o["kind"] == "through":
            first.append(o)
            continue
        if o.get("exists") or o.get("editable") is False:
            kept.append(o)
            continue
        wide = near = 0
        if o["kind"] == "interface":
            called = [r for r in interfaces if r.get("target_system_id") == o["to"]]
            calling = [r for r in interfaces if r.get("source_system_id") == o["from"]]

            def leans(system: str, outward: bool) -> float:
                # Which way a system leans: the share of its calls that go
                # out, or come in, one of each added so a system with no
                # calls leans neither way. Counted raw, a hub won both
                # ways: the card ledger, called 8 times and calling 11,
                # came out calling the card servicing web front end.
                ins = sum(1 for r in interfaces if r.get("target_system_id") == system)
                outs = sum(1 for r in interfaces if r.get("source_system_id") == system)
                return ((outs if outward else ins) + 1) / (ins + outs + 2)

            wide = len(interfaces)
            near = int(round(1000 * (leans(o["from"], True) + leans(o["to"], False))))
            by: Dict[str, int] = {}
            for r in called or calling:
                k = kind_ids.get(str(r.get("interface_id")))
                if k:
                    by[k] = by.get(k, 0) + 1
            likely = (sorted(by, key=lambda k: (-by[k], k)) or sorted(used, key=lambda k: (-used[k], k)) or [""])[0]
            if called:
                o["reason"] = "%s is called %s in the estate" % (name_of(o["to"]), _times(len(called)))
                if likely in by and likely in kinds:
                    o["reason"] += ", by %s; the estate has %d of those among its %d interfaces" % (
                        _a(_kind_word(kinds[likely].name)), used.get(likely, 0), wide)
                o["reason"] += "."
            elif calling:
                o["reason"] = "%s calls %d other %s in the estate." % (
                    name_of(o["from"]), len(calling), "system" if len(calling) == 1 else "systems")
            else:
                o["reason"] = "%s calls nothing in the estate." % name_of(o["from"])
            o["kinds"] = sorted(o.get("kinds") or [], key=lambda k: (-used.get(k["id"], 0), k["name"].lower()))
            o["likelyKind"] = likely or None
            if store_of(o["from"]) or store_of(o["to"]):
                wide = through_store(o)
        elif o["kind"] == "relation":
            spec = RELATION_TYPES[o["relation"]]
            rows = model.relation_rows(o["relation"])
            mine = sum(1 for r in rows if str(r.get(spec.left_column)) == o["from"])
            wide, near = len(rows), mine + sum(1 for r in rows if str(r.get(spec.right_column)) == o["to"])
            o["reason"] = ("None like it in the estate yet." if not wide else
                           "%d like it in the estate%s." % (wide, ", %d of them %s's" % (mine, name_of(o["from"]))
                                                            if mine else ""))
        elif o["kind"] == "field":
            found = model.find(o["from"])
            holders = model.all_of(found[0]) if found else []
            wide = sum(1 for r in holders if r.get(o["field"]))
            o["reason"] = "%d of the estate's %d %s say it." % (wide, len(holders), (found[0] if found else "").replace("_", " "))
        ranked.append(((-wide, -near, index), o))
    ranked.sort(key=lambda t: t[0])
    out = [o for _key, o in ranked]
    # The likeliest is said where it stands above the second, and not
    # beside a connection through what the person dropped it on.
    if len(ranked) > 1 and ranked[0][0][:2] < ranked[1][0][:2] and not any(not o.get("exists") for o in first):
        out[0]["likeliest"] = True
    return first + out + kept


#: Two names of one type the matcher scores this or more read alike (V15).
#: Round F measured it as a warning: at 0.85 the card issuer's 12 pairs and
#: Thurman Health's one were all two things, so it is a list beside the
#: rules, counted in neither box, and not a finding.
ALIKE = 0.85

#: A word that makes one name the other's recovery copy, as "Lending App
#: Subnetwork (DR)" is of "Lending App Subnetwork".
RECOVERY = frozenset(("dr",))

#: Where a record sits, read in this order: a stage's value stream, the
#: domain the company files it under, a capability's parent. Two capabilities
#: named alike in two domains are two capabilities.
PLACES = ("value_stream_id", "company_domain", "parent_capability_id")

#: Why a pair is probably two things, in the order the groups are listed
#: when they hold as many: "" is a pair nothing on the records explains.
READINGS = ("copy", "cloud", "account", "ends", "elsewhere", "")


def _written(name: str) -> Set[str]:
    # Every word as written, the little ones too: "Subnet A" differs from
    # "Subnet B" by its "a", which `words` drops.
    return set(re.findall(r"[a-z]+|[0-9]+", _split(name)))


def _place(model: Any, type_name: str, record: Mapping[str, Any], field: str) -> str:
    from .schema import ENTITY_TYPES

    value = str(record.get(field) or "")
    spec = next((f for f in ENTITY_TYPES[type_name].fields if f.name == field), None)
    if value and spec is not None and spec.ref:
        found = model.get(spec.ref, value)
        if found and found.get("name"):
            return str(found["name"])
    return value


def _reading(model: Any, type_name: str, a: Mapping[str, Any], b: Mapping[str, Any]) -> Dict[str, Any]:
    """Why two records named alike are probably two things, as the records
    themselves say it, or nothing where they do not."""
    from .schema import ENTITY_TYPES

    if type_name == "interfaces":
        ea = (str(a.get("source_system_id") or ""), str(a.get("target_system_id") or ""))
        eb = (str(b.get("source_system_id") or ""), str(b.get("target_system_id") or ""))
        if all(ea) and all(eb):
            if ea == eb[::-1]:
                return {"reading": "ends", "back": True}
            shared = sorted(set(ea) & set(eb))
            if shared and ea != eb:
                return {"reading": "ends", "back": False, "shared": shared[0]}
    ca, cb = str(a.get("cloud_provider") or ""), str(b.get("cloud_provider") or "")
    if ca and cb and ca != cb:
        return {"reading": "cloud", "clouds": sorted((ca, cb))}
    # A network is made once per account and names its parts for the
    # network: Cards App Subnet and Risk App Subnet read alike, and are two.
    aa, ab = str(a.get("cloud_account") or ""), str(b.get("cloud_account") or "")
    if aa and ab and aa != ab:
        return {"reading": "account", "accounts": [aa, ab]}
    differ = _written(str(a.get("name"))) ^ _written(str(b.get("name")))
    if differ and all((len(w) == 1 and w.isalpha()) or w in RECOVERY for w in differ):
        return {"reading": "copy", "copy": "recovery" if differ & RECOVERY else "letter"}
    held = {f.name for f in ENTITY_TYPES[type_name].fields}
    for field in PLACES:
        if field not in held or not a.get(field) or not b.get(field) or str(a[field]) == str(b[field]):
            continue
        return {"reading": "elsewhere", "place": field,
                "places": [_place(model, type_name, a, field), _place(model, type_name, b, field)]}
    return {"reading": ""}


def alike_pairs(model: Any, floor: float = ALIKE) -> List[Dict[str, Any]]:
    """Every two records of one type whose names the matcher scores `floor`
    or more against each other, each with its score, the words the two
    share and its reading (`_reading`), the higher of the two ways round
    taken. The pair's first is the one whose name sorts first. Nothing is
    changed, and nothing is a finding: two records named alike can be two
    things, and on both estates every pair is."""
    from .schema import ENTITY_TYPES

    out: List[Dict[str, Any]] = []
    for type_name, spec in ENTITY_TYPES.items():
        records = {str(r.get(spec.pk)): r for r in model.all_of(type_name) if r.get(spec.pk) and r.get("name")}
        if len(records) < 2:
            continue
        ids = sorted(records)
        matcher = Matcher((i, str(records[i]["name"])) for i in ids)
        # Two names that share no word score 0.4 at most, so only records
        # sharing a word's first three letters are weighed: a word agrees
        # with another only where they are one, or one begins the other.
        by_start: Dict[str, Set[int]] = {}
        for k, (w, x) in enumerate(zip(matcher.words, matcher.extras)):
            for word in set(w) | set(x):
                by_start.setdefault(word[:3], set()).add(k)
        best: Dict[Tuple[str, str], Candidate] = {}
        for k, i in enumerate(ids):
            near: Set[int] = set()
            for word in set(matcher.words[k]):
                near |= by_start.get(word[:3], set())
            for j in sorted(near - {k}):
                got = matcher.reaches(str(records[i]["name"]), j, floor)
                if got is None:
                    continue
                key = (min(i, got.id), max(i, got.id))
                if key not in best or got.score > best[key].score:
                    best[key] = got
        for (x, y), got in sorted(best.items()):
            a, b = sorted((records[x], records[y]), key=lambda r: (str(r["name"]).lower(), str(r.get(spec.pk))))
            pair = {"type": type_name, "score": got.score, "reasons": list(got.reasons),
                    "a": {"id": str(a.get(spec.pk)), "name": str(a["name"])},
                    "b": {"id": str(b.get(spec.pk)), "name": str(b["name"])}}
            pair.update(_reading(model, type_name, a, b))
            out.append(pair)
    return out


def alike_groups(model: Any, floor: float = ALIKE) -> List[Dict[str, Any]]:
    """`alike_pairs` grouped by reading, the group holding most first and
    `READINGS` breaking a tie, each group's pairs best first."""
    by: Dict[str, List[Dict[str, Any]]] = {}
    for pair in alike_pairs(model, floor):
        by.setdefault(pair["reading"], []).append(pair)
    groups = []
    for reading in sorted(by, key=lambda r: (-len(by[r]), READINGS.index(r))):
        pairs = sorted(by[reading], key=lambda p: (-p["score"], p["type"], p["a"]["id"], p["b"]["id"]))
        groups.append({"reading": reading, "pairs": pairs})
    return groups
