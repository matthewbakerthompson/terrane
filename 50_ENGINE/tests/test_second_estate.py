"""The second example estate, a health system, beside the sample.

`90_EXAMPLE/thurman-health` is a root of its own -- its model, its views and
a two-kind library -- read with the repository's engine and, through
`shipped_library` in its `model.yaml`, the repository's library. What it is
there to show is that nothing in the metamodel, the shipped shapes or the
shipped views was written for a card issuer only, so these tests hold that:
the gate passes, the products are on shipped shapes, every view draws, and
every view but one is a shipped view copied unchanged.

The estate is read where it lies, never written, so it needs no sandbox; the
refusals of `shipped_library` are tried on throwaway folders instead.
"""

from __future__ import annotations

import io
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli, validate  # noqa: E402
from terrane.archetype import load_archetypes  # noqa: E402
from terrane.connections import kind_of, load_connections  # noqa: E402
from terrane.library import LibraryError, library_roots  # noqa: E402
from terrane.model import load  # noqa: E402
from terrane.query import load_views, resolve  # noqa: E402

from _fixture import REPO, drawable, remove_scratch  # noqa: E402

ESTATE = REPO / "90_EXAMPLE" / "thurman-health"

#: The one view written for the estate rather than copied: the shipped
#: value stream view, pointed at the cancer center's stream.
RETARGETED = {"cancer-care-capabilities.view.yaml"}

#: What the gate is allowed to say about the estate, and why. Its AWS and
#: Google shapes wait for landing zones an all-Azure estate will never have,
#: once a shape; its Azure landing zone has no foundation model service, which
#: the one AI part asks for. Nothing was made up for a CMDB. The two systems
#: recording no control are the gap left on purpose. The shipped patterns'
#: owners and controls were the card issuer's and said so fifty-one times;
#: they are the estate's own now, in its model.yaml.
EXPECTED_WARNINGS = {
    "cmdb.unlinked", "governance.no_control", "library.landing_zone_gap",
    "library.no_landing_zone",
}
UNCONTROLLED = {"SYS-CDW-PIPELINE", "SYS-CDW-SEMANTIC"}

#: The ids it held only because the shipped library named them, which it now
#: calls what a health system calls them.
WERE_THE_SAMPLES = {
    "ORG-TECH", "SYS-DATA-INGEST", "TS-SNOWFLAKE", "TS-COLLIBRA", "TS-ENTRA-ID",
    "POL-TPRM", "CTL-TPRM-DD",
}


class TheHealthcareEstate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = load(ESTATE)
        cls.views = load_views(ESTATE / "30_VIEWS")
        cls.report = validate.run(cls.model, cls.views)

    def test_the_gate_passes(self) -> None:
        self.assertEqual([f.format() for f in self.report.errors], [])

    def test_what_the_gate_still_says_is_what_was_meant(self) -> None:
        self.assertLessEqual({f.code for f in self.report.warnings}, EXPECTED_WARNINGS)
        named = {f.message.split()[1] for f in self.report.warnings if f.code == "governance.no_control"}
        self.assertEqual(named, UNCONTROLLED)

    def test_it_is_read_with_the_repositorys_library(self) -> None:
        roots = library_roots(ESTATE)
        self.assertEqual(roots[0].path.resolve(), REPO.resolve())
        self.assertEqual([r.name for r in roots[1:]], ["library"])

    def test_its_products_are_built_from_shipped_shapes(self) -> None:
        shipped = load_archetypes(REPO)
        products = self.model.all_of("products")
        self.assertEqual(len(products), 4)
        for product in products:
            self.assertIn(product["archetype"], shipped, product["product_id"])
            built = [s for s in self.model.all_of("systems")
                     if s.get("archetype_instance") == product["product_id"]]
            self.assertTrue(built, "%s built nothing" % product["product_id"])

    def test_it_answers_the_library_with_its_own_records(self) -> None:
        """The private path to a vendor is Infrastructure and Cloud's here, not
        the whole technology org's as in the sample; the warehouse reads what
        Thurman's own ingestion lands; the portal signs in through Thurman's
        identity platform, found as the landing zone's identity provider."""
        held = {str(r[pk]) for pk, kind in (("org_unit_id", "org_units"), ("system_id", "systems"),
                                            ("tech_service_id", "tech_services"),
                                            ("policy_id", "policies"), ("control_id", "controls"))
                for r in self.model.all_of(kind)}
        self.assertEqual(held & WERE_THE_SAMPLES, set())
        for egress in ("SYS-CLAIMS-EGRESS", "SYS-TELEHEALTH-EGRESS"):
            self.assertEqual(self.model.get("systems", egress)["owner_org_id"], "ORG-INFRA")
        self.assertEqual(
            self.model.get("interfaces", "INT-CDW-INGEST")["source_system_id"], "SYS-CLINICAL-INGEST")
        uses = {(r["system_id"], r["tech_service_id"])
                for r in self.model.relations["system_uses_tech_service"]}
        self.assertIn(("SYS-PORTAL-WEB", "TS-IDENTITY"), uses)
        self.assertIn(("SYS-CDW-PIPELINE", "TS-CLOUD-WAREHOUSE"), uses)
        governed = {(r["system_id"], r["control_id"])
                    for r in self.model.relations["system_governed_by_control"]}
        self.assertIn(("SYS-CLAIMS-VENDOR", "CTL-BA-DUE-DILIGENCE"), governed)

    def test_the_patterns_it_applies_name_its_own_register(self) -> None:
        codes = {f.code for f in self.report.findings}
        self.assertNotIn("pattern.unknown_control", codes)
        self.assertNotIn("pattern.unknown_owner", codes)
        adoption = self.model.config["patterns"]
        applied = {p for r in self.model.all_of("products") for p in self.model.list_of(r, "patterns")}
        self.assertLessEqual(applied, set(adoption))

    def test_a_cloud_it_has_no_landing_zone_on_has_no_gaps(self) -> None:
        gaps = [f.message for f in self.report.warnings if f.code == "library.landing_zone_gap"]
        self.assertEqual(len(gaps), 1, gaps)
        self.assertIn("the Azure landing zone answers for no `foundation-model-service`", gaps[0])

    def test_a_shape_for_a_cloud_it_does_not_use_waits(self) -> None:
        """The AWS and Google shapes bind services this estate has no reason
        to hold. They wait, as they do on an empty model, rather than fail."""
        self.assertNotIn("library.bind_unknown", {f.code for f in self.report.findings})
        waiting = {f.message.split()[1] for f in self.report.warnings if f.code == "library.no_landing_zone"}
        self.assertIn("aws-product-onboarding", waiting)
        self.assertIn("gcp-digital-product", waiting)

    def test_every_interface_is_of_a_kind_and_the_clinical_ones_are_its_own(self) -> None:
        kinds = load_connections(ESTATE)
        self.assertEqual(kinds["hl7v2-feed"].library, "library")
        self.assertEqual(kinds["dicom-transfer"].library, "library")
        for interface in self.model.all_of("interfaces"):
            self.assertIsNotNone(kind_of(interface, kinds), interface["interface_id"])
        adt = self.model.get("interfaces", "INT-EHR-ENGINE-ADT")
        self.assertEqual(kind_of(adt, kinds), "hl7v2-feed")

    def test_every_view_draws_something(self) -> None:
        for view in self.views:
            with self.subTest(view=view.view_id):
                drawn = drawable(self.model, view)
                self.assertIsNotNone(drawn, "no subject to draw")
                self.assertTrue(resolve(self.model, drawn).nodes)

    def test_its_views_are_the_shipped_ones_unchanged(self) -> None:
        """A view is a query, so the card issuer's views should draw a
        hospital. Copied and held equal here: a shipped view that changes
        is copied again, and one that cannot be is a view to look at."""
        mine = sorted(p.name for p in (ESTATE / "30_VIEWS").glob("*.view.yaml"))
        extra = {name for name in mine if not (REPO / "30_VIEWS" / name).exists()}
        self.assertEqual(extra, RETARGETED)
        for name in sorted(set(mine) - RETARGETED):
            with self.subTest(view=name):
                self.assertEqual(
                    (ESTATE / "30_VIEWS" / name).read_bytes(),
                    (REPO / "30_VIEWS" / name).read_bytes(),
                    "copy 30_VIEWS/%s over the estate's" % name,
                )

    def test_it_renders(self) -> None:
        """`terrane render` over the estate, the index included: the index once
        failed on a library that adds kinds and replaces none. Every format,
        for one view: a run for one format writes its index to scratch, and
        the merge that brought this test beside that rule left it red."""
        out = Path(tempfile.mkdtemp(prefix="aac-estate-"))
        try:
            with redirect_stdout(io.StringIO()):
                code = cli.main(["--root", str(ESTATE), "render", "--view", "hub-and-spoke", "--out", str(out)])
            self.assertEqual(code, 0)
            index = (out / "INDEX.md").read_text(encoding="utf-8")
            self.assertIn("`library/` adds 2 connection kinds", index)
            self.assertTrue((out / "mermaid" / "hub-and-spoke--sys-interface-engine.mmd").exists())
        finally:
            remove_scratch(out, "aac-estate-")

    def test_the_app_opens_it(self) -> None:
        """`server.py --root` sets the root every handler reads from."""
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = ESTATE.resolve()
        try:
            model, views = server_module._load_all()
            self.assertEqual(model.config.get("name"), "Thurman Health")
            self.assertEqual(len(views), len(self.views))
        finally:
            importlib.reload(server_module)


def _estate_at(base: Path, *parts: str, says: str) -> Path:
    root = base.joinpath(*parts)
    (root / "10_MODEL").mkdir(parents=True)
    (root / "10_MODEL" / "model.yaml").write_text(
        textwrap.dedent(says), encoding="utf-8", newline="\n")
    return root


class ShippedLibrarySaysWhatItMeans(unittest.TestCase):
    """`shipped_library` names the repository an estate sits in. Anything
    that would read the library from somewhere a review of the model would
    not see, or from two places at once, is refused."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="aac-shipped-"))
        (self.base / "repo" / "25_COMPONENTS").mkdir(parents=True)

    def tearDown(self) -> None:
        remove_scratch(self.base, "aac-shipped-")

    def refused(self, root: Path, fragment: str) -> None:
        with self.assertRaises(LibraryError) as caught:
            library_roots(root)
        self.assertIn(fragment, str(caught.exception))

    def test_the_repository_it_sits_in(self) -> None:
        root = _estate_at(self.base, "repo", "estates", "clinic", says="shipped_library: ../..\n")
        self.assertEqual(library_roots(root)[0].path, (self.base / "repo").resolve())

    def test_without_it_the_root_is_the_library(self) -> None:
        root = _estate_at(self.base, "repo", "estates", "clinic", says="name: Clinic\n")
        self.assertEqual(library_roots(root)[0].path, root)

    def test_a_folder_that_does_not_hold_it(self) -> None:
        (self.base / "other" / "25_COMPONENTS").mkdir(parents=True)
        root = _estate_at(self.base, "repo", "clinic", says="shipped_library: ../../other\n")
        self.refused(root, "does not hold this estate")

    def test_a_folder_with_no_library_in_it(self) -> None:
        root = _estate_at(self.base, "repo", "estates", "clinic", says="shipped_library: ..\n")
        self.refused(root, "holds none of")

    def test_an_estate_with_layers_of_its_own(self) -> None:
        root = _estate_at(self.base, "repo", "clinic", says="shipped_library: ..\n")
        (root / "27_PATTERNS").mkdir()
        self.refused(root, "27_PATTERNS of its own")

    def test_a_list_where_a_folder_goes(self) -> None:
        root = _estate_at(self.base, "repo", "clinic", says="shipped_library: [..]\n")
        self.refused(root, "is a folder")


class TheIndexSentence(unittest.TestCase):
    def test_a_library_that_only_adds(self) -> None:
        said = cli._libraries_paragraph([("library", {"connection kind": (2, 0)})])
        self.assertIn("`library/` adds 2 connection kinds. ", said)


if __name__ == "__main__":
    unittest.main()
