"""An estate in a repository of its own, read with the installed terrane.

An organization keeps its estate in a repository it owns and everyone on it
installs terrane with pip, so nothing of terrane's sits in that repository:
`shipped_library: package` and `shipped_views: package` read the library and
the views from the installed package, `requires_terrane` pins the release
everyone is checked with, and `governance` pins the organization's governance
repository. Before this, an estate outside the terrane repository saw no
views and no library at all. Each test starts its estate with `terrane init` in
a folder of its own and removes exactly that folder.
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import __version__, cli, estate  # noqa: E402
from terrane.join import estate_copy  # noqa: E402
from terrane.library import LibraryError, library_roots  # noqa: E402
from terrane.model import load  # noqa: E402
from terrane.query import ViewError, load_views  # noqa: E402
from terrane.shipped import sample_inventory, shipped_root  # noqa: E402
from terrane import validate  # noqa: E402

SHIPPED_VIEWS = len(load_views(shipped_root() / "30_VIEWS"))


def _server():
    """The app's server module, fresh, as `terrane app` loads it."""
    import importlib

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "80_APP" / "app"))
    import server as server_module

    return importlib.reload(server_module)


class _Estate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="aac-estate-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = self.tmp / "estate"

    def init(self, *extra: str) -> int:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return cli.main(["init", str(self.root), "--name", "Contoso Architecture", *extra])

    def config(self, text: str) -> None:
        path = self.root / "10_MODEL" / "model.yaml"
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def findings(self) -> list:
        report = validate.run(load(self.root), estate.views_of(self.root))
        return [(f.severity, f.code) for f in report.findings if f.code.startswith("estate.")]

    def write_view(self, name: str, text: str) -> None:
        (self.root / "30_VIEWS" / name).write_text(text, encoding="utf-8")


class TestInit(_Estate):
    def test_an_estate_starts_with_the_installed_library_and_views(self) -> None:
        self.assertEqual(self.init(), 0)
        for rel in ("10_MODEL/model.yaml", "30_VIEWS/README.md", "README.md", ".gitignore"):
            self.assertTrue((self.root / rel).is_file(), rel)
        text = (self.root / "10_MODEL" / "model.yaml").read_text(encoding="utf-8")
        self.assertIn("shipped_library: package", text)
        self.assertIn("shipped_views: package", text)
        self.assertIn('requires_terrane: "%s"' % estate.default_requirement(__version__), text)
        self.assertEqual(len(estate.views_of(self.root)), SHIPPED_VIEWS)
        self.assertEqual(library_roots(self.root)[0].path, shipped_root().resolve())
        report = validate.run(load(self.root), estate.views_of(self.root))
        self.assertEqual([f.format() for f in report.findings if f.severity == "error"], [])
        # Generated pictures stay out of the repository, so two people's
        # renders never conflict.
        self.assertIn("70_ARTIFACTS/", (self.root / ".gitignore").read_text(encoding="utf-8"))

    def test_the_spreadsheet_init_offers_is_there_and_adopt_reads_it(self) -> None:
        # The hints an empty estate gets once named `../90_EXAMPLE/csv`, a
        # folder only a clone of the repository has.
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["init", str(self.root), "--name", "Contoso Architecture"]), 0)
        offered = Path(out.getvalue().splitlines()[-1].strip())
        self.assertEqual(offered, sample_inventory())
        self.assertTrue(offered.is_file(), offered)
        self.assertNotIn("90_EXAMPLE/csv", out.getvalue())
        tried = io.StringIO()
        with redirect_stdout(tried), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["--root", str(self.root), "adopt", str(offered), "--dry-run"]), 0)
        self.assertIn("would adopt 5", tried.getvalue())

    def test_the_app_on_an_empty_estate_names_what_an_install_has(self) -> None:
        self.assertEqual(self.init(), 0)
        server = _server()

        class Stopped:
            """The server, stopped as soon as it would serve."""

            def __init__(self, *_args) -> None:
                pass

            def serve_forever(self) -> None:
                raise KeyboardInterrupt

            def server_close(self) -> None:
                pass

        out = io.StringIO()
        with mock.patch.object(server, "ThreadingHTTPServer", Stopped), redirect_stdout(out):
            self.assertEqual(server.main(["--root", str(self.root)]), 0)
        lines = out.getvalue().splitlines()
        self.assertIn("terrane adopt <a spreadsheet>", out.getvalue())
        self.assertNotIn("90_EXAMPLE/csv", out.getvalue())
        self.assertNotIn("python -m terrane", out.getvalue())
        sample = Path(lines[[i for i, line in enumerate(lines) if line.lstrip().startswith("sample")][0] + 1].strip())
        self.assertEqual(sample, sample_inventory())
        self.assertTrue(sample.is_file(), sample)

    def test_credentials_are_kept_out_of_the_repository(self) -> None:
        self.assertEqual(self.init(), 0)
        lines = (self.root / ".gitignore").read_text(encoding="utf-8").splitlines()
        for pattern in (".env", ".env.*", "*.pem", "*.key", ".secrets/"):
            self.assertIn(pattern, lines)
        # A repository that came with an ignore file of its own keeps every
        # line of it, and gains only the credential lines it lacked.
        self.root = self.tmp / "theirs"
        self.root.mkdir()
        (self.root / ".gitignore").write_text("node_modules/\n.env\n", encoding="utf-8")
        self.assertEqual(self.init(), 0)
        lines = (self.root / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[:2], ["node_modules/", ".env"])
        self.assertEqual(lines.count(".env"), 1)
        self.assertIn("*.pem", lines)
        self.assertFalse(estate.guard_secrets(self.root / ".gitignore"))

    def test_the_owners_readme_is_kept_and_an_estate_is_not_started_twice(self) -> None:
        self.root.mkdir()
        (self.root / "README.md").write_text("# Ours\n", encoding="utf-8")
        self.assertEqual(self.init(), 0)
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "# Ours\n")
        self.assertEqual(self.init(), 2)

    def test_a_folder_holding_views_or_a_library_is_not_mixed_into(self) -> None:
        (self.root / "26_BLOCKS").mkdir(parents=True)
        self.assertEqual(self.init(), 2)
        self.assertFalse((self.root / "10_MODEL").exists())

    def test_a_governance_pin_is_a_repository_and_a_ref_together(self) -> None:
        self.assertEqual(self.init("--governance", "https://dev.azure.com/contoso/a/_git/governance"), 2)
        self.assertEqual(self.init("--governance", "https://dev.azure.com/contoso/a/_git/governance",
                                   "--governance-ref", "v1.0.0"), 0)
        self.assertEqual(self.findings(), [])
        self.assertEqual(estate.pins(self.root)["governance"],
                         "https://dev.azure.com/contoso/a/_git/governance at v1.0.0")


class TestPins(_Estate):
    def setUp(self) -> None:
        super().setUp()
        self.init()

    def _requires(self, spec: str) -> None:
        path = self.root / "10_MODEL" / "model.yaml"
        text = path.read_text(encoding="utf-8")
        old = 'requires_terrane: "%s"' % estate.default_requirement(__version__)
        self.assertEqual(text.count(old), 1)
        path.write_text(text.replace(old, 'requires_terrane: "%s"' % spec), encoding="utf-8")

    def test_another_terrane_is_an_error_on_validate(self) -> None:
        self.assertEqual(self.findings(), [])
        self._requires(">=99.0")
        self.assertEqual(self.findings(), [("error", "estate.requires")])
        # Every other command still runs, and says so once.
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            self.assertEqual(cli.main(["--root", str(self.root), "stats"]), 0)
        self.assertIn("checked with terrane >=99.0", err.getvalue())

    def test_a_range_terrane_cannot_read_is_an_error(self) -> None:
        self._requires("about 1.10")
        self.assertEqual(self.findings(), [("error", "estate.requires")])

    def test_the_ranges_read(self) -> None:
        self.assertTrue(estate.version_accepted(">=1.10.0,<1.11", "1.10.4"))
        self.assertFalse(estate.version_accepted(">=1.10.0,<1.11", "1.11.0"))
        self.assertTrue(estate.version_accepted("==1.10", "1.10.0"))
        self.assertFalse(estate.version_accepted("!=1.10.0", "1.10"))
        self.assertIsNone(estate.version_accepted("~=1.10", "1.10.0"))
        self.assertEqual(estate.default_requirement("1.10.0"), ">=1.10.0,<1.11")

    def test_a_governance_pin_without_its_ref_is_an_error(self) -> None:
        self.config('governance:\n  repository: "https://dev.azure.com/contoso/a/_git/governance"\n')
        self.assertEqual(self.findings(), [("error", "estate.governance")])


class TestViews(_Estate):
    def setUp(self) -> None:
        super().setUp()
        self.init()
        self.landscape = (shipped_root() / "30_VIEWS" / "application-landscape.view.yaml").read_text(encoding="utf-8")

    def test_a_view_of_the_estates_own_is_read_after_the_shipped_ones(self) -> None:
        self.write_view("our-landscape.view.yaml", self.landscape.replace(
            "view_id: application-landscape", "view_id: our-landscape"))
        ids = [v.view_id for v in estate.views_of(self.root)]
        self.assertEqual(len(ids), SHIPPED_VIEWS + 1)
        self.assertIn("our-landscape", ids)

    def test_a_diagram_of_the_estates_own_places_a_shipped_view(self) -> None:
        """Merged once the shipped views are read: the estate's folder alone
        does not hold the view it places."""
        self.write_view("lending.view.yaml", "view_id: lending\ntitle: Lending\nkind: diagram\n"
                        "places: [network-topology]\nedges:\n  - via: interfaces\n")
        views = {v.view_id: v for v in estate.views_of(self.root)}
        network, lending = views["network-topology"], views["lending"]
        self.assertEqual(lending.group_by, network.group_by)
        self.assertEqual(lending.scope["include"], network.scope["include"])
        self.assertEqual(lending.own.places, [{"view": "network-topology"}])

    def test_a_shipped_id_is_taken_only_by_saying_replaces(self) -> None:
        self.write_view("application-landscape.view.yaml",
                        self.landscape.replace("title: Application Landscape", "title: Our Landscape"))
        with self.assertRaises(ViewError) as caught:
            estate.views_of(self.root)
        self.assertIn("replaces: application-landscape", str(caught.exception))
        self.write_view("application-landscape.view.yaml", self.landscape.replace(
            "title: Application Landscape", "replaces: application-landscape\ntitle: Our Landscape"))
        views = estate.views_of(self.root)
        self.assertEqual(len(views), SHIPPED_VIEWS)
        self.assertEqual([v.title for v in views if v.view_id == "application-landscape"], ["Our Landscape"])

    def test_replacing_what_is_not_shipped_is_refused(self) -> None:
        self.write_view("ours.view.yaml", self.landscape.replace(
            "view_id: application-landscape", "view_id: ours\nreplaces: ours"))
        with self.assertRaises(ViewError):
            estate.views_of(self.root)

    def test_an_estate_that_does_not_ask_reads_its_own_views_only(self) -> None:
        path = self.root / "10_MODEL" / "model.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("shipped_views: package\n", ""), encoding="utf-8")
        self.assertEqual(estate.views_of(self.root), [])

    def test_a_shipped_views_setting_with_no_meaning_is_refused(self) -> None:
        path = self.root / "10_MODEL" / "model.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("shipped_views: package", "shipped_views: ../.."),
                        encoding="utf-8")
        with self.assertRaises(ViewError):
            estate.views_of(self.root)
        self.assertIn(("error", "estate.shipped_views"),
                      [("error", code) for code, _ in estate.problems(self.root)])


class TestShippedViewsOnARealEstate(_Estate):
    """Once the estate holds records, a view that selects nothing is an
    error -- but a shipped view that names the sample's own systems can never
    select anything in another estate, and the estate cannot edit it. The
    first estate built on the package failed its gate six times for that."""

    SYSTEM = ("system_id: SYS-PORTAL\nname: Customer Portal\nstatus: Active\nowner_org_id: ORG-PLATFORM\n"
              "criticality: High\nhosting: Azure\ncompany_domain: Digital\n")

    def setUp(self) -> None:
        super().setUp()
        self.init()
        for rel, text in (("10_MODEL/org_units/ORG-PLATFORM.yaml",
                           "org_unit_id: ORG-PLATFORM\nname: Platform Engineering\nstatus: Active\n"),
                          ("10_MODEL/systems/SYS-PORTAL.yaml", self.SYSTEM)):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text, encoding="utf-8")

    def report(self):
        return validate.run(load(self.root), estate.views_of(self.root)).findings

    def test_a_shipped_view_that_selects_nothing_warns_and_the_estates_own_fails(self) -> None:
        findings = self.report()
        self.assertEqual([f.format() for f in findings if f.severity == "error"], [])
        nothing = [f for f in findings if f.code == "view.shipped_nothing"]
        self.assertIn("harvested-estate", " ".join(f.message for f in nothing))
        landscape = (shipped_root() / "30_VIEWS" / "harvested-estate.view.yaml").read_text(encoding="utf-8")
        self.write_view("ours.view.yaml", landscape.replace("view_id: harvested-estate", "view_id: ours"))
        errors = [f for f in self.report() if f.severity == "error"]
        self.assertEqual([f.code for f in errors], ["view.unresolvable"])

    def test_without_leaves_a_shipped_view_out_and_a_wrong_name_is_refused(self) -> None:
        self.config("")
        path = self.root / "10_MODEL" / "model.yaml"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("shipped_views: package\n",
                                     "shipped_views: {from: package, without: [harvested-estate]}\n"),
                        encoding="utf-8")
        ids = [v.view_id for v in estate.views_of(self.root)]
        self.assertEqual(len(ids), SHIPPED_VIEWS - 1)
        self.assertNotIn("harvested-estate", ids)
        self.assertIn("without harvested-estate", estate.pins(self.root)["shipped views"])
        path.write_text(text.replace("shipped_views: package\n",
                                     "shipped_views: {from: package, without: [harvest-estate]}\n"),
                        encoding="utf-8")
        with self.assertRaises(ViewError) as caught:
            estate.views_of(self.root)
        self.assertIn("harvest-estate", str(caught.exception))


class TestLibraryFromThePackage(_Estate):
    def setUp(self) -> None:
        super().setUp()
        self.init()

    def test_a_layer_of_the_estates_own_belongs_in_library_paths(self) -> None:
        (self.root / "27_PATTERNS").mkdir()
        with self.assertRaises(LibraryError) as caught:
            library_roots(self.root)
        self.assertIn("library_paths", str(caught.exception))

    def test_the_adoption_copy_reads_the_package_too(self) -> None:
        scratch = self.tmp / "scratch"
        place = estate_copy(self.root, scratch)
        self.assertEqual(place, scratch)
        self.assertTrue((place / "10_MODEL" / "model.yaml").is_file())
        self.assertEqual(len(estate.views_of(place)), SHIPPED_VIEWS)
        self.assertEqual(library_roots(place)[0].path, shipped_root().resolve())


if __name__ == "__main__":
    unittest.main()
