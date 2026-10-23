"""Render the library -- blocks, patterns, parts and shapes -- as documentation.

The pattern catalog is the thing an architecture review board actually reads,
and a catalog that lives only in YAML is a catalog nobody reads. So `terrane
render` writes it out beside the diagrams, with the one column no hand-kept
catalog ever has: which products apply each pattern, computed from the model
rather than surveyed. The parts and the shapes get the same treatment: where
each part is used and which products sit on each shape are read off the
library and the model, not kept by hand.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

from .archetype import (
    Archetype,
    ArchetypeError,
    effective_bind,
    landing_providers,
    landing_zone_gaps,
    landing_zone_index,
    resolve_kind,
    zone_binds,
)
from .adoption import candidates, drifts
from .build_types import BuildType, conformance, uses_by_build_types
from .blocks import BuildingBlock, ComponentType, Pattern, PATTERN_STATUS
from .answers import adopted_patterns
from .modules import Module, members_of, uses_of
from .schema import ENTITY_TYPES

#: A provider column appears in the block tables only when some component in
#: the library names it, so a library with no GCP resolution has no empty
#: GCP column.
_PROVIDER_ORDER = ("AWS", "Azure", "GCP", "On-prem", "SaaS")


def _providers_in(components: Iterable[ComponentType]) -> List[str]:
    seen = {name for c in components for name in c.providers}
    ordered = [p for p in _PROVIDER_ORDER if p in seen]
    return ordered + sorted(seen - set(_PROVIDER_ORDER))


def _para(text: str) -> str:
    return " ".join(str(text or "").split())


def _spoken(items: List[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _folders(folder: str, records: Iterable) -> List[str]:
    """The layer's folder in the shipped library, then in each of the
    organization's that a record here came from (`library.load_layer`)."""
    named = sorted({str(getattr(r, "library", "") or "") for r in records} - {""})
    return ["`%s/`" % folder] + ["`%s/%s/`" % (name, folder) for name in named]


def _generated(folder: str, records: Iterable) -> str:
    """"Generated from `X/` by `terrane render`; edit that, not this", with the
    organization's folders named beside the shipped one."""
    folders = _folders(folder, records)
    return "Generated from %s by `terrane render`; edit %s, not this." % (
        _spoken(folders), "that" if len(folders) == 1 else "those")


def _mark(record) -> str:
    """After a name in a table: the library a record came from, when it is
    not the shipped one."""
    library = str(getattr(record, "library", "") or "")
    return " *(%s)*" % library if library else ""


def _origin(record) -> Optional[str]:
    """A record's library in its own section, and the file it replaced: a
    replacement the catalog did not mention would be a shadow with extra
    steps."""
    library = str(getattr(record, "library", "") or "")
    if not library:
        return None
    replaced = str(getattr(record, "replaced", "") or "")
    if replaced:
        return "From `%s/`, in place of the one in `%s`." % (library, replaced)
    return "From `%s/`." % library


def _asked(param) -> str:
    """After a parameter's name: what it takes when the product says nothing.
    One the estate answers says so, since that is where an adopter writes
    it: `answers` in model.yaml, not the product file."""
    if getattr(param, "estate", False):
        return " (the estate's answer%s)" % (
            ", else `%s`" % param.default if param.default is not None else "")
    if param.required:
        return " (required)"
    return " (default `%s`)" % param.default if param.default is not None else ""


def _applied_by(model, pattern_id: str, type_name: str = "products") -> List[dict]:
    """Products (or interfaces) carrying this pattern, so adoption is read
    off the model rather than off a register."""
    if model is None:
        return []
    pk = "product_id" if type_name == "products" else "interface_id"
    out = []
    for record in model.all_of(type_name):
        if pattern_id in model.list_of(record, "patterns"):
            out.append(record)
    return sorted(out, key=lambda r: str(r.get("name") or r[pk]).lower())


def render_patterns(
    patterns: Dict[str, Pattern],
    blocks: Dict[str, BuildingBlock],
    components: Dict[str, ComponentType],
    model=None,
    pictures=None,
) -> str:
    """The patterns catalog: a block plus the decision, each. With
    `pictures` (`terrane.pictures`), each pattern shows the drawing of every
    block it is made of, since a pattern with no picture of its own is the
    one page of the library that was words alone."""
    # Who owns each pattern, the decision that approved it and the controls
    # it meets are the estate's, from its model.yaml (terrane/answers.py).
    if model is not None:
        patterns = adopted_patterns(patterns, model.config)
    order = {status: index for index, status in enumerate(PATTERN_STATUS)}
    ordered = sorted(
        patterns.values(),
        key=lambda p: (order.get(p.status, len(order)), p.name.lower()),
    )

    def control_name(control_id: str) -> str:
        record = model.get("controls", control_id) if model is not None else None
        return "%s (`%s`)" % (record["name"], control_id) if record else "`%s`" % control_id

    lines: List[str] = ["# Patterns", ""]
    lines.append(
        "A building block plus the decision: what it is for, what it costs, and "
        "when not to use it. Generated from %s by `terrane render`; edit "
        "the pattern files, not this. Who owns each one here, the decision that "
        "approved it and the controls it satisfies are the estate's, under "
        "`patterns` in `10_MODEL/model.yaml`." % _spoken(_folders("27_PATTERNS", ordered))
    )
    lines.append("")
    lines.append(
        "The last column is the adoption report. It is read off the `patterns` "
        "field of every product and every interface in the model, so it is "
        "current whether or not anybody remembered to update a register. Where "
        "a pattern implements one of the method's reference patterns, the "
        "**Method** line names it."
    )
    lines.append("")
    lines.append("| Pattern | Status | Category | Made of | Satisfies | Applied by |")
    lines.append("|---|---|---|---|---|---|")
    for pattern in ordered:
        applied = _applied_by(model, pattern.pattern_id)
        on_interfaces = _applied_by(model, pattern.pattern_id, "interfaces")
        cell = [str(r.get("name") or r["product_id"]) for r in applied]
        if on_interfaces:
            # The interfaces by count in the table and by name below it; a
            # pattern on twelve feeds would otherwise make the table a wall.
            cell.append(
                "%d interface%s" % (len(on_interfaces), "" if len(on_interfaces) == 1 else "s")
            )
        lines.append(
            "| [%s](#%s)%s | %s | %s | %s | %s | %s |"
            % (
                pattern.name,
                pattern.pattern_id,
                _mark(pattern),
                pattern.status,
                pattern.category,
                ", ".join("`%s`" % b for b in pattern.blocks) or "—",
                ", ".join("`%s`" % c for c in pattern.satisfies) or "—",
                ", ".join(cell) or "—",
            )
        )
    lines.append("")

    for pattern in ordered:
        lines.append('<a id="%s"></a>' % pattern.pattern_id)
        lines.append("## %s" % pattern.name)
        lines.append("")
        facts = [
            "**Id:** `%s`" % pattern.pattern_id,
            "**Status:** %s" % pattern.status,
            "**Category:** %s" % pattern.category,
        ]
        if pattern.owner_org_id:
            owner = model.get("org_units", pattern.owner_org_id) if model is not None else None
            facts.append(
                "**Owner:** %s" % (owner["name"] if owner else "`%s`" % pattern.owner_org_id)
            )
        if pattern.decision_ref:
            facts.append("**Decision:** %s" % pattern.decision_ref)
        if pattern.method_ref:
            facts.append("**Method:** %s" % pattern.method_ref)
        lines.append(" · ".join(facts))
        lines.append("")
        if _origin(pattern):
            lines.append(_origin(pattern))
            lines.append("")
        lines.append("**Intent.** %s" % _para(pattern.intent))
        lines.append("")
        lines.append("**What it costs.** %s" % _para(pattern.consequences))
        lines.append("")
        lines.append("**When not to use it.** %s" % _para(pattern.when_not_to_use))
        lines.append("")
        made_of = []
        for block_id in pattern.blocks:
            block = blocks.get(block_id)
            if block is None:
                made_of.append("`%s`" % block_id)
                continue
            parts = ", ".join(
                components[p.component].name if p.component in components else p.component
                for p in block.provides
            )
            made_of.append("%s (`%s`): %s" % (block.name, block_id, parts))
        if made_of:
            lines.append("**Made of.** " + "; ".join(made_of) + ".")
            lines.append("")
        if pictures is not None:
            for block_id in pattern.blocks:
                if block_id in pictures.blocks:
                    block = blocks.get(block_id)
                    lines.extend(_picture_lines(
                        pictures.blocks[block_id], "%s, as the block is drawn" % (block.name if block else block_id),
                        "%s: the block's components with the category glyph and the services each resolves "
                        "to, and the connections between them." % (block.name if block else block_id)))
        if pattern.satisfies:
            lines.append(
                "**Satisfies.** " + ", ".join(control_name(c) for c in pattern.satisfies) + "."
            )
            lines.append("")
        applied = _applied_by(model, pattern.pattern_id)
        on_interfaces = _applied_by(model, pattern.pattern_id, "interfaces")
        if applied:
            lines.append(
                "**Applied by.** "
                + ", ".join(
                    "%s (`%s`)" % (r.get("name") or r["product_id"], r["product_id"])
                    for r in applied
                )
                + "."
            )
        elif not on_interfaces:
            lines.append("**Applied by.** Nothing in the model yet.")
        if on_interfaces:
            if applied:
                lines.append("")
            lines.append(
                "**On interfaces.** "
                + ", ".join(
                    "%s (`%s`)" % (r.get("name") or r["interface_id"], r["interface_id"])
                    for r in on_interfaces
                )
                + "."
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_blocks(
    blocks: Dict[str, BuildingBlock],
    components: Dict[str, ComponentType],
    patterns: Optional[Dict[str, Pattern]] = None,
    pictures=None,
) -> str:
    providers = _providers_in(components.values())
    in_patterns: Dict[str, List[str]] = {}
    for pattern in (patterns or {}).values():
        for block_id in pattern.blocks:
            in_patterns.setdefault(block_id, []).append(pattern.name)

    ordered = sorted(blocks.values(), key=lambda b: (b.category, b.name.lower()))
    lines: List[str] = ["# Building blocks", ""]
    lines.append(
        "The handfuls of components that always arrive together, and what each "
        "cloud calls them. No block names a vendor; the provider columns are what "
        "the same block resolves to on each. Generated from %s by `terrane render`; "
        "edit those, not this."
        % _spoken(_folders("26_BLOCKS", ordered) + _folders("25_COMPONENTS", components.values()))
    )
    lines.append("")
    lines.append("| Block | Category | Components | In patterns |")
    lines.append("|---|---|---|---|")
    for block in ordered:
        lines.append(
            "| [%s](#%s)%s | %s | %d | %s |"
            % (
                block.name,
                block.building_block_id,
                _mark(block),
                block.category,
                len(block.provides),
                ", ".join(sorted(in_patterns.get(block.building_block_id, []))) or "—",
            )
        )
    lines.append("")

    for block in ordered:
        lines.append('<a id="%s"></a>' % block.building_block_id)
        lines.append("## %s" % block.name)
        lines.append("")
        lines.append("`%s` · %s" % (block.building_block_id, block.category))
        lines.append("")
        if _origin(block):
            lines.append(_origin(block))
            lines.append("")
        lines.append(_para(block.description))
        lines.append("")
        if pictures is not None and block.building_block_id in pictures.blocks:
            lines.extend(_picture_lines(pictures.blocks[block.building_block_id], block.name,
                                        "The block's components, each with the services it resolves to, and the "
                                        "connections between them."))
        lines.append("| Component | " + " | ".join(providers) + " |")
        lines.append("|---|" + "---|" * len(providers))
        for provided in block.provides:
            component = components.get(provided.component)
            if component is None:
                lines.append("| `%s` |%s" % (provided.component, " |" * len(providers)))
                continue
            cells = [component.providers.get(p, "") for p in providers]
            lines.append(
                "| %s (`%s`)%s | %s |"
                % (component.name, component.component_type_id, _mark(component), " | ".join(cells))
            )
        lines.append("")
        if block.relations:
            names = {
                p.component: (components[p.component].name if p.component in components
                              else p.component)
                for p in block.provides
            }
            lines.append(
                "**Connections.** "
                + "; ".join("%s → %s" % (names[a], names[b]) for a, b in block.relations)
                + "."
            )
            lines.append("")
        if block.defaults:
            lines.append(
                "**Defaults.** "
                + ", ".join("`%s: %s`" % (k, v) for k, v in sorted(block.defaults.items()))
                + "."
            )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _count_by_type(module: Module, modules: Dict[str, Module]) -> Dict[str, int]:
    """What a part creates, by entity type. A kit counts what its members do."""
    out: Dict[str, int] = {}
    for member in members_of(module, modules):
        for type_name, templates in modules[member].provides.items():
            out[type_name] = out.get(type_name, 0) + len(templates)
    return out


def _made(counts: Dict[str, int]) -> str:
    return ", ".join(
        "%d %s" % (n, t.replace("_", " ")) for t, n in sorted(counts.items())
    ) or "—"


def _picture_lines(path: str, alt: str, caption: str) -> List[str]:
    return ["![%s](%s)" % (alt, path), "", "*%s*" % caption, ""]


def render_modules(
    modules: Dict[str, Module],
    archetypes: Iterable[Archetype],
    model=None,
    types: Optional[Dict[str, BuildType]] = None,
    pictures=None,
) -> str:
    """The parts catalog, with the column the library did not have until it
    could answer it: where each part is used, read off the shapes, the
    assembled products and the build types. `pictures` (`terrane.pictures`)
    gives each kit its drawing per landing zone and each part its own,
    with what it requires."""
    shapes = list(archetypes)
    used = uses_of(modules, list(shapes) + list(getattr(model, "composed", {}).values()))
    if types:
        uses_by_build_types(used, types, modules)
    ordered = sorted(modules.values(), key=lambda m: (m.category, m.name.lower()))

    lines: List[str] = ["# Parts", ""]
    lines.append(
        "The parts a shape is composed from: what each provides, what it needs "
        "from the shape, the kinds of shared service it runs on, and where it is "
        "used. No part names a cloud; a kind resolves to the landing zone of "
        "whichever shape composes it. " + _generated("28_MODULES", ordered)
    )
    lines.append("")
    if pictures is not None and pictures.maps.get("kits"):
        lines.extend(_picture_lines(pictures.maps["kits"], "The kits, and what they are made of",
                                    "Every kit and the parts it picks, in their categories."))
    if pictures is not None and pictures.maps.get("parts"):
        lines.extend(_picture_lines(pictures.maps["parts"], "The parts, what they require, and what they run on",
                                    "Every part in its category, the parts it requires, and the building blocks it "
                                    "runs on."))
    lines.append("| Part | Category | Provides | Needs | Kinds | Used by |")
    lines.append("|---|---|---|---|---|---|")
    for module in ordered:
        kinds = sorted({p.component for p in module.parameters if p.component})
        lines.append(
            "| [%s](#%s)%s | %s | %s | %s | %s | %s |"
            % (
                module.name,
                module.module_id,
                (" *(kit)*" if module.is_kit else "") + _mark(module),
                module.category,
                _made(_count_by_type(module, modules)),
                ", ".join("`%s`" % n for n in module.needs) or "—",
                ", ".join("`%s`" % k for k in kinds) or "—",
                ", ".join(used.get(module.module_id, [])) or "nothing",
            )
        )
    lines.append("")

    for module in ordered:
        lines.append('<a id="%s"></a>' % module.module_id)
        lines.append("## %s" % module.name)
        lines.append("")
        facts = ["`%s`" % module.module_id, module.category,
                 "optional" if module.optional else "always present"]
        if module.is_kit:
            facts.append("kit of " + ", ".join("`%s`" % m for m in members_of(module, modules)))
        lines.append(" · ".join(facts))
        lines.append("")
        if _origin(module):
            lines.append(_origin(module))
            lines.append("")
        lines.append(_para(module.description))
        lines.append("")
        if module.is_kit and pictures is not None:
            drawn = pictures.kits.get(module.module_id, {})
            if drawn:
                first, others = list(drawn.items())[0], list(drawn.items())[1:]
                caption = "A sample product assembled from the kit on %s, drawn by the product architecture view; " \
                          "the names are placeholders." % first[0]
                if others:
                    caption += " Also on " + " and ".join("[%s](%s)" % (p, path) for p, path in others) + "."
                lines.extend(_picture_lines(first[1], "%s assembled on %s" % (module.name, first[0]), caption))
        elif pictures is not None and module.module_id in getattr(pictures, "parts", {}):
            # A part is drawn with what it requires, so the picture shows it
            # wired to what it is for rather than as a box on its own.
            caption = "A sample product assembled from this part and the parts it requires, drawn by the product " \
                      "architecture view; the names are placeholders."
            if module.requires:
                caption += " With " + ", ".join("`%s`" % r for r in module.requires) + "."
            lines.extend(_picture_lines(pictures.parts[module.module_id], "%s, with what it requires" % module.name,
                                        caption))
        if pictures is not None:
            missing = [k.split("|", 1)[1] + ": " + v for k, v in sorted(pictures.notes.items())
                       if k.startswith(module.module_id + "|")]
            if missing:
                lines.append("**No picture on** %s." % "; ".join(missing))
                lines.append("")
        lines.append("**Provides.** %s." % _made(_count_by_type(module, modules)))
        if module.needs:
            lines.append(
                "**Needs from the shape.** %s." % ", ".join("`%s`" % n for n in module.needs)
            )
        kinds = [(p.name, p.component, p.default) for p in module.parameters if p.component]
        if kinds:
            lines.append(
                "**Kinds.** "
                + "; ".join(
                    "`%s` is of kind `%s`%s" % (name, kind, " (defaults to `%s`)" % default if default else "")
                    for name, kind, default in kinds
                )
                + "."
            )
        asked = [p for p in module.parameters if not p.component]
        if asked:
            lines.append(
                "**Parameters.** "
                + "; ".join("`%s`%s" % (p.name, _asked(p)) for p in asked)
                + "."
            )
        if module.requires:
            lines.append("**Requires.** %s." % ", ".join("`%s`" % r for r in module.requires))
        if module.patterns:
            lines.append("**Applies.** %s." % ", ".join("`%s`" % p for p in module.patterns))
        by = used.get(module.module_id, [])
        lines.append(
            "**Used by.** %s" % (", ".join(by) + "." if by
                                 else "Nothing composes it; it is waiting for its shape, or forgotten.")
        )
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_shapes(
    archetypes: Iterable[Archetype],
    modules: Dict[str, Module],
    model=None,
    pictures=None,
) -> str:
    """The shapes catalog: what each is composed from, where it varies, and
    which products are on it; with `pictures` (`terrane.pictures`), what each
    makes, drawn."""
    ordered = sorted(archetypes, key=lambda a: a.title.lower())
    landing = landing_zone_index(model.all_of("tech_services")) if model is not None else {}

    def instances_of(archetype: Archetype) -> List[dict]:
        if model is None:
            return []
        return sorted(
            (r for r in model.all_of(archetype.applies_to)
             if str(r.get("archetype") or "") == archetype.archetype_id),
            key=lambda r: str(r.get("name") or ""),
        )

    lines: List[str] = ["# Shapes", ""]
    lines.append(
        "A shape is a provider, the parts it always has, the slots where it "
        "varies, and a `bind` only where the landing zone cannot decide. A "
        "product is a shape, a handful of answers, and a choice per slot; the "
        "diagram follows. Generated from %s by `terrane render`; edit "
        "those, not this." % _spoken(_folders("20_ARCHETYPES", ordered))
    )
    lines.append("")
    lines.append("| Shape | Version | Provider | Parts | Slots | Products |")
    lines.append("|---|---|---|---|---|---|")
    for archetype in ordered:
        parts = sum(
            len(members_of(modules[str(e["module"])], modules)) if str(e["module"]) in modules else 1
            for e in archetype.modules
        )
        lines.append(
            "| [%s](#%s)%s | %s | %s | %d | %d | %d |"
            % (archetype.title, archetype.archetype_id, _mark(archetype), archetype.version,
               archetype.provider or "—", parts, len(archetype.slots),
               len(instances_of(archetype)))
        )
    lines.append("")

    for archetype in ordered:
        lines.append('<a id="%s"></a>' % archetype.archetype_id)
        lines.append("## %s" % archetype.title)
        lines.append("")
        lines.append(
            "`%s` · version %s · %s · applies to %s"
            % (archetype.archetype_id, archetype.version,
               ("on " + archetype.provider) if archetype.provider else "no provider",
               archetype.applies_to.replace("_", " "))
        )
        lines.append("")
        if _origin(archetype):
            lines.append(_origin(archetype))
            lines.append("")
        lines.append(_para(archetype.description))
        lines.append("")
        if pictures is not None:
            if archetype.archetype_id in pictures.shapes:
                lines.extend(_picture_lines(
                    pictures.shapes[archetype.archetype_id], "%s, as the shape makes it" % archetype.title,
                    "A sample product on the shape, drawn by the product architecture view; the names are "
                    "placeholders."))
            elif archetype.archetype_id in pictures.notes:
                lines.append("**No picture.** %s." % pictures.notes[archetype.archetype_id].rstrip("."))
                lines.append("")
        if archetype.modules:
            named = []
            for entry in archetype.modules:
                module_id = str(entry["module"])
                alias = str(entry.get("as") or module_id)
                module = modules.get(module_id)
                if module is not None and module.is_kit:
                    named.append(
                        "`%s` (kit: %s)" % (alias, ", ".join("`%s`" % m for m in members_of(module, modules)))
                    )
                else:
                    named.append("`%s`" % alias)
            lines.append("**Parts.** %s." % ", ".join(named))
        if archetype.blocks:
            lines.append(
                "**Blocks.** %s." % ", ".join("`%s`" % str(b.get("block")) for b in archetype.blocks)
            )
        for slot in archetype.slots:
            options = ", ".join(
                "`%s`%s" % (o, " (default)" if o == slot.default else "") for o in slot.options
            )
            answered = "".join(
                "; answers %s for `%s`" % (", ".join("`%s`" % k for k in sorted(given)), option)
                for option, given in sorted(slot.answers.items()) if given
            )
            lines.append(
                "**Slot `%s`.** %s%s%s%s"
                % (slot.name, options, ", or none" if slot.optional else "", answered,
                   (". " + _para(slot.description)) if slot.description else ".")
            )
        try:
            zone = effective_bind(archetype)
            to_zone = zone_binds(archetype)
        except ArchetypeError as exc:
            zone, to_zone = {}, []
            lines.append("**Binds.** Contradictory: %s" % exc)
        # A kind bound to the landing zone is whatever the estate's zone
        # answers; this model's answer is named, so the catalog still says
        # what a product on the shape lands on here.
        bound = [(k, "`%s` → `%s`" % (k, v)) for k, v in zone.items()]
        for kind in sorted({k for k, _block in to_zone}):
            found, _candidates = resolve_kind(kind, archetype.provider, landing)
            bound.append((kind, "`%s` → the landing zone's%s" % (kind, " (`%s`)" % found if found else "")))
        if bound:
            lines.append("**Binds.** %s." % ", ".join(text for _k, text in sorted(bound)))
        if archetype.patterns:
            lines.append("**Applies.** %s." % ", ".join("`%s`" % p for p in archetype.patterns))
        asked = [p for p in archetype.parameters]
        if asked:
            lines.append(
                "**Asks for.** "
                + ", ".join(
                    "`%s`%s" % (p.name, _asked(p) if p.estate
                                else "" if p.required else " (default `%s`)" % p.default)
                    for p in asked
                )
                + "."
            )
        products = instances_of(archetype)
        if products:
            pk = ENTITY_TYPES[archetype.applies_to].pk
            lines.append(
                "**Products.** %s."
                % ", ".join("%s (`%s`)" % (r.get("name") or r[pk], r[pk]) for r in products)
            )
        else:
            lines.append("**Products.** None yet.")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _anchor(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def render_landing_zones(
    modules: Dict[str, Module],
    archetypes: Iterable[Archetype],
    model=None,
) -> str:
    """The landing zones: what each provider answers for, by kind, and the
    kinds the parts name that it does not. The second column is the one
    nothing kept until it could be computed."""
    shapes = sorted(archetypes, key=lambda a: a.archetype_id)
    services = list(model.all_of("tech_services")) if model is not None else []
    zone = landing_zone_index(services)
    names = {str(s["tech_service_id"]): str(s.get("name") or s["tech_service_id"]) for s in services}
    asked: Dict[str, List[str]] = {}
    for module in sorted(modules.values(), key=lambda m: m.module_id):
        for param in module.parameters:
            if param.component and param.default is None:
                asked.setdefault(param.component, []).append("`%s` (%s)" % (module.module_id, param.name))
    gaps = {(g.provider, g.kind): g for g in landing_zone_gaps(modules, shapes, zone)}

    primary = {str(s["tech_service_id"]): str(s.get("component_type") or "") for s in services}

    def named(ids: List[str], kind: str = "") -> str:
        cells = []
        for i in ids:
            cell = "%s (`%s`)" % (names.get(i, i), i)
            # A service answering for a kind that is not its own says which
            # it is, so the reader sees one service doing two jobs.
            if kind and primary.get(i) and primary[i] != kind:
                cell += " — a `%s` that answers for it" % primary[i]
            cells.append(cell)
        return ", ".join(cells)

    def products_on(provider: str) -> int:
        if model is None:
            return 0
        return sum(
            1
            for a in shapes if str(a.provider) == provider
            for r in model.all_of(a.applies_to)
            if str(r.get("archetype") or "") == a.archetype_id
        )

    providers = landing_providers(shapes)
    lines: List[str] = ["# Landing zones", ""]
    lines.append(
        "A landing zone is what a provider already runs for whatever lands on "
        "it: one shared service of each kind, tagged `landing-zone`, found by "
        "kind when a part asks. Nothing about it is written on a shape; a shape "
        "says its provider and the parts resolve. Measured here against the "
        "providers the shapes land on, with the kinds the parts name that each "
        "cannot answer -- where the next onboarding would stop. Generated from "
        "`10_MODEL/tech_services/`, `28_MODULES/` and `20_ARCHETYPES/` by `terrane "
        "render`; edit those, not this."
    )
    lines.append("")
    lines.append("| Provider | Shapes | Products | Kinds | Asked for and missing |")
    lines.append("|---|---|---:|---:|---|")
    for provider in providers:
        own = sorted(k for (p, k) in zone if p == provider)
        missing = sorted(k for (p, k) in gaps if p == provider)
        on_it = [a.archetype_id for a in shapes if str(a.provider) == provider]
        lines.append(
            "| [%s](#%s) | %s | %d | %d | %s |"
            % (provider, _anchor(provider), ", ".join("`%s`" % s for s in on_it),
               products_on(provider), len(own),
               ", ".join("`%s`" % k for k in missing) or "—")
        )
    lines.append("")

    for provider in providers:
        own = {k for (p, k) in zone if p == provider}
        lines.append('<a id="%s"></a>' % _anchor(provider))
        lines.append("## %s" % provider)
        lines.append("")
        lines.append(
            "**Shapes.** %s."
            % ", ".join("`%s`" % a.archetype_id for a in shapes if str(a.provider) == provider)
        )
        lines.append("")
        lines.append("| Kind | Service | Asked for by |")
        lines.append("|---|---|---|")
        for kind in sorted(own | set(asked)):
            found, candidates = resolve_kind(kind, provider, zone)
            if kind in own:
                cell = named(candidates, kind) + (" — ambiguous" if len(candidates) > 1 else "")
            elif candidates:
                cell = named(candidates, kind) + ", shared"
            else:
                gap = gaps.get((provider, kind))
                cell = "**none**"
                if gap is not None and gap.bound_by:
                    cell += " — bound by hand on %s" % ", ".join("`%s`" % b for b in gap.bound_by)
            lines.append("| `%s` | %s | %s |" % (kind, cell, ", ".join(asked.get(kind, [])) or "—"))
        lines.append("")

    shared = sorted(k for (p, k) in zone if p == "")
    if shared:
        lines.append('<a id="shared"></a>')
        lines.append("## Shared")
        lines.append("")
        lines.append(
            "Services with no provider of their own, answering for any landing "
            "zone that has none of their kind."
        )
        lines.append("")
        lines.append("| Kind | Service | Asked for by |")
        lines.append("|---|---|---|")
        for kind in shared:
            lines.append(
                "| `%s` | %s | %s |"
                % (kind, named(zone[("", kind)], kind), ", ".join(asked.get(kind, [])) or "—")
            )
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_adoption(
    modules: Dict[str, Module],
    archetypes: Iterable[Archetype],
    model,
) -> str:
    """Shapes and the estate: which products sit on a shape and how far each
    has drifted, which hand-authored products a shape would reproduce, and
    which fit none. Pattern adoption's counterpart for the modular layer."""
    shapes = list(archetypes)
    on_shapes = drifts(model, shapes, modules)
    fits = candidates(model, shapes, modules)
    fitted = {c.product_id for c in fits}
    on_ids = {d.product_id for d in on_shapes}
    composed = getattr(model, "composed", {}) or {}
    assembled = {
        archetype.archetype_id.split(":", 1)[1]: archetype for archetype in composed.values()
    }
    hand = [
        r for r in sorted(model.all_of("products"), key=lambda r: str(r["product_id"]))
        if str(r["product_id"]) not in on_ids and str(r["product_id"]) not in fitted
        and str(r["product_id"]) not in assembled
    ]

    def code(items) -> str:
        return ", ".join("`%s`" % i for i in items) if items else "—"

    lines: List[str] = ["# Shapes and the estate", ""]
    lines.append(
        "Which products sit on a shape and how far each has moved from it, which "
        "hand-authored products have the systems a shape's parts would make and "
        "are not on one, and which fit no shape. Drift is read from each product's "
        "own file, since what a product says beyond its shape is stripped when the "
        "shape expands; a candidate is a product whose systems, by category, are "
        "the shape's required parts. Generated from `10_MODEL/products/`, "
        "`20_ARCHETYPES/` and `28_MODULES/` by `terrane render`; edit those, not this."
    )
    lines.append("")
    lines.append(
        "%d product%s on a shape, %d assembled from parts, %d candidate%s, %d fitting no shape."
        % (len(on_shapes), "" if len(on_shapes) == 1 else "s", len(assembled),
           len(fits), "" if len(fits) == 1 else "s", len(hand))
    )
    lines.append("")

    if assembled:
        lines.append("## Assembled from parts")
        lines.append("")
        lines.append(
            "Products made of the library's parts with no shape, each from its own "
            "`compose` block. The second project like one of these is when a shape is "
            "worth naming."
        )
        lines.append("")
        lines.append("| Product | Provider | Parts |")
        lines.append("|---|---|---|")
        for product_id in sorted(assembled):
            archetype = assembled[product_id]
            record = model.get("products", product_id) or {}
            lines.append(
                "| %s (`%s`) | %s | %s |"
                % (record.get("name") or product_id, product_id, archetype.provider or "—",
                   code(str(e.get("module")) for e in archetype.modules))
            )
        lines.append("")

    lines.append("## On a shape")
    lines.append("")
    lines.append(
        "Moves counts every way a product differs from a bare instance of its "
        "shape: an answer that is not the default, an override, a record under "
        "`extra`, a part added or dropped, a slot chosen against its default, an "
        "id kept under the estate's name. A high count is not a fault; it is "
        "where the shape's next default lives."
    )
    lines.append("")
    lines.append("| Product | Shape | Answers | Overrides | Extra | Added | Dropped | Choices | Kept ids | Moves |")
    lines.append("|---|---|---|---|---|---|---|---|---|---:|")
    for d in on_shapes:
        extras = ", ".join("%d %s" % (n, t) for t, n in d.extras.items()) or "—"
        choices = ", ".join(
            "%s: `%s`%s" % (slot, pick, "" if default else " (not the default)")
            for slot, (pick, default) in d.choices.items()
        ) or "—"
        lines.append(
            "| %s (`%s`) | `%s` | %s | %s | %s | %s | %s | %s | %s | %d |"
            % (d.name, d.product_id, d.archetype_id, code(d.answered_defaults),
               code(d.overrides), extras, code(d.added), code(d.dropped), choices,
               code(d.renamed), d.moves)
        )
    lines.append("")

    lines.append("## Candidates")
    lines.append("")
    lines.append(
        "Hand-authored products whose systems are, by category, what a shape's "
        "required parts make. Not a fault: the shape came after the product. It "
        "is a product that is a handful of answers away from being on one, and "
        "`terrane validate` says so (`library.shape_candidate`)."
    )
    lines.append("")
    if fits:
        lines.append("| Product | Fits | Parts it has | Optional parts it lacks | Systems left over |")
        lines.append("|---|---|---|---|---|")
        for c in fits:
            lines.append(
                "| %s (`%s`) | `%s` | %s | %s | %s |"
                % (c.name, c.product_id, c.archetype_id,
                   ", ".join("`%s`" % a for a, _cat in c.covered),
                   ", ".join("`%s`" % a for a, _cat in c.missing_optional) or "—",
                   ", ".join(c.spare) or "—")
            )
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## No shape fits")
    lines.append("")
    if hand:
        lines.append(
            "Hand-authored products no shape's parts would reproduce. A shape that "
            "would is a shape worth writing when there are two of them."
        )
        lines.append("")
        for r in hand:
            lines.append("- %s (`%s`)" % (r.get("name") or r["product_id"], r["product_id"]))
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_build_types(
    types: Dict[str, BuildType],
    modules: Dict[str, Module],
    archetypes: Iterable[Archetype],
    model=None,
) -> str:
    """The build types catalog: each kind of thing the organization builds,
    its standard parts, the shape that is the type on each provider, and the
    products on it with how far each departs from the standard."""
    shapes = {a.archetype_id: a for a in archetypes}
    ordered = sorted(types.values(), key=lambda t: t.name.lower())

    def products_of(build_type: BuildType) -> List[dict]:
        if model is None:
            return []
        return sorted(
            (r for r in model.all_of("products") if str(r.get("build_type") or "") == build_type.build_type_id),
            key=lambda r: str(r.get("name") or ""),
        )

    lines: List[str] = ["# Build types", ""]
    lines.append(
        "The kinds of thing the organization builds, and the standard build of each: "
        "the parts every build of a kind has, the parts it includes unless there is a "
        "reason not to, the parts it offers as additions, and the shape that is the type "
        "on each provider. A product records its type as `build_type`, and `terrane validate` "
        "lists where it departs from the standard. " + _generated("29_TYPES", ordered)
    )
    lines.append("")
    lines.append("| Type | Requires | Includes | Offers | Shapes | Products |")
    lines.append("|---|---:|---:|---:|---|---:|")
    for build_type in ordered:
        lines.append(
            "| [%s](#%s)%s | %d | %d | %d | %s | %d |"
            % (build_type.name, build_type.build_type_id, _mark(build_type), len(build_type.requires),
               len(build_type.includes), len(build_type.offers),
               ", ".join("%s: `%s`" % (p, sid) for p, sid in sorted(build_type.shapes.items())) or "none",
               len(products_of(build_type)))
        )
    lines.append("")
    for build_type in ordered:
        lines.append('<a id="%s"></a>' % build_type.build_type_id)
        lines.append("## %s" % build_type.name)
        lines.append("")
        lines.append("`%s`" % build_type.build_type_id)
        lines.append("")
        if _origin(build_type):
            lines.append(_origin(build_type))
            lines.append("")
        if build_type.description:
            lines.append(_para(build_type.description))
            lines.append("")
        lines.append("**Requires.** %s." % (", ".join("`%s`" % p for p in build_type.requires) or "nothing"))
        lines.append("**Includes.** %s." % (", ".join("`%s`" % p for p in build_type.includes) or "nothing beyond what it requires"))
        lines.append("**Offers.** %s." % (", ".join("`%s`" % p for p in build_type.offers) or "nothing"))
        if build_type.shapes:
            named = []
            for provider, shape_id in sorted(build_type.shapes.items()):
                shape = shapes.get(shape_id)
                named.append("%s: `%s`%s" % (provider, shape_id, (" (%s)" % shape.title) if shape else ""))
            lines.append("**Shapes.** %s." % ", ".join(named))
        else:
            lines.append("**Shapes.** None: assembled from its parts against the landing zone.")
        products = products_of(build_type)
        if products:
            said = []
            for record in products:
                fit = conformance(build_type, (getattr(model, "parts", {}) or {}).get(str(record.get("product_id")), []), modules)
                notes = []
                notes.extend("without %s" % p for p in fit.missing + fit.dropped)
                notes.extend("with %s" % p for p in fit.unlisted)
                said.append(
                    "%s (`%s`)%s" % (record.get("name") or record.get("product_id"), record.get("product_id"),
                                      (", " + ", ".join(notes)) if notes else "")
                )
            lines.append("**Products.** %s." % "; ".join(said))
        else:
            lines.append("**Products.** None yet.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_connections(kinds, patterns=None, model=None) -> str:
    """The connection kinds, and the interfaces of each read off their own
    fields, with the ones of no kind listed last: those are the finding, a
    connection built unlike anything around it or a kind the library has yet
    to learn."""
    from .connections import sorted_by_kind

    interfaces = model.all_of("interfaces") if model is not None else []
    by_kind, none = sorted_by_kind(interfaces, kinds)
    lines: List[str] = ["# Connection kinds", ""]
    lines.append(
        "The ways two systems are connected here: each kind a recurring shape of "
        "integration style, protocol and authentication, with the pattern that says how "
        "that kind is built. An interface is of a kind when its style is the kind's and its "
        "protocol one of the kind's, read off its own fields, so this counts the estate as it "
        "is whether or not anyone chose a kind. " + _generated("24_CONNECTIONS", kinds.values())
    )
    lines.append("")
    total = len(interfaces)
    matched = total - len(none)
    lines.append(
        "%d of %d interfaces are of a kind; %d of none." % (matched, total, len(none))
        if total else "The model holds no interfaces yet."
    )
    lines.append("")
    lines.append("| Kind | Style | Protocols | Pattern | Interfaces |")
    lines.append("|---|---|---|---|---:|")
    for kind in kinds.values():
        lines.append(
            "| [%s](#%s)%s | %s | %s | %s | %d |"
            % (kind.name, kind.connection_id, _mark(kind), kind.integration_style, ", ".join(kind.protocols),
               ", ".join("`%s`" % p for p in kind.patterns) or "none",
               len(by_kind.get(kind.connection_id, [])))
        )
    lines.append("")

    def said(record) -> str:
        return "%s (`%s`): %s to %s" % (
            record.get("name") or record.get("interface_id"), record.get("interface_id"),
            record.get("source_system_id"), record.get("target_system_id"))

    for kind in kinds.values():
        lines.append('<a id="%s"></a>' % kind.connection_id)
        lines.append("## %s" % kind.name)
        lines.append("")
        lines.append("`%s`" % kind.connection_id)
        lines.append("")
        if _origin(kind):
            lines.append(_origin(kind))
            lines.append("")
        if kind.description:
            lines.append(_para(kind.description))
            lines.append("")
        proposed = kind.defaults()
        lines.append(
            "**Proposed with.** %s." % ", ".join(
                "%s %s" % (key.replace("_", " "), ", ".join(value) if isinstance(value, list) else value)
                for key, value in proposed.items())
        )
        if kind.patterns:
            named = []
            for pattern_id in kind.patterns:
                pattern = (patterns or {}).get(pattern_id)
                named.append("`%s`%s" % (pattern_id, " (%s, %s)" % (pattern.name, pattern.status) if pattern else ""))
            lines.append("**Pattern.** %s." % ", ".join(named))
        found = by_kind.get(kind.connection_id, [])
        if found:
            lines.append("**Interfaces.** %d in the estate:" % len(found))
            lines.append("")
            lines.extend("- %s" % said(r) for r in found)
        else:
            lines.append("**Interfaces.** None yet.")
        lines.append("")
    lines.append("## Of no kind")
    lines.append("")
    if none:
        lines.append(
            "Each of these is either built unlike anything around it, or a kind the library "
            "has yet to learn; several sharing a shape is a kind waiting to be written."
        )
        lines.append("")
        for record in none:
            lines.append("- %s, %s over %s" % (said(record), record.get("integration_style") or "no style",
                                                record.get("protocol") or "no protocol"))
    else:
        lines.append("None.")
    return "\n".join(lines).rstrip() + "\n"
