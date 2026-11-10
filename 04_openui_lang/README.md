# 04 · OpenUI Lang: a compact language for UI

[OpenUI Lang](https://www.openui.com) (Thesys) describes a UI as lines of code:

```text
root = Column([title, metrics, chart, reorder])      ← arrives first, refers FORWARD
title = Heading("Weekly sales · Nov 3 - Nov 9")
metrics = Row([revenue, orders])
revenue = MetricCard("Revenue", "$48,200", "+12%")
...
```

Arguments are positional, and the catalog maps them to prop names. A bare name such as `title` is a **reference** to another line. The program streams line by line, and the page re-parses and re-renders after each line. References that haven't arrived yet show as placeholders.

| Mode | Program |
|---|---|
| Static | `root = MetricCard(...)` |
| Declarative | `root = Column([...])` plus one line per component |
| Open-ended | `root = HtmlArtifact("title", "<html>…")`, rendered in a sandbox |
| Hybrid | The catalog program plus one `HtmlArtifact` line |

The **Size** panel (`/compare`) measures the same dashboard written in OpenUI Lang and as a nested JSON tree. Token counts there are a rough characters ÷ 4 estimate, not real tokenizer output.

## Files

- `openui_lang.py` / `openui_lang.js`: the same small parser in Python (server and tests) and JS (browser). This is a teaching subset of the language.
- `server.py`: builds the program for each mode, streams it line by line, and serves the size comparison.
- `index.html`: the streaming renderer.

## Run

```bash
python server.py          # http://localhost:8004
python -m unittest -v
```
