"""Topic 07 - Harness integration: the UI becomes a tool in the agent loop.

A coding-agent harness is a loop:

    messages -> model -> (tool calls -> run tools -> tool results -> model)* -> final text

Here the model gets UI tools, one per generation mode:

  static       render_component(name, props)   pick one pre-built component
  declarative  render_ui(spec)                 a json-render style spec from the catalog
  open_ended   render_html(html)               raw HTML for a sandboxed surface
  hybrid       render_ui(spec) with a GeneratedView element

Every UI tool validates its input and returns errors TO THE MODEL, so the
model can fix its own mistake on the next turn. The scripted model below
does exactly that in declarative mode: its first spec uses a PieChart that
is not in the catalog, it reads the error, and it retries.

    python harness.py --mode declarative          terminal surface
    python harness.py --web                       browser surface on :8007

``ScriptedModel`` stands in for an LLM so this runs offline and free;
swap it for a real model client later - the loop does not change.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import server_base  # noqa: E402
from common.sales_data import SALES, custom_widget_html, money  # noqa: E402

MODES = ["static", "declarative", "open_ended", "hybrid"]
CATALOG = {"Column": [], "Row": [], "Heading": ["text"], "Text": ["text"],
           "MetricCard": ["label", "value"], "BarChart": ["data"], "GeneratedView": ["html"]}
STATIC_COMPONENTS = {"MetricCard", "BarChart"}


# --------------------------------------------------------------------------- tools
def get_sales_data(_args: dict) -> dict:
    return SALES


def validate_spec(spec: dict, allow_generated: bool) -> list[str]:
    errors, elements = [], spec.get("elements", {})
    if spec.get("root") not in elements:
        errors.append("root must name an element")
    for eid, el in elements.items():
        kind = el.get("type")
        if kind not in CATALOG or (kind == "GeneratedView" and not allow_generated):
            errors.append(f"{eid}: '{kind}' is not in the catalog {sorted(CATALOG)}")
            continue
        errors += [f"{eid}: missing prop '{p}'" for p in CATALOG[kind] if p not in el.get("props", {})]
        errors += [f"{eid}: child '{c}' does not exist" for c in el.get("children", []) if c not in elements]
    return errors


def make_tools(surface, mode: str) -> dict:
    """The tools the model may call. ``surface(kind, payload)`` draws the UI."""
    def render_component(args):
        if args.get("name") not in STATIC_COMPONENTS:
            return {"ok": False, "error": f"name must be one of {sorted(STATIC_COMPONENTS)}"}
        surface("component", args)
        return {"ok": True}

    def render_ui(args):
        errors = validate_spec(args.get("spec", {}), allow_generated=(mode == "hybrid"))
        if errors:
            return {"ok": False, "errors": errors}  # goes back to the model
        surface("spec", args["spec"])
        return {"ok": True}

    def render_html(args):
        html = args.get("html", "")
        if not html.strip() or len(html) > 50_000:
            return {"ok": False, "error": "html must be non-empty and under 50k characters"}
        surface("html", {"html": html})
        return {"ok": True}

    return {"get_sales_data": get_sales_data, "render_component": render_component,
            "render_ui": render_ui, "render_html": render_html}


# --------------------------------------------------------------------------- model
def _spec(data: dict, hybrid: bool, mistake: bool) -> dict:
    children = ["title", "metrics", "chart"]
    elements = {
        "main": {"type": "Column", "children": children},
        "title": {"type": "Heading", "props": {"text": f"Weekly sales · {data['week']}"}},
        "metrics": {"type": "Row", "children": ["rev", "ord"]},
        "rev": {"type": "MetricCard", "props": {"label": "Revenue", "value": money(data["revenue"]), "delta": data["revenue_delta"]}},
        "ord": {"type": "MetricCard", "props": {"label": "Orders", "value": str(data["orders"]), "delta": data["orders_delta"]}},
        "chart": {"type": "BarChart", "props": {"title": "Daily revenue", "data": data["daily"]}},
    }
    if mistake:  # the kind of thing a real model gets wrong
        elements["chart"] = {"type": "PieChart", "props": {"slices": data["daily"]}}
    if hybrid:
        children.append("planner")
        elements["planner"] = {"type": "GeneratedView", "props": {"html": custom_widget_html()}}
    return {"root": "main", "elements": elements}


class ScriptedModel:
    """Deterministic stand-in for an LLM. Reads the transcript, returns the next turn."""

    def __init__(self, mode: str):
        self.mode = mode

    def next(self, messages: list[dict]) -> dict:
        tool_results = [m for m in messages if m["role"] == "tool"]
        if not tool_results:
            return {"tool_calls": [{"name": "get_sales_data", "arguments": {}}]}
        last = json.loads(tool_results[-1]["content"])
        if last.get("ok") is True:
            return {"text": f"Done - I rendered the sales view ({self.mode} mode)."}
        if "errors" in last or "error" in last:  # read the error and fix the spec
            return {"tool_calls": [{"name": "render_ui", "arguments": {"spec": _spec(SALES, self.mode == "hybrid", mistake=False)}}]}
        data = last  # the result of get_sales_data
        if self.mode == "static":
            call = {"name": "render_component", "arguments": {"name": "MetricCard", "props": {
                "label": "Revenue this week", "value": money(data["revenue"]), "delta": data["revenue_delta"]}}}
        elif self.mode == "open_ended":
            call = {"name": "render_html", "arguments": {"html": custom_widget_html()}}
        else:
            call = {"name": "render_ui", "arguments": {"spec": _spec(data, self.mode == "hybrid", mistake=(self.mode == "declarative"))}}
        return {"tool_calls": [call]}


# --------------------------------------------------------------------------- loop
def run_agent(prompt: str, mode: str, surface, trace=print, max_turns: int = 8) -> str:
    model, tools = ScriptedModel(mode), make_tools(surface, mode)
    messages = [{"role": "system", "content": "You are a sales assistant. Answer with UI using the render tools."},
                {"role": "user", "content": prompt}]
    for turn in range(1, max_turns + 1):
        reply = model.next(messages)
        if "text" in reply:
            trace(f"[turn {turn}] model: {reply['text']}")
            return reply["text"]
        messages.append({"role": "assistant", "tool_calls": reply["tool_calls"]})
        for call in reply["tool_calls"]:
            trace(f"[turn {turn}] tool call: {call['name']}({json.dumps(call['arguments'])[:70]}…)")
            result = tools[call["name"]](call["arguments"])
            brief = {k: v for k, v in result.items() if k in ("ok", "error", "errors")} or "sales data"
            trace(f"[turn {turn}] tool result -> model: {brief}")
            messages.append({"role": "tool", "name": call["name"], "content": json.dumps(result)})
    return "stopped: too many turns"


# --------------------------------------------------------------------------- terminal surface
def terminal_surface(kind: str, payload: dict) -> None:
    print("\n┌─ UI surface " + "─" * 40)
    if kind == "component":
        p = payload["props"]
        print(f"│ [{payload['name']}] {p['label']}: {p['value']} {p.get('delta', '')}")
    elif kind == "html":
        print(f"│ [sandboxed HTML, {len(payload['html'])} chars] - run with --web to see it")
    else:
        def draw(eid, depth):
            el = payload["elements"][eid]
            p, pad = el.get("props", {}), "│ " + "  " * depth
            if el["type"] == "Heading":
                print(pad + p["text"].upper())
            elif el["type"] == "MetricCard":
                print(pad + f"[{p['label']}: {p['value']} {p.get('delta', '')}]")
            elif el["type"] == "BarChart":
                top = max(d["value"] for d in p["data"])
                for d in p["data"]:
                    print(pad + f"{d['label']:>4} {'█' * round(20 * d['value'] / top)}")
            elif el["type"] == "GeneratedView":
                print(pad + "[GeneratedView - sandboxed HTML, see --web]")
            for c in el.get("children", []):
                draw(c, depth + 1)
        draw(payload["root"], 0)
    print("└" + "─" * 53 + "\n")


# --------------------------------------------------------------------------- web surface
def web_run(params: dict):
    """SSE: every trace line and every UI render, as the loop runs."""
    events = []
    run_agent(params.get("prompt", "How did sales go this week?"), params.get("mode", "declarative"),
              surface=lambda kind, payload: events.append({"type": "ui", "kind": kind, "payload": payload}),
              trace=lambda line: events.append({"type": "trace", "text": line}))
    for e in events:
        if server_base.DELAY:
            time.sleep(server_base.DELAY * 2)
        yield e
    yield {"type": "done"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=MODES, default="declarative")
    ap.add_argument("--prompt", default="How did sales go this week?")
    ap.add_argument("--web", action="store_true", help="serve the browser surface instead")
    ap.add_argument("--port", type=int, default=8007)
    args = ap.parse_args()
    if args.web:
        server_base.serve(args.port, Path(__file__).parent, sse_routes={"/run": web_run},
                          title="Topic 07 - harness with a browser UI surface")
    else:
        print(f"user: {args.prompt}   (mode: {args.mode})\n")
        run_agent(args.prompt, args.mode, terminal_surface)
