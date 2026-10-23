"""Build the sdist and the wheel from it, install the wheel into a fresh
virtual environment, and use it from an empty folder: the check to run
before a release.

    python tools/wheel_check.py            (from 50_ENGINE)

What it proves: the sdist carries the package's source and nothing else of
the repository's, and a wheel built from it alone is whole; the shipped
folders travel inside the package (the views, the library, the marks, the
faces, ELK and Cytoscape, the examples, the landing zones, the sample's
answers), the `terrane` command is on the path and nothing is installed as
`aac`, a sketch and a reader's file draw, a part draws with what it
requires, both examples on the library draw, an editable deck and a draw.io
file are written with no repository around, `terrane init` and `terrane
app` point an empty estate at a spreadsheet the wheel carries, and the
wheel is named `terrane` and carries the license and its notice. Both files are copied to
`dist/` at the repository's root once they pass; `tools/release.py` runs
this and uploads the two it proved.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import venv
import zipfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parent
# The views the repository ships, counted rather than remembered: "more
# than fifty" was written when 55 shipped, and once 48 did it stopped
# `release.py` here before anything was uploaded.
SHIPPED_VIEWS = len(list((REPO / "30_VIEWS").glob("*.yaml")))
SMOKE = r'''
from pathlib import Path
import terrane, terrane.shipped as shipped
from terrane.draw.elk import vendor_file, CYTOSCAPE_FILE
root, web = shipped.shipped_root(), shipped.shipped_web()
assert shipped.repo_root() is None, "the installed package still sees a repository"
assert "site-packages" in str(root), root
assert vendor_file(web) is not None and vendor_file(web, CYTOSCAPE_FILE) is not None, "ELK or Cytoscape missing"
d = terrane.diagrams(str(root / "90_EXAMPLE" / "quick" / "sample.vsdx"), date="2026-10-17")
assert sorted(d) == ["applications", "data"], sorted(d)
p = terrane.diagrams(terrane.part("mobile-channel"), date="2026-10-17")
assert "SYS-SAMPLE-API" in p["product-architecture--PRD-SAMPLE-MOBILE-CHANNEL"].svg
d.pack(Path("deck.pptx"), title="Visio", editable=True)
d.drawio(Path("visio.drawio"))
d.excel(Path("visio.xlsx"))
back = terrane.diagrams("visio.xlsx", date="2026-10-17")
assert sorted(back) == ["applications", "data"], "the workbook did not read back as the drawing: %s" % sorted(back)
presets = terrane.presets()
link = terrane.connect("SYS-A", "SYS-B", "API call")
assert link["protocol"] == "HTTPS" and presets["connections"], "the connection kinds are not in the wheel"
made = terrane.made_by(terrane.from_parts("AWS", "Portal", parts=["web-app-baseline"]))
assert any(m["part"] == "api-service" for rows in made.values() for m in rows), "the parts made nothing"
for name in ("on-a-shape", "from-parts"):
    drawn = terrane.diagrams(terrane.example(name), date="2026-10-17")
    assert len(drawn) and not [n for n in drawn.notes if n.startswith("ERROR")], (name, drawn.notes)
assert len(terrane.views()) == SHIPPED_VIEWS and len(presets["kits"]) > 5, "the shipped views or kits are not in the wheel"
print("ok: %d parts, %d views, %d shapes; deck %d bytes, drawio %d bytes" % (
    len(presets["parts"]), len(terrane.views()), len(presets["shapes"]), Path("deck.pptx").stat().st_size,
    Path("visio.drawio").stat().st_size))
'''


def _inside_the_wheel(said: str, who: str) -> None:
    """A path a command tells a pip user to open is a file of the installed
    package, not of the repository the wheel was built in."""
    path = Path(said)
    assert path.is_file() and "site-packages" in path.parts, "%s names %s" % (who, said)


def main() -> int:
    # The build used to clear `ENGINE / "dist"` first, with an rmtree and
    # `ignore_errors=True` on a path worked out from this file's own place:
    # the kind of delete that emptied most of AppData\Local on 2026-10-18.
    # The files are built into the check's own folder now, so a stale one
    # cannot be picked up, and only the two that passed are copied to
    # `dist/`; nothing is removed.
    work = Path(tempfile.mkdtemp(prefix="aac-wheel-"))
    built = work / "dist"
    # No --wheel: `build` makes the sdist, then the wheel from the sdist
    # alone, as anyone building from PyPI's source would. Built from the
    # tree instead, the wheel passed while the sdist held the engine alone.
    subprocess.run([sys.executable, "-m", "build", "--outdir", str(built), str(REPO)], check=True)
    sdist, wheel = next(built.glob("*.tar.gz")), next(built.glob("*.whl"))
    print("built", sdist.name, "and", wheel.name, "from it")
    with tarfile.open(sdist) as tar:
        top = sdist.name[:-len(".tar.gz")] + "/"
        members = {name[len(top):] for name in tar.getnames() if name.startswith(top)}
    for needed in ("pyproject.toml", "LICENSE", "THIRD_PARTY_NOTICES.md", "LICENSES", "50_ENGINE/terrane/__init__.py",
                   "30_VIEWS", "80_APP/web/vendor/elk.bundled.js", "80_APP/web/index.html", "80_APP/app/server.py",
                   "10_MODEL/model.yaml"):
        assert any(m == needed or m.startswith(needed + "/") for m in members), "the sdist has no %s" % needed
    strays = sorted({m.split("/")[0] for m in members} & {"70_ARTIFACTS", "00_METHOD", "60_SOURCES"})
    assert not strays and not any(m.startswith("50_ENGINE/tests") for m in members), "the sdist carries %s" % strays
    print("the sdist carries the package's source and no more (%d files)" % len(members))
    # What PyPI shows and what a copy must carry: the name the upload goes
    # under, the license expression, and PolyForm's Required Notice itself,
    # with the line of business that keeps Shield's noncompete on a product
    # that pauses.
    with zipfile.ZipFile(wheel) as z:
        info = wheel.name.split("-")[0] + "-" + wheel.name.split("-")[1] + ".dist-info/"
        metadata = z.read(info + "METADATA").decode("utf-8").splitlines()
        notice = z.read(info + "licenses/LICENSE").decode("utf-8")
        carried = set(z.namelist())
    assert "Name: terrane" in metadata, "the wheel is not named terrane"
    assert any(line.startswith("License-Expression: LicenseRef-PolyForm-Shield-1.0.0 AND ") for line in metadata), \
        "the wheel names no license, or not what it bundles"
    assert "License-File: LICENSE" in metadata and "Required Notice" in notice, "the wheel carries no notice"
    assert "License-File: THIRD_PARTY_NOTICES.md" in metadata, "the wheel carries no third-party notices"
    bundled_texts = [n for n in carried if n.startswith(info + "licenses/LICENSES/")]
    assert len(bundled_texts) == len(list((REPO / "LICENSES").iterdir())), "the wheel lacks a bundled license text"
    for page in ("terrane/shipped/app/server.py", "terrane/shipped/web/index.html", "terrane/shipped/web/app.js"):
        assert page in carried, "the wheel has no %s" % page
    assert "Licensor Line of Business: Terrane" in notice, "the wheel's license names no line of business"
    print("the license and its notice are in the wheel")
    env_dir = work / "venv"
    venv.create(env_dir, with_pip=True)
    python = env_dir / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    subprocess.run([str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", str(wheel)],
                   check=True)
    empty = work / "empty"
    empty.mkdir()
    bin_dir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    terrane_cmd = bin_dir / ("terrane.exe" if os.name == "nt" else "terrane")
    # `aac` is AaC's module and command on PyPI; installing either here
    # would break theirs, or ours, in an environment that holds both.
    assert not list(bin_dir.glob("aac*")), "the wheel installs an aac command"
    found = subprocess.run([str(python), "-c", "import importlib.util as u; print(u.find_spec('aac') is None)"],
                           capture_output=True, text=True, cwd=str(empty), check=True)
    assert found.stdout.strip() == "True", "the wheel installs an aac module"
    example = subprocess.run([str(terrane_cmd), "draw", "--example"], capture_output=True, text=True,
                             cwd=str(empty), check=True)
    assert "views:" in example.stdout, "terrane draw --example printed no sketch"
    print("terrane on the path and nothing as aac; the example prints")
    # An estate in a folder of its own reads the library and the views from
    # the wheel: before `shipped_library: package` it saw none of either.
    init = subprocess.run([str(terrane_cmd), "init", "estate", "--name", "Wheel estate"], capture_output=True,
                          text=True, cwd=str(empty))
    assert init.returncode == 0 and " 0 error(s)" in init.stdout, init.stdout + init.stderr
    _inside_the_wheel(init.stdout.splitlines()[-1].strip(), "terrane init")
    stats =subprocess.run([str(terrane_cmd), "--root", "estate", "stats"], capture_output=True, text=True,
                           cwd=str(empty), check=True).stdout
    # The heading line, not the first "views:": `shipped views:` comes first.
    views = [line for line in stats.split("\nviews:\n", 1)[1].split("\n\n", 1)[0].splitlines() if line.strip()]
    assert "library: the installed terrane" in stats and len(views) == SHIPPED_VIEWS, stats
    assert " 0 component type(s)" not in stats, "the estate read no library from the wheel"
    print("terrane init starts an estate on the wheel's library and its %d views" % len(views))
    # The app from the wheel, on that estate: `terrane app` starts the
    # server that ships inside the package, which serves the pages beside
    # it and the estate it was pointed at.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    # Unbuffered, so the note the app prints on starting is there to read
    # once it is stopped: a stopped process on Windows flushes nothing.
    app = subprocess.Popen([str(terrane_cmd), "--root", "estate", "app", "--no-browser", "--port", str(port)],
                           cwd=str(empty), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           env=dict(os.environ, PYTHONUNBUFFERED="1"))
    try:
        overview = None
        for _ in range(150):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/api/overview" % port, timeout=2) as r:
                    overview = json.loads(r.read().decode("utf-8"))
                break
            except OSError:
                if app.poll() is not None:
                    break
                time.sleep(0.2)
        assert overview is not None, "terrane app did not answer: %s" % (app.stdout.read() if app.poll() is not None else "")
        assert overview.get("modelName") == "Wheel estate", overview.get("modelName")
        assert len(overview.get("views") or []) == SHIPPED_VIEWS, len(overview.get("views") or [])
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=5) as r:
            page = r.read().decode("utf-8")
        with urllib.request.urlopen("http://127.0.0.1:%d/app.js" % port, timeout=5) as r:
            script_bytes = len(r.read())
        assert "<title>" in page and script_bytes > 100000, "terrane app served no page"
    finally:
        app.terminate()
        try:
            app.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app.kill()
    print("terrane app opens the estate from the wheel, with its %d views" % len(overview["views"]))
    # The estate is empty, so the app says how to fill it: in 1.0.0 with
    # `../90_EXAMPLE/csv`, a folder of the repository's no install has.
    said = app.stdout.read()
    assert "90_EXAMPLE/csv" not in said and "terrane adopt" in said, said
    lines = said.splitlines()
    sample = [i for i, line in enumerate(lines) if line.lstrip().startswith("sample")]
    assert sample, "terrane app named no sample for an empty estate: %s" % said
    _inside_the_wheel(lines[sample[0] + 1].strip(), "terrane app")
    print("an empty estate is pointed at a spreadsheet the wheel carries")
    subprocess.run([str(python), "-X", "utf8", "-c", SMOKE.replace("SHIPPED_VIEWS", str(SHIPPED_VIEWS))],
                   check=True, cwd=str(empty))
    dist = REPO / "dist"
    dist.mkdir(exist_ok=True)
    for made in (sdist, wheel):
        shutil.copy2(made, dist / made.name)
    print("the wheel works from an empty folder:", dist / wheel.name)
    print("and the sdist it was built from:", dist / sdist.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
