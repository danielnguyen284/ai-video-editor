"""Standing technical choices; never approves an edit or downloads model weights."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from core.common import EditorError, ROOT, read_json, within


def workflow_defaults(config=None, root=ROOT):
    frozen = (config or {}).get("workflow_defaults")
    return deepcopy(frozen if frozen is not None else read_json(Path(root) / "preferences/workflow.json"))


def transcription_options(config, model_name=None, device=None, root=ROOT):
    defaults = workflow_defaults(config, root)
    selected = defaults["transcription"]
    effective_model = model_name or selected["model"]
    if effective_model == selected["model"]:
        model_dir = within(root, selected["local_model_dir"])
        required = ("model.bin", "config.json", "tokenizer.json", "vocabulary.json")
        missing = [name for name in required if not (model_dir/name).is_file() or not (model_dir/name).stat().st_size]
        if missing:
            raise EditorError(f"Selected local {selected['model']} model is missing/incomplete at {model_dir}: {', '.join(missing)}. Restore this model or supply its compatible local directory with --model. No model was changed or downloaded.")
        effective_model = str(model_dir)
    elif Path(effective_model).is_dir():
        effective_model = str(Path(effective_model).resolve())
    effective_device = device or selected["device"]
    if effective_device not in ("cpu", "cuda"):
        raise EditorError("Transcription device must be cpu or cuda.")
    compute_type = selected["compute_type"] if effective_device == selected["device"] else ("float16" if effective_device == "cuda" else "int8")
    return {"model": str(effective_model), "model_id": selected["model"] if model_name is None or model_name == selected["model"] else str(model_name),
            "device": effective_device, "compute_type": compute_type,
            "word_timestamps": selected["word_timestamps"], "selection_source": "explicit-cli-argument" if model_name is not None else "standing-workflow",
            "device_selection_source": "explicit-cli-argument" if device is not None else "standing-workflow",
            "workflow_version": defaults["version"]}
