# 02 · AG-UI: keeping the agent and the page in sync

[AG-UI](https://docs.ag-ui.com) is the **transport** between an agent and a frontend you own. The page sends one `RunAgentInput`, and the agent streams back typed events over Server-Sent Events:

```text
RUN_STARTED
TEXT_MESSAGE_START → TEXT_MESSAGE_CONTENT… → TEXT_MESSAGE_END     streamed chat text
TOOL_CALL_START → TOOL_CALL_ARGS… → TOOL_CALL_END                 a tool call, args as partial JSON
STATE_SNAPSHOT, STATE_DELTA (JSON Patch)                          shared state
RUN_FINISHED  (or RUN_ERROR)
```

| Mode | How it travels over AG-UI |
|---|---|
| Static | A `render_metric_card` tool call. The **frontend** owns the component for that tool name. |
| Declarative | `STATE_SNAPSHOT` sends the layout with "loading…" values, then `STATE_DELTA` patches fill in the data. |
| Open-ended | A `render_html` tool call whose args (the HTML) stream in chunks, then render in a sandbox. |
| Hybrid | A state snapshot whose tree contains a `GeneratedView`. |

Clicking **Reorder lemons** starts a **new run** with `forwardedProps.action`. The agent answers with text and a `STATE_DELTA` that updates the stock line.

## Files

- `server.py`: `run_agent()` yields the event stream (scripted agent, AG-UI event names).
- `index.html`: reads the stream with `fetch` (a POST, so not `EventSource`), applies patches with `../common/json_patch.js`, and renders state.
- `test_server.py`: checks event order, that tool args reassemble, and that deltas build the dashboard.

## Run

```bash
python server.py          # http://localhost:8002
python -m unittest -v
```

## What to show in the video

Show the event log on the left for each mode. In declarative mode, point out that the layout appears first and the numbers arrive later as JSON Patch. Then click the button to show the second run.
