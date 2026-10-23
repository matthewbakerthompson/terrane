"""The assembled model: entities, relations, and the indexes views run against."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .build_types import module_ids_of
from .archetype import Archetype, ArchetypeError, expand, landing_zone_index, load_archetypes
from .blocks import LibraryError, load_blocks, load_components
from .answers import EstateError, estate_answers
from .loader import ModelFileError, load_folder, read_data_file
from .modules import ModuleError, load_modules
from .schema import ENTITY_TYPES, FIELD_ALIASES, RELATION_TYPES, EntityType

MODEL_CONFIG = "model.yaml"


class ModelError(ValueError):
    """The model could not be assembled."""


def _normalize(record: dict, entity_type: EntityType, source: Path) -> dict:
    out: Dict[str, Any] = {}
    aliases = FIELD_ALIASES.get(entity_type.name, {})
    for key, value in record.items():
        out[aliases.get(key, key)] = value
    out["_type"] = entity_type.name
    out["_source_file"] = str(source)
    if not out.get(entity_type.pk):
        raise ModelFileError(source, "record is missing %s" % entity_type.pk)
    return out


def _list_field(raw) -> List[str]:
    """A list-valued field, whether written as a list or as a `;` string.

    Both forms are accepted because both arrive: a hand-written file says
    `[a, b]`, and a CSV import says `a;b`.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        return [t.strip() for t in raw.replace(";", ",").split(",") if t.strip()]
    return [str(t).strip() for t in raw if str(t).strip()]


def _tags_of(record: dict) -> List[str]:
    return _list_field(record.get("tags"))


class Model:
    """Every entity and relation, with the lookups the renderers need."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.config: Dict[str, Any] = {}
        self.entities: Dict[str, Dict[str, dict]] = {n: {} for n in ENTITY_TYPES}
        self.relations: Dict[str, List[dict]] = {n: [] for n in RELATION_TYPES}
        self.archetypes: Dict[str, Archetype] = {}
        #: The shapes of one behind products assembled from parts with no
        #: shape file: built from each product's `compose` block as it loads,
        #: keyed by `compose:<id>`. Kept apart from `archetypes` so the New
        #: form and the catalog do not offer them as shapes to build on.
        self.composed: Dict[str, Archetype] = {}
        #: Instance id to the parts it ended up with, by module id, for every
        #: product on a shape or assembled from parts. A build type is held
        #: to a product through this; nothing else kept the list after the
        #: expansion was folded into the entities.
        self.parts: Dict[str, List[str]] = {}
        self.warnings: List[str] = []
        #: Lazily built by `_adjacency`; anything that mutates the model after
        #: load must clear it.
        self._adjacent: Optional[Dict[str, Set[str]]] = None

    # -- lookups -------------------------------------------------------

    def get(self, entity_type: str, entity_id: str) -> Optional[dict]:
        return self.entities.get(entity_type, {}).get(entity_id)

    def all_of(self, entity_type: str) -> List[dict]:
        return list(self.entities.get(entity_type, {}).values())

    def find(self, entity_id: str) -> Optional[Tuple[str, dict]]:
        """Locate an entity by id across every type. Ids are globally unique."""
        for type_name, records in self.entities.items():
            if entity_id in records:
                return type_name, records[entity_id]
        return None

    def tags(self, record: dict) -> List[str]:
        return _tags_of(record)

    def list_of(self, record: dict, field: str) -> List[str]:
        """Any list-valued field on a record, in either form it is written in."""
        return _list_field(record.get(field))

    def relation_rows(self, name: str) -> List[dict]:
        return self.relations.get(name, [])

    def _adjacency(self) -> Dict[str, Set[str]]:
        """Undirected adjacency over every relation and every reference field.

        Built once and cached. It used to walk the relations on each call and
        skip reference fields entirely, which meant an org unit had no
        neighbors at all -- its only link to anything is the `owner_org_id` on
        the records it owns -- and a data asset was never reachable from the
        system that masters it.
        """
        if self._adjacent is not None:
            return self._adjacent

        graph: Dict[str, Set[str]] = {}

        def join(a: object, b: object) -> None:
            if not a or not b or a == b:
                return
            graph.setdefault(str(a), set()).add(str(b))
            graph.setdefault(str(b), set()).add(str(a))

        for name, rows in self.relations.items():
            spec = RELATION_TYPES[name]
            for row in rows:
                join(row.get(spec.left_column), row.get(spec.right_column))

        for type_name, entity_type in ENTITY_TYPES.items():
            refs = [f.name for f in entity_type.fields if f.ref]
            if not refs:
                continue
            for record in self.entities.get(type_name, {}).values():
                own = record.get(entity_type.pk)
                for field in refs:
                    join(own, record.get(field))

        # Two systems either end of an interface are adjacent to each other as
        # well as to the interface, because the question "what does this talk
        # to" is asked about systems far more often than about interfaces.
        for record in self.entities.get("interfaces", {}).values():
            join(record.get("source_system_id"), record.get("target_system_id"))

        self._adjacent = graph
        return graph

    def neighbors(self, entity_id: str) -> Set[str]:
        """Ids directly connected to `entity_id` by any relation or FK."""
        return set(self._adjacency().get(entity_id, ()))

    def counts(self) -> Dict[str, int]:
        counts = {name: len(records) for name, records in self.entities.items() if records}
        counts.update(
            {name: len(rows) for name, rows in self.relations.items() if rows}
        )
        return counts

    # -- assembly ------------------------------------------------------

    def _add_entity(self, entity_type: EntityType, record: dict, source: Path) -> None:
        record = _normalize(record, entity_type, source)
        entity_id = str(record[entity_type.pk])
        existing = self.entities[entity_type.name].get(entity_id)
        if existing is not None:
            raise ModelError(
                "duplicate %s %r defined in %s and %s"
                % (entity_type.label, entity_id, existing["_source_file"], source)
            )
        clash = self.find(entity_id)
        if clash is not None:
            raise ModelError(
                "id %r is used by both a %s and a %s; ids must be unique across types"
                % (entity_id, clash[0], entity_type.name)
            )
        self.entities[entity_type.name][entity_id] = record
        self._adjacent = None

    def _add_relation(self, name: str, row: dict, source: str) -> None:
        if name not in RELATION_TYPES:
            raise ModelError("%s: unknown relation %r" % (source, name))
        spec = RELATION_TYPES[name]
        for column in (spec.left_column, spec.right_column):
            if not row.get(column):
                raise ModelError(
                    "%s: relation %s row is missing %s" % (source, name, column)
                )
        row = dict(row)
        row.setdefault("_source", source)
        key = (
            str(row[spec.left_column]),
            str(row[spec.right_column]),
            str(row.get(spec.qualifier, "")) if spec.qualifier else "",
        )
        for existing in self.relations[name]:
            existing_key = (
                str(existing[spec.left_column]),
                str(existing[spec.right_column]),
                str(existing.get(spec.qualifier, "")) if spec.qualifier else "",
            )
            if existing_key == key:
                self.warnings.append(
                    "duplicate %s row %s dropped (%s)" % (name, key, source)
                )
                return
        self.relations[name].append(row)
        self._adjacent = None


def load(root: Path) -> Model:
    """Read a model repository into memory, expanding archetypes on the way."""
    root = Path(root)
    model = Model(root)

    config_path = root / "10_MODEL" / MODEL_CONFIG
    if config_path.exists():
        model.config = read_data_file(config_path) or {}

    model.archetypes = load_archetypes(root)

    # The component library, for the archetypes built on blocks. A library
    # that does not load is reported rather than fatal: a model whose shapes
    # never touch a block should still open, and `terrane validate` says what is
    # wrong with the library either way.
    library = None
    try:
        components = load_components(root)
        library = (components, load_blocks(root, components), load_modules(root))
    except (LibraryError, ModuleError) as exc:
        model.warnings.append("component library not loaded: %s" % exc)

    model_dir = root / "10_MODEL"
    deferred: List[Tuple[EntityType, dict, Path]] = []

    for entity_type in ENTITY_TYPES.values():
        folder = model_dir / entity_type.folder
        for source, record in load_folder(folder):
            if not isinstance(record, dict):
                raise ModelFileError(source, "expected a mapping")
            if record.get("archetype") or record.get("compose"):
                deferred.append((entity_type, record, source))
            else:
                model._add_entity(entity_type, record, source)

    # The landing zone a part's kinds resolve against: the shared services,
    # which are plain entities and so are all loaded by now. A service a
    # shape creates for one product is never in it.
    # And what the estate answers for the parameters that ask it, from
    # `answers` in model.yaml (terrane/answers.py).
    if library is not None:
        try:
            answers = estate_answers(model.config)
        except EstateError as exc:
            raise ModelError("%s: %s" % (config_path, exc))
        library = library + (landing_zone_index(model.all_of("tech_services")), answers)

    # Archetype instances are expanded after plain entities so that overrides
    # and exclusions are reported against a complete picture.
    # A late import: compose reaches this module through the sketch writer,
    # and at call time both are whole.
    from .compose import ComposeError, inline_shape

    for entity_type, record, source in deferred:
        if record.get("compose"):
            # Assembled from parts, with no shape: the shape of one is built
            # from the product's own `compose` block, then expanded like any
            # other. A bad block fails here, by file and by name.
            try:
                archetype = inline_shape(root, record, entity_type.name, model.archetypes.values())
            except (ComposeError, ArchetypeError, ModuleError, LibraryError) as exc:
                raise ModelError("%s: %s" % (source, exc))
            model.composed[archetype.archetype_id] = archetype
        else:
            archetype_id = record["archetype"]
            archetype = model.archetypes.get(archetype_id)
        if archetype is None:
            raise ModelError(
                "%s: unknown archetype %r (available: %s)"
                % (source, record.get("archetype"), ", ".join(sorted(model.archetypes)) or "none")
            )
        if archetype.applies_to != entity_type.name:
            raise ModelError(
                "%s: archetype %s applies to %s, not %s"
                % (source, archetype_id, archetype.applies_to, entity_type.name)
            )
        expansion = expand(record, archetype, entity_type.name, library)
        model.parts[str(record[entity_type.pk])] = module_ids_of(expansion.modules_applied, archetype, record)
        model._add_entity(entity_type, expansion.instance, source)
        for type_name, records in expansion.entities.items():
            for produced in records:
                model._add_entity(ENTITY_TYPES[type_name], produced, source)
        for relation_name, rows in expansion.relations.items():
            for row in rows:
                model._add_relation(relation_name, row, str(source))
        # A dependent of a dependent pointed at something that went, not at
        # something excluded, so it names the exclusion it traces back to.
        # Each is said to go for what went in an earlier wave, so the trail
        # ends.
        went_with = dict(expansion.dropped_dependents)
        for dropped_id, because in expansion.dropped_dependents:
            origin = because
            while origin in went_with:
                origin = went_with[origin]
            if origin == because:
                model.warnings.append(
                    "%s: %s dropped because it referenced excluded %s"
                    % (record[entity_type.pk], dropped_id, because)
                )
            else:
                model.warnings.append(
                    "%s: %s dropped because it referenced %s, which went with excluded %s"
                    % (record[entity_type.pk], dropped_id, because, origin)
                )

    for source, data in load_folder(model_dir / "relations"):
        if not isinstance(data, dict):
            raise ModelFileError(source, "expected a mapping of relation name to rows")
        for relation_name, rows in data.items():
            if relation_name.startswith("_"):
                continue
            for row in rows or []:
                model._add_relation(relation_name, row, str(source))

    return model


def iter_entities(model: Model, types: Optional[Iterable[str]] = None) -> Iterable[dict]:
    for type_name in types or ENTITY_TYPES:
        for record in model.all_of(type_name):
            yield record
