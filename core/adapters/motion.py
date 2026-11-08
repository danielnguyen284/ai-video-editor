"""Render validated Remotion templates into immutable alpha video assets."""
import base64
from copy import deepcopy
import shutil
import subprocess

from core.common import EditorError, ROOT, digest, identifier, read_json, timestamp, within, write_json
from core.decisions import require_setup
from core.validation import number, supported_keys

TEMPLATES = ("MetricCard", "BarChart", "LowerThird", "KineticScene", "Keyword", "Illustration", "Points")
# Illustration entry/exit and on-screen camera move; mirrors motion/src/Illustration.tsx.
ILLUSTRATION_MOVES = ("slide-left", "slide-right", "slide-up", "zoom", "wipe", "fade")
ILLUSTRATION_MOTIONS = ("zoom-in", "zoom-out", "pan-left", "pan-right", "none")
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def validate_spec(spec):
    supported_keys(spec, "template width height fps duration_frames props", "motion spec")
    if spec["template"] not in TEMPLATES:
        raise EditorError("Motion template must be one of: " + ", ".join(TEMPLATES) + ".")
    for key in ("width", "height", "fps", "duration_frames"):
        number(spec[key], f"motion {key}", 1, integer=True)
    if spec["width"] % 2 or spec["height"] % 2 or spec["duration_frames"] < 24:
        raise EditorError("Motion dimensions must be even and duration at least 24 frames.")
    content = spec["props"]
    if spec["template"] == "Keyword":
        validate_keyword(spec, content)
        return
    if spec["template"] == "Illustration":
        validate_illustration(spec, content)
        return
    if spec["template"] == "Points":
        validate_points(spec, content)
        return
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


def validate_keyword(spec, content):
    import re
    supported_keys(content, 'title emphasis emphasis_frame font_size color accent enter_frames exit_frames', 'Keyword props')
    for key in ('title', 'emphasis'):
        if key not in content and key == 'emphasis': continue
        value = content.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 48 or '\n' in value or '\r' in value:
            raise EditorError(f'Keyword {key} needs 1-48 characters on one input line.')
    for key in ('color', 'accent'):
        if key in content and (not isinstance(content[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', content[key])):
            raise EditorError(f'Keyword {key} must be a six-digit hex color.')
    size = number(content.get('font_size', min(44, spec['height']//3.5)), 'Keyword font_size', 12)
    if size > 120 or size * (3 if content.get('emphasis') else 1.6) > spec['height']:
        raise EditorError('Keyword font is too large for its layer height.')
    enter = number(content.get('enter_frames', 6), 'Keyword enter_frames', 1, integer=True)
    leave = number(content.get('exit_frames', 5), 'Keyword exit_frames', 1, integer=True)
    emphasis = number(content.get('emphasis_frame', 0), 'Keyword emphasis_frame', integer=True)
    if 'emphasis_frame' in content and not content.get('emphasis'):
        raise EditorError('Keyword emphasis_frame needs emphasis text.')
    if emphasis + enter + leave >= spec['duration_frames']:
        raise EditorError('Keyword needs enough frames for entry, emphasis and exit.')


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


def validate_job_image(image, label):
    if (not isinstance(image, str) or not image.strip() or image.startswith(("/", "\\")) or ":" in image
            or ".." in image.replace("\\", "/").split("/")):
        raise EditorError(f"{label} must be a path inside the job, e.g. assets/illustrations/chart.jpg.")
    if "." + image.rsplit(".", 1)[-1].lower() not in IMAGE_TYPES:
        raise EditorError(f"{label} must be JPEG, PNG or WebP.")


def validate_illustration(spec, content):
    supported_keys(content, "image enter exit motion radius fill enter_frames exit_frames", "Illustration props")
    validate_job_image(content.get("image"), "Illustration image")
    if "fill" in content and not isinstance(content["fill"], bool):
        raise EditorError("Illustration fill must be true or false.")
    for key in ("enter", "exit"):
        if key in content and content[key] not in ILLUSTRATION_MOVES:
            raise EditorError(f"Illustration {key} must be one of: " + ", ".join(ILLUSTRATION_MOVES) + ".")
    if "motion" in content and content["motion"] not in ILLUSTRATION_MOTIONS:
        raise EditorError("Illustration motion must be one of: " + ", ".join(ILLUSTRATION_MOTIONS) + ".")
    if "radius" in content:
        number(content["radius"], "Illustration radius", 0, integer=True)
    enter = number(content.get("enter_frames", 10), "Illustration enter_frames", 1, integer=True)
    leave = number(content.get("exit_frames", 8), "Illustration exit_frames", 1, integer=True)
    if enter + leave >= spec["duration_frames"]:
        raise EditorError("Illustration entry plus exit must be shorter than the asset.")


def validate_points(spec, content):
    import re
    supported_keys(content, "title items big big_at emphasis emphasis_at accent fill icon", "Points props")
    if "fill" in content and not isinstance(content["fill"], bool):
        raise EditorError("Points fill must be true or false.")
    if "icon" in content:
        validate_job_image(content["icon"], "Points icon")

    def text(key, value, limit):
        if not isinstance(value, str) or not value.strip() or len(value) > limit or "\n" in value:
            raise EditorError(f"Points {key} needs 1-{limit} characters on one line.")

    def moment(key, value):
        if number(value, f"Points {key}", 0, integer=True) >= spec["duration_frames"]:
            raise EditorError(f"Points {key} must fall inside the asset.")

    text("title", content.get("title"), 40)
    items = content.get("items", [])
    if not isinstance(items, list) or len(items) > 6:
        raise EditorError("Points takes 0-6 items.")
    for item in items:
        supported_keys(item, "text at", "Points item")
        text("item text", item.get("text"), 36)
        moment("item at", item.get("at"))
    for key, limit in (("big", 10), ("emphasis", 30)):
        if key in content:
            text(key, content[key], limit)
            moment(key + "_at", content.get(key + "_at", 0))
        elif key + "_at" in content:
            raise EditorError(f"Points {key}_at needs {key} text.")
    if not items and "big" not in content and "emphasis" not in content:
        raise EditorError("Points needs items, a big figure or an emphasis line.")
    if "accent" in content and not re.fullmatch(r"#[0-9a-fA-F]{6}", content["accent"]):
        raise EditorError("Points accent must be a six-digit hex color.")


def job_images(spec):
    """Prop names holding job image paths: Illustration image, Points icon."""
    key = {"Illustration": "image", "Points": "icon"}.get(spec["template"])
    return [key] if key and key in spec["props"] else []


def render_inputs(folder, spec):
    """Props as Remotion renders them: a job image becomes a data URL; the saved request keeps its path."""
    if not job_images(spec):
        return spec
    inputs = deepcopy(spec)
    for key in job_images(spec):
        path = within(folder, spec["props"][key])
        if not path.is_file():
            raise EditorError(f"{spec['template']} image not found: {spec['props'][key]}")
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        inputs["props"][key] = f"data:{IMAGE_TYPES[path.suffix.lower()]};base64,{data}"
    return inputs


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
    inputs = render_inputs(folder, spec)
    write_json(request, spec, replace=True)
    rendered = request
    if inputs is not spec:
        rendered = target / "render-input.json"
        write_json(rendered, inputs, replace=True)
    partial = target / "motion.partial.mov"
    with (target / "render.log").open("w", encoding="utf-8") as log:
        result = subprocess.run([node, str(ROOT / "motion/render.mjs"), str(rendered), str(partial)], stdout=log, stderr=subprocess.STDOUT)
    if rendered != request:
        rendered.unlink(missing_ok=True)
    if result.returncode or not partial.is_file():
        tail = "\n".join((target / "render.log").read_text(encoding="utf-8", errors="replace").splitlines()[-12:])
        raise EditorError(f"Remotion failed. See {target / 'render.log'}\n{tail}")
    partial.replace(output)
    write_json(target / "manifest.json", {
        "schema_version": "1.0", "job_id": read_json(folder / "job.json")["job_id"],
        "revision": int(revision.name[1:]), "created_at": timestamp(),
        "renderer": "remotion", "remotion_version": read_json(ROOT / "motion/package.json")["dependencies"]["remotion"],
        "template": spec["template"], "spec": spec, "spec_sha256": digest(request),
        **({"image_sha256": {key: digest(within(folder, spec["props"][key])) for key in job_images(spec)}} if job_images(spec) else {}),
        "output": output.relative_to(folder).as_posix(), "output_sha256": digest(output),
        "codec": "prores", "pixel_format": "yuva444p10le", "alpha": True,
    })
    return output
