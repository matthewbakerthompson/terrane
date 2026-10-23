"""ServiceNow CMDB reconciliation.

The CMDB is not trusted yet, so nothing here writes to it and nothing here
changes the model. The adapter reads a CI export, matches it against the model,
and produces a drift report. Three things follow from that:

* the model stays authoritative while the CMDB is unreliable;
* the drift report is the evidence that makes the CMDB better, one reconciled
  CI at a time;
* when a field in the CMDB does become trustworthy, `field_sot.yaml` flips it
  without a code change.

Matching runs in three passes, weakest last, and a weak match is reported as a
candidate for a human rather than applied.
"""

from __future__ import annotations

import csv
import difflib
import re
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence

from .loader import read_data_file
from .model import Model

#: Columns this adapter reads from a `cmdb_ci` export. Extra columns are kept
#: and ignored; missing ones simply produce no comparison for that field.
DEFAULT_FIELD_MAP = {
    "sys_id": "cmdb_ci_sys_id",
    "name": "name",
    "sys_class_name": "cmdb_ci_class",
    "operational_status": "status",
    "business_criticality": "criticality",
    "owned_by": "owner_org_id",
    "environment": "environment",
    "u_hosting": "hosting",
}

#: ServiceNow's vocabulary is not the model's. Anything not listed here is
#: compared as-is and will show up as a mismatch, which is the honest outcome.
VALUE_MAP = {
    "status": {
        "1": "Active",
        "operational": "Active",
        "non-operational": "Retired",
        "retired": "Retired",
        "6": "Retired",
        "installed": "Active",
    },
    "criticality": {
        "1 - most critical": "High",
        "2 - somewhat critical": "High",
        "3 - less critical": "Medium",
        "4 - not critical": "Low",
        "most critical": "High",
        "less critical": "Medium",
        "not critical": "Low",
    },
}

FUZZY_THRESHOLD = 0.86


class DriftRow(NamedTuple):
    category: str
    system_id: str
    cmdb_sys_id: str
    model_name: str
    cmdb_name: str
    field: str
    model_value: str
    cmdb_value: str
    confidence: str
    note: str


class DriftResult(NamedTuple):
    rows: List[DriftRow]
    counts: Dict[str, int]
    field_sot: Dict[str, str]
    export_path: str


def normalize_name(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    for noise in (" system", " service", " application", " app", " platform", " prod"):
        if text.endswith(noise):
            text = text[: -len(noise)]
    return " ".join(text.split())


def _map_value(field: str, value: str) -> str:
    text = str(value or "").strip()
    lookup = VALUE_MAP.get(field)
    if lookup:
        return lookup.get(text.lower(), text)
    return text


def read_ci_export(path: Path) -> List[dict]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_field_sot(path: Path) -> Dict[str, str]:
    """Per-field owner: `model` or `cmdb`. Missing file means the model owns all."""
    if not Path(path).exists():
        return {}
    data = read_data_file(Path(path)) or {}
    fields = data.get("fields") or {}
    return {str(k): str(v).lower() for k, v in fields.items()}


def reconcile(
    model: Model,
    ci_rows: Sequence[dict],
    field_sot: Optional[Dict[str, str]] = None,
    field_map: Optional[Dict[str, str]] = None,
    export_path: str = "",
) -> DriftResult:
    field_map = dict(field_map or DEFAULT_FIELD_MAP)
    field_sot = dict(field_sot or {})
    rows: List[DriftRow] = []

    systems = model.all_of("systems")
    by_sys_id = {
        str(s["cmdb_ci_sys_id"]): s for s in systems if s.get("cmdb_ci_sys_id")
    }
    by_name: Dict[str, list] = {}
    for system in systems:
        by_name.setdefault(normalize_name(system.get("name") or ""), []).append(system)

    matched_systems = set()
    unmatched_ci: List[dict] = []

    for ci in ci_rows:
        ci_sys_id = str(ci.get("sys_id") or "").strip()
        ci_name = str(ci.get("name") or "").strip()
        system = by_sys_id.get(ci_sys_id) if ci_sys_id else None
        confidence = "linked"

        if system is None:
            candidates = by_name.get(normalize_name(ci_name)) or []
            if len(candidates) == 1:
                system = candidates[0]
                confidence = "name-exact"
            elif len(candidates) > 1:
                rows.append(
                    DriftRow(
                        "AMBIGUOUS",
                        ";".join(str(c["system_id"]) for c in candidates),
                        ci_sys_id,
                        "",
                        ci_name,
                        "",
                        "",
                        "",
                        "name-exact",
                        "%d systems share this normalized name" % len(candidates),
                    )
                )
                continue

        if system is None:
            close = difflib.get_close_matches(
                normalize_name(ci_name), list(by_name), n=1, cutoff=FUZZY_THRESHOLD
            )
            if close:
                candidate = by_name[close[0]][0]
                rows.append(
                    DriftRow(
                        "CANDIDATE_MATCH",
                        str(candidate["system_id"]),
                        ci_sys_id,
                        str(candidate.get("name") or ""),
                        ci_name,
                        "",
                        "",
                        "",
                        "fuzzy-%.2f"
                        % difflib.SequenceMatcher(
                            None, normalize_name(ci_name), close[0]
                        ).ratio(),
                        "Not applied. Confirm, then set cmdb_ci_sys_id on the system.",
                    )
                )
                continue
            unmatched_ci.append(ci)
            continue

        matched_systems.add(str(system["system_id"]))
        mismatches = 0
        for ci_column, model_field in field_map.items():
            if model_field in ("cmdb_ci_sys_id",):
                continue
            if ci_column not in ci:
                continue
            cmdb_value = _map_value(model_field, ci.get(ci_column, ""))
            model_value = str(system.get(model_field) or "")
            if not cmdb_value and not model_value:
                continue
            if cmdb_value == model_value:
                continue
            owner = field_sot.get(model_field, "model")
            mismatches += 1
            rows.append(
                DriftRow(
                    "ATTR_MISMATCH",
                    str(system["system_id"]),
                    ci_sys_id,
                    str(system.get("name") or ""),
                    ci_name,
                    model_field,
                    model_value,
                    cmdb_value,
                    confidence,
                    "source of truth: %s" % owner,
                )
            )
        if confidence == "name-exact":
            rows.append(
                DriftRow(
                    "UNLINKED_MATCH",
                    str(system["system_id"]),
                    ci_sys_id,
                    str(system.get("name") or ""),
                    ci_name,
                    "cmdb_ci_sys_id",
                    str(system.get("cmdb_ci_sys_id") or ""),
                    ci_sys_id,
                    confidence,
                    "Matched on name. Record cmdb_ci_sys_id to make it durable.",
                )
            )
        elif mismatches == 0:
            rows.append(
                DriftRow(
                    "LINKED_OK",
                    str(system["system_id"]),
                    ci_sys_id,
                    str(system.get("name") or ""),
                    ci_name,
                    "",
                    "",
                    "",
                    confidence,
                    "",
                )
            )

    for ci in unmatched_ci:
        rows.append(
            DriftRow(
                "CMDB_ONLY",
                "",
                str(ci.get("sys_id") or ""),
                "",
                str(ci.get("name") or ""),
                "",
                "",
                str(ci.get("sys_class_name") or ""),
                "none",
                "In the CMDB, absent from the model.",
            )
        )

    for system in systems:
        system_id = str(system["system_id"])
        if system_id in matched_systems:
            continue
        rows.append(
            DriftRow(
                "MODEL_ONLY",
                system_id,
                str(system.get("cmdb_ci_sys_id") or ""),
                str(system.get("name") or ""),
                "",
                "",
                str(system.get("status") or ""),
                "",
                "none",
                "In the model, absent from the CI export.",
            )
        )

    counts: Dict[str, int] = {}
    for row in rows:
        counts[row.category] = counts.get(row.category, 0) + 1
    return DriftResult(
        rows=rows, counts=counts, field_sot=field_sot, export_path=str(export_path)
    )


def write_drift_csv(result: DriftResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(DriftRow._fields)
        for row in sorted(result.rows, key=lambda r: (r.category, r.system_id, r.field)):
            writer.writerow(list(row))
    return path


def write_drift_markdown(result: DriftResult, path: Path, model: Model) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    total_systems = len(model.all_of("systems"))
    linked = result.counts.get("LINKED_OK", 0) + result.counts.get("ATTR_MISMATCH", 0)

    lines: List[str] = []
    lines.append("# ServiceNow CMDB drift report")
    lines.append("")
    lines.append(
        "Generated by `terrane cmdb drift`. Read-only: nothing was written to ServiceNow "
        "and nothing was written to the model."
    )
    lines.append("")
    lines.append("**CI export:** `%s`" % (result.export_path or "unspecified"))
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append("| Measure | Count |")
    lines.append("|---|---:|")
    lines.append("| Systems in the model | %d |" % total_systems)
    lines.append("| Systems reconciled to a CI | %d |" % linked)
    lines.append(
        "| Model coverage | %s |"
        % ("%.0f%%" % (100.0 * linked / total_systems) if total_systems else "n/a")
    )
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    lines.append("| Category | Count | What to do |")
    lines.append("|---|---:|---|")
    for category, action in (
        ("LINKED_OK", "Nothing. Linked and agreeing."),
        ("ATTR_MISMATCH", "Decide per field. `field_sot.yaml` records who wins."),
        ("UNLINKED_MATCH", "Record `cmdb_ci_sys_id` on the system to make the link durable."),
        ("CANDIDATE_MATCH", "Human confirmation. Not applied automatically."),
        ("AMBIGUOUS", "Disambiguate the model names, then re-run."),
        ("MODEL_ONLY", "Either the CI is missing from ServiceNow, or the system is stale."),
        ("CMDB_ONLY", "Either the model is incomplete, or the CI is junk. Usually the latter, for now."),
    ):
        if result.counts.get(category):
            lines.append("| `%s` | %d | %s |" % (category, result.counts[category], action))
    lines.append("")

    mismatches = [r for r in result.rows if r.category == "ATTR_MISMATCH"]
    if mismatches:
        lines.append("## Attribute mismatches")
        lines.append("")
        lines.append("| System | Field | Model | CMDB | Source of truth |")
        lines.append("|---|---|---|---|---|")
        for row in sorted(mismatches, key=lambda r: (r.system_id, r.field))[:200]:
            lines.append(
                "| `%s` | `%s` | %s | %s | %s |"
                % (
                    row.system_id,
                    row.field,
                    row.model_value or "—",
                    row.cmdb_value or "—",
                    result.field_sot.get(row.field, "model"),
                )
            )
        if len(mismatches) > 200:
            lines.append("")
            lines.append("_%d further mismatches are in the CSV._" % (len(mismatches) - 200))
        lines.append("")

    candidates = [r for r in result.rows if r.category == "CANDIDATE_MATCH"]
    if candidates:
        lines.append("## Candidate matches awaiting confirmation")
        lines.append("")
        lines.append("| Model system | CMDB name | CMDB sys_id | Confidence |")
        lines.append("|---|---|---|---|")
        for row in sorted(candidates, key=lambda r: r.confidence, reverse=True)[:100]:
            lines.append(
                "| `%s` %s | %s | `%s` | %s |"
                % (row.system_id, row.model_name, row.cmdb_name, row.cmdb_sys_id, row.confidence)
            )
        lines.append("")

    lines.append("## How to read this while the CMDB is immature")
    lines.append("")
    lines.append(
        "A high `CMDB_ONLY` count is expected and is not a defect in the model. The "
        "number worth tracking over time is model coverage, and the number worth "
        "escalating is `ATTR_MISMATCH` on fields the CMDB is supposed to own."
    )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
