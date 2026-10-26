from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.common import EditorError, ROOT, executable, read_json, write_json
from core.jobs import create_job, new_revision
from core.adapters.ffmpeg import mapped_captions, probe, render, validate_plan
from core.decisions import record_choice


class TimelineTests(unittest.TestCase):
    def test_word_captions_follow_reordered_cuts(self):
        plan = {
            "fps": 30, "captions": {"max_chars": 28, "max_lines": 2},
            "clips": [
                {"source_in_seconds": 2, "source_out_seconds": 3, "timeline_in_frame": 0},
                {"source_in_seconds": 0, "source_out_seconds": 1, "timeline_in_frame": 30},
            ],
        }
        transcript = {"segments": [
            {"start": 0.1, "end": 0.5, "text": "first", "words": [{"start": 0.1, "end": 0.5, "text": "first"}]},
            {"start": 2.1, "end": 2.5, "text": "second", "words": [{"start": 2.1, "end": 2.5, "text": "second"}]},
        ]}
        captions = mapped_captions(plan, transcript)
        self.assertEqual([cue[2] for cue in captions], ["second", "first"])
        self.assertAlmostEqual(captions[0][0], 0.1)
        self.assertAlmostEqual(captions[1][0], 1.1)

    def test_partial_segment_without_word_times_is_not_silently_mislabelled(self):
        plan = {"fps": 30, "captions": {"max_chars": 28, "max_lines": 2}, "clips": [
            {"source_in_seconds": 1, "source_out_seconds": 2, "timeline_in_frame": 0},
        ]}
        with self.assertRaisesRegex(EditorError, "without word timestamps"):
            mapped_captions(plan, {"segments": [{"start": 0, "end": 3, "text": "a longer sentence"}]})


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = executable("ffmpeg")
            executable("ffprobe")
        except EditorError as error:
            raise unittest.SkipTest(str(error))
        test_root = (ROOT / ".test-output").resolve()
        test_root.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="workflow-", dir=test_root)
        cls.base = Path(cls.temp.name).resolve()
        # Verify the recursive TemporaryDirectory cleanup stays inside the test workspace.
        assert cls.base.is_relative_to(test_root) and cls.base != test_root
        cls.source = cls.base / "raw ti\u1ebfng Vi\u1ec7t test.mp4"
        cls.run_tool([
            cls.ffmpeg, "-v", "error", "-nostdin", "-y",
            "-f", "lavfi", "-i", "color=red:size=160x90:rate=30:duration=2",
            "-f", "lavfi", "-i", "color=blue:size=160x90:rate=30:duration=2",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.source),
        ])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def run_tool(command, input=None):
        result = subprocess.run(command, input=input, capture_output=True)
        if result.returncode:
            raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
        return result.stdout

    def make_job(self, name, source=None, profile="finance-premium-vi"):
        with patch("core.jobs.ROOT", self.base):
            folder = create_job(name, source or self.source, profile, "Synthetic test only")
        revision = folder / "revisions/r001"
        plan = read_json(revision / "edit-plan.json")
        plan["export"].update({"width": 160, "height": 284, "fit": "pad"})
        plan["captions"].update({"font_size": 14, "margin_v": 24, "max_chars": 20})
        write_json(revision / "edit-plan.json", plan, replace=True)
        return folder, revision, plan

    def pixel(self, video, second):
        data = self.run_tool([
            self.ffmpeg, "-v", "error", "-ss", str(second), "-i", str(video),
            "-vf", "crop=80:40:40:122,scale=1:1", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ])
        return tuple(data[:3])

    def select_setup(self, revision, plan, footage=False):
        skills = read_json(revision / "resolved-config.json")["profile"]["skills"]
        record_choice(revision, "setup", "Test user selected these explicit settings", answers={
            "style": skills["style"]["id"], "domain": skills["domain"]["id"],
            "output": {key: plan["export"][key] for key in ("width", "height", "fps", "fit")},
            "footage_analysis": footage, "transcription": False,
            "editing": "Test user selected the listed cuts", "captions": plan["captions"]["enabled"],
            "research": "None", "visuals": "Test user selected the supplied visual layers" if plan["overlays"] else "Caption/framing only", "audio": "Test user selected this audio treatment",
        })

    def select_plan(self, revision):
        record_choice(revision, "edit-plan", "Test user selected this concrete proposal", summary="Selected exact cuts, captions and audio for synthetic test")

    def test_visual_keyword_title_at_first_frame_and_only_selected_words(self):
        folder, revision, plan = self.make_job("visual-keyword", profile="finance-visual-keyword-vi")
        transcript = {"segments": [{"start":0.1,"end":3.9,"text":"FULL TRANSCRIPT MUST NOT APPEAR"}]}
        # Even with an existing transcript, this style has no automatic word cues.
        self.assertEqual(mapped_captions(plan, transcript), [])
        write_json(folder / "transcript/cleaned.json", transcript)
        text_file = folder / "assets/title.txt"
        text_file.write_text("TI\u00caU \u0110\u1ec0", encoding="utf-8")
        helper = ROOT / "skills/styles/visual-keyword/scripts/render_text.py"
        title = folder / "assets/visuals/title.png"
        command = [sys.executable, str(helper), "--text-file",str(text_file),"--output",str(title),"--width","160","--height","50","--font-size","20","--background","#15803D","--outline-width","0"]
        self.run_tool(command)
        original = title.read_bytes()
        duplicate = subprocess.run(command, capture_output=True)
        self.assertNotEqual(duplicate.returncode,0)
        self.assertEqual(title.read_bytes(),original)

        keyword = folder / "assets/visuals/keyword.png"
        transparent_command = [sys.executable,str(helper),"--text-file",str(text_file),"--output",str(keyword),"--width","160","--height","50","--font-size","20"]
        self.run_tool(transparent_command)
        pixels = self.run_tool([self.ffmpeg,"-v","error","-i",str(keyword),"-frames:v","1","-f","rawvideo","-pix_fmt","rgba","pipe:1"])
        alpha = pixels[3::4]
        self.assertEqual(alpha[0],0)
        self.assertEqual(max(alpha),255)

        picture = folder / "assets/visuals/illustration.png"
        self.run_tool([self.ffmpeg,"-v","error","-f","lavfi","-i","color=yellow:s=40x40","-frames:v","1",str(picture)])
        plan["captions"].update(enabled=True,items=[{"timeline_in_frame":30,"timeline_out_frame":60,"text":"KEYWORD"}])
        plan["overlays"] = [
            {"id":"opening-title","type":"image","path":"assets/visuals/title.png","timeline_in_frame":0,"timeline_out_frame":30,"x":0,"y":20,"width":160,"height":50,"fit":"contain"},
            {"id":"illustration","type":"image","path":"assets/visuals/illustration.png","timeline_in_frame":60,"timeline_out_frame":90,"x":110,"y":120,"width":40,"height":40,"fit":"contain"},
        ]
        write_json(revision / "edit-plan.json",plan,replace=True)
        self.select_setup(revision,plan)
        self.select_plan(revision)
        video = render(folder,revision)
        ass = (revision / "captions.ass").read_text(encoding="utf-8")
        self.assertIn("KEYWORD",ass)
        self.assertNotIn("FULL TRANSCRIPT",ass)
        self.assertIn("0:00:01.00,0:00:02.00",ass)
        # Title background is visible in the very first decoded frame.
        first = self.run_tool([self.ffmpeg,"-v","error","-i",str(video),"-vf","crop=2:2:4:24,scale=1:1","-frames:v","1","-f","rawvideo","-pix_fmt","rgb24","pipe:1"])
        self.assertGreater(first[1],first[0]+50,tuple(first[:3]))
        inset = self.run_tool([self.ffmpeg,"-v","error","-ss","2.4","-i",str(video),"-vf","crop=8:8:120:130,scale=1:1","-frames:v","1","-f","rawvideo","-pix_fmt","rgb24","pipe:1"])
        self.assertGreater(inset[0],inset[2]+100,tuple(inset[:3]))
        self.assertGreater(inset[1],inset[2]+100,tuple(inset[:3]))

    def test_render_reordered_video_captions_music_and_revision(self):
        folder, revision, plan = self.make_job("render-order")
        plan["clips"] = [
            {"clip_id": "blue", "asset_id": "raw-001", "source_in_seconds": 2, "source_out_seconds": 3, "timeline_in_frame": 0, "timeline_out_frame": 30, "playback_rate": 1.0},
            {"clip_id": "red", "asset_id": "raw-001", "source_in_seconds": 0, "source_out_seconds": 1, "timeline_in_frame": 30, "timeline_out_frame": 60, "playback_rate": 1.0},
        ]
        plan["duration_frames"] = 60
        plan["captions"]["enabled"] = True
        write_json(folder / "transcript/cleaned.json", {
            "schema_version": "1.0", "job_id": "render-order", "revision": 0, "asset_id": "raw-001",
            "segments": [
                {"start": 0.1, "end": 0.8, "text": "Xin ch\u00e0o", "words": [{"start": 0.1, "end": 0.8, "text": "Xin ch\u00e0o"}]},
                {"start": 2.1, "end": 2.8, "text": "T\u00e0i ch\u00ednh", "words": [{"start": 2.1, "end": 2.8, "text": "T\u00e0i ch\u00ednh"}]},
            ],
        })
        music = folder / "assets/music/test.wav"
        self.run_tool([self.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=0.7", str(music)])
        plan["audio"]["music"] = {"path": "assets/music/test.wav", "gain": 0.08, "ducking": True}
        write_json(revision / "edit-plan.json", plan, replace=True)
        self.select_setup(revision, plan)
        self.select_plan(revision)
        output = render(folder, revision)
        info = probe(output)
        self.assertEqual((info["width"], info["height"]), (160, 284))
        self.assertTrue(info["has_audio"])
        self.assertAlmostEqual(info["duration_seconds"], 2, delta=0.08)
        first, second = self.pixel(output, 0.4), self.pixel(output, 1.4)
        self.assertGreater(first[2], first[0] + 100, first)
        self.assertGreater(second[0], second[2] + 100, second)
        decoded = self.run_tool([self.ffmpeg, "-v", "error", "-i", str(output), "-vn", "-f", "s16le", "-ac", "1", "-ar", "48000", "pipe:1"])
        self.assertGreater(len(decoded), 48000 * 2 * 1.8)
        captions = (revision / "captions.ass").read_text(encoding="utf-8")
        self.assertLess(captions.index("T\u00e0i ch\u00ednh"), captions.index("Xin ch\u00e0o"))
        self.assertIn("0:00:00.10", captions)
        with self.assertRaisesRegex(EditorError, "already rendered"):
            render(folder, revision)
        with patch("core.jobs.ROOT", self.base):
            next_revision = new_revision("render-order", "Remove the first clip", "r001")
        next_plan = read_json(next_revision / "edit-plan.json")
        self.assertEqual(next_plan["revision"], 2)
        self.assertTrue(output.is_file())
        self.assertEqual(read_json(folder / "feedback/r002.json")["viewed_revision"], "r001")
        self.assertEqual(read_json(next_revision / "resolved-config.json")["revision"], 2)
        next_choices = read_json(next_revision / "decisions.json")
        self.assertEqual(next_choices["setup"]["status"], "selected")
        self.assertEqual(next_choices["edit_plan"]["status"], "pending")

    def test_no_audio_source_crop_and_dry_run(self):
        silent = self.base / "silent source.mp4"
        self.run_tool([self.ffmpeg, "-v", "error", "-y", "-i", str(self.source), "-an", "-c:v", "copy", str(silent)])
        folder, revision, plan = self.make_job("no-audio", silent)
        plan["export"]["fit"] = "crop"
        write_json(revision / "edit-plan.json", plan, replace=True)
        command = render(folder, revision, dry_run=True)
        self.assertTrue(command.is_file())
        self.assertFalse((revision / "renders/video.mp4").exists())
        self.select_setup(revision, plan)
        self.select_plan(revision)
        output = render(folder, revision)
        self.assertTrue(probe(output)["has_audio"])
        self.assertAlmostEqual(probe(output)["duration_seconds"], 4, delta=0.08)

    def test_invalid_plan_fails_before_export(self):
        folder, revision, plan = self.make_job("invalid-plan")
        bad = deepcopy(plan)
        bad["clips"][0]["source_out_seconds"] = 10
        with self.assertRaisesRegex(EditorError, "beyond"):
            validate_plan(bad, read_json(folder / "job.json"), probe(self.source))
        bad = deepcopy(plan)
        bad["overlays"] = [{"component": "UnsupportedMotion"}]
        write_json(revision / "edit-plan.json", bad, replace=True)
        with self.assertRaisesRegex(EditorError, "Unsupported overlay"):
            render(folder, revision)
        self.assertFalse((revision / "renders/video.mp4").exists())

    def rgb_at(self, video, second, x, y):
        # Decode RGB before a one-pixel crop to avoid chroma-subsampling rounding.
        data = self.run_tool([self.ffmpeg, "-v", "error", "-ss", str(second), "-i", str(video), "-vf", f"format=rgba,crop=1:1:{x}:{y}", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"])
        return tuple(data[:4])

    def test_image_alpha_video_loop_overlay_timing_and_source_crop(self):
        folder, revision, plan = self.make_job("visual-layers")
        image = folder / "assets/visuals/logo with space.png"
        rgba = b"".join(bytes((0,255,0,255 if x < 20 else 0)) for y in range(40) for x in range(40))
        self.run_tool([self.ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgba", "-video_size", "40x40", "-i", "pipe:0", "-frames:v", "1", str(image)], input=rgba)
        broll = folder / "assets/visuals/broll.mp4"
        self.run_tool([self.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=magenta:size=40x40:rate=30:duration=0.4", "-c:v", "libx264", str(broll)])
        music = folder / "assets/music/bed.wav"
        self.run_tool([self.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=0.7", str(music)])
        plan["audio"]["music"] = {"path": "assets/music/bed.wav", "gain": 0.05, "ducking": True}
        plan["clips"][0]["crop"] = {"x":40,"y":0,"width":80,"height":90}
        plan["overlays"] = [
            {"id":"logo","type":"image","path":"assets/visuals/logo with space.png","timeline_in_frame":15,"timeline_out_frame":45,"x":0,"y":120,"width":40,"height":40,"fit":"contain","opacity":0.5},
            {"id":"broll","type":"video","path":"assets/visuals/broll.mp4","timeline_in_frame":15,"timeline_out_frame":45,"x":80,"y":120,"width":40,"height":40,"fit":"cover","loop":True},
        ]
        write_json(revision / "edit-plan.json", plan, replace=True)
        self.select_setup(revision, plan)
        self.select_plan(revision)
        output = render(folder, revision)
        before = self.rgb_at(output, .2, 5, 130)
        blended = self.rgb_at(output, .8, 5, 130)
        transparent = self.rgb_at(output, .8, 25, 130)
        after = self.rgb_at(output, 1.7, 5, 130)
        self.assertGreater(before[0], 220, before)
        self.assertGreater(blended[1], 90, blended)
        self.assertLess(blended[0], 170, blended)
        self.assertGreater(transparent[0], 220, transparent)
        self.assertLess(transparent[1], 25, transparent)
        self.assertGreater(after[0], 220, after)
        broll_pixel = self.rgb_at(output, 1.2, 90, 130)
        self.assertGreater(broll_pixel[0], 220, broll_pixel)
        self.assertGreater(broll_pixel[2], 220, broll_pixel)
        self.assertGreater(self.rgb_at(output, .2, 70, 70)[0], 220)
        manifest = read_json(revision / "render-manifest.json")
        self.assertEqual(len(manifest["visual_assets"]), 2)

    def test_footage_analysis_is_selected_and_returns_source_proposals(self):
        try:
            import cv2
        except ImportError:
            self.skipTest("Optional vision dependencies not installed")
        from core.adapters.footage import analyze_footage
        folder, revision, plan = self.make_job("footage-signals")
        self.select_setup(revision, plan)
        with self.assertRaisesRegex(EditorError, "not selected"):
            analyze_footage(folder, revision)
        self.select_setup(revision, plan, footage=True)
        write_json(folder / "transcript/cleaned.json", {"segments":[
            {"start":0,"end":1,"text":"Today we explain this complete repeated sentence"},
            {"start":2,"end":3,"text":"Today we explain this complete repeated sentence"},
        ]})
        report_file = analyze_footage(folder, revision, interval=.5, max_samples=12)
        report = read_json(report_file)
        self.assertFalse(report["automatically_applied"])
        self.assertEqual(len(report["samples"]), 8)
        self.assertGreaterEqual(len(report["scene_candidates"]), 2)
        self.assertAlmostEqual(report["scene_candidates"][1]["source_in_seconds"], 2, delta=.5)
        self.assertEqual(len(report["repeated_take_candidates"]), 1)
        self.assertTrue((folder / report["contact_sheet"]).is_file())
        self.assertNotIn("crop", read_json(revision / "edit-plan.json")["clips"][0])
        for sample in report["samples"]:
            crop = sample["crop_proposal"]
            self.assertLessEqual(crop["x"] + crop["width"], sample["image_width"])
            self.assertLessEqual(crop["y"] + crop["height"], sample["image_height"])

    def test_remotion_templates_alpha_and_ffmpeg_integration(self):
        from core.adapters.motion import render_motion
        if not (ROOT / "motion/node_modules/@remotion/renderer").is_dir():
            self.skipTest("Optional Remotion dependencies not installed")
        folder, revision, plan = self.make_job("motion-templates")
        self.select_setup(revision, plan)
        templates = {
            "MetricCard": {"title":"Example metric","value":"42","subtitle":"Synthetic test data","source":"Source: test fixture"},
            "BarChart": {"title":"Example chart","unit":"units","data":[{"label":"A","value":10},{"label":"B","value":20}],"source":"Source: test fixture"},
            "LowerThird": {"title":"Example speaker","subtitle":"Synthetic fixture"},
        }
        assets = []
        for template, content in templates.items():
            name = template.lower()
            spec = {"template":template,"width":320,"height":180,"fps":30,"duration_frames":24,"props":content}
            path = folder / "assets" / f"{name}.json"
            write_json(path, spec)
            asset = render_motion(folder, revision, name, path.relative_to(folder).as_posix())
            assets.append(asset)
            self.assertAlmostEqual(probe(asset)["duration_seconds"], .8, delta=.04)
            self.assertEqual(self.rgb_at(asset, .4, 0, 0)[3], 0)
            self.assertGreater(self.rgb_at(asset, .4, 160, 90)[3], 200)
        plan["overlays"] = [{"id":"metric","type":"video","path":assets[0].relative_to(folder).as_posix(),"timeline_in_frame":15,"timeline_out_frame":39,"x":0,"y":97,"width":160,"height":90,"fit":"contain"}]
        write_json(revision / "edit-plan.json", plan, replace=True)
        self.select_setup(revision, plan)
        self.select_plan(revision)
        output = render(folder, revision)
        self.assertGreater(self.rgb_at(output, .9, 0, 97)[0], 220)
        self.assertLess(self.rgb_at(output, .9, 80, 142)[0], 210)

    def test_kinetic_scene_animates_alpha_progress_and_composites(self):
        from core.adapters.motion import render_motion
        if not (ROOT / "motion/node_modules/@remotion/renderer").is_dir():
            self.skipTest("Optional Remotion dependencies not installed")
        folder, revision, plan = self.make_job("kinetic-scene", profile="kinetic-motion-vi")
        self.assertEqual(mapped_captions(plan, {"segments": [{"start": 0, "end": 4, "text": "No automatic captions"}]}), [])
        self.select_setup(revision, plan)
        assets = []
        for index, transparent in enumerate((False, True)):
            spec = {"template": "KineticScene", "width": 360, "height": 640, "fps": 30, "duration_frames": 90,
                    "props": {"title": "Tập trung làm việc", "emphasis": "Một việc",
                              "theme": "dark" if transparent else "light", "transparent": transparent,
                              "layout": "grid" if transparent else "stack",
                              "cards": [{"label": "Bắt đầu", "detail": "Một bước nhỏ"}], "progress": 1}}
            path = folder / "assets" / f"kinetic-{index}.json"
            write_json(path, spec)
            asset = render_motion(folder, revision, f"kinetic-{index}", path.relative_to(folder).as_posix())
            assets.append(asset)
            self.assertAlmostEqual(probe(asset)["duration_seconds"], 3, delta=.04)
            self.assertEqual(self.rgb_at(asset, 1.5, 0, 0)[3], 0 if transparent else 255)
            self.assertGreater(self.rgb_at(asset, 1.5, 50, 280)[3], 240)
            # Before reveal the card area is background/transparent; later it contains a panel.
            early = self.rgb_at(asset, .1, 50, 280)
            late = self.rgb_at(asset, 1.5, 50, 280)
            self.assertNotEqual(early, late)
            if not transparent:
                # Sample inside the progress track: grey early, orange after filling.
                early_bar = self.rgb_at(asset, .7, 160, 503)
                late_bar = self.rgb_at(asset, 2.5, 160, 503)
                self.assertGreater(late_bar[0] - late_bar[2], 100)
                self.assertLess(abs(early_bar[0] - early_bar[2]), 30)
        plan["overlays"] = [{"id": "kinetic", "type": "video", "path": assets[0].relative_to(folder).as_posix(),
                             "timeline_in_frame": 0, "timeline_out_frame": 90, "x": 0, "y": 0,
                             "width": 160, "height": 284, "fit": "cover"}]
        write_json(revision / "edit-plan.json", plan, replace=True)
        self.select_setup(revision, plan)
        self.select_plan(revision)
        output = render(folder, revision)
        self.assertGreater(self.rgb_at(output, 1.5, 2, 2)[1], 200)
        # After the 3s motion layer the original blue source becomes visible again.
        after = self.rgb_at(output, 3.5, 80, 140)
        self.assertGreater(after[2], after[0] + 100)
        self.assertTrue(probe(output)["has_audio"])

    def test_export_waits_for_user_choices_and_rejects_changed_plan(self):
        folder, revision, plan = self.make_job("user-choice")
        with self.assertRaisesRegex(EditorError, "Waiting for user setup"):
            render(folder, revision)
        self.select_setup(revision, plan)
        with self.assertRaisesRegex(EditorError, "concrete edit proposal"):
            render(folder, revision)
        self.select_plan(revision)
        plan["audio"]["voice_gain"] = 0.8
        write_json(revision / "edit-plan.json", plan, replace=True)
        with self.assertRaisesRegex(EditorError, "changed after"):
            render(folder, revision)
        self.assertFalse((revision / "renders/video.mp4").exists())


if __name__ == "__main__":
    unittest.main()
