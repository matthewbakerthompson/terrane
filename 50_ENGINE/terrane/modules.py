"""Modules: the plug-and-play parts an archetype is composed from.

A block is infrastructure that arrives together. An archetype is a whole
product. Between them, most architecture is done at the size of *a part of a
product*: the identity federation into a vendor, the private path out to it,
the return feed that lands in the warehouse, the callback listener for its
webhooks. Each of those is a handful of entities with the relations between
them, and each turns up in most onboardings and in none of them exactly.

A module is that handful, with parameters. An archetype composes modules; an
instance drops the ones that do not apply (`without`) and adds the ones the
shape did not expect (`modules`). That is what makes the diagram for a new
vendor ninety percent chosen rather than drawn: the parts already exist, the
question is which of them this vendor needs.

Two things a part can say about itself beyond what it provides. `needs` is
its contract with the shape: the bindings it reads and does not declare as
parameters of its own, so a shape that cannot supply one is refused when the
library loads rather than when a template fails mid-expansion. And `modules`
makes it a **kit**: a part made of parts, so the four things every vendor
onboarding starts with have one name.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Set

from .library import load_layer
from .schema import ENTITY_TYPES

MODULES_DIR = "28_MODULES"

#: Bindings every template can read without anybody declaring them: the
#: alias the part was composed under, and the loop variables of `each`.
BUILTIN_BINDINGS = frozenset({"alias", "item", "index"})

_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)")


class ModuleError(ValueError):
    """A module is malformed or names something that does not exist."""


class ModuleParameter(NamedTuple):
    name: str
    required: bool = False
    default: Any = None
    description: str = ""
    #: The kind of shared service the parameter stands for -- `api-gateway`,
    #: `secrets-manager` -- as a component type id. A part that says this
    #: never names a cloud: the shape it is composed into binds the kind to
    #: the service that is that kind on its landing zone, the same way it
    #: binds a block's components. Thirteen parts carried `TS-AWS-...` as a
    #: default before this, and a part chosen on the Azure shape bound them.
    component: str = ""
    #: Answered by the estate: `answers` in `model.yaml` holds the value under
    #: the same name, taken ahead of the default when neither the product nor
    #: the shape says. For what a part needs from the estate that is not a
    #: kind of service -- who owns the shared network, where an audit trail
    #: goes, which controls govern a vendor tenancy -- which the parts used to
    #: name as the sample's own records, so a second estate had to hold them.
    estate: bool = False


class Module(NamedTuple):
    module_id: str
    name: str
    category: str
    description: str
    #: Whether an instance may drop it. A vendor tenancy is not optional in
    #: a vendor onboarding; the return feed is.
    optional: bool
    parameters: Sequence[ModuleParameter]
    #: Modules whose entities this one wires to. Dropping one of those while
    #: keeping this one would leave a dangling reference, so it is refused.
    requires: Sequence[str]
    #: Patterns every product with this part applies.
    patterns: Sequence[str]
    provides: Dict[str, List[dict]]
    relations: Dict[str, List[dict]]
    source_file: Optional[Path] = None
    #: What the part reads from the shape's bindings: `slug`, `vendor`,
    #: `owner_org` and the like. Declared rather than discovered, so a shape
    #: that binds no `vendor` is refused with the part's name in the message
    #: instead of "no value bound for template token {vendor}" from inside a
    #: template.
    needs: Sequence[str] = ()
    #: The parts this one is made of, in order, as `modules` entries. A module
    #: with any is a kit; it may provide nothing of its own.
    modules: Sequence[dict] = ()
    #: The library it was read from, "" for the shipped one, and the file it
    #: stands in for when it says `replaces` (`library.load_layer`).
    library: str = ""
    replaced: str = ""

    @property
    def is_kit(self) -> bool:
        return bool(self.modules)


def _listed(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.replace(";", ",").split(",") if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


def module_entries(raw_entries, where) -> List[dict]:
    """Normalize a `modules` list: strings become entries, entries are checked.

    Shared by archetypes, kits and instances, which is what keeps the three
    from accepting three slightly different shapes of the same thing.
    """
    entries: List[dict] = []
    for raw in raw_entries or []:
        if isinstance(raw, str):
            raw = {"module": raw}
        if not isinstance(raw, dict) or not raw.get("module"):
            raise ModuleError("%s: every entry under `modules` names a module" % where)
        if raw.get("with") is not None and not isinstance(raw["with"], dict):
            raise ModuleError(
                "%s: module %s: `with` maps parameter names to values" % (where, raw["module"])
            )
        entries.append(dict(raw))
    return entries


def _tokens_in(value: Any) -> Set[str]:
    """Every `{token}` name anywhere in a structure."""
    found: Set[str] = set()
    if isinstance(value, str):
        found.update(_TOKEN.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            found |= _tokens_in(v)
    elif isinstance(value, list):
        for v in value:
            found |= _tokens_in(v)
    return found


def undeclared_tokens(module: Module) -> Set[str]:
    """Tokens a part's templates read that nothing declares.

    A template under `each` is left out: its bindings include the keys of
    whatever mapping the list holds, which cannot be known here, and the
    composer names the part and the instance if one turns out to be missing.
    Everything else has to come from the part's own parameters, from `needs`,
    or from the builtins, and a token that comes from none of them is either a
    typo or an undeclared dependency on the shape.
    """
    declared = {p.name for p in module.parameters} | set(module.needs) | BUILTIN_BINDINGS
    used: Set[str] = set()
    for templates in module.provides.values():
        for template in templates:
            if "each" in template:
                continue
            used |= _tokens_in(template)
    for rows in module.relations.values():
        for row in rows:
            if "each" in row:
                continue
            used |= _tokens_in(row)
    for param in module.parameters:
        used |= _tokens_in(param.default)
    for entry in module.modules:
        used |= _tokens_in(entry.get("with"))
    return used - declared


def derive_needs(data: dict) -> List[str]:
    """What a part written as data would have to declare under `needs`.

    For the sketch, which rewrites the ids of picked entities into the
    shape's vocabulary -- `SYS-{slug|upper}-EGRESS`, `{product_name}` -- and
    so knows exactly which bindings the part it writes will read. Writing them
    down is what lets the part load, and what lets `terrane validate` refuse a
    shape that cannot supply them.
    """
    names = [
        str(p["name"]) if isinstance(p, dict) else str(p)
        for p in data.get("parameters") or []
    ]
    draft = Module(
        module_id=str(data.get("module_id") or "draft"),
        name="", category="", description="", optional=True,
        parameters=[ModuleParameter(name=n) for n in names],
        requires=(), patterns=(),
        provides={k: list(v or []) for k, v in (data.get("provides") or {}).items()},
        relations={k: list(v or []) for k, v in (data.get("relations") or {}).items()},
        needs=(),
        modules=module_entries(data.get("modules"), data.get("module_id") or "draft"),
    )
    return sorted(undeclared_tokens(draft))


def parse_module(data: dict, source: Optional[Path] = None) -> Module:
    if not isinstance(data, dict) or "module_id" not in data:
        raise ModuleError("%s: missing module_id" % (source or "<module>"))
    module_id = str(data["module_id"])
    where = source or module_id
    params: List[ModuleParameter] = []
    for raw in data.get("parameters") or []:
        if isinstance(raw, str):
            params.append(ModuleParameter(name=raw, required=True))
            continue
        if not isinstance(raw, dict) or "name" not in raw:
            raise ModuleError("%s: each parameter needs a name" % where)
        component = str(raw.get("component") or "")
        params.append(ModuleParameter(
            name=str(raw["name"]),
            # A parameter that names a kind is bound by the shape, not asked
            # of the instance; it is only "required" if nothing binds it, and
            # the composer says so by kind when that happens.
            required=bool(raw.get("required", "default" not in raw and not component)),
            default=raw.get("default"),
            description=str(raw.get("description") or ""),
            component=component,
            estate=bool(raw.get("estate", False)),
        ))
    provides = data.get("provides") or {}
    if not isinstance(provides, dict):
        raise ModuleError("%s: provides must map entity types to templates" % where)
    for entity_type, templates in provides.items():
        if entity_type not in ENTITY_TYPES:
            raise ModuleError("%s: provides unknown entity type %r" % (where, entity_type))
        pk = ENTITY_TYPES[entity_type].pk
        for template in templates or []:
            if not isinstance(template, dict) or not template.get(pk):
                raise ModuleError(
                    "%s: every %s the module provides needs %s" % (where, entity_type, pk)
                )
    members = module_entries(data.get("modules"), where)
    if not provides and not data.get("relations") and not members:
        raise ModuleError(
            "%s: a module that provides nothing, relates nothing and is made of "
            "nothing is not a part" % where
        )
    if not str(data.get("description") or "").strip():
        raise ModuleError("%s: a module needs a description; it is what the form shows" % where)
    needs = _listed(data.get("needs"))
    own = {p.name for p in params}
    for name in needs:
        if name in own:
            raise ModuleError(
                "%s: `needs` lists %r, which is one of the module's own parameters; "
                "a part needs from the shape only what it does not ask for itself"
                % (where, name)
            )
    module = Module(
        module_id=module_id,
        name=str(data.get("name") or module_id),
        category=str(data.get("category") or "Other"),
        description=str(data["description"]).strip(),
        optional=bool(data.get("optional", True)),
        parameters=params,
        requires=_listed(data.get("requires")),
        patterns=_listed(data.get("patterns")),
        provides={k: list(v or []) for k, v in provides.items()},
        relations={k: list(v or []) for k, v in (data.get("relations") or {}).items()},
        source_file=source,
        needs=needs,
        modules=members,
    )
    loose = sorted(undeclared_tokens(module))
    if loose:
        raise ModuleError(
            "%s: reads {%s} and declares none of them; add them to `needs` if they "
            "come from the shape, or to `parameters` if the part asks for them"
            % (where, "}, {".join(loose))
        )
    return module


def _check_kits(modules: Dict[str, Module]) -> None:
    """Every kit names parts that exist, and no kit contains itself.

    A cycle would not fail loudly on its own -- the composer would recurse
    until Python stopped it -- so it is caught here, with the path named.
    """
    def walk(module_id: str, trail: List[str]) -> None:
        module = modules[module_id]
        for entry in module.modules:
            member = str(entry["module"])
            if member not in modules:
                raise ModuleError(
                    "kit %s is made of %r, which is not in %s"
                    % (module_id, member, MODULES_DIR)
                )
            if member in trail or member == module_id:
                raise ModuleError(
                    "kit %s contains itself: %s"
                    % (trail[0], " > ".join(trail + [member]))
                )
            walk(member, trail + [member])

    for module_id, module in modules.items():
        if module.is_kit:
            walk(module_id, [module_id])


def load_modules(root: Path) -> Dict[str, Module]:
    out: Dict[str, Module] = load_layer(
        root, MODULES_DIR, parse_module, lambda m: m.module_id, "module", ModuleError
    )
    for module in out.values():
        for needed in module.requires:
            if needed not in out:
                raise ModuleError(
                    "module %s requires %r, which is not in %s"
                    % (module.module_id, needed, MODULES_DIR)
                )
    _check_kits(out)
    return out


def members_of(module: Module, modules: Dict[str, Module]) -> List[str]:
    """The leaf parts a module stands for: itself, or a kit's members, all the
    way down, in composition order."""
    if not module.is_kit:
        return [module.module_id]
    out: List[str] = []
    for entry in module.modules:
        out.extend(members_of(modules[str(entry["module"])], modules))
    return out


def provided_count(module: Module, modules: Optional[Dict[str, Module]] = None) -> int:
    """How many entities the part creates. A kit counts what its members do."""
    if module.is_kit and modules is not None:
        return sum(
            provided_count(modules[m], modules)
            for m in members_of(module, modules)
        )
    return sum(len(v) for v in module.provides.values())


def uses_of(modules: Dict[str, Module], archetypes: Iterable[Any]) -> Dict[str, List[str]]:
    """Where each part is composed: by which shapes, directly, through a slot
    or through a kit, and by which kits.

    The reverse index the library did not have. Eight parts were composed by
    nothing when this was written, and the library could not say so.
    """
    used: Dict[str, List[str]] = {m: [] for m in modules}

    def note(module_id: str, by: str) -> None:
        if module_id in used and by not in used[module_id]:
            used[module_id].append(by)

    for kit in modules.values():
        for entry in kit.modules:
            note(str(entry["module"]), "kit %s" % kit.module_id)
    for archetype in archetypes:
        title = getattr(archetype, "title", None) or getattr(archetype, "archetype_id", "?")
        for entry in getattr(archetype, "modules", ()):
            module_id = str(entry.get("module"))
            note(module_id, title)
            if module_id in modules:
                for member in members_of(modules[module_id], modules):
                    note(member, title)
        for slot in getattr(archetype, "slots", ()):
            for option in slot.options:
                note(str(option), "%s (slot %s)" % (title, slot.name))
                if option in modules:
                    for member in members_of(modules[option], modules):
                        note(member, "%s (slot %s)" % (title, slot.name))
    return used
