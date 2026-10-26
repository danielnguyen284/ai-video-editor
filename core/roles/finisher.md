# Finisher

Execute `render` for the requested job/revision only after explicit user choices have been recorded. It validates executable plan structure and matching decision hashes, writes the filter graph and command, and invokes FFmpeg without a shell. This records the user's selections, not content review by AI.

Supported operations: one source video, cut/reorder/repeat clips at 1x speed, per-clip fixed source crop plus output crop/pad, image/logo/video overlays (including Remotion alpha assets), ASS captions remapped from source word timings or explicit timeline cues, voice gain, background music and ducking. Read `core/schemas/visuals-and-footage.md` for layers. Remotion assets must already have been rendered before this command.

Keep outputs and logs in the revision folder. Existing exports must stay available; create a new revision for changes. On success, return `renders/video.mp4` and revision. On failure, use `ffmpeg.log` to resolve the command error; do not start a quality-review loop.
