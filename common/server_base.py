"""A tiny HTTP server built only on the Python standard library.

Every topic uses it, so the basic code needs no `pip install`. It serves:

* the topic's own files (``/`` -> ``index.html``) from the topic folder,
* shared files under ``/common/...`` from this folder,
* JSON routes: ``handler(params) -> dict`` sent as ``application/json``,
* SSE routes:  ``handler(params) -> iterator of dicts``, each one sent as a
  Server-Sent Event line ``data: {...}``.

``params`` merges the query string with a JSON request body (for POST).
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

COMMON_DIR = Path(__file__).resolve().parent

# Streaming demos pause between events so you can watch the UI build up.
# Tests set GENUI_DELAY=0 to run instantly.
DELAY = float(os.environ.get("GENUI_DELAY", "0.25"))


def _safe_file(base: Path, rel: str) -> Path | None:
    """Resolve ``rel`` inside ``base``; refuse anything that escapes it."""
    base = base.resolve()
    target = (base / rel.lstrip("/")).resolve()
    if target != base and base not in target.parents:
        return None
    return target if target.is_file() else None


def make_handler(static_dir: Path, json_routes: dict, sse_routes: dict):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quieter, one line per request
            sys.stderr.write(f"  {fmt % args}\n")

        # -- helpers -------------------------------------------------------
        def _params(self) -> tuple[str, dict]:
            url = urlparse(self.path)
            params = {k: v[-1] for k, v in parse_qs(url.query).items()}
            if self.command == "POST":
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    body = json.loads(self.rfile.read(length))
                    if isinstance(body, dict):
                        params.update(body)
            return url.path, params

        def _send_json(self, obj, status: int = 200) -> None:
            body = json.dumps(obj, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_sse(self, events) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                for event in events:
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # the browser went away mid-stream

        def _send_file(self, path: str) -> None:
            if path == "/":
                path = "/index.html"
            if path.startswith("/common/"):
                target = _safe_file(COMMON_DIR, path[len("/common/"):])
            else:
                target = _safe_file(static_dir, path)
            if target is None:
                return self._send_json({"error": f"not found: {path}"}, 404)
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix == ".js":
                ctype = "text/javascript"
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # -- dispatch ------------------------------------------------------
        def _handle(self) -> None:
            path, params = self._params()
            try:
                if path in sse_routes:
                    return self._send_sse(sse_routes[path](params))
                if path in json_routes:
                    return self._send_json(json_routes[path](params))
            except ValueError as exc:  # handlers raise ValueError for bad input
                return self._send_json({"error": str(exc)}, 400)
            if self.command == "GET":
                return self._send_file(path)
            self._send_json({"error": f"no route {path}"}, 404)

        do_GET = _handle
        do_POST = _handle

    return Handler


def serve(port: int, static_dir, json_routes=None, sse_routes=None, title="GenUI demo") -> None:
    handler = make_handler(Path(static_dir), json_routes or {}, sse_routes or {})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"{title}\n  open http://localhost:{port}   (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
