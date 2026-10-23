"""Build types: the kinds of thing the organization builds, and the standard
build of each.

A shape is one provider's answer to "what does a digital product look like".
A build type is the question, asked once, whoever hosts the product: the parts
every build of its kind has, the parts it includes unless there is a reason
not to, and the parts it offers as additions. The Assemble panel starts from a
type, and `terrane validate` says where a product departs from its standard. A
deviation is not an error; it is what a design review should see without
having to ask.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

from .library import load_layer
from .modules import Module, members_of

TYPES_DIR = "29_TYPES"

#: The key under `shapes` for a shape that lands on no cloud of its own.
ANY_PROVIDER = "any"


class BuildTypeError(ValueError):
    """A build type is malformed or names something that does not exist."""


class BuildType(NamedTuple):
    build_type_id: str
    name: str
    description: str
    #: Parts every build of this kind has. Locked in the panel; missing on a
    #: product is a finding.
    requires: Tuple[str, ...]
    #: Parts a build of this kind has unless there is a reason not to. Ticked
    #: in the panel; dropped on a product is a deviation.
    includes: Tuple[str, ...]
    #: Parts a build of this kind may add. Offered in the panel; a part not
    #: listed anywhere on the type is a deviation.
    offers: Tuple[str, ...]
    #: Provider to the shape that is this type there; `any` for a shape on
    #: no cloud.
    shapes: Dict[str, str]
    source_file: Optional[Path] = None
    library: str = ""
    replaced: str = ""

    @property
    def listed(self) -> Tuple[str, ...]:
        return self.requires + self.includes + self.offers


def _listed(value: Any) -> Tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return tuple(x.strip() for x in value.replace(";", ",").split(",") if x.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(x).strip() for x in value if str(x).strip())
    raise BuildTypeError("expected a list of part ids, got %r" % (value,))


def parse_build_type(data: dict, source: Optional[Path] = None) -> BuildType:
    if not isinstance(data, dict):
        raise BuildTypeError("%s: a build type is a mapping" % source)
    type_id = str(data.get("build_type_id") or "").strip()
    if not type_id:
        raise BuildTypeError("%s: a build type needs a build_type_id" % source)
    name = str(data.get("name") or "").strip()
    if not name:
        raise BuildTypeError("build type %s needs a name" % type_id)
    shapes_raw = data.get("shapes") or {}
    if not isinstance(shapes_raw, dict):
        raise BuildTypeError("build type %s: shapes is a mapping of provider to shape" % type_id)
    shapes = {str(k): str(v).strip() for k, v in shapes_raw.items() if str(v).strip()}
    return BuildType(
        build_type_id=type_id,
        name=name,
        description=str(data.get("description") or "").strip(),
        requires=_listed(data.get("requires")),
        includes=_listed(data.get("includes")),
        offers=_listed(data.get("offers")),
        shapes=shapes,
        source_file=source,
    )


def load_build_types(root: Path) -> Dict[str, BuildType]:
    """Every build type under `29_TYPES/`, the organization's after the
    shipped ones. A repository without the folder has no types, and nothing
    below cares."""
    return load_layer(
        root, TYPES_DIR, parse_build_type, lambda t: t.build_type_id, "build type", BuildTypeError
    )


def shape_for(build_type: BuildType, provider: str) -> str:
    """The shape that is this type on a provider, or the one for no cloud,
    or nothing: then the type is assembled from its parts."""
    return build_type.shapes.get(provider or "", "") or build_type.shapes.get(ANY_PROVIDER, "")


def _composed_by(archetype, modules: Dict[str, Module]) -> set:
    """Every part a shape composes, by id, kits flattened, and every part
    that can fill one of its slots."""
    out: set = set()
    for entry in getattr(archetype, "modules", ()):
        module_id = str(entry.get("module"))
        out.add(module_id)
        if module_id in modules:
            out.update(members_of(modules[module_id], modules))
    for slot in getattr(archetype, "slots", ()):
        for option in slot.options:
            out.add(str(option))
            if str(option) in modules:
                out.update(members_of(modules[str(option)], modules))
    return out


def check_build_types(
    types: Dict[str, BuildType], modules: Dict[str, Module], archetypes: Iterable[Any]
) -> List[Tuple[str, str]]:
    """What is wrong with the library's types, as (problem, where) pairs: a
    part that is not in the library, a part listed twice, a shape that does
    not exist or is on another provider, a shape that does not compose a part
    the type requires."""
    shapes = {a.archetype_id: a for a in archetypes}
    problems: List[Tuple[str, str]] = []
    for build_type in types.values():
        where = str(build_type.source_file or "")
        seen: Dict[str, str] = {}
        for role, parts in (("requires", build_type.requires), ("includes", build_type.includes),
                            ("offers", build_type.offers)):
            for part in parts:
                if part not in modules:
                    problems.append((
                        "build type %s %s %r, which is not in 28_MODULES" % (build_type.build_type_id, role, part), where))
                if part in seen:
                    problems.append((
                        "build type %s lists %s under %s and %s; a part is one or the other"
                        % (build_type.build_type_id, part, seen[part], role), where))
                seen[part] = role
        for provider, shape_id in build_type.shapes.items():
            shape = shapes.get(shape_id)
            if shape is None:
                problems.append((
                    "build type %s names shape %r for %s, which is not in 20_ARCHETYPES"
                    % (build_type.build_type_id, shape_id, provider), where))
                continue
            if getattr(shape, "applies_to", "products") != "products":
                problems.append((
                    "build type %s names shape %s, which applies to %s, not products"
                    % (build_type.build_type_id, shape_id, shape.applies_to), where))
            shape_provider = str(getattr(shape, "provider", "") or "")
            if provider == ANY_PROVIDER:
                if shape_provider:
                    problems.append((
                        "build type %s names shape %s for any provider, but the shape is on %s"
                        % (build_type.build_type_id, shape_id, shape_provider), where))
            elif shape_provider != provider:
                problems.append((
                    "build type %s names shape %s for %s, but the shape is on %s"
                    % (build_type.build_type_id, shape_id, provider, shape_provider or "no cloud"), where))
            composed = _composed_by(shape, modules)
            for part in build_type.requires:
                if part not in composed:
                    problems.append((
                        "build type %s requires %s, which shape %s does not compose"
                        % (build_type.build_type_id, part, shape_id), where))
    return problems


def uses_by_build_types(
    used: Dict[str, List[str]], types: Dict[str, BuildType], modules: Dict[str, Module]
) -> None:
    """Add the build types to `used`, the part -> users map `uses_of` builds.

    A part a build type requires, includes or offers is used by that type,
    and so is every member of a kit it lists: the application parts live on
    their types' menus until a product picks them, and a part on a menu is
    neither waiting for its shape nor forgotten.
    """
    for build_type in types.values():
        label = "type %s" % build_type.name
        for part in build_type.listed:
            members = [part]
            if part in modules and modules[part].is_kit:
                members.extend(members_of(modules[part], modules))
            for member in members:
                if member in used and label not in used[member]:
                    used[member].append(label)


def module_ids_of(applied: Sequence[str], archetype, instance: dict) -> List[str]:
    """The parts a product ended up with, by module id. An expansion lists
    the aliases it applied; an alias is the part's own id unless the shape or
    the instance composed the part under another name."""
    by_alias: Dict[str, str] = {}
    entries = list(getattr(archetype, "modules", ()) or ())
    for entry in list((instance or {}).get("modules") or ()) + list(((instance or {}).get("compose") or {}).get("modules") or ()):
        if isinstance(entry, dict):
            entries.append(entry)
        elif entry:
            entries.append({"module": entry})
    for entry in entries:
        module_id = str(entry.get("module") or "")
        alias = str(entry.get("as") or module_id)
        if module_id:
            by_alias[alias] = module_id
    out: List[str] = []
    for alias in applied:
        module_id = by_alias.get(str(alias), str(alias))
        if module_id not in out:
            out.append(module_id)
    return out


class Conformance(NamedTuple):
    #: Required parts the product does not have.
    missing: List[str]
    #: Included parts the product does without.
    dropped: List[str]
    #: Parts the product has that the type neither requires, includes nor offers.
    unlisted: List[str]

    @property
    def clean(self) -> bool:
        return not (self.missing or self.dropped or self.unlisted)


def conformance(build_type: BuildType, parts: Sequence[str], modules: Dict[str, Module]) -> Conformance:
    """How a product's parts compare with its type's standard. A kit counts
    as present when every member is; a member of a listed kit counts as
    listed."""
    have = set(parts)

    def present(part: str) -> bool:
        module = modules.get(part)
        if module is not None and module.is_kit:
            return all(member in have for member in members_of(module, modules))
        return part in have

    listed: set = set()
    for part in build_type.listed:
        listed.add(part)
        module = modules.get(part)
        if module is not None:
            listed.update(members_of(module, modules))
    return Conformance(
        missing=[p for p in build_type.requires if not present(p)],
        dropped=[p for p in build_type.includes if not present(p)],
        unlisted=sorted(p for p in have if p not in listed),
    )
