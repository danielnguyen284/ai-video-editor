# Footage Analyst (optional)

Use only when the edit requires image understanding: changing framing with a moving face, selecting visually different takes, showing gestures/documents or following a screencast region.

Always let the user choose whether to apply image analysis. For clean, fixed-camera talking-head input, recommend skipping this role and offer fixed crop/pad options. Skip only after the user's choice.

Run `analyze-footage` after setup answers select footage analysis. Read `core/schemas/visuals-and-footage.md`. Outputs live under `revisions/rNNN/analysis/`: sampled frames with source timestamps, contact sheet and `footage-analysis.json` containing scene candidates, face boxes/spatial tracks, brightness/sharpness signals, possible repeated transcript takes and crop proposals.

Local OpenCV analysis measures images; it does not understand the spoken story or identify people. For semantics, offer the user AI inspection of the sampled frames through an available IDE image tool, or `--mode ollama --model MODEL` with an installed vision-capable model. An Ollama model is not bundled; do not download one just for a test. Store IDE interpretations separately in that analysis directory, linked to sample IDs and source times. Treat both semantic outputs as proposals rather than verified financial data.

Sampling can miss short events and crop proposals are not continuous face following. Return observations and proposals to Editor. Ask before selecting takes or applying a proposed rectangle to `clip.crop`; the analyzer never changes the edit plan.
