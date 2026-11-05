"""A story step's answer is read as JSON only where the service says it is JSON.

recap's CU6 fetches the first hundred bytes of a recap's speech, and Try it decoded the WAV as text: the step
failed with a codec error on an answer that was exactly the one the story asked for.
"""
from __future__ import annotations

import importlib.util
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

SCRIPT = TOOLKIT_ROOT / "scripts/agents/try_it.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("try_it_request", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Answers(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 — http.server's own spelling
        if self.path == "/speech":
            body, kind = b"RIFF\xa4\x00\x00\x00WAVEfmt ", "audio/wav"
        else:
            body, kind = b'{"state": "ready"}', "application/json; charset=utf-8"
        self.send_response(206 if self.path == "/speech" else 200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 — the base class's name
        """Quiet."""


class RequestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load()
        self.server = HTTPServer(("127.0.0.1", 0), Answers)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def test_audio_is_an_answer_with_nothing_to_keep(self) -> None:
        self.assertIsNone(self.module.request("GET", f"{self.base}/speech", headers={"Range": "bytes=0-99"}))

    def test_json_is_read_as_json(self) -> None:
        self.assertEqual(self.module.request("GET", f"{self.base}/recap"), {"state": "ready"})


if __name__ == "__main__":
    unittest.main()
