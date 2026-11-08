"""Voice cleanup/loudness, transcript words for text editing, and Studio proposals.

Synthetic media only. Proposals are checked as data flow: nothing changes the
draft until an explicit accept, and stale or locked proposals are refused.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from core.common import ROOT, EditorError, digest, executable, read_json, write_json
from core.adapters.ffmpeg import render, validate_plan
from core.decisions import record_choice
from core.editor_server import make_server
from core.editor_service import EditorStore, describe_changes, transcript_words
from core.jobs import create_job


def run(command):
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result


class ToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = executable("ffmpeg")
        except EditorError as error:
            raise unittest.SkipTest(str(error))
        root = (ROOT / ".test-output").resolve()
        root.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="editing-tools-", dir=root)
        cls.base = Path(cls.temp.name).resolve()
        assert cls.base.is_relative_to(root) and cls.base != root
        # A tone for 2 s, then only room noise for 2 s, under a quiet hiss throughout.
        cls.source = cls.base / "noisy.mp4"
        run([cls.ffmpeg, "-v", "error", "-y",
             "-f", "lavfi", "-i", "color=gray:size=160x284:rate=30:duration=4",
             "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=48000:duration=2,volume=0.3,apad=pad_dur=2",
             "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.02:sample_rate=48000:duration=4",
             "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=longest:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
             str(cls.source)])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.job = self.id().split(".")[-1].replace("_", "-")
        with patch("core.jobs.ROOT", self.base):
            self.folder = create_job(self.job, self.source, "motion-catalog-vi", "Synthetic tool test; not a user choice")
        self.revision = self.folder / "revisions/r001"
        self.store = EditorStore(self.base)

    def export(self, plan):
        write_json(self.revision / "edit-plan.json", plan, replace=True)
        record_choice(self.revision, "setup", "Test user selected these explicit settings", answers={
            "style": "style/motion-catalog", "domain": "domain/source-context",
            "output": {k: plan["export"][k] for k in ("width", "height", "fps", "fit")},
            "footage_analysis": False, "transcription": False, "editing": "Synthetic", "captions": False,
            "research": "None", "visuals": "None", "audio": "Test user selected voice cleanup"})
        record_choice(self.revision, "edit-plan", "Test user selected this proposal", summary="Synthetic audio test")
        return render(self.folder, self.revision)

    def measure(self, video, filters):
        result = subprocess.run([self.ffmpeg, "-hide_banner", "-nostdin", "-i", str(video), "-vn", "-af", filters, "-f", "null", "-"],
                                capture_output=True)
        return result.stderr.decode("utf-8", errors="replace")

    def room_level(self, video):
        log = self.measure(video, "atrim=start=2.6:end=3.8,astats=metadata=0")
        return float(re.findall(r"RMS level dB: (-?[\d.]+|-inf)", log)[0])

    # Audio cleanup

    def test_strong_denoise_lowers_the_room_between_phrases(self):
        plan = read_json(self.revision / "edit-plan.json")
        plain = self.room_level(self.source)
        plan["audio"]["denoise"] = "strong"
        cleaned = self.room_level(self.export(plan))
        self.assertLess(cleaned, plain - 10)
        graph = (self.revision / "filtergraph.txt").read_text(encoding="utf-8")
        self.assertIn("afftdn", graph)

    def test_loudness_target_is_met_on_the_final_mix(self):
        plan = read_json(self.revision / "edit-plan.json")
        plan["audio"]["loudness_lufs"] = -14
        log = self.measure(self.export(plan), "ebur128")
        integrated = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", log)[-1])
        self.assertAlmostEqual(integrated, -14, delta=1.5)

    def test_invalid_cleanup_values_fail_explicitly(self):
        plan = read_json(self.revision / "edit-plan.json")
        job = read_json(self.folder / "job.json")
        for key, value, message in (("denoise", "max", "light or strong"), ("loudness_lufs", -40, "loudness"), ("loudness_lufs", -3, "between")):
            broken = deepcopy(plan)
            broken["audio"][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(EditorError, message):
                validate_plan(broken, job, job["input"]["media"])

    # Transcript words

    def test_transcript_words_prefer_corrected_text_and_keep_sentences_without_words(self):
        self.assertIsNone(transcript_words(self.folder, read_json(self.revision / "edit-plan.json")))
        raw = {"asset_id": "raw-001", "segments": [{"start": 0, "end": 1, "text": "sai", "words": [{"start": 0, "end": 1, "text": "sai"}]}]}
        write_json(self.folder / "transcript/raw.json", raw)
        cleaned = {"asset_id": "raw-001", "segments": [
            {"start": 0.2, "end": 1.0, "text": "Xin chào", "words": [{"start": 0.2, "end": 0.5, "text": " Xin"}, {"start": 0.5, "end": 1.0, "text": "chào "}]},
            {"start": 1.5, "end": 3.0, "text": "câu không có mốc từ"},
        ]}
        write_json(self.folder / "transcript/cleaned.json", cleaned)
        result = transcript_words(self.folder, read_json(self.revision / "edit-plan.json"))
        self.assertEqual(result["ref"], "transcript/cleaned.json")
        self.assertEqual([w["text"] for w in result["words"]], ["Xin", "chào", "câu không có mốc từ"])
        self.assertEqual(result["words"][2]["segment"], 1)
        cleaned["asset_id"] = "another-video"
        write_json(self.folder / "transcript/cleaned.json", cleaned, replace=True)
        self.assertEqual(transcript_words(self.folder, read_json(self.revision / "edit-plan.json"))["ref"], "transcript/raw.json")

    # Proposals

    def proposed(self, state):
        changed = deepcopy(state)
        clip = changed["plan"]["clips"][0]
        clip.update(source_out_seconds=3, timeline_out_frame=90)
        changed["plan"]["duration_frames"] = 90
        changed["plan"]["audio"]["denoise"] = "light"
        return changed

    def test_proposal_changes_nothing_until_accepted_then_is_one_version(self):
        state = self.store.save(self.job, self.store.load(self.job), 0)
        project = self.folder / "editor/project.json"
        before = digest(project)
        proposal = self.store.propose(self.job, self.proposed(state), state["version"], "Cắt 1 giây cuối và giảm ồn nhẹ")
        self.assertEqual(digest(project), before)
        self.assertIn("Thời lượng 4.0s → 3.0s", proposal["changes"])
        self.assertIn("Âm thanh thay đổi", proposal["changes"])
        self.assertEqual(self.store.proposal(self.job)["status"], "pending")
        accepted = self.store.decide_proposal(self.job, proposal["id"], True, state["version"])
        self.assertEqual(accepted["version"], state["version"] + 1)
        self.assertEqual(accepted["plan"]["duration_frames"], 90)
        record = self.store.proposal(self.job)
        self.assertEqual(record["status"], "accepted")
        self.assertNotIn("state", record)
        with self.assertRaisesRegex(EditorError, "không còn chờ"):
            self.store.decide_proposal(self.job, proposal["id"], True, accepted["version"])

    def test_stale_rejected_and_superseded_proposals(self):
        state = self.store.save(self.job, self.store.load(self.job), 0)
        first = self.store.propose(self.job, self.proposed(state), state["version"], "Bản một")
        second = self.store.propose(self.job, self.proposed(state), state["version"], "Bản hai")
        self.assertEqual(read_json(self.folder / f"editor/proposals/{first['id']}.json")["status"], "superseded")
        edited = deepcopy(state)
        edited["plan"]["audio"]["voice_gain"] = 0.9
        edited = self.store.save(self.job, edited, state["version"])
        with self.assertRaisesRegex(EditorError, "Draft đã thay đổi"):
            self.store.decide_proposal(self.job, second["id"], True, edited["version"])
        self.store.decide_proposal(self.job, second["id"], False)
        self.assertEqual(self.store.proposal(self.job)["status"], "rejected")
        self.assertEqual(self.store.load(self.job)["plan"]["audio"]["voice_gain"], 0.9)
        with self.assertRaisesRegex(EditorError, "tóm tắt"):
            self.store.propose(self.job, self.proposed(edited), edited["version"], " ")

    def test_proposal_cannot_change_an_approved_region(self):
        state = self.store.save(self.job, self.store.load(self.job), 0)
        state = self.store.lock(self.job, 60, 90, "Approved", state["version"])
        with self.assertRaisesRegex(EditorError, "khóa"):
            self.store.propose(self.job, self.proposed(state), state["version"], "Cắt vào vùng đã duyệt")
        self.assertIsNone(self.store.proposal(self.job))

    def test_studio_http_proposal_flow_and_transcript_in_project(self):
        write_json(self.folder / "transcript/cleaned.json", {"asset_id": "raw-001", "segments": [
            {"start": 0.2, "end": 0.6, "text": "một", "words": [{"start": 0.2, "end": 0.6, "text": "một"}]}]})
        state = self.store.save(self.job, self.store.load(self.job), 0)
        proposal = self.store.propose(self.job, self.proposed(state), state["version"], "Cắt đuôi")
        server = make_server(0, self.base)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            project = json.load(urlopen(f"{base}/api/project?job={self.job}"))
            self.assertEqual([w["text"] for w in project["transcript"]["words"]], ["một"])
            brief = json.load(urlopen(f"{base}/api/proposal?brief=1&job={self.job}"))["proposal"]
            self.assertEqual(brief["id"], proposal["id"])
            self.assertNotIn("state", brief)
            full = json.load(urlopen(f"{base}/api/proposal?job={self.job}"))["proposal"]
            self.assertEqual(full["state"]["plan"]["duration_frames"], 90)
            body = json.dumps({"job": self.job, "id": proposal["id"], "accept": True, "expected_version": state["version"]}).encode()
            accepted = json.load(urlopen(Request(f"{base}/api/proposal", data=body, headers={"Content-Type": "application/json", "X-AI-Editor": "studio"})))
            self.assertEqual(accepted["plan"]["duration_frames"], 90)
        finally:
            server.shutdown()
            server.server_close()

    def test_describe_changes_counts_captions(self):
        before = {"plan": {"fps": 30, "duration_frames": 30, "clips": [], "overlays": [], "audio": {}, "export": {}, "captions": {}},
                  "cues": [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}], "motions": {}}
        after = deepcopy(before)
        after["cues"] = [{"id": "a", "text": "x!"}, {"id": "c", "text": "z"}]
        self.assertEqual(describe_changes(before, after), ["Caption: thêm 1, bỏ 1, sửa 1"])
        self.assertEqual(describe_changes(before, deepcopy(before)), ["Không có thay đổi nhìn thấy được"])


if __name__ == "__main__":
    unittest.main()
