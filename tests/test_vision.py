import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest

from core.common import EditorError, ROOT
from core.adapters.footage import assign_tracks, crop_proposal
from core.adapters.vision import describe_frame


class VisionTests(unittest.TestCase):
    def test_crop_stays_inside_frame_and_tracks_are_spatial(self):
        crop = crop_proposal(400, 200, [350, 10, 40, 60], 9/16)
        self.assertLessEqual(crop["x"] + crop["width"], 400)
        self.assertLessEqual(crop["y"] + crop["height"], 200)
        previous, next_id = assign_tracks([], [[10,10,40,50]], 1)
        current, next_id = assign_tracks(previous, [[20,12,40,50], [300,10,40,50]], next_id)
        self.assertEqual(current[0]["track_id"], previous[0]["track_id"])
        self.assertNotEqual(current[1]["track_id"], previous[0]["track_id"])

    def test_ollama_request_encodes_image_and_marks_semantics_unverified(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(payload)
                result = {"message":{"content":None if payload["model"] == "broken" else json.dumps({"description":"Synthetic frame","visible_text":[],"events":[],"edit_suggestions":["Consider a closer crop"]})}}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        test_root = (ROOT / ".test-output").resolve()
        test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(test_root))
            image = Path(directory) / "test.jpg"
            image.write_bytes(b"synthetic-image-payload")
            try:
                result = describe_frame(image, "test-vision-model", f"http://127.0.0.1:{server.server_port}/api/chat")
                with self.assertRaisesRegex(EditorError, "Vision provider failed"):
                    describe_frame(image, "broken", f"http://127.0.0.1:{server.server_port}/api/chat")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
        self.assertEqual(requests[0]["messages"][0]["images"], [base64.b64encode(b"synthetic-image-payload").decode()])
        self.assertFalse(requests[0]["stream"])
        self.assertEqual(result["status"], "model-proposal-unverified")
        with self.assertRaisesRegex(EditorError, "Select an installed"):
            describe_frame(Path("unused"), "")
        with self.assertRaisesRegex(EditorError, "HTTP"):
            describe_frame(Path("unused"), "test-model", "file:///test")
