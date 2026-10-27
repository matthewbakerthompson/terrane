"""One id for another, wherever it sits.

A shape's parts are renamed when a product takes them (`terrane.archetype`)
and a sketch's records when a person says one is a record the estate has
already (`terrane.join`, `same`): either way every string equal to the old
id is the new one, in a record's own id, the systems an interface joins, a
data asset's system of record, a relation row's columns and a view's pins.
"""

from __future__ import annotations

from typing import Dict


def rename_deep(value, renames: Dict[str, str]):
    """`value` with every string equal to a key of `renames` replaced by
    its value, through dicts, lists, tuples and sets."""
    if isinstance(value, str):
        return renames.get(value, value)
    if isinstance(value, dict):
        return {k: rename_deep(v, renames) for k, v in value.items()}
    if isinstance(value, list):
        return [rename_deep(v, renames) for v in value]
    if isinstance(value, tuple):
        return tuple(rename_deep(v, renames) for v in value)
    if isinstance(value, set):
        return {rename_deep(v, renames) for v in value}
    return value
