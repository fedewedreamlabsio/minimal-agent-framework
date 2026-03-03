from __future__ import annotations

import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from maf import RuntimeConfig, build_power_tools


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello-http"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        del format, args


def _tool_by_name(tools, name):
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"missing tool: {name}")


class PowerToolTests(unittest.TestCase):
    def test_shell_exec_success_and_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = RuntimeConfig(fs_root_path=tmp, default_tool_timeout_seconds=1.0)
            tool = _tool_by_name(build_power_tools(config), "shell.exec")

            ok = tool.handler({"cmd": "printf hi"}, None)
            self.assertTrue(ok["success"])
            self.assertEqual(ok["stdout"], "hi")

            timeout = tool.handler(
                {
                    "cmd": "python3 -c 'import time; time.sleep(0.2)'",
                    "timeout_seconds": 0.05,
                },
                None,
            )
            self.assertTrue(timeout["timed_out"])
            self.assertFalse(timeout["success"])

    def test_fs_write_read_and_list_with_root_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = RuntimeConfig(fs_root_path=tmp)
            fs = _tool_by_name(build_power_tools(config), "fs")

            write = fs.handler({"op": "write", "path": "notes/a.txt", "content": "alpha"}, None)
            self.assertTrue(write["ok"])

            read = fs.handler({"op": "read", "path": "notes/a.txt"}, None)
            self.assertEqual(read["content"], "alpha")

            listing = fs.handler({"op": "list", "path": "notes"}, None)
            self.assertEqual(listing["entries"][0]["name"], "a.txt")

            with self.assertRaises(PermissionError):
                fs.handler({"op": "read", "path": "../escape.txt"}, None)

    def test_http_fetch_respects_allowlist(self):
        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            allowed_prefix = f"http://127.0.0.1:{server.server_port}"
            config = RuntimeConfig(http_allowlist=[allowed_prefix])
            http_tool = _tool_by_name(build_power_tools(config), "http.fetch")
            res = http_tool.handler({"url": f"{allowed_prefix}/hello"}, None)
            self.assertTrue(res["ok"])
            self.assertEqual(res["body"], "hello-http")

            denied_config = RuntimeConfig(http_allowlist=[])
            denied_tool = _tool_by_name(build_power_tools(denied_config), "http.fetch")
            with self.assertRaises(PermissionError):
                denied_tool.handler({"url": f"{allowed_prefix}/hello"}, None)
        finally:
            server.shutdown()
            server.server_close()

    def test_kv_set_get_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            kv_path = str(Path(tmp) / "kv.json")
            config = RuntimeConfig(kv_store_path=kv_path)
            tools = build_power_tools(config)
            kv_set = _tool_by_name(tools, "kv.set")
            kv_get = _tool_by_name(tools, "kv.get")

            set_res = kv_set.handler({"key": "x", "value": 123}, None)
            self.assertTrue(set_res["ok"])
            get_res = kv_get.handler({"key": "x"}, None)
            self.assertTrue(get_res["found"])
            self.assertEqual(get_res["value"], 123)
            self.assertTrue(Path(kv_path).exists())


if __name__ == "__main__":
    unittest.main()
