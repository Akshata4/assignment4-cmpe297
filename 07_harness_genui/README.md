# 07 · Harness integration: the UI joins the agent loop

A coding-agent harness is a loop:

```text
messages → model → tool calls → run tools → tool results → model → … → final text
```

Here the model gets **UI tools**, one per mode:

| Mode | Tool the model calls |
|---|---|
| Static | `render_component(name, props)`: picks one pre-built component |
| Declarative | `render_ui(spec)`: a json-render style element map from the catalog |
| Open-ended | `render_html(html)`: raw HTML for a sandboxed surface |
| Hybrid | `render_ui(spec)` with a `GeneratedView` element |

Every UI tool validates its input and **returns errors to the model** instead of crashing. In declarative mode, the scripted model's first spec uses a `PieChart` that isn't in the catalog. It reads the error and fixes the spec on the next turn, which is the self-correction loop.

The same loop drives two surfaces: the **terminal** (default) and the **browser** (`--web`, over SSE).

## Run

```bash
python harness.py --mode declarative   # watch the error → retry → render in the terminal
python harness.py --mode static
python harness.py --web                # http://localhost:8007
python -m unittest -v
```

`ScriptedModel` stands in for the LLM so the demo is offline and free. Replacing it with a real model client doesn't change `run_agent()`.
