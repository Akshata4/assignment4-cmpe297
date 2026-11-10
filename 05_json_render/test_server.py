import os
import sys
import unittest
from pathlib import Path

os.environ["GENUI_DELAY"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import render_terminal  # noqa: E402
import server  # noqa: E402
import spec as specs  # noqa: E402
from common.json_patch import apply_patch  # noqa: E402


class JsonRenderTest(unittest.TestCase):
    def test_every_mode_is_valid(self):
        for mode in specs.MODES:
            self.assertEqual(specs.validate(specs.build_spec(mode)), [], mode)

    def test_patches_rebuild_the_spec(self):
        doc = {}
        for event in server.stream({"mode": "hybrid"}):
            if "patch" in event:
                doc = apply_patch(doc, event["patch"])
        self.assertEqual(doc, specs.build_spec("hybrid"))

    def test_bad_spec_rejected(self):
        bad = specs.build_spec("declarative")
        bad["elements"]["pie"] = {"type": "PieChart", "props": {}}
        bad["elements"]["title"]["props"]["text"] = 42
        errors = specs.validate(bad)
        self.assertTrue(any("PieChart" in e for e in errors))
        self.assertTrue(any("expected str" in e for e in errors))

    def test_terminal_target(self):
        spec = specs.build_spec("declarative")
        text = "\n".join(render_terminal.render(spec, spec["root"]))
        self.assertIn("Revenue: $48,200", text)

    def test_action(self):
        self.assertIn("25 crates", server.action({"name": "reorder", "params": {"crates": 25}})["patch"][0]["value"])


if __name__ == "__main__":
    unittest.main()
