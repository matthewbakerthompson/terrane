"""`terrane render --format X` writes that format and nothing else: asked for the
workspace alone, the command rewrote the committed docs, the library pages
and the index without their picture lines, since a doc's picture line is
written only when the SVG is drawn in the same run."""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli  # noqa: E402

from _fixture import Sandbox  # noqa: E402


class TestFormats(unittest.TestCase):
    def test_one_format_writes_that_format_alone(self) -> None:
        with Sandbox(seed=True) as root:
            out = Path(tempfile.mkdtemp(prefix="aac-render-")) / "out"
            text = io.StringIO()
            with redirect_stdout(text):
                code = cli.main(["--root", str(root), "render", "--format", "structurizr", "--out", str(out)])
            self.assertEqual(code, 0, text.getvalue())
            self.assertTrue((out / "structurizr" / "workspace.dsl").is_file())
            self.assertFalse((out / "docs").exists(), sorted(p.name for p in out.iterdir()))
            self.assertFalse((out / "INDEX.md").exists())
            self.assertEqual(sorted((out / "library").glob("*.md")) if (out / "library").exists() else [], [])
            # The count says what landed under the output folder, not what went to scratch.
            self.assertIn("file(s) written under", text.getvalue())


if __name__ == "__main__":
    unittest.main()
