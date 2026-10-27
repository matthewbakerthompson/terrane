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
