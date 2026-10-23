"""The patterns page carries the pictures of the blocks each pattern is made
of: under *Made of*, one drawing per block that has one, the same path the
blocks page uses, and nothing where the pictures were not given."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.blocks import load_blocks, load_components, load_patterns  # noqa: E402
from terrane.pictures import Pictures  # noqa: E402
from terrane.render_library import render_patterns  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class TestPatternsPictured(unittest.TestCase):
    def test_each_block_a_pattern_is_made_of_is_pictured_under_it(self) -> None:
        components = load_components(ROOT)
        blocks = load_blocks(ROOT, components)
        patterns = load_patterns(ROOT, blocks)
        pictured = {block_id: "svg/block--%s.svg" % block_id for block_id in blocks}
        pictures = Pictures(shapes={}, kits={}, notes={}, written=[], blocks=pictured)
        page = render_patterns(patterns, blocks, components, None, pictures)
        plain = render_patterns(patterns, blocks, components, None)
        self.assertNotIn("![", plain)
        shown = [line for line in page.splitlines() if line.startswith("![")]
        wanted = sum(len([b for b in p.blocks if b in pictured]) for p in patterns.values())
        self.assertEqual(len(shown), wanted)
        self.assertGreater(wanted, len(patterns) // 2)
        # The picture sits in the pattern's own section, after what it is made of.
        first = next(p for p in patterns.values() if any(b in pictured for b in p.blocks))
        section = page.split('<a id="%s"></a>' % first.pattern_id, 1)[1].split('\n<a id="', 1)[0]
        self.assertIn("**Made of.**", section)
        self.assertIn("](svg/block--%s.svg)" % next(b for b in first.blocks if b in pictured), section)
        self.assertLess(section.index("**Made of.**"), section.index("]("))


if __name__ == "__main__":
    unittest.main()
