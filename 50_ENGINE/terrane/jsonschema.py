"""JSON Schema generation from the entity definitions.

Generated rather than hand-written so the schemas cannot drift from what the
engine actually enforces. Their job is editor support: point the YAML language
server at them and an author gets field completion and enum checking while
typing, instead of finding out at `terrane validate` time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .archetype import Archetype
from .query import VIEW_KINDS
from .schema import ENTITY_TYPES, RELATION_TYPES, EntityType

SCHEMA_VERSION = "https://json-schema.org/draft/2020-12/schema"
ID_PATTERN = "^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$"

#: Any library record may stand in for one read before it, in a library
#: `model.yaml` names under `library_paths` (`library.load_layer`).
_REPLACES = {
    "type": "string",
    "description": "This record's own id, said to stand in for the record of that id in a "
                   "library read before this one. Without it a second record of an id is an error.",
}


def _field_schema(field) -> dict:
    if field.enum:
        return {"enum": list(field.enum)}
    if field.name in ("tags", "patterns", "answers_for"):
        return {
            "oneOf": [
                {"type": "array", "items": {"type": "string"}},
                {"type": "string"},
            ]
        }
    if field.name in ("maturity_level", "maturity_rating"):
        return {"type": "integer", "minimum": 0, "maximum": 5}
    if field.ref:
        return {"type": "string", "pattern": ID_PATTERN}
    return {"type": ["string", "number", "boolean", "null"]}


def entity_schema(entity_type: EntityType) -> dict:
    properties: Dict[str, dict] = {
        entity_type.pk: {"type": "string", "pattern": ID_PATTERN}
    }
    for field in entity_type.fields:
        properties[field.name] = _field_schema(field)

    # Archetype instances carry expansion keys instead of a full field set.
    properties.update(
        {
            "archetype": {"type": "string"},
            "parameters": {"type": "object"},
            "overrides": {"type": "object"},
            "exclude": {"type": "array", "items": {"type": "string"}},
            "without": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Parts of the shape this instance does without, by alias.",
            },
            "modules": {
                "type": "array",
                "items": _MODULE_ENTRY,
                "description": "Parts added to the shape, or re-bound, by this instance.",
            },
            "choose": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Slot name to the option this instance chooses, or `none` for an optional slot.",
            },
            "ids": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "An id the shape makes to the id the estate already uses for it, so a product "
                               "moves onto a shape without renaming what points at it.",
            },
            "extra": {"type": "object"},
            "compose": {
                "type": "object",
                "additionalProperties": False,
                "required": ["modules"],
                "description": (
                    "Assembled from parts with no shape: the parts under `modules`, the "
                    "provider they resolve against, and the blocks, binds, patterns and "
                    "relations a shape would carry. Not with `archetype`."
                ),
                "properties": {
                    "provider": {"type": "string"},
                    "title": {"type": "string"},
                    "modules": {"type": "array", "items": _MODULE_ENTRY},
                    "blocks": {"type": "array"},
                    "bind": {"type": "object", "additionalProperties": {"type": "string"}},
                    "patterns": {"type": "array", "items": {"type": "string"}},
                    "relations": {"type": "object"},
                },
            },
        }
    )

    record = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": [entity_type.pk],
    }
    return {
        "$schema": SCHEMA_VERSION,
        "$id": "https://architecture-as-code/schemas/%s.schema.json" % entity_type.name,
        "title": entity_type.label.title(),
        "description": "A %s, or a list of them in one file." % entity_type.label,
        "oneOf": [record, {"type": "array", "items": record}],
    }


def relations_schema() -> dict:
    properties: Dict[str, dict] = {}
    for name, spec in RELATION_TYPES.items():
        row_props = {
            spec.left_column: {"type": "string", "pattern": ID_PATTERN},
            spec.right_column: {"type": "string", "pattern": ID_PATTERN},
        }
        required = [spec.left_column, spec.right_column]
        if spec.qualifier:
            row_props[spec.qualifier] = {"type": "string"}
        properties[name] = {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": row_props,
                "required": required,
            },
        }
    return {
        "$schema": SCHEMA_VERSION,
        "$id": "https://architecture-as-code/schemas/relations.schema.json",
        "title": "Relations",
        "description": "A mapping of relation name to rows.",
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }


def _annotations_schema() -> dict:
    """What a diagram draws of its own, as `terrane.annotations.read` takes
    it; that reader is the authority, and says which frame a key misses."""
    from .annotations import ENDS, FILLS, OUTLINES, ROLES, ROUTES, SHAPES, TEXT_SIZES

    pair = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
    end = {"oneOf": [{"type": "string", "description": "A record on the drawing by id, or a key of this list."},
                     dict(pair, description="A point on the sheet.")]}
    return {
        "type": "array",
        "description": "Shapes, text, notes, frames and free lines the diagram draws of its own, none of them "
                       "records. Each has a key that never changes; a box its corner `at` in the innermost "
                       "frame of `in`, or on the sheet, and its `size`; a line its two ends.",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["key", "role"],
            "properties": {
                "key": {"type": "string"},
                "role": {"enum": list(ROLES)},
                "label": {"type": "string", "description": "Its words."},
                "shape": {"enum": list(SHAPES)},
                "in": {"type": "array", "items": {"type": "string"},
                       "description": "The keys of the frames it sits in, outermost first."},
                "at": dict(pair, description="Its top-left corner in the frame around it, or on the sheet."),
                "size": dict(pair, description="[width, height]."),
                "from": end,
                "to": end,
                "ends": {"enum": list(ENDS)},
                "route": {"enum": list(ROUTES)},
                "look": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "fill": {"enum": sorted(FILLS)},
                        "line": {"enum": list(OUTLINES)},
                        "text": {"enum": sorted(TEXT_SIZES)},
                    },
                },
            },
        },
    }


def view_schema() -> dict:
    where = {
        "type": "object",
        "description": (
            "Field to value or list of values. Also tags_any, tags_all, tags_none, "
            "has_any, has_all, has_none (relation names, testing whether the relation "
            "exists at all), id_in, id_prefix, and the {not: [...]} / {exists: true} "
            "forms."
        ),
    }
    clause = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "type": {"enum": sorted(ENTITY_TYPES)},
            "where": where,
        },
        "required": ["type"],
    }
    return {
        "$schema": SCHEMA_VERSION,
        "$id": "https://architecture-as-code/schemas/view.schema.json",
        "title": "View",
        "type": "object",
        "additionalProperties": False,
        "required": ["view_id"],
        # What it draws: a query, things pinned to it, or views placed on it
        # as boundaries (a diagram drawn on the canvas may be only those, or
        # only shapes of its own).
        "anyOf": [{"required": ["scope"]}, {"required": ["places"]}, {"required": ["annotations"]}],
        "properties": {
            "view_id": {"type": "string"},
            "replaces": {
                "type": "string",
                "description": "In an estate reading the shipped views from the installed terrane: this view "
                               "stands in for the shipped view of the same id.",
            },
            "places": {
                "type": "array",
                "description": "Views placed on this one as boundaries, read as they are now whenever views "
                               "are loaded, so the diagram stays in step with them. Each brings its scope, its "
                               "lines and, unless this view groups by something of its own, its boundaries.",
                "items": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["view"],
                            "properties": {
                                "view": {"type": "string", "description": "The id of the view placed."},
                                "only": {
                                    "type": "object",
                                    "description": "Field to the values kept: the rest of the placed view is "
                                                   "left off this diagram.",
                                },
                                "leave_out": {
                                    "type": "object",
                                    "description": "Field to the values left off this diagram; they stay in "
                                                   "the placed view.",
                                },
                                "parts": {
                                    "type": "boolean",
                                    "description": "false keeps the placed view's boundaries without its own "
                                                   "boxes, so only what is placed inside them is drawn.",
                                },
                            },
                        },
                    ],
                },
            },
            "annotations": _annotations_schema(),
            "positions": {
                "type": "object",
                "description": "Where each thing was put by hand on the canvas: a box keyed by the boundaries it "
                               "sits in and its id, joined by ' / ', a boundary by its path, each to its top-left "
                               "corner [x, y] in the boundary around it. A drawing with positions is arranged by "
                               "hand: the layout places only what has none.",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2,
                },
            },
            "title": {"type": "string"},
            "description": {"type": "string"},
            "category": {"type": "string", "description": "The layer the view is listed under: Business, "
                                                         "Application, Data, Technology, Governance, Change."},
            "section": {"type": "string", "description": "The heading it sits under within its layer."},
            "kind": {"enum": list(VIEW_KINDS)},
            "parameters": {
                "type": "array",
                "description": "What the view must be told before it can be drawn: a subject it is about.",
                "items": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"enum": sorted(ENTITY_TYPES)},
                                "field": {
                                    "type": "string",
                                    "description": "For a subject that is a value on the records rather than a "
                                                   "record: the field it is a value of (a business domain is a "
                                                   "value of company_domain). Instead of type.",
                                },
                                "required": {"type": "boolean"},
                                "default": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                    ],
                },
            },
            "render_for": {
                "type": "object",
                "description": "Which subjects the view is drawn for when every view is rendered.",
                "properties": {
                    "type": {"enum": sorted(ENTITY_TYPES)},
                    "where": where,
                    "parameter": {"type": "string", "description": "The parameter each subject binds."},
                    "field": {
                        "type": "string",
                        "description": "Drawn once for each value this field takes on the selected records, "
                                       "rather than once per record.",
                    },
                    "limit": {"type": "integer"},
                },
                "required": ["type"],
            },
            "up": {
                "type": "string",
                "description": "For a view about one thing: the view one level above it, drawn for what the "
                               "subject sits in. A system's architecture goes up to its domain's landscape.",
            },
            "order_by": {"type": "string"},
            "group_direction": {"enum": ["LR", "RL", "TB", "BT", "lr", "rl", "tb", "bt"]},
            # A direction for a layered drawing, or a layout that is not
            # layered at all: a hub is a wheel, a neighborhood is organic.
            "layout": {"enum": ["LR", "RL", "TB", "BT", "concentric", "cose", "grid"]},
            "group_by": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ],
                "description": "One field, or a list for nested boundaries.",
            },
            "node_label": {"type": "string"},
            "lanes": {
                "oneOf": [
                    {"type": "boolean", "enum": [False]},
                    {"type": "array", "items": {"type": "string"}},
                    {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}}},
                ],
                "description": "The order the grouped values are laid out in: a list for the innermost "
                               "group_by field, a mapping of field to values, or false to leave the fields' "
                               "own enumerations aside.",
            },
            "renderers": {
                "type": "array",
                "items": {"enum": ["mermaid", "structurizr"]},
            },
            "scope": {
                "type": "object",
                "additionalProperties": False,
                "anyOf": [{"required": ["include"]}, {"required": ["pin"]}],
                "properties": {
                    "include": {"type": "array", "items": clause, "minItems": 1},
                    "exclude": {"type": "array", "items": clause},
                    "pin": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Ids kept on this drawing whatever the query finds. One thing "
                            "each, not a seed for `expand`; kept first when the drawing is "
                            "cut to max_nodes."
                        ),
                    },
                    "hide": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ids left off this drawing, applied last; a hide beats a pin.",
                    },
                    "expand": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "relation": {"type": "string"},
                                "depth": {"type": "integer", "minimum": 0},
                                "types": {
                                    "type": "array",
                                    "items": {"enum": sorted(ENTITY_TYPES)},
                                },
                            },
                        },
                    },
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "via": {
                            "enum": sorted(
                                set(RELATION_TYPES)
                                | {"interfaces", "source_of_truth", "owner"}
                                # Any reference field draws as an edge too.
                                | {
                                    f.name
                                    for e in ENTITY_TYPES.values()
                                    for f in e.fields
                                    if f.ref
                                }
                            )
                        },
                        "label": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["via"],
                },
            },
            "style": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "color_by": {"type": "string"},
                    "marks": {
                        "enum": sorted(RELATION_TYPES),
                        "description": "A relation whose other ends each node carries, for the app to show "
                                       "one at a time: the frameworks a capability is placed in.",
                    },
                    "matrix": {
                        "type": "object",
                        "description": "A report drawn as a grid: rows down the side, an entity type across "
                                       "the top, a mark and a count in each cell.",
                        "additionalProperties": False,
                        "required": ["columns"],
                        "properties": {
                            "rows": {"type": "object", "description": "Field to value: which things are rows."},
                            "group": {"type": "string", "description": "A field the rows are sectioned by."},
                            "columns": {"enum": sorted(ENTITY_TYPES)},
                            "column_detail": {"type": "string"},
                            "roll_up": {"type": "string", "description": "A reference field a row counts "
                                                                          "what sits under it by."},
                            "mark": {"enum": sorted(RELATION_TYPES)},
                            "count": {"enum": sorted(RELATION_TYPES)},
                        },
                    },
                },
            },
            "limits": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"max_nodes": {
                    "type": "integer", "minimum": 1,
                    "description": (
                        "How many things a diagram, map or timeline draws before it is cut, "
                        "pins and what the scope names kept first. A report is a table and "
                        "is never cut: past its limit it is listed whole and says so."
                    ),
                }},
            },
        },
    }


#: One entry under `modules`, on a shape or an instance: the module by id, or
#: the module with an alias and the parameters it is given.
_MODULE_ENTRY = {
    "oneOf": [
        {"type": "string"},
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["module"],
            "properties": {
                "module": {"type": "string"},
                "as": {"type": "string"},
                "optional": {"type": "boolean"},
                "with": {
                    "type": "object",
                    "description": "Parameter name to value; a value may use the shape tokens.",
                },
            },
        },
    ]
}


def archetype_schema() -> dict:
    return {
        "$schema": SCHEMA_VERSION,
        "$id": "https://architecture-as-code/schemas/archetype.schema.json",
        "title": "Archetype",
        "type": "object",
        "additionalProperties": False,
        "required": ["archetype_id"],
        "properties": {
            "archetype_id": {"type": "string"},
            "replaces": _REPLACES,
            "title": {"type": "string"},
            "description": {"type": "string"},
            "version": {"type": "string"},
            "applies_to": {"enum": sorted(ENTITY_TYPES)},
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                        "required": {"type": "boolean"},
                        "default": {},
                        "description": {"type": "string"},
                        "estate": {
                            "type": "boolean",
                            "description": "Answered by the estate: `answers` in model.yaml holds it under this name, taken ahead of the default.",
                        },
                    },
                },
            },
            "defaults": {"type": "object"},
            "patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Patterns from 27_PATTERNS/ that every instance applies.",
            },
            "provider": {
                "type": "string",
                "description": "The cloud every block resolves against, unless an entry says.",
            },
            "entity_defaults": {
                "type": "object",
                "description": (
                    "What every entity the shape creates has in common, by entity type, "
                    "with `all` for the fields every type shares."
                ),
                "additionalProperties": False,
                "properties": {
                    name: {"type": "object"} for name in ["all"] + sorted(ENTITY_TYPES)
                },
            },
            "blocks": {
                "type": "array",
                "description": "Building blocks the shape is built on.",
                "items": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "object",
                            "required": ["block"],
                            "properties": {
                                "block": {"type": "string"},
                                "as": {"type": "string"},
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "provider": {"type": "string"},
                                "bind": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"},
                                    "description": (
                                        "Component to the shared tech service that already "
                                        "provides it, or to `landing-zone` for the landing "
                                        "zone's service of that kind. Nothing is created for "
                                        "a bound component."
                                    ),
                                },
                            },
                        },
                    ]
                },
            },
            "include_systems": {
                "type": "boolean",
                "description": "Include every provided system in the product. On by default.",
            },
            "bind": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "The landing zone by kind: component type id to the shared service that is that kind here. Block binds count too; this wins.",
            },
            "modules": {
                "type": "array",
                "description": "Modules from 28_MODULES/ the shape is composed from, in order.",
                "items": _MODULE_ENTRY,
            },
            "slots": {
                "type": "array",
                "description": "Where the shape varies: a need, the parts that can fill it, and the default.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "options"],
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "default": {"type": "string"},
                        "optional": {
                            "type": "boolean",
                            "description": "Whether an instance may choose `none`.",
                        },
                        "with": {
                            "type": "object",
                            "description": "Option to the parameters the shape answers for that part from its "
                                           "own parameters; the instance's own `with` for the part wins.",
                            "additionalProperties": {"type": "object"},
                        },
                    },
                },
            },
            "provides": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    name: {"type": "array", "items": {"type": "object"}}
                    for name in ENTITY_TYPES
                },
            },
            "relations": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    name: {"type": "array", "items": {"type": "object"}}
                    for name in RELATION_TYPES
                },
            },
        },
    }


def _one_or_many(record: dict, title: str, description: str, name: str) -> dict:
    return {
        "$schema": SCHEMA_VERSION,
        "$id": "https://architecture-as-code/schemas/%s.schema.json" % name,
        "title": title,
        "description": description,
        "oneOf": [record, {"type": "array", "items": record}],
    }


def component_type_schema() -> dict:
    from .blocks import SHAPES

    record = {
        "type": "object",
        "additionalProperties": False,
        "required": ["component_type_id", "name", "category", "description"],
        "properties": {
            "component_type_id": {"type": "string"},
            "replaces": _REPLACES,
            "name": {"type": "string"},
            "category": {"type": "string"},
            "applies_to": {"enum": sorted(ENTITY_TYPES)},
            "shape": {"enum": sorted(SHAPES)},
            "description": {"type": "string"},
            "providers": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "What each provider calls it: the solution building block.",
            },
            "defaults": {"type": "object"},
        },
    }
    return _one_or_many(
        record, "Component type",
        "A kind of thing an estate is made of, or a list of them in one file.",
        "component_type",
    )


def building_block_schema() -> dict:
    record = {
        "type": "object",
        "additionalProperties": False,
        "required": ["building_block_id", "name", "provides"],
        "properties": {
            "building_block_id": {"type": "string"},
            "replaces": _REPLACES,
            "name": {"type": "string"},
            "category": {"type": "string"},
            "description": {"type": "string"},
            "provides": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "object",
                            "required": ["component"],
                            "properties": {"component": {"type": "string"}},
                        },
                    ]
                },
            },
            "relations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["from", "to"],
                    "properties": {"from": {"type": "string"}, "to": {"type": "string"}},
                },
            },
            "defaults": {"type": "object"},
        },
    }
    return _one_or_many(
        record, "Building block",
        "A handful of component types that always arrive together, or a list of them.",
        "building_block",
    )


def pattern_schema() -> dict:
    from .blocks import PATTERN_STATUS

    record = {
        "type": "object",
        "additionalProperties": False,
        "required": ["pattern_id", "name", "blocks", "intent", "consequences", "when_not_to_use"],
        "properties": {
            "pattern_id": {"type": "string"},
            "replaces": _REPLACES,
            "name": {"type": "string"},
            "status": {"enum": list(PATTERN_STATUS)},
            "category": {"type": "string"},
            "blocks": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "intent": {"type": "string"},
            "consequences": {"type": "string"},
            "when_not_to_use": {"type": "string"},
            "satisfies": {
                "type": "array",
                "items": {"type": "string", "pattern": ID_PATTERN},
                "description": (
                    "Controls in the register the pattern is designed to meet. An "
                    "organization's own pattern may say; a shipped one does not, and "
                    "`patterns` in model.yaml is where an estate says it of any pattern."
                ),
            },
            "owner_org_id": {"type": "string", "pattern": ID_PATTERN},
            "decision_ref": {"type": "string"},
            "method_ref": {
                "type": "string",
                "description": "The method's reference pattern this one implements, by id (PAT-002).",
            },
        },
    }
    return _one_or_many(
        record, "Pattern",
        "A building block plus the decision, or a list of them in one file.",
        "pattern",
    )


def connection_schema() -> dict:
    from .schema import INTEGRATION_STYLES

    record = {
        "type": "object",
        "additionalProperties": False,
        "required": ["connection_id", "name", "integration_style", "protocols"],
        "properties": {
            "connection_id": {"type": "string"},
            "replaces": _REPLACES,
            "name": {"type": "string"},
            "description": {"type": "string"},
            "integration_style": {"enum": list(INTEGRATION_STYLES)},
            "protocols": {
                "type": "array", "minItems": 1, "items": {"type": "string"},
                "description": "An interface over any of these, in this style, is of this kind; the first is proposed.",
            },
            "auth_methods": {
                "type": "array", "items": {"type": "string"},
                "description": "The first is what a new connection of the kind is proposed with.",
            },
            "frequency": {"type": "string"},
            "direction": {"type": "string"},
            "patterns": {
                "type": "array", "items": {"type": "string"},
                "description": "From 27_PATTERNS: how this kind of connection is built here.",
            },
        },
    }
    return _one_or_many(
        record, "Connection kind",
        "A way two systems are connected here, or a list of them in one file.",
        "connection",
    )


def module_schema() -> dict:
    record = {
        "type": "object",
        "additionalProperties": False,
        "required": ["module_id", "name", "description"],
        "properties": {
            "module_id": {"type": "string"},
            "replaces": _REPLACES,
            "name": {"type": "string"},
            "category": {"type": "string"},
            "description": {"type": "string"},
            "optional": {
                "type": "boolean",
                "description": "Whether an instance may drop the part. On by default.",
            },
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                        "required": {"type": "boolean"},
                        "default": {},
                        "description": {"type": "string"},
                        "component": {
                            "type": "string",
                            "description": "The kind of shared service this stands for, as a component type id; the shape binds it.",
                        },
                        "estate": {
                            "type": "boolean",
                            "description": "Answered by the estate: `answers` in model.yaml holds it under this name, taken ahead of the default.",
                        },
                    },
                },
            },
            "requires": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Modules that have to be present for this one to make sense.",
            },
            "needs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Bindings the part reads from the shape and does not declare as parameters of its own.",
            },
            "modules": {
                "type": "array",
                "items": _MODULE_ENTRY,
                "description": "The parts this one is made of, which makes it a kit.",
            },
            "patterns": {"type": "array", "items": {"type": "string"}},
            "provides": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    name: {"type": "array", "items": {"type": "object"}}
                    for name in ENTITY_TYPES
                },
            },
            "relations": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    name: {"type": "array", "items": {"type": "object"}}
                    for name in RELATION_TYPES
                },
            },
        },
    }
    return _one_or_many(
        record, "Module",
        "A part of a product with parameters, or a list of them in one file.",
        "module",
    )


def import_mapping_schema() -> dict:
    """The file `terrane import csv --map` reads. Per kind of record, the field
    names and each field's values come from the metamodel, so a mapping to a
    field the model lacks, or to a criticality it does not list, is flagged
    while it is typed rather than when the import refuses it.

    Written with shared definitions: spelled out per field and per kind, it
    was 287 KB, every status list eighteen times over."""
    from .inventory import ID_FROM, TYPE_KEYS
    from .schema import _COMMON

    derived = ("archetype", "archetype_instance")
    defs: Dict[str, dict] = {"id": {"type": "string", "pattern": ID_PATTERN}}
    kinds_of_value: Dict[tuple, str] = {}

    def kind(field) -> Optional[str]:
        """The shared definition a field's values are checked against, or
        None for free text."""
        if field.enum:
            name = kinds_of_value.setdefault(tuple(field.enum), field.name)
            defs.setdefault(name, {"enum": list(field.enum)})
        elif field.ref:
            name = "id"
        else:
            return None
        # An empty value is a decision too: the field is left empty.
        defs.setdefault(name + "-values", {
            "type": "object",
            "additionalProperties": {"anyOf": [{"$ref": "#/$defs/" + name}, {"enum": ["", None]}]},
        })
        return name

    def checked(fields) -> Dict[str, Dict[str, dict]]:
        values, defaults = {}, {}
        for field in fields:
            name = kind(field)
            if name:
                values[field.name] = {"$ref": "#/$defs/%s-values" % name}
                defaults[field.name] = {"$ref": "#/$defs/" + name}
        return {"values": values, "defaults": defaults}

    common = checked(_COMMON)
    defs["common-values"] = {"properties": common["values"]}
    defs["common-defaults"] = {"properties": common["defaults"]}
    common_names = {f.name for f in _COMMON}

    kinds: Dict[str, dict] = {}
    for name, entity_type in ENTITY_TYPES.items():
        fields = [f for f in entity_type.fields if f.name not in derived]
        defs[name + "-fields"] = {"enum": [f.name for f in fields]}
        own = checked([f for f in fields if f.name not in common_names])
        field_names = {"$ref": "#/$defs/%s-fields" % name}
        target = {"anyOf": [{"const": entity_type.pk}, field_names]}
        kinds[name] = {
            "allOf": [{"$ref": "#/$defs/entry"}],
            "properties": {
                "columns": {
                    "additionalProperties": {
                        "oneOf": [target, {"type": "array", "minItems": 1, "items": target}],
                    },
                },
                "values": {
                    "propertyNames": field_names,
                    "allOf": [{"$ref": "#/$defs/common-values"}],
                    "properties": own["values"],
                },
                "defaults": {
                    "propertyNames": field_names,
                    "allOf": [{"$ref": "#/$defs/common-defaults"}],
                    "properties": own["defaults"],
                },
            },
        }
    # What every kind's entry has; the kind adds which fields it fills.
    defs["entry"] = {
        "type": "object",
        "propertyNames": {"enum": list(TYPE_KEYS)},
        "properties": {
            "file": {"type": "string", "description": "The inventory file, in the --from folder: a .csv, or an "
                                                      ".xlsx workbook. Default: <type>.csv."},
            "sheet": {"type": "string", "description": "The sheet of a workbook the rows are on. Default: the first "
                                                       "sheet with a header row."},
            "code": {
                "type": "string",
                "description": "The column holding the inventory's own id. Kept in cmdb_ci_sys_id where the type "
                               "has it, and matched when another row names this one.",
            },
            "id": {
                "type": "object",
                "additionalProperties": False,
                "required": ["prefix"],
                "properties": {
                    "prefix": {"type": "string", "pattern": "^[A-Z][A-Z0-9]*-?$"},
                    "from": {"enum": list(ID_FROM), "description": "Slug the name or the code. Default: name."},
                },
            },
            "columns": {"type": "object", "description": "Inventory column: the field, or the fields, it fills."},
            "ignore": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Columns read by nothing, on purpose; any other column not mapped is reported as left out.",
            },
            "values": {"type": "object", "description": "Per field, inventory value: the model's value."},
            "defaults": {
                "type": "object",
                "description": "Per field, the value when the inventory's is empty or there is no column.",
            },
        },
    }
    return {
        "$schema": SCHEMA_VERSION,
        "$id": "https://architecture-as-code/schemas/import_mapping.schema.json",
        "title": "Import mapping",
        "description": "How an inventory's columns, values and codes become the model's, for terrane import csv --map.",
        "type": "object",
        "additionalProperties": False,
        "properties": dict({"description": {"type": "string"}}, **kinds),
        "$defs": dict(sorted(defs.items())),
    }


def write_all(out_dir: Path) -> List[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    documents = {
        "relations": relations_schema(),
        "view": view_schema(),
        "archetype": archetype_schema(),
        "component_type": component_type_schema(),
        "building_block": building_block_schema(),
        "pattern": pattern_schema(),
        "module": module_schema(),
        "connection": connection_schema(),
        "import_mapping": import_mapping_schema(),
    }
    for entity_type in ENTITY_TYPES.values():
        documents[entity_type.name] = entity_schema(entity_type)
    for name, document in sorted(documents.items()):
        path = out_dir / ("%s.schema.json" % name)
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written
