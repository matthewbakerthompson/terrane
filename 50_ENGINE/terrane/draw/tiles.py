"""The tile map, laid out the way the browser lays out the app's HTML.

A map with nothing connected is not a graph, and the app does not draw it
as one: `drawTiles()` builds HTML -- a band per top-level boundary where
the field has a reading order or there are few, a card per boundary
otherwise, each thing a button in a CSS grid -- and the stylesheet does the
geometry. So the port is the stylesheet's arithmetic: `repeat(auto-fill,
minmax(min(172px, 100%), 1fr))` is a column count and a division, a flex
row with `align-items: baseline` is two baselines lined up, a line box is
the font size times the line-height factor, and a name wraps where Chrome
breaks it, measured in the app's own face (`metrics.py`). The app is the
spec: `tests/fixtures/tiles/*.json` is every box of the eleven tile maps
as the running app laid them out, and `tests/test_draw_tiles.py` holds this
layout to them.

Three things Chrome does that the arithmetic has to do too, because they
move boxes by whole pixels. A fractional border width is snapped down to
whole device pixels, so the 1.25px the palette asks for is one pixel and
the 2.00px is two, and a tile's inner width and height follow. Every
length is kept in 1/64 px units: a 12px line at 1.3 is 15.59375 high, not
15.6, and a text run's width is rounded up to the next 1/64. And a line's
baseline sits at the font's ascent rounded to whole pixels plus half the
leading floored, which is where the count beside a card's name lands a
pixel below it.
"""

from __future__ import annotations

import math
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from .metrics import Metrics, default_metrics

SANS = "Geist"

# ---- the stylesheet, as numbers -------------------------------------------
#: `.tiles` as shown: top, right, bottom, left. The bottom is the later
#: `.tiles { padding-bottom: 80px }`, room under the last row for the
#: legend strip.
HOST_PADDING = (16.0, 20.0, 80.0, 20.0)
#: `.tiles.is-export`, the padding the PNG button's clone is given.
EXPORT_PADDING = (20.0, 24.0, 28.0, 24.0)

INK = "#10141f"
INK_2 = "#4a5368"
INK_3 = "#6b7489"
PANEL = "#f8f9fc"
RULE = "#dce1ea"
RULE_2 = "#c7cedb"


class Face(NamedTuple):
    """How a run of text is set: size, weight, the line-height factor and
    the letter-spacing in pixels (Chrome adds it after every character,
    the last one included)."""
    size: float
    weight: int
    leading: float
    spacing: float = 0.0
    #: `font-variant-numeric: tabular-nums`: every digit the same width.
    tabular: bool = False


#: `.tband-name`: 1rem at 600, line-height 1.2, letter-spacing -0.01em.
BAND_NAME = Face(16, 600, 1.2, -0.16)
#: `.tband-gloss` and `.tband-n` sit in an `h3`, which the stylesheet sets
#: at 700 with letter-spacing -0.012em of its own 1.17em (15.21px); their
#: line-height is the body's 1.5. The gloss is `text-wrap: pretty`, which
#: this breaks greedily: the three glosses there are break the same way.
BAND_GLOSS = Face(12, 700, 1.5, -0.012 * 15.21)
BAND_COUNT = Face(11, 700, 1.5, -0.012 * 15.21)
#: `.tcard-h`: 13px at 600, line-height 1.3; its count 11px at 400 in
#: tabular figures.
CARD_NAME = Face(13, 600, 1.3)
CARD_COUNT = Face(11, 400, 1.3, tabular=True)
#: `.tile`: 12px at 500, line-height 1.3; `.tile-sub` 10.5px at 400.
TILE_NAME = Face(12, 500, 1.3)
TILE_TECH = Face(10.5, 400, 1.3)
#: Geist's tabular figure, measured in the app at 100px: 60 wide, every digit.
TABULAR_DIGIT = 60.0

BAND_HEAD_W = 136.0
BAND_GAP = 16.0
BAND_PAD_TOP = 16.0
BAND_PAD_BOTTOM = 18.0
BAND_FIRST_PAD_TOP = 4.0
BAND_RULE = 1.0
BAND_HEAD_PAD_TOP = 2.0
GLOSS_GAP = 3.0
COUNT_GAP = 6.0
BODY_GAP = 10.0

CARDS_MIN = 198.0
CARDS_GAP = 10.0
NESTED_MIN = 200.0
NESTED_MARGIN_TOP = 8.0
CARD_BORDER = 1.0
CARD_PAD = 9.0
CARD_RADIUS = 12.0
HEAD_MARGIN_X = 2.0
HEAD_MARGIN_BOTTOM = 8.0
HEAD_GAP = 8.0

GRID_MIN = 172.0
GRID_GAP = 7.0
LIST_GAP = 4.0
TILE_MIN_H = 42.0
TILE_PAD = (7.0, 10.0)
LIST_MIN_H = 34.0
LIST_PAD = (5.0, 9.0)
TILE_GAP = 2.0
TILE_RADIUS = 6.0
#: `-webkit-line-clamp: 2`.
NAME_LINES = 2

#: A line under a band's name, where the field is one everybody reads the
#: same way (`BAND_GLOSS` in app.js).
BAND_GLOSSES = {
    "capability_tier": {"Direct": "Strategy and management", "Core": "Customer-facing operations",
                        "Enable": "Shared support services"},
}


# ---- Chrome's arithmetic ---------------------------------------------------
def lu(value: float) -> float:
    """A length as Chrome keeps it: whole 1/64 px, rounded toward zero."""
    return math.floor(value * 64 + 1e-9) / 64


def lu_ceil(value: float) -> float:
    """A text run's inline size: rounded up to the next 1/64 px."""
    return math.ceil(value * 64 - 1e-9) / 64


def line_height(face: Face) -> float:
    return lu(face.size * face.leading)


def border_px(stroke_width: float) -> float:
    """`--tw`: the palette's 1 to 2.6 read as 1 to 2 pixels, then Chrome's
    snap of a fractional border to whole device pixels, never under one."""
    tw = round(1 + max(0.0, min(1.0, (float(stroke_width or 1) - 1) / 1.6)), 2)
    return max(1.0, float(math.floor(tw + 1e-9)))


def columns(width: float, minimum: float, gap: float) -> Tuple[int, float]:
    """`repeat(auto-fill, minmax(min(M, 100%), 1fr))` with a gap: as many
    columns as fit at the minimum, then the width shared equally."""
    n = max(1, int(math.floor((width + gap) / (minimum + gap) + 1e-9)))
    return n, (width - gap * (n - 1)) / n


def baseline(m: Metrics, face: Face) -> float:
    """Where the first line's baseline sits below its line box's top: the
    face's ascent and descent rounded to whole pixels, half the leading
    left over floored, the ascent added."""
    ascent = math.floor(m.ascent(SANS, face.weight, face.size) + 0.5)
    descent = math.floor(m.descent(SANS, face.weight, face.size) + 0.5)
    return ascent + math.floor((line_height(face) - (ascent + descent)) / 2)


def text_width(m: Metrics, text: str, face: Face) -> float:
    if face.tabular and text.isdigit():
        return len(text) * TABULAR_DIGIT * face.size / 100
    return m.width(text, SANS, face.weight, face.size) + len(text) * face.spacing


def _breakable_after(text: str, i: int) -> bool:
    """A break opportunity between text[i] and text[i + 1], as far as the
    app's names exercise UAX #14: after a space, and after a hyphen or a
    dash that is followed by a letter rather than a digit or a space.
    Not after a slash: `KYC/CIP` moves whole."""
    if i + 1 >= len(text):
        return False
    ch, nxt = text[i], text[i + 1]
    if ch == " ":
        return nxt != " "
    if ch in "-–—":
        return nxt.isalpha()
    return False


def _chunks(text: str) -> List[str]:
    """The text cut at every break opportunity; a chunk keeps the space
    that ends it, which does not count toward the line it closes."""
    out: List[str] = []
    start = 0
    for i in range(len(text)):
        if _breakable_after(text, i):
            out.append(text[start:i + 1])
            start = i + 1
    out.append(text[start:])
    return [c for c in out if c]


#: Chrome's line breaker lets a line run one 1/64 px past the width it is
#: given, against rounding (`LineBreaker::AvailableWidthToFit`).
EPSILON = 1 / 64


def _fits(m: Metrics, text: str, width: float, face: Face) -> bool:
    return lu_ceil(text_width(m, text, face)) <= width + EPSILON


def break_lines(m: Metrics, text: str, width: float, face: Face, anywhere: bool = False) -> List[str]:
    """Chrome's greedy line breaking: a chunk joins the line while the line
    still fits, trailing spaces hanging; a chunk that does not fit even
    alone overflows its line, or with `overflow-wrap: anywhere` is broken
    at the last character that fits."""
    text = str(text or "")
    lines: List[str] = []
    current = ""
    for chunk in _chunks(text):
        probe = current + chunk
        if _fits(m, probe.rstrip(" "), width, face):
            current = probe
            continue
        if current.strip():
            lines.append(current.rstrip(" "))
            current = ""
        if anywhere and not _fits(m, chunk.rstrip(" "), width, face):
            piece = ""
            for ch in chunk:
                if piece and not _fits(m, (piece + ch).rstrip(" "), width, face):
                    lines.append(piece.rstrip(" "))
                    piece = ""
                piece += ch
            current = piece
        else:
            current = chunk
    if current.strip() or not lines:
        lines.append(current.rstrip(" "))
    return lines


class _Candidate(NamedTuple):
    """A place a line may end (`LineBreakCandidate`): where the text before
    it ends if the line breaks here, where the next line's text starts if
    it does, the index of that start, and the penalty for breaking here."""
    pos_if_break: float
    pos_no_break: float
    start: int
    penalty: float


#: Chrome balances a heading of up to this many lines; past it, the lines
#: are the greedy ones.
MAX_LINES_FOR_BALANCE = 6
#: `kOrphansPenalty`: added to the last break opportunity, so a lone word
#: on the last line costs as much as a line.
ORPHANS_PENALTY = 10000.0
OVERFULL = 1e12


def _candidates(m: Metrics, text: str, face: Face) -> List[_Candidate]:
    out = [_Candidate(0.0, 0.0, 0, 0.0)]
    position = 0
    chunks = _chunks(text)
    for chunk in chunks[:-1]:
        position += len(chunk)
        prefix = text[:position]
        out.append(_Candidate(text_width(m, prefix.rstrip(" "), face), text_width(m, prefix, face), position, 0.0))
    out.append(_Candidate(text_width(m, text.rstrip(" "), face), text_width(m, text.rstrip(" "), face), len(text), 0.0))
    return out


def _score_break(m: Metrics, text: str, width: float, face: Face, lines: int) -> Optional[List[str]]:
    """Blink's `ScoreLineBreaker` as `text-wrap: balance` runs it: every
    line's slack squared, a cost per line of four times the width times
    the font size, the orphan penalty on the last opportunity, the best
    sum by dynamic programming over the break opportunities. None when
    Chrome would not use it: fewer than three opportunities, or a result
    with a different number of lines than greedy breaking, when Chrome
    bisects instead."""
    cands = _candidates(m, text, face)
    if len(cands) < 5:
        return None
    cands[-2] = cands[-2]._replace(penalty=cands[-2].penalty + ORPHANS_PENALTY)
    line_penalty = 4 * width * face.size
    available = width + EPSILON
    scores: List[Tuple[float, int, int]] = [(0.0, 0, 0)]
    active = 0
    for end in range(1, len(cands)):
        ec = cands[end]
        best, best_prev = math.inf, 0
        start_edge = ec.pos_if_break - available
        best_hope = 0.0
        for start in range(active, end):
            s_score = scores[start][0]
            if s_score + best_hope >= best:
                continue
            delta = cands[start].pos_no_break - start_edge
            if delta < 0:
                width_score = OVERFULL
                active = start + 1
            else:
                width_score = delta * delta
                best_hope = width_score
            score = s_score + width_score
            if score <= best:
                best, best_prev = score, start
        scores.append((best + ec.penalty + line_penalty, best_prev, scores[best_prev][2] + 1))
    breaks = []
    i = len(scores) - 1
    while i > 0:
        breaks.append(i)
        i = scores[i][1]
    breaks.reverse()
    if len(breaks) != lines:
        return None
    out = []
    start = 0
    for b in breaks:
        out.append(text[start:cands[b].start].rstrip(" "))
        start = cands[b].start
    return out


def _bisect_break(m: Metrics, text: str, width: float, face: Face, greedy: List[str]) -> List[str]:
    """Blink's `ParagraphLineBreaker`: the narrowest width, to a pixel, that
    still breaks into as many lines as the full width did, searched from
    eighty percent of the average line width up, every length in 1/64 px;
    the lines are then broken at that width. The search stops a pixel
    short, so which of two breaks a hair apart it lands on depends on the
    widths it tried on the way."""
    n = len(greedy)
    total = sum(lu_ceil(text_width(m, line, face)) for line in greedy)
    avg = math.floor(total * 64 / n) / 64
    lower = round(avg * 0.8 * 64) / 64
    upper = lu(width)
    while lower + 1 < upper:
        middle = math.floor((upper + lower) * 64 / 2) / 64
        if len(break_lines(m, text, middle, face)) > n:
            lower = middle
        else:
            upper = middle
    return break_lines(m, text, upper, face)


def balance_lines(m: Metrics, text: str, width: float, face: Face) -> List[str]:
    """`text-wrap: balance` the way Chrome does it: the score breaker where
    the heading has three or more places to break, the bisection where it
    has fewer or the scores disagree with greedy breaking on the count."""
    text = str(text or "")
    greedy = break_lines(m, text, width, face)
    if len(greedy) < 2 or len(greedy) > MAX_LINES_FOR_BALANCE:
        return greedy
    scored = _score_break(m, text, width, face, len(greedy))
    if scored is not None:
        return scored
    return _bisect_break(m, text, width, face, greedy)


def clamp_lines(m: Metrics, lines: Sequence[str], width: float, face: Face, limit: int = NAME_LINES) -> List[str]:
    """`-webkit-line-clamp`: the lines past the limit are cut, and the last
    one shown ends in an ellipsis after as much of it as leaves room."""
    if len(lines) <= limit:
        return list(lines)
    shown = list(lines[:limit])
    last = shown[-1]
    while last and not _fits(m, last + "…", width, face):
        last = last[:-1].rstrip(" ")
    shown[-1] = last + "…"
    return shown


def fit_line(m: Metrics, text: str, width: float, face: Face) -> str:
    """`white-space: nowrap; text-overflow: ellipsis`."""
    text = str(text or "")
    if _fits(m, text, width, face):
        return text
    cut = text
    while len(cut) > 1 and not _fits(m, cut + "…", width, face):
        cut = cut[:-1]
    return cut + "…"


def plural(n: int, word: str) -> str:
    """`plural()` in app.js."""
    if n == 1:
        return word
    if word.endswith("y") and not word[-2:-1] in "aeiou":
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "ch", "sh")):
        return word + "es"
    return word + "s"


# ---- the tree the app builds -------------------------------------------------
class Node(NamedTuple):
    data: dict
    groups: List["Node"]
    nodes: List[dict]

    def count(self) -> int:
        return len(self.nodes) + sum(g.count() for g in self.groups)


class Tree(NamedTuple):
    roots: List[Node]
    loose: List[dict]
    type_label: str


def tree(payload: dict) -> Tree:
    """`drawTiles()`'s grouping: boundaries in payload order, parents first,
    each thing under its boundary, the rest loose."""
    groups: Dict[str, Node] = {}
    roots: List[Node] = []
    nodes: List[dict] = []
    loose: List[dict] = []
    for e in payload.get("elements", []):
        d = e["data"]
        if d.get("source"):
            continue
        if d.get("isGroup"):
            groups[d["id"]] = Node(d, [], [])
        else:
            nodes.append(d)
    for e in payload.get("elements", []):
        d = e["data"]
        if not d.get("isGroup"):
            continue
        parent = d.get("parent")
        if parent and parent in groups:
            groups[parent].groups.append(groups[d["id"]])
        else:
            roots.append(groups[d["id"]])
    for d in nodes:
        parent = d.get("parent")
        if parent and parent in groups:
            groups[parent].nodes.append(d)
        else:
            loose.append(d)
    types = (payload.get("legend") or {}).get("types") or []
    return Tree(roots, loose, str(types[0].get("label")) if types else "item")


def is_banded(payload: dict, t: Tree) -> bool:
    """Bands when the top-level field has a reading order or there are only
    a few; cards when there are many."""
    lanes = payload.get("lanes") or {}
    return bool(t.roots) and (bool(lanes.get(str(t.roots[0].data.get("kind") or ""))) or len(t.roots) <= 4)


def tile_meta(payload: dict) -> str:
    """`tileMeta()`: what the map is of, the things by their own name and
    the innermost boxes."""
    t = tree(payload)
    parents = {str(e["data"].get("parent")) for e in payload.get("elements", []) if e["data"].get("isGroup")}
    leaves = sum(1 for e in payload.get("elements", []) if e["data"].get("isGroup") and e["data"]["id"] not in parents)
    n = int((payload.get("counts") or {}).get("nodes", 0))
    text = "%d %s" % (n, plural(n, t.type_label))
    if leaves:
        text += " · %d %s" % (leaves, plural(leaves, "group"))
    return text


# ---- the layout ------------------------------------------------------------
class Text(NamedTuple):
    """A run of lines set in one face: the box its line boxes stack in and
    the lines as broken."""
    x: float
    y: float
    w: float
    lines: List[str]
    face: Face

    @property
    def h(self) -> float:
        return len(self.lines) * line_height(self.face)


class Tile(NamedTuple):
    id: str
    data: dict
    x: float
    y: float
    w: float
    h: float
    border: float
    name: Text
    tech: Optional[Text]
    listed: bool


class Grid(NamedTuple):
    x: float
    y: float
    w: float
    h: float
    tiles: List[Tile]
    listed: bool


class Card(NamedTuple):
    id: str
    data: dict
    x: float
    y: float
    w: float
    h: float
    name: Text
    count: Text
    grid: Optional[Grid]
    cards: Optional["Cards"]


class Cards(NamedTuple):
    x: float
    y: float
    w: float
    h: float
    cards: List[Card]
    nested: bool


class Band(NamedTuple):
    id: str
    data: dict
    x: float
    y: float
    w: float
    h: float
    first: bool
    name: Text
    gloss: Optional[Text]
    count: Text
    cards: Optional[Cards]
    grid: Optional[Grid]


class TileLayout(NamedTuple):
    #: The host's width and the height its content needs, padding included.
    width: float
    height: float
    padding: Tuple[float, float, float, float]
    bands: List[Band]
    cards: Optional[Cards]
    loose: Optional[Grid]
    type_label: str

    def all_tiles(self) -> List[Tile]:
        out: List[Tile] = []
        for band in self.bands:
            if band.cards:
                _tiles_of_cards(band.cards, out)
            if band.grid:
                out.extend(band.grid.tiles)
        if self.cards:
            _tiles_of_cards(self.cards, out)
        if self.loose:
            out.extend(self.loose.tiles)
        return out

    def all_cards(self) -> List[Card]:
        """Every card in document order: a card, then the cards inside it."""
        out: List[Card] = []
        for band in self.bands:
            if band.cards:
                _cards_of(band.cards, out)
        if self.cards:
            _cards_of(self.cards, out)
        return out

    def all_grids(self) -> List[Grid]:
        out: List[Grid] = []
        for band in self.bands:
            if band.cards:
                _grids_of_cards(band.cards, out)
            if band.grid:
                out.append(band.grid)
        if self.cards:
            _grids_of_cards(self.cards, out)
        if self.loose:
            out.append(self.loose)
        return out

    @property
    def content(self) -> Tuple[float, float, float, float]:
        """The box inside the host's padding."""
        return (self.padding[3], self.padding[0], self.width - self.padding[1], self.height - self.padding[2])


def _tiles_of_cards(cards: Cards, out: List[Tile]) -> None:
    for card in cards.cards:
        if card.grid:
            out.extend(card.grid.tiles)
        if card.cards:
            _tiles_of_cards(card.cards, out)


def _cards_of(cards: Cards, out: List[Card]) -> None:
    for card in cards.cards:
        out.append(card)
        if card.cards:
            _cards_of(card.cards, out)


def _grids_of_cards(cards: Cards, out: List[Grid]) -> None:
    for card in cards.cards:
        if card.grid:
            out.append(card.grid)
        if card.cards:
            _grids_of_cards(card.cards, out)


class _Measured(NamedTuple):
    """A tile before its row is known: its own height, and what goes in it."""
    data: dict
    border: float
    lines: List[str]
    tech: Optional[str]
    h: float


def _measure_tile(m: Metrics, d: dict, w: float, listed: bool) -> _Measured:
    border = border_px(d.get("strokeWidth") or 1)
    pad_y, pad_x = LIST_PAD if listed else TILE_PAD
    inner_w = w - 2 * border - 2 * pad_x
    lines = break_lines(m, str(d.get("label") or ""), inner_w, TILE_NAME, anywhere=True)
    shown = clamp_lines(m, lines, inner_w, TILE_NAME)
    tech = str(d.get("tech") or "") or None
    content = len(shown) * line_height(TILE_NAME)
    if tech:
        content += TILE_GAP + line_height(TILE_TECH)
    natural = max(LIST_MIN_H if listed else TILE_MIN_H, content + 2 * border + 2 * pad_y)
    return _Measured(d, border, shown, tech, natural)


def layout_grid(m: Metrics, items: Sequence[dict], x: float, y: float, w: float, listed: bool) -> Grid:
    """`.tgrid`: tiles in equal columns, each row as tall as its tallest
    tile, every tile stretched to its row and its text centered in it."""
    if listed:
        n, cw, gap = 1, w, LIST_GAP
    else:
        n, cw = columns(w, GRID_MIN, GRID_GAP)
        gap = GRID_GAP
    measured = [_measure_tile(m, d, cw, listed) for d in items]
    tiles: List[Tile] = []
    cursor = y
    for start in range(0, len(measured), n):
        row = measured[start:start + n]
        row_h = max(t.h for t in row)
        for col, t in enumerate(row):
            tx = x + col * (cw + gap)
            pad_y, pad_x = LIST_PAD if listed else TILE_PAD
            inner_w = cw - 2 * t.border - 2 * pad_x
            inner_h = row_h - 2 * t.border - 2 * pad_y
            content = len(t.lines) * line_height(TILE_NAME) + (TILE_GAP + line_height(TILE_TECH) if t.tech else 0)
            top = cursor + t.border + pad_y + lu((inner_h - content) / 2)
            name = Text(tx + t.border + pad_x, top, inner_w, t.lines, TILE_NAME)
            tech = None
            if t.tech:
                tech = Text(tx + t.border + pad_x, top + name.h + TILE_GAP, inner_w,
                            [fit_line(m, t.tech, inner_w, TILE_TECH)], TILE_TECH)
            tiles.append(Tile(str(t.data["id"]), t.data, tx, cursor, cw, row_h, t.border, name, tech, listed))
        cursor += row_h + gap
    height = (cursor - gap - y) if measured else 0.0
    return Grid(x, y, w, height, tiles, listed)


def _layout_card(m: Metrics, node: Node, x: float, y: float, w: float) -> Card:
    """`.tcard` at its own height: the name beside its count, the things as
    a list, the boundaries inside it as cards, their margins collapsing
    where the stylesheet lets them."""
    cx = x + CARD_BORDER + CARD_PAD
    inner_w = w - 2 * CARD_BORDER - 2 * CARD_PAD
    head_y = y + CARD_BORDER + CARD_PAD
    head_w = inner_w - 2 * HEAD_MARGIN_X
    count_text = str(node.count())
    count_w = lu_ceil(text_width(m, count_text, CARD_COUNT))
    name_w = head_w - HEAD_GAP - count_w
    label = str(node.data.get("label") or "")
    lines = balance_lines(m, label, name_w, CARD_NAME)
    # A flex item is as wide as its text when that fits on one line.
    name = Text(cx + HEAD_MARGIN_X, head_y,
                min(name_w, lu_ceil(text_width(m, lines[0], CARD_NAME))) if len(lines) == 1 else name_w,
                lines, CARD_NAME)
    # `align-items: baseline`: the count's first baseline on the name's.
    count = Text(cx + HEAD_MARGIN_X + head_w - count_w, head_y + baseline(m, CARD_NAME) - baseline(m, CARD_COUNT),
                 count_w, [count_text], CARD_COUNT)
    cursor = head_y + name.h + HEAD_MARGIN_BOTTOM
    grid = None
    if node.nodes:
        grid = layout_grid(m, node.nodes, cx, cursor, inner_w, listed=True)
        cursor = grid.y + grid.h
    cards = None
    if node.groups:
        # The nested cards' top margin collapses into the heading's bottom
        # margin when nothing stands between them.
        if grid is not None:
            cursor += NESTED_MARGIN_TOP
        cards = layout_cards(m, node.groups, cx, cursor, inner_w, nested=True)
        cursor = cards.y + cards.h
    h = cursor + CARD_PAD + CARD_BORDER - y
    return Card(str(node.data["id"]), node.data, x, y, w, h, name, count, grid, cards)


def layout_cards(m: Metrics, nodes: Sequence[Node], x: float, y: float, w: float, nested: bool) -> Cards:
    """`.tcards`: cards in equal columns, each stretched to its row."""
    n, cw = columns(w, NESTED_MIN if nested else CARDS_MIN, CARDS_GAP)
    cards: List[Card] = []
    cursor = y
    for start in range(0, len(nodes), n):
        row = [_layout_card(m, node, x + col * (cw + CARDS_GAP), cursor, cw) for col, node in
               enumerate(nodes[start:start + n])]
        row_h = max(c.h for c in row)
        cards.extend(c._replace(h=row_h) for c in row)
        cursor += row_h + CARDS_GAP
    height = (cursor - CARDS_GAP - y) if nodes else 0.0
    return Cards(x, y, w, height, cards, nested)


def layout_band(m: Metrics, node: Node, x: float, y: float, w: float, first: bool, type_label: str) -> Band:
    """`.tband`: the heading column and the body, the band as tall as the
    taller, a rule above every band but the first."""
    rule = 0.0 if first else BAND_RULE
    pad_top = BAND_FIRST_PAD_TOP if first else BAND_PAD_TOP
    top = y + rule + pad_top
    label = str(node.data.get("label") or "")
    name = Text(x, top + BAND_HEAD_PAD_TOP, BAND_HEAD_W, break_lines(m, label, BAND_HEAD_W, BAND_NAME), BAND_NAME)
    cursor = name.y + name.h
    gloss = None
    words = (BAND_GLOSSES.get(str(node.data.get("kind") or "")) or {}).get(str(node.data.get("value") or ""))
    if words:
        gloss = Text(x, cursor + GLOSS_GAP, BAND_HEAD_W, break_lines(m, words, BAND_HEAD_W, BAND_GLOSS), BAND_GLOSS)
        cursor = gloss.y + gloss.h
    n = node.count()
    count = Text(x, cursor + COUNT_GAP, BAND_HEAD_W, ["%d %s" % (n, plural(n, type_label))], BAND_COUNT)
    head_h = count.y + count.h - top
    body_x = x + BAND_HEAD_W + BAND_GAP
    body_w = w - BAND_HEAD_W - BAND_GAP
    cursor = top
    cards = None
    if node.groups:
        cards = layout_cards(m, node.groups, body_x, cursor, body_w, nested=False)
        cursor = cards.y + cards.h
    grid = None
    if node.nodes:
        if cards is not None:
            cursor += BODY_GAP
        grid = layout_grid(m, node.nodes, body_x, cursor, body_w, listed=False)
        cursor = grid.y + grid.h
    body_h = cursor - top
    h = rule + pad_top + max(head_h, body_h) + BAND_PAD_BOTTOM
    return Band(str(node.data["id"]), node.data, x, y, w, h, first, name, gloss, count, cards, grid)


def layout_tiles(payload: dict, width: float = 1240, metrics: Optional[Metrics] = None,
                 padding: Tuple[float, float, float, float] = EXPORT_PADDING) -> TileLayout:
    """The tile map for a host `width` wide, every box where the browser
    puts it. `padding` is the host's: the export's by default, the
    on-screen one when comparing with what the page shows."""
    m = metrics or default_metrics()
    t = tree(payload)
    x = padding[3]
    y = padding[0]
    content_w = width - padding[1] - padding[3]
    bands: List[Band] = []
    cards = None
    if is_banded(payload, t):
        for i, node in enumerate(t.roots):
            band = layout_band(m, node, x, y, content_w, i == 0, t.type_label)
            bands.append(band)
            y += band.h
    elif t.roots:
        cards = layout_cards(m, t.roots, x, y, content_w, nested=False)
        y += cards.h
    loose = None
    if t.loose:
        loose = layout_grid(m, t.loose, x, y, content_w, listed=False)
        y += loose.h
    return TileLayout(width, y + padding[2], padding, bands, cards, loose, t.type_label)
