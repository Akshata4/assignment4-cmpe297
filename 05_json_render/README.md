# 05 · json-render: one catalog, several renderers

[json-render](https://github.com/vercel-labs/json-render) (Vercel) uses a **flat element map** plus state:

```json
{ "root": "main",
  "elements": { "main": {"type": "Column", "props": {}, "children": ["title", "metrics"]},
                "revenue": {"type": "MetricCard", "props": {"label": "Revenue", "value": {"$state": "/revenue"}}} },
  "state": { "revenue": "$48,200" } }
```

- **The catalog is the contract.** In `spec.py`, `CATALOG` drives both `validate()` (types, required props, unknown props, children and state paths) and `catalog_prompt()`, the text you would put in the model's system prompt.
- **Streaming:** the spec arrives as RFC 6902 JSON Patch operations, one per event. Missing children render as placeholders.
- **Actions:** a Button's `{"name": "reorder", "params": {...}}` is POSTed to `/action`, which returns patches against `/state`.
- **Two render targets:** the browser (`index.html`) and the terminal (`render_terminal.py`) draw the **same spec**.

| Mode | Spec |
|---|---|
| Static | One `MetricCard` element |
| Declarative | The full dashboard element map |
| Open-ended | One `GeneratedView` element (HTML) |
| Hybrid | The dashboard plus a `GeneratedView`. The terminal target shows its limit: it can't run HTML |

These are the library's ideas in plain Python and JS. The real `@json-render/core` uses Zod schemas.

## Run

```bash
python server.py                              # http://localhost:8005
python render_terminal.py --mode declarative  # same spec in the terminal
python render_terminal.py --mode hybrid
python -m unittest -v
```
