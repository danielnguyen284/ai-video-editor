from __future__ import annotations

import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import textwrap

from core.common import EXPORT_FITS, EditorError, ROOT, digest, executable, identifier, read_json, timestamp, within, write_json
from core.decisions import require_render_choices
from core.validation import number, supported_keys
from core.adapters.camera import validate_zoom, zoom_filter
from core.adapters.visuals import composite_overlays, validate_overlays

# Constant per-clip speed. atempo keeps the voice pitch.
MIN_RATE, MAX_RATE = 0.5, 2.0
MAX_SFX = 200
# Voice cleanup before voice_gain. "strong" adds a gentle gate that lowers the
# room by 12 dB only between phrases; very quiet speech can be softened too.
DENOISE = {
    "light": "highpass=f=70,afftdn=nr=12:nf=-50:tn=1",
    "strong": "highpass=f=80,afftdn=nr=20:nf=-50:tn=1,agate=threshold=0.015:ratio=2:range=0.25:attack=10:release=250",
}
# Integrated loudness target of the final mix (TikTok plays around -14 LUFS).
MIN_LUFS, MAX_LUFS = -24, -9
# Picture transition into a clip, centred on the cut; the voice still cuts hard.
TRANSITIONS = {"fade": "fade", "flash": "fadewhite", "slide-left": "slideleft", "slide-right": "slideright",
               "slide-up": "slideup", "wipe-left": "wipeleft", "whip": "hblur"}
MIN_TRANSITION_FRAMES, MAX_TRANSITION_FRAMES = 2, 30


def transition_split(frames):
    """Frames of a transition before and after its cut."""
    return frames // 2, frames - frames // 2


def clip_handles(plan):
    """Extra picture frames each clip needs before its start and after its end for transitions."""
    handles = [[0, 0] for _ in plan["clips"]]
    for i, clip in enumerate(plan["clips"]):
        if i and clip.get("transition"):
            before, after = transition_split(clip["transition"]["frames"])
            handles[i][0], handles[i - 1][1] = before, after
    return handles


def join_with_transitions(plan, filters, audio_parts):
    """[cutv]/[cuta]: hard-cut runs are concatenated and runs meet in an xfade centred on the cut.

    Each clip picture [vN] already carries its handles, so the xfade output keeps
    the plan's exact frame count; the voice is concatenated without overlap.
    """
    fps, runs = plan["fps"], [[0]]
    for i in range(1, len(plan["clips"])):
        if plan["clips"][i].get("transition"):
            runs.append([i])
        else:
            runs[-1].append(i)
    labels = []
    for r, run in enumerate(runs):
        if len(run) == 1:
            labels.append(f"v{run[0]}")
        else:
            filters.append("".join(f"[v{i}]" for i in run) + f"concat=n={len(run)}:v=1:a=0,settb=1/{fps}[run{r}]")
            labels.append(f"run{r}")
    current = labels[0]
    for r in range(1, len(runs)):
        clip = plan["clips"][runs[r][0]]
        before, after = transition_split(clip["transition"]["frames"])
        joined = "cutv" if r == len(runs) - 1 else f"joined{r}"
        filters.append(f"[{current}][{labels[r]}]xfade=transition={TRANSITIONS[clip['transition']['type']]}:"
                       f"duration={(before + after) / fps:.9f}:offset={(clip['timeline_in_frame'] - before) / fps:.9f}[{joined}]")
        current = joined
    filters.append("".join(audio_parts) + f"concat=n={len(audio_parts)}:v=0:a=1[cuta]")


def validate_transitions(plan, media):
    fps, clips = plan["fps"], plan["clips"]
    for i, clip in enumerate(clips):
        if "transition" not in clip:
            continue
        item = clip["transition"]
        supported_keys(item, "type frames", "clip transition")
        if item["type"] not in TRANSITIONS:
            raise EditorError("Transition type must be one of: " + ", ".join(TRANSITIONS) + ".")
        frames = number(item["frames"], "transition frames", MIN_TRANSITION_FRAMES, integer=True)
        if frames > MAX_TRANSITION_FRAMES:
            raise EditorError(f"A transition lasts {MIN_TRANSITION_FRAMES}-{MAX_TRANSITION_FRAMES} frames.")
        if i == 0:
            raise EditorError("The first clip cannot have a transition into it.")
    handles = clip_handles(plan)
    for i, clip in enumerate(clips):
        before, after = handles[i]
        # The clip's own frames used by the transition into it and the one out of it.
        opening = transition_split(clip["transition"]["frames"])[1] if i and clip.get("transition") else 0
        closing = transition_split(clips[i + 1]["transition"]["frames"])[0] if i + 1 < len(clips) and clips[i + 1].get("transition") else 0
        if opening + closing > clip["timeline_out_frame"] - clip["timeline_in_frame"]:
            raise EditorError(f"Transitions around {clip['clip_id']} overlap; shorten them or the neighbouring cuts.")
        rate = clip.get("playback_rate", 1.0)
        if clip["source_in_seconds"] - before * rate / fps < -0.001 or clip["source_out_seconds"] + after * rate / fps > media["duration_seconds"] + 0.001:
            raise EditorError(f"Transition at {clip['clip_id']} needs picture beyond the input video; shorten it or move the cut.")


def output_seconds(clip, source_seconds, fps):
    """Output time of a source instant inside a clip, at the clip's speed."""
    return clip["timeline_in_frame"] / fps + (source_seconds - clip["source_in_seconds"]) / clip.get("playback_rate", 1.0)


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
    if export["fps"] != fps or export["fit"] not in EXPORT_FITS:
        raise EditorError("Export fps must match plan fps; fit must be pad, crop or blur.")
    if not plan["clips"]:
        raise EditorError("Plan must contain at least one clip.")
    asset_ids = {asset["asset_id"] for asset in job["assets"]}
    cursor, ids = 0, set()
    for clip in plan["clips"]:
        supported_keys(clip, "clip_id asset_id source_in_seconds source_out_seconds timeline_in_frame timeline_out_frame playback_rate crop zoom transition", "clip")
        if clip["clip_id"] in ids:
            raise EditorError("clip_id must be unique inside a revision.")
        ids.add(clip["clip_id"])
        if clip["asset_id"] not in asset_ids or clip["asset_id"] != job["assets"][0]["asset_id"]:
            raise EditorError("The starter renderer supports one input video asset per job.")
        rate = number(clip["playback_rate"], "playback_rate")
        if not MIN_RATE <= rate <= MAX_RATE:
            raise EditorError(f"playback_rate must be between {MIN_RATE:g} and {MAX_RATE:g}.")
        start = number(clip["source_in_seconds"], "source_in_seconds")
        end = number(clip["source_out_seconds"], "source_out_seconds")
        tin = number(clip["timeline_in_frame"], "timeline_in_frame", integer=True)
        tout = number(clip["timeline_out_frame"], "timeline_out_frame", integer=True)
        if end <= start or end > media["duration_seconds"] + 0.001:
            raise EditorError("Source range is empty or extends beyond the input video.")
        if tin != cursor or tout <= tin:
            raise EditorError("Clips must form a contiguous, ordered timeline starting at frame 0.")
        if abs((end - start) * fps / rate - (tout - tin)) > 0.51:
            raise EditorError("Source duration divided by playback_rate and timeline duration differ by more than half a frame.")
        if "zoom" in clip:
            validate_zoom(clip["zoom"], media["duration_seconds"])
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
    validate_transitions(plan, media)
    validate_overlays(plan)
    caps = plan["captions"]
    supported_keys(caps, "enabled transcript_ref font_name font_size margin_v max_chars max_lines items outline_width", "captions")
    if not isinstance(caps["enabled"], bool):
        raise EditorError("captions.enabled must be true or false.")
    if not re.fullmatch(r"[\w -]+", caps["font_name"]):
        raise EditorError("Font name may contain letters, numbers, spaces and hyphens.")
    for key in ("font_size", "max_chars", "max_lines"):
        number(caps[key], f"captions.{key}", 1, integer=True)
    number(caps["margin_v"], "captions.margin_v", integer=True)
    if 'outline_width' in caps and number(caps['outline_width'], 'captions.outline_width') > 6:
        raise EditorError('Caption outline_width must be between 0 and 6 pixels.')
    audio = plan["audio"]
    supported_keys(audio, "voice_gain music sfx denoise loudness_lufs", "audio")
    number(audio["voice_gain"], "voice_gain")
    if "denoise" in audio and audio["denoise"] not in DENOISE:
        raise EditorError("audio.denoise must be light or strong; omit it for no cleanup.")
    if "loudness_lufs" in audio and not MIN_LUFS <= number(audio["loudness_lufs"], "loudness_lufs", MIN_LUFS) <= MAX_LUFS:
        raise EditorError(f"audio.loudness_lufs must be between {MIN_LUFS} and {MAX_LUFS}.")
    if audio.get("music"):
        supported_keys(audio["music"], "path gain ducking", "music")
        number(audio["music"]["gain"], "music gain")
        if not isinstance(audio["music"]["ducking"], bool):
            raise EditorError("music.ducking must be true or false.")
    validate_sfx(audio.get("sfx", []), plan["duration_frames"])


def validate_sfx(items, duration_frames):
    """Timed one-shot sounds on the output timeline, mixed after music ducking."""
    if not isinstance(items, list) or len(items) > MAX_SFX:
        raise EditorError(f"audio.sfx must be an array of at most {MAX_SFX} sounds.")
    ids = set()
    for item in items:
        supported_keys(item, "id path timeline_in_frame timeline_out_frame gain", "sfx")
        identifier(item["id"])
        if item["id"] in ids:
            raise EditorError("SFX IDs must be unique.")
        ids.add(item["id"])
        if not isinstance(item["path"], str) or not item["path"]:
            raise EditorError("SFX needs a job-relative audio path.")
        start = number(item["timeline_in_frame"], "sfx start", integer=True)
        end = number(item["timeline_out_frame"], "sfx end", integer=True)
        if not start < end <= duration_frames:
            raise EditorError("SFX timing must stay inside the output timeline.")
        if number(item["gain"], "sfx gain") > 4:
            raise EditorError("SFX gain must be between 0 and 4.")


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
        rate = clip.get("playback_rate", 1.0)
        out = lambda seconds: output_seconds(clip, seconds, fps)
        group = []

        def flush():
            if group:
                results.append((out(max(source_in, group[0][0])), out(min(source_out, group[-1][1])), " ".join(w[2] for w in group)))
                group.clear()

        for segment in transcript.get("segments", []):
            if segment["end"] <= source_in or segment["start"] >= source_out:
                continue
            if not segment.get("words"):
                flush()
                if segment["start"] < source_in - 0.001 or segment["end"] > source_out + 0.001:
                    raise EditorError("A cut crosses a transcript segment without word timestamps. Supply caption items or word timestamps.")
                results.append((out(segment["start"]), out(segment["end"]), segment["text"]))
                continue
            for word in segment["words"]:
                mid = (word["start"] + word["end"]) / 2
                if not source_in <= mid < source_out or word["end"] <= word["start"]:
                    continue
                text = word["text"].strip()
                candidate = " ".join([*(w[2] for w in group), text])
                lines = textwrap.wrap(candidate, width=caps["max_chars"], break_long_words=False, break_on_hyphens=False)
                if group and (len(candidate) > limit or len(lines) > caps["max_lines"] or (word["end"] - group[0][0]) / rate > 2.5):
                    flush()
                group.append((word["start"], word["end"], text))
            flush()
        flush()
    return results


def ass_time(seconds):
    total = max(0, round(seconds * 100))
    return f"{total // 360000}:{total // 6000 % 60:02d}:{total // 100 % 60:02d}.{total % 100:02d}"


def caption_lines(text, width):
    """Lines as exported and previewed: a typed line break is kept, each line wraps at width."""
    lines = []
    for part in str(text).split("\n"):
        lines += textwrap.wrap(" ".join(part.split()), width=width, break_long_words=False, break_on_hyphens=False)
    return lines


def write_ass(path, plan, items):
    caps, export = plan["captions"], plan["export"]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {export['width']}
PlayResY: {export['height']}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{caps['font_name']},{caps['font_size']},&H00FFFFFF,&H0000FFFF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,1,{caps.get('outline_width', 3)},1,2,70,70,{caps['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for start, end, text in items:
        safe = str(text).replace("\\", " ").replace("{", "(").replace("}", ")")
        wrapped = caption_lines(safe, caps["max_chars"])
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
    elif any(clip.get("transition") for clip in plan["clips"]):
        # With transitions the picture and the voice are joined by separate
        # filters; one shared demuxer would make one branch queue frames for
        # the other. A second reader of the same file keeps memory flat.
        command += ["-i", str(source)]
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
    elif export["fit"] == "crop":
        size += f"increase:force_divisible_by=2,crop={width}:{height}"
    else:
        size += "decrease:force_divisible_by=2"
        # Blur a 1/8-size cover copy, then upscale it: cheap and smooth.
        small_w, small_h = max(2, width // 16 * 2), max(2, height // 16 * 2)
        backdrop = (f"scale={small_w}:{small_h}:force_original_aspect_ratio=increase,crop={small_w}:{small_h},"
                    f"gblur=sigma=4,scale={width}:{height},setsar=1,eq=brightness=-0.08")
    filters, concat, audio_parts = [], [], []
    handles = clip_handles(plan)
    transitions = any(clip.get("transition") for clip in plan["clips"])
    for i, clip in enumerate(plan["clips"]):
        start, end = clip["source_in_seconds"], clip["source_out_seconds"]
        rate = clip["playback_rate"]
        frames = clip["timeline_out_frame"] - clip["timeline_in_frame"]
        duration = frames / fps
        crop = clip.get("crop")
        source_crop = f"crop={crop['width']}:{crop['height']}:{crop['x']}:{crop['y']}," if crop else ""
        timing = "setpts=PTS-STARTPTS" if rate == 1 else f"setpts=(PTS-STARTPTS)/{rate:.9g}"
        # A transition shows picture just beyond the cut points (handles); the
        # zoom stays anchored to source time, so the handle frames zoom correctly.
        before, after = handles[i]
        picture_start = max(0.0, start - before * rate / fps)
        picture_frames = frames + before + after
        picture_clip = dict(clip, source_in_seconds=picture_start, source_out_seconds=end + after * rate / fps,
                            timeline_in_frame=0, timeline_out_frame=picture_frames)
        camera = zoom_filter(picture_clip, fps)
        picture = f"[0:v:0]trim=start={picture_start:.9f}:end={end + after * rate / fps:.9f},{timing},fps={fps},{source_crop}{camera + ',' if camera else ''}"
        finish = f"setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration={1/fps:.9f},trim=end_frame={picture_frames}{f',settb=1/{fps}' if transitions else ''}[v{i}]"
        if export["fit"] == "blur":
            filters += [f"{picture}split=2[back{i}][front{i}]", f"[back{i}]{backdrop}[blurred{i}]",
                        f"[front{i}]{size},setsar=1[fitted{i}]", f"[blurred{i}][fitted{i}]overlay=(W-w)/2:(H-h)/2,{finish}"]
        else:
            filters.append(f"{picture}{size},{finish}")
        if not media["has_audio"]:
            source_audio = f"atrim=start={0:.9f}:duration={duration:.9f},asetpts=PTS-STARTPTS"
        elif rate == 1:
            source_audio = f"atrim=start={start:.9f}:duration={duration:.9f},asetpts=PTS-STARTPTS"
        else:
            source_audio = f"atrim=start={start:.9f}:duration={end - start:.9f},asetpts=PTS-STARTPTS,atempo={rate:.9g}"
        filters.append(f"[{audio_input}]{source_audio},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={duration:.9f}[a{i}]")
        audio_parts.append(f"[a{i}]")
        concat += [f"[v{i}]", f"[a{i}]"]
    if transitions:
        join_with_transitions(plan, filters, audio_parts)
    else:
        filters.append("".join(concat) + f"concat=n={len(plan['clips'])}:v=1:a=1[cutv][cuta]")
    base_video, visual_assets = composite_overlays(plan, folder, command, filters, next_input + (1 if music else 0))
    sfx, audio_assets = plan["audio"].get("sfx", []), []
    first_sfx = next_input + (1 if music else 0) + len(plan.get("overlays", []))
    for i, item in enumerate(sfx):
        path = within(folder, item["path"])
        if not path.is_file() or not probe(path)["has_audio"]:
            raise EditorError(f"SFX file must contain an audio stream: {item['path']}")
        command += ["-i", str(path)]
        length = (item["timeline_out_frame"] - item["timeline_in_frame"]) / fps
        delay = round(item["timeline_in_frame"] / fps * 48000)
        filters.append(f"[{first_sfx + i}:a:0]atrim=duration={length:.9f},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={item['gain']},adelay=delays={delay}S:all=1[sfx{i}]")
        audio_assets.append({"id": item["id"], "path": item["path"], "sha256": digest(path), "type": "sfx"})
    if plan["captions"]["enabled"]:
        caps = plan["captions"]
        transcript = {} if "items" in caps else read_json(within(folder, caps["transcript_ref"]))
        if transcript and (transcript.get("job_id") != job["job_id"] or transcript.get("asset_id") != job["assets"][0]["asset_id"]):
            raise EditorError("Transcript job/asset does not match the video.")
        items = mapped_captions(plan, transcript)
        if not items:
            raise EditorError("Captions are enabled but no cues were produced. Disable captions or supply timed text.")
        write_ass(revision / "captions.ass", plan, items)
        fonts_option = ''
        if caps['font_name'] == 'Be Vietnam Pro':
            # libass and browser load the exact same bundled TTF files, without
            # installing fonts on the host. Keep the filter path simple/local.
            bundled = ROOT/'motion/public/fonts'
            selected_fonts = revision/'fonts'
            selected_fonts.mkdir(exist_ok=True)
            for name in ('BeVietnamPro-Regular.ttf', 'BeVietnamPro-Bold.ttf', 'OFL.txt'):
                if not (bundled/name).is_file():
                    raise EditorError('Missing bundled Vietnamese font: '+name)
                shutil.copy2(bundled/name, selected_fonts/name)
            fonts_option = ':fontsdir=fonts'
        filters.append(f"[{base_video}]subtitles=filename=captions.ass{fonts_option}[vout]")
    else:
        filters.append(f"[{base_video}]null[vout]")
    cleanup = DENOISE[plan["audio"]["denoise"]] + "," if "denoise" in plan["audio"] else ""
    filters.append(f"[cuta]{cleanup}volume={plan['audio']['voice_gain']}[voice]")
    # SFX join after ducking, so music never ducks under a whoosh. Loudness
    # normalization runs last, on the whole mix.
    loudness = plan["audio"].get("loudness_lufs")
    final = "mixed" if loudness is not None else "aout"
    bed = "amain" if sfx else final
    if music:
        filters.append(f"[{next_input}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={music['gain']}[music]")
        if music["ducking"]:
            filters += ["[voice]asplit=2[keepvoice][side]", "[music][side]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[ducked]", f"[keepvoice][ducked]amix=inputs=2:duration=first:normalize=0[{bed}]"]
        else:
            filters.append(f"[voice][music]amix=inputs=2:duration=first:normalize=0[{bed}]")
    else:
        filters.append(f"[voice]anull[{bed}]")
    if sfx:
        filters.append(f"[{bed}]" + "".join(f"[sfx{i}]" for i in range(len(sfx))) + f"amix=inputs={len(sfx) + 1}:duration=first:normalize=0[{final}]")
    if loudness is not None:
        # Single-pass loudnorm works internally at 192 kHz; resample back.
        filters.append(f"[mixed]loudnorm=I={loudness}:TP=-1.5:LRA=11,aresample=48000[aout]")
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
        "visual_assets": visual_assets, **({"audio_assets": audio_assets} if audio_assets else {}),
    })
    return output
