"""FFmpeg visual layers with explicit output timing and silent B-roll."""
import json
import subprocess

from core.common import EditorError, digest, executable, identifier, within
from core.validation import number, supported_keys


def validate_overlays(plan):
    layers = plan.get("overlays", [])
    if not isinstance(layers, list):
        raise EditorError("overlays must be an array.")
    ids = set()
    for layer in layers:
        supported_keys(layer, "id type path timeline_in_frame timeline_out_frame x y width height fit opacity source_in_seconds loop", "overlay")
        identifier(layer["id"])
        if layer["id"] in ids:
            raise EditorError("Overlay IDs must be unique.")
        ids.add(layer["id"])
        if layer["type"] not in ("image", "video"):
            raise EditorError("Overlay type must be image or video. Render Remotion to an asset first.")
        start = number(layer["timeline_in_frame"], "overlay start", integer=True)
        end = number(layer["timeline_out_frame"], "overlay end", integer=True)
        if not start < end <= plan["duration_frames"]:
            raise EditorError("Overlay timing must stay inside the output timeline.")
        for key in ("x", "y"):
            number(layer[key], f"overlay {key}", integer=True)
        for key in ("width", "height"):
            number(layer[key], f"overlay {key}", 1, integer=True)
        if layer["x"] + layer["width"] > plan["export"]["width"] or layer["y"] + layer["height"] > plan["export"]["height"]:
            raise EditorError("Overlay rectangle extends outside output dimensions.")
        if layer["fit"] not in ("contain", "cover", "stretch"):
            raise EditorError("Overlay fit must be contain, cover or stretch.")
        if number(layer.get("opacity", 1), "overlay opacity") > 1:
            raise EditorError("Overlay opacity must be between 0 and 1.")
        number(layer.get("source_in_seconds", 0), "overlay source start")
        if not isinstance(layer.get("loop", False), bool):
            raise EditorError("Overlay loop must be true or false.")
        if layer["type"] == "image" and (layer.get("source_in_seconds", 0) or layer.get("loop", False)):
            raise EditorError("Image layers do not use source_in_seconds or loop.")


def visual_info(path):
    result = subprocess.run([executable("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise EditorError(f"Cannot inspect visual asset: {path}\n{result.stderr.strip()}")
    info = json.loads(result.stdout)
    video = next((item for item in info["streams"] if item.get("codec_type") == "video"), None)
    if video is None:
        raise EditorError(f"Visual asset has no video/image stream: {path}")
    raw_duration = video.get("duration", info.get("format", {}).get("duration"))
    return {"codec": video["codec_name"], "duration": float(raw_duration) if raw_duration not in (None, "N/A") else None}


def composite_overlays(plan, folder, command, filters, first_input, base="cutv"):
    manifest = []
    fps = plan["fps"]
    for i, layer in enumerate(plan.get("overlays", [])):
        path = within(folder, layer["path"])
        if not path.is_file():
            raise EditorError(f"Missing visual asset: {path}")
        info = visual_info(path)
        start, end = layer["timeline_in_frame"] / fps, layer["timeline_out_frame"] / fps
        duration = end - start
        source_in = layer.get("source_in_seconds", 0)
        if layer["type"] == "image":
            if info["codec"] not in ("png", "mjpeg", "webp", "bmp", "tiff"):
                raise EditorError("Image overlay must be a static PNG/JPEG/WebP/BMP/TIFF asset.")
            command += ["-loop", "1", "-framerate", str(fps), "-i", str(path)]
        else:
            if info["duration"] is None or source_in >= info["duration"]:
                raise EditorError("Video overlay needs a finite duration and a valid source start.")
            if not layer.get("loop", False) and duration + source_in > info["duration"] + 0.001:
                raise EditorError("Video overlay is too short. Shorten the layer or explicitly select loop=true.")
            if layer.get("loop", False):
                command += ["-stream_loop", "-1"]
            # Native VP8/VP9 decoders may drop alpha. libvpx retains it.
            if info["codec"] in ("vp8", "vp9"):
                command += ["-c:v", "libvpx-vp9" if info["codec"] == "vp9" else "libvpx"]
            command += ["-i", str(path)]
        w, h = layer["width"], layer["height"]
        if layer["fit"] == "contain":
            sizing = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black@0"
        elif layer["fit"] == "cover":
            sizing = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
        else:
            sizing = f"scale={w}:{h}"
        label = f"layer{i}"
        output = f"visual{i}"
        filters.append(f"[{first_input+i}:v:0]trim=start={source_in:.9f}:duration={duration:.9f},setpts=PTS-STARTPTS,fps={fps},format=rgba,{sizing},setsar=1,colorchannelmixer=aa={layer.get('opacity',1)},setpts=PTS+{start:.9f}/TB[{label}]")
        filters.append(f"[{base}][{label}]overlay=x={layer['x']}:y={layer['y']}:enable='gte(t,{start:.9f})*lt(t,{end:.9f})':eof_action=pass:repeatlast=0:format=auto[{output}]")
        base = output
        manifest.append({"id": layer["id"], "path": layer["path"], "sha256": digest(path), "type": layer["type"]})
    return base, manifest
