"""A deliberately small YAML reader for the subset this repository writes.

PyYAML is used when it is installed. This module exists so that the engine also
runs on a bare Python install, which is a common constraint inside regulated
environments where `pip install` needs a ticket.

Supported: block mappings, block sequences, `|` and `>` block scalars, flow
sequences and mappings on a single line, comments, quoted and plain scalars,
booleans, integers, floats, and nulls. Anchors, aliases, tags, multiple
documents, multi-line flow collections, and mappings nested inside flow
sequences (`[a, b: c]`) are not supported and raise `YamlishError` rather than
parsing incorrectly.

The rule that matters: where this reader and PyYAML would disagree about a
file, it raises. Two readers that both refuse something is a bad afternoon;
two readers that quietly return different models from the same file is a bad
quarter.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple


class YamlishError(ValueError):
    """Raised when input falls outside the supported subset."""


_TRUE = {"true", "yes", "on"}
_FALSE = {"false", "no", "off"}
_NULL = {"", "~", "null"}
_QUOTES = ('"', "'")


def _strip_comment(line: str) -> str:
    """Remove a trailing comment, respecting quoted spans."""
    out: List[str] = []
    quote: Optional[str] = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            out.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(line):
                out.append(line[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in _QUOTES:
            quote = ch
            out.append(ch)
        elif ch == "#" and (not out or out[-1] in " \t"):
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _unquote(text: str) -> str:
    body = text[1:-1]
    if text[0] == '"':
        body = (
            body.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
    else:
        body = body.replace("''", "'")
    return body


def _scalar(raw: str) -> Any:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in _QUOTES:
        return _unquote(text)
    # Something that opens a quote or a flow collection and never closes it is
    # an error in YAML. Reading it as a plain string would make this reader and
    # PyYAML disagree about the same file, which is worse than either of them
    # refusing it.
    if text[:1] in _QUOTES:
        raise YamlishError("unterminated quoted string: %r" % text)
    if text.startswith("[") and not text.endswith("]"):
        raise YamlishError("unterminated flow sequence: %r" % text)
    if text.startswith("{") and not text.endswith("}"):
        raise YamlishError("unterminated flow mapping: %r" % text)
    if text.startswith("[") and text.endswith("]"):
        return [_scalar(p) for p in _split_flow(text[1:-1])]
    if ": " in text and not text.startswith(("[", "{")):
        # A plain scalar cannot contain a colon followed by a space -- that is
        # exactly what separates one from a nested mapping, and PyYAML refuses
        # it. Reading it as a string made the two readers disagree about the
        # same file. `http://x/y` and `10:30` have no space, so they are fine;
        # a value that genuinely needs one goes in quotes, as YAML requires.
        raise YamlishError(
            "a plain value cannot contain ': '; quote it if it is text: %r" % text
        )
    if text.startswith("{") and text.endswith("}"):
        result = {}
        for part in _split_flow(text[1:-1]):
            pair = _split_key(part)
            if pair is None:
                raise YamlishError("flow mapping entry without a key: %r" % part)
            result[str(_scalar(pair[0]))] = _scalar(pair[1])
        return result
    low = text.lower()
    if low in _NULL:
        return None
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    try:
        if text.startswith(("0x", "-0x")):
            return int(text, 16)
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _split_flow(body: str) -> List[str]:
    """Split a flow collection body on top-level commas."""
    parts: List[str] = []
    depth = 0
    quote: Optional[str] = None
    current: List[str] = []
    for ch in body:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in _QUOTES:
            quote = ch
            current.append(ch)
        elif ch in "[{":
            depth += 1
            current.append(ch)
        elif ch in "]}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [p for p in (p.strip() for p in parts) if p != ""]


def _flow_depth(text: str) -> int:
    """How many flow collections `text` opens and never closes, quotes aside."""
    depth = 0
    quote: Optional[str] = None
    for ch in text:
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in _QUOTES:
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
    return depth


def _split_key(text: str) -> Optional[Tuple[str, str]]:
    """Split `key: value`, ignoring colons inside quotes or flow collections."""
    depth = 0
    quote: Optional[str] = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in _QUOTES:
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            after = text[i + 1 :]
            if after and not after.startswith((" ", "\t")):
                continue
            return text[:i].strip(), after.strip()
    return None


class _Reader:
    def __init__(self, text: str) -> None:
        self.raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.pos = 0

    def _indent_of(self, line: str) -> int:
        lead = line[: len(line) - len(line.lstrip(" \t"))]
        if "\t" in lead:
            raise YamlishError("tab used for indentation on line %d" % (self.pos + 1))
        return len(lead)

    def _peek(self) -> Optional[Tuple[int, str]]:
        """Return (indent, content) of the next meaningful line, or None."""
        while self.pos < len(self.raw):
            content = _strip_comment(self.raw[self.pos])
            if not content.strip() or content.strip() in ("---", "..."):
                self.pos += 1
                continue
            return self._indent_of(content), content.strip()
        return None

    def _block_scalar(self, indicator: str, parent_indent: int) -> str:
        """Consume a `|` or `>` block, honoring the chomping indicator.

        Chomping follows the spec: clip (no indicator) keeps one trailing
        newline, strip (`-`) keeps none, keep (`+`) keeps them all. Getting this
        wrong is how a fallback parser quietly disagrees with PyYAML.
        """
        style = indicator[0]
        chomp = indicator[1:] if len(indicator) > 1 else ""
        lines: List[str] = []
        block_indent: Optional[int] = None
        while self.pos < len(self.raw):
            line = self.raw[self.pos]
            if not line.strip():
                lines.append("")
                self.pos += 1
                continue
            indent = self._indent_of(line)
            if indent <= parent_indent:
                break
            if block_indent is None:
                block_indent = indent
            lines.append(line[block_indent:] if len(line) > block_indent else "")
            self.pos += 1

        trailing = 0
        while lines and lines[-1] == "":
            lines.pop()
            trailing += 1

        if style == "|":
            body = "\n".join(lines)
        else:
            # Folded: a blank line becomes a paragraph break, the rest joins.
            paragraphs: List[List[str]] = [[]]
            for entry in lines:
                if entry.strip():
                    paragraphs[-1].append(entry.strip())
                elif paragraphs[-1]:
                    paragraphs.append([])
            body = "\n".join(" ".join(p) for p in paragraphs if p)

        if not body:
            return ""
        if chomp == "-":
            return body
        if chomp == "+":
            return body + "\n" * (trailing + 1)
        return body + "\n"

    def parse(self, indent: int) -> Any:
        head = self._peek()
        if head is None:
            return None
        if head[1] == "-" or head[1].startswith("- "):
            return self._sequence(indent)
        return self._mapping(indent)

    def _sequence(self, indent: int) -> List[Any]:
        items: List[Any] = []
        while True:
            head = self._peek()
            if head is None:
                break
            line_indent, content = head
            if line_indent != indent or not (
                content == "-" or content.startswith("- ")
            ):
                break
            body = content[1:].strip()
            self.pos += 1
            if not body:
                nested = self._peek()
                if nested is not None and nested[0] > line_indent:
                    items.append(self.parse(nested[0]))
                else:
                    items.append(None)
                continue
            pair = _split_key(body)
            if pair is None:
                items.append(self._value_or_block(body, line_indent))
                continue
            # `- key: value` opens a mapping whose later keys align after the dash.
            item_indent = line_indent + (len(content[1:]) - len(content[1:].lstrip())) + 1
            mapping: dict = {}
            if pair[1] == "":
                nested = self._peek()
                if nested is not None and nested[0] > line_indent:
                    mapping[pair[0]] = self.parse(nested[0])
                else:
                    mapping[pair[0]] = None
            else:
                mapping[pair[0]] = self._value_or_block(pair[1], line_indent)
            self._continue_mapping(mapping, item_indent)
            items.append(mapping)
        return items

    def _value_or_block(self, value: str, parent_indent: int) -> Any:
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            return self._block_scalar(value, parent_indent)
        if value[:1] in ("[", "{") and _flow_depth(value) > 0:
            value = self._flow_continuation(value, parent_indent)
        return _scalar(value)

    def _flow_continuation(self, value: str, parent_indent: int) -> str:
        """A flow collection may wrap onto the lines below its key, each
        indented past it. Gather them until the collection closes; one that
        never closes is left for `_scalar` to refuse, as before."""
        parts = [value]
        while _flow_depth(" ".join(parts)) > 0 and self.pos < len(self.raw):
            content = _strip_comment(self.raw[self.pos])
            if not content.strip():
                self.pos += 1
                continue
            if self._indent_of(content) <= parent_indent:
                break
            parts.append(content.strip())
            self.pos += 1
        return " ".join(parts)

    def _mapping(self, indent: int) -> dict:
        mapping: dict = {}
        self._continue_mapping(mapping, indent)
        return mapping

    def _continue_mapping(self, mapping: dict, indent: int) -> None:
        while True:
            head = self._peek()
            if head is None:
                break
            line_indent, content = head
            if line_indent < indent:
                break
            if line_indent > indent:
                raise YamlishError("unexpected indent on line %d" % (self.pos + 1))
            if content == "-" or content.startswith("- "):
                break
            pair = _split_key(content)
            if pair is None:
                raise YamlishError(
                    "line %d is not a mapping entry: %r" % (self.pos + 1, content)
                )
            key, value = pair
            self.pos += 1
            key = _unquote(key) if len(key) >= 2 and key[0] == key[-1] and key[0] in _QUOTES else key
            if value == "":
                nested = self._peek()
                if nested is None:
                    mapping[key] = None
                elif nested[0] > line_indent:
                    mapping[key] = self.parse(nested[0])
                elif nested[0] == line_indent and (
                    nested[1] == "-" or nested[1].startswith("- ")
                ):
                    # A sequence may sit at the same indent as its key.
                    mapping[key] = self._sequence(line_indent)
                else:
                    mapping[key] = None
            else:
                mapping[key] = self._value_or_block(value, line_indent)


def loads(text: str) -> Any:
    """Parse a YAML subset document into Python data."""
    reader = _Reader(text)
    head = reader._peek()
    if head is None:
        return None
    result = reader.parse(head[0])
    if reader._peek() is not None:
        raise YamlishError("trailing content at line %d" % (reader.pos + 1))
    return result
