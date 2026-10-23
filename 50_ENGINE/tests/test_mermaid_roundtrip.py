"""The engine's own Mermaid, read back whole.

`terrane render` writes every view as a Mermaid flowchart with a `class`
statement typing every node and the method's words on every arrow. The
reader has to take all of it back without a complaint: every node as a
record of its type with the id it had, every arrow as the interface, the
reference field or the relation of the schema it stands for. The committed
files under `70_ARTIFACTS/mermaid/` are the corpus, 244 flowcharts; the one
Gantt chart, the roadmap, is not a flowchart and is refused by name. Three
of the sketches are drawn, since reading is only half the trip.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.mermaid_import import CLASS, MermaidError, _type_from_class, sketch_from_mermaid  # noqa: E402
from terrane.quick import render_sketch  # noqa: E402
from terrane.schema import ENTITY_TYPES  # noqa: E402

MERMAID = Path(__file__).resolve().parents[2] / "70_ARTIFACTS" / "mermaid"
COMPLAINT = re.compile(r"could not read|left out|never declared|not kept")
ARROW = re.compile(r"^\s*[A-Za-z0-9_]+\s*(?:-->|-\.->|==>|---|-\.-)")


def _flowcharts():
    return [p for p in sorted(MERMAID.glob("*.mmd"))
            if any(line.strip().startswith(("flowchart", "graph")) for line in p.read_text(encoding="utf-8").splitlines())]


class TestRoundTrip(unittest.TestCase):
    def test_there_is_a_corpus(self) -> None:
        self.assertGreater(len(_flowcharts()), 200)

    def test_every_flowchart_reads_back_without_a_word(self) -> None:
        for path in _flowcharts():
            text = path.read_text(encoding="utf-8")
            doc, notes = sketch_from_mermaid(text, name=path.stem)
            with self.subTest(path.name):
                self.assertFalse([n for n in notes if COMPLAINT.search(n)], notes)
                # The nodes the engine typed with a class (the boundaries get
                # a styling class too, which names no type) are the records
                # of those types; the interfaces are the arrows, not nodes.
                classed = set()
                for line in text.splitlines():
                    m = CLASS.match(line.strip().rstrip(";"))
                    if m and _type_from_class(m.group("name")):
                        classed.update(i for i in re.split(r"[,\s]+", m.group("ids")) if i)
                records = sum(len(doc.get(t) or []) for t in ENTITY_TYPES if t != "interfaces")
                self.assertEqual(records, len(classed), "every classed node is a record")
                # Every arrow is a connection, and the ids are the estate's own.
                arrows = sum(1 for line in text.splitlines() if ARROW.match(line))
                self.assertIn("%d connection(s)" % arrows, notes[0])
                for type_name in ENTITY_TYPES:
                    for record in doc.get(type_name) or []:
                        self.assertNotRegex(str(record[ENTITY_TYPES[type_name].pk]), r"^([A-Z]+)-\1-", "no doubled prefix")
                        # A name is the words, not the shape's quotes or slashes;
                        # its own parentheses (`Lending VPC (DR)`) are its own.
                        self.assertNotRegex(str(record.get("name") or ""), r'^[\\"/]|[\\"/]$', record)

    def test_the_roadmap_is_not_a_flowchart_and_is_refused(self) -> None:
        gantt = [p for p in sorted(MERMAID.glob("*.mmd")) if p not in _flowcharts()]
        self.assertEqual([p.stem for p in gantt], ["change-roadmap"])
        with self.assertRaises(MermaidError):
            sketch_from_mermaid(gantt[0].read_text(encoding="utf-8"))

    def test_three_of_the_sketches_draw(self) -> None:
        for name in ("application-landscape", "system-context", "capability-alignment--cap-bill"):
            doc, _notes = sketch_from_mermaid((MERMAID / (name + ".mmd")).read_text(encoding="utf-8"), name=name)
            drawings = render_sketch(doc)
            with self.subTest(name):
                self.assertIn("imported", drawings)
                self.assertTrue(drawings["imported"].svg.startswith("<svg"))
                self.assertFalse([n for n in drawings.notes if "not drawn" in n], drawings.notes)


if __name__ == "__main__":
    unittest.main()
