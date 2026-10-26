"""Persist user choices made in chat; never select an option automatically."""
from __future__ import annotations

from copy import deepcopy

from core.common import EditorError, digest, read_json, timestamp, write_json

SETUP_FIELDS = {
    "style", "domain", "output", "footage_analysis", "transcription", "editing",
    "captions", "research", "visuals", "audio",
}


def initial_decisions(job_id, revision, inherited=None):
    return {
        "schema_version": "1.0", "job_id": job_id, "revision": revision,
        "setup": deepcopy(inherited) if inherited else {"status": "pending", "answers": None},
        "edit_plan": {"status": "pending"},
        "history": [],
    }


def questions(revision):
    """Suggestions are not answers; the agent presents these in small chat batches."""
    config = read_json(revision / "resolved-config.json")
    return {
        "decisions": read_json(revision / "decisions.json") if (revision / "decisions.json").is_file() else initial_decisions(config["job_id"], config["revision"]),
        "suggested_choices": {
            "style": [config["profile"]["skills"]["style"]["id"], "Another installed style or create one from your reference"],
            "domain": [config["profile"]["skills"]["domain"]["id"], "Another installed domain or create a new domain skill"],
            "output": ["Vertical 9:16", "Horizontal 16:9", "Keep source aspect; specify dimensions"],
            "footage_analysis": ["Skip image analysis", "Local scene/face/crop analysis", "Local analysis plus semantic vision through Ollama or the IDE agent"],
            "transcription": ["Local STT (first use downloads model)", "Use supplied timed transcript", "No speech processing"],
            "editing": ["Keep original order, remove stumbles/repetition", "Reorder around a stronger hook", "Only make cuts I specify"],
            "captions": ["Styled captions", "Simple captions", "No captions"],
            "research": ["Use supplied materials only", "Research specified claims/assets", "No added research"],
            "visuals": ["Framing and captions only", "Image/logo/B-roll overlays", "Remotion metric card, bar chart, lower third or KineticScene text/cards/progress"],
            "audio": ["Voice only", "Supplied background music with ducking", "Propose audio treatment before applying it"],
        },
        "note": "Only the current profile's skill pair is guaranteed installed. Check skills/ before offering another as ready to use.",
    }


def validate_answers(answers):
    if not isinstance(answers, dict) or set(answers) != SETUP_FIELDS:
        raise EditorError("Setup answers must contain exactly: " + ", ".join(sorted(SETUP_FIELDS)))
    for key in ("footage_analysis", "transcription", "captions"):
        if not isinstance(answers[key], bool):
            raise EditorError(f"Decision {key} must be true or false.")
    for key in ("style", "domain", "editing", "research", "visuals", "audio"):
        if not isinstance(answers[key], str) or not answers[key].strip():
            raise EditorError(f"Decision {key} needs the user's selected option or description.")
    output = answers["output"]
    if not isinstance(output, dict) or set(output) != {"width", "height", "fps", "fit"}:
        raise EditorError("Decision output needs width, height, fps and fit.")
    for key in ("width", "height", "fps"):
        if isinstance(output[key], bool) or not isinstance(output[key], int) or output[key] < 1:
            raise EditorError(f"Decision output.{key} must be a positive integer.")
    if output["fit"] not in ("pad", "crop"):
        raise EditorError("Decision output.fit must be pad or crop.")


def require_setup(revision):
    path = revision / "decisions.json"
    if not path.is_file():
        raise EditorError("Missing user choices. Present options and record setup choices before continuing.")
    decisions = read_json(path)
    if decisions["setup"]["status"] != "selected":
        raise EditorError("Waiting for user setup choices. Ask about style, domain, footage, cuts, captions, visuals, audio and output.")
    answers = decisions["setup"]["answers"]
    validate_answers(answers)
    config = read_json(revision / "resolved-config.json")
    for kind in ("style", "domain"):
        if answers[kind] != config["profile"]["skills"][kind]["id"]:
            raise EditorError(f"Selected {kind} is not reflected in the revision config. Resolve the selected skill/profile first.")
    return decisions


def require_render_choices(revision):
    decisions = require_setup(revision)
    plan = read_json(revision / "edit-plan.json")
    answers = decisions["setup"]["answers"]
    if any(plan["export"].get(key) != value for key, value in answers["output"].items()):
        raise EditorError("Plan output does not match the user's choices.")
    if plan["captions"]["enabled"] != answers["captions"]:
        raise EditorError("Caption setting does not match the user's choice.")
    selected = decisions["edit_plan"]
    if selected["status"] != "selected":
        raise EditorError("Present the concrete edit proposal and wait for the user's selection before rendering.")
    if selected["plan_sha256"] != digest(revision / "edit-plan.json") or selected["config_sha256"] != digest(revision / "resolved-config.json"):
        raise EditorError("Plan/config changed after the user's selection. Ask about the changed decisions and record the new plan choice.")
    return decisions


def record_choice(revision, stage, user_message, *, answers=None, summary=None):
    if not user_message.strip():
        raise EditorError("Record the actual user reply, not an inferred default.")
    if (revision / "render-manifest.json").exists() or (revision / "renders/video.mp4").exists():
        raise EditorError("Create a new revision before changing choices for an exported video.")
    path = revision / "decisions.json"
    if path.is_file():
        decisions = read_json(path)
    else:
        config = read_json(revision / "resolved-config.json")
        decisions = initial_decisions(config["job_id"], config["revision"])
    if stage == "setup":
        validate_answers(answers)
        value = {"status": "selected", "answers": answers, "user_message": user_message, "selected_at": timestamp()}
        decisions["setup"] = value
        # Changing the setup requires a matching new edit proposal.
        decisions["edit_plan"] = {"status": "pending"}
    else:
        require_setup(revision)
        if not summary or not summary.strip():
            raise EditorError("Describe the concrete edit option selected by the user.")
        value = {
            "status": "selected", "summary": summary, "user_message": user_message,
            "selected_at": timestamp(), "plan_sha256": digest(revision / "edit-plan.json"),
            "config_sha256": digest(revision / "resolved-config.json"),
        }
        decisions["edit_plan"] = value
    decisions["history"].append({"stage": stage, "selection": deepcopy(value)})
    write_json(path, decisions, replace=True)
    return path
