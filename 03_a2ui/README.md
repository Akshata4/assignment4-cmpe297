# 03 · A2UI: structure and data change separately

[A2UI](https://a2ui.org) (Google) streams JSON **messages**:

| Message | Purpose |
|---|---|
| `createSurface` | Open a UI region and name its component catalog |
| `updateComponents` | A **flat** list of components linked by `id` (not a nested tree) |
| `updateDataModel` | Set data at a JSON Pointer path. Components bind with `{"path": "/revenue"}` |
| `deleteSurface` | Remove the surface |

Because components bind to data paths, the agent can update numbers **without resending the layout**. The last two messages in every mode do exactly that (revenue becomes "$49,050 · +14% (live)").

| Mode | What the agent sends |
|---|---|
| Static | A fixed, pre-written surface template. The agent only sends **data**. |
| Declarative | The full component list, composed by the agent |
| Open-ended | One `GeneratedView` component (a custom catalog entry) holding HTML |
| Hybrid | The composed list plus one `GeneratedView` |

**User actions (client → server):** typing in the `TextField` writes to the data model (two-way binding). The Button's `action.event.context` is resolved from the data model **at click time** and POSTed to `/action`. The server replies with more `updateDataModel` messages.

Message shapes follow the A2UI v0.9 envelope, simplified, with a custom catalog. A later step can use Google's official renderer.

## Run

```bash
python server.py          # http://localhost:8003
python -m unittest -v
```

## What to show in the video

Read the message panel top to bottom. Point out the flat `children: ["rev", "ord"]` ids and the `{"path": ...}` bindings. Then change the crate count, click **Reorder**, and show the action payload in the log.
