"""Signal check: is the side channel measurable at all?

Run this FIRST. It answers the question the whole dissertation rests on - does
nftables rule depth produce a timing difference this harness can actually see?
- in about thirty seconds, before committing to a full collection run.

    sudo -E python3 snr_check.py

Reported statistics:

  median        median nanoseconds per packet, per configuration
  Cohen's d     standardised effect size between shallow and deep
  AUC           probability a random deep batch is slower than a random
                shallow one; 0.5 means no signal, 1.0 means perfect separation

Interpretation:
  AUC >= 0.90   strong leak - proceed to the full run
  0.65 - 0.90   usable leak - proceed, but raise PACKETS_PER_BATCH
  < 0.65        too weak - see README, "If the signal is weak"
"""

from __future__ import annotations

import os
import statistics
import sys

import config as C
import firewall
from collect import drain, open_sockets, timed_batch

BATCHES = 120
WARMUP = 20


def measure(cfg: C.FirewallConfig, sender, listener, payload, addr) -> list[float]:
    firewall.apply_config(cfg)
    for _ in range(WARMUP):
        timed_batch(sender, payload, addr)
        drain(listener)

    samples = []
    for _ in range(BATCHES):
        ns, _ = timed_batch(sender, payload, addr)
        drain(listener)
        samples.append(ns)
    return samples


def cohens_d(a: list[float], b: list[float]) -> float:
    va, vb = statistics.variance(a), statistics.variance(b)
    pooled = (((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2)) ** 0.5
    if pooled == 0:
        return float("inf")
    return (statistics.mean(b) - statistics.mean(a)) / pooled


def auc(shallow: list[float], deep: list[float]) -> float:
    """Mann-Whitney U / (n*m) - rank-based, so outliers cannot inflate it."""
    wins = ties = 0
    for s in shallow:
        for d in deep:
            if d > s:
                wins += 1
            elif d == s:
                ties += 1
    return (wins + 0.5 * ties) / (len(shallow) * len(deep))


def main() -> int:
    if os.geteuid() != 0:
        print("error: must run as root: sudo -E python3 snr_check.py", file=sys.stderr)
        return 1

    firewall.preflight()
    sender, listener = open_sockets()
    payload = b"\x00" * C.PAYLOAD_BYTES
    addr = (C.PROBE_HOST, C.PROBE_PORT)

    print(f"{BATCHES} batches x {C.PACKETS_PER_BATCH} packets per configuration")
    print(f"depths: shallow={C.SHALLOW_DEPTH} rules, deep={C.DEEP_DEPTH} rules\n")

    results: dict[str, list[float]] = {}
    try:
        for cfg in C.CONFIGS:
            samples = measure(cfg, sender, listener, payload, addr)
            results[cfg.name] = samples
            print(f"  {cfg.name:16s} median {statistics.median(samples):8.1f} ns/pkt"
                  f"   iqr {_iqr(samples):7.1f}")
    finally:
        sender.close()
        listener.close()
        try:
            firewall.teardown()
        except firewall.FirewallError as exc:
            print(f"warning: teardown failed: {exc}", file=sys.stderr)

    print("\nshallow vs deep, per verdict:")
    verdict_auc = []
    for verdict in ("accept", "drop"):
        shallow = results[f"{verdict}_shallow"]
        deep = results[f"{verdict}_deep"]
        a = auc(shallow, deep)
        verdict_auc.append(a)
        print(f"  {verdict:7s} d = {cohens_d(shallow, deep):6.2f}   AUC = {a:.3f}")

    print("\naccept vs drop, per depth:")
    for depth in ("shallow", "deep"):
        acc = results[f"accept_{depth}"]
        drp = results[f"drop_{depth}"]
        print(f"  {depth:7s} d = {cohens_d(drp, acc):6.2f}   AUC = {auc(drp, acc):.3f}")

    best = max(verdict_auc)
    print()
    if best >= 0.90:
        print(f"STRONG leak (AUC {best:.3f}). Proceed to the full run.")
    elif best >= 0.65:
        print(f"USABLE leak (AUC {best:.3f}). Proceed; consider raising "
              f"PACKETS_PER_BATCH from {C.PACKETS_PER_BATCH} to "
              f"{C.PACKETS_PER_BATCH * 4}.")
    else:
        print(f"WEAK leak (AUC {best:.3f}). Do not start the full run yet - "
              f"see README, 'If the signal is weak'.")
    return 0


def _iqr(xs: list[float]) -> float:
    q = statistics.quantiles(xs, n=4)
    return q[2] - q[0]


if __name__ == "__main__":
    sys.exit(main())
