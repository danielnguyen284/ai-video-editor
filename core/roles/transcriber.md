# Transcriber

Offer local STT, a user-supplied timed transcript or no speech processing; record the user's choice first. Use `transcribe` when local STT was selected. It produces source timestamps and word timings with faster-whisper. The first use downloads the selected model. CPU/int8 is the starter default; CUDA is opt-in for a configured machine.

Read [Whisper setup guidance](../../README.md#whisper) on a new machine. The setup flag installs the package, not model weights. Before a first model download, explain the large-v3 default (about 3 GB plus dependencies/cache, potentially slow on CPU) and a lighter alternative, then use the user's chosen model explicitly. A previously selected model does not need another question. Record the choice in the job's intake/setup notes without adding unsupported setup fields. Distinguish downloading the model from running inference; do not silently switch models when a download is slow. Reuse cached weights or a complete compatible local model directory when available. Supplied transcripts and skipped STT require no model download.

Read the domain glossary from the job's resolved skill snapshot. Keep ASR output in `raw.json`, edit only `cleaned.json`, and record each correction with its segment/word and reason. If changing word text, update both word text and segment text so captions reflect the correction.

Do not infer financial numbers from a plausible company/ticker. Listen again or mark uncertainty. Preserve source timestamps; output timeline mapping happens during rendering. No speech means this role can be skipped and captions left off.
