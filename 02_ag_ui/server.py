"""Topic 02 - AG-UI: the event protocol between an agent and your page.

The page sends one ``RunAgentInput`` (threadId, runId, messages, ...) and
gets back one stream of typed events over Server-Sent Events:

  RUN_STARTED
  TEXT_MESSAGE_START / TEXT_MESSAGE_CONTENT / TEXT_MESSAGE_END   chat text
  TOOL_CALL_START / TOOL_CALL_ARGS / TOOL_CALL_END               a tool call, args streamed
  STATE_SNAPSHOT / STATE_DELTA (JSON Patch)                      shared state
  RUN_FINISHED  (or RUN_ERROR)

How each generation mode travels over AG-UI:

  static       a TOOL_CALL to ``render_metric_card``; the page owns that component
  declarative  STATE_SNAPSHOT carries a catalog tree, STATE_DELTA patches update it
  open_ended   a TOOL_CALL to ``render_html`` whose args stream in as chunks
  hybrid       STATE_SNAPSHOT with a catalog tree that includes a GeneratedView

A user click starts a *new run* with ``forwardedProps.action``. The agent is
scripted (no LLM needed); event names follow the AG-UI spec.

Run:  python server.py     then open http://localhost:8002
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import server_base  # noqa: E402
from common.sales_data import ALLOWED_ACTIONS, SALES, custom_widget_html, money, reorder  # noqa: E402

MODES = ["static", "declarative", "open_ended", "hybrid"]


def ev(type_: str, **fields) -> dict:
    return {"type": type_, "timestamp": int(time.time() * 1000), **fields}


def pause():
    if server_base.DELAY:
        time.sleep(server_base.DELAY)


def text_message(text: str):
    mid = f"msg_{uuid.uuid4().hex[:8]}"
    yield ev("TEXT_MESSAGE_START", messageId=mid, role="assistant")
    for word in text.split(" "):  # stream word by word, like model tokens
        yield ev("TEXT_MESSAGE_CONTENT", messageId=mid, delta=word + " ")
    yield ev("TEXT_MESSAGE_END", messageId=mid)


def tool_call(name: str, args: dict, chunk: int = 400):
    tid = f"call_{uuid.uuid4().hex[:8]}"
    yield ev("TOOL_CALL_START", toolCallId=tid, toolCallName=name)
    encoded = json.dumps(args)
    for i in range(0, len(encoded), chunk):  # args arrive as partial JSON
        pause()
        yield ev("TOOL_CALL_ARGS", toolCallId=tid, delta=encoded[i:i + chunk])
    yield ev("TOOL_CALL_END", toolCallId=tid)


def dashboard_state(hybrid: bool) -> dict:
    children = [
        {"type": "Heading", "props": {"text": f"Weekly sales · {SALES['week']}"}},
        {"type": "Row", "children": [
            {"type": "MetricCard", "props": {"label": "Revenue", "value": "loading…"}},
            {"type": "MetricCard", "props": {"label": "Orders", "value": "loading…"}},
        ]},
        {"type": "BarChart", "props": {"title": "Daily revenue", "data": []}},
        {"type": "Text", "props": {"text": f"Stock: {SALES['stock_left']} crates of {SALES['top_product']}"}},
        {"type": "Button", "props": {"label": "Reorder lemons", "action": "reorder"}},
    ]
    if hybrid:
        children.insert(3, {"type": "GeneratedView", "props": {"html": custom_widget_html(), "height": 150}})
    return {"dashboard": {"type": "Column", "children": children}}


# JSON Patch paths into the tree above. A real agent emits these as its tools finish.
DATA_PATCHES = [
    [{"op": "replace", "path": "/dashboard/children/1/children/0/props/value", "value": money(SALES["revenue"])},
     {"op": "add", "path": "/dashboard/children/1/children/0/props/delta", "value": SALES["revenue_delta"]}],
    [{"op": "replace", "path": "/dashboard/children/1/children/1/props/value", "value": str(SALES["orders"])},
     {"op": "add", "path": "/dashboard/children/1/children/1/props/delta", "value": SALES["orders_delta"]}],
    [{"op": "replace", "path": "/dashboard/children/2/props/data", "value": SALES["daily"]}],
]


def run_agent(run_input: dict):
    """One AG-UI run. ``run_input`` is the RunAgentInput the page POSTed."""
    thread_id = run_input.get("threadId") or "thread_1"
    run_id = run_input.get("runId") or f"run_{uuid.uuid4().hex[:8]}"
    props = run_input.get("forwardedProps") or {}
    mode, action = props.get("mode", "static"), props.get("action")

    yield ev("RUN_STARTED", threadId=thread_id, runId=run_id)
    if mode not in MODES:
        yield ev("RUN_ERROR", message=f"unknown mode {mode!r}")
        return

    if action:  # the second half of the loop: the user clicked something
        if action not in ALLOWED_ACTIONS:
            yield ev("RUN_ERROR", message=f"action {action!r} is not allowed")
            return
        yield from text_message(reorder())
        if mode in ("declarative", "hybrid"):
            stock_idx = 4 if mode == "hybrid" else 3
            yield ev("STATE_DELTA", delta=[{"op": "replace", "path": f"/dashboard/children/{stock_idx}/props/text",
                                            "value": f"Stock: {SALES['stock_left']} crates + 60 on order"}])
    else:
        yield from text_message("Here is this week's sales summary.")
        if mode == "static":
            yield from tool_call("render_metric_card",
                                 {"label": "Revenue this week", "value": money(SALES["revenue"]), "delta": SALES["revenue_delta"]})
        elif mode == "open_ended":
            yield from tool_call("render_html", {"html": custom_widget_html()}, chunk=120)
        else:
            yield ev("STATE_SNAPSHOT", snapshot=dashboard_state(hybrid=(mode == "hybrid")))
            for patch in DATA_PATCHES:  # data arrives after the layout
                pause()
                yield ev("STATE_DELTA", delta=patch)
    yield ev("RUN_FINISHED", threadId=thread_id, runId=run_id)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8002)
    args = ap.parse_args()
    server_base.serve(args.port, Path(__file__).parent, sse_routes={"/agent": run_agent},
                      title="Topic 02 - AG-UI event stream")
