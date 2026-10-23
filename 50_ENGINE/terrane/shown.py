"""What the pictures show, as a sketch.

A deck goes to a reviewer; the workbook beside it should hold what the
slides show and nothing else, so the reviewer corrects a name or an owner
in Excel and the corrected workbook comes back as the same pages. This
collects, as the views are drawn, the records on each picture, the
connections the model has among them, and a page per picture saying what
it shows by id and which lines, as the sketch the workbook writer takes
(`Drawings.excel`, `terrane pack --excel`). A register is a table, not a page
of records, and is said and left out; a view's styling is the method's
default once read back, since styling is not a cell; and a product on a
shape travels as the records the shape made, the shape itself said and
left out, since the pictures show the expansion done.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .compose import COMPOSE_KEY
from .exports import _clean
from .model import Model
from .query import View, ViewGraph
from .schema import ENTITY_TYPES, RELATION_TYPES

#: What an instance says to be expanded by a shape or assembled from parts.
#: On the pictures the expansion has happened; the workbook holds what it
#: made, so these are not written, or the loader would make it all again
#: beside the records that are already there.
INSTANCE_KEYS = ("archetype", COMPOSE_KEY, "parameters", "modules", "overrides", "exclude", "extra", "without")
#: Where a record made by a shape says it came from.
MADE_BY_SHAPE = ("archetype", "archetype_instance", "module")


class Shown:
    """The records on the pictures drawn so far, and a page per picture."""

    def __init__(self, model: Model, name: str) -> None:
        self.model = model
        self.name = name
        self.records: Dict[str, Dict[str, dict]] = {}
        self.pages: List[dict] = []
        self.notes: List[str] = []

    def _keep(self, type_name: str, entity_id: str) -> None:
        record = self.model.get(type_name, entity_id)
        if record is not None:
            self.records.setdefault(type_name, {})[entity_id] = record

    def view(self, name: str, view: View, graph: ViewGraph, subjects: Optional[Dict[str, str]] = None) -> None:
        """A picture drawn: its records kept and a page written for it.
        `name` is the view id with its subject, as the drawing is named,
        so two subjects of one view are two pages; `subjects` is what the
        view was told, by parameter name, and travels too, since a page
        about a product shows the product's systems and not the product."""
        if view.kind == "report":
            self.notes.append("%s: a register is a table, not a page of records; not in the workbook" % name)
            return
        for value in (subjects or {}).values():
            # An id names its type; the bound view may no longer say it.
            type_name = next((t for t in ENTITY_TYPES if self.model.get(t, str(value)) is not None), None)
            if type_name is not None:
                self._keep(type_name, str(value))
        by_type: Dict[str, List[str]] = {}
        for node in graph.nodes:
            self.records.setdefault(node.entity_type, {})[node.key] = node.record
            by_type.setdefault(node.entity_type, []).append(node.key)
        page: dict = {
            "view_id": name, "title": view.title, "kind": view.kind, "layout": view.layout,
            "description": view.description,
            "scope": {"include": [{"type": t, "where": {"id_in": by_type[t]}} for t in ENTITY_TYPES if t in by_type]},
            "edges": [dict(edge) for edge in view.edges],
        }
        if view.group_by:
            page["group_by"] = list(view.group_by) if len(view.group_by) > 1 else view.group_by[0]
        self.pages.append(page)

    def flow(self, flow_id: str) -> None:
        """A flow drawn: the flow, the interfaces it steps through and the
        systems at their ends, the faces of the sequence diagram."""
        self._keep("flows", flow_id)
        for row in self.model.relation_rows("flow_step"):
            if str(row.get("flow_id")) != flow_id:
                continue
            interface = self.model.get("interfaces", str(row.get("interface_id")))
            if interface is None:
                continue
            self.records.setdefault("interfaces", {})[str(row["interface_id"])] = interface
            for end in ("source_system_id", "target_system_id"):
                if interface.get(end):
                    self._keep("systems", str(interface[end]))

    def _referenced(self) -> None:
        """What the records point at by a reference field comes along, to
        a fixpoint: a system's owner is an org unit on no picture, and a
        sketch read back with every owner dangling is a sketch of a
        mistake. Said once, with the count, since it is more than the
        pictures show."""
        came_along: Dict[str, int] = {}
        pending = True
        while pending:
            pending = False
            for type_name in list(self.records):
                refs = [f for f in ENTITY_TYPES[type_name].fields if f.ref in ENTITY_TYPES]
                for record in list(self.records[type_name].values()):
                    for field in refs:
                        value = record.get(field.name)
                        targets = [str(v) for v in value] if isinstance(value, (list, tuple)) else ([str(value)] if value else [])
                        for target in targets:
                            if target in self.records.get(field.ref, {}):
                                continue
                            found = self.model.get(field.ref, target)
                            if found is not None:
                                self.records.setdefault(field.ref, {})[target] = found
                                came_along[field.ref] = came_along.get(field.ref, 0) + 1
                                pending = True
        if came_along:
            note = "%d record(s) the pictures do not show came along, since what is shown points at them: %s" % (
                sum(came_along.values()),
                ", ".join("%d %s" % (n, t.replace("_", " ")) for t, n in sorted(came_along.items())))
            if note not in self.notes:
                self.notes.append(note)

    def sketch(self) -> dict:
        """The records, the connections the model has among them, and the
        pages, as a sketch. An interface between two systems on the
        pictures is on them too, as the line it draws, and what the
        records point at comes along."""
        systems = self.records.get("systems", {})
        for interface in self.model.all_of("interfaces"):
            if interface.get("source_system_id") in systems and interface.get("target_system_id") in systems:
                self.records.setdefault("interfaces", {})[str(interface["interface_id"])] = interface
        # After the interfaces, so their owners come along too.
        self._referenced()
        ids = {entity_id: type_name for type_name, records in self.records.items() for entity_id in records}
        doc: dict = {"model": {"name": self.name}}
        for type_name in ENTITY_TYPES:
            records = self.records.get(type_name)
            if not records:
                continue
            rows: List[dict] = []
            on_shapes: List[str] = []
            assembled: List[str] = []
            for entity_id in sorted(records):
                record = _clean(records[entity_id])
                if record.get("archetype_instance"):
                    # Made by a shape: the record travels as what it is now.
                    for key in MADE_BY_SHAPE:
                        record.pop(key, None)
                elif record.get("archetype") or record.get(COMPOSE_KEY):
                    (on_shapes if record.get("archetype") else assembled).append(entity_id)
                    for key in INSTANCE_KEYS:
                        record.pop(key, None)
                rows.append(record)
            doc[type_name] = rows
            # One line per type, not per product: the pack of this estate
            # said it twelve times before the path of the workbook.
            for ids_on, how in ((on_shapes, "on a shape"), (assembled, "assembled from parts")):
                if ids_on:
                    label = ENTITY_TYPES[type_name].label
                    note = "%d %s %s (%s); the workbook holds what the shapes made, not the shapes" % (
                        len(ids_on), label if len(ids_on) == 1 else label + "s", how, ", ".join(ids_on))
                    if note not in self.notes:
                        self.notes.append(note)
        relations: Dict[str, List[dict]] = {}
        for relation, spec in RELATION_TYPES.items():
            rows = [dict(row) for row in self.model.relation_rows(relation)
                    if ids.get(str(row.get(spec.left_column))) == spec.left
                    and ids.get(str(row.get(spec.right_column))) == spec.right]
            if rows:
                relations[relation] = rows
        if relations:
            doc["relations"] = relations
        doc["views"] = list(self.pages)
        return doc
