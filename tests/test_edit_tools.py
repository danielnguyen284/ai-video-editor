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
from core.edit_tools import build_captions, caption_items, cut_draft, cut_plan, place_cuts, place_splits, preview
from core.editor_service import EditorStore
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
        # Tone 0-1.0 s, pause 1.0-2.0 s, tone 2.0-3.2 s with no gap, short pause 3.2-3.5 s, tone 3.5-4.0 s.
        cls.source = cls.base / "speech.mp4"
        run([cls.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=gray:s=160x284:r=30:d=4",
             "-f", "lavfi", "-i", "aevalsrc='0.5*sin(2*PI*440*t)*(lt(t,1)+between(t,2,3.2)+gte(t,3.5))':s=48000:d=4",
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

    def test_cuts_land_in_pauses_keep_a_breath_and_skip_continuous_speech(self):
        # 10 ms levels: speech 0-1 s, pause 1-2 s, speech 2-3.2 s, pause 3.2-3.5 s, speech 3.5-4 s.
        levels = [-20.0] * 100 + [-60.0] * 100 + [-20.0] * 120 + [-60.0] * 30 + [-20.0] * 50
        placed, skipped = place_cuts(levels, [(0.95, 2.05), (2.55, 2.65), (3.15, 3.55)], 4.0, 30)
        self.assertEqual(len(placed), 1)
        start, end = placed[0]["remove"]
        self.assertTrue(1.1 <= start <= 1.2 and 1.8 <= end <= 1.9, (start, end))  # 0.15 s of pause kept each side
        self.assertAlmostEqual(start * 30, round(start * 30), places=2)  # on a frame
        self.assertIn("continuous speech", skipped[0]["reason"])  # 2.55-2.65 has no pause at either edge
        self.assertIn("minimum", skipped[1]["reason"])  # a 0.3 s pause is not worth a cut
        # An edge never crosses a word to reach a pause.
        self.assertEqual(place_cuts(levels, [(1.5, 2.3)], 4.0, 30, search=1.0)[0], [])
        # Head and tail trims join nothing, so they may be short.
        self.assertEqual(len(place_cuts(levels, [(3.9, 4.0)], 4.0, 30, allow_tight=True)[0]), 1)
        # Only when the user asks: a tight edge goes on a frame between syllables.
        placed, _ = place_cuts(levels, [(2.0, 2.6)], 4.0, 30, allow_tight=True)
        self.assertTrue(placed[0]["notes"] and 1.1 <= placed[0]["remove"][0] <= 1.2)
        # A split for a transition sits in the middle of the nearest pause.
        self.assertAlmostEqual(place_splits(levels, [1.2], 30)[0], 1.5, delta=1 / 30)
        with self.assertRaises(EditorError):
            place_splits(levels, [2.6], 30)

    def test_cut_retimes_layers_sounds_and_transitions_when_loosened(self):
        folder, revision = self.make_job("cut")
        write_json(folder / "transcript/cleaned.json", {"job_id": "cut", "asset_id": "raw-001", "segments": [
            {"start": 0.1, "end": 3.9, "text": "một hai ba bốn", "words": [
                word(0.1, 0.9, "một"), word(2.0, 2.6, "hai"), word(2.6, 3.2, "ba"), word(3.5, 3.9, "bốn")]}]})
        report = cut_plan(folder, revision, [(1.0, 2.0)], refine=False)
        self.assertEqual(report["cuts"][0]["dropped_words"], "")
        plan = read_json(revision / "edit-plan.json")
        self.assertEqual([c["timeline_in_frame"] for c in plan["clips"]], [0, 30])
        plan["clips"][1]["transition"] = {"type": "fade", "frames": 6}
        plan["clips"][1]["zoom"] = [{"source_seconds": 2.0, "scale": 1.08, "x": 0.5, "y": 0.5}]
        plan["overlays"] = [{"id": "card", "type": "image", "path": "assets/card.png", "timeline_in_frame": 15,
                             "timeline_out_frame": 45, "x": 0, "y": 0, "width": 160, "height": 100}]
        plan["audio"]["sfx"] = [{"id": "whoosh", "path": "assets/whoosh.wav", "timeline_in_frame": 25,
                                 "timeline_out_frame": 40, "gain": 0.4}]
        write_json(revision / "edit-plan.json", plan, replace=True)
        # The user wants less cut: the same pause, now with a breath kept on both sides.
        report = cut_plan(folder, revision, [(0.95, 2.05), (2.55, 2.65)])
        plan = read_json(revision / "edit-plan.json")
        clips = plan["clips"]
        self.assertEqual(len(clips), 2)
        self.assertTrue(1.1 <= clips[0]["source_out_seconds"] <= 1.2 and 1.8 <= clips[1]["source_in_seconds"] <= 1.9)
        self.assertEqual(clips[1]["timeline_in_frame"], clips[0]["timeline_out_frame"])
        for clip in clips:
            frames = clip["timeline_out_frame"] - clip["timeline_in_frame"]
            self.assertAlmostEqual((clip["source_out_seconds"] - clip["source_in_seconds"]) * 30, frames, delta=0.51)
        self.assertEqual(clips[1]["transition"], {"type": "fade", "frames": 6})
        self.assertEqual(clips[1]["zoom"][0]["scale"], 1.08)
        cut = clips[1]["timeline_in_frame"]
        self.assertEqual(plan["audio"]["sfx"][0]["timeline_in_frame"], cut - 5)  # still 5 frames before the cut
        layer = plan["overlays"][0]
        self.assertEqual(layer["timeline_in_frame"], 15)
        self.assertEqual(layer["timeline_out_frame"], cut + round((2.5 - clips[1]["source_in_seconds"]) * 30))
        self.assertEqual(report["resized_layers"], ["card"])
        self.assertIn("continuous speech", report["skipped"][0]["reason"])
        self.assertTrue((revision / "cut-report.json").is_file())
        # Removing a spoken word is reported; overlapping ranges are refused.
        report = cut_plan(folder, revision, [(2.0, 2.6)], refine=False)
        self.assertEqual(report["cuts"][0]["dropped_words"], "hai")
        with self.assertRaises(EditorError):
            cut_plan(folder, revision, [(1.0, 2.0), (1.5, 2.5)])

    def test_studio_cut_is_a_proposal_with_rebuilt_captions(self):
        folder, revision = self.make_job("studio")
        write_json(folder / "transcript/cleaned.json", {"job_id": "studio", "asset_id": "raw-001", "segments": [
            {"start": 0.1, "end": 3.9, "text": "một hai ba bốn", "words": [
                word(0.1, 0.9, "Một"), word(2.0, 2.6, "hai"), word(2.6, 3.2, "ba"), word(3.5, 3.9, "bốn")]}]})
        store = EditorStore(self.base)
        result = cut_draft(folder, store, "studio", [(0.95, 2.05)])
        self.assertFalse((folder / "editor/project.json").exists())  # nothing changes before approval
        state = store.proposal("studio")["state"]
        self.assertEqual(len(state["plan"]["clips"]), 2)
        self.assertEqual(" ".join(" ".join(c["text"].split()) for c in state["cues"]), "Một hai ba bốn")
        self.assertAlmostEqual(result["duration_seconds"], state["plan"]["duration_frames"] / 30, places=2)

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
