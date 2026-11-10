# 01 · Foundations: how much should the model decide?

**Question:** when an agent answers with UI instead of text, how much control does the model get?

| Mode | Agent reply (see `scripted_agent` in `server.py`) | How the page renders it |
|---|---|---|
| Static | `{"component": "MetricCard", "props": {...}}` | Looks up that one pre-built component |
| Declarative | `{"tree": {"type": "Column", "children": [...]}}` | `renderNode` walks the tree, catalog components only |
| Open-ended | `{"html": "<!doctype html>..."}` | `GeneratedView`, a sandboxed iframe |
| Hybrid | A catalog tree containing one `GeneratedView` | Both of the above |

## Files

- `server.py`: the scripted agent, the **catalog** and **`validate()`**, the contract that every reply must pass before it renders, plus the action allow-list.
- `index.html`: the renderer. It shows the raw agent JSON on the left and the rendered UI on the right.
- `test_server.py`: offline tests.
- Shared code: `../common/components.js` (the catalog and the sandbox).

## Run

```bash
python server.py          # http://localhost:8001
python -m unittest -v     # tests
```

## What to show in the video

1. **Static:** the agent can only pick `MetricCard` or `BarChart`.
2. **Declarative:** the same data now arrives as a full dashboard tree. Walk through `renderNode`.
3. **Declarative (invalid reply):** the model "hallucinates" a `PieChart`. `validate()` rejects it and nothing renders.
4. **Open-ended:** model-written HTML with its own `<script>` runs inside `sandbox="allow-scripts"` with a CSP that blocks the network. Explain why there's no `allow-same-origin`.
5. **Hybrid:** catalog components everywhere, plus one sandboxed region (dashed border).
6. Click **Reorder lemons**. The click sends a named action, and the server checks it against `ALLOWED_ACTIONS`.
