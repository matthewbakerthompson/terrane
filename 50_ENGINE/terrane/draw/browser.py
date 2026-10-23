"""A headless browser, driven from Python over the DevTools protocol, and
the PNG of a drawing through it.

A PNG is a rasterizer's job and the engine ships none; what nearly every
machine ships is a Chrome or an Edge. This is the smallest thing that uses
one from the standard library: launch it with a debugging port, open a
page over its websocket, evaluate JavaScript, read the answer, take the
screenshot. The dev tools under `80_APP/tools/dev/` drive the app with the
same class to read layouts and font metrics back; `terrane render --png` and
`terrane draw --png` shoot each drawing with it (`terrane.draw.raster`), and the
faces inside the picture are the ones the browser sets it in, which
`resvg-py` cannot, since it reads TrueType and OpenType and the app ships
woff2.

    with Chrome() as browser:
        page = browser.page("http://127.0.0.1:8020/#view=capability-map")
        page.wait_for("document.readyState === 'complete'")
        print(page.evaluate("document.title"))

The browser is found through `TERRANE_CHROME`, then the usual places, then
the path. The websocket client speaks just enough of RFC 6455 for one
local, unencrypted connection: masked text frames out, any frame in,
fragments joined, pings answered.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

CHROMES = [
    os.environ.get("TERRANE_CHROME"),
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
]


def browser_path() -> Optional[str]:
    """A Chrome or an Edge on this machine, or None."""
    for candidate in CHROMES:
        if candidate and Path(candidate).exists():
            return candidate
    for name in ("google-chrome", "chromium", "chrome", "msedge", "microsoft-edge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def find_chrome() -> str:
    found = browser_path()
    if not found:
        raise RuntimeError("no Chrome or Edge found; set TERRANE_CHROME to a chrome.exe or msedge.exe")
    return found



def mask_payload(payload: bytes, mask: bytes) -> bytes:
    """The payload XORed with the four-byte mask, as the websocket client
    side must send it: done on the whole payload as one integer, since
    the ELK bundle is a megabyte and a half and a generator over its bytes
    was a fifth of a second on every browser opened."""
    if not payload:
        return b""
    repeated = (mask * (len(payload) // 4 + 1))[:len(payload)]
    return (int.from_bytes(payload, "big") ^ int.from_bytes(repeated, "big")).to_bytes(len(payload), "big")

class _WebSocket:
    """One client connection to a `ws://` URL on the local machine."""

    def __init__(self, url: str) -> None:
        rest = url[len("ws://"):]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)
        )
        self.sock.sendall(request.encode("ascii"))
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket handshake closed early")
            head += chunk
        status = head.split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise ConnectionError("websocket handshake refused: %r" % status)
        self.buffer = head.split(b"\r\n\r\n", 1)[1]

    def _read(self, n: int) -> bytes:
        while len(self.buffer) < n:
            chunk = self.sock.recv(max(65536, n - len(self.buffer)))
            if not chunk:
                raise ConnectionError("websocket closed")
            self.buffer += chunk
        out, self.buffer = self.buffer[:n], self.buffer[n:]
        return out

    def send_text(self, text: str) -> None:
        payload = text.encode("utf-8")
        head = bytearray([0x81])
        length = len(payload)
        if length < 126:
            head.append(0x80 | length)
        elif length < 65536:
            head.append(0x80 | 126)
            head += struct.pack(">H", length)
        else:
            head.append(0x80 | 127)
            head += struct.pack(">Q", length)
        mask = os.urandom(4)
        self.sock.sendall(bytes(head) + mask + mask_payload(payload, mask))

    def recv_text(self) -> str:
        """The next complete text message, fragments joined, pings answered."""
        parts = []
        while True:
            b0, b1 = self._read(2)
            fin, opcode = b0 & 0x80, b0 & 0x0F
            length = b1 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b1 & 0x80 else None
            data = self._read(length)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x9:
                self.sock.sendall(bytes([0x8A, 0x80]) + b"\x00\x00\x00\x00")
                continue
            if opcode == 0x8:
                raise ConnectionError("websocket closed by the browser")
            if opcode in (0x1, 0x0):
                parts.append(data)
                if fin:
                    return b"".join(parts).decode("utf-8")
            # Binary and pong frames carry nothing this client asked for.

    def close(self) -> None:
        try:
            self.sock.sendall(bytes([0x88, 0x80]) + b"\x00\x00\x00\x00")
        except OSError:
            pass
        self.sock.close()


class Page:
    """One tab, with the things a capture needs: evaluate, wait, shoot."""

    def __init__(self, ws_url: str, target_id: str = "") -> None:
        self.ws = _WebSocket(ws_url)
        self.target_id = target_id
        self.next_id = 0
        self.events: List[dict] = []

    def send(self, method: str, **params: Any) -> Dict[str, Any]:
        self.next_id += 1
        my_id = self.next_id
        self.ws.send_text(json.dumps({"id": my_id, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv_text())
            if message.get("id") == my_id:
                if "error" in message:
                    raise RuntimeError("%s: %s" % (method, message["error"]))
                return message.get("result", {})
            self.events.append(message)

    def navigate(self, url: str) -> None:
        self.send("Page.navigate", url=url)

    def evaluate(self, expression: str, await_promise: bool = False) -> Any:
        """The value of a JavaScript expression in the page, by value."""
        result = self.send(
            "Runtime.evaluate", expression=expression, returnByValue=True,
            awaitPromise=await_promise,
        )
        if "exceptionDetails" in result:
            detail = result["exceptionDetails"]
            text = detail.get("exception", {}).get("description") or detail.get("text")
            raise RuntimeError("page script failed: %s" % text)
        return result.get("result", {}).get("value")

    def screenshot(self, width: float, height: float, scale: float = 1.0) -> bytes:
        """A PNG of the page's top-left `width` by `height` CSS pixels, at
        `scale` device pixels each, whatever the window's size."""
        result = self.send(
            "Page.captureScreenshot", format="png", captureBeyondViewport=True,
            clip={"x": 0, "y": 0, "width": width, "height": height, "scale": scale},
        )
        return base64.b64decode(result["data"])

    def wait_for(self, expression: str, timeout: float = 30.0, settle: float = 0.0) -> None:
        """Poll until the expression is truthy, then let the page settle."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.evaluate(expression):
                if settle:
                    time.sleep(settle)
                return
            time.sleep(0.2)
        raise TimeoutError("waited %.0fs for %s" % (timeout, expression))

    def close(self) -> None:
        self.ws.close()


def _remove_own(folder: Path, prefix: str) -> None:
    """Remove a folder made here with `tempfile.mkdtemp(prefix=prefix)`, and
    refuse anything else. On 2026-10-18 a test's
    `shutil.rmtree(root.parents[1], ignore_errors=True)` emptied most of
    AppData\\Local, `ignore_errors` hiding that the target was wrong; once
    the folder is known to be the one made here, what is left to ignore is
    a browser still holding its profile a moment after it ends."""
    if not (folder.parent == Path(tempfile.gettempdir()) and folder.name.startswith(prefix)
            and folder.name != prefix and not folder.is_symlink()):
        raise RuntimeError("refusing to remove %s: not a %s* folder made in %s"
                           % (folder, prefix, tempfile.gettempdir()))
    shutil.rmtree(folder, ignore_errors=True)


class Chrome:
    """One headless browser, launched on entry and ended on exit."""

    def __init__(self, width: int = 1600, height: int = 1000) -> None:
        self.width, self.height = width, height
        self.profile = Path(tempfile.mkdtemp(prefix="aac-chrome-"))
        self.process: Optional[subprocess.Popen] = None
        self.port = 0
        self.pages: List[Page] = []

    def __enter__(self) -> "Chrome":
        args = [
            find_chrome(), "--headless=new", "--remote-debugging-port=0",
            "--user-data-dir=%s" % self.profile, "--window-size=%d,%d" % (self.width, self.height),
            "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
            "--disable-gpu", "--no-sandbox", "--disable-extensions", "about:blank",
        ]
        self.process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        marker = self.profile / "DevToolsActivePort"
        deadline = time.time() + 30
        while time.time() < deadline:
            if marker.exists():
                # The browser is still writing the file the first time it
                # shows up, and Windows refuses the read while it does.
                try:
                    lines = marker.read_text(encoding="utf-8").splitlines()
                except OSError:
                    lines = []
                if lines and lines[0].strip().isdigit():
                    self.port = int(lines[0].strip())
                    break
            if self.process.poll() is not None:
                raise RuntimeError("the browser exited before it listened")
            time.sleep(0.1)
        if not self.port:
            raise TimeoutError("the browser did not open its debugging port")
        return self

    def page(self, url: str, init_script: str = "") -> Page:
        """A fresh tab at `url`. `init_script` runs before the page's own
        scripts, on every document: what `evaluateOnNewDocument` does."""
        request = urllib.request.Request(
            "http://127.0.0.1:%d/json/new?about:blank" % self.port, method="PUT")
        with urllib.request.urlopen(request, timeout=30) as response:
            target = json.loads(response.read().decode("utf-8"))
        page = Page(target["webSocketDebuggerUrl"], str(target.get("id") or ""))
        page.send("Page.enable")
        page.send("Runtime.enable")
        page.send("Emulation.setDeviceMetricsOverride", width=self.width, height=self.height,
                  deviceScaleFactor=1, mobile=False)
        if init_script:
            page.send("Page.addScriptToEvaluateOnNewDocument", source=init_script)
        page.navigate(url)
        self.pages.append(page)
        return page

    def close_page(self, page: Page) -> None:
        """Close the tab itself, not only the connection to it: three hundred
        drawings shot through one browser would otherwise be three hundred
        open tabs."""
        page.close()
        if page in self.pages:
            self.pages.remove(page)
        if page.target_id:
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/json/close/%s" % (self.port, page.target_id),
                                       timeout=10).close()
            except OSError:
                pass

    def __exit__(self, *exc) -> None:
        for page in self.pages:
            try:
                page.close()
            except OSError:
                pass
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        _remove_own(self.profile, "aac-chrome-")


class Rasterizer:
    """PNGs of SVG texts through one headless browser, opened on entry and
    closed on exit, so a hundred drawings cost one launch. Each SVG is
    written to a file and opened as a document of its own, waited for
    (loaded, faces ready), measured by its viewBox and shot at `scale`
    device pixels per CSS pixel: the sheet at 2x, as the app exports it."""

    def __init__(self, scale: float = 2.0) -> None:
        self.scale = scale
        self.browser: Optional[Chrome] = None
        self.folder: Optional[Path] = None
        self.count = 0

    def __enter__(self) -> "Rasterizer":
        self.browser = Chrome(width=1600, height=1200).__enter__()
        self.folder = Path(tempfile.mkdtemp(prefix="aac-png-"))
        return self

    def __call__(self, svg_text: str) -> bytes:
        if self.browser is None or self.folder is None:
            raise RuntimeError("Rasterizer is used inside a `with` block")
        self.count += 1
        path = self.folder / ("%d.svg" % self.count)
        path.write_text(svg_text, encoding="utf-8")
        page = self.browser.page(path.resolve().as_uri())
        try:
            page.wait_for("document.readyState === 'complete' && !!document.documentElement.getAttribute('viewBox')",
                          timeout=60)
            # The faces are inside the picture as data URIs; the browser still
            # decodes them after the document is complete.
            page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true", await_promise=True)
            box = page.evaluate("document.documentElement.getAttribute('viewBox').split(/\\s+/).map(Number)")
            return page.screenshot(box[2], box[3], self.scale)
        finally:
            self.browser.close_page(page)
            try:
                path.unlink()
            except OSError:
                pass

    def __exit__(self, *exc) -> None:
        if self.browser is not None:
            self.browser.__exit__(*exc)
            self.browser = None
        if self.folder is not None:
            _remove_own(self.folder, "aac-png-")
            self.folder = None
