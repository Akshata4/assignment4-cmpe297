"""The json-render style spec, its catalog, validation and patch stream.

json-render (Vercel) uses a FLAT element map plus state:

    {"root": "main",
     "elements": {"main": {"type": "Column", "props": {}, "children": ["title", ...]},
                  "title": {"type": "Heading", "props": {"text": "..."}}, ...},
     "state": {"revenue": "$48,200", ...}}

Props may read state with ``{"$state": "/revenue"}``. The spec streams as
RFC 6902 JSON Patch operations, so the page can render while it arrives.
The catalog is the contract: it is used to validate the spec AND to write
the system prompt, so the model and the renderer agree.

This mirrors the library's ideas in plain Python; the real library
(@json-render/core) does the same with Zod schemas.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.json_patch import get_pointer  # noqa: E402
from common.sales_data import ALLOWED_ACTIONS, SALES, custom_widget_html, money  # noqa: E402

MODES = ["static", "declarative", "open_ended", "hybrid"]

# type -> {prop: (python type, required?)}
CATALOG = {
    "Column": {},
    "Row": {},
    "Heading": {"text": (str, True)},
    "Text": {"text": (str, True)},
    "MetricCard": {"label": (str, True), "value": (str, True), "delta": (str, False)},
    "BarChart": {"title": (str, False), "data": (list, True)},
    "Button": {"label": (str, True), "action": (dict, True)},
    "GeneratedView": {"html": (str, True), "height": (int, False)},
}
CONTAINERS = {"Column", "Row"}


def catalog_prompt() -> str:
    """The catalog rendered as instructions for a model's system prompt."""
    lines = ["Reply with a JSON spec {root, elements, state}. Allowed element types:"]
    for name, props in CATALOG.items():
        sig = ", ".join(f"{p}{'' if req else '?'}: {t.__name__}" for p, (t, req) in props.items())
        lines.append(f"- {name}({sig}){'  [has children]' if name in CONTAINERS else ''}")
    lines.append('Props may read state with {"$state": "/path"}. Button.action = {"name": ..., "params": {...}}.')
    return "\n".join(lines)


def build_spec(mode: str) -> dict:
    state = {"revenue": money(SALES["revenue"]), "orders": str(SALES["orders"]),
             "daily": SALES["daily"], "status": f"{SALES['stock_left']} crates of lemons in stock"}
    if mode == "static":
        return {"root": "card", "state": state, "elements": {
            "card": {"type": "MetricCard", "props": {"label": "Revenue this week", "value": {"$state": "/revenue"},
                                                     "delta": SALES["revenue_delta"]}}}}
    if mode == "open_ended":
        return {"root": "view", "state": {}, "elements": {
            "view": {"type": "GeneratedView", "props": {"html": custom_widget_html(), "height": 200}}}}
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    children = ["title", "metrics", "chart", "status", "reorder"]
    elements = {
        "main": {"type": "Column", "props": {}, "children": children},
        "title": {"type": "Heading", "props": {"text": f"Weekly sales · {SALES['week']}"}},
        "metrics": {"type": "Row", "props": {}, "children": ["revenue", "orders"]},
        "revenue": {"type": "MetricCard", "props": {"label": "Revenue", "value": {"$state": "/revenue"}, "delta": SALES["revenue_delta"]}},
        "orders": {"type": "MetricCard", "props": {"label": "Orders", "value": {"$state": "/orders"}, "delta": SALES["orders_delta"]}},
        "chart": {"type": "BarChart", "props": {"title": "Daily revenue", "data": {"$state": "/daily"}}},
        "status": {"type": "Text", "props": {"text": {"$state": "/status"}}},
        "reorder": {"type": "Button", "props": {"label": "Reorder lemons", "action": {"name": "reorder", "params": {"crates": 60}}}},
    }
    if mode == "hybrid":
        children.insert(3, "planner")
        elements["planner"] = {"type": "GeneratedView", "props": {"html": custom_widget_html(), "height": 150}}
    return {"root": "main", "elements": elements, "state": state}


def validate(spec: dict) -> list[str]:
    errors = []
    elements, state = spec.get("elements", {}), spec.get("state", {})
    if spec.get("root") not in elements:
        errors.append(f"root '{spec.get('root')}' is not an element")
    for eid, el in elements.items():
        kind = el.get("type")
        if kind not in CATALOG:
            errors.append(f"{eid}: type '{kind}' is not in the catalog")
            continue
        props = el.get("props", {})
        for name, (typ, required) in CATALOG[kind].items():
            if name not in props:
                if required:
                    errors.append(f"{eid}: missing required prop '{name}'")
                continue
            value = props[name]
            if isinstance(value, dict) and "$state" in value:
                try:
                    value = get_pointer(state, value["$state"])
                except (KeyError, IndexError):
                    errors.append(f"{eid}.{name}: state path {value['$state']} does not exist")
                    continue
            if not isinstance(value, typ):
                errors.append(f"{eid}.{name}: expected {typ.__name__}")
        errors += [f"{eid}: unknown prop '{p}'" for p in props if p not in CATALOG[kind]]
        if kind == "Button" and props.get("action", {}).get("name") not in ALLOWED_ACTIONS:
            errors.append(f"{eid}: action is not allowed")
        for child in el.get("children", []):
            if child not in elements:
                errors.append(f"{eid}: child '{child}' does not exist")
    return errors


def to_patches(spec: dict) -> list[dict]:
    """How the spec streams: root and state first, then one element per patch."""
    ops = [{"op": "add", "path": "/root", "value": spec["root"]},
           {"op": "add", "path": "/state", "value": spec["state"]},
           {"op": "add", "path": "/elements", "value": {}}]
    ops += [{"op": "add", "path": f"/elements/{eid}", "value": el} for eid, el in spec["elements"].items()]
    return ops
