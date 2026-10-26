"""Sample source footage, detect scene/face signals and propose crops without applying them."""
import difflib
import math
from pathlib import Path
import re
import statistics

from core.common import EditorError, digest, read_json, timestamp, within, write_json
from core.decisions import require_setup
from core.adapters.ffmpeg import probe
from core.adapters.vision import describe_frame
from core.validation import number


def crop_proposal(width, height, face, target_aspect):
    crop_w = min(width, round(height * target_aspect))
    crop_h = min(height, round(crop_w / target_aspect))
    center_x = face[0] + face[2] / 2 if face else width / 2
    center_y = face[1] + face[3] / 2 + crop_h * 0.16 if face else height / 2
    return {
        "x": max(0, min(width - crop_w, round(center_x - crop_w / 2))),
        "y": max(0, min(height - crop_h, round(center_y - crop_h / 2))),
        "width": crop_w, "height": crop_h,
    }


def repeated_takes(transcript):
    segments = transcript.get("segments", [])
    candidates = []
    for i, first in enumerate(segments):
        a = " ".join(re.findall(r"\w+", first["text"].lower()))
        if len(a.split()) < 6:
            continue
        for second in segments[i + 1:]:
            b = " ".join(re.findall(r"\w+", second["text"].lower()))
            if len(b.split()) < 6:
                continue
            similarity = difflib.SequenceMatcher(None, a, b).ratio()
            if similarity >= 0.86:
                candidates.append({"first_source_range": [first["start"], first["end"]], "second_source_range": [second["start"], second["end"]], "text_similarity": round(similarity, 3), "status": "candidate-user-must-choose"})
    return candidates


def assign_tracks(previous, faces, next_id):
    """Associate nearby sampled face boxes. These are spatial tracks, not identities."""
    available = list(previous)
    output = []
    for face in faces:
        cx, cy = face[0] + face[2] / 2, face[1] + face[3] / 2
        best = min(available, key=lambda item: math.hypot(cx - item["box"][0] - item["box"][2] / 2, cy - item["box"][1] - item["box"][3] / 2), default=None)
        if best and math.hypot(cx - best["box"][0] - best["box"][2] / 2, cy - best["box"][1] - best["box"][3] / 2) <= max(face[2], face[3]) * 1.5:
            track_id = best["track_id"]
            available.remove(best)
        else:
            track_id = f"face-track-{next_id:03d}"
            next_id += 1
        output.append({"box": list(map(int, face)), "track_id": track_id})
    return output, next_id


def analyze_footage(folder, revision, *, mode="local", interval=1.0, max_samples=120, model=None, endpoint=None, semantic_samples=12):
    choices = require_setup(revision)
    if not choices["setup"]["answers"]["footage_analysis"]:
        raise EditorError("Footage analysis was not selected. Ask the user before changing that choice.")
    number(interval, "sample interval", 0.1)
    number(max_samples, "max samples", 1, integer=True)
    number(semantic_samples, "semantic samples", 1, integer=True)
    if mode not in ("local", "ollama") or max_samples > 600:
        raise EditorError("Select local/ollama mode and at most 600 sampled frames.")
    if mode == "ollama" and not model:
        raise EditorError("Ollama mode needs --model selecting an installed vision model.")
    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise EditorError("Install local analysis: python -m pip install -r requirements-vision.txt") from error
    job = read_json(folder / "job.json")
    source = within(folder, job["assets"][0]["path"])
    media = probe(source)
    target = revision / "analysis"
    report_path = target / "footage-analysis.json"
    if report_path.is_file():
        raise EditorError("Analysis already exists for this revision. Use a new revision to preserve it.")
    frames_dir = target / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise EditorError("OpenCV could not open the source video.")
    classifier = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"))
    if classifier.empty():
        cap.release()
        raise EditorError("OpenCV face cascade is missing.")
    step = max(interval, media["duration_seconds"] / max_samples)
    samples, previous_hist, previous_faces, track_id = [], None, [], 1
    aspect = choices["setup"]["answers"]["output"]["width"] / choices["setup"]["answers"]["output"]["height"]
    try:
        for index in range(min(max_samples, math.ceil(media["duration_seconds"] / step))):
            requested = index * step
            cap.set(cv2.CAP_PROP_POS_MSEC, requested * 1000)
            ok, frame = cap.read()
            if not ok:
                raise EditorError(f"Could not decode sampled frame at source {requested:.3f}s.")
            actual = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            h, w = frame.shape[:2]
            scale = min(1, 640 / w)
            thumb = cv2.resize(frame, (round(w * scale), round(h * scale)))
            gray = cv2.cvtColor(thumb, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([cv2.cvtColor(thumb, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            difference = 0 if previous_hist is None else float(cv2.compareHist(previous_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
            scene_change = previous_hist is not None and difference > 0.45
            boxes = classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
            faces = [[round(int(value) / scale) for value in box] for box in boxes]
            tracked, track_id = assign_tracks([] if scene_change else previous_faces, faces, track_id)
            blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            brightness = float(gray.mean())
            flags = []
            if blur < 40:
                flags.append("low-texture-or-blur")
            if brightness < 30:
                flags.append("dark-frame")
            if brightness > 225:
                flags.append("bright-frame")
            filename = frames_dir / f"frame-{index:04d}.jpg"
            if not cv2.imwrite(str(filename), thumb):
                raise EditorError(f"Could not write sample image: {filename}")
            largest = max(faces, key=lambda box: box[2] * box[3], default=None)
            samples.append({
                "sample_id": f"frame-{index:04d}", "source_time_seconds": round(actual if actual >= 0 else requested, 6),
                "requested_source_time_seconds": requested, "image": filename.relative_to(folder).as_posix(),
                "image_width": w, "image_height": h, "faces": tracked,
                "laplacian_variance": round(blur, 3), "brightness": round(brightness, 3),
                "scene_distance": round(difference, 4), "scene_change_candidate": scene_change,
                "flags": flags, "crop_proposal": crop_proposal(w, h, largest, aspect),
            })
            previous_hist, previous_faces = hist, tracked
    finally:
        cap.release()
    if not samples:
        raise EditorError("No frames were sampled.")
    scenes = []
    for item in samples:
        if not scenes or item["scene_change_candidate"]:
            if scenes:
                scenes[-1]["source_out_seconds"] = item["source_time_seconds"]
            scenes.append({"source_in_seconds": item["source_time_seconds"], "source_out_seconds": media["duration_seconds"], "sample_ids": [], "crop_proposals": []})
        scenes[-1]["sample_ids"].append(item["sample_id"])
        scenes[-1]["crop_proposals"].append(item["crop_proposal"])
    for scene in scenes:
        values = scene.pop("crop_proposals")
        scene["suggested_crop"] = {key: round(statistics.median(value[key] for value in values)) for key in ("x", "y", "width", "height")}
    columns, tile_w, tile_h = 4, 320, 210
    sheet = np.full((math.ceil(len(samples) / columns) * tile_h, columns * tile_w, 3), 22, dtype=np.uint8)
    for i, sample in enumerate(samples):
        thumb = cv2.imread(str(within(folder, sample["image"])))
        factor = min(tile_w / thumb.shape[1], 180 / thumb.shape[0])
        thumb = cv2.resize(thumb, (round(thumb.shape[1] * factor), round(thumb.shape[0] * factor)))
        x, y = i % columns * tile_w, i // columns * tile_h
        sheet[y:y+thumb.shape[0], x:x+thumb.shape[1]] = thumb
        cv2.putText(sheet, f"{sample['sample_id']}  {sample['source_time_seconds']:.2f}s", (x+4,y+200), cv2.FONT_HERSHEY_SIMPLEX, .5, (240,240,240), 1)
    contact = target / "contact-sheet.jpg"
    if not cv2.imwrite(str(contact), sheet):
        raise EditorError("Could not write footage contact sheet.")
    transcript_file = folder / "transcript/cleaned.json"
    report = {
        "schema_version": "1.0", "job_id": job["job_id"], "revision": int(revision.name[1:]),
        "created_at": timestamp(), "source_sha256": digest(source), "mode": mode,
        "sample_interval_seconds": step, "samples": samples, "scene_candidates": scenes,
        "repeated_take_candidates": repeated_takes(read_json(transcript_file)) if transcript_file.is_file() else [],
        "contact_sheet": contact.relative_to(folder).as_posix(), "automatically_applied": False,
        "limitations": ["Scene boundaries are approximate at the sampling interval.", "Face tracks associate sampled boxes, not identities or continuous motion.", "Blur/brightness flags are signals, not automatic cut decisions.", "Crop proposals require the user's selection before applying them to clip.crop."],
    }
    if mode == "ollama":
        chosen = sorted({round(i * (len(samples)-1) / max(1, min(semantic_samples,len(samples))-1)) for i in range(min(semantic_samples,len(samples)))})
        report["vision_model"] = model
        try:
            for index in chosen:
                samples[index]["semantic"] = describe_frame(within(folder, samples[index]["image"]), model, endpoint or "http://127.0.0.1:11434/api/chat")
        except EditorError as error:
            report["semantic_status"] = "failed"
            report["semantic_error"] = str(error)
            write_json(target / "footage-analysis.partial.json", report, replace=True)
            raise
        report["semantic_status"] = "completed-model-proposals"
    write_json(report_path, report)
    return report_path
