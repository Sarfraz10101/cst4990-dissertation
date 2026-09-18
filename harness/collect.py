"""Trace collector: measures nftables chain-traversal cost under each firewall
configuration, with and without the noise-injection defence.

Run inside the Lubuntu guest, as root (nft requires it):

    sudo -E python3 collect.py --out ../data/run01.csv
    sudo -E python3 collect.py --out ../data/smoke.csv --dry-run

Output is tidy long format - one row per timed batch - so it can be re-featurised
without recollecting, and opened directly in Excel.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import random
import socket
import subprocess
import sys
import time
from pathlib import Path

import config as C
import firewall
from noise import NoiseInjector

CLOCK = time.CLOCK_MONOTONIC_RAW


# ---------------------------------------------------------------------------
# Victim-side measurement primitives
# ---------------------------------------------------------------------------
def open_sockets() -> tuple[socket.socket, socket.socket]:
    """Create the probe sender and a real listener on the probe port.

    The listener is essential, not incidental. With nothing bound, an
    *accepted* packet makes the kernel generate an ICMP port-unreachable
    reply, and that reply costs far more than the chain traversal we are
    trying to measure - the classifier would be separating "ICMP sent" from
    "no ICMP sent" rather than reading the firewall's decision cost.
    """
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
    listener.bind((C.PROBE_HOST, C.PROBE_PORT))
    listener.setblocking(False)

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return sender, listener


def drain(listener: socket.socket) -> int:
    """Empty the listener's receive queue. Called outside timed regions."""
    count = 0
    while True:
        try:
            listener.recv(65535)
        except BlockingIOError:
            return count
        except OSError:
            return count
        count += 1


def timed_batch(sender: socket.socket, payload: bytes, addr: tuple[str, int]) -> tuple[float, int]:
    """Send one batch, returning (nanoseconds per packet, send errors).

    Attribute lookups are hoisted out of the loop so the timed region contains
    as little interpreter overhead as possible.
    """
    send = sender.sendto
    n = C.PACKETS_PER_BATCH
    errors = 0

    t0 = time.clock_gettime_ns(CLOCK)
    for _ in range(n):
        try:
            send(payload, addr)
        except OSError:
            errors += 1
    t1 = time.clock_gettime_ns(CLOCK)

    return (t1 - t0) / n, errors


def read_proc_stat_self() -> tuple[float, float]:
    """Return (user, system) CPU seconds for this process."""
    ticks = os.sysconf("SC_CLK_TCK")
    with open("/proc/self/stat", "rb") as fh:
        data = fh.read()
    # The comm field (2) is parenthesised and may itself contain spaces, so
    # parse from the *last* ')' rather than splitting the whole line. After it,
    # index 0 is field 3 (state), hence field N lives at index N - 3.
    # utime is field 14, stime is field 15.
    fields = data[data.rindex(b")") + 2:].split()
    return int(fields[11]) / ticks, int(fields[12]) / ticks


# ---------------------------------------------------------------------------
# Run metadata - reproducibility appendix material
# ---------------------------------------------------------------------------
def collect_metadata(args: argparse.Namespace) -> dict:
    def _cpu_model() -> str:
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
        return "unknown"

    def _nft_version() -> str:
        try:
            return subprocess.run(
                [firewall.NFT, "--version"], capture_output=True, text=True
            ).stdout.strip()
        except OSError:
            return "unknown"

    return {
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kernel": platform.release(),
        "python": sys.version.split()[0],
        "cpu_model": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "nft_version": _nft_version(),
        "clock_resolution_ns": time.get_clock_info("monotonic").resolution * 1e9,
        "args": vars(args),
        "parameters": {
            "packets_per_batch": C.PACKETS_PER_BATCH,
            "batches_per_trial": C.BATCHES_PER_TRIAL,
            "warmup_batches": C.WARMUP_BATCHES,
            "trials_per_cell": args.trials,
            "shallow_depth": C.SHALLOW_DEPTH,
            "deep_depth": C.DEEP_DEPTH,
            "noise_workers": C.NOISE_WORKERS,
            "noise_burst_rate_hz": C.NOISE_BURST_RATE_HZ,
            "random_seed": C.RANDOM_SEED,
        },
    }


# ---------------------------------------------------------------------------
# Main collection loop
# ---------------------------------------------------------------------------
FIELDS = (
    "trial_idx", "config", "verdict", "depth", "noise",
    "batch_idx", "ns_per_pkt", "send_errors",
    "noise_cpu_s", "victim_user_s", "victim_sys_s",
)


def build_schedule(trials_per_cell: int, rng: random.Random) -> list[tuple[C.FirewallConfig, bool]]:
    """Full randomised, interleaved trial schedule.

    Interleaving is the single most important control in this experiment. If
    all noise-off trials ran first and all noise-on trials second, CPU thermal
    drift alone would let a classifier separate the conditions at high
    accuracy - and the result would be an artefact, not a defence effect.
    """
    schedule = [
        (cfg, noise)
        for cfg in C.CONFIGS
        for noise in (False, True)
        for _ in range(trials_per_cell)
    ]
    rng.shuffle(schedule)
    return schedule


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="../data/run.csv", help="output CSV path")
    ap.add_argument("--trials", type=int, default=C.TRIALS_PER_CELL,
                    help="trials per (config x condition) cell")
    ap.add_argument("--noise-mode", choices=("poisson", "reactive"),
                    default="poisson")
    ap.add_argument("--pin", type=int, default=None, metavar="CPU",
                    help="pin the collector to this vCPU")
    ap.add_argument("--noise-cpus", default=None, metavar="LIST",
                    help="comma-separated vCPUs for noise workers "
                         "(default: all but --pin)")
    ap.add_argument("--dry-run", action="store_true",
                    help="2 trials per cell, for a smoke test")
    args = ap.parse_args()

    if args.dry_run:
        args.trials = 2

    if os.geteuid() != 0:
        print("error: must run as root (nft needs it): use sudo -E", file=sys.stderr)
        return 1

    firewall.preflight()

    # Core pinning. On a hybrid host (P-core/E-core), an unpinned thread can
    # migrate between core types mid-trial; the resulting timing step is far
    # larger than the side-channel signal.
    if args.pin is not None:
        os.sched_setaffinity(0, {args.pin})
        print(f"collector pinned to vCPU {args.pin}")

    if args.noise_cpus:
        noise_cpus = tuple(int(x) for x in args.noise_cpus.split(","))
    elif args.pin is not None:
        noise_cpus = tuple(c for c in range(os.cpu_count() or 1) if c != args.pin)
    else:
        noise_cpus = None

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = out_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(collect_metadata(args), indent=2))

    rng = random.Random(C.RANDOM_SEED)
    schedule = build_schedule(args.trials, rng)
    payload = b"\x00" * C.PAYLOAD_BYTES
    addr = (C.PROBE_HOST, C.PROBE_PORT)

    sender, listener = open_sockets()
    injector = NoiseInjector(
        mode=args.noise_mode, seed=C.RANDOM_SEED, cpus=noise_cpus
    ).start()

    total = len(schedule)
    started = time.time()
    print(f"{total} trials -> {out_path}  (mode={args.noise_mode})")

    try:
        with out_path.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(FIELDS)

            for trial_idx, (cfg, noise_on) in enumerate(schedule):
                firewall.apply_config(cfg)
                injector.set_active(noise_on)

                # Warm-up: excluded from the record so cold-cache and
                # noise-onset transients do not enter the dataset.
                for _ in range(C.WARMUP_BATCHES):
                    timed_batch(sender, payload, addr)
                    drain(listener)

                noise_cpu0 = injector.cpu_seconds()
                user0, sys0 = read_proc_stat_self()

                rows = []
                for batch_idx in range(C.BATCHES_PER_TRIAL):
                    ns, errors = timed_batch(sender, payload, addr)
                    drain(listener)
                    rows.append([ns, errors, batch_idx])

                noise_cpu = injector.cpu_seconds() - noise_cpu0
                user1, sys1 = read_proc_stat_self()

                for ns, errors, batch_idx in rows:
                    writer.writerow([
                        trial_idx, cfg.name, cfg.verdict, cfg.depth_label,
                        int(noise_on), batch_idx, f"{ns:.1f}", errors,
                        f"{noise_cpu:.6f}", f"{user1 - user0:.6f}",
                        f"{sys1 - sys0:.6f}",
                    ])

                if trial_idx % 25 == 0:
                    fh.flush()
                    done = trial_idx + 1
                    rate = done / max(time.time() - started, 1e-9)
                    eta = (total - done) / max(rate, 1e-9)
                    print(f"  {done}/{total}  {rate:5.1f} trial/s  eta {eta/60:4.1f} min",
                          flush=True)
    finally:
        injector.stop()
        sender.close()
        listener.close()
        try:
            firewall.teardown()
        except firewall.FirewallError as exc:
            print(f"warning: nft teardown failed: {exc}", file=sys.stderr)

    print(f"done in {(time.time() - started)/60:.1f} min -> {out_path}")
    print(f"metadata -> {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
