from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys

from core.common import EditorError, executable, read_json
from core.decisions import questions, record_choice
from core.jobs import create_job, job_folder, new_revision, revision_folder
from core.adapters.ffmpeg import render
from core.adapters.transcription import transcribe


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Local role/skill video editing tools. The agent handles creative decisions.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check local tools; does not download a model")
    studio = commands.add_parser("editor", help="Open the local visual timeline editor")
    studio.add_argument("--port", type=int, default=8765)
    studio.add_argument("--no-open", action="store_true")
    new = commands.add_parser("new-job", help="Copy input, resolve skills and create an initial full-length plan")
    new.add_argument("job_id")
    new.add_argument("--video", required=True)
    new.add_argument("--profile", default="finance-premium-vi")
    new.add_argument("--brief", default="")
    speech = commands.add_parser("transcribe", help="Local STT; downloads the model on first use")
    speech.add_argument("job_id")
    speech.add_argument("--model", default="large-v3")
    speech.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    revision = commands.add_parser("revision", help="Clone a plan; the editor must apply the feedback afterwards")
    revision.add_argument("job_id")
    revision.add_argument("--feedback", required=True)
    revision.add_argument("--from-revision")
    export = commands.add_parser("render", help="Execute an edit plan with FFmpeg")
    export.add_argument("job_id")
    export.add_argument("--revision")
    export.add_argument("--dry-run", action="store_true")
    choices = commands.add_parser("choices", help="Show pending choices and suggested chat options; never auto-select")
    choices.add_argument("job_id")
    choices.add_argument("--revision")
    decide = commands.add_parser("decide", help="Record an explicit user reply from chat; does not interpret answers")
    decide.add_argument("job_id")
    decide.add_argument("--revision")
    decide.add_argument("--stage", choices=("setup", "edit-plan"), required=True)
    decide.add_argument("--user-message", required=True)
    decide.add_argument("--answers", help="JSON file of setup choices collected from the user")
    decide.add_argument("--summary", help="Concrete edit option selected by the user")
    motion = commands.add_parser("render-motion", help="Render a chosen Remotion template into a transparent asset")
    motion.add_argument("job_id")
    motion.add_argument("name", help="Unique asset name; preserves existing motion assets")
    motion.add_argument("--spec", required=True, help="Motion request JSON path relative to job root")
    motion.add_argument("--revision")
    analysis = commands.add_parser("analyze-footage", help="Analyze selected source footage; returns proposals without applying edits")
    analysis.add_argument("job_id")
    analysis.add_argument("--revision")
    analysis.add_argument("--mode", choices=("local", "ollama"), default="local")
    analysis.add_argument("--interval", type=float, default=1)
    analysis.add_argument("--max-samples", type=int, default=120)
    analysis.add_argument("--model", help="Installed Ollama vision model, required for ollama mode")
    analysis.add_argument("--vision-endpoint", help="Ollama /api/chat endpoint (default local port 11434)")
    analysis.add_argument("--semantic-samples", type=int, default=12)
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            missing = False
            for name in ("ffmpeg", "ffprobe"):
                try:
                    tool = executable(name)
                    result = subprocess.run([tool, "-version"], capture_output=True, text=True, encoding="utf-8")
                    if result.returncode:
                        raise EditorError(f"{name} returned exit code {result.returncode}")
                    print(f"OK {name}: {tool}\n  {result.stdout.splitlines()[0]}")
                except EditorError as error:
                    print(f"MISSING: {error}")
                    missing = True
            installed = importlib.util.find_spec("faster_whisper") is not None
            print("STT package: " + ("installed (model loads on first transcription)" if installed else "optional; install requirements-stt.txt"))
            print("Local footage analysis: " + ("installed" if importlib.util.find_spec("cv2") else "optional; install requirements-vision.txt"))
            from core.common import ROOT
            import shutil
            if shutil.which("node") and (ROOT / "motion/node_modules/@remotion/renderer").is_dir():
                result = subprocess.run([shutil.which("node"), str(ROOT / "motion/render.mjs"), "--doctor"], capture_output=True, text=True, encoding="utf-8")
                print("Motion: " + (result.stdout.strip() if result.returncode == 0 else result.stderr.strip()))
                missing = missing or result.returncode != 0
            else:
                print("Motion: optional; run npm.cmd ci in motion/")
            print("Semantic vision: optional Ollama model or agent inspection of sampled frames; no model downloaded by doctor.")
            print("Visual editor: " + ("ready; run ai_editor.py editor" if (ROOT / "editor/build/index.html").is_file() else "optional; run scripts/setup.ps1 -WithEditor"))
            return 1 if missing else 0
        if args.command == "editor":
            from core.editor_server import serve
            serve(args.port, not args.no_open)
        elif args.command == "new-job":
            result = create_job(args.job_id, args.video, args.profile, args.brief)
            print(f"Created: {result}\nSetup choices are pending. Present options to the user before transcription or editing.")
        elif args.command == "transcribe":
            print(transcribe(job_folder(args.job_id), args.model, args.device))
        elif args.command == "revision":
            result = new_revision(args.job_id, args.feedback, args.from_revision)
            print(f"Created: {result}\nFeedback is recorded. The editor must now apply changes to edit-plan.json before rendering.")
        elif args.command == "render":
            folder = job_folder(args.job_id)
            print(render(folder, revision_folder(folder, args.revision), dry_run=args.dry_run))
        elif args.command == "choices":
            folder = job_folder(args.job_id)
            print(json.dumps(questions(revision_folder(folder, args.revision)), ensure_ascii=False, indent=2))
        elif args.command == "decide":
            folder = job_folder(args.job_id)
            print(record_choice(
                revision_folder(folder, args.revision), args.stage, args.user_message,
                answers=read_json(args.answers) if args.answers else None, summary=args.summary,
            ))
        elif args.command == "render-motion":
            from core.adapters.motion import render_motion
            folder = job_folder(args.job_id)
            print(render_motion(folder, revision_folder(folder, args.revision), args.name, args.spec))
        elif args.command == "analyze-footage":
            from core.adapters.footage import analyze_footage
            folder = job_folder(args.job_id)
            print(analyze_footage(
                folder, revision_folder(folder, args.revision), mode=args.mode, interval=args.interval,
                max_samples=args.max_samples, model=args.model, endpoint=args.vision_endpoint,
                semantic_samples=args.semantic_samples,
            ))
        return 0
    except (EditorError, FileNotFoundError, FileExistsError, json.JSONDecodeError, KeyError, ValueError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
