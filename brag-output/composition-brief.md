# Hyperframes Composition Brief: CST4990 dissertation viva video

## Objective
A short, serious explainer video summarizing the dissertation's central finding,
to open a viva presentation alongside slides and a poster.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: ~24.5 seconds

## Source Material
- Project root: `C:\Users\abdul\CST4990-dissertation`
- Primary content read: `CH4_NUMBERS.md`, `CH4_RESULTS.md`, `CH3_METHODOLOGY.md`
- Project name: "Algorithmic noise injection against a firewall side channel" (CST4990)
- Strongest claim: single-shot accuracy barely moves (90.6% → 90.4%) but the
  attacker needs ~2x the observation time to reach the same accuracy
- Key visuals to reuse: `assets/images/architecture.png` (Chapter 3 experimental
  architecture diagram), `assets/images/sweep_curve.png` (the observation-budget
  sweep curve, run04 — the dissertation's headline figure)
- Copy that must appear verbatim (real numbers, not invented for the video):
  - "90.6% → 90.4%"
  - "2x observation time"
  - "+536% CPU, +148% tail latency"

## Creative Direction
- Tone preset: polished
- Creative direction: a quiet, serious research explainer for an academic viva
  — no jokes, no hype language, no comedic timing or fast-cut energy
- Angle: a single accuracy number looks like the defence does nothing; the
  real effect only shows up when you look at how long the attacker has to
  observe, not just their final accuracy
- Hook (0-2.5s): "Can noise hide a firewall from an attacker?"
- Outro (22.5-24.5s): "A rate-limiting control — not a fix. CST4990, Sarfraz Masood."
- Avoid: generic language, decorative motion unrelated to the content, any
  invented numbers not sourced from the dissertation

## Visual Identity
- Background: white (#ffffff)
- Text: near-black (#111827)
- Accent (for key numbers only): deep blue (#1d4ed8)
- Display/body font: system font stack (no custom webfont — avoids needing
  a shipped @font-face for a one-off academic video)
- Visual references: the two PNGs above, used at their real aspect ratio,
  never stretched or cropped in a way that misrepresents the data

## Storyboard
Scene summary (from `brag-plan.md`):
1. Title card — 2.5s — "Can noise hide a firewall from an attacker?"
2. Architecture diagram — 3.5s — diagram + "A timing leak. A machine-learning attacker. A noise-based defence."
3. Accuracy number card — 3.5s — "Accuracy: 90.6% → 90.4%" / "barely moved"
4. Turn card — 3.0s — "So does the defence do... nothing?"
5. Sweep curve reveal — 6.5s — figure + "The attacker needs 2x the observation time to catch up."
6. Cost card — 3.5s — "Cost: up to +536% CPU, +148% tail latency"
7. Closing card — 2.0s — "A rate-limiting control — not a fix. CST4990, Sarfraz Masood."

## Audio
- Audio role: intentional silence
- Audio arc: none — the presenter will speak over/around this during the viva,
  so a voice or music track would compete with them
- Music: none
- Audio-reactive treatment: none
- SFX: none

## Hyperframes Instructions
Build to the composition contract in `hyperframes-core`, motion choices per
`hyperframes-animation` (simple fades/slides only — no bounce, no spin, no
zoom-punch, matching the polished/serious direction), no audio track at all.
Run `hyperframes check` before render.
