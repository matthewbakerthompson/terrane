"""Architecture as code: a model-driven layer for architecture diagrams.

Every diagram is a query over a model rather than a drawing of it. The
front door from Python is `diagrams`: give it a sketch -- a small model and
the views it wants, as a dict, a YAML string or a path -- or the folder of
a repository and the views to draw, and get the pictures back by name, each
showing itself in a notebook and saving itself to a file. The command `terrane draw` writes the same pictures beside the
file; `terrane render` draws a whole repository. (The function is not called
`draw` because `terrane.draw` is the drawing package, and a function shadowed
by its own submodule on first import is a bug, not a name.)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

__version__ = "1.0.0"
__all__ = ["__version__", "adopt", "change", "diagrams", "example", "examples", "export_archimate", "export_drawio",
           "connect", "export_changes", "export_excel", "export_plantuml", "from_parts", "made_by", "on_shape",
           "part", "presets", "since", "views"]


def diagrams(source: Any, *, date: str = "", mermaid: bool = False, views: Any = None):
    """The pictures of a sketch, or of a repository, by name
    (`terrane.quick.Drawings`).

    `source` is the sketch: a dict, the YAML text of one, or the path of a
    file holding one. A shipped view is named (`system-context`), a subject
    view bound (`{use: product-architecture, with: {product: PRD-X}}`), a
    view written out drawn as written; a sketch that names no views gets
    the context and the landscape. The `notes` on the result say what was
    filled in, what was answered for a shape, and what could not be drawn
    and why. `date` dates the title block and the timeline's current
    quarter; `mermaid` draws the Mermaid beside each SVG.

    `source` may instead be the folder of a repository, with its `10_MODEL`
    and `30_VIEWS`: then `views` names what to draw, view ids, `{use,
    with}` for subject views, and views written out with a `view_id`,
    drawn over the estate without a file (a question of the moment as a
    picture), or, left out, every view of the whole estate, the reports as
    tables; and the flows come either way, as `terrane render` draws them.

    Or the path of what someone already has: an ArchiMate model
    (`.archimate`, or `.xml` in the exchange format), a Structurizr
    workspace (`.dsl`), a C4-PlantUML diagram (`.puml`), a draw.io file
    (`.drawio`), a Visio drawing (`.vsdx`), a spreadsheet of systems
    (`.csv`, `.tsv`, or an Excel workbook, `.xlsx`), a Mermaid
    diagram (`.mmd`) or a Markdown file holding some (`.md`), read as a
    sketch the way `terrane draw --from-...` reads it, the reader's notes among
    the result's.
    """
    from .loader import ModelFileError, parse_data_text
    from .mermaid_import import ReadError
    from .quick import READERS, QuickError, check_sketch, read_any, render_repository, render_sketch

    if isinstance(source, (str, Path)) and "\n" not in str(source) and Path(source).is_dir():
        return render_repository(Path(source), views, date=date, mermaid=mermaid)
    if views is not None:
        raise TypeError("terrane.diagrams takes `views` only with a repository folder; a sketch names its own")
    read_notes: list = []

    def read_file(path: Path) -> dict:
        try:
            doc_, notes_ = read_any(path)
        except ReadError as exc:
            raise QuickError("%s: %s" % (path.name, exc)) from exc
        read_notes.extend(notes_)
        return doc_

    if isinstance(source, dict):
        doc = check_sketch(source)
    elif isinstance(source, Path):
        doc = read_file(source)
    elif isinstance(source, str):
        # A path when it reads like one: one line, ending in a suffix a
        # reader takes or carrying a separator. Anything else is the sketch
        # itself.
        suffixes = (".yaml", ".yml") + tuple(READERS)
        is_path = "\n" not in source and (source.lower().endswith(suffixes) or "/" in source or "\\" in source)
        if is_path:
            doc = read_file(Path(source))
        else:
            try:
                data = parse_data_text(source, "the sketch")
            except ModelFileError as exc:
                # The bundled reader refuses text that is not a mapping where
                # PyYAML returns the string; either way it is not a sketch.
                raise QuickError(str(exc)) from exc
            doc = check_sketch(data)
    else:
        raise TypeError("terrane.diagrams takes a sketch as a dict, the YAML text of one, or a path; got %s"
                        % type(source).__name__)
    drawings = render_sketch(doc, date=date, mermaid=mermaid)
    drawings.notes[:0] = read_notes
    return drawings


def views(root: Any = None):
    """The shipped views a sketch may name, as records: id, kind, category,
    title, description, the subject a view takes, and the fields it reads
    off the records, which a sketch has to set for the picture to have its
    boundaries and colors. With `root`, an estate's own views instead."""
    from pathlib import Path as _Path

    from .quick import shipped_views

    return shipped_views(_Path(root) if root else None)


def presets(root: Any = None):
    """The shipped shapes, kits, parts, landing zones and connection kinds
    a sketch may draw on, as data: `shapes` (a product sits on one as
    `archetype:`), `kits` and `parts` (assembled under `compose:`, with
    what each asks for and requires), `landing_zones` (the shared service
    each provider answers a kind with, which a sketch may name its own
    for), and `connections` (the ways two systems are connected here, each
    with what a new interface of the kind is proposed with). With `root`,
    an estate's own library after the shipped one: its kinds, its parts."""
    from pathlib import Path as _Path

    from .quick import shipped_presets

    return shipped_presets(_Path(root) if root else None)


def made_by(source: Any) -> Dict[str, List[dict]]:
    """What the shapes and parts in a sketch make, by the product they make
    it for, before anything is drawn: each record's type, id, name and the
    part that made it. `source` is a sketch as a dict (what `on_shape` and
    `from_parts` return) or the path of a sketch or of any file a reader
    reads. With the ids in hand, `connect(made_id, "SYS-X", kind)` joins a
    part's system to the rest of the estate, and the drawing shows the
    line; `pictures.made` says the same once a sketch is drawn."""
    from pathlib import Path as _Path

    from .quick import check_sketch, made_by as _made_by, read_any

    doc = check_sketch(source) if isinstance(source, dict) else read_any(_Path(source))[0]
    return _made_by(doc)


def connect(source: str, target: str, kind: str, *, name: str = "", interface_id: str = "", **fields: Any) -> dict:
    """An interface of a connection kind between two systems, as the record
    a sketch takes under `interfaces` (or `terrane.adopt({"interfaces": [...]},
    root)`): the kind's proposal from `terrane.presets()["connections"]`, its
    style, first protocol and authentication, frequency, direction and
    patterns, with `fields` over them; the kind by its id or its name
    (`api-call`, `API call`), refused with the kinds when there is none."""
    from .quick import connection_of

    return connection_of(source, target, kind, name=name, interface_id=interface_id, **fields)


def examples():
    """The names of the example sketches beside the engine, for `example`."""
    from .quick import example_names

    return example_names()


def example(name: str = "payments") -> str:
    """One example sketch's text, to start from; refused with the names
    when there is no such example."""
    from .quick import example_text

    return example_text(name)


def export_archimate(root: Any, out: Any = None):
    """The repository at `root` as an ArchiMate exchange file at `out`
    (`70_ARTIFACTS/export/archimate.xml` by default): elements,
    relationships, and every picture view laid out; the path written and
    the notes, what was left out and why."""
    from pathlib import Path as _Path

    from .blocks import load_components
    from .icons import IconMap, web_dir
    from .model import load
    from .palette import Palette
    from .estate import views_of
    from .render_archimate import export_archimate as _export
    from .shipped import shipped_root

    root = _Path(root)
    model = load(root)
    shipped = shipped_root()
    web = web_dir(root) or web_dir(shipped) or shipped / "web"
    return _export(model, views_of(root), _Path(out) if out else root / "70_ARTIFACTS" / "export" / "archimate.xml",
                   Palette(model.config.get("palette")), IconMap(web), load_components(root))


def export_drawio(root: Any, out: Any = None, views: Any = None):
    """The repository at `root` as one draw.io file at `out`
    (`70_ARTIFACTS/export/estate.drawio` by default): a page per picture
    view, or per view named in `views`, each box where the engine's own
    layout put it, in the styles the reader takes back to their types;
    the path written and the notes, what was left out and why."""
    from pathlib import Path as _Path

    from .blocks import load_components
    from .icons import IconMap, web_dir
    from .model import load
    from .palette import Palette
    from .estate import views_of
    from .render_drawio import export_drawio as _export
    from .shipped import shipped_root

    root = _Path(root)
    model = load(root)
    shipped = shipped_root()
    web = web_dir(root) or web_dir(shipped) or shipped / "web"
    wanted = views_of(root)
    if views is not None:
        names = set(views)
        wanted = [v for v in wanted if v.view_id in names]
    return _export(model, wanted, _Path(out) if out else root / "70_ARTIFACTS" / "export" / "estate.drawio",
                   Palette(model.config.get("palette")), IconMap(web), load_components(root), web)


def export_plantuml(root: Any, out: Any = None, views: Any = None):
    """The repository at `root` as C4-PlantUML, a `.puml` per picture view
    under `out` (`70_ARTIFACTS/export/plantuml` by default), or per view
    named in `views`: the macros the reader takes back, the method's
    colors as element tags; the paths written and the notes."""
    from pathlib import Path as _Path

    from .model import load
    from .palette import Palette
    from .estate import views_of
    from .render_plantuml import export_plantuml as _export

    root = _Path(root)
    model = load(root)
    wanted = views_of(root)
    if views is not None:
        names = set(views)
        wanted = [v for v in wanted if v.view_id in names]
    return _export(model, wanted, _Path(out) if out else root / "70_ARTIFACTS" / "export" / "plantuml",
                   Palette(model.config.get("palette")))


def export_excel(root: Any, out: Any = None):
    """The repository at `root` as one Excel workbook at `out`
    (`70_ARTIFACTS/export/estate.xlsx` by default): a contents sheet, a
    sheet per entity type with the CSV export's columns, the systems first
    so the spreadsheet reader takes the workbook back, and a relations
    sheet; the path written."""
    from pathlib import Path as _Path

    from .model import load
    from .render_excel import export_excel as _export

    root = _Path(root)
    return _export(load(root), _Path(out) if out else root / "70_ARTIFACTS" / "export" / "estate.xlsx")


def _product_id(name: str, product_id: Any) -> str:
    import re

    if product_id:
        return str(product_id)
    slug = re.sub(r"[^A-Z0-9]+", "-", str(name).upper()).strip("-") or "X"
    return slug if slug.startswith("PRD-") else "PRD-" + slug


def on_shape(shape: str, name: str, *, product_id: str = None, domain: str = "", answers: dict = None,
             modules: Any = (), views: Any = ("product-architecture", "product-parts", "onboarding"),
             extra: dict = None) -> dict:
    """The sketch of one product on a shipped shape (`terrane.presets()["shapes"]`
    names them), ready for `diagrams`: `answers` are the shape's parameters
    (what it asks for and the sketch would otherwise be answered for with
    a placeholder), `modules` the parts added beside the shape's own,
    `views` the subject views to draw it with, `extra` any other records of
    the sketch (`{"systems": [...]}`) merged in. Three lines in a notebook
    where the YAML was a file."""
    pid = _product_id(name, product_id)
    product: dict = {"product_id": pid, "name": name, "archetype": shape}
    if domain:
        product["company_domain"] = domain
    if answers:
        product["parameters"] = dict(answers)
    if modules:
        product["modules"] = [{"module": m} if isinstance(m, str) else dict(m) for m in modules]
    doc: dict = {"model": {"name": "%s, on %s" % (name, shape)}, "products": [product],
                 "views": [{"use": v, "with": {"product": pid}} if isinstance(v, str) else v for v in views]}
    for key, value in (extra or {}).items():
        doc.setdefault(key, []).extend(value) if isinstance(value, list) and isinstance(doc.get(key), list) else doc.setdefault(key, value)
    return doc


def from_parts(provider: str, name: str, *, parts: Any, product_id: str = None, domain: str = "",
               answers: dict = None, views: Any = ("product-architecture", "product-parts"),
               extra: dict = None) -> dict:
    """The sketch of one product assembled from the shipped kits and parts
    (`terrane.presets()["kits"]` and `["parts"]`) on a provider's landing zone,
    ready for `diagrams`: `parts` the kit or part ids, `answers` what they
    ask for, `views` the subject views to draw it with, `extra` any other
    records merged in."""
    pid = _product_id(name, product_id)
    compose: dict = {"provider": provider, "modules": [{"module": p} if isinstance(p, str) else dict(p) for p in parts]}
    product: dict = {"product_id": pid, "name": name, "compose": compose}
    if answers:
        # The answers sit on the product, as on one the Assemble panel
        # writes; `compose` itself takes none, and the first cut put them
        # there and was refused the first time a sketch had any.
        product["parameters"] = dict(answers)
    if domain:
        product["company_domain"] = domain
    doc: dict = {"model": {"name": "%s, from parts" % name}, "products": [product],
                 "views": [{"use": v, "with": {"product": pid}} if isinstance(v, str) else v for v in views]}
    for key, value in (extra or {}).items():
        doc.setdefault(key, []).extend(value) if isinstance(value, list) and isinstance(doc.get(key), list) else doc.setdefault(key, value)
    return doc


def part(part_id: str, provider: str = "AWS", *, name: str = None, answers: dict = None,
         views: Any = ("product-architecture", "product-parts"), extra: dict = None) -> dict:
    """The sketch of one shipped part (`terrane.presets()["parts"]` names them)
    with the parts it requires, assembled on a provider's landing zone,
    ready for `diagrams`: what the parts ask for is answered with
    placeholders that name themselves unless `answers` says otherwise, so
    `terrane.diagrams(terrane.part("mobile-channel"))` is the part's own picture,
    the one the library's parts page carries, in a notebook cell. Refused
    by name, with the names, when there is no such part."""
    from .modules import load_modules
    from .pictures import _sample_answers, requires_of
    from .quick import QuickError
    from .shipped import shipped_root

    modules = load_modules(shipped_root())
    module = modules.get(part_id)
    if module is None or module.is_kit:
        parts = sorted(m.module_id for m in modules.values() if not m.is_kit)
        raise QuickError("no shipped part %r; the parts are %s" % (part_id, ", ".join(parts)))
    members = requires_of(module, modules)
    title = name or "Sample %s" % module.name.lower()
    # No estate here to wire a `caller_system` to; the placeholder names
    # itself, as it does on the parts page.
    answered = _sample_answers(members, type("Estate", (), {"entities": {}})(), modules, title)
    answered.update(answers or {})
    return from_parts(provider, title, parts=members, answers=answered, views=views, extra=extra)


def change(source: Any, root: Any, *, owner: str = None, date: str = "", correct: bool = False):
    """What `source` would add to the repository at `root`, as a picture
    (`terrane.quick.Drawing`): the new records in full, the estate's own
    things one hop away faded, before anything is written; with `correct`,
    what it would correct as well, each with a heavy border and a corrected
    connection as a heavy line. `source` is what `adopt` takes."""
    from pathlib import Path as _Path

    from .join import change_picture

    doc, name = _sketch_and_name(source, root)
    return change_picture(doc, _Path(root), owner=owner, source_name=name, date=date, correct=correct)


def export_changes(root: Any, since: str, out: Any, until: str = None):
    """What changed in the repository at `root` from the git revision
    `since` (to `until`, or to the working tree) as one workbook at `out`:
    what was added, removed and changed field by field, the relation rows,
    the views, the shapes and the parts, a sheet each; the path written.
    `DiffError` when the revision is not one."""
    from pathlib import Path as _Path

    from .diff import between
    from .render_excel import export_changes as _export

    return _export(between(_Path(root), since, until), _Path(out))


def since(root: Any, revision: str, until: str = None, *, view: str = None, date: str = ""):
    """What changed in the repository at `root` since the git `revision`
    (to `until`, or to the working tree), as a picture (`terrane.quick.Drawing`):
    added in full, removed dashed in red, changed with a heavy border or a
    heavy line, and what is there unchanged one hop away, faded. `view`
    puts the marks on a
    view of the whole estate (`application-landscape`) instead of the
    change-scoped drawing. `DiffError` when nothing changed."""
    from pathlib import Path as _Path

    from .diff_picture import changes_since

    return changes_since(_Path(root), revision, until, view_id=view, date=date)


def _sketch_and_name(source: Any, root: Any = None):
    """The sketch `adopt` and `change` are handed, read as `diagrams` reads
    it, and a name for it; a file is read for the estate at `root`, whose
    own connection kinds then count."""
    from pathlib import Path as _Path

    from .loader import ModelFileError, parse_data_text
    from .mermaid_import import ReadError
    from .quick import READERS, QuickError, check_sketch, read_any

    if isinstance(source, dict):
        # Named as the sketch names itself, so the picture of the change
        # says "What Merchant onboarding adds" and not "What a sketch adds".
        name = str(((source.get("model") or {}) if isinstance(source.get("model"), dict) else {}).get("name") or "")
        return check_sketch(source), name or "a sketch"
    if isinstance(source, (str, _Path)) and ("\n" not in str(source)) and (
            str(source).lower().endswith((".yaml", ".yml") + tuple(READERS)) or "/" in str(source)
            or "\\" in str(source)):
        path = _Path(source)
        try:
            doc, _notes = read_any(path, _Path(root) if root is not None else None)
        except ReadError as exc:
            raise QuickError("%s: %s" % (path.name, exc)) from exc
        return doc, path.name
    if isinstance(source, str):
        try:
            return check_sketch(parse_data_text(source, "the sketch")), "a sketch"
        except ModelFileError as exc:
            raise QuickError(str(exc)) from exc
    raise TypeError("takes a sketch as a dict, the YAML text of one, or a path; got %s" % type(source).__name__)


def adopt(source: Any, root: Any, *, owner: str = None, dry_run: bool = False, correct: bool = False):
    """Write a sketch into the repository at `root` as its own records
    (`terrane.join.Adoption` says what was added, what was already there and
    what validate says after). `source` is what `diagrams` takes: a sketch
    as a dict, as YAML text or as a path, or the path of an ArchiMate,
    Structurizr, C4-PlantUML, draw.io, Visio, spreadsheet, Mermaid or
    Markdown file, read by its suffix. `owner` names the org unit of the estate that owns what the
    sketch left without one; without it the sketch's placeholder owner is
    adopted too, and said. Nothing already in the estate is touched unless
    `correct`, when a record already there takes the source's differing
    cells, written into its own file with the file otherwise left as it
    is, so a reviewer's workbook comes back as corrections; a blank cell
    is left alone, and a correction to what a shape made goes under the
    product's overrides."""
    from pathlib import Path as _Path

    from .join import join_estate
    from .loader import ModelFileError, parse_data_text
    from .mermaid_import import ReadError
    from .quick import READERS, QuickError, check_sketch, read_any

    notes: list = []
    name = "a sketch"
    if isinstance(source, dict):
        doc = check_sketch(source)
    elif isinstance(source, (str, _Path)) and ("\n" not in str(source)) and (
            str(source).lower().endswith((".yaml", ".yml") + tuple(READERS)) or "/" in str(source)
            or "\\" in str(source)):
        path = _Path(source)
        name = path.name
        try:
            doc, notes = read_any(path, _Path(root))
        except ReadError as exc:
            raise QuickError("%s: %s" % (path.name, exc)) from exc
    elif isinstance(source, str):
        try:
            doc = check_sketch(parse_data_text(source, "the sketch"))
        except ModelFileError as exc:
            raise QuickError(str(exc)) from exc
    else:
        raise TypeError("terrane.adopt takes a sketch as a dict, the YAML text of one, or a path; got %s"
                        % type(source).__name__)
    result = join_estate(doc, _Path(root), owner=owner, source_name=name, dry_run=dry_run, correct=correct)
    result.notes[:0] = notes
    return result
