"""Agent helpers: cut placement on quiet audio, balanced captions, previews.

Synthetic media only: these check timing and text layout, not editorial taste.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from core.common import ROOT, EditorError, executable, read_json, write_json
from core.edit_tools import build_captions, caption_items, cut_plan, preview
from core.jobs import create_job


def run(command):
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def word(start, end, text):
    return {"start": start, "end": end, "text": " " + text}


class EditToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = executable("ffmpeg")
        except EditorError as error:
            raise unittest.SkipTest(str(error))
        root = (ROOT / ".test-output").resolve()
        root.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="edit-tools-", dir=root)
        cls.base = Path(cls.temp.name).resolve()
        assert cls.base.is_relative_to(root) and cls.base != root
        # Tone 0-1.0 s, silence 1.0-1.4 s, tone 1.4-4.0 s.
        cls.source = cls.base / "speech.mp4"
        run([cls.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=gray:s=160x284:r=30:d=4",
             "-f", "lavfi", "-i", "aevalsrc='0.5*sin(2*PI*440*t)*(lt(t,1)+gte(t,1.4))':s=48000:d=4",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(cls.source)])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def make_job(self, name):
        with patch("core.jobs.ROOT", self.base):
            folder = create_job(name, self.source, "melvynx-raw-vi", "Synthetic tool test only")
        revision = folder / "revisions/r001"
        plan = read_json(revision / "edit-plan.json")
        plan["export"].update(width=160, height=284)
        write_json(revision / "edit-plan.json", plan, replace=True)
        return folder, revision

    def test_cut_moves_boundaries_into_the_gap_and_reports_words(self):
        folder, revision = self.make_job("cut")
        write_json(folder / "transcript/cleaned.json", {"job_id": "cut", "asset_id": "raw-001", "segments": [
            {"start": 0.1, "end": 3.0, "text": "một hai ba", "words": [word(0.1, 0.9, "một"), word(1.4, 2.0, "hai"), word(2.2, 3.0, "ba")]}]})
        # The rough range starts inside the tone; the quiet gap is 1.0-1.4 s.
        report = cut_plan(folder, revision, [(0.95, 1.45)], search=0.15)
        clips = read_json(revision / "edit-plan.json")["clips"]
        self.assertEqual(len(clips), 2)
        self.assertGreaterEqual(clips[0]["source_out_seconds"], 1.0 - 1 / 30)
        self.assertLessEqual(clips[1]["source_in_seconds"], 1.4 + 1 / 30)
        self.assertEqual(clips[1]["timeline_in_frame"], clips[0]["timeline_out_frame"])
        for clip in clips:
            frames = clip["timeline_out_frame"] - clip["timeline_in_frame"]
            self.assertAlmostEqual((clip["source_out_seconds"] - clip["source_in_seconds"]) * 30, frames, delta=0.51)
        self.assertEqual(report["cuts"][0]["dropped_words"], "")
        self.assertTrue((revision / "cut-report.json").is_file())
        # Removing a spoken word is reported; overlapping ranges are refused.
        report = cut_plan(folder, revision, [(1.4, 2.05)], refine=False)
        self.assertEqual(report["cuts"][0]["dropped_words"], "hai")
        with self.assertRaises(EditorError):
            cut_plan(folder, revision, [(1.0, 2.0), (1.5, 2.5)])

    def test_cut_refuses_an_exported_revision(self):
        folder, revision = self.make_job("exported")
        (revision / "renders").mkdir()
        (revision / "renders/video.mp4").write_bytes(b"")
        with self.assertRaisesRegex(EditorError, "already exported"):
            cut_plan(folder, revision, [(1.0, 1.4)])

    def test_captions_are_balanced_keep_compounds_and_capitalise_after_a_cut(self):
        plan = {"fps": 30, "duration_frames": 300, "captions": {"max_chars": 26, "max_lines": 2},
                "clips": [{"source_in_seconds": 0, "source_out_seconds": 4, "timeline_in_frame": 0, "timeline_out_frame": 120},
                          {"source_in_seconds": 5, "source_out_seconds": 11, "timeline_in_frame": 120, "timeline_out_frame": 300}]}
        texts = "Có thể nhận ra thông qua cái việc kiểm tra giao dịch của ban lãnh đạo".split()
        first = [word(0.1 + i * 0.25, 0.3 + i * 0.25, t) for i, t in enumerate(texts)]
        transcript = {"segments": [
            {"start": 0.1, "end": 4.0, "words": first},
            # "Đấy nhá," is cut away (source 4-5 s); the sentence continues with lowercase "đấy".
            {"start": 4.2, "end": 7.0, "words": [word(4.2, 4.5, "Đấy"), word(4.5, 4.8, "nhá,"), word(5.1, 5.4, "đấy"),
                                                 word(5.4, 5.7, "chính"), word(5.7, 6.0, "là"), word(6.0, 6.3, "nghịch"), word(6.3, 6.6, "lý")]},
        ]}
        items = caption_items(plan, transcript)
        for item in items:
            lines = item["text"].split("\n")
            self.assertLessEqual(len(lines), 2)
            self.assertTrue(all(len(line) <= 26 for line in lines))
            for left, right in zip(lines, lines[1:]):
                self.assertNotIn((left.split()[-1].lower(), right.split()[0].lower()),
                                 {("thông", "qua"), ("kiểm", "tra"), ("lãnh", "đạo"), ("giao", "dịch")})
        self.assertEqual(" ".join(" ".join(i["text"].split()) for i in items[:-1]), " ".join(texts))
        self.assertTrue(items[-1]["text"].startswith("Đấy chính là"))
        self.assertTrue(all(a["timeline_out_frame"] <= b["timeline_in_frame"] for a, b in zip(items, items[1:])))

    def test_build_captions_and_preview_write_outside_the_revision_render(self):
        folder, revision = self.make_job("preview")
        write_json(folder / "transcript/cleaned.json", {"job_id": "preview", "asset_id": "raw-001", "segments": [
            {"start": 0.1, "end": 3.0, "text": "một hai ba", "words": [word(0.1, 0.9, "Một"), word(1.4, 2.0, "hai"), word(2.2, 3.0, "ba")]}]})
        result = build_captions(folder, revision)
        self.assertEqual(result["cues"], 1)
        video, sheet = preview(folder, revision, seconds=2, stills=[0.5, 1.5])
        self.assertTrue(video.is_file() and sheet.is_file())
        self.assertEqual(video.parent, folder / "previews")
        duration = json.loads(run([executable("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)]))
        self.assertAlmostEqual(float(duration["format"]["duration"]), 2.0, delta=0.1)
        self.assertFalse((revision / "renders/video.mp4").exists())


if __name__ == "__main__":
    unittest.main()
