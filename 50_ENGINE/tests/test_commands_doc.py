"""The command reference is the command line's own.

`docs/COMMANDS.md` is what `tools/commands_doc.py` writes from the parser,
so a command added, renamed or given a new argument without the page
changing fails here, before a reader is told about a flag that is not there.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tools"))

import commands_doc  # noqa: E402
from terrane.cli import build_parser  # noqa: E402


class TestCommandsDoc(unittest.TestCase):
    def test_the_page_is_what_the_parser_says(self) -> None:
        committed = commands_doc.OUT.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertEqual(committed, commands_doc.render(), "run python tools/commands_doc.py from 50_ENGINE")

    def test_every_command_has_a_heading(self) -> None:
        page = commands_doc.render()
        for name, _words, _sub in commands_doc._subcommands(build_parser()):
            self.assertIn("\n## terrane %s\n" % name, page, name)


if __name__ == "__main__":
    unittest.main()
