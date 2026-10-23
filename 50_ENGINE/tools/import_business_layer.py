"""Bring the business layer across from the business architecture repository.

The capability map, the value streams and the org structure are authored there
and consumed here. Keeping a second, smaller set of capabilities in this
repository meant the application landscape and the capability map could not be
talked about together, which defeats the point of having either.

This is a one-way import, run deliberately rather than on every build: the
business layer changes at the pace of a workshop, not a commit. Ids are taken
verbatim so a capability means the same thing in both places.

    python 50_ENGINE/tools/import_business_layer.py --from ../business-architecture

Nothing about the application or technology estate is touched. What this
rewrites is `10_MODEL/capabilities/`, `10_MODEL/value_streams/`,
`10_MODEL/org_units/`, `10_MODEL/policies/` and `10_MODEL/controls/`, plus the
two relation files it owns.

The governance register comes across the same way, and one join is done on
the way in: the business layer says which processes a control governs and
which capabilities a process supports, and neither processes nor steps are
held here, so the capability-to-control pairs are derived at import and only
the result is kept. Each pair carries its basis, so nobody mistakes an
inference for a statement.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "50_ENGINE"))

from terrane.importer import _yaml_scalar  # noqa: E402
from terrane.style import americanize  # noqa: E402
from terrane.schema import ENTITY_TYPES  # noqa: E402

#: The business repository works a named fictional scenario. This one does not,
#: on purpose: a method that reads as one company's case study gets treated as
#: one company's case study. The structure is what transfers.
SCENARIO_NAMES = ("Meridian Bank", "Meridian's", "Meridian")


def _rows(path: Path) -> List[dict]:
    if not path.exists():
        raise SystemExit("no such file: %s" % path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def descenario(text: str) -> str:
    """Remove the scenario's company name without leaving a hole in a sentence."""
    out = str(text or "")
    out = re.sub(r"\bMeridian Bank\b", "the bank", out)
    out = re.sub(r"\bMeridian's\b", "the bank's", out)
    out = re.sub(r"\bMeridian\b", "the bank", out)
    # "onto the bank servicing" reads badly where the name was possessive.
    out = out.replace("onto the bank servicing", "onto our servicing platform")
    return out


def _clean(value: str) -> str:
    """Scrub the scenario name and normalize the spelling.

    Prose arriving from another repository is exactly where a British form gets
    in, and the repository commits to American spelling. Fixing it on the way
    in beats a test that can only refuse it.
    """
    return americanize(descenario(str(value or "").strip()))


def write_records(path: Path, header: str, records: Iterable[dict]) -> int:
    """One file per table, in the layout a person would have written."""
    lines = [line for line in header.strip().split("\n")]
    lines.append("")
    count = 0
    for record in records:
        count += 1
        first = True
        for key, value in record.items():
            if value in (None, ""):
                continue
            prefix = "- " if first else "  "
            first = False
            lines.append("%s%s: %s" % (prefix, key, _yaml_scalar(value)))
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return count


def _drop_unknown(record: dict, type_name: str) -> dict:
    """Keep only what this metamodel declares, so nothing arrives unvalidated."""
    known = {f.name for f in ENTITY_TYPES[type_name].fields}
    known.add(ENTITY_TYPES[type_name].pk)
    return {k: v for k, v in record.items() if k in known and v not in (None, "")}


def capabilities(rows: List[dict]) -> List[dict]:
    out = []
    for row in rows:
        out.append(_drop_unknown({
            "capability_id": row["capability_id"].strip(),
            "name": _clean(row["name"]),
            "description": _clean(row["description"]),
            "status": row.get("status") or "Proposed",
            "togaf_layer": "Business",
            "architecture_domain": "Business",
            # Every level of a capability map is conceptual; the map level is
            # its own field rather than overloading the TOGAF one.
            "abstraction_level": "Conceptual",
            "capability_level": (row.get("abstraction_level") or "").strip(),
            "capability_tier": (row.get("capability_tier") or "").strip(),
            "strategic_importance": (row.get("strategic_importance") or "").strip(),
            "parent_capability_id": (row.get("parent_capability_id") or "").strip(),
            "owner_org_id": (row.get("owner_org_id") or "").strip(),
            "maturity_level": (row.get("maturity_level") or "").strip(),
            "company_domain": _clean(row.get("company_domain")),
            "company_subdomain": _clean(row.get("company_subdomain")),
            "source": "Business architecture repository",
        }, "capabilities"))
    out.sort(key=lambda r: r["capability_id"])
    return out


def value_streams(rows: List[dict]) -> List[dict]:
    out = []
    for row in rows:
        out.append(_drop_unknown({
            "value_stream_id": row["value_stream_id"].strip(),
            "name": _clean(row["name"]),
            "description": _clean(row["description"]),
            "status": row.get("status") or "Proposed",
            "togaf_layer": "Business",
            "architecture_domain": "Business",
            "abstraction_level": "Conceptual",
            "value_stream_type": (row.get("value_stream_type") or "").strip(),
            "stakeholders": _clean(row.get("stakeholders")),
            "value_proposition": _clean(row.get("value_proposition")),
            "owner_org_id": (row.get("owner_org_id") or "").strip(),
            "last_reviewed": (row.get("last_reviewed") or "").strip(),
            "source": "Business architecture repository",
        }, "value_streams"))
    out.sort(key=lambda r: r["value_stream_id"])
    return out


def stages(rows: List[dict]) -> List[dict]:
    out = []
    for row in rows:
        out.append(_drop_unknown({
            "stage_id": row["stage_id"].strip(),
            "name": _clean(row["name"]),
            "status": row.get("status") or "Proposed",
            "togaf_layer": "Business",
            "architecture_domain": "Business",
            "abstraction_level": "Conceptual",
            "value_stream_id": row["value_stream_id"].strip(),
            "stage_order": (row.get("order") or "").strip(),
            "exit_criterion": _clean(row.get("exit_criterion")),
            "source": "Business architecture repository",
        }, "value_stream_stages"))
    out.sort(key=lambda r: (r["value_stream_id"], int(r.get("stage_order") or 0)))
    return out


def org_units(rows: List[dict]) -> List[dict]:
    out = []
    for row in rows:
        out.append(_drop_unknown({
            "org_unit_id": row["org_unit_id"].strip(),
            "name": _clean(row["name"]),
            "description": _clean(row.get("description")),
            "status": row.get("status") or "Active",
            "togaf_layer": "Business",
            "architecture_domain": "Business",
            "abstraction_level": "Conceptual",
            "parent_org_unit_id": (row.get("parent_org_unit_id") or "").strip(),
            "company_domain": _clean(row.get("company_domain")),
            "dama_role": _clean(row.get("dama_role")),
            "source": "Business architecture repository",
        }, "org_units"))
    out.sort(key=lambda r: r["org_unit_id"])
    return out


def policies(rows: List[dict]) -> List[dict]:
    out = []
    for row in rows:
        out.append(_drop_unknown({
            "policy_id": row["policy_id"].strip(),
            "name": _clean(row["name"]),
            "purpose": _clean(row.get("purpose")),
            "description": _clean(row.get("description")),
            "status": row.get("status") or "Proposed",
            "togaf_layer": "Business",
            "architecture_domain": "Governance",
            "abstraction_level": "Conceptual",
            "regulatory_framework": _clean(row.get("regulatory_framework")),
            "owner_org_id": (row.get("owner_org_id") or "").strip(),
            "effective_date": (row.get("effective_date") or "").strip(),
            "external_ref": (row.get("external_ref") or "").strip(),
            "last_reviewed": (row.get("last_reviewed") or "").strip(),
            "source": "Business architecture repository",
        }, "policies"))
    out.sort(key=lambda r: r["policy_id"])
    return out


def controls(rows: List[dict]) -> List[dict]:
    out = []
    for row in rows:
        out.append(_drop_unknown({
            "control_id": row["control_id"].strip(),
            "name": _clean(row["name"]),
            "description": _clean(row.get("description")),
            "status": row.get("status") or "Proposed",
            "togaf_layer": "Business",
            "architecture_domain": "Governance",
            "abstraction_level": "Conceptual",
            "control_type": (row.get("control_type") or "").strip(),
            "frequency": (row.get("frequency") or "").strip(),
            "regulatory_framework": _clean(row.get("regulatory_framework")),
            "policy_id": (row.get("policy_id") or "").strip(),
            "owner_org_id": (row.get("owner_org_id") or "").strip(),
            "external_ref": (row.get("external_ref") or "").strip(),
            "cri_ref": (row.get("cri_ref") or "").strip(),
            "last_reviewed": (row.get("last_reviewed") or "").strip(),
            "source": "Business architecture repository",
        }, "controls"))
    out.sort(key=lambda r: r["control_id"])
    return out


def derived_governance(
    supports: List[dict],
    governed: List[dict],
    subject: List[dict],
    caps: List[dict],
    known_controls,
    known_policies,
) -> Dict[str, List[dict]]:
    """Capability-to-control and capability-to-policy, through the processes.

    Two bases, and the row says which. `Process`: a process supporting this
    capability is governed by the control. `Descendant`: a capability below
    this one is, so the obligation sits somewhere inside this domain. Rolling
    up is what lets a system that realizes a whole domain be asked about the
    controls inside it; marking it is what stops the roll-up being mistaken
    for something the business said.
    """
    known_caps = {c["capability_id"] for c in caps}
    parent = {
        c["capability_id"]: c.get("parent_capability_id")
        for c in caps if c.get("parent_capability_id")
    }
    by_process: Dict[str, set] = {}
    for row in supports:
        by_process.setdefault(row["process_id"].strip(), set()).add(
            row["capability_id"].strip()
        )

    def ancestors(capability_id: str):
        seen = set()
        current = parent.get(capability_id)
        while current and current not in seen:
            seen.add(current)
            yield current
            current = parent.get(current)

    def join(rows: List[dict], column: str, known_targets) -> List[dict]:
        direct = set()
        for row in rows:
            target = row[column].strip()
            if target not in known_targets:
                continue
            for capability_id in by_process.get(row["process_id"].strip(), ()):
                if capability_id in known_caps:
                    direct.add((capability_id, target))
        rolled = set()
        for capability_id, target in direct:
            for ancestor in ancestors(capability_id):
                if (ancestor, target) not in direct:
                    rolled.add((ancestor, target))
        out = [
            {"capability_id": a, column: b, "basis": "Process"} for a, b in sorted(direct)
        ] + [
            {"capability_id": a, column: b, "basis": "Descendant"} for a, b in sorted(rolled)
        ]
        out.sort(key=lambda r: (r["capability_id"], r[column], r["basis"]))
        return out

    return {
        "capability_governed_by_control": join(governed, "control_id", known_controls),
        "capability_subject_to_policy": join(subject, "policy_id", known_policies),
    }


def stage_capability_rows(rows: List[dict], known_stages, known_caps) -> List[dict]:
    seen = set()
    out = []
    for row in rows:
        pair = (row["stage_id"].strip(), row["capability_id"].strip())
        if pair in seen or pair[0] not in known_stages or pair[1] not in known_caps:
            continue
        seen.add(pair)
        out.append({"stage_id": pair[0], "capability_id": pair[1]})
    out.sort(key=lambda r: (r["stage_id"], r["capability_id"]))
    return out


HEADERS = {
    "capabilities": """# The enterprise capability map.
#
# Imported from the business architecture repository by
# `50_ENGINE/tools/import_business_layer.py`. Ids are verbatim, so a capability
# means the same thing in both places; edit it there and re-run the import.
#
# `capability_level` is the map level (L0 domain, L1, L2). `abstraction_level`
# stays Conceptual throughout: a capability map is conceptual at every level of
# itself, and the two fields answer different questions.""",
    "value_streams": """# Value streams: how the enterprise actually delivers something someone wants.
#
# Imported from the business architecture repository. A value stream is not a
# process: it is stated from the point of view of whoever receives the value,
# and it ends when they have it.""",
    "value_stream_stages": """# The stages of each value stream, in order.
#
# Every stage carries the exit criterion that has to be true to leave it.
# Stages without one end up named after departments rather than after progress,
# which is how a value stream turns back into an org chart.""",
    "org_units": """# The org structure, as the business architecture repository holds it.
#
# Accountability, not reporting lines: this is what the ownership view and the
# `owner_org_id` on everything else point at.""",
    "stage_crosses_capability": """# Which capabilities each value stream stage depends on.
#
# This is the join that makes "what is on the critical path of originations"
# answerable from the model rather than from a workshop.""",
    "policies": """# The policy register, as the business architecture repository holds it.
#
# Imported by `50_ENGINE/tools/import_business_layer.py`; edit it there. A
# policy is what a control gives effect to, and what a system or a data asset
# is subject to. Nothing here says where a policy is enforced -- the controls
# under it and the `*_subject_to_policy` relations do.""",
    "controls": """# The control register, as the business architecture repository holds it.
#
# Imported by `50_ENGINE/tools/import_business_layer.py`; edit it there. A
# control is an obligation with a mechanism: something that runs, at some
# frequency, to give effect to a policy. Which systems and data assets enforce
# each one is recorded in `relations/governance.yaml`, by hand, because that
# is a fact about the estate rather than about the register.""",
    "systems_harvest": """# Systems the business layer harvested, that this estate did not hold.
#
# Imported from the business architecture repository by
# `50_ENGINE/tools/import_business_layer.py`. The processes were mapped against
# these in workshops, so they are the systems the organization actually runs
# on, drafted at low confidence and Proposed until someone who owns one
# confirms it. A system this estate already holds under another id is mapped
# in `60_SOURCES/business_layer/aliases.yaml` and does not arrive twice.
#
# To promote one: move it into its own file and give it a hosting, an
# account and a tier; editing it in the app moves it for you. The import
# leaves alone any system outside this file. Take `source` off it when its
# owner confirms it, which takes it off the harvested-estate drawing.""",
    "data_assets_harvest": """# Data assets the business layer harvested, that this estate did not hold.
#
# Imported from the business architecture repository by
# `50_ENGINE/tools/import_business_layer.py`, with the same aliasing as the
# systems. Each names the system that is its source of truth.""",
    "processes": """# The process inventory.
#
# Imported from the business architecture repository by
# `50_ENGINE/tools/import_business_layer.py`. The steps, the flows and the
# BPMN stay there; what is here is the process and what it touches, which is
# enough to draw a system's reach across the organization. Every one is
# Proposed: a straw-man drafted against the reference frameworks, waiting
# for the workshop that corrects it.""",
    "process_relations": """# What each process touches, as the business layer records it.
#
# Imported from the business architecture repository by
# `50_ENGINE/tools/import_business_layer.py`. Systems and data assets are
# mapped through `60_SOURCES/business_layer/aliases.yaml`, so a process lands
# on the id this estate uses.""",
    "realization": """# Which systems realize which capabilities, through the processes.
#
# Derived at import, never authored: a system a process uses in the Primary
# role realizes every capability that process supports. Hand-authored
# realizations live in `relations/imported_relations.yaml`; this file is the
# business layer's answer, and where the two disagree the workshop decides.""",
    "references": """# Where in each framework a capability is placed.
#
# Imported from the business architecture repository by
# `50_ENGINE/tools/import_business_layer.py`. A placement is a path in the
# framework's own terms, outermost first: BIAN's business area and domain over
# the service domain, ITIL's group of practices over the practice, CRI's
# function over the statement, the APQC category, the DMBOK knowledge area. A
# framework's landscape is drawn from these paths. How firmly a domain follows a
# framework is the other link, in relations/capability_frameworks.yaml.""",
    "governance": """# Which capabilities each control and policy governs, through the processes.
#
# Derived at import, never authored. The business layer says which processes
# a control governs and which capabilities each process supports; this is the
# join of the two. `basis: Process` means a process supporting the capability
# is governed directly. `basis: Descendant` means a capability below this one
# is, rolled up so a system that realizes a whole domain can be asked about
# the controls inside it. Do not edit; re-run the import.""",
}


#: The business layer's hosting words, in this metamodel's enum.
_HOSTING = {"Public Cloud": "", "SaaS": "SaaS", "Vendor-Hosted": "External", "On-prem": "On-prem"}
_CRITICALITY = {"Critical": "High", "High": "High", "Medium": "Medium", "Low": "Low"}
_FRAMEWORKS = {"BIAN": "FW-BIAN", "ITIL": "FW-ITIL", "CRI": "FW-CRI", "APQC": "FW-APQC",
               "DMBOK": "FW-DMBOK", "COBIT": "FW-COBIT", "NIST": "FW-NIST-CSF"}


def load_aliases(root: Path) -> dict:
    """What the two repositories call the same thing, from 60_SOURCES."""
    from terrane.loader import read_data_file

    path = root / "60_SOURCES" / "business_layer" / "aliases.yaml"
    if not path.exists():
        return {"systems": {}, "data_assets": {}, "exclude": []}
    data = read_data_file(path) or {}
    return {
        "systems": dict(data.get("systems") or {}),
        "data_assets": dict(data.get("data_assets") or {}),
        "exclude": list(data.get("exclude") or []),
    }


#: The file the harvest writes in each folder. A record anywhere else is held
#: by the estate, whatever its `source` still says: moving one out is how a
#: harvested system is promoted, and the app moves it the first time it is
#: edited. Held by `source` instead, a promoted system that kept its source
#: was harvested again beside itself and the model would not load.
HARVEST_FILE = "from_business_layer.yaml"


def existing_ids(root: Path, type_name: str) -> set:
    """The ids this estate already holds, so nothing arrives twice."""
    try:
        from terrane import model as model_module

        model = model_module.load(root)
    except Exception:  # noqa: BLE001 - a model mid-edit means no dedupe, not a crash
        return set()
    return {
        record_id for record_id, record in model.entities.get(type_name, {}).items()
        if Path(str(record.get("_source_file") or "")).name != HARVEST_FILE
    }


def harvest_systems(rows: List[dict], aliases: dict, held: set) -> List[dict]:
    out = []
    for row in rows:
        system_id = row["system_id"].strip()
        if system_id in aliases["systems"] or system_id in aliases["exclude"] or system_id in held:
            continue
        record = {
            "system_id": system_id,
            "name": _clean(row["name"]),
            "description": _clean(row.get("description")) or "Harvested from the process inventory; not yet described.",
            "status": row.get("status") or "Proposed",
            "togaf_layer": "Application",
            "architecture_domain": "Application",
            "abstraction_level": "Logical",
            "owner_org_id": (row.get("owner_org_id") or "").strip(),
            "criticality": "Medium",
            "hosting": _HOSTING.get((row.get("hosting") or "").strip(), ""),
            "provider": _clean(row.get("provider")),
            "service_tier": (row.get("service_tier") or "").strip(),
            "data_classification_supported": (row.get("data_classification_supported") or "").strip(),
            "source": "Business architecture repository",
        }
        out.append(_drop_unknown(record, "systems"))
    out.sort(key=lambda r: r["system_id"])
    return out


def harvest_data_assets(rows: List[dict], aliases: dict, held: set, known_systems: set) -> List[dict]:
    out = []
    for row in rows:
        asset_id = row["data_asset_id"].strip()
        if asset_id in aliases["data_assets"] or asset_id in held:
            continue
        sot = aliases["systems"].get(row.get("source_of_truth", "").strip(), row.get("source_of_truth", "").strip())
        record = {
            "data_asset_id": asset_id,
            "name": _clean(row["name"]),
            "description": _clean(row.get("description")),
            "status": row.get("status") or "Proposed",
            "togaf_layer": "Data",
            "architecture_domain": "Data",
            "abstraction_level": "Logical",
            "classification": (row.get("classification") or "").strip(),
            "pii_flag": (row.get("pii_flag") or "").strip(),
            "risk_level": (row.get("risk_level") or "").strip(),
            "data_owner_org_id": (row.get("data_owner_org_id") or "").strip(),
            "data_steward_org_id": (row.get("data_steward_org_id") or "").strip(),
            "source_of_truth": sot if sot in known_systems else "",
            "source": "Business architecture repository",
        }
        out.append(_drop_unknown(record, "data_assets"))
    out.sort(key=lambda r: r["data_asset_id"])
    return out


def processes(rows: List[dict], known_streams: set, known_orgs: set) -> List[dict]:
    out = []
    for row in rows:
        stream = (row.get("value_stream_id") or "").strip()
        owner = (row.get("owner_org_id") or "").strip()
        record = {
            "process_id": row["process_id"].strip(),
            "name": _clean(row["name"]),
            "description": _clean(row.get("description")),
            "status": row.get("status") or "Proposed",
            "togaf_layer": "Business",
            "architecture_domain": "Business",
            "abstraction_level": "Logical",
            "process_level": (row.get("abstraction_level") or "").strip(),
            "value_stream_id": stream if stream in known_streams else "",
            "owner_org_id": owner if owner in known_orgs else "",
            "business_unit": _clean(row.get("business_unit")),
            "criticality": _CRITICALITY.get((row.get("criticality") or "").strip(), ""),
            "risk_level": (row.get("risk_level") or "").strip(),
            "trigger": (row.get("trigger") or "").strip(),
            "frequency": (row.get("frequency") or "").strip(),
            "rto_hours": "" if (row.get("rto_hours") or "").startswith("NO-") else (row.get("rto_hours") or "").strip(),
            "rpo_hours": "" if (row.get("rpo_hours") or "").startswith("NO-") else (row.get("rpo_hours") or "").strip(),
            "data_classification": (row.get("data_classification") or "").strip(),
            "pii_flag": (row.get("pii_flag") or "").strip(),
            "last_reviewed": (row.get("last_reviewed") or "").strip(),
            "source": "Business architecture repository",
        }
        out.append(_drop_unknown(record, "processes"))
    out.sort(key=lambda r: r["process_id"])
    return out


def process_relations(seed: Path, aliases: dict, known: Dict[str, set]) -> Dict[str, List[dict]]:
    """The five relations a process carries, with ids mapped and unknowns dropped."""
    def mapped(kind: str, value: str) -> str:
        value = (value or "").strip()
        if value in aliases["exclude"]:
            return ""
        if kind == "systems":
            value = aliases["systems"].get(value, value)
        if kind == "data_assets":
            value = aliases["data_assets"].get(value, value)
        return value if value in known[kind] else ""

    out: Dict[str, List[dict]] = {}
    seen = set()

    def add(name: str, row: dict) -> None:
        key = (name,) + tuple(row.values())
        if key in seen:
            return
        seen.add(key)
        out.setdefault(name, []).append(row)

    for row in _rows(seed / "relations" / "process_supports_capability.csv"):
        p, c = row["process_id"].strip(), row["capability_id"].strip()
        if p in known["processes"] and c in known["capabilities"]:
            add("process_supports_capability", {"process_id": p, "capability_id": c})
    for row in _rows(seed / "relations" / "process_uses_system.csv"):
        p, s_id = row["process_id"].strip(), mapped("systems", row["system_id"])
        if p in known["processes"] and s_id:
            add("process_uses_system", {"process_id": p, "system_id": s_id, "role": (row.get("role") or "").strip()})
    for row in _rows(seed / "relations" / "process_uses_data_asset.csv"):
        p, d = row["process_id"].strip(), mapped("data_assets", row["data_asset_id"])
        if p in known["processes"] and d:
            add("process_uses_data_asset", {"process_id": p, "data_asset_id": d, "access": (row.get("access") or "").strip()})
    for row in _rows(seed / "relations" / "process_governed_by_control.csv"):
        p, c = row["process_id"].strip(), row["control_id"].strip()
        if p in known["processes"] and c in known["controls"]:
            add("process_governed_by_control", {"process_id": p, "control_id": c})
    for row in _rows(seed / "relations" / "process_subject_to_policy.csv"):
        p, pol = row["process_id"].strip(), row["policy_id"].strip()
        if p in known["processes"] and pol in known["policies"]:
            add("process_subject_to_policy", {"process_id": p, "policy_id": pol})
    return out


def derived_realization(relations: Dict[str, List[dict]]) -> List[dict]:
    """A system used in the Primary role realizes what the process supports."""
    supports: Dict[str, List[str]] = {}
    for row in relations.get("process_supports_capability", []):
        supports.setdefault(row["process_id"], []).append(row["capability_id"])
    pairs = set()
    for row in relations.get("process_uses_system", []):
        if row.get("role") != "Primary":
            continue
        for capability_id in supports.get(row["process_id"], []):
            pairs.add((row["system_id"], capability_id))
    return [{"system_id": s_id, "capability_id": c} for s_id, c in sorted(pairs)]



#: Between the levels of a placement: "Sales and Service > Sales > Customer
#: Offer". Not a slash, which BIAN already uses inside a service domain's own
#: name ("Card Authorization / Fraud Check").
PATH = " > "

#: ITIL 4's three groups of practices, which the practice's name places it in.
ITIL_GROUPS = {
    "General management": (
        "Architecture Management", "Continual Improvement", "Information Security Management",
        "Knowledge Management", "Measurement and Reporting", "Organizational Change Management",
        "Portfolio Management", "Project Management", "Relationship Management", "Risk Management",
        "Service Financial Management", "Strategy Management", "Supplier Management",
        "Workforce and Talent Management",
    ),
    "Service management": (
        "Availability Management", "Business Analysis", "Capacity and Performance Management",
        "Change Enablement", "Incident Management", "IT Asset Management", "Monitoring and Event Management",
        "Problem Management", "Release Management", "Service Catalog Management",
        "Service Configuration Management", "Service Continuity Management", "Service Design", "Service Desk",
        "Service Level Management", "Service Request Management", "Service Validation and Testing",
    ),
    "Technical management": (
        "Deployment Management", "Infrastructure and Platform Management", "Software Development and Management",
    ),
}

#: The CRI Profile's functions, by the first two letters of a statement's code.
CRI_FUNCTIONS = {"GV": "Govern", "ID": "Identify", "PR": "Protect", "DE": "Detect", "RS": "Respond",
                 "RC": "Recover", "EX": "Extend"}


def _many(value) -> List[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def bian_places(capability_rows: Iterable[dict]) -> Dict[str, tuple]:
    """Each BIAN service domain's business area and domain, as the business
    layer records them. The layer sometimes puts one service domain in two
    places (Underwriting is in three); a service domain sits in one, so the
    place most records give it wins, and a tie goes to the first seen. Read
    from the layer's own words, never from a copy of BIAN's classification
    this repository has no license to hold."""
    votes: Dict[str, Dict[tuple, int]] = {}
    for row in capability_rows:
        areas, domains = _many(row.get("bian_business_area")), _many(row.get("bian_business_domain"))
        services = _many(row.get("bian_service_domains"))
        if not services or not domains:
            continue
        if len(domains) == 1:
            pairs = [(areas[0] if len(areas) == 1 else "", domains[0], s) for s in services]
        elif len(domains) == len(services) and len(areas) in (1, len(domains)):
            pairs = [(areas[0] if len(areas) == 1 else areas[i], domains[i], s) for i, s in enumerate(services)]
        else:
            continue
        for area, domain, service in pairs:
            if area:
                tally = votes.setdefault(service, {})
                tally[(area, domain)] = tally.get((area, domain), 0) + 1
    return {service: max(tally, key=lambda place: tally[place]) for service, tally in votes.items()}


def term_path(framework_id: str, term: str, capability: dict, places: Dict[str, tuple]) -> str:
    """Where in a framework a placement sits, outermost first: BIAN's
    business area and domain over the service domain, ITIL's group of
    practices over the practice, CRI's function over the statement. A term
    whose place is not known stands alone, which a landscape draws under
    its own name rather than in a guessed area."""
    term = str(term or "").strip()
    if not term or PATH.strip() in term:
        return term
    if framework_id == "FW-BIAN":
        service = term.split(" / ", 1)[0].strip()
        place = places.get(term) or places.get(service)
        if place is None:
            areas, domains = _many(capability.get("bian_business_area")), _many(capability.get("bian_business_domain"))
            if len(areas) == 1 and len(domains) == 1:
                place = (areas[0], domains[0])
        return PATH.join(list(place) + [term]) if place else term
    if framework_id == "FW-ITIL":
        group = next((g for g, practices in ITIL_GROUPS.items() if term in practices), "")
        return PATH.join([group, term]) if group else term
    if framework_id == "FW-CRI":
        function = CRI_FUNCTIONS.get(term[:2].upper(), "")
        return PATH.join([function, term]) if function else term
    return term


def place_references(references: List[dict], capability_rows: List[dict]) -> List[dict]:
    """The references with each term written as its path."""
    places = bian_places(capability_rows)
    by_id = {str(row.get("capability_id") or "").strip(): row for row in capability_rows}

    def placed_by(capability_id: str) -> dict:
        """The nearest capability up the tree that says where it sits in
        BIAN: a level-2 capability usually does not, and its parent does."""
        seen = set()
        while capability_id and capability_id not in seen:
            seen.add(capability_id)
            row = by_id.get(capability_id, {})
            if row.get("bian_business_area"):
                return row
            capability_id = str(row.get("parent_capability_id") or "").strip()
        return {}

    out = []
    for row in references:
        placed = dict(row)
        placed["ref"] = term_path(row["framework_id"], row["ref"], placed_by(row["capability_id"]), places)
        out.append(placed)
    return out

def capability_references(rows: List[dict], known_caps: set, known_frameworks: set) -> List[dict]:
    out = []
    seen = set()
    for row in rows:
        cap = row["capability_id"].strip()
        fw = _FRAMEWORKS.get((row.get("framework") or "").strip(), "")
        ref = _clean(row.get("ref"))
        if cap not in known_caps or fw not in known_frameworks or not ref:
            continue
        key = (cap, fw, ref)
        if key in seen:
            continue
        seen.add(key)
        out.append({"capability_id": cap, "framework_id": fw, "ref": ref})
    return out


def write_relation_file(path: Path, header: str, relations: Dict[str, List[dict]]) -> int:
    lines = [header]
    total = 0
    for relation_name in sorted(relations):
        rows = relations[relation_name]
        if not rows:
            continue
        lines.append("")
        lines.append("%s:" % relation_name)
        for row in rows:
            first = True
            for key, value in row.items():
                if value in (None, ""):
                    continue
                lines.append("%s%s: %s" % ("  - " if first else "    ", key, _yaml_scalar(value)))
                first = False
            total += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return total


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="source", required=True,
                        help="path to the business architecture repository")
    parser.add_argument("--seed", default="30_SEED_DATA",
                        help="folder inside it holding the CSVs")
    args = parser.parse_args(argv)

    seed = (Path(args.source) / args.seed).resolve()
    model = ROOT / "10_MODEL"

    capability_rows = _rows(seed / "capabilities.csv")
    caps = capabilities(capability_rows)
    streams = value_streams(_rows(seed / "value_streams.csv"))
    stage_rows = stages(_rows(seed / "value_stream_stages.csv"))
    orgs = org_units(_rows(seed / "org_units.csv"))
    crossings = stage_capability_rows(
        _rows(seed / "relations" / "stage_crosses_capability.csv"),
        {s["stage_id"] for s in stage_rows},
        {c["capability_id"] for c in caps},
    )

    policy_rows = policies(_rows(seed / "policies.csv"))
    control_rows = controls(_rows(seed / "controls.csv"))
    governance = derived_governance(
        _rows(seed / "relations" / "process_supports_capability.csv"),
        _rows(seed / "relations" / "process_governed_by_control.csv"),
        _rows(seed / "relations" / "process_subject_to_policy.csv"),
        caps,
        {c["control_id"] for c in control_rows},
        {p["policy_id"] for p in policy_rows},
    )

    written = [
        ("capabilities/capability_map.yaml", HEADERS["capabilities"], caps),
        ("value_streams/value_streams.yaml", HEADERS["value_streams"], streams),
        ("value_stream_stages/stages.yaml", HEADERS["value_stream_stages"], stage_rows),
        ("org_units/org_units.yaml", HEADERS["org_units"], orgs),
        ("policies/policies.yaml", HEADERS["policies"], policy_rows),
        ("controls/controls.yaml", HEADERS["controls"], control_rows),
    ]
    for rel, header, records in written:
        count = write_records(model / rel, header, records)
        print("%-40s %d records" % (rel, count))

    relation_path = model / "relations" / "value_stream_capabilities.yaml"
    lines = [HEADERS["stage_crosses_capability"], "", "stage_crosses_capability:"]
    for row in crossings:
        lines.append("  - stage_id: %s" % row["stage_id"])
        lines.append("    capability_id: %s" % row["capability_id"])
    relation_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("%-40s %d rows" % ("relations/value_stream_capabilities.yaml", len(crossings)))

    # The estate side of the business layer: the systems and data the
    # processes were mapped against, the processes, and what each touches.
    aliases = load_aliases(ROOT)
    held_systems = existing_ids(ROOT, "systems")
    held_assets = existing_ids(ROOT, "data_assets")
    harvested = harvest_systems(_rows(seed / "systems.csv"), aliases, held_systems)
    known_systems = held_systems | {r["system_id"] for r in harvested} | set(aliases["systems"].values())
    assets = harvest_data_assets(_rows(seed / "data_assets.csv"), aliases, held_assets, known_systems)
    known_assets = held_assets | {r["data_asset_id"] for r in assets} | set(aliases["data_assets"].values())
    process_rows = processes(
        _rows(seed / "processes.csv"),
        {v["value_stream_id"] for v in streams},
        {o["org_unit_id"] for o in orgs},
    )
    known = {
        "processes": {p["process_id"] for p in process_rows},
        "capabilities": {c["capability_id"] for c in caps},
        "systems": known_systems,
        "data_assets": known_assets,
        "controls": {c["control_id"] for c in control_rows},
        "policies": {p["policy_id"] for p in policy_rows},
    }
    touches = process_relations(seed, aliases, known)
    realization = derived_realization(touches)
    frameworks_held = existing_ids(ROOT, "frameworks")
    references = place_references(capability_references(
        _rows(seed / "relations" / "capability_reference.csv"), known["capabilities"], frameworks_held,
    ), capability_rows)
    for rel, header, records in (
        ("systems/from_business_layer.yaml", HEADERS["systems_harvest"], harvested),
        ("data_assets/from_business_layer.yaml", HEADERS["data_assets_harvest"], assets),
        ("processes/processes.yaml", HEADERS["processes"], process_rows),
    ):
        count = write_records(model / rel, header, records)
        print("%-40s %d records" % (rel, count))
    for rel, header, relations in (
        ("relations/processes_from_business_layer.yaml", HEADERS["process_relations"], touches),
        ("relations/realization_from_business_layer.yaml", HEADERS["realization"],
         {"system_realizes_capability": realization}),
        ("relations/capability_references.yaml", HEADERS["references"],
         {"capability_references_framework": references}),
    ):
        count = write_relation_file(model / rel, header, relations)
        print("%-40s %d rows" % (rel, count))

    governance_path = model / "relations" / "governance_from_business_layer.yaml"
    lines = [HEADERS["governance"]]
    for relation_name, rows in governance.items():
        lines.append("")
        lines.append("%s:" % relation_name)
        for row in rows:
            first = True
            for key, value in row.items():
                lines.append("%s%s: %s" % ("  - " if first else "    ", key, value))
                first = False
    governance_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("%-40s %d rows" % (
        "relations/governance_from_business_layer.yaml",
        sum(len(rows) for rows in governance.values()),
    ))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
