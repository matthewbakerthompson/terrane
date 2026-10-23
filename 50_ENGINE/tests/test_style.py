"""Prose conventions the repository commits to.

American spelling throughout. This is a test rather than a review note because
it was caught three times by a human before it was caught once by a machine:
the `-ise` family, then the identifier forms that `\\b` boundaries miss because
`_` is a word character, then `instalment`, which belongs to a different family
altogether (doubled consonant, not a suffix swap). The fourth, `Parameterise`
and `misspelt` in AAC-03, went through this test: neither was in the word
list, which `terrane/style.py` now builds from stems and reads through a prefix.

Any of those would have been caught here on the first run.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane.style import BRITISH, americanize, offences  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

SUFFIXES = {".md", ".yaml", ".yml", ".csv", ".py", ".js", ".mjs", ".html", ".css", ".json", ".txt", ".ps1", ".sh", ".cmd"}
#: Third-party code, the built site, and the design critique snapshots the
#: review tooling writes are not ours to rewrite.
SKIP_PARTS = {".git", ".claude", "vendor", "fonts", "__pycache__", "node_modules", "site", ".impeccable"}



#: This file is the one place the British forms are allowed to appear: it is
#: the list of what to look for.
#: The two files that have to contain British spellings in order to catch
#: them: this one, and the vocabulary it now reads from.
SELF = {
    Path(__file__).resolve(),
    (Path(__file__).resolve().parents[1] / "terrane" / "style.py").resolve(),
}


#: Read once. Three tests over ~600 files is three full reads of the tree,
#: and the reading is the cost here rather than the matching.
_TEXT = {}


def _text_of(path):
    if path not in _TEXT:
        _TEXT[path] = path.read_text(encoding="utf-8", errors="ignore")
    return _TEXT[path]


def _yours_to_spell():
    """The model's own folders, once it is an organization's rather than the
    sample. A company that writes British English writes its estate in it,
    and the repository's house style is no business of its model; `terrane clear`
    takes the `sample_estate` line out of `model.yaml` with the sample."""
    from terrane.cli import is_sample_estate

    return set() if is_sample_estate(REPO) else {"10_MODEL", "70_ARTIFACTS"}


def _source_files():
    theirs = _yours_to_spell()
    for path in sorted(REPO.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        if path.resolve() in SELF:
            continue
        parts = path.relative_to(REPO).parts
        if any(part in SKIP_PARTS for part in parts):
            continue
        if parts and parts[0] in theirs:
            continue
        yield path


class TestAmericanSpelling(unittest.TestCase):
    def test_no_british_spellings_in_prose_or_data(self) -> None:
        """One pass over each file, a word looked up at a time: searching
        every file once per word was 102 scans of ~600 files, and 22 of the
        suite's 280 seconds, when the list was a sixth of its size."""
        found_in = []
        for path in _source_files():
            for found, american in offences(_text_of(path)):
                found_in.append("%s: %r should be %r" % (path.relative_to(REPO), found, american))
        self.assertEqual(sorted(found_in), [], "\n" + "\n".join(sorted(found_in)))

    def test_no_british_spellings_in_identifiers(self) -> None:
        """`\\b` does not fire around `_`, so `normalise_name` slipped past the
        prose check and identifiers had a pass of their own. A word is the
        letters between anything else now, so the pass above reads them."""
        self.assertEqual(
            offences("def normalise_name(colour_by, x_labelled2):"),
            [("colour", "color"), ("labelled", "labeled"), ("normalise", "normalize")],
        )

    def test_the_check_actually_matches_something(self) -> None:
        """A guard that silently matches nothing is worse than no guard."""
        self.assertGreater(len(list(_source_files())), 50)
        self.assertEqual(offences("an instalment plan"), [("instalment", "installment")])
        # The two that went through in AAC-03: an inflection nobody had
        # listed, and a listed word behind a prefix.
        self.assertEqual(
            americanize("Parameterise the misspelt, unrecognised COLOURS."),
            "Parameterize the misspelled, unrecognized COLORS.",
        )
        # Words spelled the same in both stay put.
        self.assertEqual(
            offences("advise, otherwise, analyses, cancellation, controlled, glamour, recent"), []
        )
        self.assertGreater(len(BRITISH), 500)


class TestViewProse(unittest.TestCase):
    """What a view says about itself is read under its title, in the app and
    in the index. It has to be plain: what is drawn and what to read from it,
    in a few sentences, with nothing the app already shows.

    The forty-one descriptions had grown a house of tics: "It takes a subject"
    on every subject view (the picker says so), two dash styles, and a
    closing aphorism apiece. A test keeps the next forty-one honest."""

    @classmethod
    def setUpClass(cls) -> None:
        from terrane.query import load_views

        cls.views = load_views(REPO / "30_VIEWS")

    def test_titles_are_distinct(self) -> None:
        """Two views were called "What Is In Flight" and "Change In Flight"."""
        titles = [v.title for v in self.views]
        self.assertEqual(sorted(set(titles)), sorted(titles))

    def test_descriptions_are_short_and_plain(self) -> None:
        offences = []
        for view in self.views:
            text = " ".join(view.description.split())
            sentences = len(re.findall(r"[.?!](\s|$)", text))
            if "--" in text:
                offences.append("%s: uses a double hyphen; write the sentence without it" % view.view_id)
            if "takes a subject" in text.lower():
                offences.append("%s: says it takes a subject; the parameters say so" % view.view_id)
            if sentences > 3:
                offences.append("%s: %d sentences, at most three" % (view.view_id, sentences))
            if len(text) > 460:
                offences.append("%s: %d characters, at most 460" % (view.view_id, len(text)))
            if not text.endswith((".", "?")):
                offences.append("%s: does not end a sentence" % view.view_id)
        self.assertEqual(offences, [], "\n" + "\n".join(offences))


if __name__ == "__main__":
    unittest.main()
