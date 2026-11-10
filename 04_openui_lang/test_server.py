import os
import unittest

os.environ["GENUI_DELAY"] = "0"
import server  # noqa: E402
from openui_lang import ParseError, parse, resolve  # noqa: E402


class OpenUiLangTest(unittest.TestCase):
    def test_every_mode_parses_and_resolves(self):
        for mode in server.MODES:
            tree = resolve(parse(server.program(mode)))
            self.assertIn("component", tree, mode)

    def test_forward_reference(self):
        st = parse('root = Column([a])\na = Text("hi")')
        self.assertEqual(resolve(st)["props"]["children"][0]["props"]["text"], "hi")

    def test_unknown_component_rejected(self):
        with self.assertRaises(ParseError):
            parse('root = PieChart([1, 2])')

    def test_lang_is_smaller_than_json(self):
        c = server.compare({})
        self.assertLess(c["openui_lang"]["chars"], c["json_tree"]["chars"])

    def test_stream_is_line_by_line(self):
        events = list(server.stream({"mode": "declarative"}))
        self.assertTrue(events[0]["line"].startswith("root ="))
        self.assertTrue(events[-1]["done"])


if __name__ == "__main__":
    unittest.main()
