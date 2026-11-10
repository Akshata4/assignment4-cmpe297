import unittest

import harness


def run(mode):
    drawn, trace = [], []
    final = harness.run_agent("How did sales go?", mode, lambda k, p: drawn.append((k, p)), trace.append)
    return final, drawn, trace


class HarnessTest(unittest.TestCase):
    def test_each_mode_draws_once_and_finishes(self):
        expected = {"static": "component", "declarative": "spec", "open_ended": "html", "hybrid": "spec"}
        for mode, kind in expected.items():
            final, drawn, _ = run(mode)
            self.assertTrue(final.startswith("Done"), mode)
            self.assertEqual([k for k, _ in drawn], [kind], mode)

    def test_model_recovers_from_invalid_spec(self):
        _, _, trace = run("declarative")
        self.assertTrue(any("PieChart" in line for line in trace))  # error was fed back
        self.assertTrue(any("'ok': True" in line for line in trace))  # and then fixed

    def test_generated_view_blocked_outside_hybrid(self):
        spec = harness._spec(harness.SALES, hybrid=True, mistake=False)
        self.assertTrue(harness.validate_spec(spec, allow_generated=False))
        self.assertEqual(harness.validate_spec(spec, allow_generated=True), [])


if __name__ == "__main__":
    unittest.main()
