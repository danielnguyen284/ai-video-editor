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


def quietest(levels, seconds, search):
    """The gap between syllables nearest to `seconds`, else the quietest point nearby.

    A gap is a local minimum at least 10 dB below the loudest level within 80 ms. The
    absolute minimum alone can jump past a short syllable that should be cut ("Đúng").
    """
    lo, hi = max(0, int((seconds - search) * 100)), min(len(levels), int((seconds + search) * 100) + 1)
    if lo >= hi:
        return seconds
    gaps = [i for i in range(lo, hi)
            if levels[i] <= levels[max(0, i - 1)] and levels[i] <= levels[min(len(levels) - 1, i + 1)]
            and max(levels[max(0, i - 8):i + 9]) - levels[i] >= 10]
    index = min(gaps, key=lambda i: abs(i / 100 + 0.005 - seconds)) if gaps else min(range(lo, hi), key=lambda i: levels[i])
    return index / 100 + 0.005


def cut_plan(folder, revision, remove, *, refine=True, search=0.15):
    """Replace the plan's clips by the source with `remove` ranges taken out; returns a report.

    Boundaries move to the quietest 10 ms within ±search seconds (refine) and snap to
    frames. The report lists the words at each cut and Whisper words that cross it.
    """
    plan = revision_plan(revision)
    job = read_json(folder / "job.json")
    from core.adapters.ffmpeg import probe
    source = within(folder, job["assets"][0]["path"])
    duration = probe(source)["duration_seconds"]
    fps = plan["fps"]
    ranges = sorted((float(a), float(b)) for a, b in remove)
    for (a, b), following in zip(ranges, ranges[1:] + [(math.inf, math.inf)]):
        if not 0 <= a < b <= duration + 0.001 or b > following[0]:
            raise EditorError(f"Remove ranges must be ordered, inside 0-{duration:.2f} s and not overlap: {a}-{b}")
    levels = energy(folder, source) if refine else []
    snap = lambda t: round(t * fps) / fps
    edges = []
    for a, b in ranges:
        a = 0.0 if a <= 0.001 else snap(quietest(levels, a, search) if refine else a)
        b = duration if b >= duration - 0.001 else snap(quietest(levels, b, search) if refine else b)
        edges.append((a, min(b, duration)))
    keeps, cursor = [], 0.0
    for a, b in edges:
        if a > cursor:
            keeps.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < duration:
        keeps.append((cursor, snap(duration) if snap(duration) <= duration else duration))
    clips, frame = [], 0
    for index, (a, b) in enumerate(keeps, 1):
        frames = round((b - a) * fps)
        if frames < 1:
            continue
        clips.append({"clip_id": f"clip-{index:03d}", "asset_id": job["assets"][0]["asset_id"], "source_in_seconds": round(a, 4),
                      "source_out_seconds": round(b, 4), "timeline_in_frame": frame, "timeline_out_frame": frame + frames,
                      "playback_rate": 1.0})
        frame += frames
    if not clips:
        raise EditorError("Nothing would remain after these cuts.")
    stale = [name for name, present in (("overlays", plan.get("overlays")), ("audio.sfx", plan["audio"].get("sfx")),
                                        ("captions.items", plan["captions"].get("items"))) if present]
    plan.update(clips=clips, duration_frames=frame)
    plan["captions"].pop("items", None)
    write_json(revision / "edit-plan.json", plan, replace=True)
    try:
        transcript = transcript_of(folder, plan)
    except EditorError:
        transcript = {}
    words = [(w["start"], w["end"], w["text"].strip()) for s in transcript.get("segments", [])
             for w in s.get("words", []) if w["end"] > w["start"]]
    kept = lambda t: any(c["source_in_seconds"] <= t < c["source_out_seconds"] for c in clips)
    cuts = []
    for a, b in edges:
        dropped = [w[2] for w in words if a <= (w[0] + w[1]) / 2 < b]
        crossing = [f"{w[2]} {w[0]:.2f}-{w[1]:.2f}" for w in words if (w[0] < a < w[1] or w[0] < b < w[1])]
        stretched = [f"{w[2]} {w[0]:.2f}-{w[1]:.2f}" for w in words if kept((w[0] + w[1]) / 2) and (w[0] < a - 0.15 < a < w[1] or w[0] < b < b + 0.15 < w[1])]
        cuts.append({"remove": [a, b], "dropped_words": " ".join(dropped), "words_crossing_cut": crossing, "check_word_timing": stretched})
    report = {"created_at": timestamp(), "duration_seconds": round(frame / fps, 3), "clips": len(clips), "cuts": cuts,
              "refined": refine, "stale_after_cut": stale,
              "next": "Captions mapped from words whose midpoint is kept; fix stretched word times in cleaned.json, then run captions."}
    write_json(revision / "cut-report.json", report, replace=True)
    return report


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
