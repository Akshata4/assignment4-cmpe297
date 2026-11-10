import json
import os
import sys
import unittest
from pathlib import Path

os.environ["GENUI_DELAY"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402
from common.json_patch import apply_patch  # noqa: E402


def run(**props):
    return list(server.run_agent({"forwardedProps": props}))


class AgUiTest(unittest.TestCase):
    def test_run_is_bracketed(self):
        for mode in server.MODES:
            events = run(mode=mode)
            self.assertEqual(events[0]["type"], "RUN_STARTED")
            self.assertEqual(events[-1]["type"], "RUN_FINISHED")

    def test_static_tool_args_reassemble(self):
        events = run(mode="static")
        args = "".join(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS")
        self.assertEqual(json.loads(args)["label"], "Revenue this week")

    def test_declarative_deltas_fill_the_dashboard(self):
        state = {}
        for e in run(mode="declarative"):
            if e["type"] == "STATE_SNAPSHOT":
                state = e["snapshot"]
            elif e["type"] == "STATE_DELTA":
                state = apply_patch(state, e["delta"])
        card = state["dashboard"]["children"][1]["children"][0]["props"]
        self.assertEqual(card["value"], "$48,200")

    def test_disallowed_action_errors(self):
        self.assertEqual(run(mode="static", action="drop_tables")[-1]["type"], "RUN_ERROR")


if __name__ == "__main__":
    unittest.main()
