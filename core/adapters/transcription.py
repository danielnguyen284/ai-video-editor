from __future__ import annotations

import shutil

from core.common import EditorError, executable, read_json, timestamp, within, write_json
from core.adapters.ffmpeg import execute
from core.decisions import require_setup


def transcribe(folder, model_name="large-v3", device="cpu"):
    from core.jobs import revision_folder
    decisions = require_setup(revision_folder(folder))
    if not decisions["setup"]["answers"]["transcription"]:
        raise EditorError("Local transcription was not selected. Use the supplied transcript or ask the user to change the choice.")
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise EditorError("Install transcription: .venv\\Scripts\\python.exe -m pip install -r requirements-stt.txt") from error
    raw_output = folder / "transcript/raw.json"
    cleaned_output = folder / "transcript/cleaned.json"
    if raw_output.exists() or cleaned_output.exists():
        raise EditorError("Transcript already exists; preserve it and edit cleaned.json instead of overwriting.")
    job = read_json(folder / "job.json")
    config = read_json(folder / "resolved-config.json")
    media = within(folder, job["assets"][0]["path"])
    if not job["input"]["media"]["has_audio"]:
        raise EditorError("No audio stream. Leave captions disabled or supply a transcript manually.")
    wav = folder / "transcript/audio.wav"
    execute([executable("ffmpeg"), "-nostdin", "-y", "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", str(wav)], folder / "transcript/extract.log")
    glossary = " ".join(
        text.strip() for skill in config["skills"] for name, text in skill["files"].items()
        if name.endswith("glossary.txt")
    )
    print(f"Loading {model_name} on {device}; the first run downloads the model.", flush=True)
    model = WhisperModel(model_name, device=device, compute_type="float16" if device == "cuda" else "int8")
    segments, info = model.transcribe(
        str(wav), language=config["profile"]["language"], word_timestamps=True,
        vad_filter=True, initial_prompt=glossary[:500] or None,
    )
    output = {
        "schema_version": "1.0", "job_id": job["job_id"], "revision": 0,
        "asset_id": job["assets"][0]["asset_id"], "created_at": timestamp(),
        "model": model_name, "language": info.language,
        "segments": [], "corrections": [],
    }
    for number, segment in enumerate(segments, 1):
        output["segments"].append({
            "segment_id": f"segment-{number:04d}", "start": segment.start, "end": segment.end,
            "text": segment.text.strip(), "avg_logprob": segment.avg_logprob,
            "words": [{"start": word.start, "end": word.end, "text": word.word, "probability": word.probability} for word in (segment.words or [])],
        })
        print(f"{segment.start:.2f}-{segment.end:.2f}: {segment.text.strip()}", flush=True)
    write_json(raw_output, output)
    shutil.copy2(raw_output, cleaned_output)
    return cleaned_output
