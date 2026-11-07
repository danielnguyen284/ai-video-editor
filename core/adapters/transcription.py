from __future__ import annotations

import shutil
from pathlib import Path

from core.common import EditorError, executable, read_json, timestamp, within, write_json
from core.adapters.ffmpeg import execute
from core.decisions import require_setup
from core.workflow_defaults import transcription_options, workflow_defaults


def transcribe(folder, model_name=None, device=None):
    from core.jobs import revision_folder
    revision = revision_folder(folder)
    config = read_json(revision / "resolved-config.json")
    defaults = workflow_defaults(config)
    decisions = read_json(revision / "decisions.json") if (revision / "decisions.json").is_file() else None
    if decisions and decisions["setup"]["status"] == "selected":
        choices = require_setup(revision)
        if not choices["setup"]["answers"]["transcription"]:
            raise EditorError("Local transcription was not selected. Use the supplied transcript or ask the user to change the choice.")
    elif not defaults["transcription"].get("allow_before_creative_setup", False):
        require_setup(revision)
    raw_output = folder / "transcript/raw.json"
    cleaned_output = folder / "transcript/cleaned.json"
    if raw_output.exists() or cleaned_output.exists():
        raise EditorError("Transcript already exists; preserve it and edit cleaned.json instead of overwriting.")
    job = read_json(folder / "job.json")
    media = within(folder, job["assets"][0]["path"])
    if not job["input"]["media"]["has_audio"]:
        raise EditorError("No audio stream. Leave captions disabled or supply a transcript manually.")
    options = transcription_options(config, model_name, device)
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise EditorError("Install transcription: .venv\\Scripts\\python.exe -m pip install -r requirements-stt.txt") from error
    # Technical provenance is not a fabricated user reply or approval of the edit.
    processing = {"schema_version": "1.0", "job_id": job["job_id"], "revision": revision.name,
                  "resolved_at": timestamp(), "workflow_ref": f"revisions/{revision.name}/resolved-config.json#workflow_defaults" if "workflow_defaults" in config else "preferences/workflow.json",
                  "options": options}
    history_path = folder / "transcript/processing.json"
    history = read_json(history_path) if history_path.is_file() else {"attempts": []}
    history["attempts"].append(processing)
    write_json(history_path, history, replace=history_path.exists())
    wav = folder / "transcript/audio.wav"
    execute([executable("ffmpeg"), "-nostdin", "-y", "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", str(wav)], folder / "transcript/extract.log")
    glossary = " ".join(
        text.strip() for skill in config["skills"] for name, text in skill["files"].items()
        if name.endswith("glossary.txt")
    )
    location = "existing local weights; no download" if Path(options["model"]).is_dir() else "explicit model name; uncached weights may download"
    print(f"Loading {options['model']} on {options['device']} ({location}).", flush=True)
    model = WhisperModel(options["model"], device=options["device"], compute_type=options["compute_type"])
    segments, info = model.transcribe(
        str(wav), language=config["profile"]["language"], word_timestamps=options["word_timestamps"],
        vad_filter=True, initial_prompt=glossary[:500] or None,
    )
    output = {
        "schema_version": "1.0", "job_id": job["job_id"], "revision": 0,
        "asset_id": job["assets"][0]["asset_id"], "created_at": timestamp(),
        "model": options["model"], "processing": options, "language": info.language,
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
