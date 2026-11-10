import unittest

import server


def call(method, **params):
    return server.handle_rpc({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})


class McpAppsTest(unittest.TestCase):
    def test_view_tools_link_resources(self):
        tools = {t["name"]: t for t in call("tools/list")["result"]["tools"]}
        uri = tools["show_sales_card"]["_meta"]["ui"]["resourceUri"]
        self.assertEqual(uri, "ui://sales/card")
        self.assertNotIn("_meta", tools["reorder_product"])  # app-only tool, no view

    def test_tool_result_has_model_text_and_ui_data(self):
        result = call("tools/call", name="show_sales_dashboard", arguments={})["result"]
        self.assertEqual(result["content"][0]["type"], "text")
        self.assertEqual(result["structuredContent"]["spec"]["type"], "Column")

    def test_every_resource_reads_as_mcp_app_html(self):
        for res in call("resources/list")["result"]["resources"]:
            content = call("resources/read", uri=res["uri"])["result"]["contents"][0]
            self.assertEqual(content["mimeType"], "text/html;profile=mcp-app")
            self.assertIn("<html", content["text"].lower())

    def test_errors(self):
        self.assertEqual(call("nope")["error"]["code"], -32601)
        self.assertIn("error", call("tools/call", name="rm_rf"))


if __name__ == "__main__":
    unittest.main()
