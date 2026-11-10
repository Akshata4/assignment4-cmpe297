"""Topic 06 - MCP Apps: ship the UI to a host you do not control.

MCP Apps (SEP-1865, https://github.com/modelcontextprotocol/ext-apps) lets a
tool result point at a UI *resource*:

  1. ``tools/list``     each tool's ``_meta.ui.resourceUri`` names a ``ui://`` resource
  2. ``tools/call``     returns ``content`` (text for the model) and
                        ``structuredContent`` (data for the UI)
  3. ``resources/read`` returns the HTML (mimeType ``text/html;profile=mcp-app``)
  4. the HOST mounts that HTML in a sandboxed iframe and talks to it over
     ``postMessage`` JSON-RPC (``ui/initialize``, ``ui/notifications/tool-result``,
     and ``tools/call`` requests from the app that the host may allow or refuse)

Modes:
  static       show_sales_card        -> ui://sales/card       fixed HTML, data from the tool result
  declarative  show_sales_dashboard   -> ui://sales/dashboard  a renderer app that draws a catalog spec
  open_ended   show_custom_view       -> ui://sales/custom     the resource IS model-written HTML
  hybrid       show_hybrid_dashboard  -> ui://sales/dashboard  spec + a nested sandboxed GeneratedView

For the basic version this is plain JSON-RPC over ``POST /mcp`` (no SDK).
A later step can swap in the official ``mcp`` FastMCP server and a real host.

Run:  python server.py     then open http://localhost:8006  (index.html is a mini host)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.sales_data import SALES, custom_widget_html, money, reorder  # noqa: E402
from common.server_base import serve  # noqa: E402

HERE = Path(__file__).resolve().parent
MIME = "text/html;profile=mcp-app"


def dashboard_spec(hybrid: bool) -> dict:
    children = [
        {"type": "Heading", "props": {"text": f"Weekly sales · {SALES['week']}"}},
        {"type": "Row", "children": [
            {"type": "MetricCard", "props": {"label": "Revenue", "value": money(SALES["revenue"]), "delta": SALES["revenue_delta"]}},
            {"type": "MetricCard", "props": {"label": "Orders", "value": str(SALES["orders"]), "delta": SALES["orders_delta"]}},
        ]},
        {"type": "BarChart", "props": {"title": "Daily revenue", "data": SALES["daily"]}},
        {"type": "Button", "props": {"label": "Reorder lemons", "tool": "reorder_product", "arguments": {"crates": 60}}},
    ]
    if hybrid:
        children.insert(3, {"type": "GeneratedView", "props": {"html": custom_widget_html()}})
    return {"type": "Column", "children": children}


RESOURCES = {
    "ui://sales/card": {"name": "Sales card", "text": lambda: (HERE / "ui" / "card.html").read_text()},
    "ui://sales/dashboard": {"name": "Sales dashboard renderer", "text": lambda: (HERE / "ui" / "dashboard.html").read_text()},
    "ui://sales/custom": {"name": "Model-written view", "text": custom_widget_html},
}

TOOLS = {
    "show_sales_card": {
        "description": "Show this week's revenue as a card.",
        "resourceUri": "ui://sales/card",
        "run": lambda args: ("Revenue this week is " + money(SALES["revenue"]),
                             {"label": "Revenue this week", "value": money(SALES["revenue"]), "delta": SALES["revenue_delta"]}),
    },
    "show_sales_dashboard": {
        "description": "Show the weekly sales dashboard.",
        "resourceUri": "ui://sales/dashboard",
        "run": lambda args: ("Dashboard shown.", {"spec": dashboard_spec(hybrid=False)}),
    },
    "show_custom_view": {
        "description": "Show a custom interactive reorder planner.",
        "resourceUri": "ui://sales/custom",
        "run": lambda args: ("Planner shown.", {}),
    },
    "show_hybrid_dashboard": {
        "description": "Dashboard plus a custom planner region.",
        "resourceUri": "ui://sales/dashboard",
        "run": lambda args: ("Hybrid dashboard shown.", {"spec": dashboard_spec(hybrid=True)}),
    },
    "reorder_product": {  # called by the APP (through the host), not shown as a view
        "description": "Reorder the top product.",
        "resourceUri": None,
        "run": lambda args: (reorder(int(args.get("crates", 60))), {"ok": True}),
    },
}


def handle_rpc(req: dict) -> dict:
    """One JSON-RPC 2.0 request -> response."""
    rid, method, params = req.get("id"), req.get("method"), req.get("params") or {}

    def ok(result):
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({"protocolVersion": "2025-06-18", "serverInfo": {"name": "sales-mcp-app", "version": "0.1.0"},
                   "capabilities": {"tools": {}, "resources": {}}})
    if method == "tools/list":
        tools = []
        for name, t in TOOLS.items():
            tool = {"name": name, "description": t["description"], "inputSchema": {"type": "object"}}
            if t["resourceUri"]:
                tool["_meta"] = {"ui": {"resourceUri": t["resourceUri"]}}
            tools.append(tool)
        return ok({"tools": tools})
    if method == "tools/call":
        tool = TOOLS.get(params.get("name"))
        if not tool:
            return err(-32602, f"unknown tool {params.get('name')!r}")
        text, data = tool["run"](params.get("arguments") or {})
        result = {"content": [{"type": "text", "text": text}], "structuredContent": data}
        if tool["resourceUri"]:
            result["_meta"] = {"ui": {"resourceUri": tool["resourceUri"]}}
        return ok(result)
    if method == "resources/list":
        return ok({"resources": [{"uri": u, "name": r["name"], "mimeType": MIME} for u, r in RESOURCES.items()]})
    if method == "resources/read":
        res = RESOURCES.get(params.get("uri"))
        if not res:
            return err(-32602, f"unknown resource {params.get('uri')!r}")
        return ok({"contents": [{"uri": params["uri"], "mimeType": MIME, "text": res["text"](),
                                 "_meta": {"ui": {"csp": {"connectDomains": [], "resourceDomains": []}}}}]})
    return err(-32601, f"method not found: {method}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8006)
    args = ap.parse_args()
    serve(args.port, HERE, json_routes={"/mcp": handle_rpc}, title="Topic 06 - MCP Apps server + mini host")
