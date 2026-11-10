"""Topic 03 - A2UI: structure and data travel separately.

A2UI (Google, https://a2ui.org) streams JSON *messages*, one per line:

  createSurface     open a surface (a UI region) and name its component catalog
  updateComponents  a FLAT list of components, joined by id (not a nested tree)
  updateDataModel   set data at a JSON Pointer path; components bind to paths
  deleteSurface     remove the surface

Because components bind to data paths (``{"path": "/revenue"}``), the agent
can change the numbers later without resending the layout. A Button's
``action`` carries a context resolved from the data model at click time.

The message shapes follow the A2UI v0.9 envelope, simplified for teaching,
with a custom catalog (our shared components). How each mode looks here:

  static       a fixed, pre-written surface template; the agent only sends DATA
  declarative  the agent composes the whole component list
  open_ended   a single GeneratedView component (a custom catalog entry) holding HTML
  hybrid       the composed list plus one GeneratedView

Run:  python server.py     then open http://localhost:8003
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import server_base  # noqa: E402
from common.sales_data import ALLOWED_ACTIONS, SALES, custom_widget_html, money, reorder  # noqa: E402

MODES = ["static", "declarative", "open_ended", "hybrid"]
VERSION = "v0.9"
CATALOG_ID = "cmpe297/sales-catalog"
CATALOG = {"Column", "Row", "Heading", "Text", "MetricCard", "BarChart", "Button", "TextField", "GeneratedView"}


def msg(kind: str, **body) -> dict:
    return {"version": VERSION, kind: {"surfaceId": "main", **body}}


def bind(path: str) -> dict:
    return {"path": path}


def initial_data() -> dict:
    return {
        "week": SALES["week"],
        "revenue": money(SALES["revenue"]),
        "revenueDelta": SALES["revenue_delta"],
        "orders": str(SALES["orders"]),
        "ordersDelta": SALES["orders_delta"],
        "daily": SALES["daily"],
        "product": SALES["top_product"],
        "crates": "60",
        "status": f"{SALES['stock_left']} crates in stock",
    }


# The pre-written template used by static mode: the agent never changes it.
STATIC_TEMPLATE = [
    {"id": "root", "component": "MetricCard", "label": "Revenue this week",
     "value": bind("/revenue"), "delta": bind("/revenueDelta")},
]


def composed_components(hybrid: bool) -> list[dict]:
    root_children = ["title", "metrics", "chart", "qty", "reorder", "status"]
    if hybrid:
        root_children.insert(3, "planner")
    comps = [
        {"id": "root", "component": "Column", "children": root_children},
        {"id": "title", "component": "Heading", "text": "Weekly sales"},
        {"id": "metrics", "component": "Row", "children": ["rev", "ord"]},
        {"id": "rev", "component": "MetricCard", "label": "Revenue", "value": bind("/revenue"), "delta": bind("/revenueDelta")},
        {"id": "ord", "component": "MetricCard", "label": "Orders", "value": bind("/orders"), "delta": bind("/ordersDelta")},
        {"id": "chart", "component": "BarChart", "title": "Daily revenue", "data": bind("/daily")},
        {"id": "qty", "component": "TextField", "label": "Crates to reorder", "value": bind("/crates")},
        {"id": "reorder", "component": "Button", "label": "Reorder",
         "action": {"event": {"name": "reorder", "context": {"product": bind("/product"), "crates": bind("/crates")}}}},
        {"id": "status", "component": "Text", "text": bind("/status")},
    ]
    if hybrid:
        comps.append({"id": "planner", "component": "GeneratedView", "html": custom_widget_html(), "height": 150})
    return comps


def surface_messages(mode: str):
    """The message stream an A2UI agent would emit for this mode."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    yield msg("createSurface", catalogId=CATALOG_ID)
    if mode == "static":
        components = STATIC_TEMPLATE
    elif mode == "open_ended":
        components = [{"id": "root", "component": "GeneratedView", "html": custom_widget_html(), "height": 200}]
    else:
        components = composed_components(hybrid=(mode == "hybrid"))
    for err in validate(components):
        raise ValueError(err)
    yield msg("updateComponents", components=components)
    yield msg("updateDataModel", path="/", value=initial_data())
    # Later, ONLY the data changes - the layout is not resent.
    if server_base.DELAY:
        time.sleep(server_base.DELAY * 6)
    yield msg("updateDataModel", path="/revenue", value=money(SALES["revenue"] + 850))
    yield msg("updateDataModel", path="/revenueDelta", value="+14% (live)")


def validate(components: list[dict]) -> list[str]:
    ids = {c["id"] for c in components}
    errors = [f"{c['id']}: '{c['component']}' not in catalog" for c in components if c["component"] not in CATALOG]
    for c in components:
        errors += [f"{c['id']}: unknown child '{ch}'" for ch in c.get("children", []) if ch not in ids]
    if "root" not in ids:
        errors.append("no component with id 'root'")
    return errors


def handle_action(params: dict) -> dict:
    """Client -> server: the ``action`` message a Button raises."""
    action = params.get("action", {})
    if action.get("name") not in ALLOWED_ACTIONS:
        return {"messages": [msg("updateDataModel", path="/status", value=f"refused: {action.get('name')}")]}
    crates = int(action.get("context", {}).get("crates") or 0)
    return {"messages": [msg("updateDataModel", path="/status", value=reorder(crates))]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8003)
    args = ap.parse_args()
    server_base.serve(args.port, Path(__file__).parent,
                      json_routes={"/action": handle_action},
                      sse_routes={"/a2ui": lambda p: surface_messages(p.get("mode", "declarative"))},
                      title="Topic 03 - A2UI surfaces + data model")
