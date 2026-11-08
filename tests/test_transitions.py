"""Clip transitions, the Illustration image card and the Points card.

Synthetic media only: these check frame counts, pixels, timing and validation, not taste.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from core.common import ROOT, EditorError, executable, read_json, write_json
from core.adapters.ffmpeg import render, validate_plan
from core.adapters.motion import render_inputs, validate_spec
from core.decisions import record_choice
from core.editor_service import EditorStore, content_signature
from core.jobs import create_job


def run(command):
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def two_clips(transition=None):
    # Red source 0.5-1.5 s, then blue source 2.5-3.5 s: 30 frames each at 30 fps.
    clips = [
        {"clip_id": "red", "asset_id": "raw-001", "source_in_seconds": 0.5, "source_out_seconds": 1.5,
         "timeline_in_frame": 0, "timeline_out_frame": 30, "playback_rate": 1.0},
        {"clip_id": "blue", "asset_id": "raw-001", "source_in_seconds": 2.5, "source_out_seconds": 3.5,
         "timeline_in_frame": 30, "timeline_out_frame": 60, "playback_rate": 1.0},
    ]
    if transition:
        clips[1]["transition"] = transition
    return clips


class TransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = executable("ffmpeg")
        except EditorError as error:
            raise unittest.SkipTest(str(error))
        root = (ROOT / ".test-output").resolve()
        root.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="transitions-", dir=root)
        cls.base = Path(cls.temp.name).resolve()
        assert cls.base.is_relative_to(root) and cls.base != root
        cls.colors = cls.base / "colors.mp4"
        run([cls.ffmpeg, "-v", "error", "-y",
             "-f", "lavfi", "-i", "color=red:size=160x90:rate=30:duration=2",
             "-f", "lavfi", "-i", "color=blue:size=160x90:rate=30:duration=2",
             "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
             "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.colors)])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def make_job(self, name, clips):
        with patch("core.jobs.ROOT", self.base):
            folder = create_job(name, self.colors, "melvynx-raw-vi", "Synthetic transition test only")
        revision = folder / "revisions/r001"
        plan = read_json(revision / "edit-plan.json")
        plan["export"].update(width=160, height=90, fit="pad")
        plan.update(clips=clips, duration_frames=clips[-1]["timeline_out_frame"])
        return folder, revision, plan

    def export(self, revision, plan):
        write_json(revision / "edit-plan.json", plan, replace=True)
        skills = read_json(revision / "resolved-config.json")["profile"]["skills"]
        record_choice(revision, "setup", "Test user selected these explicit settings", answers={
            "style": skills["style"]["id"], "domain": skills["domain"]["id"],
            "output": {key: plan["export"][key] for key in ("width", "height", "fps", "fit")},
            "footage_analysis": False, "transcription": False, "editing": "Test user selected the listed timing",
            "captions": False, "research": "None", "visuals": "Framing only", "audio": "Test user selected this audio",
        })
        record_choice(revision, "edit-plan", "Test user selected this concrete proposal", summary="Synthetic transition test")
        return render(revision.parents[1], revision)

    def pixel(self, video, frame, x=80, y=45):
        data = run([self.ffmpeg, "-v", "error", "-i", str(video), "-vf",
                    f"select=eq(n\\,{frame}),crop=8:8:{x - 4}:{y - 4},scale=1:1", "-frames:v", "1",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"])
        return tuple(data[:3])

    def probe(self, video):
        result = run([executable("ffprobe"), "-v", "error", "-count_frames", "-show_entries",
                      "stream=codec_type,nb_read_frames,duration", "-of", "json", str(video)])
        return {s["codec_type"]: s for s in json.loads(result)["streams"]}

    def test_fade_is_centred_on_the_cut_and_keeps_length_and_voice(self):
        folder, revision, plan = self.make_job("fade", two_clips({"type": "fade", "frames": 10}))
        video = self.export(revision, plan)
        streams = self.probe(video)
        self.assertEqual(int(streams["video"]["nb_read_frames"]), 60)
        self.assertAlmostEqual(float(streams["audio"]["duration"]), 2.0, delta=0.03)
        red, middle, blue = self.pixel(video, 20), self.pixel(video, 30), self.pixel(video, 40)
        self.assertGreater(red[0], 200); self.assertLess(red[2], 60)
        self.assertGreater(blue[2], 200); self.assertLess(blue[0], 60)
        # Half way through the 25-35 window both colours are visible.
        self.assertTrue(70 < middle[0] < 190 and 70 < middle[2] < 190, middle)

    def test_slide_moves_the_incoming_clip_across(self):
        folder, revision, plan = self.make_job("slide", two_clips({"type": "slide-left", "frames": 10}))
        video = self.export(revision, plan)
        left, right = self.pixel(video, 30, x=20), self.pixel(video, 30, x=140)
        self.assertGreater(left[0], 200)
        self.assertGreater(right[2], 200)

    def test_invalid_transitions_fail_before_export(self):
        folder, revision, plan = self.make_job("invalid", two_clips())
        job, media = read_json(folder / "job.json"), {"duration_seconds": 4.0, "width": 160, "height": 90}
        validate_plan(plan, job, media)
        cases = []
        first = deepcopy(plan); first["clips"][0]["transition"] = {"type": "fade", "frames": 10}; cases.append(first)
        long = deepcopy(plan); long["clips"][1]["transition"] = {"type": "fade", "frames": 40}; cases.append(long)
        kind = deepcopy(plan); kind["clips"][1]["transition"] = {"type": "spin", "frames": 10}; cases.append(kind)
        # The blue clip would need picture before source second 0.
        early = deepcopy(plan); early["clips"][1]["source_in_seconds"], early["clips"][1]["source_out_seconds"] = 0.0, 1.0
        early["clips"][1]["transition"] = {"type": "fade", "frames": 10}; cases.append(early)
        # Two 10-frame transitions around a 6-frame clip overlap.
        crowded = deepcopy(plan)
        crowded["clips"] = [dict(plan["clips"][0], timeline_out_frame=30),
                            dict(plan["clips"][1], clip_id="short", source_out_seconds=2.7, timeline_out_frame=36,
                                 transition={"type": "fade", "frames": 10}),
                            dict(plan["clips"][1], clip_id="after", source_in_seconds=3.0, source_out_seconds=3.5,
                                 timeline_in_frame=36, timeline_out_frame=51, transition={"type": "fade", "frames": 10})]
        crowded["duration_frames"] = 51
        cases.append(crowded)
        for case in cases:
            with self.assertRaises(EditorError):
                validate_plan(case, job, media)

    def test_plan_without_transitions_keeps_one_concat(self):
        folder, revision, plan = self.make_job("plain", two_clips())
        write_json(revision / "edit-plan.json", plan, replace=True)
        render(folder, revision, dry_run=True)
        graph = (revision / "filtergraph.txt").read_text(encoding="utf-8")
        self.assertIn("concat=n=2:v=1:a=1[cutv][cuta]", graph)
        self.assertNotIn("xfade", graph)
        self.assertEqual(json.loads((revision / "ffmpeg-command.json").read_text(encoding="utf-8"))["argv"].count("-i"), 1)


class TransitionLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / ".test-output"
        base.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="transition-locks-", dir=base)
        cls.base = Path(cls.temp.name).resolve()
        cls.source = cls.base / "source.mp4"
        run([executable("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "color=red:s=160x284:r=30:d=4",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-c:a", "aac", str(cls.source)])
        with patch("core.jobs.ROOT", cls.base):
            cls.folder = create_job("locks", cls.source, "melvynx-raw-vi", "Synthetic editor test; not a real user choice")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_transition_joins_only_locks_touching_its_window(self):
        state = EditorStore(self.base).load("locks")
        plain = deepcopy(state["plan"])
        plain.update(clips=two_clips(), duration_frames=60)
        sign = lambda plan, a, b: content_signature(self.folder, plan, [], {}, a, b, canonical=True)
        faded = deepcopy(plain)
        faded["clips"][1]["transition"] = {"type": "fade", "frames": 10}
        self.assertEqual(sign(plain, 0, 20), sign(faded, 0, 20))
        self.assertEqual(sign(plain, 40, 60), sign(faded, 40, 60))
        self.assertNotEqual(sign(plain, 20, 30), sign(faded, 20, 30))
        # The incoming clip's handle is visible before the cut, so its trim matters there too.
        trimmed = deepcopy(faded)
        trimmed["clips"][1]["source_in_seconds"] = 2.6
        self.assertNotEqual(sign(faded, 20, 30), sign(trimmed, 20, 30))


class CardTemplateTests(unittest.TestCase):
    def test_illustration_validation_and_data_url_inputs(self):
        spec = {"template": "Illustration", "width": 400, "height": 300, "fps": 30, "duration_frames": 60,
                "props": {"image": "assets/illustrations/card.png", "enter": "slide-left", "exit": "fade", "motion": "zoom-in"}}
        validate_spec(spec)
        for change in ({"image": "../outside.png"}, {"image": "C:/abs.png"}, {"image": "assets/a.gif"},
                       {"enter": "spin"}, {"motion": "orbit"}, {"enter_frames": 40, "exit_frames": 30}, {"title": "x"}):
            bad = deepcopy(spec)
            bad["props"].update(change)
            with self.assertRaises(EditorError):
                validate_spec(bad)
        root = (ROOT / ".test-output").resolve()
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="illustration-", dir=root) as folder:
            folder = Path(folder)
            with self.assertRaisesRegex(EditorError, "not found"):
                render_inputs(folder, spec)
            (folder / "assets/illustrations").mkdir(parents=True)
            (folder / "assets/illustrations/card.png").write_bytes(b"\x89PNG fixture")
            inputs = render_inputs(folder, spec)
            self.assertTrue(inputs["props"]["image"].startswith("data:image/png;base64,"))
            self.assertEqual(spec["props"]["image"], "assets/illustrations/card.png")

    def test_points_validation(self):
        spec = {"template": "Points", "width": 1000, "height": 840, "fps": 30, "duration_frames": 90,
                "props": {"title": "Khi ban lãnh đạo", "items": [{"text": "Bán cổ phiếu", "at": 0}, {"text": "Cầm cố", "at": 40}],
                          "big": "99", "big_at": 10, "emphasis": "= đều là BÁN", "emphasis_at": 60, "accent": "#E5484D"}}
        validate_spec(spec)
        for change in ({"items": [{"text": "x", "at": 90}]}, {"items": [{"text": "x", "at": 0}] * 7},
                       {"title": ""}, {"emphasis_at": 120}, {"accent": "red"}, {"subtitle": "x"}):
            bad = deepcopy(spec)
            bad["props"].update(change)
            with self.assertRaises(EditorError):
                validate_spec(bad)
        only_title = {**spec, "props": {"title": "Chỉ có tiêu đề"}}
        with self.assertRaises(EditorError):
            validate_spec(only_title)
        # Full-width opaque panel with an app icon from the job.
        panel = deepcopy(spec)
        panel["props"].update(fill=True, icon="assets/illustrations/app-icon.png")
        validate_spec(panel)
        for change in ({"fill": "yes"}, {"icon": "../icon.png"}, {"icon": "assets/icon.svg"}):
            bad = deepcopy(panel)
            bad["props"].update(change)
            with self.assertRaises(EditorError):
                validate_spec(bad)
        root = (ROOT / ".test-output").resolve()
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="points-icon-", dir=root) as folder:
            folder = Path(folder)
            (folder / "assets/illustrations").mkdir(parents=True)
            (folder / "assets/illustrations/app-icon.png").write_bytes(b"\x89PNG fixture")
            inputs = render_inputs(folder, panel)
            self.assertTrue(inputs["props"]["icon"].startswith("data:image/png;base64,"))
            self.assertEqual(panel["props"]["icon"], "assets/illustrations/app-icon.png")
            self.assertIs(render_inputs(folder, spec), spec)


if __name__ == "__main__":
    unittest.main()
