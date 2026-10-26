# Sound Designer

Use the plan's `audio.voice_gain` and optional `audio.music` settings. Place user-supplied/permitted music inside the job; store its source/credit with the asset manifest.

The FFmpeg adapter can loop background music, apply a fixed gain and duck it against the speaker. Keep the voice prominent. No music/SFX catalog is bundled. Do not invent a local music path or add unimplemented cleanup/SFX fields to the plan.

For specialized audio cleanup or SFX placement, add an explicit FFmpeg operation/adapter for that request before claiming it was executed.
