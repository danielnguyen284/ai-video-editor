"""Clip speed, keyframed zoom, blurred framing and timed SFX.

Synthetic media only: these check timing, pixels and audio placement, not taste.
"""
from __future__ import annotations

import array
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from core.common import ROOT, EditorError, executable, read_json, write_json
from core.adapters.camera import validate_zoom, zoom_at, zoom_filter
from core.adapters.ffmpeg import mapped_captions, render
from core.decisions import record_choice
from core.editor_service import EditorStore, content_signature
from core.jobs import create_job


def run(command):
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


class ZoomMathTests(unittest.TestCase):
    keys = [{"source_seconds": 1, "scale": 1, "x": 0.5, "y": 0.5},
            {"source_seconds": 3, "scale": 2, "x": 0, "y": 1, "ease": "linear"}]

    def test_values_hold_outside_and_interpolate_inside(self):
        self.assertEqual(zoom_at(self.keys, 0), (1, 0.5, 0.5))
        self.assertEqual(zoom_at(self.keys, 2), (1.5, 0.25, 0.75))
        self.assertEqual(zoom_at(self.keys, 5), (2, 0, 1))

    def test_eases_and_hold(self):
        keys = deepcopy(self.keys)
        keys[1]["ease"] = "hold"
        self.assertEqual(zoom_at(keys, 2.999)[0], 1)
        self.assertEqual(zoom_at(keys, 3)[0], 2)
        keys[1]["ease"] = "in-out"
        self.assertAlmostEqual(zoom_at(keys, 2)[0], 1.5)
        self.assertLess(zoom_at(keys, 1.5)[0], 1.25)
        default = deepcopy(keys)
        del default[1]["ease"]
        self.assertEqual(zoom_at(default, 1.5), zoom_at(keys, 1.5))

    def test_invalid_keyframes_fail_explicitly(self):
        good = {"source_seconds": 1, "scale": 1.2, "x": 0.5, "y": 0.5}
        cases = (
            ([], "1-32"),
            ([good, {**good, "source_seconds": 0.5}], "increasing"),
            ([{**good, "scale": 0.5}], "zoom scale"),
            ([{**good, "scale": 5}], "between 1 and 4"),
            ([{**good, "x": 1.5}], "between 0 and 1"),
            ([{**good, "ease": "bounce"}], "ease"),
            ([{**good, "rotate": 3}], "Unsupported"),
            ([{**good, "source_seconds": 11}], "beyond"),
        )
        for zoom, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(EditorError, message):
                validate_zoom(zoom, 10)

    def test_identity_zoom_adds_no_filter(self):
        clip = {"source_in_seconds": 0, "source_out_seconds": 2, "timeline_in_frame": 0,
                "timeline_out_frame": 60, "playback_rate": 1,
                "zoom": [{"source_seconds": 0, "scale": 1, "x": 0, "y": 0}]}
        self.assertEqual(zoom_filter(clip, 30), "")
        clip["zoom"].append({"source_seconds": 1, "scale": 1.2, "x": 0, "y": 0})
        self.assertIn("perspective=", zoom_filter(clip, 30))
        # A later keyframe that this clip never reaches does not change it.
        clip["zoom"][1]["source_seconds"] = 5
        clip["zoom"][1]["ease"] = "hold"
        self.assertEqual(zoom_filter(clip, 30), "")


class SpeedTimingTests(unittest.TestCase):
    def test_captions_follow_clip_speed(self):
        plan = {"fps": 30, "captions": {"max_chars": 28, "max_lines": 2}, "clips": [
            {"source_in_seconds": 2, "source_out_seconds": 4, "timeline_in_frame": 0, "playback_rate": 2},
            {"source_in_seconds": 0, "source_out_seconds": 1, "timeline_in_frame": 30, "playback_rate": 0.5},
        ]}
        transcript = {"segments": [
            {"start": 0.2, "end": 0.4, "text": "slow", "words": [{"start": 0.2, "end": 0.4, "text": "slow"}]},
            {"start": 3.0, "end": 3.4, "text": "fast", "words": [{"start": 3.0, "end": 3.4, "text": "fast"}]},
        ]}
        cues = mapped_captions(plan, transcript)
        self.assertEqual([cue[2] for cue in cues], ["fast", "slow"])
        self.assertAlmostEqual(cues[0][0], 0.5)
        self.assertAlmostEqual(cues[0][1], 0.7)
        self.assertAlmostEqual(cues[1][0], 1.4)
        self.assertAlmostEqual(cues[1][1], 1.8)


class EffectRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = executable("ffmpeg")
        except EditorError as error:
            raise unittest.SkipTest(str(error))
        root = (ROOT / ".test-output").resolve()
        root.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="effects-", dir=root)
        cls.base = Path(cls.temp.name).resolve()
        assert cls.base.is_relative_to(root) and cls.base != root
        # Red for 2 s then blue for 2 s, with a 440 Hz tone.
        cls.colors = cls.base / "colors.mp4"
        run([cls.ffmpeg, "-v", "error", "-y",
             "-f", "lavfi", "-i", "color=red:size=160x90:rate=30:duration=2",
             "-f", "lavfi", "-i", "color=blue:size=160x90:rate=30:duration=2",
             "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
             "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.colors)])
        # Left half black, right half white: zoom moves the boundary.
        cls.split = cls.base / "split.mp4"
        run([cls.ffmpeg, "-v", "error", "-y",
             "-f", "lavfi", "-i", "color=white:size=320x180:rate=30:duration=3,drawbox=x=0:y=0:w=160:h=180:color=black:t=fill",
             "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.split)])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def make_job(self, name, source, width, height, fit):
        with patch("core.jobs.ROOT", self.base):
            folder = create_job(name, source, "melvynx-raw-vi", "Synthetic effect test only")
        revision = folder / "revisions/r001"
        plan = read_json(revision / "edit-plan.json")
        plan["export"].update(width=width, height=height, fit=fit)
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
        record_choice(revision, "edit-plan", "Test user selected this concrete proposal", summary="Synthetic effect test")
        return render(revision.parents[1], revision)

    def pixel(self, video, second, x, y):
        data = run([self.ffmpeg, "-v", "error", "-ss", f"{second:.3f}", "-i", str(video),
                    "-vf", f"crop=8:8:{x - 4}:{y - 4},scale=1:1", "-frames:v", "1",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"])
        return tuple(data[:3])

    def samples(self, video):
        data = run([self.ffmpeg, "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "48000",
                    "-f", "s16le", "pipe:1"])
        return array.array("h", data)

    def duration(self, video):
        result = run([executable("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)])
        return float(json.loads(result)["format"]["duration"])

    def test_double_speed_halves_time_and_keeps_pitch(self):
        folder, revision, plan = self.make_job("speed-2x", self.colors, 160, 90, "pad")
        plan["clips"][0].update(source_in_seconds=0, source_out_seconds=4, timeline_in_frame=0,
                                timeline_out_frame=60, playback_rate=2.0)
        plan["duration_frames"] = 60
        video = self.export(revision, plan)
        self.assertAlmostEqual(self.duration(video), 2.0, delta=0.05)
        red, blue = self.pixel(video, 0.5, 80, 45), self.pixel(video, 1.5, 80, 45)
        self.assertGreater(red[0], 180)
        self.assertLess(red[2], 80)
        self.assertGreater(blue[2], 180)
        self.assertLess(blue[0], 80)
        # atempo keeps 440 Hz; resampling would double it to 880 Hz.
        audio = self.samples(video)[24000:72000]
        rises = sum(1 for a, b in zip(audio, audio[1:]) if a < -500 <= b)
        self.assertAlmostEqual(rises, 440, delta=25)

    def test_keyframed_zoom_scales_around_its_focal_point(self):
        folder, revision, plan = self.make_job("zoom-linear", self.split, 320, 180, "pad")
        plan["clips"][0]["zoom"] = [
            {"source_seconds": 0, "scale": 1, "x": 0, "y": 0.5},
            {"source_seconds": 2, "scale": 2, "x": 0, "y": 0.5, "ease": "linear"},
        ]
        video = self.export(revision, plan)
        # The black/white edge starts at x=160 and moves right as the left edge stays fixed.
        self.assertGreater(self.pixel(video, 0, 200, 90)[0], 200)
        self.assertLess(self.pixel(video, 1.0, 200, 90)[0], 40)
        self.assertGreater(self.pixel(video, 1.0, 280, 90)[0], 200)
        self.assertLess(self.pixel(video, 2.5, 280, 90)[0], 40)

    def test_hold_punch_in_lands_on_its_source_second_at_any_speed(self):
        folder, revision, plan = self.make_job("zoom-punch", self.split, 320, 180, "pad")
        plan["clips"][0].update(timeline_out_frame=45, playback_rate=2.0)
        plan["duration_frames"] = 45
        plan["clips"][0]["zoom"] = [
            {"source_seconds": 0, "scale": 1, "x": 0, "y": 0.5},
            {"source_seconds": 2, "scale": 2, "x": 0, "y": 0.5, "ease": "hold"},
        ]
        video = self.export(revision, plan)
        # Source second 2 plays at output second 1 when doubled.
        self.assertGreater(self.pixel(video, 0.9, 200, 90)[0], 200)
        self.assertLess(self.pixel(video, 1.1, 200, 90)[0], 40)

    def test_blur_fit_fills_the_bars_with_the_picture(self):
        colors = {}
        for fit in ("pad", "blur"):
            folder, revision, plan = self.make_job("fit-" + fit, self.colors, 160, 284, fit)
            video = self.export(revision, plan)
            colors[fit] = self.pixel(video, 0.5, 80, 20), self.pixel(video, 0.5, 80, 142)
        self.assertLess(max(colors["pad"][0]), 20)
        top = colors["blur"][0]
        self.assertGreater(top[0], 120)
        self.assertLess(top[2], 60)
        self.assertGreater(colors["pad"][1][0], 180)
        self.assertGreater(colors["blur"][1][0], 180)

    def test_sfx_plays_at_its_frame_and_missing_files_fail(self):
        folder, revision, plan = self.make_job("sfx", self.colors, 160, 90, "pad")
        (folder / "assets/audio").mkdir(parents=True, exist_ok=True)
        run([self.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=0.5",
             str(folder / "assets/audio/beep.wav")])
        plan["audio"]["voice_gain"] = 0
        plan["audio"]["sfx"] = [{"id": "beep", "path": "assets/audio/beep.wav",
                                 "timeline_in_frame": 30, "timeline_out_frame": 45, "gain": 1}]
        broken = deepcopy(plan)
        broken["audio"]["sfx"][0]["path"] = "assets/audio/missing.wav"
        write_json(revision / "edit-plan.json", broken, replace=True)
        with self.assertRaisesRegex(EditorError, "SFX"):
            render(folder, revision, dry_run=True)
        video = self.export(revision, plan)
        audio = self.samples(video)
        loudness = lambda a, b: max(abs(v) for v in audio[int(a * 48000):int(b * 48000)])
        self.assertLess(loudness(0.2, 0.9), 300)
        self.assertGreater(loudness(1.1, 1.4), 2000)
        self.assertLess(loudness(1.6, 1.9), 300)
        manifest = read_json(revision / "render-manifest.json")
        self.assertEqual([item["id"] for item in manifest["audio_assets"]], ["beep"])

    def test_plain_plan_keeps_its_original_filtergraph(self):
        folder, revision, plan = self.make_job("plain", self.colors, 160, 90, "pad")
        write_json(revision / "edit-plan.json", plan, replace=True)
        render(folder, revision, dry_run=True)
        graph = (revision / "filtergraph.txt").read_text(encoding="utf-8")
        self.assertIn("setpts=PTS-STARTPTS,fps=30,scale=160:90", graph)
        for added in ("perspective", "atempo", "gblur", "adelay"):
            self.assertNotIn(added, graph)


class EffectLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / ".test-output"
        base.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="effect-locks-", dir=base)
        cls.base = Path(cls.temp.name).resolve()
        assert cls.base.is_relative_to(base.resolve())
        cls.source = cls.base / "source.mp4"
        run([executable("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "color=red:s=160x284:r=30:d=4",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-c:a", "aac", str(cls.source)])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.job = self.id().split(".")[-1].replace("_", "-")
        with patch("core.jobs.ROOT", self.base):
            self.folder = create_job(self.job, self.source, "motion-catalog-vi", "Synthetic editor test; not a real user choice")
        revision = self.folder / "revisions/r001"
        plan = read_json(revision / "edit-plan.json")
        plan["export"].update(width=160, height=284)
        write_json(revision / "edit-plan.json", plan, replace=True)
        (self.folder / "assets/audio").mkdir(parents=True, exist_ok=True)
        run([executable("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "sine=frequency=900:duration=0.3",
             str(self.folder / "assets/audio/pop.wav")])
        self.store = EditorStore(self.base)

    def sfx(self, start, end):
        return {"id": f"pop-{start}", "path": "assets/audio/pop.wav", "timeline_in_frame": start, "timeline_out_frame": end, "gain": 0.8}

    def test_new_fields_without_visible_effect_keep_existing_signatures(self):
        state = self.store.load(self.job)
        signature = lambda plan: content_signature(self.folder, plan, state["cues"], state["motions"], 0, 60, canonical=True)
        same = deepcopy(state["plan"])
        same["audio"]["sfx"] = [self.sfx(90, 100)]
        same["clips"][0]["zoom"] = [{"source_seconds": 0, "scale": 1, "x": 0.1, "y": 0.9},
                                    {"source_seconds": 3, "scale": 1.3, "x": 0.5, "y": 0.5, "ease": "hold"}]
        self.assertEqual(signature(state["plan"]), signature(same))
        same["audio"]["sfx"].append(self.sfx(50, 70))
        self.assertNotEqual(signature(state["plan"]), signature(same))

    def test_lock_blocks_speed_zoom_and_overlapping_sfx_only(self):
        state = self.store.save(self.job, self.store.load(self.job), 0)
        state = self.store.lock(self.job, 30, 60, "Approved", state["version"])
        blocked = {
            "speed": lambda s: (s["plan"]["clips"][0].update(playback_rate=2.0, timeline_out_frame=60),
                                s["plan"].update(duration_frames=60)),
            "zoom": lambda s: s["plan"]["clips"][0].update(zoom=[
                {"source_seconds": 1, "scale": 1, "x": 0.5, "y": 0.5},
                {"source_seconds": 2, "scale": 1.3, "x": 0.5, "y": 0.5}]),
            "sfx": lambda s: s["plan"]["audio"].update(sfx=[self.sfx(40, 50)]),
        }
        for name, mutate in blocked.items():
            changed = deepcopy(state)
            mutate(changed)
            with self.subTest(change=name), self.assertRaisesRegex(EditorError, "khóa"):
                self.store.save(self.job, changed, state["version"])
        changed = deepcopy(state)
        changed["plan"]["audio"]["sfx"] = [self.sfx(70, 80)]
        changed["plan"]["clips"][0]["zoom"] = [{"source_seconds": 2.5, "scale": 1, "x": 0.5, "y": 0.5},
                                               {"source_seconds": 3, "scale": 1.3, "x": 0.5, "y": 0.5}]
        saved = self.store.save(self.job, changed, state["version"])
        self.assertEqual(saved["plan"]["audio"]["sfx"][0]["timeline_in_frame"], 70)

    def test_studio_export_renders_all_effects_together(self):
        state = self.store.load(self.job)
        plan = state["plan"]
        plan["export"]["fit"] = "blur"
        plan["clips"][0].update(playback_rate=1.25, timeline_out_frame=96,
                                zoom=[{"source_seconds": 0, "scale": 1, "x": 0.5, "y": 0.4},
                                      {"source_seconds": 4, "scale": 1.15, "x": 0.5, "y": 0.4, "ease": "in-out"}])
        plan["duration_frames"] = 96
        plan["audio"]["sfx"] = [self.sfx(10, 19)]
        state = self.store.save(self.job, state, 0)
        record_choice(self.folder / "revisions/r001", "setup", "Synthetic test fixture explicitly selects these settings", answers={
            "style": "style/motion-catalog", "domain": "domain/source-context",
            "output": {k: state["plan"]["export"][k] for k in ("width", "height", "fps", "fit")},
            "footage_analysis": False, "transcription": False, "editing": "Synthetic fixture",
            "captions": False, "research": "None", "visuals": "Synthetic zoom", "audio": "Fixture voice and one SFX"})
        task_id = self.store.export(self.job, state["version"])["task"]
        for _ in range(300):
            task = self.store.tasks[task_id]
            if task["status"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual(task["status"], "complete", task)
        exported = read_json(self.folder / "revisions" / task["revision"] / "edit-plan.json")
        self.assertEqual(exported["export"]["fit"], "blur")
        self.assertEqual(exported["clips"][0]["playback_rate"], 1.25)
        self.assertEqual(len(exported["audio"]["sfx"]), 1)
        graph = (self.folder / "revisions" / task["revision"] / "filtergraph.txt").read_text(encoding="utf-8")
        for added in ("perspective", "atempo=1.25", "gblur", "adelay"):
            self.assertIn(added, graph)


if __name__ == "__main__":
    unittest.main()
