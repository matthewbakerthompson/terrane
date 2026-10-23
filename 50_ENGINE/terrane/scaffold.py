"""Scaffolding for new model entries.

`terrane new` exists so that adding an application is a command rather than an act
of remembering which fields matter. It writes a file with the required fields
present and the optional ones commented, which is the difference between a model
that stays complete and one that decays into name-only stubs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .archetype import Archetype
from .model import Model
from .schema import ENTITY_TYPES, field_map


class ScaffoldError(ValueError):
    """A new entry could not be scaffolded."""


def _yaml_value(value) -> str:
    if value is None:
        return '""'
    text = str(value)
    if text == "":
        return '""'
    if any(ch in text for ch in ":#{}[],&*?|-<>=!%@`") or text != text.strip():
        return '"%s"' % text.replace('"', '\\"')
    return text


def scaffold_entity(
    entity_type_name: str,
    entity_id: str,
    values: Dict[str, str],
    model: Optional[Model] = None,
) -> str:
    entity_type = ENTITY_TYPES.get(entity_type_name)
    if entity_type is None:
        raise ScaffoldError("unknown entity type %r" % entity_type_name)
    if model is not None and model.find(entity_id) is not None:
        raise ScaffoldError("%r already exists in the model" % entity_id)

    fields = field_map(entity_type)
    unknown = sorted(set(values) - set(fields))
    if unknown:
        raise ScaffoldError(
            "%s has no field(s) %s" % (entity_type.label, ", ".join(unknown))
        )

    lines: List[str] = []
    lines.append("# %s. Validate with `terrane validate` before committing." % entity_type.label.title())
    lines.append("%s: %s" % (entity_type.pk, _yaml_value(entity_id)))
    for field in entity_type.fields:
        if field.name in values:
            lines.append("%s: %s" % (field.name, _yaml_value(values[field.name])))
        elif field.required:
            hint = (" # one of: %s" % ", ".join(field.enum)) if field.enum else ""
            lines.append("%s: \"\"%s" % (field.name, hint))
    lines.append("")
    lines.append("# Optional, and worth filling in:")
    for field in entity_type.fields:
        if field.required or field.name in values:
            continue
        hint = (" one of: %s" % ", ".join(field.enum)) if field.enum else ""
        lines.append("# %s:%s" % (field.name, hint))
    return "\n".join(lines) + "\n"


def scaffold_instance(archetype: Archetype, entity_id: str, values: Dict[str, str]) -> str:
    """A product (or other) instance file that applies an archetype."""
    entity_type = ENTITY_TYPES[archetype.applies_to]
    lines: List[str] = []
    lines.append("# %s built from archetype %s." % (entity_type.label.title(), archetype.archetype_id))
    lines.append("# Everything the archetype provides is generated. Use `overrides` where")
    lines.append("# this instance genuinely differs and `exclude` where a part does not apply.")
    lines.append("%s: %s" % (entity_type.pk, _yaml_value(entity_id)))
    for field in entity_type.fields:
        if field.name in values:
            lines.append("%s: %s" % (field.name, _yaml_value(values[field.name])))
        elif field.required:
            hint = (" # one of: %s" % ", ".join(field.enum)) if field.enum else ""
            lines.append("%s: \"\"%s" % (field.name, hint))
    lines.append("")
    lines.append("archetype: %s" % archetype.archetype_id)
    lines.append("parameters:")
    for param in archetype.parameters:
        comment = "  # %s" % param.description if param.description else ""
        if param.name in values:
            lines.append("  %s: %s%s" % (param.name, _yaml_value(values[param.name]), comment))
        elif param.required:
            lines.append("  %s: \"\"%s" % (param.name, comment))
        else:
            lines.append(
                "  # %s: %s%s" % (param.name, _yaml_value(param.default), comment)
            )
    lines.append("")
    lines.append("# overrides:")
    lines.append("#   SYS-EXAMPLE-WEB:")
    lines.append("#     criticality: High")
    lines.append("# exclude:")
    lines.append("#   - SYS-EXAMPLE-CACHE")
    return "\n".join(lines) + "\n"


def target_path(root: Path, entity_type_name: str, entity_id: str) -> Path:
    entity_type = ENTITY_TYPES[entity_type_name]
    return Path(root) / "10_MODEL" / entity_type.folder / ("%s.yaml" % entity_id)
