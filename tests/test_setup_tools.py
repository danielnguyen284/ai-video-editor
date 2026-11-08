"""Setup helpers for a new machine: resumable pinned-model download and the skill check in doctor.

A local HTTP server stands in for Hugging Face; no real model weights are downloaded.
"""
from __future__ import annotations

import hashlib
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest

from core.common import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import download_model  # noqa: E402

FILES = {"config.json": b'{"a": 1}', "model.bin": bytes(range(256)) * 4000}


class RangeServer(BaseHTTPRequestHandler):
    drop_first_model_request = True

    def log_message(self, *args):
        pass

    def do_GET(self):
        name = self.path.rsplit("/", 1)[-1]
        body = FILES.get(name)
        if body is None:
            self.send_error(404)
            return
        start = int(self.headers["Range"].split("=")[1].split("-")[0]) if self.headers.get("Range") else 0
        self.send_response(206 if start else 200)
        self.send_header("Content-Length", str(len(body) - start))
        self.end_headers()
        if name == "model.bin" and RangeServer.drop_first_model_request:
            RangeServer.drop_first_model_request = False
            self.wfile.write(body[start:start + 300_000])  # the connection drops part way
            self.wfile.flush()
            self.close_connection = True
            return
        self.wfile.write(body[start:])


class ModelDownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), RangeServer)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/resolve"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        base = (ROOT / ".test-output").resolve()
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="model-download-", dir=base)
        self.target = Path(self.temp.name) / "faster-whisper-large-v3"
        self.sha = hashlib.sha256(FILES["model.bin"]).hexdigest()
        RangeServer.drop_first_model_request = True

    def tearDown(self):
        self.temp.cleanup()

    def restore(self, sha=None):
        return download_model.restore(self.target, base_url=self.url, files=tuple(FILES), model_sha256=sha or self.sha, needed=0, quiet=True)

    def test_interrupted_download_resumes_and_is_verified(self):
        with self.assertRaises((OSError, HTTPException)):
            self.restore()
        partial = self.target / "model.bin.part"
        self.assertTrue(partial.is_file())
        self.assertFalse((self.target / "model.bin").exists())
        self.restore()
        self.assertEqual((self.target / "model.bin").read_bytes(), FILES["model.bin"])
        self.assertFalse(partial.exists())
        self.assertIn(self.sha, (self.target / "source.json").read_text(encoding="utf-8"))
        # A complete, valid folder is only verified, never downloaded again.
        RangeServer.drop_first_model_request = True
        self.restore()
        self.assertTrue(RangeServer.drop_first_model_request)

    def test_wrong_checksum_is_refused_and_set_aside(self):
        RangeServer.drop_first_model_request = False
        with self.assertRaises(SystemExit):
            self.restore(sha="0" * 64)
        self.assertFalse((self.target / "model.bin").exists())
        self.assertTrue((self.target / "model.bin.bad").is_file())


if __name__ == "__main__":
    unittest.main()
