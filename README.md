# CMPE 297 · Assignment 4 · Generative UI (GenUI)

Progressive codelabs for **A2UI, AG-UI, MCP Apps, json-render, OpenUI and harness integration**.
Each topic shows all four generation modes: **static, declarative, open-ended and mixed (hybrid)**.

Reference course: [dlmastery/simple-coding-harness · genui](https://github.com/dlmastery/simple-coding-harness/tree/main/genui)

## Videos

| # | Assignment topic | Code | Video |
|---|---|---|---|
| 1 | Foundations: static, declarative, open-ended and hybrid UX | [`01_foundations`](01_foundations/) | _Video link coming soon_ |
| 2 | AG-UI (agent ⇄ UI event protocol) | [`02_ag_ui`](02_ag_ui/) | _Video link coming soon_ |
| 3 | A2UI (Google's declarative UI protocol) | [`03_a2ui`](03_a2ui/) | _Video link coming soon_ |
| 4 | OpenUI (OpenUI Lang) | [`04_openui_lang`](04_openui_lang/) | _Video link coming soon_ |
| 5 | json-render | [`05_json_render`](05_json_render/) | _Video link coming soon_ |
| 6 | MCP Apps | [`06_mcp_apps`](06_mcp_apps/) | _Video link coming soon_ |
| 7 | Harness integration | [`07_harness_genui`](07_harness_genui/) | _Video link coming soon_ |

## The four modes (used in every topic)

| Mode | What the agent emits | Who decides the layout |
|---|---|---|
| **Static** | A pre-built component's name and its props | You, ahead of time |
| **Declarative** | A layout built only from a catalog of allowed components | The agent, within your catalog |
| **Open-ended** | Raw HTML/CSS/JS, rendered in a sandboxed iframe | The agent alone |
| **Hybrid (mixed)** | Catalog components plus one sandboxed generated region | Both |

Every topic uses the same example, a small shop's weekly sales dashboard (`common/sales_data.py`), so you can compare formats and protocols side by side.

## Run it

You need **Python 3.10+** and a modern browser. There is nothing to install: the basic code uses only the Python standard library and plain HTML/JS.

```bash
python run_tests.py            # offline tests for all 7 topics
python run_tests.py 03         # tests for one topic

cd 01_foundations && python server.py     # then open http://localhost:8001
```

| Topic | Command (from the topic folder) | URL |
|---|---|---|
| 01 | `python server.py` | http://localhost:8001 |
| 02 | `python server.py` | http://localhost:8002 |
| 03 | `python server.py` | http://localhost:8003 |
| 04 | `python server.py` | http://localhost:8004 |
| 05 | `python server.py` · `python render_terminal.py --mode declarative` | http://localhost:8005 |
| 06 | `python server.py` | http://localhost:8006 |
| 07 | `python harness.py --mode declarative` · `python harness.py --web` | http://localhost:8007 |

The agent in each topic is **scripted**: it returns exactly the output a model would be prompted to produce, so every demo runs offline at no cost. Swapping in a real LLM is a later step.

## Repository layout

```text
common/            shared by every topic
  server_base.py   tiny stdlib HTTP + SSE server
  sales_data.py    the example data + the "model-written" HTML widget
  components.js    the component catalog (MetricCard, BarChart, ...) + sandboxed iframe
  json_patch.*     RFC 6902 JSON Patch in Python and JS
  style.css
01_foundations/ ... 07_harness_genui/   one folder per topic: README, server, page, tests
run_tests.py       runs every topic's tests
```
