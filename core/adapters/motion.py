"""Render validated Remotion templates into immutable alpha video assets."""
import shutil
import subprocess

from core.common import EditorError, ROOT, digest, identifier, read_json, timestamp, within, write_json
from core.decisions import require_setup
from core.validation import number, supported_keys


def validate_spec(spec):
    supported_keys(spec, "template width height fps duration_frames props", "motion spec")
    if spec["template"] not in ("MetricCard", "BarChart", "LowerThird", "KineticScene"):
        raise EditorError("Motion template must be MetricCard, BarChart, LowerThird or KineticScene.")
    for key in ("width", "height", "fps", "duration_frames"):
        number(spec[key], f"motion {key}", 1, integer=True)
    if spec["width"] % 2 or spec["height"] % 2 or spec["duration_frames"] < 24:
        raise EditorError("Motion dimensions must be even and duration at least 24 frames.")
    content = spec["props"]
    if spec["template"] == "KineticScene":
        validate_kinetic(spec, content)
        return
    supported_keys(content, "title value subtitle source unit accent data", "motion props")
    for key in ("title", "value", "subtitle", "source", "unit", "accent"):
        if key in content and not isinstance(content[key], str):
            raise EditorError(f"Motion {key} must be text.")
    if not content.get("title"):
        raise EditorError("Motion title is required.")
    import re
    if "accent" in content and not re.fullmatch(r"#[0-9a-fA-F]{6}", content["accent"]):
        raise EditorError("Motion accent must be a six-digit hex color.")
    if spec["template"] == "MetricCard" and not content.get("value"):
        raise EditorError("MetricCard requires a text value.")
    if spec["template"] == "BarChart":
        data = content.get("data")
        if not isinstance(data, list) or not 1 <= len(data) <= 8:
            raise EditorError("BarChart needs 1-8 data points.")
        for item in data:
            supported_keys(item, "label value", "chart point")
            if not isinstance(item["label"], str) or not item["label"].strip():
                raise EditorError("Bar labels must be nonempty text.")
            number(item["value"], "bar value")


def validate_kinetic(spec, content):
    """Constrain text density and timing to the template's portrait design canvas."""
    import re

    supported_keys(content, "title emphasis subtitle source accent theme transparent layout cards progress", "KineticScene props")
    if spec["width"] < 320 or spec["height"] < 480 or not .5 <= spec["width"] / spec["height"] <= .8:
        raise EditorError("KineticScene needs a portrait canvas, at least 320x480 and width/height between 0.5 and 0.8.")
    if spec["duration_frames"] < spec["fps"] * 2:
        raise EditorError("KineticScene needs at least 2 seconds for reveal and reading time.")
    for key, limit in (("title", 60), ("emphasis", 36), ("subtitle", 90), ("source", 100)):
        if key not in content and key != "title":
            continue
        value = content.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit or "\n" in value or "\r" in value:
            raise EditorError(f"KineticScene {key} needs 1-{limit} characters on one input line.")
    if content.get("theme", "light") not in ("light", "dark"):
        raise EditorError("KineticScene theme must be light or dark.")
    if content.get("layout", "stack") not in ("stack", "grid"):
        raise EditorError("KineticScene layout must be stack or grid.")
    if "transparent" in content and not isinstance(content["transparent"], bool):
        raise EditorError("KineticScene transparent must be true or false.")
    if "accent" in content and (not isinstance(content["accent"], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", content["accent"])):
        raise EditorError("KineticScene accent must be a six-digit hex color.")
    if "progress" in content:
        if number(content["progress"], "KineticScene progress") > 1:
            raise EditorError("KineticScene progress must be between 0 and 1.")
    if "cards" in content:
        if not isinstance(content["cards"], list) or not 1 <= len(content["cards"]) <= 4:
            raise EditorError("KineticScene cards must contain 1-4 items when supplied.")
        # Stack cards have less height; grid cards are narrower.
        limits = (("label", 24), ("detail", 38)) if content.get("layout") == "grid" else (("label", 36), ("detail", 48))
        for card in content["cards"]:
            supported_keys(card, "label detail", "KineticScene card")
            for key, limit in limits:
                if key == "detail" and key not in card:
                    continue
                value = card.get(key)
                if not isinstance(value, str) or not value.strip() or len(value) > limit or "\n" in value or "\r" in value:
                    raise EditorError(f"KineticScene card {key} needs 1-{limit} characters on one input line.")


def render_motion(folder, revision, name, spec_path):
    require_setup(revision)
    name = identifier(name)
    source = within(folder, spec_path)
    spec = read_json(source)
    validate_spec(spec)
    node = shutil.which("node")
    if not node or not (ROOT / "motion/node_modules/@remotion/renderer").is_dir():
        raise EditorError("Install motion tools: run npm.cmd ci in motion/ (Node.js is required).")
    target = folder / "assets/visuals" / name
    output = target / "motion.mov"
    if output.exists() or (target / "manifest.json").exists():
        raise EditorError("Motion asset already exists. Choose a new name to preserve the previous asset.")
    target.mkdir(parents=True, exist_ok=True)
    request = target / "request.json"
    write_json(request, spec, replace=True)
    partial = target / "motion.partial.mov"
    with (target / "render.log").open("w", encoding="utf-8") as log:
        result = subprocess.run([node, str(ROOT / "motion/render.mjs"), str(request), str(partial)], stdout=log, stderr=subprocess.STDOUT)
    if result.returncode or not partial.is_file():
        tail = "\n".join((target / "render.log").read_text(encoding="utf-8", errors="replace").splitlines()[-12:])
        raise EditorError(f"Remotion failed. See {target / 'render.log'}\n{tail}")
    partial.replace(output)
    write_json(target / "manifest.json", {
        "schema_version": "1.0", "job_id": read_json(folder / "job.json")["job_id"],
        "revision": int(revision.name[1:]), "created_at": timestamp(),
        "renderer": "remotion", "remotion_version": read_json(ROOT / "motion/package.json")["dependencies"]["remotion"],
        "template": spec["template"], "spec": spec, "spec_sha256": digest(request),
        "output": output.relative_to(folder).as_posix(), "output_sha256": digest(output),
        "codec": "prores", "pixel_format": "yuva444p10le", "alpha": True,
    })
    return output
