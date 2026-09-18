# Brag plan — CST4990 dissertation viva video

Adapted from a product-launch brief to an academic-viva explainer: this project
has no website/UI, so the "product" being shown is the experimental finding
itself, using real figures already generated for the dissertation.

## 9-question rubric

1. **What is the app?** Not an app — an MSc dissertation experiment. It tests
   whether flooding a firewall's CPU with random noise can hide a timing
   side-channel from a machine-learning attacker trying to guess the
   firewall's configuration.

2. **What is the funniest/most impressive claim?** A single accuracy number
   barely moves (90.6% → 90.4%) and looks like the defence does nothing — but
   the attacker actually needs to watch twice as long to get that number. The
   "aha": a single statistic lies about what's really happening.

3. **What is the visual hook?** The observation-budget sweep curve
   (`fig3b_sweep_curve_verdict.png`) — two lines that separate, then
   reconverge. That shape *is* the finding.

4. **What should be shown?** The Chapter 3 architecture diagram (the
   experimental setup) and the sweep curve, both already built for the
   dissertation, plus 2-3 real numbers as clean text cards.

5. **Shortest satisfying video?** ~25 seconds — enough to state the problem,
   show the method, land the finding, without padding.

6. **Tone.** Preset: `polished`. Direction: a quiet, serious research
   explainer suitable for opening a viva presentation — no jokes, no hype
   language, no comedic timing. Confidence comes from the result being
   genuinely couninterintuitive, not from editing tricks.

7. **Audio.** No music, no SFX, no narration for this pass (silent, caption-led)
   — the safest choice for playing inside a formal academic presentation where
   the presenter will be talking over/around it. Text on screen must therefore
   be fully self-sufficient and readable without narration.

8. **Share caption.** "Does adding noise stop a firewall timing leak? Not
   quite — it just makes the attacker wait twice as long. A summary of my
   MSc dissertation (CST4990, Middlesex University)."

9. **User flow worth showing.** Not a UI flow — a findings flow:
   leak exists → defence applied → single number looks unchanged →
   observation-budget curve reveals the real effect → cost of the defence.

## Storyboard (target ~24s, landscape 16:9)

| # | Time | Visual | On-screen text |
|---|---|---|---|
| 1 | 0.0–2.5s | Plain title card, black text on white | "Can noise hide a firewall from an attacker?" |
| 2 | 2.5–6.0s | Ch3 architecture diagram fades in | "A timing leak. A machine-learning attacker. A noise-based defence." |
| 3 | 6.0–9.5s | Big number card | "Accuracy: 90.6% → 90.4%" then small text beneath: "barely moved" |
| 4 | 9.5–12.5s | Same card, text changes | "So does the defence do... nothing?" |
| 5 | 12.5–19.0s | Sweep curve figure (fig3b) animates in, two lines revealed left-to-right | "The attacker needs 2x the observation time to catch up." |
| 6 | 19.0–22.5s | Cost card | "Cost: up to +536% CPU, +148% tail latency" |
| 7 | 22.5–24.5s | Closing card, same plain style as opener | "A rate-limiting control — not a fix. CST4990, Sarfraz Masood." |

Transitions: simple crossfades only, no spins/bounces/zoom-punches — matches
the polished/serious direction. No SFX or music cues (silent, per audio
decision above).

## Assets to use (already exist, not generated for this video)

- `build/assets/ch3_architecture.png` — experimental architecture diagram
- `results/run04/figures/fig3b_sweep_curve_verdict.png` — the headline sweep curve
- Numbers sourced directly from `CH4_NUMBERS.md` / `CH4_RESULTS.md` (no new
  numbers invented for the video)
