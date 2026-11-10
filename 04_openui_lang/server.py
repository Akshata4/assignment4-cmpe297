"""Topic 04 - OpenUI Lang: a compact, line-oriented language for UI.

The agent's reply is a *program*, streamed one line at a time. ``root`` is
the entry point and may reference lines that have not arrived yet.

  static       root = MetricCard(...)                      one pre-built component
  declarative  root = Column([...]) + one line per part    composed from the catalog
  open_ended   root = HtmlArtifact(title, "<html>...")      raw HTML, sandboxed
  hybrid       a catalog program with one HtmlArtifact line

``/compare`` measures the same dashboard as OpenUI Lang vs. a nested JSON
tree (characters, and a rough chars/4 token estimate - not a real tokenizer).

Run:  python server.py     then open http://localhost:8004
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import server_base  # noqa: E402
from common.sales_data import SALES, custom_widget_html, money  # noqa: E402
from openui_lang import parse, resolve  # noqa: E402

MODES = ["static", "declarative", "open_ended", "hybrid"]
q = json.dumps  # quote a Python value as an OpenUI Lang literal


def program(mode: str) -> str:
    if mode == "static":
        return f'root = MetricCard("Revenue this week", {q(money(SALES["revenue"]))}, {q(SALES["revenue_delta"])})'
    if mode == "open_ended":
        return f'root = HtmlArtifact("Lemon reorder planner", {q(custom_widget_html())})'
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    # Note the order: root comes FIRST and refers forward to everything else.
    parts = "[title, metrics, planner, chart, reorder]" if mode == "hybrid" else "[title, metrics, chart, reorder]"
    lines = [
        f"root = Column({parts})",
        f'title = Heading({q("Weekly sales · " + SALES["week"])})',
        "metrics = Row([revenue, orders])",
        f'revenue = MetricCard("Revenue", {q(money(SALES["revenue"]))}, {q(SALES["revenue_delta"])})',
        f'orders = MetricCard("Orders", {q(str(SALES["orders"]))}, {q(SALES["orders_delta"])})',
        f'chart = BarChart("Daily revenue", {q(SALES["daily"])})',
        'reorder = Button("Reorder lemons", "reorder")',
    ]
    if mode == "hybrid":
        lines.insert(5, f'planner = HtmlArtifact("Reorder planner", {q(custom_widget_html())})')
    return "\n".join(lines)


def stream(params: dict):
    """Stream the program line by line, the way a model emits it."""
    text = program(params.get("mode", "declarative"))
    parse(text)  # never send a program we cannot parse ourselves
    for line in text.splitlines():
        if server_base.DELAY:
            time.sleep(server_base.DELAY * 2)
        yield {"line": line}
    yield {"done": True}


def compare(_params: dict) -> dict:
    lang = program("declarative")
    tree = resolve(parse(lang))
    as_json = json.dumps(tree, indent=2)
    return {
        "openui_lang": {"chars": len(lang), "approx_tokens": len(lang) // 4},
        "json_tree": {"chars": len(as_json), "approx_tokens": len(as_json) // 4},
        "note": "approx_tokens = chars / 4, a rough rule of thumb; use a real tokenizer for real numbers.",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8004)
    args = ap.parse_args()
    server_base.serve(args.port, Path(__file__).parent,
                      json_routes={"/compare": compare, "/program": lambda p: {"program": program(p.get("mode", "declarative"))}},
                      sse_routes={"/stream": stream},
                      title="Topic 04 - OpenUI Lang streaming parser")
