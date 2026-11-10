# 06 · MCP Apps: UI inside a host you do not control

With [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) (SEP-1865), an MCP server ships its UI to a host such as Claude, ChatGPT, VS Code or Goose:

1. `tools/list`: a tool's `_meta.ui.resourceUri` points to a `ui://` resource.
2. `tools/call`: returns `content` (text **for the model**) and `structuredContent` (data **for the UI**).
3. `resources/read`: returns HTML with mimeType `text/html;profile=mcp-app`.
4. The **host** mounts that HTML in a sandboxed iframe and talks to it with JSON-RPC over `postMessage`: `ui/initialize`, then `ui/notifications/tool-result`. The app can ask the host to call `tools/call`, and the **host decides** whether to allow it.

| Mode | Tool → resource |
|---|---|
| Static | `show_sales_card` → `ui://sales/card`: fixed HTML, numbers from `structuredContent` |
| Declarative | `show_sales_dashboard` → `ui://sales/dashboard`: a renderer app that draws a catalog spec |
| Open-ended | `show_custom_view` → `ui://sales/custom`: the resource itself is model-written HTML |
| Hybrid | `show_hybrid_dashboard` → the same renderer, with a **nested** sandboxed iframe for the generated part |

## Files

- `server.py`: a minimal MCP server (JSON-RPC over `POST /mcp`, no SDK) with tools, resources and the app-only `reorder_product` tool.
- `ui/card.html`, `ui/dashboard.html`: the app documents, each with a small `postMessage` bridge.
- `index.html`: a **mini host**. It discovers tools, calls them, mounts the resource and enforces an allow-list (`APP_MAY_CALL`) for tool calls coming from the app.

This basic version uses plain JSON-RPC over HTTP. A later step can swap in the official Python `mcp` (FastMCP) server and a real host such as Claude Desktop.

## Run

```bash
python server.py          # http://localhost:8006
python -m unittest -v
```

## What to show in the video

Follow the JSON-RPC log for one tool, from `tools/call` through `resources/read`, `ui/initialize` and the tool-result notification. Then click **Reorder lemons** inside the app to show the app → host → server tool call.
