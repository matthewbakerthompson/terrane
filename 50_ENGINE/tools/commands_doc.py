"""Write `docs/COMMANDS.md`, the command reference, from the command line's
own parser.

    python tools/commands_doc.py            (from 50_ENGINE)

Every command and every argument, with the words its `--help` says, so the
page cannot say something the command does not do: `tests/test_commands_doc.py`
holds the committed page equal to what this writes. Built from the parser's
arguments rather than from argparse's formatted help, whose layout changes
between Python versions and with the width of the terminal.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parent
OUT = REPO / "docs" / "COMMANDS.md"
sys.path.insert(0, str(ENGINE))

from terrane.cli import build_parser  # noqa: E402

INTRO = """# Commands

Everything Terrane does from a terminal, generated from the command line
itself; `terrane --help` and `terrane <command> --help` say the same. Each
command works on the estate in the current folder, or the one `--root`
names (in a clone of this repository, the sample estate). `terrane app`
opens the same estate in the browser.
"""


def _subcommands(parser: argparse.ArgumentParser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            helps = {choice.dest: choice.help for choice in action._choices_actions}
            for name, sub in action.choices.items():
                yield name, helps.get(name) or "", sub


def _cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _rows(parser: argparse.ArgumentParser) -> List[str]:
    rows = []
    for action in parser._actions:
        if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
            continue
        if action.option_strings:
            name = ", ".join(action.option_strings)
            if action.nargs != 0:
                name += " " + (action.metavar or action.dest.upper())
        else:
            name = action.metavar or action.dest
            if action.nargs in ("?", "*"):
                name = "[%s]" % name
        words = action.help or ""
        if action.choices and not isinstance(action, argparse._SubParsersAction):
            words = (words + "; " if words else "") + "one of: " + ", ".join(str(c) for c in action.choices)
        rows.append("| `%s` | %s |" % (name, _cell(words)))
    return rows


def _section(name: str, words: str, parser: argparse.ArgumentParser, depth: int) -> List[str]:
    out = ["", "#" * depth + " terrane " + name, "", words[:1].upper() + words[1:] + "." if words else ""]
    rows = _rows(parser)
    if rows:
        out += ["", "| Argument | What it is |", "|---|---|"] + rows
    for sub_name, sub_words, sub in _subcommands(parser):
        out += _section(name + " " + sub_name, sub_words, sub, depth + 1)
    return out


def render() -> str:
    parser = build_parser()
    lines = [INTRO.rstrip("\n"), "", "| Option | What it is |", "|---|---|"] + _rows(parser)
    for name, words, sub in _subcommands(parser):
        lines += _section(name, words, sub, 2)
    text = "\n".join(lines) + "\n"
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def main() -> int:
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(), encoding="utf-8", newline="\n")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
