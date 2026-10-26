from copy import deepcopy
import unittest

from core.adapters.motion import validate_spec
from core.common import EditorError, resolve_profile


class KineticSpecTests(unittest.TestCase):
    def spec(self):
        return {"template": "KineticScene", "width": 720, "height": 1280,
                "fps": 30, "duration_frames": 90,
                "props": {"title": "Tập trung", "cards": [{"label": "Một việc"}], "progress": 1}}

    def test_valid_scene_can_be_text_only_or_transparent_grid(self):
        spec = self.spec()
        validate_spec(spec)
        spec["props"].pop("cards")
        validate_spec(spec)
        spec["props"].update(transparent=True, layout="grid", theme="dark", accent="#33CCAA",
                             cards=[{"label": "Bước 1", "detail": "Thực hiện"}])
        validate_spec(spec)

    def test_rejects_invalid_timing_density_and_ignored_effects(self):
        variants = [
            {"duration_frames": 59}, {"fps": 60, "duration_frames": 90},
            {"width": 1280, "height": 720}, {"width": 160, "height": 284},
        ]
        for change in variants:
            with self.subTest(change=change), self.assertRaises(EditorError):
                validate_spec({**self.spec(), **change})
        changes = [{"title": ""}, {"title": "W" * 61}, {"title": "A\nB"},
                   {"cards": []}, {"cards": [{"label": "Test"}] * 5},
                   {"cards": [{"label": "X", "image": "ignored.png"}]},
                   {"layout": "grid", "cards": [{"label": "W" * 25}]},
                   {"cards": [{"label": "X", "detail": "W" * 49}]},
                   {"progress": -1}, {"progress": 1.1}, {"progress": True}, {"progress": float("nan")},
                   {"transparent": "true"}, {"theme": "neon"}, {"accent": 123},
                   {"camera_zoom": 2}, {"data": []}]
        for change in changes:
            spec = deepcopy(self.spec())
            spec["props"].update(change)
            with self.subTest(change=change), self.assertRaises(EditorError):
                validate_spec(spec)

    def test_new_profiles_resolve_exact_versions_and_separate_text_defaults(self):
        for domain in ("general", "finance"):
            for style in ("talking-head-pro", "kinetic-motion"):
                profile = f"{style}-vi" if domain == "general" else f"finance-{style}-vi"
                resolved = resolve_profile(profile)
                self.assertEqual([s["id"] for s in resolved["skills"]], [f"style/{style}", f"domain/{domain}"])
                captions = resolved["settings"]["captions"]
                self.assertEqual("items" in captions, style == "kinetic-motion")
                if style == "kinetic-motion":
                    self.assertEqual(captions["items"], [])


if __name__ == "__main__":
    unittest.main()
