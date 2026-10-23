"""Exports out of the model.

The model here is the source; everything downstream is generated. That is what
keeps Backstage from quietly becoming a second place where the truth lives.

Two targets:

* `csv` writes the metamodel v2 layout (entity tables plus a `relations/`
  folder), which is what the Collibra import path and the existing
  `scripts/validate_csvs.py` already expect.
* `backstage` writes catalog entities for the Backstage pilot.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

from .model import Model
from .schema import ENTITY_TYPES, RELATION_TYPES

#: Internal bookkeeping that must not reach an export.
_INTERNAL = ("_type", "_source_file", "_source")


def _clean(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in _INTERNAL}


def _flatten(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def export_csv(model: Model, out_dir: Path) -> List[Path]:
    """Write metamodel v2 CSVs: one file per entity, relations in `relations/`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "relations").mkdir(exist_ok=True)
    written: List[Path] = []

    for type_name, entity_type in ENTITY_TYPES.items():
        records = model.all_of(type_name)
        if not records:
            continue
        columns = [entity_type.pk] + [
            f.name for f in entity_type.fields if f.name != entity_type.pk
        ]
        path = out_dir / ("%s.csv" % type_name)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=columns, extrasaction="ignore", lineterminator='\n'
            )
            writer.writeheader()
            for record in sorted(records, key=lambda r: str(r[entity_type.pk])):
                clean = _clean(record)
                writer.writerow({c: _flatten(clean.get(c)) for c in columns})
        written.append(path)

    for name, spec in RELATION_TYPES.items():
        rows = model.relation_rows(name)
        if not rows:
            continue
        columns = [spec.left_column, spec.right_column]
        if spec.qualifier:
            columns.append(spec.qualifier)
        path = out_dir / "relations" / ("%s.csv" % name)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=columns, extrasaction="ignore", lineterminator='\n'
            )
            writer.writeheader()
            for row in sorted(rows, key=lambda r: (str(r[spec.left_column]), str(r[spec.right_column]))):
                writer.writerow({c: _flatten(row.get(c)) for c in columns})
        written.append(path)

    return written


def _slug(value: str) -> str:
    """Backstage names allow lower-case alphanumerics plus `-`, `_` and `.`."""
    out = []
    for ch in str(value).lower():
        out.append(ch if (ch.isalnum() or ch in "-_.") else "-")
    return "".join(out).strip("-") or "unnamed"


def _entity_yaml(entity: dict) -> str:
    """Serialize a Backstage entity without needing a YAML writer."""
    lines: List[str] = []

    def emit(data: dict, indent: str) -> None:
        for key, value in data.items():
            if value in (None, "", [], {}):
                continue
            if isinstance(value, dict):
                lines.append("%s%s:" % (indent, key))
                emit(value, indent + "  ")
            elif isinstance(value, list):
                lines.append("%s%s:" % (indent, key))
                for item in value:
                    lines.append("%s  - %s" % (indent, json.dumps(str(item))))
            else:
                lines.append("%s%s: %s" % (indent, key, json.dumps(str(value))))

    emit(entity, "")
    return "\n".join(lines)


def export_backstage(model: Model, out_dir: Path) -> List[Path]:
    """Write Backstage catalog entities derived from the model."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    documents: List[str] = []

    for record in model.all_of("org_units"):
        documents.append(
            _entity_yaml(
                {
                    "apiVersion": "backstage.io/v1alpha1",
                    "kind": "Group",
                    "metadata": {
                        "name": _slug(record["org_unit_id"]),
                        "title": record.get("name"),
                        "description": record.get("description"),
                        "annotations": {"architecture-as-code/id": record["org_unit_id"]},
                    },
                    "spec": {"type": "team", "children": []},
                }
            )
        )

    for record in model.all_of("products"):
        documents.append(
            _entity_yaml(
                {
                    "apiVersion": "backstage.io/v1alpha1",
                    "kind": "Domain",
                    "metadata": {
                        "name": _slug(record["product_id"]),
                        "title": record.get("name"),
                        "description": record.get("description"),
                        "annotations": {"architecture-as-code/id": record["product_id"]},
                    },
                    "spec": {"owner": _slug(record.get("owner_org_id") or "unowned")},
                }
            )
        )

    product_of: Dict[str, str] = {}
    for row in model.relation_rows("product_includes_system"):
        product_of.setdefault(str(row["system_id"]), str(row["product_id"]))

    for record in model.all_of("systems"):
        system_id = str(record["system_id"])
        tags = [_slug(t) for t in model.tags(record)]
        if record.get("criticality"):
            tags.append(_slug("criticality-%s" % record["criticality"]))
        entity = {
            "apiVersion": "backstage.io/v1alpha1",
            "kind": "System",
            "metadata": {
                "name": _slug(system_id),
                "title": record.get("name"),
                "description": record.get("description"),
                "tags": sorted(set(tags)),
                "annotations": {
                    "architecture-as-code/id": system_id,
                    "architecture-as-code/archetype": record.get("archetype") or "",
                    "servicenow.com/cmdb-ci-sys-id": record.get("cmdb_ci_sys_id") or "",
                },
            },
            "spec": {
                "owner": _slug(record.get("owner_org_id") or "unowned"),
                "lifecycle": _slug(record.get("status") or "unknown"),
            },
        }
        if system_id in product_of:
            entity["spec"]["domain"] = _slug(product_of[system_id])
        documents.append(_entity_yaml(entity))

    # What a system offers is Backstage's API, as it is ArchiMate's
    # application interface: one entity, in its system, whatever number of
    # connections go through it.
    for record in model.all_of("offered_interfaces"):
        documents.append(
            _entity_yaml(
                {
                    "apiVersion": "backstage.io/v1alpha1",
                    "kind": "API",
                    "metadata": {
                        "name": _slug(record["offered_interface_id"]),
                        "title": record.get("name"),
                        "description": record.get("description"),
                        "annotations": {"architecture-as-code/id": record["offered_interface_id"]},
                    },
                    "spec": {
                        "type": _api_type(record),
                        "owner": _slug(record.get("owner_org_id") or "unowned"),
                        "lifecycle": _slug(record.get("status") or "unknown"),
                        "system": _slug(str(record.get("system_id") or "")),
                        "definition": record.get("specification") or record.get("description") or "See the model.",
                    },
                }
            )
        )

    # A connection through an offered interface is a use of that API, not
    # an API of its own. One through none is still written as one, its
    # caller's, until it says which door it opens.
    for record in model.all_of("interfaces"):
        if model.get("offered_interfaces", str(record.get("offered_interface_id") or "")):
            continue
        documents.append(
            _entity_yaml(
                {
                    "apiVersion": "backstage.io/v1alpha1",
                    "kind": "API",
                    "metadata": {
                        "name": _slug(record["interface_id"]),
                        "title": record.get("name"),
                        "description": record.get("description"),
                        "annotations": {"architecture-as-code/id": record["interface_id"]},
                    },
                    "spec": {
                        "type": _slug(record.get("protocol") or "other"),
                        "owner": _slug(record.get("owner_org_id") or "unowned"),
                        "lifecycle": _slug(record.get("status") or "unknown"),
                        "system": _slug(str(record.get("source_system_id") or "")),
                        "definition": record.get("description") or "See the model.",
                    },
                }
            )
        )

    header = (
        "# Generated from the model by `terrane export backstage`. Do not edit by hand.\n"
        "# The model in 10_MODEL/ is the source; this catalog is a projection of it.\n"
    )
    path = out_dir / "catalog-info.yaml"
    path.write_text(header + "\n---\n".join(documents) + "\n", encoding="utf-8")
    return [path]


def _api_type(record: dict) -> str:
    """Backstage's word for what kind of API this is: its specification
    formats where the protocol and style say one, else the protocol."""
    protocol = str(record.get("protocol") or "").lower()
    style = str(record.get("integration_style") or "")
    if protocol == "grpc":
        return "grpc"
    if protocol == "graphql":
        return "graphql"
    if style == "Event":
        return "asyncapi"
    if protocol in ("https", "http") and style in ("", "Request-response"):
        return "openapi"
    return _slug(protocol or "other")


def export_json(model: Model, out_path: Path) -> Path:
    """One JSON document holding the resolved model, for downstream tooling."""
    payload = {
        "meta": dict(model.config),
        "entities": {
            name: [_clean(r) for r in model.all_of(name)]
            for name in ENTITY_TYPES
            if model.all_of(name)
        },
        "relations": {
            name: [_clean(r) for r in rows]
            for name, rows in model.relations.items()
            if rows
        },
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out_path
