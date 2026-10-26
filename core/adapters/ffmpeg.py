from __future__ import annotations

import json
import math
from pathlib import Path
import re
import subprocess
import textwrap

from core.common import EditorError, digest, executable, read_json, timestamp, within, write_json
from core.decisions import require_render_choices
from core.validation import number, supported_keys
from core.adapters.visuals import composite_overlays, validate_overlays


def execute(command, log, cwd=None):
    with Path(log).open("w", encoding="utf-8") as output:
        result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, shell=False)
    if result.returncode:
        tail = "\n".join(Path(log).read_text(encoding="utf-8", errors="replace").splitlines()[-12:])
        raise EditorError(f"FFmpeg failed. Log: {log}\n{tail}")


def probe(path):
    result = subprocess.run([
        executable("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
    if result.returncode:
        raise EditorError(f"Cannot read media: {path}\n{result.stderr.strip()}")
    data = json.loads(result.stdout)
    video = next((s for s in data["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    duration = float((video or {}).get("duration", data.get("format", {}).get("duration", 0)))
    if not math.isfinite(duration) or duration <= 0:
        raise EditorError(f"No finite media duration: {path}")
    width, height = (video or {}).get("width"), (video or {}).get("height")
    rotation = next((item.get("rotation", 0) for item in (video or {}).get("side_data_list", []) if "rotation" in item), 0)
    if abs(round(float(rotation))) % 180 == 90:
        width, height = height, width
    return {
        "duration_seconds": duration, "has_video": video is not None, "has_audio": audio is not None,
        "width": width, "height": height,
    }


def validate_plan(plan, job, media):
    supported_keys(plan, "schema_version job_id revision config_ref fps duration_frames export clips captions audio overlays notes", "plan")
    if plan["schema_version"] != "1.0" or plan["job_id"] != job["job_id"]:
        raise EditorError("Plan schema/job ID does not match the job.")
    number(plan["revision"], "revision", 1, integer=True)
    fps = number(plan["fps"], "fps", 1, integer=True)
    export = plan["export"]
    supported_keys(export, "preset width height fps fit", "export")
    for key in ("width", "height"):
        value = number(export[key], key, 2, integer=True)
        if value % 2:
            raise EditorError(f"{key} must be even for H.264 yuv420p.")
    if export["fps"] != fps or export["fit"] not in ("pad", "crop"):
        raise EditorError("Export fps must match plan fps; fit must be pad or crop.")
    if not plan["clips"]:
        raise EditorError("Plan must contain at least one clip.")
    asset_ids = {asset["asset_id"] for asset in job["assets"]}
    cursor, ids = 0, set()
    for clip in plan["clips"]:
        supported_keys(clip, "clip_id asset_id source_in_seconds source_out_seconds timeline_in_frame timeline_out_frame playback_rate crop", "clip")
        if clip["clip_id"] in ids:
            raise EditorError("clip_id must be unique inside a revision.")
        ids.add(clip["clip_id"])
        if clip["asset_id"] not in asset_ids or clip["asset_id"] != job["assets"][0]["asset_id"]:
            raise EditorError("The starter renderer supports one input video asset per job.")
        if clip["playback_rate"] != 1.0:
            raise EditorError("Playback speed changes are not implemented in the starter renderer.")
        start = number(clip["source_in_seconds"], "source_in_seconds")
        end = number(clip["source_out_seconds"], "source_out_seconds")
        tin = number(clip["timeline_in_frame"], "timeline_in_frame", integer=True)
        tout = number(clip["timeline_out_frame"], "timeline_out_frame", integer=True)
        if end <= start or end > media["duration_seconds"] + 0.001:
            raise EditorError("Source range is empty or extends beyond the input video.")
        if tin != cursor or tout <= tin:
            raise EditorError("Clips must form a contiguous, ordered timeline starting at frame 0.")
        if abs((end - start) * fps - (tout - tin)) > 0.51:
            raise EditorError("Source duration and timeline duration differ by more than half a frame.")
        if "crop" in clip:
            crop = clip["crop"]
            supported_keys(crop, "x y width height", "clip crop")
            for key in ("x", "y", "width", "height"):
                number(crop[key], f"crop {key}", 1 if key in ("width", "height") else 0, integer=True)
            if crop["x"] + crop["width"] > media["width"] or crop["y"] + crop["height"] > media["height"]:
                raise EditorError("Clip crop extends beyond the source image.")
        cursor = tout
    if number(plan["duration_frames"], "duration_frames", 1, integer=True) != cursor:
        raise EditorError("duration_frames must equal the end of the last clip.")
    validate_overlays(plan)
    caps = plan["captions"]
    supported_keys(caps, "enabled transcript_ref font_name font_size margin_v max_chars max_lines items", "captions")
    if not isinstance(caps["enabled"], bool):
        raise EditorError("captions.enabled must be true or false.")
    if not re.fullmatch(r"[\w -]+", caps["font_name"]):
        raise EditorError("Font name may contain letters, numbers, spaces and hyphens.")
    for key in ("font_size", "max_chars", "max_lines"):
        number(caps[key], f"captions.{key}", 1, integer=True)
    number(caps["margin_v"], "captions.margin_v", integer=True)
    audio = plan["audio"]
    supported_keys(audio, "voice_gain music", "audio")
    number(audio["voice_gain"], "voice_gain")
    if audio.get("music"):
        supported_keys(audio["music"], "path gain ducking", "music")
        number(audio["music"]["gain"], "music gain")
        if not isinstance(audio["music"]["ducking"], bool):
            raise EditorError("music.ducking must be true or false.")


def mapped_captions(plan, transcript):
    """Map source words into the output timeline, including reordered/repeated takes."""
    caps, fps = plan["captions"], plan["fps"]
    if "items" in caps:
        result = []
        for item in caps["items"]:
            supported_keys(item, "timeline_in_frame timeline_out_frame text", "caption item")
            start = number(item["timeline_in_frame"], "caption start", integer=True)
            end = number(item["timeline_out_frame"], "caption end", integer=True)
            if not 0 <= start < end <= plan["duration_frames"]:
                raise EditorError("Caption item must stay inside the output timeline.")
            result.append((start / fps, end / fps, str(item["text"])))
        return result
    results = []
    limit = caps["max_chars"] * caps["max_lines"]
    for clip in plan["clips"]:
        source_in, source_out = clip["source_in_seconds"], clip["source_out_seconds"]
        offset = clip["timeline_in_frame"] / fps - source_in
        group = []

        def flush():
            if group:
                results.append((max(source_in, group[0][0]) + offset, min(source_out, group[-1][1]) + offset, " ".join(w[2] for w in group)))
                group.clear()

        for segment in transcript.get("segments", []):
            if segment["end"] <= source_in or segment["start"] >= source_out:
                continue
            if not segment.get("words"):
                flush()
                if segment["start"] < source_in - 0.001 or segment["end"] > source_out + 0.001:
                    raise EditorError("A cut crosses a transcript segment without word timestamps. Supply caption items or word timestamps.")
                results.append((segment["start"] + offset, segment["end"] + offset, segment["text"]))
                continue
            for word in segment["words"]:
                mid = (word["start"] + word["end"]) / 2
                if not source_in <= mid < source_out or word["end"] <= word["start"]:
                    continue
                text = word["text"].strip()
                candidate = " ".join([*(w[2] for w in group), text])
                lines = textwrap.wrap(candidate, width=caps["max_chars"], break_long_words=False, break_on_hyphens=False)
                if group and (len(candidate) > limit or len(lines) > caps["max_lines"] or word["end"] - group[0][0] > 2.5):
                    flush()
                group.append((word["start"], word["end"], text))
            flush()
        flush()
    return results


def ass_time(seconds):
    total = max(0, round(seconds * 100))
    return f"{total // 360000}:{total // 6000 % 60:02d}:{total // 100 % 60:02d}.{total % 100:02d}"


def write_ass(path, plan, items):
    caps, export = plan["captions"], plan["export"]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {export['width']}
PlayResY: {export['height']}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{caps['font_name']},{caps['font_size']},&H00FFFFFF,&H0000FFFF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,1,3,1,2,70,70,{caps['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for start, end, text in items:
        safe = str(text).replace("\\", " ").replace("{", "(").replace("}", ")")
        safe = " ".join(safe.split())
        wrapped = textwrap.wrap(safe, width=caps["max_chars"], break_long_words=False, break_on_hyphens=False)
        if len(wrapped) > caps["max_lines"]:
            raise EditorError("Caption exceeds max_lines. Split its words/items into shorter cues.")
        safe = r"\N".join(wrapped)
        if end > start and safe:
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{safe}\n")
    Path(path).write_text("".join(lines), encoding="utf-8")


def render(folder, revision, *, dry_run=False):
    job = read_json(folder / "job.json")
    plan_file = revision / "edit-plan.json"
    plan = read_json(plan_file)
    if plan.get("config_ref") != "resolved-config.json":
        raise EditorError("config_ref must reference the revision's resolved-config.json.")
    config_file = revision / "resolved-config.json"
    config = read_json(config_file)
    if plan["revision"] != int(revision.name[1:]) or config["revision"] != plan["revision"] or config["job_id"] != job["job_id"]:
        raise EditorError("Plan/config revision does not match the revision folder.")
    source = within(folder, job["assets"][0]["path"])
    media = probe(source)
    validate_plan(plan, job, media)
    from core.editor_service import check_render_locks
    check_render_locks(folder, plan)
    if not dry_run:
        require_render_choices(revision)
    render_dir = revision / "renders"
    output = render_dir / "video.mp4"
    if output.exists() or (revision / "render-manifest.json").exists():
        raise EditorError("This revision was already rendered. Create a new revision to preserve the previous video.")
    command = [executable("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-i", str(source)]
    audio_input = "0:a:0"
    next_input = 1
    if not media["has_audio"]:
        command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        audio_input = "1:a:0"
        next_input += 1
    music = plan["audio"].get("music")
    if music:
        music_file = within(folder, music["path"])
        if not music_file.is_file() or not probe(music_file)["has_audio"]:
            raise EditorError("Music file must contain an audio stream.")
        command += ["-stream_loop", "-1", "-i", str(music_file)]
    fps, export = plan["fps"], plan["export"]
    width, height = export["width"], export["height"]
    size = f"scale={width}:{height}:force_original_aspect_ratio="
    if export["fit"] == "pad":
        size += f"decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
    else:
        size += f"increase:force_divisible_by=2,crop={width}:{height}"
    filters, concat = [], []
    for i, clip in enumerate(plan["clips"]):
        start, end = clip["source_in_seconds"], clip["source_out_seconds"]
        frames = clip["timeline_out_frame"] - clip["timeline_in_frame"]
        duration = frames / fps
        crop = clip.get("crop")
        source_crop = f"crop={crop['width']}:{crop['height']}:{crop['x']}:{crop['y']}," if crop else ""
        filters.append(f"[0:v:0]trim=start={start:.9f}:end={end:.9f},setpts=PTS-STARTPTS,fps={fps},{source_crop}{size},setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration={1/fps:.9f},trim=end_frame={frames}[v{i}]")
        audio_start = start if media["has_audio"] else 0
        filters.append(f"[{audio_input}]atrim=start={audio_start:.9f}:duration={duration:.9f},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={duration:.9f}[a{i}]")
        concat += [f"[v{i}]", f"[a{i}]"]
    filters.append("".join(concat) + f"concat=n={len(plan['clips'])}:v=1:a=1[cutv][cuta]")
    base_video, visual_assets = composite_overlays(plan, folder, command, filters, next_input + (1 if music else 0))
    if plan["captions"]["enabled"]:
        caps = plan["captions"]
        transcript = {} if "items" in caps else read_json(within(folder, caps["transcript_ref"]))
        if transcript and (transcript.get("job_id") != job["job_id"] or transcript.get("asset_id") != job["assets"][0]["asset_id"]):
            raise EditorError("Transcript job/asset does not match the video.")
        items = mapped_captions(plan, transcript)
        if not items:
            raise EditorError("Captions are enabled but no cues were produced. Disable captions or supply timed text.")
        write_ass(revision / "captions.ass", plan, items)
        filters.append(f"[{base_video}]subtitles=filename=captions.ass[vout]")
    else:
        filters.append(f"[{base_video}]null[vout]")
    filters.append(f"[cuta]volume={plan['audio']['voice_gain']}[voice]")
    if music:
        filters.append(f"[{next_input}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={music['gain']}[music]")
        if music["ducking"]:
            filters += ["[voice]asplit=2[keepvoice][side]", "[music][side]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[ducked]", "[keepvoice][ducked]amix=inputs=2:duration=first:normalize=0[aout]"]
        else:
            filters.append("[voice][music]amix=inputs=2:duration=first:normalize=0[aout]")
    else:
        filters.append("[voice]anull[aout]")
    (revision / "filtergraph.txt").write_text(";\n".join(filters), encoding="utf-8")
    duration = plan["duration_frames"] / fps
    command += [
        "-/filter_complex", "filtergraph.txt", "-map", "[vout]", "-map", "[aout]",
        "-frames:v", str(plan["duration_frames"]), "-t", f"{duration:.9f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "renders/video.partial.mp4",
    ]
    write_json(revision / "ffmpeg-command.json", {"cwd": str(revision), "argv": command}, replace=True)
    if dry_run:
        return revision / "ffmpeg-command.json"
    render_dir.mkdir(exist_ok=True)
    write_json(revision / "render-plan.json", plan, replace=True)
    execute(command, revision / "ffmpeg.log", cwd=revision)
    (render_dir / "video.partial.mp4").replace(output)
    version = subprocess.run([executable("ffmpeg"), "-version"], capture_output=True, text=True, encoding="utf-8").stdout.splitlines()[0]
    write_json(revision / "render-manifest.json", {
        "schema_version": "1.0", "job_id": job["job_id"], "revision": plan["revision"],
        "status": "exported-awaiting-user-feedback", "created_at": timestamp(),
        "plan_sha256": digest(plan_file), "config_sha256": digest(config_file),
        "ffmpeg_version": version, "output": "renders/video.mp4",
        "duration_frames": plan["duration_frames"], "export": export,
        "visual_assets": visual_assets,
    })
    return output
