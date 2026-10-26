import math

from core.common import EditorError


def number(value, label, minimum=0, *, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EditorError(f"{label} must be a finite number.")
    if value < minimum or (integer and not isinstance(value, int)):
        raise EditorError(f"Invalid {label}: {value}")
    return value


def supported_keys(data, allowed, label):
    if not isinstance(data, dict):
        raise EditorError(f"{label} must be an object.")
    extra = set(data) - set(allowed.split())
    if extra:
        raise EditorError(f"Unsupported {label} fields: {', '.join(sorted(extra))}. No fields are silently ignored.")
