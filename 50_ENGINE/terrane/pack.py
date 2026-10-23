"""The review pack: a slide per view, from the model, with nothing installed.

The deliverable an architecture practice still makes by hand the night
before the board, produced from the model instead, so it cannot disagree
with it: a cover with the model's numbers and what validate says, a
contents page by shelf, one slide per view with the picture, the view's
own account of what it is and its counts, then one slide per product
drawn with the product architecture view, since what a board asks about
each product is what it is made of, and one per flow. It is built from the
engine's own drawings, not from the running app, laid out by ELK through the
browser where the app would use ELK, rasterized by the same browser, and
written as a deck by `terrane.pptx`, so the Pages workflow needs neither the
app listening nor npm. The deck is not committed: it is a picture of a
commit, and the commit is the record.

The pictures are drawn before the contents page is written, so the page
numbers what is in the deck: the first cut numbered the views it meant
to draw, and a ribbon left out at drawing time put every slide after it
off by one.
"""

from __future__ import annotations

import datetime as _dt
import math
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Sequence, Tuple

from . import validate
from .blocks import load_components
from .draw import Undrawable, drawing_mode, render_sequence_svg, render_svg, render_timeline_svg
from .draw.dml import slide_shapes
from .draw.table import pages, render_table_svg
from .draw.elk import open_runner
from .draw.raster import NoRasterizer, open_rasterizer
from .icons import IconMap, web_dir
from .model import Model, load
from .palette import Palette
from .payload import graph_payload
from .pptx import Deck, Paragraph, fitted, png_size
from .estate import views_of
from .query import View, ViewError, bind, load_views, resolve
from .render_sequence import all_flows
from .shipped import shipped_root

INK, INK_2, INK_3, ACCENT = "1F2A44", "4B5563", "7B8798", "3D4FA3"
#: Where the picture goes on a slide, inches: under the description, above
#: the facts line, kept in aspect inside it.
PICTURE_BOX = (0.5, 1.9, 12.3, 5.0)
CONTENTS_BOX = (0.6, 1.3, 12.2, 5.8)
#: Lines of 11pt that fit the contents box; past it the type shrinks.
CONTENTS_LINES = 31
DOT = "  ·  "


class PackError(ValueError):
    pass


class Entry(NamedTuple):
    """One picture slide, drawn and waiting for its number."""
    title: str
    description: str
    #: The picture; None when the slide is drawn as shapes instead.
    png: Optional[bytes]
    facts: str
    category: str
    #: What the contents page says in brackets after the title: nothing for
    #: a diagram, else the kind (map, timeline, flow).
    kind: str
    #: The drawing as shapes (`terrane.draw.svg.Scene`), for the editable deck.
    scene: Optional[object] = None


class _Shooter:
    """The rasterizer, opened the first time a slide needs a picture and
    not at all for an editable deck of diagrams, so that deck is written
    on a machine with no browser; what a picture needs is said when one is
    first asked for."""

    def __init__(self) -> None:
        self._rasterize = None

    def __enter__(self) -> "_Shooter":
        return self

    def __exit__(self, *exc) -> None:
        if self._rasterize is not None:
            self._rasterize.__exit__(*exc)

    def __call__(self, svg: str) -> bytes:
        if self._rasterize is None:
            try:
                self._rasterize = open_rasterizer()
            except NoRasterizer as exc:
                raise PackError("a slide needs a picture, and %s" % exc)
            self._rasterize.__enter__()
        return self._rasterize(svg)


def _commit(root: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def choose(views: Sequence[View], model: Model, names: Sequence[str]) -> List[Tuple[View, str, str]]:
    """What goes on the slides, in order: (view, subject id, category).
    Named views, `view` or `view:SUBJECT`, as named; or, named none, every
    view that takes no subject and is a picture, in the rail's order, then
    every product on the product architecture view, by name."""
    by_id = {v.view_id: v for v in views}
    wanted: List[Tuple[View, str, str]] = []
    if names:
        for spec in names:
            view_id, _, subject = spec.partition(":")
            view = by_id.get(view_id)
            if view is None:
                raise PackError("no such view: %s; the views are %s" % (view_id, ", ".join(sorted(by_id))))
            if view.parameters and not subject:
                raise PackError("%s takes a subject; name one as %s:ID" % (view_id, view_id))
            wanted.append((view, subject, view.category))
        return wanted
    for view in views:
        if not view.parameters:
            wanted.append((view, "", view.category))
    per_product = by_id.get("product-architecture")
    if per_product is not None and per_product.parameters:
        products = sorted(model.entities.get("products", {}).items(),
                          key=lambda item: str(item[1].get("name") or item[0]).lower())
        for product_id, _record in products:
            wanted.append((per_product, product_id, "Products"))
    return wanted


def build_pack(root: Path, out: Path, names: Sequence[str] = (), *, date: str = "",
               log: Optional[Callable[[str], None]] = None, all_rows: bool = False,
               editable: bool = False, since: Optional[str] = None,
               excel: Optional[Path] = None) -> Tuple[Path, int]:
    """Write the deck for the repository at `root` to `out`; the path and
    the number of slides. A view that cannot be drawn is said and left
    out, as the Node pack left it out. A register goes on one slide, its
    first page of rows, the facts line saying how many rows there are;
    with `all_rows` it goes on as many slides as it has pages. With
    `editable`, every diagram goes on as shapes a reviewer can move, glued
    by its connectors (`terrane.draw.dml`); maps, registers, timelines and
    flows keep their pictures. With `since`, a git revision, the deck opens
    with what changed since it (`terrane.diff_picture`), the slide a review
    starts from; nothing changed is said and the slide left out. With
    `excel`, a path, the workbook of what the slides show goes there
    (`terrane.shown`): the records on the pictures, the connections among
    them and a page per slide, so a reviewer's corrections come back as
    the same pages; a register is said and left out of it."""
    root = Path(root)
    say = log or (lambda text: print(text, file=sys.stderr))
    model = load(root)
    views = views_of(root)
    report = validate.run(model, views)
    palette = Palette(model.config.get("palette"))
    shipped = shipped_root()
    web = web_dir(root) or web_dir(shipped) or shipped / "web"
    icons = IconMap(web)
    components = load_components(root)
    model_name = str(model.config.get("name") or "Architecture Model")
    wanted = choose(views, model, names)
    flows = [] if names else all_flows(model)
    from .shown import Shown

    shown = Shown(model, model_name)
    shoot = _Shooter()
    elk = open_runner(web)

    entries: List[Entry] = []
    try:
        with shoot:
            for view, subject, category in wanted:
                try:
                    bound = bind(view, {view.parameters[0].name: subject}, model) if subject else view
                    graph = resolve(model, bound)
                    name = "%s%s" % (view.view_id, "--%s" % subject if subject else "")
                    told = {view.parameters[0].name: subject} if subject else None
                    if view.kind == "report":
                        shown.view(name, bound, graph, told)
                        # A register goes on one slide, its first page of
                        # rows, the facts saying how many rows there are:
                        # fifteen slides of control rows is a register, not
                        # a deck. Asked for all of them, every page goes on.
                        cut = pages(graph)
                        if not all_rows:
                            cut = cut[:1]
                        for n, (first, last) in enumerate(cut, 1):
                            svg = render_table_svg(graph, model_name=model_name, date=date, rows_from=first,
                                                   rows_to=last)
                            total = pages(graph)[-1][1]
                            where = ("rows %d\u2013%d of %d" % (first, last, total)) if total > last or first > 1 else (
                                "%d rows" % last)
                            entries.append(Entry(bound.title if n == 1 else "%s (%d of %d)" % (bound.title, n, len(cut)),
                                                 str(bound.description or "") if n == 1 else "", shoot(svg),
                                                 DOT.join(["report", where, view.view_id, category]), category,
                                                 "report"))
                        continue
                    payload = graph_payload(model, bound, palette, icons, components, graph=graph)
                    collected: list = []
                    if view.kind == "timeline":
                        svg = render_timeline_svg(payload, model_name=model_name, date=date)
                    else:
                        drawing_mode(payload)
                        svg = render_svg(payload, icon_loader=icons.read, model_name=model_name, elk=elk,
                                         scene_out=collected if editable else None)
                except (ViewError, Undrawable) as exc:
                    say("%s: %s; left out" % (view.view_id, exc))
                    continue
                counts = payload.get("counts") or {}
                facts = DOT.join([view.kind, "%s nodes" % counts.get("nodes", 0), "%s edges" % counts.get("edges", 0),
                                  view.view_id] + ([subject] if subject else []) + [category])
                scene = collected[0] if collected else None
                entries.append(Entry(bound.title, str(bound.description or ""), None if scene else shoot(svg),
                                     DOT.join([facts, "editable"]) if scene else facts, category,
                                     "" if view.kind == "diagram" else view.kind, scene))
                shown.view(name, bound, graph, told)
            for flow_id in flows:
                flow = model.get("flows", flow_id) or {}
                svg = render_sequence_svg(model, flow_id, palette, model_name=model_name, date=date)
                entries.append(Entry(str(flow.get("name") or flow_id), str(flow.get("description") or ""),
                                     shoot(svg), DOT.join(["flow", flow_id, "Flows"]), "Flows", "flow"))
                shown.flow(flow_id)
            if since:
                # The slide a review starts from: what moved since the last
                # one, first in the deck, the counts in its facts line.
                from .diff import DiffError, between
                from .diff_picture import changes_since

                try:
                    moved = between(root, since)
                    change = changes_since(root, since, date=date, web=web)
                except DiffError as exc:
                    say("what changed since %s: %s; left out" % (since, exc))
                else:
                    facts = DOT.join(["change", "%d added" % len(moved.added), "%d removed" % len(moved.removed),
                                      "%d changed" % len(moved.changed), "since %s" % since, "Changes"])
                    entries.insert(0, Entry(
                        change.title, "What moved since %s: added drawn in full, removed dashed in red, changed "
                        "with a heavy border, and what is there unchanged one hop away, faded." % since,
                        shoot(change.svg), facts, "Changes", "change"))
    finally:
        if elk is not None:
            elk.close()

    deck = Deck("%s — architecture review pack" % model_name)
    entities = sum(len(records) for records in model.entities.values())
    relationships = sum(len(rows) for rows in model.relations.values())
    errors, warnings = len(report.errors), len(report.warnings)
    commit = _commit(root)
    _cover(deck, model_name, [
        "%d entities, %d relationships, %d views." % (entities, relationships, len(views)),
        "Validate: %d error%s, %d warning%s. Every diagram is a query over the model; nothing here was drawn." % (
            errors, "" if errors == 1 else "s", warnings, "" if warnings == 1 else "s"),
        "Generated %s%s by `terrane pack`." % (date or _dt.date.today().isoformat(),
                                           " from commit %s" % commit if commit else ""),
    ])
    _contents(deck, entries)
    for entry in entries:
        _picture_slide(deck, entry)
    saved = deck.save(out)
    if excel is not None:
        # The workbook beside the deck: what the slides show, as records
        # and pages, so a reviewer's corrections come back as the same
        # pages. Written after the deck, so a deck that cannot be written
        # leaves no workbook behind to be sent without it.
        from .render_excel import sketch_sheets, workbook_bytes

        doc = shown.sketch()
        said = list(shown.notes)
        Path(excel).parent.mkdir(parents=True, exist_ok=True)
        Path(excel).write_bytes(workbook_bytes(sketch_sheets(doc, said, root)))
        for note in said:
            say(note)
        say("%s: what the slides show, as a workbook" % excel)
    return saved, len(deck.slides)


def _cover(deck: Deck, title: str, lines: Sequence[str]) -> None:
    cover = deck.slide()
    cover.text(0.6, 2.2, 12, 1.0, title, size=36, bold=True, color=INK)
    cover.text(0.6, 3.15, 12, 0.6, "Architecture review pack", size=20, color=INK_2)
    cover.text(0.6, 4.1, 12, 1.6, "\n".join(lines), size=13, color=INK_2)


def _contents(deck: Deck, entries: Sequence[Entry]) -> None:
    """The contents page: every slide by its shelf, numbered as it sits in
    the deck, the shelves stacked down three columns of about equal
    length. Eight shelves in a grid of three put the last two off the
    sheet; stacking does not."""
    slide = deck.slide()
    slide.text(0.6, 0.4, 12, 0.7, "Contents", size=24, bold=True, color=INK)
    shelves: Dict[str, List[Paragraph]] = {}
    for number, entry in enumerate(entries, 3):
        line = "%d.  %s%s" % (number, entry.title, "  (%s)" % entry.kind if entry.kind else "")
        shelves.setdefault(entry.category, []).append([(line, {"color": INK_2})])
    blocks: List[List[Paragraph]] = [[[(name, {"bold": True, "color": ACCENT})]] + lines
                                     for name, lines in shelves.items()]
    total = sum(len(block) for block in blocks) + max(0, len(blocks) - 1)
    columns: List[List[Paragraph]] = [[]]
    for block in blocks:
        if columns[-1] and len(columns) < 3 and len(columns[-1]) + len(block) > math.ceil(total / 3):
            columns.append([])
        if columns[-1]:
            columns[-1].append([])  # a blank line between shelves
        columns[-1].extend(block)
    x, y, w, h = CONTENTS_BOX
    col_w = w / 3
    longest = max(len(column) for column in columns)
    size = 11 if longest <= CONTENTS_LINES else max(7.0, 11 * CONTENTS_LINES / longest)
    for i, column in enumerate(columns):
        slide.text(x + i * col_w, y, col_w - 0.2, h, column, size=size)


def _picture_slide(deck: Deck, entry: Entry) -> None:
    slide = deck.slide()
    slide.text(0.5, 0.3, 12.3, 0.6, entry.title, size=22, bold=True, color=INK)
    slide.text(0.5, 0.9, 12.3, 0.95, " ".join(entry.description.split()), size=10.5, color=INK_2, shrink=True)
    if entry.scene is not None:
        slide.shapes_xml(slide_shapes(entry.scene, PICTURE_BOX, slide.next_id))
    else:
        x, y, w, h = fitted(png_size(entry.png), PICTURE_BOX)
        slide.image(entry.png, x, y, w, h)
    slide.text(0.5, 7.0, 12.3, 0.35, entry.facts, size=9, color=INK_3, font="Consolas")


def pack_drawings(drawings, out: Path, title: str, *, date: str = "", editable: bool = False) -> Tuple[Path, int]:
    """A deck from pictures already drawn (`terrane.quick.Drawings`): a cover,
    a contents page, then one slide per picture, rasterized through what
    the machine has; with `editable`, each diagram that carries its scene
    goes on as shapes instead, and a deck of nothing but diagrams needs no
    browser."""
    entries: List[Entry] = []
    with _Shooter() as shoot:
        for name, drawing in drawings.items():
            category = "Flows" if drawing.kind == "flow" else "Views"
            scene = getattr(drawing, "scene", None) if editable else None
            facts = DOT.join([drawing.kind, name] + (["editable"] if scene is not None else []))
            entries.append(Entry(drawing.title or name, "", None if scene is not None else shoot(drawing.svg), facts,
                                 category, "" if drawing.kind == "diagram" else drawing.kind, scene))
    deck = Deck("%s — architecture review pack" % title)
    _cover(deck, title, ["%d picture%s. Generated %s by terrane." % (
        len(entries), "" if len(entries) == 1 else "s", date or _dt.date.today().isoformat())])
    _contents(deck, entries)
    for entry in entries:
        _picture_slide(deck, entry)
    return deck.save(out), len(deck.slides)
