"""Tests for the bundled YAML subset reader.

The important test is the parity one: whenever PyYAML is installed, every YAML
file in this repository is parsed both ways and the results must be identical.
That is what makes it safe to ship a fallback parser at all.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import yamlish  # noqa: E402

try:
    import yaml as pyyaml
except ImportError:  # pragma: no cover
    pyyaml = None

from terrane.loader import read_data_file  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


class TestScalars(unittest.TestCase):
    def test_plain_types(self) -> None:
        data = yamlish.loads(
            "a: 1\nb: 2.5\nc: true\nd: false\ne: null\nf:\ng: text\n"
        )
        self.assertEqual(
            data, {"a": 1, "b": 2.5, "c": True, "d": False, "e": None, "f": None, "g": "text"}
        )

    def test_quoted_scalars_keep_their_text(self) -> None:
        data = yamlish.loads('a: "1"\nb: \'yes\'\nc: "with: colon"\n')
        self.assertEqual(data, {"a": "1", "b": "yes", "c": "with: colon"})

    def test_comment_stripping_respects_quotes(self) -> None:
        data = yamlish.loads('a: "text # not a comment"  # a comment\n')
        self.assertEqual(data, {"a": "text # not a comment"})

    def test_flow_collections(self) -> None:
        data = yamlish.loads("tags: [one, two, three]\nmap: {a: 1, b: two}\n")
        self.assertEqual(data["tags"], ["one", "two", "three"])
        self.assertEqual(data["map"], {"a": 1, "b": "two"})

    def test_url_value_is_not_split_on_its_colon(self) -> None:
        data = yamlish.loads("link: https://example.test/path\n")
        self.assertEqual(data, {"link": "https://example.test/path"})


class TestStructures(unittest.TestCase):
    def test_nested_mapping(self) -> None:
        data = yamlish.loads("outer:\n  inner:\n    leaf: 1\n")
        self.assertEqual(data, {"outer": {"inner": {"leaf": 1}}})

    def test_sequence_of_mappings(self) -> None:
        text = "items:\n  - id: A\n    name: First\n  - id: B\n    name: Second\n"
        self.assertEqual(
            yamlish.loads(text),
            {"items": [{"id": "A", "name": "First"}, {"id": "B", "name": "Second"}]},
        )

    def test_sequence_at_same_indent_as_key(self) -> None:
        text = "items:\n- one\n- two\n"
        self.assertEqual(yamlish.loads(text), {"items": ["one", "two"]})

    def test_top_level_sequence(self) -> None:
        text = "- id: A\n  name: First\n- id: B\n  name: Second\n"
        self.assertEqual(
            yamlish.loads(text), [{"id": "A", "name": "First"}, {"id": "B", "name": "Second"}]
        )

    def test_nested_mapping_inside_sequence_item(self) -> None:
        text = "items:\n  - id: A\n    spec:\n      kind: thing\n      size: 2\n"
        self.assertEqual(
            yamlish.loads(text),
            {"items": [{"id": "A", "spec": {"kind": "thing", "size": 2}}]},
        )

    def test_literal_block_scalar_keeps_newlines(self) -> None:
        text = "body: |\n  line one\n  line two\n"
        self.assertEqual(yamlish.loads(text), {"body": "line one\nline two\n"})

    def test_folded_block_scalar_joins_lines(self) -> None:
        text = "body: >\n  line one\n  line two\nnext: 1\n"
        data = yamlish.loads(text)
        # Clip chomping: one trailing newline survives, as in PyYAML.
        self.assertEqual(data["body"], "line one line two\n")
        self.assertEqual(data["next"], 1)

    def test_strip_chomping_drops_the_trailing_newline(self) -> None:
        self.assertEqual(
            yamlish.loads("body: >-\n  line one\n  line two\n"),
            {"body": "line one line two"},
        )
        self.assertEqual(
            yamlish.loads("body: |-\n  line one\n  line two\n"),
            {"body": "line one\nline two"},
        )


class TestErrors(unittest.TestCase):
    def test_tab_indentation_is_rejected(self) -> None:
        with self.assertRaises(yamlish.YamlishError):
            yamlish.loads("a:\n\tb: 1\n")

    def test_unexpected_indent_is_rejected(self) -> None:
        with self.assertRaises(yamlish.YamlishError):
            yamlish.loads("a: 1\n    b: 2\n")

    #: Text that opens a flow collection or a quote and never closes it. These
    #: used to come back as plain strings, so this reader and PyYAML disagreed
    #: about the same file instead of both refusing it. Silent disagreement is
    #: the failure this reader exists to avoid.
    UNTERMINATED = ("a: [1,", "a: [1, 2", "a: {b: 1", "a: 'x", 'a: "x')

    #: A flow collection wrapped across lines, as the build types write
    #: theirs. PyYAML reads it; this reader used to refuse it as unterminated,
    #: which broke the workflows that run without PyYAML.
    WRAPPED = (
        "a:\n  offers: [one, two,\n           three, four]\n  b: 5\n",
        "- id: x\n  offers: [one,\n    two]\n- id: y\n",
        "a: {b: 1,\n    c: [2,\n        3]}\nd: 4\n",
        "a: [one,\n\n     two]\n",
    )

    def test_a_flow_collection_may_wrap_across_lines(self) -> None:
        self.assertEqual(
            yamlish.loads(self.WRAPPED[0]), {"a": {"offers": ["one", "two", "three", "four"], "b": 5}}
        )
        self.assertEqual(yamlish.loads(self.WRAPPED[1]), [{"id": "x", "offers": ["one", "two"]}, {"id": "y"}])
        self.assertEqual(yamlish.loads(self.WRAPPED[2]), {"a": {"b": 1, "c": [2, 3]}, "d": 4})
        self.assertEqual(yamlish.loads(self.WRAPPED[3]), {"a": ["one", "two"]})

    @unittest.skipIf(pyyaml is None, "PyYAML is not installed")
    def test_pyyaml_reads_the_wrapped_collections_the_same_way(self) -> None:
        for text in self.WRAPPED:
            with self.subTest(text=text):
                self.assertEqual(yamlish.loads(text), pyyaml.safe_load(text))

    def test_unterminated_flow_and_quotes_are_rejected(self) -> None:
        for text in self.UNTERMINATED:
            with self.subTest(text=text):
                with self.assertRaises(yamlish.YamlishError):
                    yamlish.loads(text)

    @unittest.skipIf(pyyaml is None, "PyYAML is not installed")
    def test_both_readers_refuse_the_same_malformed_text(self) -> None:
        for text in self.UNTERMINATED:
            with self.subTest(text=text):
                with self.assertRaises(Exception):
                    pyyaml.safe_load(text)

    #: A plain scalar containing a colon and a space. PyYAML refuses these;
    #: this reader used to return them as strings, which is the same silent
    #: disagreement as the unterminated cases above.
    COLON_SPACE = ("a: b: c", "not: valid: yaml:", "note: see this: that")

    def test_a_plain_value_with_a_colon_and_space_is_rejected(self) -> None:
        for text in self.COLON_SPACE:
            with self.subTest(text=text):
                with self.assertRaises(yamlish.YamlishError):
                    yamlish.loads(text)

    @unittest.skipIf(pyyaml is None, "PyYAML is not installed")
    def test_pyyaml_refuses_them_too(self) -> None:
        for text in self.COLON_SPACE:
            with self.subTest(text=text):
                with self.assertRaises(Exception):
                    pyyaml.safe_load(text)

    def test_colons_without_a_space_are_left_alone(self) -> None:
        """A URL and a clock time are the reason the rule needs the space."""
        self.assertEqual(
            yamlish.loads("a: http://example.com/p\nb: 10:30\n"),
            {"a": "http://example.com/p", "b": "10:30"},
        )

    def test_a_quoted_value_may_contain_anything(self) -> None:
        self.assertEqual(
            yamlish.loads("a: 'b: c'\nb: \"d: e\"\n"), {"a": "b: c", "b": "d: e"}
        )

    def test_a_block_scalar_may_contain_anything(self) -> None:
        self.assertEqual(yamlish.loads("a: |\n  b: c\n"), {"a": "b: c\n"})

    def test_brackets_inside_a_plain_scalar_are_left_alone(self) -> None:
        """The check is on what a value starts with, not what it contains."""
        self.assertEqual(
            yamlish.loads("a: plain [text] here\nb: x[1]\n"),
            {"a": "plain [text] here", "b": "x[1]"},
        )


@unittest.skipIf(pyyaml is None, "PyYAML is not installed")
class TestParityWithPyYAML(unittest.TestCase):
    """Every YAML file in the repository must parse identically both ways."""

    def test_repository_files_match(self) -> None:
        files = sorted(
            p
            for folder in ("10_MODEL", "20_ARCHETYPES", "30_VIEWS", "60_SOURCES")
            for p in (REPO / folder).rglob("*.yaml")
        )
        self.assertGreater(len(files), 10, "expected the repository to hold model files")
        for path in files:
            text = path.read_text(encoding="utf-8-sig")
            with self.subTest(path=str(path.relative_to(REPO))):
                # Compared against `read_data_file`, not `safe_load`: the
                # engine disables PyYAML's timestamp resolver so dates stay
                # text, and parity has to be measured against what actually
                # loads the model.
                self.assertEqual(
                    yamlish.loads(text),
                    read_data_file(path),
                    "%s parses differently under the fallback reader" % path.name,
                )


if __name__ == "__main__":
    unittest.main()
