"""The technology line under a node's name.

The C4 model asks every container to show its technology, and a reader of a
cloud diagram expects a box to say what it runs on. Here it is read from the
model rather than typed: a technology service says the product behind it or
the kind of thing it is; a system says the platform services it uses, the
compute first and the data after, unless the system is a data system, whose
data services are the point; a bought system says it is bought.
"""

from __future__ import annotations

from typing import Dict, List, Optional

#: The categories of technology service that are a system's own technology,
#: in the order worth saying them: what runs it, then what it talks through,
#: then what it keeps its data in. Network, security and operations services
#: are the estate's rather than the system's, and would make every box say
#: "VPC".
_PLATFORM_ORDER = {"Compute": 0, "Application": 1, "Integration": 2, "Data": 3, "Storage": 4}

#: A pipeline, an analytics layer or a datastore is its data services first:
#: the warehouse a pipeline fills says more about it than the queue it reads.
_DATA_FIRST = {"Data": 0, "Compute": 1, "Application": 2, "Integration": 3, "Storage": 4}
_DATA_SYSTEMS = {"Pipeline", "Analytics", "Datastore"}

#: Within a category, the kinds that say least about a system go last: a
#: catalog registers its data and a scheduler runs its jobs, and neither is
#: what it is made of. Alphabetical after that, in both the repository and
#: an export of it.
_KIND_RANK = {"catalog": 3, "workflow": 2}

#: How many services a line names before it counts the rest.
_NAMED = 2

#: Hosting words that are the technology of a system using no platform
#: service of ours: a bought thing is bought.
_BOUGHT = {"SaaS": "SaaS", "External": "external"}


class TechnologyLines:
    """What to write under each node's name, for one model."""

    def __init__(self, model, components: Dict[str, object]) -> None:
        self._components = components or {}
        self._services = {str(r.get("tech_service_id")): r for r in model.all_of("tech_services")}
        self._uses: Dict[str, List[str]] = {}
        for row in model.relation_rows("system_uses_tech_service"):
            self._uses.setdefault(str(row.get("system_id")), []).append(str(row.get("tech_service_id")))

    def of(self, entity_type: str, record: dict) -> str:
        if entity_type == "tech_services":
            return self._service_line(record)
        if entity_type == "systems":
            return self._system_line(record)
        if entity_type == "offered_interfaces":
            # What it is spoken in, said once for every line through it.
            return str(record.get("protocol") or "").strip()
        return ""

    def _service_line(self, record: dict) -> str:
        name = str(record.get("name") or "").strip()
        product = str(record.get("product") or "").strip()
        if product and product.lower() != name.lower():
            return product
        component = self._components.get(str(record.get("component_type") or ""))
        kind = str(getattr(component, "name", "") or "").strip()
        return kind if kind and kind.lower() != name.lower() else ""

    def lead(self, record: dict) -> Optional[dict]:
        """The platform service a system's line names first, which is the
        mark it wears when it carries none of its own: what it runs on, or
        for a data system what it keeps its data in."""
        services = self._platform(record)
        return services[0] if services else None

    def _platform(self, record: dict) -> List[dict]:
        """The system's platform services in the order its line says them,
        one per name."""
        found = []
        seen = set()
        order = _DATA_FIRST if str(record.get("system_category") or "") in _DATA_SYSTEMS else _PLATFORM_ORDER
        for service_id in self._uses.get(str(record.get("system_id")), []):
            service = self._services.get(service_id)
            if service is None:
                continue
            component = self._components.get(str(service.get("component_type") or ""))
            category = str(getattr(component, "category", "") or "")
            if category not in order:
                continue
            short = str(service.get("service_name") or service.get("name") or "").strip()
            if not short or short.lower() in seen:
                continue
            seen.add(short.lower())
            kind = str(service.get("component_type") or "")
            found.append((order[category], _KIND_RANK.get(kind, 0), short, service_id))
        found.sort(key=lambda item: item[:3])
        return [self._services[item[-1]] for item in found]

    def _system_line(self, record: dict) -> str:
        names = [str(s.get("service_name") or s.get("name") or "").strip() for s in self._platform(record)]
        if names:
            return _said(names)
        # A bought system names its vendor, which is its technology: a
        # mark where the vendor lets one travel, and the name here always.
        vendor = str(record.get("provider") or "").strip()
        if vendor and vendor.lower() != "in-house":
            return vendor
        return _BOUGHT.get(str(record.get("hosting") or ""), "")


#: A line longer than this is a second name, not a second line: name fewer
#: and count the rest.
_WIDTH = 36


def _said(names: List[str]) -> str:
    """The first names and a count of the rest, as many as fit the line."""
    for named in range(min(_NAMED, len(names)), 0, -1):
        line = " · ".join(names[:named])
        if len(names) > named:
            line += " +%d" % (len(names) - named)
        if len(line) <= _WIDTH or named == 1:
            return line
    return names[0]
