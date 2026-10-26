from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
import re
import shutil

from core.common import EditorError, ROOT, identifier, read_json, resolve_profile, timestamp, within, write_json
from core.adapters.ffmpeg import probe
from core.decisions import initial_decisions


def job_folder(job_id):
    folder = ROOT / "jobs" / identifier(job_id)
    if not (folder / "job.json").is_file():
        raise EditorError(f"Job not found: {job_id}")
    return folder


def revision_folder(folder, revision=None):
    if revision is None:
        revisions = sorted(p for p in (folder / "revisions").glob("r[0-9]*") if re.fullmatch(r"r\d{3,}", p.name))
        if not revisions:
            raise EditorError("No revision exists for this job.")
        return max(revisions, key=lambda p: int(p.name[1:]))
    if not re.fullmatch(r"r\d{3,}", revision):
        raise EditorError("Revision must look like r001.")
    result = within(folder / "revisions", revision)
    if not (result / "edit-plan.json").is_file():
        raise EditorError(f"Revision not found: {revision}")
    return result


def create_job(job_id, video, profile_id, brief):
    identifier(job_id)
    source = Path(video).resolve()
    if not source.is_file():
        raise EditorError(f"Video not found: {source}")
    folder = ROOT / "jobs" / job_id
    if folder.exists():
        raise EditorError(f"Job already exists: {job_id}. Choose another ID or create a revision.")
    resolved = resolve_profile(profile_id)
    media = probe(source)
    if not media["has_video"]:
        raise EditorError("Input must contain a video stream.")
    export = resolved["profile"]["export"]
    fps = export["fps"]
    frames = math.floor(media["duration_seconds"] * fps + 1e-6)
    if frames < 1:
        raise EditorError("Video is shorter than one output frame.")
    for name in ("input", "transcript", "analysis", "research", "assets/music", "assets/visuals", "feedback", "revisions/r001"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    imported = folder / "input" / ("raw" + source.suffix.lower())
    shutil.copy2(source, imported)
    relative = imported.relative_to(folder).as_posix()
    job = {
        "schema_version": "1.0", "job_id": job_id, "created_at": timestamp(),
        "brief": brief, "profile_id": profile_id,
        "assets": [{"asset_id": "raw-001", "path": relative}],
        "input": {"original_path": str(source), "media": media},
        "optional_roles": {"footage_analyst": "awaiting-user-choice", "researcher": "awaiting-user-choice", "animator": "awaiting-user-choice"},
    }
    resolved.update({"job_id": job_id, "revision": 1})
    plan = {
        "schema_version": "1.0", "job_id": job_id, "revision": 1,
        "config_ref": "resolved-config.json", "fps": fps, "duration_frames": frames,
        "export": deepcopy(export),
        "clips": [{
            "clip_id": "clip-001", "asset_id": "raw-001", "source_in_seconds": 0,
            "source_out_seconds": frames / fps, "timeline_in_frame": 0,
            "timeline_out_frame": frames, "playback_rate": 1.0,
        }],
        "captions": merge_caption_defaults(resolved),
        "audio": deepcopy(resolved["settings"]["audio"]),
        "overlays": [],
        "notes": ["Initial plan keeps the full input. The editor must choose cuts from the brief/transcript."],
    }
    write_json(folder / "job.json", job)
    write_json(folder / "analysis" / "media.json", {"schema_version": "1.0", "job_id": job_id, "revision": 0, **media})
    write_json(folder / "resolved-config.json", resolved)
    write_json(folder / "revisions/r001/resolved-config.json", resolved)
    write_json(folder / "revisions/r001/edit-plan.json", plan)
    write_json(folder / "revisions/r001/decisions.json", initial_decisions(job_id, 1))
    return folder


def merge_caption_defaults(resolved):
    return {**deepcopy(resolved["settings"]["captions"]), "enabled": False, "transcript_ref": "transcript/cleaned.json"}


def new_revision(job_id, feedback, from_revision=None):
    folder = job_folder(job_id)
    source = revision_folder(folder, from_revision)
    return clone_revision(folder, source, feedback)


def clone_revision(folder, source, feedback):
    job_id = read_json(folder / "job.json")["job_id"]
    number = int(revision_folder(folder).name[1:]) + 1
    target = folder / "revisions" / f"r{number:03d}"
    target.mkdir()
    for filename in ("edit-plan.json", "resolved-config.json"):
        data = read_json(source / filename)
        data["revision"] = number
        if filename == "edit-plan.json":
            data.setdefault("notes", []).append(f"User feedback from {source.name}: {feedback}")
        write_json(target / filename, data)
    previous_decisions = read_json(source / "decisions.json") if (source / "decisions.json").is_file() else None
    write_json(target / "decisions.json", initial_decisions(job_id, number, previous_decisions["setup"] if previous_decisions else None))
    write_json(folder / "feedback" / f"r{number:03d}.json", {
        "schema_version": "1.0", "job_id": job_id, "revision": number,
        "viewed_revision": source.name, "prompt": feedback, "created_at": timestamp(),
        "status": "pending-editor-changes",
    })
    return target
