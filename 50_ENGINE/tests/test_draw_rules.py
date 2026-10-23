"""Two small rules of the drawing, held on their own: a port under a
boundary's name moves along its side to clear the name, and a label never
lies along another edge's line, though one may pass under it crosswise.

Both came from one picture, the C4 sample read as a sketch: the line into
the top-left node ran through the boundary's name whatever the name cost,
since the last piece into the port had nowhere else to be, and a protocol
label set along a vertical run lay across the line beside it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.draw.labels import place_labels, piece  # noqa: E402
from terrane.draw.router import FAN_INSET, NAME_CLEAR, _off_the_name  # noqa: E402


class TestPortClearsTheName(unittest.TestCase):
    NAME = (80.0, 10.0, 150.0, 40.0)   # a boundary's name box, top-left of the boundary
    NODE = (60.0, 30.0, 300.0, 100.0)  # the node under it

    def test_a_top_port_under_the_name_moves_past_its_far_end(self) -> None:
        port = (100.0, 20.0)
        moved = _off_the_name(port, "y", [self.NAME], self.NODE)
        self.assertEqual(moved, (self.NAME[2] + NAME_CLEAR, 20.0))

    def test_a_port_already_clear_stays(self) -> None:
        port = (200.0, 20.0)
        self.assertEqual(_off_the_name(port, "y", [self.NAME], self.NODE), port)

    def test_a_short_side_moves_back_past_the_near_end_or_not_at_all(self) -> None:
        # The side ends before the far end of the name: back past the near end.
        node = (60.0, 30.0, 140.0, 100.0)
        moved = _off_the_name((100.0, 20.0), "y", [self.NAME], node)
        self.assertEqual(moved, (self.NAME[0] - NAME_CLEAR, 20.0))
        # The whole side is under the name: left where it is.
        under = (85.0, 30.0, 145.0, 100.0)
        self.assertEqual(_off_the_name((100.0, 20.0), "y", [self.NAME], under), (100.0, 20.0))
        self.assertGreater(FAN_INSET, 0)

    def test_a_side_port_in_the_band_moves_down(self) -> None:
        # The name starts at the boundary's left edge, so a left port of the
        # corner node, a margin out from the node, is inside it.
        name = (30.0, 10.0, 150.0, 40.0)
        port = (50.0, 25.0)
        moved = _off_the_name(port, "x", [name], (60.0, 15.0, 300.0, 100.0))
        self.assertEqual(moved, (50.0, name[3] + NAME_CLEAR))


def _edge(edge_id: str, label: str) -> dict:
    return {"id": edge_id, "source": "S-" + edge_id, "target": "T-" + edge_id, "label": label, "kind": "calls"}


class TestLabelKeepsOffTheLines(unittest.TestCase):
    def test_a_label_never_lies_along_another_line(self) -> None:
        # Two lines side by side in a corridor between nodes too narrow for
        # an upright label: turned along its own line, the label would lie
        # along the neighbor too, so it shows nothing.
        own = piece(100.0, 0.0, 100.0, 300.0)
        beside = piece(104.0, 0.0, 104.0, 300.0)
        walls = [(0.0, 0.0, 85.0, 300.0), (115.0, 0.0, 300.0, 300.0)]
        placed = place_labels([_edge("a", "sync, JDBC over the wire"), _edge("b", "")],
                              {"a": [own], "b": [beside]}, {"a": (100.0, 150.0), "b": (104.0, 150.0)}, walls, [])
        self.assertEqual(placed, [])
        # Alone in the corridor, the same label turns along its line.
        alone = place_labels([_edge("a", "sync, JDBC over the wire")], {"a": [own]}, {"a": (100.0, 150.0)}, walls, [])
        self.assertEqual([(p.edge_id, p.turned) for p in alone], [("a", True)])

    def test_a_line_may_pass_under_a_label_crosswise(self) -> None:
        own = piece(100.0, 0.0, 100.0, 300.0)
        across = piece(0.0, 150.0, 300.0, 150.0)
        placed = place_labels([_edge("a", "sync, JDBC over the wire"), _edge("b", "")],
                              {"a": [own], "b": [across]}, {"a": (100.0, 150.0), "b": (150.0, 150.0)}, [], [])
        self.assertEqual([p.edge_id for p in placed], ["a"])

    def test_a_clear_run_takes_the_label_at_its_midpoint(self) -> None:
        own = piece(0.0, 100.0, 300.0, 100.0)
        placed = place_labels([_edge("a", "HTTPS")], {"a": [own]}, {"a": (150.0, 100.0)}, [], [])
        self.assertEqual(len(placed), 1)
        self.assertEqual((placed[0].x, placed[0].y, placed[0].turned), (150.0, 100.0, False))


if __name__ == "__main__":
    unittest.main()
