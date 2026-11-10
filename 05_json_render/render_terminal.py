"""A second render target: the SAME spec, drawn as text in a terminal.

    python render_terminal.py --mode declarative
    python render_terminal.py --mode hybrid

One catalog, two renderers: the browser maps each type to DOM, this file
maps each type to lines of text. A terminal cannot run HTML, so the
GeneratedView escape hatch degrades to a notice - a real limit of
open-ended output.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.json_patch import get_pointer  # noqa: E402
from spec import MODES, build_spec, validate  # noqa: E402


def resolve(value, state):
    return get_pointer(state, value["$state"]) if isinstance(value, dict) and "$state" in value else value


def render(spec: dict, eid: str, indent: int = 0) -> list[str]:
    el = spec["elements"][eid]
    p = {k: resolve(v, spec["state"]) for k, v in el.get("props", {}).items()}
    pad = "  " * indent
    kind = el["type"]
    if kind in ("Column", "Row"):
        out = []
        for child in el.get("children", []):
            out += render(spec, child, indent + (kind == "Row"))
        return out
    if kind == "Heading":
        return [pad + p["text"].upper(), pad + "=" * len(p["text"])]
    if kind == "Text":
        return [pad + p["text"]]
    if kind == "MetricCard":
        body = f"{p['label']}: {p['value']}  {p.get('delta', '')}".rstrip()
        return [pad + "┌" + "─" * (len(body) + 2) + "┐", pad + f"│ {body} │", pad + "└" + "─" * (len(body) + 2) + "┘"]
    if kind == "BarChart":
        top = max(d["value"] for d in p["data"]) or 1
        lines = [pad + (p.get("title") or "")]
        lines += [pad + f"{d['label']:>4} {'█' * round(24 * d['value'] / top)} {d['value']:,}" for d in p["data"]]
        return lines
    if kind == "Button":
        return [pad + f"[ {p['label']} ]  (action: {p['action']['name']})"]
    if kind == "GeneratedView":
        return [pad + "[GeneratedView: custom HTML - open the browser target to see it]"]
    return [pad + f"<unknown {kind}>"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=MODES, default="declarative")
    args = ap.parse_args()
    spec = build_spec(args.mode)
    errors = validate(spec)
    if errors:
        sys.exit("invalid spec:\n" + "\n".join(errors))
    print("\n".join(render(spec, spec["root"])))
