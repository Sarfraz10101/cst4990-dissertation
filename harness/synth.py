"""Synthetic trace generator - validates the analysis pipeline before real data.

This is a test fixture, not an experiment. It writes a CSV with exactly the
schema `collect.py` produces, from a latency model with *known* parameters, so
you can confirm that `attack.py` and `stats.py` recover an effect you planted
and report chance when you plant none.

The physics the model respects
------------------------------
A noise-injection defence burns CPU in parallel with the victim. Therefore it:

  * ADDS latency (contention) - it can never make chain traversal cheaper;
  * INFLATES variance (scheduling interference);
  * does NOT remove the deterministic cost difference between configurations.

That last point is the one that matters, and it is why `--signal-attenuation`
defaults to 0. Zero-mean additive noise does not delete a leak, it *buries* it:
averaging over enough batches pulls the signal back out, because the noise
averages toward zero while the signal does not. This is exactly the limitation
Chari et al. (1999) identified in noise-based countermeasures, and confirming it
on your own data is a genuine finding rather than a disappointment. Use
`sweep.py` to measure how many batches the attacker needs.

    # realistic pure-noise defence: heavy variance, signal intact
    python synth.py --out ../data/synth_noise.csv --noise-sigma-mult 8

    # hypothetical ideal defence that also perturbs the signal itself
    python synth.py --out ../data/synth_ideal.csv --signal-attenuation 0.9

    # no effect at all -> both conditions must sit at chance
    python synth.py --out ../data/synth_null.csv --null

Keep output in `data/synth_*.csv` so it can never be mistaken for a real run.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from config import BATCHES_PER_TRIAL, CONFIGS, DEEP_DEPTH, RANDOM_SEED

# Latency model, nanoseconds per packet. Plausible for loopback UDP on a modern
# core; the structure matters, not the absolute values.
BASE_NS = 1500.0
DEPTH_EFFECT_NS = 420.0    # cost of traversing DEEP_DEPTH extra rules
VERDICT_EFFECT_NS = 260.0  # accept costs more: the packet is actually delivered
TRIAL_SIGMA = 55.0         # between-trial drift (thermal, scheduling)
BATCH_SIGMA = 40.0         # within-trial jitter, defence inactive
SPIKE_RATE = 0.02          # fraction of batches hit by a scheduling spike
SPIKE_NS = 900.0

# Cost of the defence. Both are positive: contention slows the victim down.
NOISE_LATENCY_OFFSET_NS = 185.0
NOISE_CPU_PER_TRIAL_S = 0.021


def generate(
    trials_per_cell: int,
    noise_sigma_mult: float,
    signal_attenuation: float,
    effect_scale: float,
    null: bool,
    seed: int,
) -> pd.DataFrame:
    """Build a synthetic dataset.

    noise_sigma_mult:   variance inflation when the defence is active. This is
                        the realistic mechanism - it buries the signal.
    signal_attenuation: fraction of the deterministic signal the defence
                        actually removes. 0.0 is the honest default; raise it
                        only to model a hypothetically stronger countermeasure.
    """
    rng = np.random.default_rng(seed)

    schedule = [
        (cfg, noise)
        for cfg in CONFIGS
        for noise in (0, 1)
        for _ in range(trials_per_cell)
    ]
    rng.shuffle(schedule)

    rows = []
    for trial_idx, (cfg, noise) in enumerate(schedule):
        depth_term = DEPTH_EFFECT_NS if cfg.filler_rules == DEEP_DEPTH else 0.0
        verdict_term = VERDICT_EFFECT_NS if cfg.verdict == "accept" else 0.0
        signal = (depth_term + verdict_term) * effect_scale

        if null:
            signal = 0.0
        elif noise:
            signal *= (1.0 - signal_attenuation)

        sigma = BATCH_SIGMA * (noise_sigma_mult if noise else 1.0)
        contention = NOISE_LATENCY_OFFSET_NS if noise else 0.0

        trial_offset = rng.normal(0.0, TRIAL_SIGMA)
        mean_ns = BASE_NS + signal + contention + trial_offset

        ns = rng.normal(mean_ns, sigma, size=BATCHES_PER_TRIAL)
        spikes = rng.random(BATCHES_PER_TRIAL) < SPIKE_RATE
        ns += spikes * rng.exponential(SPIKE_NS, size=BATCHES_PER_TRIAL)
        # Latency cannot be negative; clip rather than let heavy noise produce
        # impossible values that would themselves be a giveaway feature.
        ns = np.maximum(ns, 1.0)

        noise_cpu = (
            NOISE_CPU_PER_TRIAL_S * rng.normal(1.0, 0.08) if noise else 0.0
        )
        victim_user = 0.004 * rng.normal(1.0, 0.1)
        victim_sys = 0.011 * rng.normal(1.0, 0.1) * (1.15 if noise else 1.0)

        for batch_idx in range(BATCHES_PER_TRIAL):
            rows.append((
                trial_idx, cfg.name, cfg.verdict, cfg.depth_label, noise,
                batch_idx, round(float(ns[batch_idx]), 1), 0,
                round(noise_cpu, 6), round(victim_user, 6), round(victim_sys, 6),
            ))

    return pd.DataFrame(rows, columns=[
        "trial_idx", "config", "verdict", "depth", "noise",
        "batch_idx", "ns_per_pkt", "send_errors",
        "noise_cpu_s", "victim_user_s", "victim_sys_s",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--trials", type=int, default=120,
                    help="trials per (config x condition) cell")
    ap.add_argument("--noise-sigma-mult", type=float, default=8.0,
                    help="variance inflation under the defence (realistic knob)")
    ap.add_argument("--signal-attenuation", type=float, default=0.0,
                    help="fraction of the deterministic signal removed; 0 is "
                         "the physically honest default")
    ap.add_argument("--effect-scale", type=float, default=1.0,
                    help="scale the planted leak; 0.3 simulates a weak channel")
    ap.add_argument("--null", action="store_true",
                    help="plant no effect at all (false-positive check)")
    ap.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = ap.parse_args()

    if not 0.0 <= args.signal_attenuation <= 1.0:
        ap.error("--signal-attenuation must be between 0 and 1")
    if args.noise_sigma_mult < 1.0:
        ap.error("--noise-sigma-mult must be >= 1 (the defence cannot reduce jitter)")

    df = generate(
        args.trials, args.noise_sigma_mult, args.signal_attenuation,
        args.effect_scale, args.null, args.seed,
    )
    df.to_csv(args.out, index=False)

    print("SYNTHETIC DATA - not a result")
    print(f"  rows               {len(df)}")
    print(f"  trials             {df['trial_idx'].nunique()}")
    print(f"  batches per trial  {BATCHES_PER_TRIAL}")
    print(f"  null               {args.null}")
    print(f"  effect_scale       {args.effect_scale}")
    print(f"  noise_sigma_mult   {args.noise_sigma_mult}")
    print(f"  signal_attenuation {args.signal_attenuation}")
    print(f"  -> {args.out}")
    print()
    print("expected outcome:")
    if args.null:
        print("  Both conditions at chance (0.25). Anything higher means the")
        print("  pipeline manufactures signal from nothing - a real bug.")
    else:
        print("  noise_off: well above chance.")
        if args.signal_attenuation > 0.6:
            print("  noise_on : collapsed toward chance, and it STAYS there as")
            print("             the batch budget grows (the signal is gone).")
        else:
            print(f"  noise_on : reduced at small batch budgets, but recovering")
            print(f"             as the budget grows - averaging defeats zero-mean")
            print(f"             noise. Run sweep.py to see the crossover.")
        print(f"  latency  : must INCREASE under noise "
              f"(~{NOISE_LATENCY_OFFSET_NS:.0f} ns contention). A decrease means")
        print(f"             the model or the analysis is wrong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
