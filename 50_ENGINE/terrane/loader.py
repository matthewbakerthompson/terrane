"""File discovery and YAML reading.

PyYAML is used when importable; otherwise the bundled `yamlish` subset reader
handles the files this repository writes. Both paths return plain dicts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, List, Tuple

from . import yamlish

try:  # pragma: no cover - depends on the environment, both paths are exercised
    import yaml as _pyyaml
except ImportError:  # pragma: no cover
    _pyyaml = None


if _pyyaml is not None:  # pragma: no branch

    # libyaml's parser under the same safe constructor and resolver, where
    # PyYAML was built with it: nine times faster on this model, and every
    # file parses to the same data (`test_yamlish` holds both to the bundled
    # reader). Parsing was most of the wait after every write in the app,
    # since a write reloads the model and validation rereads the library.
    _SAFE = getattr(_pyyaml, "CSafeLoader", None) or _pyyaml.SafeLoader

    class _ModelLoader(_SAFE):
        """SafeLoader that leaves dates as text.

        PyYAML resolves `2026-11-02` to a `datetime.date`. Nothing here does
        arithmetic on dates, but a date object is not JSON-serializable, so it
        would break `terrane export json`, and it would disagree with the bundled
        fallback reader. Model files are text; dates stay text.
        """

    _ModelLoader.yaml_implicit_resolvers = {
        key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
        for key, resolvers in _pyyaml.SafeLoader.yaml_implicit_resolvers.items()
    }
else:  # pragma: no cover
    _ModelLoader = None

PARSER = "PyYAML" if _pyyaml is not None else "yamlish (bundled)"

MODEL_SUFFIXES = (".yaml", ".yml", ".json")


class ModelFileError(ValueError):
    """A model file could not be read."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__("%s: %s" % (path, message))
        self.path = path
        self.message = message


def read_data_file(path: Path) -> Any:
    """Parse one YAML or JSON file."""
    text = path.read_text(encoding="utf-8-sig")
    try:
        if path.suffix.lower() == ".json":
            return json.loads(text)
        if _pyyaml is not None:
            return _pyyaml.load(text, Loader=_ModelLoader)
        return yamlish.loads(text)
    except Exception as exc:  # noqa: BLE001 - re-raised with the file name attached
        raise ModelFileError(path, str(exc)) from exc


def parse_data_text(text: str, what: str = "<text>") -> Any:
    """Parse YAML held in memory, for text a person is still typing.

    The same reader the model files go through, so the editor cannot accept
    something the loader would later reject.
    """
    try:
        if _pyyaml is not None:
            return _pyyaml.load(text, Loader=_ModelLoader)
        return yamlish.loads(text)
    except Exception as exc:  # noqa: BLE001 - re-raised with a name attached
        raise ModelFileError(Path(what), str(exc)) from exc


def iter_data_files(folder: Path) -> Iterator[Path]:
    """Yield model files under `folder`, sorted, skipping dotfiles and READMEs."""
    if not folder.is_dir():
        return
    # Case-insensitive, so the order is the same on every platform. Windows
    # compares paths without case and Linux by byte, and an export that
    # keeps load order was coming out differently on the two.
    for path in sorted(folder.rglob("*"), key=lambda p: str(p).lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in MODEL_SUFFIXES:
            continue
        if path.name.startswith(("_", ".")):
            continue
        yield path


def load_folder(folder: Path) -> List[Tuple[Path, Any]]:
    """Read every model file in a folder, returning (path, data) pairs.

    A file holding a top-level list is treated as several records, which keeps
    small reference sets (org units, capabilities) in one readable file while
    letting systems stay one-per-file for clean diffs and code ownership.
    """
    records: List[Tuple[Path, Any]] = []
    for path in iter_data_files(folder):
        data = read_data_file(path)
        if data is None:
            continue
        if isinstance(data, list):
            for item in data:
                records.append((path, item))
        elif isinstance(data, dict):
            records.append((path, data))
        else:
            raise ModelFileError(path, "expected a mapping or a list of mappings")
    return records
