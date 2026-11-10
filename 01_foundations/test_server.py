import unittest

import server


class FoundationsTest(unittest.TestCase):
    def test_every_mode_validates(self):
        for mode in server.MODES:
            self.assertEqual(server.get_ui({"mode": mode})["errors"], [], mode)

    def test_unknown_component_is_rejected(self):
        errors = server.get_ui({"mode": "declarative", "broken": "1"})["errors"]
        self.assertTrue(any("PieChart" in e for e in errors))

    def test_generated_view_only_in_hybrid(self):
        reply = server.scripted_agent("hybrid")
        self.assertTrue(server.validate("declarative", reply))  # not allowed there
        self.assertEqual(server.validate("hybrid", reply), [])

    def test_actions_are_allow_listed(self):
        self.assertTrue(server.post_action({"name": "reorder"})["ok"])
        self.assertFalse(server.post_action({"name": "delete_database"})["ok"])


if __name__ == "__main__":
    unittest.main()
