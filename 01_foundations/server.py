"""Topic 01 - Foundations: the four generation modes, side by side.

The question this topic answers: *how much should the model decide?*

  static       the model picks ONE pre-built component and fills its props
  declarative  the model composes a tree, but only from our catalog
  open_ended   the model writes raw HTML/CSS/JS (shown in a sandboxed iframe)
  hybrid       a catalog tree with ONE sandboxed GeneratedView region

``scripted_agent`` stands in for the LLM: it returns exactly the JSON a
model would be prompted to return, so the demo runs offline and free.
Whatever the model returns, ``validate`` checks it before anything renders.

Run:  python server.py     then open http://localhost:8001
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.sales_data import ALLOWED_ACTIONS, SALES, custom_widget_html, money, reorder  # noqa: E402
from common.server_base import serve  # noqa: E402

MODES = ["static", "declarative", "open_ended", "hybrid"]

# The catalog: component name -> props it must have.
CATALOG = {
    "Heading": ["text"],
    "Text": ["text"],
    "MetricCard": ["label", "value"],
    "BarChart": ["data"],
    "Button": ["label", "action"],
    "Row": [],
    "Column": [],
    "GeneratedView": ["html"],  # only allowed in hybrid mode
}
STATIC_CHOICES = {"MetricCard", "BarChart"}  # static mode: pick one of these
MAX_HTML = 50_000


def _dashboard_children() -> list[dict]:
    return [
        {"type": "Heading", "props": {"text": f"Weekly sales · {SALES['week']}"}},
        {"type": "Row", "children": [
            {"type": "MetricCard", "props": {"label": "Revenue", "value": money(SALES["revenue"]), "delta": SALES["revenue_delta"]}},
            {"type": "MetricCard", "props": {"label": "Orders", "value": str(SALES["orders"]), "delta": SALES["orders_delta"]}},
        ]},
        {"type": "BarChart", "props": {"title": "Daily revenue", "data": SALES["daily"]}},
        {"type": "Button", "props": {"label": f"Reorder {SALES['top_product'].lower()}", "action": "reorder"}},
    ]


def scripted_agent(mode: str, broken: bool = False) -> dict:
    """What the model would answer to 'How did sales go this week?'."""
    if mode == "static":
        return {"component": "MetricCard",
                "props": {"label": "Revenue this week", "value": money(SALES["revenue"]), "delta": SALES["revenue_delta"]}}
    if mode == "declarative":
        children = _dashboard_children()
        if broken:  # a model hallucinating a component we never built
            children.append({"type": "PieChart", "props": {"slices": [1, 2, 3]}})
        return {"tree": {"type": "Column", "children": children}}
    if mode == "open_ended":
        return {"html": custom_widget_html()}
    if mode == "hybrid":
        children = _dashboard_children()
        children.insert(3, {"type": "GeneratedView", "props": {"html": custom_widget_html(), "height": 150}})
        return {"tree": {"type": "Column", "children": children}}
    raise ValueError(f"unknown mode {mode!r}; use one of {MODES}")


def _validate_tree(node, allow_generated: bool, path="tree") -> list[str]:
    errors = []
    kind = node.get("type")
    if kind not in CATALOG or (kind == "GeneratedView" and not allow_generated):
        return [f"{path}: '{kind}' is not in the catalog"]
    props = node.get("props", {})
    errors += [f"{path}: {kind} is missing prop '{p}'" for p in CATALOG[kind] if p not in props]
    if kind == "Button" and props.get("action") not in ALLOWED_ACTIONS:
        errors.append(f"{path}: action '{props.get('action')}' is not allowed")
    for i, child in enumerate(node.get("children", [])):
        errors += _validate_tree(child, allow_generated, f"{path}.children[{i}]")
    return errors


def validate(mode: str, reply: dict) -> list[str]:
    """The contract. Nothing renders unless this returns []."""
    if mode == "static":
        if reply.get("component") not in STATIC_CHOICES:
            return [f"static mode only allows {sorted(STATIC_CHOICES)}"]
        return [f"missing prop '{p}'" for p in CATALOG[reply["component"]] if p not in reply.get("props", {})]
    if mode == "open_ended":
        html = reply.get("html")
        if not isinstance(html, str) or not html.strip():
            return ["open-ended reply has no html"]
        return [f"html is larger than {MAX_HTML} characters"] if len(html) > MAX_HTML else []
    return _validate_tree(reply.get("tree", {}), allow_generated=(mode == "hybrid"))


# -- HTTP routes ---------------------------------------------------------------
def get_ui(params: dict) -> dict:
    mode = params.get("mode", "static")
    reply = scripted_agent(mode, broken=params.get("broken") == "1")
    return {"mode": mode, "reply": reply, "errors": validate(mode, reply)}


def post_action(params: dict) -> dict:
    name = params.get("name")
    if name not in ALLOWED_ACTIONS:  # a click is a *request*, not a permission
        return {"ok": False, "error": f"action '{name}' is not allowed"}
    return {"ok": True, "message": reorder()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8001)
    args = ap.parse_args()
    serve(args.port, Path(__file__).parent, {"/api/ui": get_ui, "/api/action": post_action},
          title="Topic 01 - Foundations (static / declarative / open-ended / hybrid)")
