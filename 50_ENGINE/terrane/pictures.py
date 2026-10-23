"""Pictures of the library's presets: every shape and every kit, drawn.

The catalog read a shape as a list of parts and a kit as a list of members,
and a list of parts is not what anyone asks to see. A shape is a product
waiting to be made; so each is made here, once, from a sample instance --
the same expansion the loader runs for a real product, over a scratch copy
of the model that nothing else sees -- and drawn by the product architecture
view through the same drawing every product gets. A kit has no provider of
its own, so it is assembled the way the Assemble panel assembles it, once
per landing zone that can answer for its parts, and drawn the same way.

The names in the pictures are placeholders on purpose (`sample-slug`,
`Sample Web application`): the picture is about the shape, not about a
product, and a reader should see that at a glance. A shape or a kit that
cannot be made from a sample -- a part whose kind no landing zone answers,
an id the estate already holds -- gets no picture and the reason in the
catalog instead, which beats a picture of something else.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence

from .answers import estate_answers
from .archetype import Archetype, ArchetypeError, expand, landing_providers, landing_zone_index
from .blocks import LibraryError
from .compose import ComposeError, inline_shape
from .draw import Undrawable, drawing_mode, render_svg
from .model import Model, ModelError
from .modules import Module, ModuleError
from .palette import Palette
from .payload import edge_style, graph_payload
from .query import View, ViewError, bind
from .schema import ENTITY_TYPES

#: The view every picture is drawn by: one product, its parts, what they
#: run on and reach.
PICTURE_VIEW = "product-architecture"

#: The vocabulary a kit is asked for when it is assembled for its picture:
#: every required answer, given as a placeholder that says it is one.
_REQUIRED_ANSWERS = ("slug", "product_name", "owner_org", "domain", "account", "vendor", "caller_system")


class Pictures(NamedTuple):
    #: Shape id to the picture's path relative to the library folder.
    shapes: Dict[str, str]
    #: Kit id to provider to path, in the providers' order.
    kits: Dict[str, Dict[str, str]]
    #: Shape or kit id to why it has no picture (or none on a provider,
    #: keyed `kit|Provider`).
    notes: Dict[str, str]
    written: List[Path]
    #: Block id to its picture: the components and the connections between.
    blocks: Dict[str, str] = {}
    #: The maps of the library: "kits" (the kits and the parts they are made
    #: of) and "parts" (the parts, what they require, the blocks they run
    #: on), each to its path.
    maps: Dict[str, str] = {}
    #: Part id to its picture: the part with what it requires, assembled on
    #: the first landing zone.
    parts: Dict[str, str] = {}


def sample_instance(archetype: Archetype) -> dict:
    """A stand-in instance, so the shape can be made without a product.
    Required parameters with no default get a placeholder that names them,
    which is obviously one in the output, and that is the point."""
    entity_type = ENTITY_TYPES[archetype.applies_to]
    parameters = {}
    for param in archetype.parameters:
        if param.default is not None:
            parameters[param.name] = param.default
        elif param.required:
            parameters[param.name] = "sample-" + param.name
    return {
        entity_type.pk: "SAMPLE-" + str(archetype.archetype_id).upper(),
        "name": "Sample %s" % archetype.title,
        "status": "Planned",
        "archetype": archetype.archetype_id,
        "parameters": parameters,
    }


_TOKEN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(?:\|[^}]*)?\}")


def _sample_entries(module: Module, parameter: str) -> Optional[list]:
    """A list parameter's one sample entry, for a part that templates
    `each: "{parameter}"` over it (the operator role's `roles`): a mapping
    with every key the templates read off an entry, each a placeholder that
    names itself, so the part makes one of what it makes rather than
    failing on a token nobody bound. None for a parameter no template
    walks."""
    keys: set = set()
    found = False
    for records in list(module.provides.values()) + list(module.relations.values()):
        for template in records:
            if not isinstance(template, dict) or str(template.get("each", "")) != "{%s}" % parameter:
                continue
            found = True
            rest = {k: v for k, v in template.items() if k != "each"}
            for token in _TOKEN.findall(str(rest)):
                if token not in ("item", "alias") and token not in _REQUIRED_ANSWERS:
                    keys.add(token)
    if not found:
        return None
    entry = {"id": "sample-" + parameter}
    entry.update({key: "sample-" + key for key in sorted(keys)})
    return [entry]


def _sample_answers(member_ids: Sequence[str], model: Model, modules: Dict[str, Module], product_name: str) -> Dict[str, Any]:
    """Every answer the parts require, given as a placeholder that names
    it; the systems a part wires to (`system`, `caller_system`,
    `source_system`) are a real system where the model has one, so the
    picture shows the line rather than a line to nothing."""
    systems = sorted(model.entities.get("systems", {}))
    answers: Dict[str, Any] = {name: "sample-" + name for name in _REQUIRED_ANSWERS}
    for member_id in member_ids:
        member = modules.get(member_id)
        # A member the library does not hold is the assembly's complaint to
        # make, by name; the answers are not where it is caught.
        for parameter in (member.parameters if member is not None else ()):
            if parameter.required and parameter.default is None and not parameter.component:
                entries = _sample_entries(member, parameter.name)
                answers.setdefault(parameter.name, entries if entries is not None else "sample-" + parameter.name)
    answers["slug"] = "sample"
    answers["product_name"] = product_name
    if systems:
        for name in list(answers):
            if name == "system" or name.endswith("_system"):
                answers[name] = systems[0]
    return answers


def sample_assembly(kit: Module, provider: str, model: Model, modules: Dict[str, Module]) -> dict:
    """A stand-in product assembled from one kit on one landing zone, the
    record the Assemble panel would write, its answers placeholders that
    name themselves."""
    from .modules import members_of

    answers = _sample_answers(members_of(kit, modules), model, modules, "Sample %s" % kit.name.lower())
    return {
        "product_id": "SAMPLE-KIT-%s-%s" % (kit.module_id.upper(), provider.upper()),
        "name": "Sample %s on %s" % (kit.name.lower(), provider),
        "description": "A sample product, assembled for its picture.",
        "status": "Planned",
        "compose": {"modules": [{"module": kit.module_id}], "provider": provider},
        "parameters": answers,
    }


def requires_of(part: Module, modules: Dict[str, Module]) -> List[str]:
    """The parts a part needs beside it, all the way down, in the order they
    are composed: what a part requires comes before the part, and the part
    itself comes last."""
    out: List[str] = []

    def walk(module_id: str, seen: set) -> None:
        module = modules.get(module_id)
        if module is None or module_id in seen:
            return
        seen.add(module_id)
        for required in module.requires:
            walk(str(required), seen)
        if module_id not in out:
            out.append(module_id)

    walk(part.module_id, set())
    return out


def sample_part(part: Module, provider: str, model: Model, modules: Dict[str, Module]) -> dict:
    """A stand-in product assembled from one part and the parts it requires
    on one landing zone, so the picture of a part shows it wired to what it
    is for: the mobile channel calling the product API, the async worker
    reading the event stream the publisher writes."""
    members = requires_of(part, modules)
    answers = _sample_answers(members, model, modules, "Sample %s" % part.name.lower())
    # A part may template the product's description (the operator role
    # does), so the sample has one, as a real product would.
    return {
        "product_id": "SAMPLE-PART-%s-%s" % (part.module_id.upper(), provider.upper()),
        "name": "Sample %s on %s" % (part.name.lower(), provider),
        "description": "A sample product, assembled for its picture.",
        "status": "Planned",
        "compose": {"modules": [{"module": member} for member in members], "provider": provider},
        "parameters": answers,
    }


def _reason(message: str, instance_id: str) -> str:
    """An expansion error names the sample and its shape of one before it
    says what is wrong; the catalog has room only for what is wrong."""
    for prefix in ("%s: archetype compose:%s " % (instance_id, instance_id), "%s: " % instance_id):
        if message.startswith(prefix):
            message = message[len(prefix):]
    return message.rstrip(".")


def scratch_model(model: Model) -> Model:
    """A copy of the loaded model that can take an expansion without the
    model, or anything holding it, seeing the sample."""
    twin = copy.copy(model)
    twin.entities = {t: dict(v) for t, v in model.entities.items()}
    twin.relations = {n: list(v) for n, v in model.relations.items()}
    twin.warnings = list(model.warnings)
    twin._adjacent = None
    return twin


def overlay(model: Model, instance: dict, expansion, instance_type: str) -> Model:
    """The model with one expansion in it, or a `ModelError` naming the id
    the estate already holds: a picture that pulled a real product's parts
    in under a sample's name would be a picture of a lie."""
    scratch = scratch_model(model)
    source = Path("<sample>")
    entity_type = ENTITY_TYPES[instance_type]
    instance_id = str(instance[entity_type.pk])
    if scratch.find(instance_id) is not None:
        raise ModelError("the estate already holds %s" % instance_id)
    scratch._add_entity(entity_type, dict(expansion.instance), source)
    for type_name, records in expansion.entities.items():
        pk = ENTITY_TYPES[type_name].pk
        for record in records:
            entity_id = str(record.get(pk) or "")
            if scratch.find(entity_id) is not None:
                raise ModelError("the estate already holds %s" % entity_id)
            scratch._add_entity(ENTITY_TYPES[type_name], dict(record), source)
    for relation_name, rows in expansion.relations.items():
        for row in rows:
            try:
                scratch._add_relation(relation_name, dict(row), str(source))
            except ModelError:
                # A row the sample duplicates (two parts naming one platform
                # service) is the same fact twice, not a reason to stop.
                pass
    return scratch


def picture_payload(scratch: Model, views: Sequence[View], instance_id: str, picture_id: str, title: str,
                    description: str, palette: Palette, icons, components) -> dict:
    view = next((v for v in views if v.view_id == PICTURE_VIEW), None)
    if view is None:
        raise ViewError("no %s view to draw the picture with" % PICTURE_VIEW)
    bound = bind(view, {"product": instance_id}, scratch)
    payload = graph_payload(scratch, bound, palette, icons, components)
    payload["viewId"] = picture_id
    payload["title"] = title
    payload["description"] = description
    return payload


def render_pictures(model: Model, views: Sequence[View], shapes: Sequence[Archetype], modules: Dict[str, Module],
                    palette: Palette, icons, components, blocks, out_dir: Path, model_name: str,
                    root: Path, elk=None) -> Pictures:
    """Every shape's picture and every kit's, written under `out_dir`, a
    picture an earlier render wrote for a shape or kit that is gone removed.
    `blocks` are the library's building blocks; the landing zone a part's
    kinds resolve against is read off the model's technology services."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # The estate's answers ride with the library, as they do when the model
    # loads: a part asks the estate who stewards its data, and drawn without
    # them six shapes were "No picture".
    library = (components, blocks, modules, landing_zone_index(model.all_of("tech_services")),
               estate_answers(model.config))
    shape_paths: Dict[str, str] = {}
    kit_paths: Dict[str, Dict[str, str]] = {}
    notes: Dict[str, str] = {}
    written: List[Path] = []

    def draw(payload: dict, path: Path) -> bool:
        drawing_mode(payload)
        text = render_svg(payload, icon_loader=icons.read, model_name=model_name, elk=elk)
        path.write_text(text, encoding="utf-8")
        written.append(path)
        return True

    for archetype in sorted(shapes, key=lambda a: a.archetype_id):
        instance = sample_instance(archetype)
        picture_id = "shape--%s" % archetype.archetype_id
        try:
            expansion = expand(instance, archetype, archetype.applies_to, library)
            scratch = overlay(model, instance, expansion, archetype.applies_to)
            payload = picture_payload(
                scratch, views, str(instance[ENTITY_TYPES[archetype.applies_to].pk]), picture_id,
                "%s, as the shape makes it" % archetype.title,
                "A sample product on this shape: every box is something the shape creates, named with "
                "placeholders, and every line a relation it records. Drawn by the %s view, the way a real "
                "product on the shape is." % PICTURE_VIEW.replace("-", " "),
                palette, icons, components)
            draw(payload, out_dir / (picture_id + ".svg"))
            shape_paths[archetype.archetype_id] = "svg/%s.svg" % picture_id
        except (ArchetypeError, ModuleError, LibraryError, ComposeError, ModelError, ViewError, Undrawable) as exc:
            notes[archetype.archetype_id] = _reason(str(exc), str(instance[ENTITY_TYPES[archetype.applies_to].pk]))

    providers = landing_providers(shapes)
    for kit in sorted((m for m in modules.values() if m.is_kit), key=lambda m: m.module_id):
        for provider in providers:
            instance = sample_assembly(kit, provider, model, modules)
            picture_id = "kit--%s--%s" % (kit.module_id, provider.lower())
            try:
                shape = inline_shape(root, instance, "products", shapes)
                expansion = expand(instance, shape, "products", library)
                scratch = overlay(model, instance, expansion, "products")
                payload = picture_payload(
                    scratch, views, instance["product_id"], picture_id,
                    "%s, assembled on %s" % (kit.name, provider),
                    "A sample product assembled from this kit on the %s landing zone: its parts, what they run "
                    "on there, and what they reach, named with placeholders. Drawn by the %s view, the way an "
                    "assembled product is." % (provider, PICTURE_VIEW.replace("-", " ")),
                    palette, icons, components)
                draw(payload, out_dir / (picture_id + ".svg"))
                kit_paths.setdefault(kit.module_id, {})[provider] = "svg/%s.svg" % picture_id
            except (ArchetypeError, ModuleError, LibraryError, ComposeError, ModelError, ViewError,
                    Undrawable) as exc:
                notes["%s|%s" % (kit.module_id, provider)] = _reason(str(exc), instance["product_id"])

    # Every part as what it makes, assembled with the parts it requires on
    # the first landing zone: one picture a part, since what a part is does
    # not change with the provider, only what it runs on.
    part_paths: Dict[str, str] = {}
    if providers:
        first = providers[0]
        for part in sorted((m for m in modules.values() if not m.is_kit), key=lambda m: m.module_id):
            instance = sample_part(part, first, model, modules)
            picture_id = "part--%s" % part.module_id
            try:
                shape = inline_shape(root, instance, "products", shapes)
                expansion = expand(instance, shape, "products", library)
                scratch = overlay(model, instance, expansion, "products")
                payload = picture_payload(
                    scratch, views, instance["product_id"], picture_id,
                    "%s, with what it requires, on %s" % (part.name, first),
                    "A sample product assembled from this part and the parts it requires, on the %s landing zone: "
                    "what the part makes, what it runs on there, and what it reaches, named with placeholders. "
                    "Drawn by the %s view, the way an assembled product is." % (first, PICTURE_VIEW.replace("-", " ")),
                    palette, icons, components)
                draw(payload, out_dir / (picture_id + ".svg"))
                part_paths[part.module_id] = "svg/%s.svg" % picture_id
            except (ArchetypeError, ModuleError, LibraryError, ComposeError, ModelError, ViewError,
                    Undrawable) as exc:
                notes["%s|%s" % (part.module_id, first)] = _reason(str(exc), instance["product_id"])

    # Every block as the small diagram it is, and the library as a map.
    block_paths: Dict[str, str] = {}
    for block in sorted(blocks.values(), key=lambda b: b.building_block_id):
        picture_id = "block--%s" % block.building_block_id
        try:
            draw(block_payload(block, components, palette), out_dir / (picture_id + ".svg"))
            block_paths[block.building_block_id] = "svg/%s.svg" % picture_id
        except Undrawable as exc:
            notes[block.building_block_id] = str(exc)
    maps: Dict[str, str] = {}
    for name, payload in (("kits", kits_map_payload(modules, palette)),
                          ("parts", parts_map_payload(modules, blocks, components, palette))):
        try:
            draw(payload, out_dir / ("%s-map.svg" % name))
            maps[name] = "svg/%s-map.svg" % name
        except Undrawable as exc:
            notes["%s-map" % name] = str(exc)

    # A picture of a shape or kit that is no longer in the library is stale,
    # and an untouched file is not a stale one to CI.
    keep = {p.resolve() for p in written}
    for old in sorted(out_dir.glob("*.svg")):
        if old.resolve() not in keep:
            old.unlink()
    return Pictures(shape_paths, kit_paths, notes, written, block_paths, maps, part_paths)


def _swatch_node(entity_type: str, palette: Palette) -> dict:
    sw = palette.type_swatch(entity_type)
    return {"fill": sw.fill, "stroke": sw.stroke, "ink": sw.ink, "strokeWidth": 1.4, "dash": "solid", "faded": False}


def _legend(palette: Palette, types: List[Tuple[str, str, int]], edge_kinds: List[str],
            boundaries: List[dict]) -> dict:
    return {
        "types": [{"key": key, "label": label, "fill": palette.type_swatch(key).fill,
                   "stroke": palette.type_swatch(key).stroke, "count": count} for key, label, count in types],
        "dimension": {"name": "", "role": "nominal", "grouped": False, "keys": []},
        "edges": [{"kind": kind, "style": edge_style(kind)} for kind in edge_kinds],
        "boundaries": boundaries,
    }


def block_payload(block, components, palette: Palette) -> dict:
    """A block as the small diagram it is: its components, each with the
    glyph of its category and the services it resolves to on each cloud,
    and the connections between them."""
    elements: List[dict] = []
    counts: Dict[str, int] = {}
    for provided in block.provides:
        component = components.get(provided.component)
        entity_type = str(component.applies_to if component else "tech_services")
        counts[entity_type] = counts.get(entity_type, 0) + 1
        resolves = " \u00b7 ".join(component.providers[p] for p in ("AWS", "Azure", "GCP")
                                    if component and component.providers.get(p)) if component else ""
        node = {
            "id": provided.component, "label": component.name if component else provided.component, "parent": None,
            "entityType": entity_type, "componentType": provided.component,
            "componentCategory": component.category if component else "", "tech": resolves, "icon": "",
            "start": "", "end": "", "status": "", "styleKey": entity_type,
        }
        node.update(_swatch_node(entity_type, palette))
        elements.append({"data": node})
    for i, (a, b) in enumerate(block.relations):
        elements.append({"data": {"id": "e%d::%s::%s" % (i, a, b), "source": a, "target": b, "label": "",
                                  "kind": "tech_service_connects_to",
                                  "lineStyle": edge_style("tech_service_connects_to"), "ref": ""}})
    return {
        "viewId": "block--%s" % block.building_block_id, "title": block.name,
        "description": (block.description or "").strip(), "kind": "diagram", "layout": "LR", "lanes": {},
        "colorBy": "type", "elements": elements, "notes": [],
        "counts": {"nodes": len(block.provides), "edges": len(block.relations)}, "flows": [],
        "legend": _legend(palette, [(t, ENTITY_TYPES[t].label if t in ENTITY_TYPES else t, n)
                                    for t, n in sorted(counts.items())],
                          ["tech_service_connects_to"] if block.relations else [], []),
    }


_BLOCK_TOKEN = re.compile(r"^([a-z0-9][a-z0-9-]*)\.[a-z0-9][a-z0-9-]*$")


def _blocks_of(module: Module, blocks) -> List[str]:
    """The blocks a part runs on: every `block.component` token in what it
    provides or in its parameters' defaults whose block the library has."""
    found: List[str] = []

    def walk(value) -> None:
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                walk(v)
        elif isinstance(value, str):
            match = _BLOCK_TOKEN.match(value.strip())
            if match and match.group(1) in blocks and match.group(1) not in found:
                found.append(match.group(1))

    walk(module.provides)
    for parameter in module.parameters:
        walk(parameter.default)
    return found


def _group(gid: str, label: str, kind: str) -> dict:
    return {"data": {"id": gid, "label": label, "value": label, "parent": None, "isGroup": True, "depth": 1,
                     "kind": kind, "provider": "", "bfill": "#f3f5fb", "bstroke": "#8f9bb5", "bdash": "solid",
                     "bink": "#3b4a6b", "bkey": "", "icon": ""}}


def _made(module: Module) -> str:
    counts: Dict[str, int] = {}
    for type_name, records in module.provides.items():
        counts[type_name] = counts.get(type_name, 0) + len(records)
    return " \u00b7 ".join("%d %s" % (n, (ENTITY_TYPES[t].label if t in ENTITY_TYPES else t).lower()
                                    + ("" if n == 1 else "s")) for t, n in sorted(counts.items()))


def _part_node(part: Module, palette: Palette) -> dict:
    node = {"id": "part::" + part.module_id, "label": part.name, "parent": "grp::category::%s" % part.category,
            "entityType": "systems", "componentType": "", "componentCategory": "", "tech": _made(part),
            "icon": "", "start": "", "end": "", "status": "", "styleKey": "systems"}
    node.update(_swatch_node("systems", palette))
    return {"data": node}


def kits_map_payload(modules: Dict[str, Module], palette: Palette) -> dict:
    """The kits and the parts they are made of: a kit chosen in the
    Assemble panel picks its members, each under its own name."""
    from .modules import members_of

    kits = sorted((m for m in modules.values() if m.is_kit), key=lambda m: m.name.lower())
    member_ids = sorted({m for kit in kits for m in members_of(kit, modules) if m in modules and not modules[m].is_kit})
    parts = sorted((modules[m] for m in member_ids), key=lambda m: m.name.lower())
    elements: List[dict] = [_group("grp::kits", "Kits", "layer")]
    for category in sorted({p.category for p in parts}):
        elements.append(_group("grp::category::%s" % category, category, "category"))
    for kit in kits:
        node = {"id": "kit::" + kit.module_id, "label": kit.name, "parent": "grp::kits", "entityType": "products",
                "componentType": "", "componentCategory": "", "tech": "%d parts" % len(members_of(kit, modules)),
                "icon": "", "start": "", "end": "", "status": "", "styleKey": "products"}
        node.update(_swatch_node("products", palette))
        elements.append({"data": node})
    for part in parts:
        elements.append(_part_node(part, palette))
    edges = 0
    for kit in kits:
        for member in members_of(kit, modules):
            if member in member_ids:
                elements.append({"data": {"id": "e%d::%s::%s" % (edges, kit.module_id, member),
                                          "source": "kit::" + kit.module_id, "target": "part::" + member, "label": "",
                                          "kind": "product_includes_system",
                                          "lineStyle": edge_style("product_includes_system"), "ref": ""}})
                edges += 1
    return {
        "viewId": "kits-map", "title": "The kits, and what they are made of",
        "description": "Every kit in the library and the parts it picks: the standard applications and the vendor "
                       "baseline, each a handful of the parts below, in their categories. A product on a kit can "
                       "still do without one of them or add a part the kit did not bring.",
        "kind": "diagram", "layout": "TB", "lanes": {}, "colorBy": "type", "elements": elements, "notes": [],
        "counts": {"nodes": len(kits) + len(parts), "edges": edges}, "flows": [],
        "legend": _legend(palette, [("products", "kit", len(kits)), ("systems", "part", len(parts))],
                          ["product_includes_system"],
                          [{"key": "part category", "fill": "#f3f5fb", "stroke": "#8f9bb5", "dash": "solid"}]),
    }


def parts_map_payload(modules: Dict[str, Module], blocks, components, palette: Palette) -> dict:
    """The parts, the parts they require, and the blocks they run on; the
    parts in their categories. What a part needs from another is a line
    between them; what it needs from the landing zone is a line to the
    block that answers for it."""
    parts = sorted((m for m in modules.values() if not m.is_kit), key=lambda m: m.name.lower())
    part_ids = {m.module_id for m in parts}
    used_blocks = sorted({b for m in parts for b in _blocks_of(m, blocks)})
    elements: List[dict] = []
    for category in sorted({p.category for p in parts}):
        elements.append(_group("grp::category::%s" % category, category, "category"))
    if used_blocks:
        elements.append(_group("grp::blocks", "Building blocks", "layer"))
    for part in parts:
        elements.append(_part_node(part, palette))
    for block_id in used_blocks:
        block = blocks[block_id]
        node = {"id": "block::" + block_id, "label": block.name, "parent": "grp::blocks", "entityType": "tech_services",
                "componentType": "", "componentCategory": block.category,
                "tech": " \u00b7 ".join(components[p.component].name if p.component in components else p.component
                                        for p in block.provides),
                "icon": "", "start": "", "end": "", "status": "", "styleKey": "tech_services"}
        node.update(_swatch_node("tech_services", palette))
        elements.append({"data": node})
    edges = 0

    def edge(source: str, target: str, kind: str) -> None:
        nonlocal edges
        elements.append({"data": {"id": "e%d::%s::%s" % (edges, source, target), "source": source, "target": target,
                                  "label": "", "kind": kind, "lineStyle": edge_style(kind), "ref": ""}})
        edges += 1

    for part in parts:
        for required in part.requires:
            if required in part_ids and required != part.module_id:
                edge("part::" + part.module_id, "part::" + required, "requires")
        for block_id in _blocks_of(part, blocks):
            edge("part::" + part.module_id, "block::" + block_id, "system_uses_tech_service")
    return {
        "viewId": "parts-map", "title": "The parts, what they require, and what they run on",
        "description": "Every part in the library in its category, a line to each part it requires in the same "
                       "product, and a dashed line to each building block it runs on; the landing zone of the "
                       "shape that composes it answers for the block.",
        "kind": "diagram", "layout": "TB", "lanes": {}, "colorBy": "type", "elements": elements, "notes": [],
        "counts": {"nodes": len(parts) + len(used_blocks), "edges": edges}, "flows": [],
        "legend": _legend(palette, [("systems", "part", len(parts)), ("tech_services", "building block", len(used_blocks))],
                          ["requires", "system_uses_tech_service"],
                          [{"key": "part category", "fill": "#f3f5fb", "stroke": "#8f9bb5", "dash": "solid"}]),
    }
