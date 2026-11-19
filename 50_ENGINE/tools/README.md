# Optional verification tools

The engine itself has no dependencies. These do, and they are optional; the
test runner is the exception, and needs nothing past the standard library.

## `run_tests.py`

The full suite across the machine's cores: each test file in a process of
its own, as many at a time as `--jobs` says (the core count unless told), one
summary at the end with unittest's own `Ran N tests` line, OK or every
failure's output, and the slowest files.

```bash
cd 50_ENGINE && python tools/run_tests.py
cd 50_ENGINE && python tools/run_tests.py test_style.py test_checklist.py
```

`python -m unittest discover -s tests` runs the same tests one after
another in one process and stays the fallback; the two counts agree. A file
that alone would outlast the rest is split by test class (`SPLIT`), and a
file that cannot share the machine runs alone after the others (`SERIAL`).
The longest go first, by the last run's times, kept in the temporary folder
as `terrane-test-times.json`.

## `mermaid_parse_check.mjs`

Parses every generated `.mmd` file with the real Mermaid parser, which is the only way
to be certain the output renders rather than merely looking well formed. The Python
test suite checks structure — balanced subgraphs, every edge endpoint declared, no
comment marker eaten by string formatting — but it is not a Mermaid grammar.

Install at the **repository root** — Node resolves `node_modules` by walking up from
the script's own location, so an install anywhere else will not be found:

```bash
npm install mermaid jsdom
node 50_ENGINE/tools/mermaid_parse_check.mjs 70_ARTIFACTS/mermaid
```

Exit 0 if every diagram parses. Run it after changing anything in
`50_ENGINE/terrane/render_mermaid.py`.

## `wheel_check.py`

Builds the wheel, installs it into a fresh virtual environment, and uses it
from an empty folder: the shipped folders inside the package (the views, the
library, the marks, the faces, ELK and Cytoscape, the examples, the landing
zones and the sample's answers), the `terrane` command on the path and
nothing installed as `aac`, which is another project's name on PyPI, a
reader's file, a part and both examples on the library drawn, an
editable deck and a draw.io file written with no repository around, and
the wheel named `terrane` with the LICENSE and its notice in its metadata,
and `terrane init` starting an estate that reads the wheel's library and views.
Needs `build` (`pip install build`); hatchling is fetched into the build's
own environment.

```bash
cd 50_ENGINE && python tools/wheel_check.py
```

It builds the sdist first and the wheel from the sdist alone, as anyone
building from PyPI's source would, so a folder the wheel takes and the sdist
leaves out fails here. Publish the two files it names on its last lines: they
are built in a temporary folder and copied to `dist/` at the repository's root
only once they pass, beside any an earlier run left there, since the check
deletes nothing. Run it before a release and after adding a folder the engine
reads, which goes into both lists in `pyproject.toml`.

## Releasing to PyPI

By hand, from this machine: the repository cannot count on GitHub Actions,
so no workflow publishes. `release.py` is the hand. Set `__version__` in
`terrane/__init__.py`, commit and push `main`, then:

```bash
cd 50_ENGINE && python tools/release.py
```

```bash
cd 50_ENGINE && python tools/release.py --upload
```

The first is a dry run: the version is not on PyPI yet and its tag is free,
both estates pass the gate, `wheel_check.py` builds the sdist and the wheel
and proves them, and `twine check --strict` reads both as PyPI will (`pip
install twine`). The second does the same, refuses unless the tree is clean
and HEAD is origin/main, uploads the two files the check proved, and tags and pushes
`v<version>`. twine takes the user name `__token__` and a PyPI API token as
the password, from `~/.pypirc`, `TWINE_USERNAME` / `TWINE_PASSWORD` or a
prompt; the first upload creates the project, so that one token is scoped to
the whole account, and one scoped to `terrane` replaces it after. PyPI never
takes a version back, so a mistake is fixed by the next version.
