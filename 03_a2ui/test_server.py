import os
import unittest

os.environ["GENUI_DELAY"] = "0"
import server  # noqa: E402


class A2uiTest(unittest.TestCase):
    def test_message_order(self):
        for mode in server.MODES:
            kinds = [next(k for k in m if k != "version") for m in server.surface_messages(mode)]
            self.assertEqual(kinds[:3], ["createSurface", "updateComponents", "updateDataModel"], mode)

    def test_components_are_flat_and_linked(self):
        comps = server.composed_components(hybrid=True)
        self.assertEqual(server.validate(comps), [])
        self.assertTrue(all("children" not in c or all(isinstance(x, str) for x in c["children"]) for c in comps))

    def test_later_updates_are_data_only(self):
        tail = list(server.surface_messages("declarative"))[3:]
        self.assertTrue(all("updateDataModel" in m for m in tail))

    def test_action(self):
        out = server.handle_action({"action": {"name": "reorder", "context": {"crates": "25"}}})
        self.assertIn("25 crates", out["messages"][0]["updateDataModel"]["value"])
        out = server.handle_action({"action": {"name": "hack"}})
        self.assertIn("refused", out["messages"][0]["updateDataModel"]["value"])


if __name__ == "__main__":
    unittest.main()
