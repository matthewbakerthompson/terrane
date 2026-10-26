"""The package carries what the engine reads.

`pyproject.toml`, at the repository's root, copies the shipped folders into
the wheel under `terrane/shipped/`, and `terrane/shipped.py` looks there
when the repository is not around the engine. These tests hold the two to
each other: every folder the engine reads from beside itself is in the
bundle list, the sdist carries every folder the wheel is built from, the
resolver answers the repository while it is in one, and the quick door's
example is where the resolver says.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _fixture import remove_scratch  # noqa: E402
from terrane import quick, shipped  # noqa: E402

ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parent


def _toml_text() -> str:
    return (REPO / "pyproject.toml").read_text(encoding="utf-8")


def _tomllib():
    try:
        import tomllib
    except ImportError:  # Python 3.10: the tables are read by eye
        return None
    return tomllib


def _force_include() -> dict:
    text = _toml_text()
    tomllib = _tomllib()
    if tomllib is not None:
        return tomllib.loads(text)["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    out = {}
    inside = False
    for line in text.splitlines():
        if line.strip() == "[tool.hatch.build.targets.wheel.force-include]":
            inside = True
            continue
        if inside and line.startswith("["):
            break
        if inside and "=" in line:
            key, _, value = line.partition("=")
            out[key.strip().strip('"')] = value.strip().strip('"')
    return out


def _sdist_only_include() -> list:
    text = _toml_text()
    tomllib = _tomllib()
    if tomllib is not None:
        return tomllib.loads(text)["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    section = text.split("[tool.hatch.build.targets.sdist]", 1)[1].split("\n[", 1)[0]
    return re.findall(r'"([^"]+)"', re.search(r"only-include = \[(.*?)\]", section, re.S).group(1))


class TestShipped(unittest.TestCase):
    def test_the_engine_in_its_repository_answers_the_repository(self) -> None:
        self.assertEqual(shipped.repo_root(), REPO)
        self.assertEqual(shipped.shipped_root(), REPO)
        self.assertEqual(shipped.shipped_web(), REPO / "80_APP" / "web")
        self.assertEqual(shipped.shipped_app(), REPO / "80_APP" / "app" / "server.py")
        self.assertEqual(shipped.default_root(), REPO)
        self.assertTrue(shipped.example_path().is_file())
        self.assertEqual(quick.EXAMPLE, shipped.example_path())

    def test_the_wheel_bundles_every_folder_the_engine_reads(self) -> None:
        bundled = _force_include()
        wanted = {"30_VIEWS": "terrane/shipped/30_VIEWS",
                  # The app, for `terrane app`: its pages (the marks, the
                  # faces, ELK and Cytoscape among them, which the drawings
                  # use too) beside its server, as in the repository.
                  "80_APP/web": "terrane/shipped/web",
                  "80_APP/app/server.py": "terrane/shipped/app/server.py",
                  "90_EXAMPLE/quick": "terrane/shipped/90_EXAMPLE/quick",
                  # The sample estate, which `terrane init --sample` copies
                  # out: among its records the landing zones a product on a
                  # shipped shape binds to, and in its settings what it
                  # answers for the roles the library asks an estate to fill,
                  # both of which a sketch with no estate borrows.
                  "10_MODEL": "terrane/shipped/10_MODEL",
                  "60_SOURCES": "terrane/shipped/60_SOURCES"}
        for folder in quick.LIBRARY_FOLDERS:
            wanted[folder] = "terrane/shipped/" + folder
        for source, target in wanted.items():
            self.assertEqual(bundled.get(source), target, source)
            self.assertTrue((REPO / source).exists(), source)
        # And nothing bundled that the layout would not find.
        for source, target in bundled.items():
            self.assertTrue(target.startswith("terrane/shipped/"), target)
            # A folder lands under its own name, but `80_APP/web` is the
            # app's `web/` and the copy keeps that name.
            self.assertEqual(Path(target).name, Path(source).name, (source, target))

    def test_the_sdist_carries_what_the_wheel_is_built_from(self) -> None:
        # The project was `50_ENGINE/` and the shipped folders were `../`
        # from it, and an sdist holds only what is inside its project: one
        # built then carried the engine alone, and a wheel built from it
        # stopped at the first force-include. With the project at the
        # repository's root, every path the wheel takes is one the sdist
        # can hold, and has to.
        carried = _sdist_only_include()

        def inside(path: str) -> bool:
            return any(path == entry or path.startswith(entry.rstrip("/") + "/") for entry in carried)

        for source in list(_force_include()) + ["50_ENGINE/terrane", "50_ENGINE/README.md", "LICENSE",
                                                "THIRD_PARTY_NOTICES.md", "LICENSES"]:
            self.assertFalse(source.startswith(".."), source)
            self.assertTrue(inside(source), "%s goes into the wheel and is not in the sdist" % source)
        # Nothing else of the repository's: not the tests, which read the
        # whole repository and cannot run from an sdist, and not the
        # generated pictures or the design file.
        for entry in carried:
            self.assertTrue((REPO / entry).exists(), entry)
            self.assertFalse(entry.startswith(("70_ARTIFACTS", "80_APP/design", "50_ENGINE/tests")), entry)

    def test_the_version_is_the_packages(self) -> None:
        import terrane

        text = _toml_text()
        self.assertIn('dynamic = ["version"]', text)
        self.assertIn('path = "50_ENGINE/terrane/__init__.py"', text)
        self.assertTrue(terrane.__version__)

    def test_the_wheel_carries_the_repositorys_license(self) -> None:
        # The project is the repository, so the wheel takes the repository's
        # own LICENSE. PEP 639 takes no file from outside the project, which
        # is why the engine held a copy while the project was `50_ENGINE/`;
        # two copies were two things to keep equal, and the copy is gone.
        text = _toml_text()
        self.assertIn('license-files = ["LICENSE", "THIRD_PARTY_NOTICES.md", "LICENSES/*"]', text)
        self.assertIn('license = "LicenseRef-PolyForm-Shield-1.0.0 AND ', text)
        terms = (REPO / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("# PolyForm Shield License 1.0.0", terms)
        self.assertIn("\nRequired Notice: Copyright Matthew Baker Thompson", "\n" + terms)
        # Shield lets anyone compete with a product the licensor has stopped
        # providing unless a line of this form names it: without it, a pause
        # in a hosted Terrane would open the hosting to anyone.
        self.assertIn("\nLicensor Line of Business: Terrane", terms)
        self.assertFalse((ENGINE / "LICENSE").exists())
        self.assertFalse((ENGINE / "pyproject.toml").exists())

    def test_everything_bundled_has_its_notice(self) -> None:
        # The wheel bundles other people's work: the libraries the app and
        # the drawings run, the faces, the provider marks. Each goes with
        # its license's text, so a library, a face or a mark set added
        # without one fails here rather than on PyPI, where a version
        # cannot be taken back.
        notices = (REPO / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        web = REPO / "80_APP" / "web"
        for library in sorted((web / "vendor").glob("*.js")):
            self.assertIn("`80_APP/web/vendor/%s`" % library.name, notices, library.name)
        for face in sorted({f.name.rsplit("-latin-", 1)[0] for f in (web / "fonts").glob("*.woff2")}):
            self.assertIn("`80_APP/web/fonts/%s-*`" % face, notices, face)
        for marks in sorted(p.name for p in (web / "icons").iterdir() if p.is_dir()):
            self.assertIn("`80_APP/web/icons/%s/`" % marks, notices, marks)
        texts = sorted(p.name for p in (REPO / "LICENSES").iterdir())
        self.assertTrue(texts)
        for name in texts:
            self.assertIn("`LICENSES/%s`" % name, notices, name)
        expression = re.search(r'\nlicense = "([^"]+)"', _toml_text()).group(1)
        for ref in re.findall(r"LicenseRef-[A-Za-z0-9.-]+", expression):
            if ref != "LicenseRef-PolyForm-Shield-1.0.0":
                self.assertIn("%s.txt" % ref, texts, ref)

    def test_the_distribution_is_named_for_pypi_not_for_the_repository(self) -> None:
        # `architecture-as-code` on PyPI is someone else's project; a build
        # under that name could never be uploaded. And `aac`, the engine's
        # name until the first release, is AaC's module and command there,
        # another architecture-as-code tool, so the package installs
        # neither: an environment holding both would lose one of them.
        text = _toml_text()
        self.assertIn('\nname = "terrane"\n', text)
        self.assertIn('terrane = "terrane.cli:main"', text)
        self.assertNotIn('\naac = ', text)
        self.assertIn('packages = ["50_ENGINE/terrane"]', text)
        # A folder left beside the engine under the old name imports as an
        # empty namespace package and hides an import nobody renamed.
        self.assertFalse((ENGINE / "aac").exists())

    def test_version_prints_the_version(self) -> None:
        # It printed the usage until 1.1.0: --version was no option.
        import io
        from contextlib import redirect_stdout

        import terrane
        from terrane.cli import main

        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            main(["--version"])
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), "terrane %s" % terrane.__version__)

    def test_terrane_is_the_door_and_the_command(self) -> None:
        import terrane
        from terrane.cli import build_parser

        for name in terrane.__all__:
            self.assertTrue(hasattr(terrane, name), name)
        self.assertEqual(build_parser().prog, "terrane")
        self.assertTrue((ENGINE / "terrane" / "__main__.py").is_file())

    def test_the_wheel_names_no_private_repository_or_machine(self) -> None:
        # The method's own repository is private, so the docstrings and the
        # patterns README that sent a reader to its folders sent them
        # nowhere, and a path on this machine is nobody else's. Everything
        # the wheel carries is read, the engine and every bundled folder.
        private = re.compile(rb"ArchitectureMethod|DocsStudio|EAFoundations|[A-Za-z]:[\\/]dev[\\/]|AppData[\\/]Local",
                             re.I)
        sources = [ENGINE / "terrane", ENGINE / "README.md", REPO / "LICENSE"]
        sources += [REPO / source for source in _force_include()]
        found = []
        for source in sources:
            files = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
            for path in files:
                if "__pycache__" not in path.parts and private.search(path.read_bytes()):
                    found.append(str(path.relative_to(REPO)))
        self.assertEqual(found, [])


class TestThePackagesCopiesAlone(unittest.TestCase):
    """The quick door drawn from what the wheel carries and nothing else:
    the bundle list's folders copied where the package puts them, and no
    repository around. Run in the repository, the quick door reads the
    sample estate beside the engine, which hid that the wheel carried the
    landing zones and not the answers in `model.yaml`: every product on a
    shape or from parts, both shipped examples among them, failed to load
    from a pip install, asked who stewards its data."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="aac-wheel-copies-"))
        cls.inside = cls.tmp / "shipped"
        for source, target in _force_include().items():
            origin = REPO / source
            where = cls.inside / Path(target).relative_to("terrane/shipped")
            where.parent.mkdir(parents=True, exist_ok=True)
            if origin.is_dir():
                shutil.copytree(origin, where, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(origin, where)

    @classmethod
    def tearDownClass(cls) -> None:
        remove_scratch(cls.tmp, "aac-wheel-copies-")

    def test_a_product_from_parts_says_what_it_makes(self) -> None:
        import terrane

        made = quick.made_by(terrane.from_parts("AWS", "Portal", parts=["web-app-baseline"]), shipped=self.inside)
        self.assertTrue(any(m["part"] == "api-service" for rows in made.values() for m in rows), made)

    def test_both_shipped_examples_on_the_library_draw(self) -> None:
        for name in ("on-a-shape", "from-parts"):
            doc = quick.read_sketch(self.inside / "90_EXAMPLE" / "quick" / ("%s.yaml" % name))
            drawings = quick.render_sketch(doc, date="2026-10-22", shipped=self.inside)
            self.assertTrue(len(drawings), name)
            self.assertFalse([n for n in drawings.notes if n.startswith("ERROR")], (name, drawings.notes))

    def test_the_sample_copies_out_of_the_packages_copies(self) -> None:
        # `terrane init --sample` from what the wheel carries: a folder of
        # the sample's left out of the bundle list would copy a sample that
        # does not load, or loads with less than the repository's.
        from terrane import __version__, estate, validate
        from terrane.model import load

        copy = self.tmp / "sample"
        estate.init_sample(copy, __version__, source=self.inside)
        model = load(copy)
        self.assertEqual(model.counts(), load(REPO).counts())
        report = validate.run(model, estate.views_of(copy))
        self.assertEqual([f.format() for f in report.findings if f.severity == "error"], [])

    def test_the_spreadsheet_an_empty_estate_is_offered_travels(self) -> None:
        # `terrane init` and the app's note for an empty model name it. The
        # note once named `../90_EXAMPLE/csv`, which no wheel carries.
        offered = shipped.sample_inventory().relative_to(shipped.shipped_root())
        self.assertTrue((self.inside / offered).is_file(), offered)


if __name__ == "__main__":
    unittest.main()
