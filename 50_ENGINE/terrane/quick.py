"""One file, drawn: the quick door into the diagrams.

Everything else here wants a repository: a model in its folders, the views
beside it, the library under them. That is right for an estate and wrong
for the first ten minutes with the tool, or for the picture an architect
wants of nine things for a review on Thursday. `terrane draw sketch.yaml` takes
one file holding a small model and the views it wants and draws them, the
way Mermaid takes one block of text, except that the text is a model: the
things, what they are, and the lines between them, in the method's own
vocabulary, and the pictures are queries over it, the shipped views by
name or a view written in the file.

Nothing is drawn differently for being quick. The file is laid out as a
repository in a scratch folder the loader already understands, with the
shipped library beside it, and loaded, resolved and painted by the same
code as the estate. What is quick is what the file may leave out: a status
defaults to Active, a name to the id, an owner to one org unit made for the
sketch, a criticality to Medium, an interface's name to its ends; so a
sketch is a list of ids and the lines between them, and the rest is there
when it is wanted.

The presets come through the same door. A product in a sketch may sit on a
shipped shape (`archetype:`) or be assembled from the library's kits and
parts (`compose:`), exactly as in a repository, and the shipped landing
zones stand in for the shared services a shape binds when the sketch names
no technology services of its own; what the shape or the parts ask for and
the sketch does not answer is answered from the record where it can be and
with a placeholder that names the parameter where it cannot, and said.
`terrane draw --library` lists what there is to name.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from . import validate as validate_module
from .archetype import ArchetypeError, LANDING_ZONE_TAG, load_archetypes
from .blocks import load_components
from .compose import COMPOSE_KEY, inline_shape
from .draw import Undrawable, drawing_mode, render_sequence_svg, render_svg, render_timeline_svg
from .draw.table import render_table_svg
from .icons import IconMap, web_dir
from .loader import load_folder, read_data_file
from .model import ModelError, load
from .modules import load_modules, members_of
from .palette import Palette
from .payload import graph_payload
from .estate import views_of
from .query import ViewError, bind, load_views, resolve
from .render_mermaid import render as render_mermaid
from .render_mermaid import render_timeline
from .render_sequence import all_flows
from .render_sequence import render as render_sequence_mermaid
from .schema import ENTITY_TYPES
from .shipped import example_path, landing_zones_dir
from .shipped import shipped_root as _shipped_root
from .sketch import yaml_text

#: The folders a model's library is read from, copied beside a sketch so a
#: shape or a kit in it resolves the way it does in the repository.
LIBRARY_FOLDERS = ("20_ARCHETYPES", "24_CONNECTIONS", "25_COMPONENTS", "26_BLOCKS", "27_PATTERNS", "28_MODULES",
                   "29_TYPES")
#: What a sketch may say at the top level besides the entity types.
DOCUMENT_KEYS = {"model", "views", "relations", "landing_zone"}
#: The views a sketch gets when it names none: who touches what, and what
#: there is.
DEFAULT_VIEWS = ("system-context", "application-landscape")
#: The org unit a sketch's things belong to when it names none.
SKETCH_ORG = "ORG-SKETCH"
#: The example beside the engine, which `terrane draw --example` prints.
EXAMPLE = example_path()


class QuickError(ValueError):
    pass


def shipped_root() -> Path:
    """Where the shipped views and library are: the repository the engine
    sits in, else the copies inside the installed package."""
    return _shipped_root()


def check_sketch(data: Any, where: str = "the sketch") -> dict:
    """The sketch document, refused by name for a key it does not take."""
    if not isinstance(data, dict):
        raise QuickError("%s: a sketch is a mapping of entity types, relations and views" % where)
    unknown = sorted(k for k in data if k not in DOCUMENT_KEYS and k not in ENTITY_TYPES)
    if unknown:
        raise QuickError("%s: does not take %s; it takes model, views, relations and the entity types (%s)" % (
            where, ", ".join(unknown), ", ".join(sorted(ENTITY_TYPES))))
    return data


def read_sketch(path: Path) -> dict:
    return check_sketch(read_data_file(Path(path)), str(path))


def fill_defaults(doc: dict) -> Tuple[Dict[str, List[dict]], List[str]]:
    """The sketch's records with what a drawing needs and the file left
    out, and a note for each thing filled in, so nothing is silent."""
    entities: Dict[str, List[dict]] = {}
    notes: List[str] = []
    for type_name, entity_type in ENTITY_TYPES.items():
        raw = doc.get(type_name)
        if raw is None:
            continue
        if not isinstance(raw, list):
            raise QuickError("%s: a list of records, one per thing" % type_name)
        records = []
        for i, record in enumerate(raw):
            if isinstance(record, str):
                # A bare id is the smallest sketch of a thing.
                record = {entity_type.pk: record}
            if not isinstance(record, dict):
                raise QuickError("%s[%d]: a record is a mapping" % (type_name, i))
            record = dict(record)
            if not record.get(entity_type.pk):
                raise QuickError("%s[%d]: needs %s" % (type_name, i, entity_type.pk))
            records.append(record)
        entities[type_name] = records
    fields_of = {name: {f.name for f in et.fields} for name, et in ENTITY_TYPES.items()}
    needs_owner = [name for name, et in ENTITY_TYPES.items()
                   if any(f.name == "owner_org_id" and f.required for f in et.fields)]
    owners_missing = any(
        not record.get("owner_org_id") for name in needs_owner for record in entities.get(name, []))
    if owners_missing and not entities.get("org_units"):
        model_name = str((doc.get("model") or {}).get("name") or "the sketch")
        entities["org_units"] = [{"org_unit_id": SKETCH_ORG, "name": "Owner of %s" % model_name, "status": "Active"}]
        notes.append("no org unit named; %s stands for the owner" % SKETCH_ORG)
    default_owner = entities["org_units"][0]["org_unit_id"] if entities.get("org_units") else None
    filled = 0
    for type_name, records in entities.items():
        fields = fields_of[type_name]
        pk = ENTITY_TYPES[type_name].pk
        for record in records:
            if "name" in fields and not record.get("name"):
                record["name"] = str(record[pk])
                filled += 1
            if "status" in fields and not record.get("status"):
                record["status"] = "Active"
                filled += 1
            if "owner_org_id" in fields and not record.get("owner_org_id") and default_owner \
                    and type_name in needs_owner:
                record["owner_org_id"] = default_owner
                filled += 1
            if type_name == "systems" and not record.get("criticality"):
                record["criticality"] = "Medium"
                filled += 1
            if type_name == "interfaces" and record.get("name") == str(record[pk]) and record.get("source_system_id"):
                record["name"] = "%s to %s" % (record.get("source_system_id"), record.get("target_system_id"))
    if filled:
        notes.append("%d field(s) the sketch left out were filled with defaults" % filled)
    return entities, notes


def _shipped_answers(shipped: Path) -> Dict[str, Any]:
    """The shipped sample's answers to what the library asks an estate,
    from its `model.yaml`; none when it says none."""
    from .answers import estate_answers
    from .loader import read_data_file

    try:
        config = read_data_file(Path(shipped) / "10_MODEL" / "model.yaml") or {}
    except (OSError, ValueError):
        return {}
    return estate_answers(config) if isinstance(config, dict) else {}


def materialize(doc: dict, root: Path, shipped: Optional[Path] = None) -> Tuple[List[str], List[str]]:
    """Lay the sketch out as a repository under `root`, the shipped library
    beside it, and return the ids of the views to draw, in the sketch's
    order, with the notes: every default filled, every answer given."""
    shipped = shipped or shipped_root()
    doc, zone_notes = _own_zone(doc, shipped)
    entities, notes = fill_defaults(doc)
    notes.extend(zone_notes)
    model_dir = root / "10_MODEL"
    model_dir.mkdir(parents=True, exist_ok=True)
    config = dict(doc.get("model") or {})
    config.setdefault("name", "Sketch")
    # What the library asks an estate (who stewards the data, where a
    # vendor's audit trail goes), answered as the shipped sample answers it,
    # as its landing zones stand in for the sketch's; anything the sketch
    # says under `model: answers` wins. Without it a sketch with a datastore
    # part would not load.
    answers = dict(_shipped_answers(shipped))
    answers.update((config.get("answers") or {}) if isinstance(config.get("answers"), dict) else {})
    if answers:
        config["answers"] = answers
    (model_dir / "model.yaml").write_text(yaml_text(config), encoding="utf-8")
    for type_name, records in entities.items():
        folder = model_dir / ENTITY_TYPES[type_name].folder
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ("%s.yaml" % type_name)).write_text(yaml_text(records), encoding="utf-8")
    relations = doc.get("relations") or {}
    if relations:
        if not isinstance(relations, dict):
            raise QuickError("relations: a mapping of relation name to rows")
        (model_dir / "relations").mkdir(parents=True, exist_ok=True)
        (model_dir / "relations" / "sketch.yaml").write_text(yaml_text(relations), encoding="utf-8")
    for folder in LIBRARY_FOLDERS:
        source = shipped / folder
        if source.is_dir():
            shutil.copytree(source, root / folder, ignore=shutil.ignore_patterns("__pycache__"))
    notes.extend(_presets(entities, root, shipped))
    views_dir = root / "30_VIEWS"
    views_dir.mkdir(parents=True, exist_ok=True)
    wanted: List[str] = []
    asked = doc.get("views")
    if asked is None:
        asked = list(DEFAULT_VIEWS)
    if not isinstance(asked, list):
        raise QuickError("views: a list of shipped view ids, or views written out")
    for i, item in enumerate(asked):
        if isinstance(item, str):
            source = shipped / "30_VIEWS" / ("%s.view.yaml" % item)
            if not source.is_file():
                shipped_ids = sorted(p.name[:-len(".view.yaml")] for p in (shipped / "30_VIEWS").glob("*.view.yaml"))
                raise QuickError("views[%d]: no shipped view called %r; the shipped views are %s" % (
                    i, item, ", ".join(shipped_ids)))
            shutil.copy(source, views_dir / source.name)
            wanted.append(item)
        elif isinstance(item, dict) and item.get("use"):
            # A shipped view with a subject: `use: product-architecture`
            # and `with: {product: PRD-X}`.
            source = shipped / "30_VIEWS" / ("%s.view.yaml" % item["use"])
            if not source.is_file():
                raise QuickError("views[%d]: no shipped view called %r" % (i, item["use"]))
            shutil.copy(source, views_dir / source.name)
            wanted.append("%s|%s" % (item["use"], yaml_text(dict(item.get("with") or {})).strip()))
        elif isinstance(item, dict) and item.get("view_id"):
            (views_dir / ("%s.view.yaml" % item["view_id"])).write_text(yaml_text(item), encoding="utf-8")
            wanted.append(str(item["view_id"]))
        else:
            raise QuickError("views[%d]: a shipped view's id, `use:` with `with:`, or a view with a view_id" % i)
    return wanted, notes


#: Parameters a sketch is not answered for: they take a list, and a
#: placeholder string would be read as one item named after the parameter.
_UNANSWERED = {"spokes", "roles", "subscribers"}


def _landing_zone(shipped: Path) -> List[dict]:
    """The shipped landing zones: the platform services tagged
    `landing-zone` in the model beside the engine, or the copies inside the
    package, in id order."""
    folder = landing_zones_dir(shipped)
    if not folder.is_dir():
        return []
    out = []
    for _path, record in load_folder(folder):
        if not isinstance(record, dict):
            continue
        tags = record.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        if LANDING_ZONE_TAG in tags:
            out.append(dict(record))
    return sorted(out, key=lambda r: str(r.get("tech_service_id") or ""))


def _own_zone(doc: dict, shipped: Path) -> Tuple[dict, List[str]]:
    """The sketch's own landing zone, said in a few words, as the technology
    services it stands for:

        landing_zone:
          provider: AWS
          services:
            message-queue: Amazon MQ
            api-gateway: Amazon API Gateway

    or a list of those, one per provider. Each named service becomes a
    technology service of that kind tagged `landing-zone`, which is what a
    shape binds its shared services to; a kind the library does not know
    is refused with the kinds it does. The document comes back copied,
    with the services among its `tech_services`, so a dict handed to
    `terrane.diagrams` is not written into."""
    spec = doc.get("landing_zone")
    if spec is None:
        return doc, []
    specs = spec if isinstance(spec, list) else [spec]
    kinds = sorted(load_components(shipped))
    records: List[dict] = []
    notes: List[str] = []
    for i, item in enumerate(specs):
        if not isinstance(item, dict) or not item.get("provider") or not isinstance(item.get("services"), dict):
            raise QuickError("landing_zone[%d]: a provider and the services by kind, like "
                             "{provider: AWS, services: {message-queue: Amazon MQ}}" % i)
        provider = str(item["provider"])
        for kind, name in item["services"].items():
            if str(kind) not in kinds:
                raise QuickError("landing_zone: %r is not a kind the library knows; the kinds are %s" % (
                    kind, ", ".join(kinds)))
            ident = re.sub(r"[^A-Z0-9]+", "-", ("%s %s" % (provider, name)).upper()).strip("-")
            records.append({"tech_service_id": "TS-%s" % ident, "name": str(name), "status": "Active",
                            "provider": provider, "cloud_provider": provider, "component_type": str(kind),
                            "tags": [LANDING_ZONE_TAG]})
        notes.append("landing zone on %s: %d service(s) from the sketch" % (provider, len(item["services"])))
    out = dict(doc)
    out["tech_services"] = list(doc.get("tech_services") or []) + records
    return out, notes


def _presets(entities: Dict[str, List[dict]], root: Path, shipped: Path) -> List[str]:
    """A product on a shipped shape, or assembled from the library's parts,
    needs two things a sketch may leave out: a landing zone, for the shared
    services the shape binds (the message bus, the gateway, the vault), and
    an answer to every parameter the shape or the parts ask for. The
    shipped landing zones stand in for the first when the sketch names no
    technology services; the second is answered from the record where it
    can be (the owner, the name, a slug from the id, the domain) and with a
    placeholder that names the parameter where it cannot. Every answer is
    said, so the person knows what to write to choose. Runs after the
    entity files and the library are on disk, since a composed shape is
    worked out by the same code that will load it."""
    notes: List[str] = []
    presets = [(type_name, record) for type_name, records in entities.items() for record in records
               if record.get("archetype") or record.get(COMPOSE_KEY)]
    if not presets:
        return notes
    owner = str(entities["org_units"][0]["org_unit_id"]) if entities.get("org_units") else SKETCH_ORG
    model_dir = root / "10_MODEL"
    # The kinds the sketch's own landing zone answers, per provider; the
    # shipped zones stand in for every other kind, so a sketch that names
    # its message bus and nothing else still binds its gateway and vault.
    covered = set()
    own_ids = set()
    for record in entities.get("tech_services", []):
        own_ids.add(str(record.get("tech_service_id") or ""))
        tags = _words(record.get("tags"))
        if LANDING_ZONE_TAG in tags:
            # Every kind the service answers counts, not its first alone:
            # a workbook of the estate's own pictures brought Key Vault
            # back saying secrets and keys, and the shipped copy came in
            # again for the keys under the same id.
            provider = str(record.get("cloud_provider") or "")
            kinds = [str(record.get("component_type") or "")] + _words(record.get("answers_for"))
            covered.update((provider, kind) for kind in kinds if kind)
    zone = []
    for record in _landing_zone(shipped):
        if str(record.get("tech_service_id") or "") in own_ids:
            continue  # the sketch holds this very service, by its id
        provider = str(record.get("cloud_provider") or "")
        kinds = [str(record.get("component_type") or "")] + [str(k) for k in (record.get("answers_for") or []) if k]
        left = [k for k in kinds if k and (provider, k) not in covered]
        if not left:
            continue
        if left != kinds:
            # The sketch answered one of this service's kinds itself; the
            # service stays for the others (Key Vault holds the keys as
            # well as the secrets), and not as a second answer for that one.
            record = dict(record)
            record["component_type"] = left[0]
            if len(left) > 1:
                record["answers_for"] = left[1:]
            else:
                record.pop("answers_for", None)
        zone.append(record)
    if zone:
        for record in zone:
            # Their owner is an org unit of the estate they came from.
            record["owner_org_id"] = owner
        folder = model_dir / ENTITY_TYPES["tech_services"].folder
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "landing-zones.yaml").write_text(yaml_text(zone), encoding="utf-8")
        providers = sorted({str(r.get("cloud_provider") or "") for r in zone} - {""})
        if covered:
            notes.append("the sketch's landing zone answers %d kind(s); the shipped landing zones stand in for the rest "
                         "(%d platform services on %s)" % (len(covered), len(zone), ", ".join(providers)))
        else:
            notes.append("no landing zone named; the shipped landing zones stand in (%d platform services on %s)" % (
                len(zone), ", ".join(providers)))
    touched, answered = answer_parameters(entities, root, owner)
    notes.extend(answered)
    for type_name in touched:
        folder = model_dir / ENTITY_TYPES[type_name].folder
        (folder / ("%s.yaml" % type_name)).write_text(yaml_text(entities[type_name]), encoding="utf-8")
    # The org units a shape or its parts name and the sketch does not
    # hold, stood in as placeholders so the sketch draws clean: a part's
    # data asset names the sample estate's data engineering as its
    # steward, and two of the three files shipped as examples drew with
    # "ERROR ref.dangling" in their notes. Worked out on the loaded sketch,
    # since a composed shape's records exist once it is expanded; the
    # sketch's own records are left to say their own mistakes.
    try:
        model = load(root)
    except ModelError:
        return notes  # the loader says what is wrong, by name, when the sketch is loaded
    held = {str(r.get("org_unit_id") or "") for r in entities.get("org_units", [])}
    named: List[str] = []
    for type_name in ENTITY_TYPES:
        for record in model.all_of(type_name):
            if not record.get("archetype_instance"):
                continue
            for key, value in record.items():
                if str(key).endswith("_org_id") and isinstance(value, str) and value and value not in held \
                        and value not in named:
                    named.append(value)
    if named:
        orgs = list(entities.get("org_units") or [])
        orgs.extend({"org_unit_id": org_id, "name": "%s, as the library names it" % org_id, "status": "Active"}
                    for org_id in named)
        entities["org_units"] = orgs
        folder = model_dir / ENTITY_TYPES["org_units"].folder
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "org_units.yaml").write_text(yaml_text(orgs), encoding="utf-8")
        notes.append("%s named by what the shape made and not in the sketch; stand%s in as org unit%s, which the "
                     "estate this is adopted into has to hold" % (", ".join(named), "s" if len(named) == 1 else "",
                                                                    "" if len(named) == 1 else "s"))
    return notes


def answer_parameters(entities: Dict[str, List[dict]], root: Path, owner: str) -> Tuple[set, List[str]]:
    """Every parameter a product's shape or parts ask for and the sketch
    did not answer, answered from the record (`_answer`) and written
    under the record's `parameters`: the types touched, and a note per
    product saying what was answered. The drawing calls it for the scratch
    sketch and the adopter for the record it writes, since a product
    adopted without the answers made the estate fail to load after."""
    notes: List[str] = []
    touched: set = set()
    presets = [(type_name, record) for type_name, records in entities.items() for record in records
               if record.get("archetype") or record.get(COMPOSE_KEY)]
    if not presets:
        return touched, notes
    try:
        archetypes = load_archetypes(root)
    except ArchetypeError:
        return touched, notes  # the loader says what is wrong with the library, by name
    systems = sorted(str(r[ENTITY_TYPES["systems"].pk]) for r in entities.get("systems", []))
    for type_name, record in presets:
        pk = ENTITY_TYPES[type_name].pk
        try:
            if record.get(COMPOSE_KEY):
                shape = inline_shape(root, record, type_name, archetypes.values())
            else:
                shape = archetypes.get(str(record.get("archetype")))
        except ValueError:
            continue  # refused by the loader, by name, when the sketch is loaded
        if shape is None:
            continue
        given = dict(record.get("parameters") or {})
        answers: Dict[str, Any] = {}
        for parameter in shape.parameters:
            if parameter.name in given or parameter.name in _UNANSWERED:
                continue
            if not parameter.required or parameter.default is not None:
                continue
            answers[parameter.name] = _answer(parameter.name, record, pk, owner, systems)
        if answers:
            given.update(answers)
            record["parameters"] = given
            touched.add(type_name)
            notes.append("%s: %s asked for what the sketch did not say; answered %s; write them under parameters "
                         "to choose" % (record[pk], "the parts" if record.get(COMPOSE_KEY) else "the shape",
                                        ", ".join("%s=%s" % (k, v) for k, v in answers.items())))
    return touched, notes


def _answer(name: str, record: dict, pk: str, owner: str, systems: Sequence[str]) -> str:
    """What a sketch says for a parameter it did not: the record's own
    field where one answers it, a system of the sketch for a system, and a
    placeholder that names the parameter otherwise, which is obviously one
    in the picture, and that is the point."""
    identity = str(record[pk])
    if name == "owner_org":
        return str(record.get("owner_org_id") or owner)
    if name == "product_name":
        return str(record.get("name") or identity)
    if name == "slug":
        _prefix, _, rest = identity.partition("-")
        return re.sub(r"[^a-z0-9]+", "-", (rest or identity).lower()).strip("-") or "sketch"
    if name == "domain":
        return str(record.get("company_domain") or "Sketch")
    if name.endswith("_system") and systems:
        return systems[0]
    return "sketch-" + name


def _words(value) -> List[str]:
    """A list field as the list it is, whether written as one or as the
    `;` or `,` string a spreadsheet cell holds."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [t.strip() for t in str(value).replace(";", ",").split(",") if t.strip()]


def _subject_of(spec: str) -> Tuple[str, Dict[str, str]]:
    view_id, _, rest = spec.partition("|")
    values: Dict[str, str] = {}
    for line in rest.splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            values[key.strip()] = value.strip().strip('"')
    return view_id, values


class Drawing(NamedTuple):
    """One picture of a sketch: the SVG, and the Mermaid when it was asked
    for. Shows itself in a notebook and saves itself to a file."""
    #: The view id with its subject (`product-architecture--PRD-X`), or the
    #: flow id; what the file is named after.
    name: str
    #: diagram, map, timeline or flow.
    kind: str
    svg: str
    mermaid: Optional[str] = None
    #: What the sheet says at the top: the view's title with its subject in
    #: it, or the flow's name; what a slide is headed with.
    title: str = ""
    #: The drawing as shapes (`terrane.draw.svg.Scene`) for a diagram, so the
    #: editable deck draws it without laying it out again; None otherwise.
    scene: Optional[object] = None
    #: The view as C4-PlantUML (`terrane.render_plantuml`), for a diagram or a
    #: map; None for a report, a timeline or a flow.
    plantuml: Optional[str] = None

    def _repr_svg_(self) -> str:
        return self.svg

    def png(self, scale: float = 2.0) -> bytes:
        """The picture as PNG bytes, `scale` device pixels per CSS pixel,
        through a browser on the machine or resvg-py (`terrane.draw.raster`).
        Opens and closes the browser each time; a folder of pictures goes
        through `Drawings.save(..., png=True)`, which opens it once."""
        from .draw.raster import open_rasterizer

        with open_rasterizer(scale=scale) as shoot:
            return shoot(self.svg)

    def save(self, path) -> Path:
        """The picture written to `path`: the SVG, or a PNG when the path
        ends in `.png`."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".png":
            path.write_bytes(self.png())
        else:
            path.write_text(self.svg, encoding="utf-8")
        return path


class Drawings(Dict[str, Drawing]):
    """The pictures of one sketch by name, with the notes worth reading:
    what was filled in, what was answered, what could not be drawn and
    why."""

    def __init__(self, drawings=(), notes: Sequence[str] = ()) -> None:
        super().__init__(drawings)
        self.notes: List[str] = list(notes)
        #: The sketch the pictures were drawn from, when they were drawn
        #: from one, so what the drawing said can be written out again.
        self.sketch: Optional[dict] = None
        #: What the pictures show (`terrane.shown.Shown`), when they were drawn
        #: from a repository, so the records on them can be written out.
        self.shown = None
        #: What the shapes and parts made, by the product they made it for:
        #: each record's type, id, name and part (`made_by`), so a part's
        #: system is known by id once the picture is drawn.
        self.made: Dict[str, List[dict]] = {}

    def excel(self, path) -> Path:
        """What the pictures say, as an Excel workbook at `path`: for a
        sketch, its own records, a sheet per type, its own columns, the
        relations on a sheet of their own, the pages on a `views` sheet,
        and nothing the quick door filled in to draw it; for a repository,
        the records on the pictures, the connections the model has among
        them and a page per picture (`terrane.shown`), so a reviewer's
        corrections come back as the same pages. The estate whole is `terrane
        export excel`."""
        from .render_excel import sketch_sheets, workbook_bytes

        root = None
        if self.sketch is not None:
            doc = self.sketch
        elif self.shown is not None:
            doc = self.shown.sketch()
            # The estate's own connection kinds name the lines on its
            # pictures: a health system's HL7 feeds are no kind the
            # shipped catalog knows.
            root = self.shown.model.root
            self.notes.extend(n for n in self.shown.notes if n not in self.notes)
        else:
            raise QuickError("these pictures hold no records to write")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # What is not a cell is said among the notes the command prints.
        path.write_bytes(workbook_bytes(sketch_sheets(doc, self.notes, root)))
        return path

    def save(self, folder, stem: str, *, rasterize=None, png: bool = False, plantuml: bool = False) -> List[Path]:
        """Every picture under `folder` as `<stem>--<name>.svg`, a PNG
        beside it through `rasterize` when given (or through what the
        machine has, opened once for all of them, when `png` is asked), the
        Mermaid beside it when it was drawn, the C4-PlantUML beside it when
        `plantuml` is asked; the files written, in that order."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        opened = None
        if png and rasterize is None:
            from .draw.raster import open_rasterizer

            opened = rasterize = open_rasterizer()
        written: List[Path] = []
        try:
            for drawing in self.values():
                target = folder / ("%s--%s.svg" % (stem, drawing.name))
                written.append(drawing.save(target))
                if rasterize:
                    image = target.with_suffix(".png")
                    image.write_bytes(rasterize(drawing.svg))
                    written.append(image)
                if drawing.mermaid is not None:
                    mmd = target.with_suffix(".mmd")
                    mmd.write_text(drawing.mermaid, encoding="utf-8")
                    written.append(mmd)
                if plantuml and drawing.plantuml is not None:
                    puml = target.with_suffix(".puml")
                    puml.write_text(drawing.plantuml, encoding="utf-8")
                    written.append(puml)
        finally:
            if opened is not None:
                opened.close()
        return written

    def _repr_html_(self) -> str:
        """Every picture, each under its name, for a notebook cell that
        shows the whole result rather than one drawing of it."""
        parts = []
        for name, drawing in self.items():
            parts.append("<h3>%s</h3>\n%s" % (drawing.title or name, drawing.svg))
        if self.notes:
            parts.append("<ul>%s</ul>" % "".join("<li>%s</li>" % note.replace("<", "&lt;") for note in self.notes))
        return "\n".join(parts)

    def pack(self, path, *, title: str = "Architecture sketch", date: str = "", editable: bool = False) -> Path:
        """Every picture as a slide of a deck at `path`, a cover before them
        with `title` on it; the same deck `terrane pack` writes for a repository,
        for the pictures of one sketch. Needs a browser or resvg-py, as a
        PNG does, unless `editable`: then every diagram goes on as shapes a
        reviewer can move, glued by its connectors, and only a flow, a map
        or a timeline still wants a picture."""
        from .pack import pack_drawings

        return pack_drawings(self, Path(path), title, date=date, editable=editable)[0]

    def drawio(self, path) -> Path:
        """Every diagram as a page of one draw.io file at `path`, each box
        where the engine put it, in its shape and colors, the lines through
        their bends, the styles the reader takes back to their types; a
        flow, a timeline or a report has no page. Needs no browser."""
        from .render_drawio import kinds_by_interface, marks_for, render_drawio

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pages = [(name, drawing.title or name, drawing.scene) for name, drawing in self.items()
                 if drawing.scene is not None]
        # A line of a connection kind says so: the sketch's own interfaces
        # against the shipped kinds, a repository's against its own.
        records: Dict[str, Sequence[dict]] = {}
        rows: Dict[str, Sequence[dict]] = {}
        if self.sketch is not None:
            kinds = kinds_by_interface(self.sketch.get("interfaces") or [])
            records = {t: [r for r in (self.sketch.get(t) or []) if isinstance(r, dict)] for t in ENTITY_TYPES}
            rows = {r: list(v) for r, v in (self.sketch.get("relations") or {}).items() if isinstance(v, list)}
        elif self.shown is not None:
            kinds = kinds_by_interface(self.shown.model.all_of("interfaces"), self.shown.model.root)
            records = {t: self.shown.model.all_of(t) for t in ENTITY_TYPES}
            rows = {r: self.shown.model.relation_rows(r) for r in RELATION_TYPES}
        else:
            kinds = {}
        path.write_text(render_drawio(pages, kinds, marks_for(records, kinds, rows)), encoding="utf-8", newline="\n")
        return path


def _fonts(web: Path):
    """The faces, read from the app's web folder or the package's copy, so
    a picture carries them and looks the same wherever it is opened; None
    for a face that is not there, which the painter leaves out. The
    estate's committed pictures do not carry them, since three hundred
    copies of the same faces would be most of the repository; one picture
    drawn from one file is the case for it."""
    folder = Path(web) / "fonts"

    def read(name: str) -> Optional[bytes]:
        path = folder / name
        return path.read_bytes() if path.is_file() else None

    return read


def what_was_made(model) -> Dict[str, List[dict]]:
    """What the shapes and parts made in a loaded model, by the product
    (or other instance) they made it for: each record's type, id, name
    and the part that made it, in the schema's order of types and by id."""
    out: Dict[str, List[dict]] = {}
    for type_name in ENTITY_TYPES:
        pk = ENTITY_TYPES[type_name].pk
        for record in sorted(model.all_of(type_name), key=lambda r: str(r.get(pk, ""))):
            instance = record.get("archetype_instance")
            if instance:
                out.setdefault(str(instance), []).append({
                    "type": type_name, "id": str(record.get(pk, "")), "name": str(record.get("name") or ""),
                    "part": str(record.get("module") or "")})
    return out


def made_by(doc: dict, shipped: Optional[Path] = None) -> Dict[str, List[dict]]:
    """What the shapes and parts in a sketch make, by the product they make
    it for, before anything is drawn: each record's type, id, name and the
    part that made it, so a sketch can connect a part's system to the rest
    of the estate by id (`terrane.connect`) before the picture exists. The
    sketch is laid out in a scratch folder the way `terrane draw` lays it out;
    nothing is drawn or kept."""
    shipped = shipped or shipped_root()
    with tempfile.TemporaryDirectory(prefix="aac-made-") as tmp:
        root = Path(tmp)
        materialize(doc, root, shipped)
        return what_was_made(load(root))


def render_sketch(doc: dict, *, mermaid: bool = False, date: str = "", shipped: Optional[Path] = None) -> Drawings:
    """Every view the sketch names, and every flow it holds, as a drawing,
    by name: the Python door, which `terrane.diagrams` opens. Nothing is written."""
    shipped = shipped or shipped_root()
    with tempfile.TemporaryDirectory(prefix="aac-sketch-") as tmp:
        root = Path(tmp)
        wanted, notes = materialize(doc, root, shipped)
        drawings = render_root(root, wanted, notes, mermaid=mermaid, date=date,
                               web=web_dir(shipped) or shipped / "web", own_library=False)
        drawings.sketch = doc
        return drawings


def render_repository(root: Path, views: Optional[Sequence[object]] = None, *, mermaid: bool = False,
                      date: str = "") -> Drawings:
    """A repository's pictures from Python, the other thing `terrane.diagrams`
    opens on: the views named (a view id, `{use, with}` for a subject view,
    as a sketch names them, or a view written out with a `view_id`, drawn
    over the estate without a file, so a question of the moment is a
    picture in a notebook) or, named none, every view of the whole estate,
    which is every view that takes no subject, the reports as tables; and
    every flow, as `terrane render` draws them, the faces inside. A view the
    repository does not have is refused with the ones it does; a view
    written out under the id of one it has stands in for it, for this
    call."""
    from .query import ViewError, parse_view

    root = Path(root)
    if not (root / "10_MODEL").is_dir():
        raise QuickError("%s: not a repository; it has no 10_MODEL folder" % root)
    have = {v.view_id: v for v in views_of(root)}
    wanted: List[str] = []
    extra: Dict[str, object] = {}
    if views is None:
        wanted = [v.view_id for v in have.values() if not v.parameters]
    else:
        for i, item in enumerate(views):
            if isinstance(item, str):
                view_id, values = item, {}
            elif isinstance(item, dict) and item.get("use"):
                view_id, values = str(item["use"]), dict(item.get("with") or {})
            elif isinstance(item, dict) and item.get("view_id"):
                try:
                    view = parse_view(dict(item), Path("views[%d]" % i))
                except ViewError as exc:
                    raise QuickError("views[%d]: %s" % (i, exc)) from exc
                extra[view.view_id] = view
                wanted.append(view.view_id)
                continue
            else:
                raise QuickError("views[%d]: a view id, `use:` with `with:` for a subject view, or a view written "
                                 "out with a view_id" % i)
            if view_id not in have:
                raise QuickError("no view called %r in %s; the views are %s" % (view_id, root, ", ".join(sorted(have))))
            wanted.append("%s|%s" % (view_id, yaml_text(values).strip()) if values else view_id)
    shipped = shipped_root()
    web = web_dir(root) or web_dir(shipped) or shipped / "web"
    return render_root(root, wanted, [], mermaid=mermaid, date=date, web=web, extra_views=extra)


def render_root(root: Path, wanted: Sequence[str], notes: List[str], *, mermaid: bool, date: str, web: Path,
                extra_views: Optional[Dict[str, object]] = None, own_library: bool = True) -> Drawings:
    """The pictures of the repository at `root` for the view specs wanted
    (`view`, or `view|with` as `materialize` writes them) and every flow it
    holds, by name; `notes` is carried on and added to; `extra_views` are
    views given from Python rather than from `30_VIEWS`, by id;
    `own_library` is False for a sketch, whose library is the shipped
    copy, so what validate says of that library is not laid at the
    sketch's door. One painter for the sketch and the estate, so neither
    can drift from the other."""
    drawings = Drawings()
    if True:
        model = load(root)
        views = {v.view_id: v for v in views_of(root)}
        views.update(extra_views or {})
        palette = Palette(model.config.get("palette"))
        icons = IconMap(web)
        fonts = _fonts(web)
        components = load_components(root)
        model_name = str(model.config.get("name") or "Sketch")
        # The small diagrams the app hands to ELK are laid out by ELK here
        # too, through the browser on the machine, when there is one.
        from .draw.elk import open_runner

        elk = open_runner(web)
        from .shown import Shown

        shown = Shown(model, model_name)
        drawings.made = what_was_made(model)
        for spec in wanted:
            view_id, values = _subject_of(spec)
            view = views[view_id]
            try:
                if values:
                    view = bind(view, values, model)
                graph = resolve(model, view)
                payload = graph_payload(model, view, palette, icons, components, graph=graph)
            except ViewError as exc:
                notes.append("%s: not drawn: %s" % (view_id, exc))
                continue
            name = "%s%s" % (view_id, "".join("--" + v for v in values.values()))
            collected: list = []
            try:
                if view.kind == "timeline":
                    svg = render_timeline_svg(payload, font_loader=fonts, model_name=model_name, date=date)
                elif view.kind == "report":
                    # The table it always was, drawn on the sheet.
                    svg = render_table_svg(graph, font_loader=fonts, model_name=model_name, date=date)
                else:
                    drawing_mode(payload)
                    svg = render_svg(payload, icon_loader=icons.read, font_loader=fonts, model_name=model_name,
                                     date=date, elk=elk, scene_out=collected)
            except Undrawable as exc:
                notes.append("%s: not drawn: %s" % (view_id, exc))
                continue
            text = None
            if mermaid and view.kind != "report":
                text = render_timeline(graph) if view.kind == "timeline" else render_mermaid(graph, palette, model)
            puml = None
            if view.kind in ("diagram", "map"):
                from .render_plantuml import render_plantuml

                puml = render_plantuml(graph, model, title=view.title, palette=palette, generated_by="terrane draw")
            drawings[name] = Drawing(name, view.kind, svg, text, title=view.title,
                                     scene=collected[0] if collected else None, plantuml=puml)
            shown.view(name, view, graph, values)
            if not graph.nodes:
                notes.append("%s: nothing in the sketch matches this view, so the picture is empty" % view_id)
        for flow_id in all_flows(model):
            svg = render_sequence_svg(model, flow_id, palette, font_loader=fonts, model_name=model_name, date=date)
            flow = model.get("flows", flow_id) or {}
            drawings[flow_id] = Drawing(flow_id, "flow", svg, render_sequence_mermaid(model, flow_id) if mermaid else None,
                                        title=str(flow.get("name") or flow_id))
            shown.flow(flow_id)
        drawings.shown = shown
        for warning in model.warnings:
            notes.append("model: %s" % warning)
        # What the method says of the model behind the pictures: every
        # error by name, since a picture of a model with a dangling
        # reference is a picture of a mistake, and the warnings counted by
        # code, since a sketch has no CMDB ids and does not need telling
        # seventy times.
        report = validate_module.run(model, list(views.values()))
        # A sketch copies the few shipped views it draws and never the
        # levels above them, so a view's `up` naming one is not the sketch's
        # to fix.
        report = validate_module.Report([f for f in report.findings if f.code != "view.up"])
        if not own_library:
            # The shipped library's own findings (a shape binding a service
            # the scratch repository does not carry) are not the sketch's.
            report = validate_module.Report([f for f in report.findings
                                             if not f.code.startswith(("library.", "pattern."))])
        for finding in report.errors:
            notes.append("validate: ERROR %s: %s" % (finding.code, finding.message))
        if report.findings:
            by_code: Dict[str, int] = {}
            for finding in report.warnings:
                by_code[finding.code] = by_code.get(finding.code, 0) + 1
            top = sorted(by_code.items(), key=lambda item: (-item[1], item[0]))[:5]
            notes.append("validate: %d error(s), %d warning(s)%s" % (
                len(report.errors), len(report.warnings),
                " (%s%s)" % (", ".join("%s %d" % (code, n) for code, n in top), ", ..." if len(by_code) > 5 else "")
                if top else ""))
        if elk is not None:
            elk.close()
    drawings.notes = notes
    return drawings


def draw_sketch(path: Path, out_dir: Optional[Path] = None, *, mermaid: bool = False, rasterize=None,
                date: str = "", shipped: Optional[Path] = None, pack: Optional[Path] = None,
                editable: bool = False, drawio: bool = False, plantuml: bool = False,
                excel: bool = False) -> Tuple[List[Path], List[str]]:
    """Draw every view the sketch names, and every flow it holds, as SVG
    beside the file (or under `out_dir`), named `<file>--<view>.svg`; a
    file that is not a sketch (an ArchiMate model, a Structurizr workspace,
    a C4-PlantUML diagram, a draw.io file, a Visio drawing, a spreadsheet
    of systems, a Mermaid diagram or a Markdown file holding some) is read
    as one by its suffix. With `pack`, the
    pictures go into a deck there as well, as shapes a reviewer can move
    when `editable`; with `drawio`, a draw.io file beside them, a page per
    diagram; with `plantuml`, a C4-PlantUML file beside each diagram; with
    `excel`, what the file said as a workbook beside them. Returns the
    files written and the notes worth reading: what was filled in, what
    could not be drawn and why."""
    path = Path(path)
    doc, notes = read_any(path)
    drawings = render_sketch(doc, mermaid=mermaid, date=date, shipped=shipped)
    drawings.notes[:0] = notes
    written = drawings.save(Path(out_dir) if out_dir else path.parent, path.stem, rasterize=rasterize,
                            plantuml=plantuml)
    if pack is not None:
        title = str((doc.get("model") or {}).get("name") or path.stem)
        written.append(drawings.pack(Path(pack), title=title, date=date, editable=editable))
    if drawio:
        written.append(drawings.drawio((Path(out_dir) if out_dir else path.parent) / (path.stem + ".drawio")))
    if excel:
        written.append(drawings.excel((Path(out_dir) if out_dir else path.parent) / (path.stem + ".xlsx")))
    return written, drawings.notes


def example_names() -> List[str]:
    """The sketches beside the engine, by the name `--example` takes."""
    return sorted(p.stem for p in EXAMPLE.parent.glob("*.yaml"))


def example_text(name: str = "payments") -> str:
    """One of the example sketches; refused with the names when there is
    no such example."""
    path = EXAMPLE.parent / ("%s.yaml" % name)
    if not path.is_file():
        raise QuickError("no example called %r; the examples are %s" % (name, ", ".join(example_names())))
    return path.read_text(encoding="utf-8")


def _fields_of(view) -> str:
    """The fields a view reads off the records, which a sketch has to set
    for the picture to have its boundaries and colors: what it groups by,
    what it colors by, what it filters on."""
    fields = [str(f) for f in (view.group_by or [])]
    color = str((view.style or {}).get("color_by") or "")
    if color and color != "type" and color not in fields:
        fields.append(color)
    # A `where` key is a field, or a selector such as `id_in`; only the
    # fields are something a sketch can set, and `status` is filled anyway.
    declared = {f.name for entity_type in ENTITY_TYPES.values() for f in entity_type.fields} - {"status"}
    for clause in (view.scope or {}).get("include") or []:
        for key in (clause.get("where") or {}) if isinstance(clause, dict) else ():
            if key in declared and key not in fields:
                fields.append(str(key))
    return ", ".join(fields) or "-"


def shipped_views_text(shipped: Optional[Path] = None) -> str:
    """The shipped views a sketch may name, one line each: the id, the
    kind, whether it takes a subject, the fields it reads, and what it
    shows."""
    views = load_views((shipped or shipped_root()) / "30_VIEWS")
    row = "%-30s %-9s %-13s %-30s %s"
    lines = [row % ("view", "kind", "subject", "fields", "shows")]
    for view in sorted(views, key=lambda v: (v.kind, v.view_id)):
        subject = ", ".join(p.name for p in (view.parameters or ())) or "-"
        shows = " ".join(str(view.description or view.title).split())
        if len(shows) > 90:
            # Three dots, not the ellipsis character: Windows consoles print
            # that one as a question mark.
            shows = shows[:87].rstrip() + "..."
        lines.append(row % (view.view_id, view.kind, subject, _fields_of(view), shows))
    return "\n".join(lines) + "\n"


def shipped_views(shipped: Optional[Path] = None) -> List[dict]:
    """The shipped views as data, one record each: what `shipped_views_text`
    prints, for a notebook to filter rather than read."""
    views = load_views((shipped or shipped_root()) / "30_VIEWS")
    out: List[dict] = []
    for view in sorted(views, key=lambda v: (v.kind, v.view_id)):
        out.append({
            "view_id": view.view_id, "kind": view.kind, "category": view.category, "title": view.title,
            "description": " ".join(str(view.description or "").split()),
            "subject": [p.name for p in (view.parameters or ())],
            "fields": [f for f in _fields_of(view).split(", ") if f and f != "-"],
        })
    return out


def _asked(parameters) -> List[dict]:
    out = []
    for parameter in parameters:
        if getattr(parameter, "component", ""):
            continue
        out.append({"name": parameter.name, "required": bool(parameter.required and parameter.default is None),
                    "default": parameter.default if isinstance(parameter.default, (str, int, float)) else None})
    return out


def shipped_presets(shipped: Optional[Path] = None) -> dict:
    """The shipped shapes, kits, parts and landing zones as data: what
    `shipped_library_text` prints, for a notebook to pick from."""
    shipped = shipped or shipped_root()
    archetypes = load_archetypes(shipped)
    modules = load_modules(shipped)
    shapes = [{"archetype_id": str(shape.archetype_id), "for": str(shape.applies_to),
               "asks": _asked(shape.parameters)}
              for shape in sorted(archetypes.values(), key=lambda a: str(a.archetype_id))]
    kits = []
    for kit in sorted((m for m in modules.values() if m.is_kit), key=lambda m: (m.category, m.module_id)):
        members = members_of(kit, modules)
        asked = list(kit.parameters)
        for member_id in members:
            asked.extend(p for p in modules[member_id].parameters if p.required and p.default is None)
        seen = set()
        asks = [p for p in _asked(asked) if p["required"] and not (p["name"] in seen or seen.add(p["name"]))]
        kits.append({"module_id": kit.module_id, "category": kit.category, "parts": list(members), "asks": asks})
    parts = [{"module_id": part.module_id, "category": part.category, "requires": list(part.requires),
              "asks": _asked(part.parameters)}
             for part in sorted((m for m in modules.values() if not m.is_kit), key=lambda m: (m.category, m.module_id))]
    zones: Dict[str, Dict[str, str]] = {}
    for record in _landing_zone(shipped):
        provider = str(record.get("cloud_provider") or "shared")
        kinds = [str(record.get("component_type") or "")] + [str(k) for k in (record.get("answers_for") or [])]
        for kind in kinds:
            if kind:
                zones.setdefault(kind, {}).setdefault(provider, str(record.get("name") or record.get("tech_service_id")))
    from .connections import load_connections

    kinds = [{"connection_id": k.connection_id, "name": k.name, "integration_style": k.integration_style,
              "protocols": list(k.protocols), "auth_methods": list(k.auth_methods), "frequency": k.frequency,
              "direction": k.direction, "patterns": list(k.patterns), "proposes": k.defaults()}
             for k in load_connections(shipped).values()]
    return {"shapes": shapes, "kits": kits, "parts": parts, "landing_zones": zones, "connections": kinds}


def connection_of(source: str, target: str, kind: str, *, name: str = "", interface_id: str = "",
                  shipped: Optional[Path] = None, **fields: Any) -> dict:
    """An interface of a connection kind between two systems, as the record
    a sketch takes under `interfaces`: the kind's proposal, its style, first
    protocol and authentication, frequency, direction and patterns, with
    `fields` over them; the kind by its id or its name, refused with the
    kinds when there is none."""
    from .connections import find_kind, load_connections

    kinds = load_connections(shipped or shipped_root())
    found = find_kind(str(kind), kinds)
    if found is None:
        raise QuickError("no connection kind called %r; the kinds are %s" % (
            kind, ", ".join(sorted(kinds)) or "none"))
    a, b = str(source or "").strip(), str(target or "").strip()
    if not a or not b:
        raise QuickError("a connection joins two systems by id")
    record: dict = {"interface_id": interface_id or "INT-%s-%s" % (re.sub(r"^SYS-", "", a.upper()),
                                                                   re.sub(r"^SYS-", "", b.upper())),
                    "source_system_id": a, "target_system_id": b, "name": name or found.name}
    record.update(found.defaults())
    record.update({k: v for k, v in fields.items() if v not in (None, "")})
    return record


def _asks(parameters) -> str:
    """What a shape or a part asks for, required marked `*`, defaults
    given; the kinds of shared service the landing zone answers are left
    out, since the sketch is not asked for those."""
    out = []
    for parameter in parameters:
        if getattr(parameter, "component", ""):
            continue
        if isinstance(parameter.default, (str, int, float)) and str(parameter.default) != "":
            out.append("%s=%s" % (parameter.name, parameter.default))
        else:
            # A list default (the blocks a part runs on) is too long to be a
            # column; the bare name says it is answered unless the sketch says.
            out.append(parameter.name + ("*" if parameter.required and parameter.default is None else ""))
    return ", ".join(out) or "-"


def shipped_library_text(shipped: Optional[Path] = None) -> str:
    """The shipped shapes, kits and parts a sketch may name: a shape on a
    product as `archetype:`, a kit or a part under `compose:` with the
    provider; what each asks for and, for a part, what it requires; the
    landing zone kinds; and the connection kinds an arrow may name, with
    what each proposes."""
    from .connections import load_connections

    shipped = shipped or shipped_root()
    archetypes = load_archetypes(shipped)
    modules = load_modules(shipped)
    lines = ["%-26s %-10s %s" % ("shape", "for", "asks")]
    for shape in sorted(archetypes.values(), key=lambda a: str(a.archetype_id)):
        lines.append("%-26s %-10s %s" % (shape.archetype_id, shape.applies_to, _asks(shape.parameters)))
    lines += ["", "%-26s %-12s %s" % ("kit", "category", "parts, and what they ask")]
    kits = [m for m in modules.values() if m.is_kit]
    for kit in sorted(kits, key=lambda m: (m.category, m.module_id)):
        members = members_of(kit, modules)
        asked = list(kit.parameters)
        for member_id in members:
            asked.extend(p for p in modules[member_id].parameters if p.required and p.default is None)
        seen = set()
        required = [p for p in asked if p.required and p.default is None and not p.component
                    and not (p.name in seen or seen.add(p.name))]
        lines.append("%-26s %-12s %s%s" % (kit.module_id, kit.category, ", ".join(members),
                                           ("; asks " + _asks(required)) if required else ""))
    lines += ["", "%-26s %-12s %-34s %s" % ("part", "category", "requires", "asks")]
    parts = [m for m in modules.values() if not m.is_kit]
    for part in sorted(parts, key=lambda m: (m.category, m.module_id)):
        lines.append("%-26s %-12s %-34s %s" % (part.module_id, part.category, ", ".join(part.requires) or "-",
                                               _asks(part.parameters)))
    # The landing zone: the shared service each provider answers a kind
    # with, which a sketch may name its own for under `landing_zone`.
    zone = _landing_zone(shipped)
    by_kind: Dict[str, Dict[str, str]] = {}
    for record in zone:
        provider = str(record.get("cloud_provider") or "shared")
        kinds = [str(record.get("component_type") or "")] + [str(k) for k in (record.get("answers_for") or [])]
        for kind in kinds:
            if kind:
                by_kind.setdefault(kind, {}).setdefault(provider, str(record.get("name") or record.get("tech_service_id")))
    providers = sorted({p for answers in by_kind.values() for p in answers})
    if by_kind:
        lines += ["", "%-26s %s" % ("landing zone kind", "".join("%-28s" % p for p in providers)),
                  "(a sketch names its own under landing_zone: {provider: AWS, services: {kind: name}})"]
        for kind in sorted(by_kind):
            lines.append("%-26s %s" % (kind, "".join("%-28s" % by_kind[kind].get(p, "-")[:27] for p in providers)))
    # The connection kinds: what an arrow's words may name, and what a new
    # interface of each is proposed with.
    connections = load_connections(shipped)
    if connections:
        lines += ["", "%-26s %-18s %-24s %s" % ("connection kind", "style", "protocols",
                                                 "proposes (protocol, auth, frequency, direction)")]
        for connection in connections.values():
            proposal = connection.defaults()
            lines.append("%-26s %-18s %-24s %s" % (
                connection.connection_id, connection.integration_style, ", ".join(connection.protocols)[:23],
                ", ".join(str(proposal[f]) for f in ("protocol", "auth_method", "frequency", "direction") if f in proposal)))
    return "\n".join(lines) + "\n"


def sketch_from_mermaid_file(path: Path, sketch_path: Optional[Path] = None) -> Tuple[Path, List[str]]:
    """Read a Mermaid diagram as a sketch and write the sketch beside it
    (or at `sketch_path`); the path written and the notes."""
    from .mermaid_import import sketch_from_mermaid

    return _sketch_from_file(path, sketch_path, sketch_from_mermaid, "mermaid")


def sketch_from_structurizr_file(path: Path, sketch_path: Optional[Path] = None) -> Tuple[Path, List[str]]:
    """Read a Structurizr DSL workspace as a sketch and write the sketch
    beside it (or at `sketch_path`); the path written and the notes."""
    from .structurizr_import import sketch_from_structurizr

    return _sketch_from_file(path, sketch_path, sketch_from_structurizr, "structurizr")


def sketch_from_archimate_file(path: Path, sketch_path: Optional[Path] = None) -> Tuple[Path, List[str]]:
    """Read an ArchiMate model, Archi's own file or the exchange format, as
    a sketch and write the sketch beside it (or at `sketch_path`); the
    path written and the notes."""
    from .archimate_import import sketch_from_archimate

    return _sketch_from_file(path, sketch_path, sketch_from_archimate, "archimate")


def sketch_from_plantuml_file(path: Path, sketch_path: Optional[Path] = None) -> Tuple[Path, List[str]]:
    """Read a C4-PlantUML diagram as a sketch and write the sketch beside
    it (or at `sketch_path`); the path written and the notes."""
    from .plantuml_import import sketch_from_plantuml

    return _sketch_from_file(path, sketch_path, sketch_from_plantuml, "plantuml")


def sketch_from_drawio_file(path: Path, sketch_path: Optional[Path] = None) -> Tuple[Path, List[str]]:
    """Read a draw.io file as a sketch and write the sketch beside it (or
    at `sketch_path`); the path written and the notes."""
    from .drawio_import import sketch_from_drawio

    return _sketch_from_file(path, sketch_path, sketch_from_drawio, "drawio")


def sketch_from_inventory_file(path: Path, sketch_path: Optional[Path] = None) -> Tuple[Path, List[str]]:
    """Read a spreadsheet of systems, CSV, tab-separated or an Excel
    workbook by its suffix, as a sketch and write the sketch beside it (or
    at `sketch_path`); the path written and the notes."""
    if Path(path).suffix.lower() in EXCEL_SUFFIXES:
        from .excel_import import sketch_from_excel

        return _sketch_from_file(path, sketch_path, sketch_from_excel, "inventory", binary=True)
    from .inventory_import import sketch_from_inventory

    return _sketch_from_file(path, sketch_path, sketch_from_inventory, "inventory")


def sketch_from_visio_file(path: Path, sketch_path: Optional[Path] = None) -> Tuple[Path, List[str]]:
    """Read a Visio drawing (`.vsdx`) as a sketch and write the sketch
    beside it (or at `sketch_path`); the path written and the notes."""
    from .visio_import import sketch_from_visio

    return _sketch_from_file(path, sketch_path, sketch_from_visio, "visio", binary=True)


#: What a file is read as, by its suffix, when the Python door is handed a
#: path that is not a sketch: the readers behind `terrane draw --from-...`.
READERS = {".archimate": "archimate", ".xml": "archimate", ".dsl": "structurizr", ".mmd": "mermaid",
           ".mermaid": "mermaid", ".md": "mermaid", ".markdown": "mermaid",
           ".puml": "plantuml", ".plantuml": "plantuml", ".iuml": "plantuml", ".pu": "plantuml",
           ".drawio": "drawio", ".dio": "drawio", ".csv": "inventory", ".tsv": "inventory",
           ".vsdx": "visio", ".vsdm": "visio", ".xlsx": "excel", ".xlsm": "excel"}
EXCEL_SUFFIXES = (".xlsx", ".xlsm")
#: The readers handed the file's bytes rather than its text.
BINARY_READERS = ("visio", "excel")


def read_any(path: Path, root: Optional[Path] = None) -> Tuple[dict, List[str]]:
    """The sketch in a file: a sketch as it is, or an ArchiMate model, a
    Structurizr workspace, a C4-PlantUML diagram, a draw.io file, a Visio
    drawing, a spreadsheet of systems (CSV, tab-separated or an Excel
    workbook), a Mermaid diagram or a Markdown file holding some, read as
    one; the document and the reader's notes. `root` is the estate the
    read is for, when there is one: a drawing adopted into an estate with
    connection kinds of its own is read with those kinds, after the
    shipped ones."""
    from .connections import reading_for

    with reading_for(root):
        return _read_any(Path(path))


def _read_any(path: Path) -> Tuple[dict, List[str]]:
    path = Path(path)
    kind = READERS.get(path.suffix.lower())
    if kind is None:
        return read_sketch(path), []
    name = path.stem.replace("-", " ").replace("_", " ")
    if kind == "visio":
        from .visio_import import sketch_from_visio

        return sketch_from_visio(path.read_bytes(), name=name)
    if kind == "excel":
        from .excel_import import sketch_from_excel

        return sketch_from_excel(path.read_bytes(), name=name)
    text = path.read_text(encoding="utf-8")
    if kind == "archimate":
        from .archimate_import import sketch_from_archimate

        return sketch_from_archimate(text, name=name)
    if kind == "structurizr":
        from .structurizr_import import sketch_from_structurizr

        return sketch_from_structurizr(text, name=name)
    if kind == "plantuml":
        from .plantuml_import import sketch_from_plantuml

        return sketch_from_plantuml(text, name=name)
    if kind == "drawio":
        from .drawio_import import sketch_from_drawio

        return sketch_from_drawio(text, name=name)
    if kind == "inventory":
        from .inventory_import import sketch_from_inventory

        return sketch_from_inventory(text, name=name)
    from .mermaid_import import sketch_from_markdown, sketch_from_mermaid

    reader = sketch_from_markdown if path.suffix.lower() in (".md", ".markdown") else sketch_from_mermaid
    return reader(text, name=name)


def _sketch_from_file(path: Path, sketch_path: Optional[Path], reader, flag: str,
                      binary: bool = False) -> Tuple[Path, List[str]]:
    path = Path(path)
    source = path.read_bytes() if binary else path.read_text(encoding="utf-8")
    doc, notes = reader(source, name=path.stem.replace("-", " ").replace("_", " "))
    target = Path(sketch_path) if sketch_path else path.with_suffix(".yaml")
    header = ["Read from %s by `terrane draw --from-%s`. A sketch: correct it, keep it, draw it with" % (path.name, flag),
              "`terrane draw %s`." % target.name]
    target.write_text(yaml_text(doc, header), encoding="utf-8")
    return target, notes
