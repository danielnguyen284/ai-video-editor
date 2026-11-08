"""Keyframed source zoom shared by export, lock fingerprints and tests.

Keyframes are anchored to source seconds, so trimming, splitting and speed
changes keep a punch-in on the same spoken word. `x`/`y` are the focal point
(0-1) inside the clip's source picture after its fixed crop; that point stays
in place while the picture scales around it, like CSS transform-origin.
"""
from core.common import EditorError
from core.validation import number, supported_keys

EASES = ("linear", "in", "out", "in-out", "hold")
DEFAULT_EASE = "in-out"
MAX_KEYFRAMES = 32
MAX_SCALE = 4.0


def validate_zoom(zoom, duration):
    if not isinstance(zoom, list) or not 1 <= len(zoom) <= MAX_KEYFRAMES:
        raise EditorError(f"Clip zoom needs 1-{MAX_KEYFRAMES} keyframes.")
    previous = None
    for key in zoom:
        supported_keys(key, "source_seconds scale x y ease", "zoom keyframe")
        seconds = number(key["source_seconds"], "zoom source_seconds")
        if seconds > duration + 0.001:
            raise EditorError("Zoom keyframe lies beyond the input video.")
        if previous is not None and seconds <= previous:
            raise EditorError("Zoom keyframes need strictly increasing source_seconds.")
        previous = seconds
        if number(key["scale"], "zoom scale", 1) > MAX_SCALE:
            raise EditorError(f"Zoom scale must be between 1 and {MAX_SCALE:g}.")
        for axis in ("x", "y"):
            if number(key[axis], f"zoom {axis}") > 1:
                raise EditorError("Zoom focal point x/y must be between 0 and 1.")
        if key.get("ease", DEFAULT_EASE) not in EASES:
            raise EditorError("Zoom ease must be one of: " + ", ".join(EASES) + ".")


def eased(u, ease):
    if ease == "hold":
        return 0.0
    if ease == "in":
        return u * u
    if ease == "out":
        return u * (2 - u)
    if ease == "in-out":
        return u * u * (3 - 2 * u)
    return u


def zoom_at(zoom, seconds):
    """(scale, x, y) at a source time; holds the first/last keyframe outside the range."""
    values = lambda key: (key["scale"], key["x"], key["y"])
    if seconds < zoom[0]["source_seconds"]:
        return values(zoom[0])
    for a, b in zip(zoom, zoom[1:]):
        if seconds < b["source_seconds"]:
            u = (seconds - a["source_seconds"]) / (b["source_seconds"] - a["source_seconds"])
            k = eased(u, b.get("ease", DEFAULT_EASE))
            return tuple(va + (vb - va) * k for va, vb in zip(values(a), values(b)))
    return values(zoom[-1])


def clip_zoom_frames(clip, fps):
    """Zoom value for every output frame of a clip, or None when the picture never scales."""
    zoom = clip.get("zoom")
    if not zoom:
        return None
    rate = clip.get("playback_rate", 1.0)
    frames = clip["timeline_out_frame"] - clip["timeline_in_frame"]
    values = [zoom_at(zoom, clip["source_in_seconds"] + n * rate / fps) for n in range(frames)]
    return values if any(scale != 1 for scale, _, _ in values) else None


def _number(value):
    text = f"{value:.9g}"
    return f"({text})" if value < 0 else text


def _piecewise(points, name, frame_of):
    if all(key[name] == points[0][name] for key in points):
        return _number(points[0][name])
    expression = _number(points[-1][name])
    for a, b in reversed(list(zip(points, points[1:]))):
        fa, fb = frame_of(a), frame_of(b)
        u = f"clip((in-{_number(fa)})/{_number(fb - fa)},0,1)"
        k = {"hold": "0", "in": f"{u}*{u}", "out": f"{u}*(2-{u})",
             "in-out": f"{u}*{u}*(3-2*{u})", "linear": u}[b.get("ease", DEFAULT_EASE)]
        segment = _number(a[name]) if a[name] == b[name] else f"{_number(a[name])}+{_number(b[name] - a[name])}*{k}"
        expression = f"if(lt(in,{_number(fb)}),{segment},{expression})"
    return f"if(lt(in,{_number(frame_of(points[0]))}),{_number(points[0][name])},{expression})"


def zoom_filter(clip, fps):
    """FFmpeg perspective filter for one clip chain (frame `in` 0 = clip start), or ''.

    perspective samples with subpixel accuracy, so slow push-ins do not jitter
    the way integer zoompan crops do, and scale 1 is an exact identity.
    """
    if clip_zoom_frames(clip, fps) is None:
        return ""
    zoom, rate, start = clip["zoom"], clip.get("playback_rate", 1.0), clip["source_in_seconds"]
    end = start + (clip["timeline_out_frame"] - clip["timeline_in_frame"]) * rate / fps
    # Only keyframes bracketing this clip affect it; keep expressions short.
    first = max([i for i, key in enumerate(zoom) if key["source_seconds"] <= start] or [0])
    last = min([i for i, key in enumerate(zoom) if key["source_seconds"] >= end] or [len(zoom) - 1])
    points = zoom[first:last + 1]
    frame_of = lambda key: (key["source_seconds"] - start) * fps / rate
    s, x, y = (_piecewise(points, name, frame_of) for name in ("scale", "x", "y"))
    left, top = f"({x})*W*(1-1/({s}))", f"({y})*H*(1-1/({s}))"
    right, bottom = f"{left}+W/({s})", f"{top}+H/({s})"
    corners = {"x0": left, "y0": top, "x1": right, "y1": top, "x2": left, "y2": bottom, "x3": right, "y3": bottom}
    return "perspective=" + ":".join(f"{key}='{value}'" for key, value in corners.items()) + ":interpolation=cubic:eval=frame"
