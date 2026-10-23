"""Shape adoption: which products sit on a shape and how far each has
drifted, and which hand-authored products look like a shape and are not on
one.

Pattern adoption is read off the model because a product carries its
patterns. Shape adoption is not quite that: a product on a shape carries
`archetype`, but everything that makes it differ from the shape -- the
answers it gave, the overrides, the parts it added or dropped, what it chose
in each slot, what it declared under `extra` -- is stripped from the record
when the shape expands, and lives only in the file. So drift is read from
the file, the way the composer wrote it.

A candidate is the other direction: a product nobody put on a shape whose
systems, by category, are the systems a shape's required parts would make.
Card servicing has a channel, an application, a datastore and an event
publisher, which is the Azure digital shape to the part, and it predates
the shape. The finding is not that it is wrong; it is that the shape now
exists and the product is a handful of answers away from being on it.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

from .archetype import Archetype
from .loader import load_folder
from .modules import Module, members_of
from .schema import ENTITY_TYPES


class Drift(NamedTuple):
    """One product on a shape, and everything it says that the shape does not."""

    product_id: str
    name: str
    archetype_id: str
    #: Parameters the product answered that the shape has a default for; the
    #: required ones it had to answer are not drift.
    answered_defaults: Sequence[str]
    #: Entity ids the product overrides fields on.
    overrides: Sequence[str]
    #: Entity type to how many records the product adds under `extra`
    #: (relations counted under "relations").
    extras: Dict[str, int]
    #: Parts the product composes that the shape does not carry by default.
    added: Sequence[str]
    #: Parts the product dropped with `without`.
    dropped: Sequence[str]
    #: Slot name to (chosen option, whether that is the shape's default).
    choices: Dict[str, Tuple[str, bool]]
    #: Ids the shape makes that the product keeps under the estate's names.
    renamed: Sequence[str] = ()

    @property
    def moves(self) -> int:
        """How many ways the product differs from a bare instance of its shape."""
        return (
            len(self.answered_defaults) + len(self.overrides) + sum(self.extras.values())
            + len(self.added) + len(self.dropped) + len(self.renamed)
            + sum(1 for _o, default in self.choices.values() if not default)
        )


class Candidate(NamedTuple):
    """A hand-authored product that a shape's required parts would reproduce."""

    product_id: str
    name: str
    archetype_id: str
    #: (alias, system category) for each required part the product covers.
    covered: Sequence[Tuple[str, str]]
    #: Optional parts of the shape the product has no system for.
    missing_optional: Sequence[Tuple[str, str]]
    #: System categories the product has that no part of the shape makes.
    spare: Sequence[str]


def _provided_label(template: dict) -> str:
    """The token after the slug in a provided system's id: `pipeline` for
    `SYS-{slug|upper}-PIPELINE`, which is how a candidate message names it."""
    raw = str(template.get("system_id") or "")
    return (raw.rsplit("-", 1)[-1] if "-" in raw else raw).lower() or "system"


def part_categories(archetype: Archetype, modules: Dict[str, Module]) -> List[Tuple[str, str, bool]]:
    """(alias, system category, required) for every system a shape's parts
    make by default. Kits are flattened to their members; a part that makes
    no system -- secrets management, monitoring -- has no row, because it
    leaves nothing a hand-authored product could have. A shape built on no
    parts still has a footprint: the systems its own `provides` makes, each
    of them required, since nothing in such a shape is optional."""
    out: List[Tuple[str, str, bool]] = []
    if not archetype.modules:
        for template in archetype.provides.get("systems", []):
            out.append((_provided_label(template), str(template.get("system_category") or ""), True))
        return out
    for entry in archetype.modules:
        module_id = str(entry.get("module"))
        alias = str(entry.get("as") or module_id)
        root = modules.get(module_id)
        if root is None:
            continue
        for member_id in members_of(root, modules):
            member = modules[member_id]
            label = alias if member_id == module_id else member_id
            for template in member.provides.get("systems", []):
                out.append((label, str(template.get("system_category") or ""), not member.optional))
    return out


def raw_instances(model, archetypes: Iterable[Archetype]) -> Dict[str, dict]:
    """Instance id to the record as written, for every entity type a shape
    applies to. The loaded record has had its instance keys stripped; the
    file still has them."""
    out: Dict[str, dict] = {}
    root = Path(getattr(model, "root", "."))
    for folder in sorted({ENTITY_TYPES[a.applies_to].folder for a in archetypes}):
        pk = next(t.pk for t in ENTITY_TYPES.values() if t.folder == folder)
        path = root / "10_MODEL" / folder
        if not path.exists():
            continue
        for _source, data in load_folder(path):
            records = data if isinstance(data, list) else [data]
            for record in records:
                if isinstance(record, dict) and record.get("archetype") and record.get(pk):
                    out[str(record[pk])] = record
    return out


def drift_of(raw: dict, archetype: Archetype, modules: Dict[str, Module]) -> Drift:
    """Everything a product says beyond naming its shape and answering it."""
    pk = ENTITY_TYPES[archetype.applies_to].pk
    given = raw.get("parameters") or {}
    # Answering a default with the default is not a move; rewards saying
    # `region: uksouth` on a shape whose region defaults to uksouth says
    # nothing the shape did not.
    defaults = {p.name: p.default for p in archetype.parameters if not p.required}
    answered = sorted(k for k, v in given.items() if k in defaults and str(v) != str(defaults[k]))
    overrides = sorted(str(k) for k in (raw.get("overrides") or {}))
    extras: Dict[str, int] = {}
    for type_name, records in (raw.get("extra") or {}).items():
        if type_name == "relations":
            extras["relations"] = sum(len(rows or []) for rows in (records or {}).values())
        else:
            extras[str(type_name)] = len(records or [])
    carried = set()
    for entry in archetype.modules:
        module_id = str(entry.get("module"))
        carried.add(str(entry.get("as") or module_id))
        if module_id in modules:
            carried.update(members_of(modules[module_id], modules))
    slot_options = {str(o) for slot in archetype.slots for o in slot.options}
    added = []
    for entry in raw.get("modules") or []:
        module_id = str(entry.get("module") if isinstance(entry, dict) else entry)
        alias = str(entry.get("as") or module_id) if isinstance(entry, dict) else module_id
        # A part listed again to answer it is not an addition; nor is a slot's
        # option, which `choose` accounts for.
        if alias not in carried and module_id not in carried and module_id not in slot_options:
            added.append(alias)
    dropped = sorted(str(x) for x in (raw.get("without") or []))
    chosen = raw.get("choose") or {}
    choices: Dict[str, Tuple[str, bool]] = {}
    for slot in archetype.slots:
        pick = str(chosen.get(slot.name, slot.default or ""))
        choices[slot.name] = (pick, pick == str(slot.default or ""))
    return Drift(
        product_id=str(raw.get(pk)),
        name=str(raw.get("name") or raw.get(pk)),
        archetype_id=archetype.archetype_id,
        answered_defaults=answered,
        overrides=overrides,
        extras=dict(sorted(extras.items())),
        added=added,
        dropped=dropped,
        choices=choices,
        renamed=sorted(str(k) for k in (raw.get("ids") or {})),
    )


def drifts(model, archetypes: Iterable[Archetype], modules: Dict[str, Module]) -> List[Drift]:
    shapes = {a.archetype_id: a for a in archetypes}
    out = []
    for instance_id, raw in sorted(raw_instances(model, shapes.values()).items()):
        archetype = shapes.get(str(raw.get("archetype")))
        if archetype is not None:
            out.append(drift_of(raw, archetype, modules))
    return out


def _product_categories(model) -> Dict[str, Counter]:
    systems = {str(s["system_id"]): s for s in model.all_of("systems")}
    out: Dict[str, Counter] = {}
    for row in model.relation_rows("product_includes_system"):
        system = systems.get(str(row.get("system_id")))
        if system is not None:
            out.setdefault(str(row.get("product_id")), Counter())[
                str(system.get("system_category") or "")
            ] += 1
    return out


def candidates(model, archetypes: Iterable[Archetype], modules: Dict[str, Module]) -> List[Candidate]:
    """Hand-authored products whose systems are, by category, what a shape's
    required parts make. Each product is matched to the shape covering the
    most of it with the fewest systems left over. Two shapes that fit
    equally are told apart by cloud: the digital shapes share their parts
    across AWS, Azure and Google Cloud, and a product whose systems run on
    Azure is a candidate for the Azure one, not for all three. A product two
    shapes of the same cloud fit equally is listed against both."""
    shapes = [a for a in archetypes if a.applies_to == "products" and (a.modules or a.provides.get("systems"))]
    footprints = {a.archetype_id: part_categories(a, modules) for a in shapes}
    provider_of = {a.archetype_id: str(a.provider or "") for a in shapes}
    by_product = _product_categories(model)
    clouds_of = _product_clouds(model)
    out: List[Candidate] = []
    for record in sorted(model.all_of("products"), key=lambda r: str(r["product_id"])):
        if record.get("archetype"):
            continue
        have = by_product.get(str(record["product_id"]))
        if not have:
            continue
        best: List[Candidate] = []
        for archetype in shapes:
            parts = footprints[archetype.archetype_id]
            pool = Counter(have)
            covered, missing_optional, short = [], [], False
            for alias, category, required in sorted(parts, key=lambda p: (not p[2], p[0])):
                if pool.get(category, 0) > 0:
                    pool[category] -= 1
                    covered.append((alias, category))
                elif required:
                    short = True
                    break
                else:
                    missing_optional.append((alias, category))
            if short or not covered:
                continue
            spare = sorted(c for c, n in pool.items() for _ in range(n))
            candidate = Candidate(
                str(record["product_id"]), str(record.get("name") or record["product_id"]),
                archetype.archetype_id, covered, missing_optional, spare,
            )
            # Most covered, then fewest systems left over, then fewest optional
            # parts the product lacks: three systems that are three of the
            # Azure shape's four parts fit it better than three of the AWS
            # shape's seven.
            key = (len(covered), -len(spare), -len(missing_optional))
            fit = lambda c: (len(c.covered), -len(c.spare), -len(c.missing_optional))  # noqa: E731
            if not best or key > fit(best[0]):
                best = [candidate]
            elif key == fit(best[0]):
                best.append(candidate)
        if len(best) > 1:
            clouds = clouds_of.get(str(record["product_id"]), set())
            on_cloud = [c for c in best if provider_of.get(c.archetype_id, "") in clouds]
            if on_cloud:
                best = on_cloud
        out.extend(best)
    return out


def _product_clouds(model) -> Dict[str, set]:
    """The clouds a product's systems run on, by product id."""
    systems = {str(r.get("system_id")): r for r in model.all_of("systems")}
    out: Dict[str, set] = {}
    for row in model.relation_rows("product_includes_system"):
        system = systems.get(str(row.get("system_id")))
        if system is None:
            continue
        cloud = str(system.get("cloud_provider") or system.get("hosting") or "")
        if cloud:
            out.setdefault(str(row.get("product_id")), set()).add(cloud)
    return out
