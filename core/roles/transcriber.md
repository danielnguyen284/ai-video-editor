# Transcriber

Read [editing-workflow.md](../editing-workflow.md). The standing choice for needed speech transcription is faster-whisper large-v3 local, CPU/int8 with word timestamps. Reuse matching existing/supplied transcripts; do not ask large-v3 versus small again or run STT when the brief says not to. `transcribe JOB` resolves the selected local directory, and refuses missing/incomplete weights without downloading or switching. A user-selected model/directory/device can explicitly override it. The standing processing policy allows local STT before full creative setup; log actual provenance in `transcript/processing.json` and keep edit decisions pending. Preserve raw transcript and log corrections in cleaned.json.

Read [Whisper setup guidance](../../README.md#whisper) when preparing a new machine. Setup installs the package, not weights. If large-v3 local is missing, explain that restoring the selected model needs about 3 GB plus dependencies/cache; ask only about obtaining/restoring that same model when needed. Do not reopen model choice or suggest a downgrade merely because inference/download is slow. Record real model provenance without adding unsupported setup-answer fields. Supplied transcripts and skipped STT require no model download.

Read the domain glossary from the job's resolved skill snapshot. Keep ASR output in `raw.json`, edit only `cleaned.json`, and record each correction with its segment/word and reason. If changing word text, update both word text and segment text so captions reflect the correction.

Do not infer financial numbers from a plausible company/ticker. Listen again or mark uncertainty. Preserve source timestamps; output timeline mapping happens during rendering. No speech means this role can be skipped and captions left off.
