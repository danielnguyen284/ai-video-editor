"""Agent helpers between an approved treatment and its export: cuts, captions, previews.

They write only the pending revision's plan (or a preview file outside it) and never
choose creative content: the agent passes the approved ranges, the tools place them.
"""
from __future__ import annotations

import array
import math
import subprocess
import tempfile
import wave
from copy import deepcopy
from pathlib import Path

from core.common import EditorError, executable, read_json, timestamp, within, write_json

# Vietnamese pairs a caption line or cue should not split ("doanh | nghiệp").
COMPOUNDS = {tuple(pair.split()) for pair in """doanh nghiệp|cổ phiếu|cổ phần|thị trường|chứng khoán|trực tiếp|lãnh đạo|đầu tư|giao dịch|
hàng hóa|tư duy|phát hành|chủ tịch|đăng ký|nghịch lý|cộng đồng|tiểu sử|cá nhân|tài chính|sản phẩm|huy động|rủi ro|hệ thống|nội tại|
kinh nghiệm|nguyên tắc|chặng đường|nhắn tin|mọi người|chúng ta|tư nhân|chiến lược|sở hữu|nghĩa vụ|giai đoạn|thực tế|chủ thể|sai lầm|
hành động|góc nhìn|lần đầu|trao đổi|mua bán|nằm lòng|bất di|bất dịch|ngóc đầu|cầm cố|động thái|liên tục|phân phối|chia tách|chuyển đổi|
bản chất|kiểm tra|chia sẻ|xin phép|ông chủ|đặc biệt|khả năng|kể cả|tại sao|như vậy|cơ bản|anh em|thông qua|người ta|nhà đầu|ban lãnh|
vào được|các bạn|ngân hàng|lợi nhuận|doanh thu|thông tin|kinh doanh|khách hàng|công ty|sản xuất|thời gian|bây giờ|hôm nay|ngày mai|
quan trọng|vấn đề|phát triển|ví dụ|giá trị|tăng trưởng|thu nhập|chi phí|thành công|mục tiêu|biến tốt|biến xấu|cho chính|chục năm|
chủ doanh|con cá|cá con|cá mập|cá voi|các cái|cũng là|một cái|mở miệng|nợ vay|trang cá|trên thị|vật gọi""".replace("\n", "").split("|")}


def norm(text):
    return text.lower().strip(",.?!:;\"'")


def joins(left, right, compounds=COMPOUNDS):
    return (norm(left.split()[-1]), norm(right.split()[0])) in compounds


def revision_plan(revision):
    if (revision / "renders/video.mp4").exists() or (revision / "render-manifest.json").exists():
        raise EditorError("This revision was already exported. Create a new revision before changing its plan.")
    return read_json(revision / "edit-plan.json")


def transcript_of(folder, plan):
    for ref in (plan["captions"].get("transcript_ref"), "transcript/cleaned.json", "transcript/raw.json"):
        if ref and within(folder, ref).is_file():
            return read_json(within(folder, ref))
    raise EditorError("No transcript. Run transcribe (or supply cleaned.json) first.")


def energy(folder, source):
    """Loudness in dB every 10 ms of the source audio (transcription WAV when present)."""
    wav = folder / "transcript/audio.wav"
    with tempfile.TemporaryDirectory(prefix=".cut-audio-", dir=folder) as temp:
        if not wav.is_file():
            wav = Path(temp) / "audio.wav"
            result = subprocess.run([executable("ffmpeg"), "-v", "error", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
                                     "-c:a", "pcm_s16le", str(wav)], capture_output=True)
            if result.returncode:
                raise EditorError("Cannot read the source audio: " + result.stderr.decode(errors="replace")[-400:])
        with wave.open(str(wav)) as stream:
            rate, channels = stream.getframerate(), stream.getnchannels()
            samples = array.array("h", stream.readframes(stream.getnframes()))
    hop = rate // 100 * channels
    levels = []
    for start in range(0, len(samples) - hop + 1, hop):
        block = samples[start:start + hop]
        power = sum(value * value for value in block) / len(block)
        levels.append(10 * math.log10(power / 32768 ** 2 + 1e-12))
    return levels


def silence_threshold(levels, above_floor=12.0):
    """Quiet means less than `above_floor` dB over the recording's noise floor (5th percentile)."""
    if not levels:
        return -40.0
    ordered = sorted(levels)
    return ordered[int(len(ordered) * 0.05)] + above_floor


def quiet_runs(levels, threshold, shortest):
    """(start, end) seconds of stretches below `threshold` lasting at least `shortest` seconds."""
    runs, start = [], None
    for index, value in enumerate([*levels, math.inf]):
        if value < threshold:
            start = index if start is None else start
        elif start is not None:
            if (index - start) / 100 >= shortest - 1e-9:
                runs.append((start / 100, index / 100))
            start = None
    return runs


def frames_inside(run, fps):
    """First and last frame boundary inside a quiet run, or None when no boundary fits."""
    first, last = math.ceil(run[0] * fps - 1e-6), math.floor(run[1] * fps + 1e-6)
    return (first, last) if first <= last else None


def pause_near(levels, runs, seconds, search, fps, threshold, slack):
    """The quiet run nearest to `seconds` (within `search`) that a frame boundary fits in.

    Reaching it may cross at most `slack` seconds of sound: Whisper word edges are often a
    little early or late, but a longer stretch is a word that would change sides of the cut.
    """
    def sound(lo, hi):
        return sum(1 for i in range(max(0, int(lo * 100)), min(len(levels), int(hi * 100))) if levels[i] >= threshold) / 100
    near = []
    for run in runs:
        if run[0] - search <= seconds <= run[1] + search and frames_inside(run, fps):
            crossed = sound(seconds, run[0]) if seconds < run[0] else sound(run[1], seconds)
            if crossed <= slack + 1e-9:
                near.append(run)
    return min(near, key=lambda r: max(r[0] - seconds, seconds - r[1], 0), default=None)


def quietest_frame(levels, seconds, search, fps):
    """Frame boundary within ±search whose surrounding 20 ms is quietest (nearest among near-ties).

    Only for an edge the user explicitly allows to fall between syllables of continuous speech.
    """
    first, last = math.ceil((seconds - search) * fps), math.floor((seconds + search) * fps)
    score = lambda f: max(levels[max(0, round(f / fps * 100) - 2):round(f / fps * 100) + 2] or [0.0])
    frames = list(range(max(0, first), last + 1))
    if not frames or not levels:
        return round(seconds * fps) / fps
    best = min(score(f) for f in frames)
    return min((f for f in frames if score(f) <= best + 3), key=lambda f: abs(f / fps - seconds)) / fps


def place_cuts(levels, ranges, duration, fps, *, pad=0.15, min_pause=0.06, min_remove=0.5, search=0.3, slack=0.1,
               allow_tight=False, threshold=None):
    """Turn approved remove ranges into frame-exact cuts that land only in real pauses.

    Each edge moves to the quiet stretch (at least `min_pause` seconds) nearest to the
    requested time, crossing at most `slack` seconds of sound on the way, and keeps up to
    `pad` seconds of it beside the kept speech, so joined words keep a natural breath and
    no syllable is clipped. A range is skipped (and reported) when an edge has no such
    pause, i.e. continuous speech, or when less than `min_remove` seconds would go.
    `allow_tight` instead puts such an edge on the quietest frame boundary between
    syllables, only when the user asked for that cut.
    """
    threshold = silence_threshold(levels) if threshold is None else threshold
    runs = quiet_runs(levels, threshold, min_pause)
    placed, skipped = [], []
    for a, b in ranges:
        notes, edges = [], []
        for side, seconds in (("start", a), ("end", b)):
            if side == "start" and seconds <= 0.001:
                edges.append(0.0)
                continue
            if side == "end" and seconds >= duration - 0.001:
                edges.append(duration)
                continue
            run = pause_near(levels, runs, seconds, search, fps, threshold, slack)
            if run:
                first, last = frames_inside(run, fps)
                target = run[0] + pad if side == "start" else run[1] - pad
                edges.append(min(max(round(target * fps), first), last) / fps)
            elif allow_tight:
                edges.append(quietest_frame(levels, seconds, search, fps))
                notes.append(f"{side} {seconds:.2f} s sits between syllables of continuous speech (allowed)")
            else:
                edges = None
                skipped.append({"requested": [a, b], "reason": f"no pause near the {side} ({seconds:.2f} s): continuous speech, "
                                "a cut there would clip a word"})
                break
        if edges is None:
            continue
        start, end = edges
        # Trimming the head or tail joins nothing, so any length may go there.
        if 0 < start and end < duration and end - start < min_remove - 1e-6:
            skipped.append({"requested": [a, b], "reason": f"only {max(0, end - start):.2f} s would go after keeping "
                            f"{pad:g} s of pause beside the words (minimum {min_remove:g} s)"})
            continue
        placed.append({"requested": [a, b], "remove": [round(start, 4), round(min(end, duration), 4)], "notes": notes})
    return placed, skipped


def place_splits(levels, splits, fps, *, search=0.3, min_pause=0.06, threshold=None):
    """Cut points that remove nothing (e.g. for a transition), centred in the nearest pause."""
    threshold = silence_threshold(levels) if threshold is None else threshold
    runs, result = quiet_runs(levels, threshold, min_pause), []
    for seconds in splits:
        run = pause_near(levels, runs, seconds, search, fps, threshold, search)
        if not run:
            raise EditorError(f"No pause near {seconds:.2f} s for a split; pick a moment between sentences.")
        first, last = frames_inside(run, fps)
        result.append(min(max(round((run[0] + run[1]) / 2 * fps), first), last) / fps)
    return result


def keep_ranges(cuts, splits, duration, fps):
    snap = lambda t: round(t * fps) / fps
    keeps, cursor = [], 0.0
    for a, b in sorted(cuts):
        if a > cursor:
            keeps.append([cursor, a])
        cursor = max(cursor, b)
    if cursor < duration:
        keeps.append([cursor, snap(duration) if snap(duration) <= duration else duration])
    for point in sorted(splits):
        for index, (a, b) in enumerate(keeps):
            if a < point < b:
                keeps[index:index + 1] = [[a, point], [point, b]]
                break
    return [(a, b) for a, b in keeps if round((b - a) * fps) >= 1]


def source_at(clips, frame, fps):
    """Source second shown at an output frame of rate-1 clips (clamped to the timeline)."""
    clip = next((c for c in clips if c["timeline_in_frame"] <= frame < c["timeline_out_frame"]),
                clips[-1] if frame >= clips[-1]["timeline_out_frame"] else clips[0])
    return clip["source_in_seconds"] + (frame - clip["timeline_in_frame"]) / fps


def frame_at(clips, seconds, fps, *, forward=True):
    """Output frame of a source second; a cut-away second moves to the next (or previous) kept frame."""
    previous = None
    for clip in clips:
        if seconds < clip["source_in_seconds"] - 1e-6:
            return clip["timeline_in_frame"] if forward or previous is None else previous["timeline_out_frame"] - 1
        if seconds < clip["source_out_seconds"] - 1e-6:
            return clip["timeline_in_frame"] + round((seconds - clip["source_in_seconds"]) * fps)
        previous = clip
    return clips[-1]["timeline_out_frame"] - 1


def remap_span(old, new, start, end, fps, old_total, new_total):
    """Old output frames [start, end) to the new timeline by source time; None when cut away."""
    a = 0 if start <= 0 else frame_at(new, source_at(old, start, fps), fps)
    b = new_total if end >= old_total else frame_at(new, source_at(old, end - 1, fps), fps, forward=False) + 1
    return (a, b) if b > a else None


def recut(plan, cuts, splits, fps, duration, asset_id):
    """New clips for the kept source, carrying zoom/crop/transitions and retiming layers and SFX.

    Works when the current clips are rate-1 source-ordered pieces (what `cut` writes);
    otherwise layers and SFX are left for the agent to place again. Returns (plan, notes).
    """
    old = plan["clips"]
    ordered = all(c.get("playback_rate", 1) == 1 for c in old) and all(
        a["source_out_seconds"] <= b["source_in_seconds"] + 1e-6 for a, b in zip(old, old[1:]))
    old_cuts = [(a["source_out_seconds"], b["source_in_seconds"], b) for a, b in zip(old, old[1:])]
    clips, frame = [], 0
    for index, (a, b) in enumerate(keep_ranges(cuts, splits, duration, fps), 1):
        frames = round((b - a) * fps)
        clip = {"clip_id": f"clip-{index:03d}", "asset_id": asset_id, "source_in_seconds": round(a, 4),
                "source_out_seconds": round(b, 4), "timeline_in_frame": frame, "timeline_out_frame": frame + frames,
                "playback_rate": 1.0}
        if ordered:
            parent = next((c for c in old if c["source_in_seconds"] - 1e-6 <= a < c["source_out_seconds"] - 1e-6), None) \
                or next((c for c in old if c["source_in_seconds"] >= a - 1e-6), None)
            if parent and parent.get("crop"):
                clip["crop"] = parent["crop"]
            if parent and parent.get("zoom"):
                keys = [dict(k) for k in parent["zoom"] if a - 1e-6 <= k["source_seconds"] < b]
                if not keys or keys[0]["source_seconds"] > a + 1e-6:
                    keys.insert(0, {**parent["zoom"][0], "source_seconds": round(a, 4)})
                clip["zoom"] = keys
            if clips:
                # The transition of the old cut this new cut replaces (a split counts as a cut).
                before = clips[-1]["source_out_seconds"]
                match = next((c for o_out, o_in, c in old_cuts if c.get("transition")
                              and o_out - 0.35 <= a and before <= o_in + 0.35), None)
                if match:
                    clip["transition"] = dict(match["transition"])
        clips.append(clip)
        frame += frames
    if not clips:
        raise EditorError("Nothing would remain after these cuts.")
    result = deepcopy(plan)
    result.update(clips=clips, duration_frames=frame)
    notes = {"retimed": ordered, "dropped_layers": [], "resized_layers": []}
    if not ordered:
        return result, notes
    old_total = plan["duration_frames"]
    layers = []
    for layer in plan.get("overlays", []):
        span = remap_span(old, clips, layer["timeline_in_frame"], layer["timeline_out_frame"], fps, old_total, frame)
        if not span:
            notes["dropped_layers"].append(layer["id"])
            continue
        if span[1] - span[0] != layer["timeline_out_frame"] - layer["timeline_in_frame"]:
            notes["resized_layers"].append(layer["id"])
        layers.append({**layer, "timeline_in_frame": span[0], "timeline_out_frame": span[1]})
    result["overlays"] = layers
    # A one-shot sound near a cut that still exists keeps its offset to that cut (a whoosh
    # on a transition); any other sound stays on its source moment.
    new_cuts = [(a["source_out_seconds"], b["source_in_seconds"], b["timeline_in_frame"]) for a, b in zip(clips, clips[1:])]
    sounds = []
    for item in plan["audio"].get("sfx", []):
        length = item["timeline_out_frame"] - item["timeline_in_frame"]
        near = min(((abs(c["timeline_in_frame"] - item["timeline_in_frame"]), c) for c in old[1:]), default=(None, None), key=lambda x: x[0])
        start = None
        if near[1] is not None and near[0] <= fps:
            o_out = old[old.index(near[1]) - 1]["source_out_seconds"]
            match = next((f for n_out, n_in, f in new_cuts if o_out - 0.35 <= n_in and n_out <= near[1]["source_in_seconds"] + 0.35), None)
            if match is not None:
                start = match + item["timeline_in_frame"] - near[1]["timeline_in_frame"]
        if start is None:
            start = frame_at(clips, source_at(old, item["timeline_in_frame"], fps), fps)
        start = max(0, min(start, frame - 1))
        sounds.append({**item, "timeline_in_frame": start, "timeline_out_frame": min(frame, start + length)})
    if "sfx" in plan["audio"]:
        result["audio"]["sfx"] = sounds
    return result, notes


def retime_motions(motions, old_plan, new_plan):
    """Fit Remotion specs to their resized layers: duration and spoken-moment frames follow source time."""
    fps, result = new_plan["fps"], deepcopy(motions)
    old_layers = {layer["id"]: layer for layer in old_plan["overlays"]}
    for layer in new_plan["overlays"]:
        spec, before = result.get(layer["id"]), old_layers.get(layer["id"])
        if not spec or not before:
            continue
        scale = spec["fps"] / fps

        def moved(at):
            old_frame = before["timeline_in_frame"] + round(at / scale)
            new_frame = frame_at(new_plan["clips"], source_at(old_plan["clips"], old_frame, fps), fps)
            return max(0, round((new_frame - layer["timeline_in_frame"]) * scale))
        props = spec["props"]
        for item in props.get("items", []) if spec["template"] == "Points" else []:
            if "at" in item:
                item["at"] = moved(item["at"])
        if spec["template"] == "Keyword" and props.get("emphasis_frame"):
            props["emphasis_frame"] = moved(props["emphasis_frame"])
        grown = (layer["timeline_out_frame"] - layer["timeline_in_frame"]) - (before["timeline_out_frame"] - before["timeline_in_frame"])
        if grown:
            needed = math.ceil((layer["timeline_out_frame"] - layer["timeline_in_frame"]) * scale + layer.get("source_in_seconds", 0) * spec["fps"])
            spec["duration_frames"] = max(needed, spec["duration_frames"] + round(grown * scale))
    return result


def cut_report(clips, placed, skipped, transcript, fps, splits=()):
    words = [(w["start"], w["end"], w["text"].strip()) for s in transcript.get("segments", [])
             for w in s.get("words", []) if w["end"] > w["start"]]
    kept = lambda t: any(c["source_in_seconds"] <= t < c["source_out_seconds"] for c in clips)
    cuts = []
    for item in placed:
        a, b = item["remove"]
        ra, rb = item["requested"]
        dropped = [w[2] for w in words if a <= (w[0] + w[1]) / 2 < b]
        asked = [w[2] for w in words if ra <= (w[0] + w[1]) / 2 < rb]
        stretched = [f"{w[2]} {w[0]:.2f}-{w[1]:.2f}" for w in words if kept((w[0] + w[1]) / 2)
                     and (w[0] < a - 0.15 < a < w[1] or w[0] < b < b + 0.15 < w[1])]
        cut = {**item, "dropped_words": " ".join(dropped), "check_word_timing": stretched}
        if dropped != asked:
            cut["requested_words"] = " ".join(asked)
        cuts.append(cut)
    for item in skipped:
        ra, rb = item["requested"]
        item["kept_words"] = " ".join(w[2] for w in words if ra <= (w[0] + w[1]) / 2 < rb)
    return {"created_at": timestamp(), "duration_seconds": round(clips[-1]["timeline_out_frame"] / fps, 3), "clips": len(clips),
            "cuts": cuts, "skipped": skipped, "splits": list(splits)}


def cut_settings(pad=0.15, min_pause=0.06, min_remove=0.5, search=0.3, slack=0.1, allow_tight=False):
    return {"pad": pad, "min_pause": min_pause, "min_remove": min_remove, "search": search, "slack": slack, "allow_tight": allow_tight}


def _source(folder):
    job = read_json(folder / "job.json")
    from core.adapters.ffmpeg import probe
    source = within(folder, job["assets"][0]["path"])
    return job, source, probe(source)["duration_seconds"]


def _ranges(remove, duration):
    ranges = sorted((float(a), float(b)) for a, b in remove)
    for (a, b), following in zip(ranges, ranges[1:] + [(math.inf, math.inf)]):
        if not 0 <= a < b <= duration + 0.001 or b > following[0]:
            raise EditorError(f"Remove ranges must be ordered, inside 0-{duration:.2f} s and not overlap: {a}-{b}")
    return ranges


def cut_plan(folder, revision, remove, *, refine=True, splits=(), **settings):
    """Rebuild a pending revision's clips from the source minus `remove`; returns a report.

    Refined edges land only in real pauses (see place_cuts); ranges that cannot are kept
    and listed under "skipped". Layers and SFX are retimed by source time (and resized
    Remotion layers listed for a new render); caption items are dropped for `captions`.
    """
    plan = revision_plan(revision)
    job, source, duration = _source(folder)
    fps, settings = plan["fps"], cut_settings(**settings)
    ranges = _ranges(remove, duration)
    if refine:
        levels = energy(folder, source)
        placed, skipped = place_cuts(levels, ranges, duration, fps, **settings)
        points = place_splits(levels, splits, fps, search=settings["search"], min_pause=settings["min_pause"])
    else:
        snap = lambda t: round(t * fps) / fps
        placed = [{"requested": [a, b], "remove": [0.0 if a <= 0.001 else snap(a), duration if b >= duration - 0.001 else snap(b)],
                   "notes": []} for a, b in ranges]
        skipped, points = [], [snap(float(t)) for t in splits]
    new, notes = recut(plan, [p["remove"] for p in placed], points, fps, duration, job["assets"][0]["asset_id"])
    had_items = bool(plan["captions"].get("items"))
    new["captions"].pop("items", None)
    write_json(revision / "edit-plan.json", new, replace=True)
    try:
        transcript = transcript_of(folder, new)
    except EditorError:
        transcript = {}
    report = {**cut_report(new["clips"], placed, skipped, transcript, fps, points), "refined": refine, "settings": settings,
              **notes, "captions_dropped": had_items,
              "next": "Read skipped and requested_words; fix stretched word times in cleaned.json, run captions, "
                      "re-render Remotion layers listed in resized_layers."}
    write_json(revision / "cut-report.json", report, replace=True)
    return report


def cut_draft(folder, store, job_id, remove, *, splits=(), summary=None, max_seconds=3.0, **settings):
    """The same cut on the Studio draft, sent as a proposal the user approves in Studio.

    Captions are rebuilt from the transcript for the new timeline and Remotion specs are
    retimed to their layers. Locks are checked by the store; nothing changes until approval.
    """
    state = store.load(job_id)
    plan = state["plan"]
    job, source, duration = _source(folder)
    fps, settings = plan["fps"], cut_settings(**settings)
    levels = energy(folder, source)
    placed, skipped = place_cuts(levels, _ranges(remove, duration), duration, fps, **settings)
    points = place_splits(levels, splits, fps, search=settings["search"], min_pause=settings["min_pause"])
    new, notes = recut(plan, [p["remove"] for p in placed], points, fps, duration, job["assets"][0]["asset_id"])
    if not notes["retimed"]:
        raise EditorError("The draft has reordered or speed-changed clips; edit it in Studio instead of re-cutting from source.")
    transcript = transcript_of(folder, new)
    items = caption_items(new, transcript, max_seconds=max_seconds)
    new["captions"]["items"] = items
    candidate = {**state, "plan": new, "motions": retime_motions(state["motions"], plan, new),
                 "cues": [{"id": f"cue-{i:04d}", **item} for i, item in enumerate(items)]}
    report = {**cut_report(new["clips"], placed, skipped, transcript, fps, points), "settings": settings, **notes}
    text = summary or (f"Cắt lại: {len(placed)} chỗ cắt ở khoảng lặng thật, giữ {len(skipped)} chỗ không cắt được an toàn; "
                       f"thời lượng {report['duration_seconds']:.1f} giây. Caption, minh họa và SFX đã dời theo.")
    proposal = store.propose(job_id, candidate, state["version"], text)
    write_json(folder / "editor/cut-report.json", {**report, "proposal": proposal["id"]}, replace=True)
    return {**report, "proposal": proposal["id"], "summary": text}


def caption_items(plan, transcript, *, max_seconds=3.0, compounds=COMPOUNDS):
    """Balanced caption cues on the output timeline, with typed line breaks.

    One group per sentence (a lowercase continuation joins the previous one), the fewest
    cues that fit `max_chars` x 2 lines and `max_seconds`, balanced lengths, breaks after
    commas, never inside a compound; capitalised only at a real sentence start or after a cut.
    """
    fps, width = plan["fps"], plan["captions"]["max_chars"]
    if plan["captions"]["max_lines"] < 2:
        raise EditorError("Balanced captions need max_lines of at least 2.")
    clips = plan["clips"]
    from core.adapters.ffmpeg import output_seconds
    clip_of = lambda t: next((c for c in clips if c["source_in_seconds"] <= t < c["source_out_seconds"]), None)
    out = lambda c, t: output_seconds(c, min(max(t, c["source_in_seconds"]), c["source_out_seconds"]), fps)
    groups = []
    for segment in transcript.get("segments", []):
        real = [w for w in segment.get("words", []) if w["end"] > w["start"]]
        kept = [(out(c, w["start"]), out(c, w["end"]), w["text"].strip()) for w in real if (c := clip_of((w["start"] + w["end"]) / 2))]
        if not kept:
            continue
        first_is_first = kept[0][2] == real[0]["text"].strip() and clip_of((real[0]["start"] + real[0]["end"]) / 2) is not None
        if first_is_first and kept[0][2][:1].islower() and groups and kept[0][0] - groups[-1]["words"][-1][1] < 0.3:
            groups[-1]["words"].extend(kept)
        else:
            groups.append({"words": kept, "capitalize": not first_is_first or kept[0][2][:1].isupper()})

    def lines_of(chunk):
        tokens = [w[2] for w in chunk]
        text = " ".join(tokens)
        if len(text) <= width:
            return [text]
        options = []
        for i in range(1, len(tokens)):
            a, b = " ".join(tokens[:i]), " ".join(tokens[i:])
            if len(a) <= width and len(b) <= width and not joins(tokens[i - 1], tokens[i], compounds):
                options.append((abs(len(a) - len(b)) - (8 if tokens[i - 1].endswith(",") else 0) + (2 if len(a) < len(b) else 0), i))
        if not options:
            return None
        i = min(options)[1]
        return [" ".join(tokens[:i]), " ".join(tokens[i:])]

    def valid(chunk):
        return lines_of(chunk) is not None and chunk[-1][1] - chunk[0][0] <= max_seconds

    def split(words):
        n = len(words)
        need = [0] + [10 ** 9] * n
        for i in range(1, n + 1):
            for j in range(i):
                if need[j] + 1 < need[i] and valid(words[j:i]):
                    need[i] = need[j] + 1
        if need[n] >= 10 ** 9:
            raise EditorError("A single word is longer than a caption line; raise max_chars.")
        ideal = sum(len(w[2]) + 1 for w in words) / need[n]
        cost, count, back = [0.0] + [math.inf] * n, [0] + [10 ** 9] * n, [0] * (n + 1)
        for i in range(1, n + 1):
            for j in range(i):
                if count[j] + 1 > need[n] or not valid(words[j:i]):
                    continue
                c = cost[j] + (sum(len(w[2]) + 1 for w in words[j:i]) - ideal) ** 2
                if i < n:
                    c += (-40 if words[i - 1][2].endswith((",", "?")) else 0) + (600 if joins(words[i - 1][2], words[i][2], compounds) else 0)
                if (count[j] + 1, c) < (count[i], cost[i]):
                    cost[i], count[i], back[i] = c, count[j] + 1, j
        chunks, i = [], n
        while i:
            chunks.append(words[back[i]:i])
            i = back[i]
        return chunks[::-1]

    cues = []
    for group in groups:
        for index, chunk in enumerate(split(group["words"])):
            lines = lines_of(chunk)
            if index == 0 and group["capitalize"]:
                lines[0] = lines[0][:1].upper() + lines[0][1:]
            cues.append((chunk[0][0], chunk[-1][1], "\n".join(lines)))
    items = []
    for i, (a, b, text) in enumerate(cues):
        start, end = round(a * fps), round((b + 0.15) * fps)
        if i + 1 < len(cues):
            following = round(cues[i + 1][0] * fps)
            end = following if following - round(b * fps) < 12 else min(end, following)
        end = min(end, plan["duration_frames"])
        if items:
            start = max(start, items[-1]["timeline_out_frame"])
        if end > start:
            items.append({"timeline_in_frame": start, "timeline_out_frame": end, "text": text})
    return items


def build_captions(folder, revision, *, max_seconds=3.0, extra_compounds=()):
    plan = revision_plan(revision)
    compounds = COMPOUNDS | {tuple(norm(word) for word in pair.split()) for pair in extra_compounds if len(pair.split()) == 2}
    items = caption_items(plan, transcript_of(folder, plan), max_seconds=max_seconds, compounds=compounds)
    plan["captions"].update(enabled=True, items=items)
    write_json(revision / "edit-plan.json", plan, replace=True)
    from core.adapters.ffmpeg import caption_lines
    long_lines = [item["text"] for item in items if len(caption_lines(item["text"], plan["captions"]["max_chars"])) > plan["captions"]["max_lines"]]
    return {"cues": len(items), "single_word_cues": [i["text"] for i in items if len(i["text"].split()) == 1], "over_max_lines": long_lines}


def preview(folder, revision, *, seconds=25.0, stills=()):
    """Encode the first `seconds` (0 = all) of the current plan into previews/, outside any revision."""
    import json
    from core.adapters.ffmpeg import render
    render(folder, revision, dry_run=True)
    command = json.loads((revision / "ffmpeg-command.json").read_text(encoding="utf-8"))
    target = folder / "previews"
    target.mkdir(exist_ok=True)
    name = f"{revision.name}-{'full' if not seconds else f'0-{seconds:g}s'}"
    output = target / f"{name}.mp4"
    argv = list(command["argv"])[:-1] + (["-t", f"{seconds:g}"] if seconds else []) + ["-y", str(output)]
    result = subprocess.run(argv, cwd=command["cwd"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise EditorError("Preview render failed:\n" + result.stderr[-1200:])
    sheet = None
    if stills:
        frames = []
        with tempfile.TemporaryDirectory(prefix=".stills-", dir=target) as temp:
            for index, second in enumerate(stills):
                still = Path(temp) / f"{index}.png"
                subprocess.run([executable("ffmpeg"), "-v", "error", "-y", "-ss", f"{second:.3f}", "-i", str(output), "-frames:v", "1",
                                "-vf", "scale=270:480", str(still)], capture_output=True)
                if still.is_file():
                    frames.append(still)
            if frames:
                sheet = target / f"{name}-stills.png"
                inputs = [part for still in frames for part in ("-i", str(still))]
                stack = "".join(f"[{i}]" for i in range(len(frames))) + f"hstack=inputs={len(frames)}" if len(frames) > 1 else "null"
                subprocess.run([executable("ffmpeg"), "-v", "error", "-y", *inputs, "-filter_complex", stack, str(sheet)], capture_output=True)
    return output, sheet
