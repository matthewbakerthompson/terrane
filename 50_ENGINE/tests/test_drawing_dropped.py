"""A drawing dropped into the app is adopted as `terrane adopt FILE` adopts it.

What is checked: a Visio file and a draw.io file adopted through the app's
endpoints write the same files, byte for byte, as the command line writes
for the same file and owner, corrections included; reading one writes
nothing, stages it outside the repository, and answers with what it would
add, what is here already and what the file says differently, how many
records it leaves without an owner, and the change picture `terrane adopt
--dry-run --picture` draws, without its title block; a file no reader takes, or one
its reader cannot read, is refused with nothing staged; a drawing let go is
removed from where it was staged; and a page the file drew becomes a
diagram the canvas opens, of the things the file drew and no more, filed
under the layer they belong to, the one page of a file named for the file,
so a second drawing adopted keeps its page beside the first.
"""

from __future__ import annotations

import base64
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import cli  # noqa: E402
from terrane.join import change_picture  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402
from terrane.quick import read_any  # noqa: E402

from _fixture import REPO, Sandbox  # noqa: E402

QUICK = REPO / "90_EXAMPLE" / "quick"


def _server(root: Path):
    sys.path.insert(0, str(REPO / "80_APP" / "app"))
    import importlib

    import server as server_module

    importlib.reload(server_module)
    server_module.REPO_ROOT = root
    return server_module


def _upload(path: Path) -> dict:
    return {"name": path.name, "data": base64.b64encode(path.read_bytes()).decode("ascii")}


def _written(root: Path) -> dict:
    """Every file under the model and the views, by its path in the estate."""
    out = {}
    for folder in ("10_MODEL", "30_VIEWS"):
        for path in sorted((root / folder).rglob("*")):
            if path.is_file():
                out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


class TestTheSameAsTheCommand(unittest.TestCase):
    def _both(self, name: str, *args: str) -> None:
        source = QUICK / name
        owner = "ORG-PAYMENTS"
        correct = "--correct" in args
        with Sandbox(seed=True) as by_hand, Sandbox(seed=True) as by_app:
            before = _written(by_app)
            with redirect_stdout(io.StringIO()) as out:
                code = cli.main(["--root", str(by_hand), "adopt", str(source), "--owner", owner] + list(args))
            self.assertEqual(code, 0, out.getvalue())
            server = _server(by_app)
            read = server.api_adopt_read({}, dict(_upload(source), owner=owner, correct=correct))
            self.addCleanup(server.api_adopt_discard, {}, {"token": read["token"]})
            # Read and drawn, and nothing written yet.
            self.assertEqual(_written(by_app), before)
            done = server.api_adopt_write({}, {"token": read["token"], "owner": owner, "correct": correct})
            self.assertEqual(done["errors"], [])
            hand, app = _written(by_hand), _written(by_app)
            self.assertEqual(sorted(app), sorted(hand))
            for path in hand:
                self.assertEqual(app[path], hand[path], path)
            self.assertGreater(len(app), len(before))
            self.assertTrue(done["views"], "no page of %s became a diagram" % name)
            if name == "sample.vsdx":
                # Filed by what most of each page draws: the Data page of the
                # Visio sample is two data assets and the system that reads one.
                layers = {v: read_data_file(by_app / "30_VIEWS" / ("%s.view.yaml" % v)).get("category")
                          for v in ("applications", "data")}
                self.assertEqual(layers, {"applications": "Application", "data": "Data"})

    def test_a_visio_drawing(self) -> None:
        self._both("sample.vsdx")

    def test_a_drawio_file(self) -> None:
        self._both("sample.drawio")

    def test_a_drawio_file_with_its_corrections(self) -> None:
        self._both("sample.drawio", "--correct")


class TestTheDrop(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sandbox = Sandbox(seed=True)
        cls.root = cls.sandbox.__enter__()
        cls.server = _server(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sandbox.__exit__(None, None, None)

    def test_reading_says_what_adopting_would_do_and_writes_nothing(self) -> None:
        before = _written(self.root)
        read = self.server.api_adopt_read({}, _upload(QUICK / "sample.vsdx"))
        staged = self.server._STAGED[read["token"]]["dir"]
        self.addCleanup(self.server.api_adopt_discard, {}, {"token": read["token"]})
        self.assertNotIn(self.root.resolve(), Path(staged).resolve().parents)
        self.assertEqual((read["file"], read["readAs"]), ("sample.vsdx", "a Visio drawing"))
        self.assertEqual([r["name"] for r in read["adds"]["systems"]], ["Authorization switch", "Fraud scoring"])
        # The placeholder owner is the picker's to replace, not a record listed.
        self.assertNotIn("org_units", read["adds"])
        # The two systems: a data asset or a capability needs no owner.
        self.assertEqual(read["unowned"], 2)
        self.assertIn("ORG-PAYMENTS", [o["id"] for o in read["owners"]])
        # The estate's merchant is here, and the drawing says it differently.
        self.assertEqual([r["id"] for r in read["differs"]["actors"]], ["ACT-MERCHANT"])
        self.assertEqual(read["changes"], ["ACT-MERCHANT actor_kind: Organization -> Person"])
        self.assertEqual([v["id"] for v in read["views"]["adds"]], ["applications", "data"])
        self.assertTrue(read["notes"][0].startswith("read 2 systems"), read["notes"])
        doc, _notes = read_any(QUICK / "sample.vsdx", self.root)
        # The page shows it from the app, the engine's picture without its title block.
        self.assertEqual(self.server.api_adopt_picture(parse_qs(urlparse(read["picture"]).query)),
                         change_picture(doc, self.root, source_name="sample.vsdx", sheet=False).svg)
        self.assertEqual(read["pictureTitle"], "What sample.vsdx adds")
        # Read again for an owner and with the corrections: the corrected
        # actor drawn with the heavy border, and still nothing written.
        again = self.server.api_adopt_read({}, {"token": read["token"], "owner": "ORG-PAYMENTS", "correct": True})
        self.assertEqual(again["pictureTitle"], "What sample.vsdx adds and corrects")
        self.assertEqual(again["owner"], "ORG-PAYMENTS")
        self.assertEqual(_written(self.root), before)

    def test_an_owner_the_estate_lacks_is_refused(self) -> None:
        read = self.server.api_adopt_read({}, _upload(QUICK / "sample.drawio"))
        self.addCleanup(self.server.api_adopt_discard, {}, {"token": read["token"]})
        with self.assertRaises(self.server.ApiError):
            self.server.api_adopt_read({}, {"token": read["token"], "owner": "ORG-NOBODY"})

    def test_a_file_no_reader_takes_is_refused_and_nothing_staged(self) -> None:
        staged = set(self.server._STAGED)
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_adopt_read({}, {"name": "notes.txt", "data": base64.b64encode(b"hello").decode("ascii")})
        self.assertIn("not a drawing terrane reads", str(caught.exception))
        with self.assertRaises(self.server.ApiError) as caught:
            self.server.api_adopt_read({}, {"name": "broken.vsdx", "data": base64.b64encode(b"not a zip").decode("ascii")})
        self.assertIn("broken.vsdx could not be read", str(caught.exception))
        self.assertEqual(set(self.server._STAGED), staged)

    def test_what_the_drop_takes_is_the_engines_readers(self) -> None:
        from unittest import mock

        from terrane import quick

        offered = self.server.api_adopt_readers({}, {})
        self.assertEqual(offered["exports"], [".csv", ".xlsx"])
        self.assertEqual(set(offered["drawings"]) | set(offered["exports"]),
                         set(quick.READERS) | {".yaml", ".yml"})
        self.assertEqual(offered["drawings"][".vsdx"], "a Visio drawing")
        # A reader the engine gains is offered and taken with no change to
        # the app; one that cannot read the file says so, and nothing stays.
        staged = set(self.server._STAGED)
        with mock.patch.dict(quick.READERS, {".png": "image"}):
            self.assertEqual(self.server.api_adopt_readers({}, {})["drawings"][".png"], "a drawing")
            with self.assertRaises(self.server.ApiError) as caught:
                self.server.api_adopt_read({}, {"name": "whiteboard.png",
                                                "data": base64.b64encode(b"not a picture").decode("ascii")})
            self.assertIn("whiteboard.png could not be read", str(caught.exception))
        self.assertEqual(set(self.server._STAGED), staged)

    def test_a_drawing_let_go_leaves_nothing_staged(self) -> None:
        read = self.server.api_adopt_read({}, _upload(QUICK / "sample.drawio"))
        folder = Path(self.server._STAGED[read["token"]]["dir"])
        self.assertTrue(folder.is_dir())
        self.server.api_adopt_discard({}, {"token": read["token"]})
        self.assertFalse(folder.exists())
        with self.assertRaises(self.server.ApiError):
            self.server.api_adopt_read({}, {"token": read["token"]})


class TestAnEmptyEstate(unittest.TestCase):
    def test_the_placeholder_owner_is_said_apart_from_the_records(self) -> None:
        # An estate with no org units: no owner to choose, and the page
        # counted nine records where the answer after counted ten.
        with Sandbox() as root:
            server = _server(root)
            read = server.api_adopt_read({}, _upload(QUICK / "sample.vsdx"))
            self.addCleanup(server.api_adopt_discard, {}, {"token": read["token"]})
            self.assertEqual(read["owners"], [])
            added = sum(len(v) for v in read["adds"].values())
            done = server.api_adopt_write({}, {"token": read["token"]})
            self.assertTrue(done["placeholder"])
            self.assertNotIn("org_units", done["added"])
            self.assertEqual(sum(done["added"].values()), added)


class TestThePagesBecomeDiagrams(unittest.TestCase):
    def test_a_page_opens_on_the_canvas_and_a_second_files_page_is_kept_too(self) -> None:
        with Sandbox(seed=True) as root:
            server = _server(root)
            single = root.parent / "Card switch.puml"
            single.write_bytes((QUICK / "sample.puml").read_bytes())
            read = server.api_adopt_read({}, _upload(single))
            self.addCleanup(server.api_adopt_discard, {}, {"token": read["token"]})
            self.assertEqual([v["id"] for v in read["views"]["adds"]], ["card-switch"])
            done = server.api_adopt_write({}, {"token": read["token"], "owner": "ORG-PAYMENTS"})
            self.assertEqual([v["id"] for v in done["views"]], ["card-switch"])
            view = read_data_file(root / "30_VIEWS" / "card-switch.view.yaml")
            # The things the page drew, pinned: a diagram the canvas opens.
            # The reader names its types bare, which in the estate was every
            # system and actor there, the sample's cardholder among them.
            doc, _notes = read_any(QUICK / "sample.puml", root)
            drawn = sorted(str(r[pk]) for t, pk in (("systems", "system_id"), ("data_assets", "data_asset_id"),
                                                    ("actors", "actor_id")) for r in doc[t])
            self.assertEqual(set(view["scope"]), {"pin"})
            self.assertEqual(sorted(view["scope"]["pin"]), drawn)
            model, views = server._load_all()
            adopted = [v for v in views if v.view_id == "card-switch"][0]
            self.assertTrue(server._on_canvas(adopted))
            graph = server.resolve(model, adopted)
            self.assertEqual(sorted(n.key for n in graph.nodes), drawn)
            # Another file of one page: its page is a diagram of its own,
            # where both were `imported` and the second was skipped.
            other = root.parent / "Fraud.mmd"
            other.write_bytes((QUICK / "sample.mmd").read_bytes())
            read = server.api_adopt_read({}, _upload(other))
            self.addCleanup(server.api_adopt_discard, {}, {"token": read["token"]})
            done = server.api_adopt_write({}, {"token": read["token"], "owner": "ORG-PAYMENTS"})
            self.assertEqual([v["id"] for v in done["views"]], ["fraud"])
            self.assertEqual(done["errors"], [])


if __name__ == "__main__":
    unittest.main()
