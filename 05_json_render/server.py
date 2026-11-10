"""Topic 05 - json-render: one catalog, a streamed spec, several renderers.

  GET  /prompt            the catalog as a model system prompt
  GET  /stream?mode=...   SSE: the spec as JSON Patch ops, one per event
  POST /action            a named action -> JSON Patch ops that change state

The browser renders the spec (index.html); the terminal renders the SAME
spec with ``python render_terminal.py --mode declarative``.

Run:  python server.py     then open http://localhost:8005
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import server_base  # noqa: E402
from common.sales_data import ALLOWED_ACTIONS, reorder  # noqa: E402
from spec import build_spec, catalog_prompt, to_patches, validate  # noqa: E402


def stream(params: dict):
    spec = build_spec(params.get("mode", "declarative"))
    errors = validate(spec)
    if errors:  # never stream an invalid spec
        yield {"errors": errors}
        return
    for op in to_patches(spec):
        if server_base.DELAY:
            time.sleep(server_base.DELAY)
        yield {"patch": [op]}
    yield {"done": True}


def action(params: dict) -> dict:
    name = params.get("name")
    if name not in ALLOWED_ACTIONS:
        return {"patch": [{"op": "replace", "path": "/state/status", "value": f"refused action '{name}'"}]}
    crates = int((params.get("params") or {}).get("crates", 60))
    return {"patch": [{"op": "replace", "path": "/state/status", "value": reorder(crates)}]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8005)
    args = ap.parse_args()
    server_base.serve(args.port, Path(__file__).parent,
                      json_routes={"/prompt": lambda p: {"prompt": catalog_prompt()}, "/action": action},
                      sse_routes={"/stream": stream},
                      title="Topic 05 - json-render spec + patches")
