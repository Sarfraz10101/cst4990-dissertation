"""Algorithmic power-noise injection - the defence under evaluation.

Design notes that belong in the methodology chapter:

* Workers are *processes*, not threads. CPython's GIL serialises bytecode, so
  a threaded injector cannot saturate more than one core and would inject far
  less entropy into the execution footprint than intended.
* Workers are started once per run and gated by a shared flag rather than
  spawned per trial. Spawning ~2000 process groups mid-experiment would stamp
  a process-startup artefact onto every noise-on trial - the classifier could
  then separate the conditions from the artefact alone, not from the defence.
* Each burst draws a random duration *and* a random work kernel, so the
  footprint is not itself a stable pattern an attacker could learn and filter.
"""

from __future__ import annotations

import ctypes
import math
import multiprocessing as mp
import os
import random
import time

from config import (
    NOISE_BURST_MAX_S,
    NOISE_BURST_MIN_S,
    NOISE_BURST_RATE_HZ,
    NOISE_POLL_INTERVAL_S,
    NOISE_WORKERS,
)

CLOCK = time.CLOCK_MONOTONIC_RAW


# ---------------------------------------------------------------------------
# Work kernels - deliberately heterogeneous
# ---------------------------------------------------------------------------
def _kernel_integer(rng: random.Random) -> None:
    acc = rng.getrandbits(32)
    for _ in range(64):
        acc = (acc * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF


def _kernel_float(rng: random.Random) -> None:
    x = rng.random() + 0.5
    for _ in range(64):
        x = math.sqrt(x * 1.0000001) + math.sin(x)


def _kernel_memory(rng: random.Random, _buf: bytearray = bytearray(1 << 16)) -> None:
    n = len(_buf)
    for _ in range(64):
        _buf[rng.randrange(n)] = rng.getrandbits(8)


_KERNELS = (_kernel_integer, _kernel_float, _kernel_memory)


def _burst(rng: random.Random) -> None:
    """Run one randomised burst of work."""
    kernel = rng.choice(_KERNELS)
    duration = rng.uniform(NOISE_BURST_MIN_S, NOISE_BURST_MAX_S)
    end = time.clock_gettime(CLOCK) + duration
    while time.clock_gettime(CLOCK) < end:
        kernel(rng)


# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------
def _worker(
    active: "mp.sharedctypes.Synchronized",
    trigger_seq: "mp.sharedctypes.Synchronized",
    stop: mp.Event,
    seed: int,
    mode: str,
    cpus: tuple[int, ...] | None,
) -> None:
    if cpus:
        try:
            os.sched_setaffinity(0, set(cpus))
        except OSError:
            pass  # affinity is an optimisation, not a requirement

    rng = random.Random(seed)
    last_seq = -1

    while not stop.is_set():
        if not active.value:
            time.sleep(0.001)
            continue

        if mode == "poisson":
            # Exponential inter-arrivals give a Poisson process, so burst
            # onsets carry no periodicity for the attacker to lock onto.
            time.sleep(rng.expovariate(NOISE_BURST_RATE_HZ))
            if active.value:
                _burst(rng)
        else:  # reactive
            seq = trigger_seq.value
            if seq != last_seq:
                last_seq = seq
                _burst(rng)
            else:
                time.sleep(NOISE_POLL_INTERVAL_S / 2)


def _poller(
    trigger_seq: "mp.sharedctypes.Synchronized",
    stop: mp.Event,
) -> None:
    """Publish a counter bump whenever the target rule matches packets.

    This is the proposal's "inject whenever security policies are triggered".
    One poller shells out to nft; workers watch a shared integer, so we pay
    the subprocess cost once rather than once per worker.
    """
    import firewall

    last = -1
    while not stop.is_set():
        try:
            packets, _ = firewall.read_counter()
        except Exception:
            time.sleep(NOISE_POLL_INTERVAL_S)
            continue
        if packets != last:
            last = packets
            trigger_seq.value += 1
        time.sleep(NOISE_POLL_INTERVAL_S)


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------
class NoiseInjector:
    """Long-lived worker pool whose output is gated on demand.

    Use `set_active(True/False)` to switch the defence per trial, and
    `cpu_seconds()` to read cumulative worker CPU time for overhead analysis.
    """

    def __init__(
        self,
        workers: int = NOISE_WORKERS,
        mode: str = "poisson",
        seed: int = 0,
        cpus: tuple[int, ...] | None = None,
    ) -> None:
        if mode not in ("poisson", "reactive"):
            raise ValueError(f"unknown noise mode: {mode!r}")
        self.mode = mode
        self._active = mp.Value(ctypes.c_int, 0)
        self._trigger_seq = mp.Value(ctypes.c_longlong, 0)
        self._stop = mp.Event()
        self._procs: list[mp.Process] = [
            mp.Process(
                target=_worker,
                args=(self._active, self._trigger_seq, self._stop,
                      seed + i, mode, cpus),
                daemon=True,
            )
            for i in range(workers)
        ]
        if mode == "reactive":
            self._procs.append(
                mp.Process(
                    target=_poller,
                    args=(self._trigger_seq, self._stop),
                    daemon=True,
                )
            )

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> "NoiseInjector":
        for p in self._procs:
            p.start()
        return self

    def stop(self) -> None:
        self._active.value = 0
        self._stop.set()
        for p in self._procs:
            p.join(timeout=2.0)
            if p.is_alive():
                p.terminate()

    def __enter__(self) -> "NoiseInjector":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # -- control ------------------------------------------------------------
    def set_active(self, on: bool) -> None:
        self._active.value = 1 if on else 0

    def cpu_seconds(self) -> float:
        """Cumulative CPU seconds used by the injector's worker processes.

        Sampled either side of a trial, this is the defence's CPU overhead -
        research question 2's dependent variable.

        Read from each worker's `/proc/<pid>/stat` rather than from
        `getrusage(RUSAGE_CHILDREN)`. RUSAGE_CHILDREN only accounts for
        children that have been *waited on*, and this pool is deliberately
        long-lived (see the module docstring), so nothing is ever reaped
        mid-run and that counter would stay at exactly zero for the whole
        experiment. `/proc` reports live processes, which is what we need.
        """
        ticks = os.sysconf("SC_CLK_TCK")
        total = 0.0
        for p in self._procs:
            if p.pid is None:
                continue
            try:
                with open(f"/proc/{p.pid}/stat", "rb") as fh:
                    data = fh.read()
            except OSError:
                continue  # worker exited; its remaining time is unrecoverable
            # comm (field 2) is parenthesised and may contain spaces, so parse
            # from the last ')'. After it, index 0 is field 3, so field N is at
            # index N - 3: utime is field 14, stime is field 15.
            fields = data[data.rindex(b")") + 2:].split()
            total += (int(fields[11]) + int(fields[12])) / ticks
        return total
