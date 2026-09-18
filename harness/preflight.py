"""Pre-run readiness check: is this machine in a state where the run is valid?

    sudo -E python3 preflight.py
    sudo -E python3 preflight.py --json ../data/preflight.json

`setup_guest.sh` installs things. This is different: it runs immediately before a
real collection and asks whether the numbers that come out will mean anything.
A 2,000-trial run takes minutes, but discovering afterwards that the guest had
one vCPU, or that a stale table from a crashed run was still loaded, costs a day.

Exit codes: 0 ready, 1 at least one blocking failure, 2 usage error.

Two checks here are worth understanding rather than just passing.

`achieved parallelism` forks the same number of busy processes the defence uses
and measures how much CPU time they actually consumed. On a single-core guest the
answer is ~1.0x no matter how many workers were asked for, which is direct
evidence that the injector time-sliced the victim instead of running beside it -
a much stronger statement than inferring it from `nproc`.

`RAPL energy counters` is expected to fail inside a VM. It is checked anyway, so
the claim that power measurement was unavailable is recorded evidence rather
than an assertion in the limitations section.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time

import config as C

OK, WARN, FAIL = "OK", "WARN", "FAIL"

# Every trial reloads the ruleset, so total batches is the whole run.
TOTAL_TRIALS = C.TRIALS_PER_CELL * len(C.CONFIGS) * 2
BATCHES_PER_TRIAL_TOTAL = C.WARMUP_BATCHES + C.BATCHES_PER_TRIAL
TOTAL_BATCHES = TOTAL_TRIALS * BATCHES_PER_TRIAL_TOTAL
BYTES_PER_ROW = 110          # measured from a smoke-test CSV, rounded up
MIN_FREE_BYTES = 200 << 20   # 200 MB: the trace, plus room for results

results: list[tuple[str, str, str]] = []


def record(level: str, title: str, detail: str) -> None:
    results.append((level, title, detail))


def run(cmd: list[str], timeout: float = 10.0) -> tuple[int, str]:
    """Run a command, returning (returncode, combined output). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
def check_platform() -> None:
    if sys.platform.startswith("linux"):
        record(OK, "platform", f"{platform.system()} {platform.release()}")
    else:
        record(FAIL, "platform",
               f"{platform.system()} - collection needs Linux and nftables. "
               "Run this inside the guest. (The analysis scripts do run here.)")


def check_root() -> None:
    geteuid = getattr(os, "geteuid", None)
    if geteuid is None:
        record(WARN, "privileges", "cannot determine euid on this platform")
    elif geteuid() == 0:
        record(OK, "privileges", "running as root")
    else:
        record(FAIL, "privileges",
               "not root - nft cannot load rules. Use `sudo -E python3 ...`; "
               "the -E keeps the virtualenv on PATH.")


def check_cpus() -> None:
    # Affinity count, not nproc: if this process has been restricted to a
    # subset of cores, that subset is what the run actually gets.
    try:
        usable = len(os.sched_getaffinity(0))
    except AttributeError:
        usable = os.cpu_count() or 0
    total = os.cpu_count() or 0
    needed = C.NOISE_WORKERS + 1  # workers, plus one core for the victim

    detail = f"{usable} usable of {total} present; run needs {needed}"
    if usable >= needed:
        record(OK, "vCPUs", detail)
    elif usable >= 2:
        record(WARN, "vCPUs", detail + " - the injector will contend with the "
               "victim for cores, which inflates the measured latency cost")
    else:
        record(FAIL, "vCPUs", detail + " - on one core the defence time-slices "
               "the victim rather than running beside it. Shut the VM down and "
               "raise it to 4 vCPUs before collecting.")


def check_packages() -> None:
    missing = []
    for mod in ("numpy", "pandas", "sklearn", "scipy"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        record(FAIL, "python packages",
               f"missing {', '.join(missing)} - activate the venv "
               "(source ~/cst4990-venv/bin/activate) and re-run with sudo -E")
    else:
        record(OK, "python packages", f"numpy, pandas, sklearn, scipy on "
               f"{platform.python_version()}")


# ---------------------------------------------------------------------------
# Firewall state
# ---------------------------------------------------------------------------
def check_nft() -> None:
    if shutil.which("nft") is None:
        record(FAIL, "nftables", "nft not on PATH - run setup_guest.sh")
        return
    rc, out = run(["nft", "--version"])
    if rc != 0:
        record(FAIL, "nftables", f"nft --version failed: {out}")
        return
    version = out.splitlines()[0] if out else "unknown"

    rc, _ = run(["nft", "list", "ruleset"])
    if rc != 0:
        record(FAIL, "nftables", f"{version} present but cannot list ruleset "
                                 "- check privileges")
    else:
        record(OK, "nftables", version)


def check_stale_table() -> None:
    """A leftover table from a crashed run silently changes the baseline."""
    if shutil.which("nft") is None:
        return
    rc, _ = run(["nft", "list", "table", C.NFT_FAMILY, C.NFT_TABLE])
    if rc == 0:
        record(WARN, "stale ruleset",
               f"table {C.NFT_FAMILY} {C.NFT_TABLE} is already loaded, "
               "probably from an interrupted run. Remove it first: "
               f"sudo nft delete table {C.NFT_FAMILY} {C.NFT_TABLE}")
    else:
        record(OK, "stale ruleset", "no leftover experiment table")


def check_foreign_rules() -> None:
    """Pre-existing rules raise the measurement floor for every condition."""
    if shutil.which("nft") is None:
        return
    rc, out = run(["nft", "list", "ruleset"])
    if rc != 0:
        return
    others = sorted({
        line.strip() for line in out.splitlines()
        if line.strip().startswith("table ") and C.NFT_TABLE not in line
    })
    if others:
        record(WARN, "other firewall tables",
               f"{len(others)} present ({'; '.join(others)[:120]}). Their rules "
               "are traversed on every probe, adding a constant to both "
               "conditions. Not fatal, but note it in the methodology.")
    else:
        record(OK, "other firewall tables", "none - clean measurement baseline")


def check_probe_port() -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind((C.PROBE_HOST, C.PROBE_PORT))
        record(OK, "probe port", f"udp/{C.PROBE_PORT} free")
    except OSError as exc:
        record(FAIL, "probe port",
               f"cannot bind udp/{C.PROBE_PORT}: {exc}. The collector needs a "
               "real listener there, otherwise accepted packets provoke ICMP "
               "port-unreachable replies that dwarf the effect being measured.")
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
def check_clock() -> None:
    if not hasattr(time, "CLOCK_MONOTONIC_RAW"):
        record(FAIL, "clock", "CLOCK_MONOTONIC_RAW unavailable - the collector "
                              "needs a clock that NTP cannot slew mid-run")
        return
    res_ns = time.get_clock_info("monotonic").resolution * 1e9
    # The effect being measured is single-digit microseconds per packet, and a
    # batch of 200 amortises it, but a clock coarser than a microsecond would
    # quantise the per-batch figure into a handful of distinct values.
    if res_ns <= 1000:
        record(OK, "clock", f"CLOCK_MONOTONIC_RAW, resolution {res_ns:.0f} ns")
    else:
        record(FAIL, "clock", f"resolution {res_ns:.0f} ns is too coarse to "
                              "resolve per-batch differences")


def check_affinity() -> None:
    """Pinning is a mandatory control on a hybrid P-core/E-core host."""
    if not hasattr(os, "sched_setaffinity"):
        record(FAIL, "core pinning", "sched_setaffinity unavailable - the "
                                     "collector's --pin control cannot work")
        return
    try:
        original = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(original)})
        os.sched_setaffinity(0, original)
        record(OK, "core pinning", f"sched_setaffinity works; "
                                   f"{len(original)} cores available to pin to")
    except OSError as exc:
        record(FAIL, "core pinning", f"sched_setaffinity failed: {exc}")


# ---------------------------------------------------------------------------
# Can the defence actually run in parallel?
# ---------------------------------------------------------------------------
def _spin(deadline: float) -> None:
    x = 1
    while time.monotonic() < deadline:
        for _ in range(2000):      # amortise the clock read
            x = (x * x + 7) % 9973
    os._exit(0)


def check_parallelism(duration: float = 0.4) -> None:
    """Fork NOISE_WORKERS busy children and measure the CPU time they got.

    This is the check that catches a misconfigured guest for what it is. Asking
    for three workers and getting 1.0x of a core back means the defence never
    ran alongside the victim - it interleaved with it, and every latency number
    from that run describes contention rather than injected noise.
    """
    if not hasattr(os, "fork"):
        record(WARN, "achieved parallelism", "no fork() on this platform")
        return
    import resource

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    pids = []
    for _ in range(C.NOISE_WORKERS):
        pid = os.fork()
        if pid == 0:
            _spin(t0 + duration)
        pids.append(pid)
    for pid in pids:
        os.waitpid(pid, 0)
    elapsed = time.monotonic() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)

    cpu = ((after.ru_utime - before.ru_utime)
           + (after.ru_stime - before.ru_stime))
    achieved = cpu / elapsed if elapsed > 0 else 0.0
    detail = (f"{achieved:.2f}x of one core from {C.NOISE_WORKERS} workers "
              f"({cpu:.3f} CPU s in {elapsed:.3f} s wall)")

    if achieved >= C.NOISE_WORKERS * 0.8:
        record(OK, "achieved parallelism", detail)
    elif achieved >= 1.5:
        record(WARN, "achieved parallelism", detail + " - workers are sharing "
               "cores, so the injected footprint is smaller than configured")
    else:
        record(FAIL, "achieved parallelism", detail + " - the defence cannot "
               "run concurrently with the victim on this machine. Results would "
               "measure time-slicing, not noise injection.")


# ---------------------------------------------------------------------------
# Contention and drift
# ---------------------------------------------------------------------------
def check_load() -> None:
    try:
        one, five, _ = os.getloadavg()
    except (AttributeError, OSError):
        record(WARN, "system load", "load average unavailable")
        return
    cpus = os.cpu_count() or 1
    per_cpu = one / cpus
    detail = f"1-min load {one:.2f} across {cpus} cpu(s) = {per_cpu:.2f}/cpu"
    if per_cpu < 0.2:
        record(OK, "system load", detail)
    else:
        record(WARN, "system load", detail + " - something else is running. "
               "Idle the machine, or run setup_guest.sh --quiet, before "
               "collecting; background work lands in the measurements.")


def check_memory() -> None:
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            info = {}
            for line in fh:
                key, _, rest = line.partition(":")
                info[key] = int(rest.split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        record(WARN, "memory", "cannot read /proc/meminfo")
        return

    available = info.get("MemAvailable", 0)
    swap_used = info.get("SwapTotal", 0) - info.get("SwapFree", 0)
    detail = f"{available / (1 << 30):.2f} GiB available"
    if swap_used > (64 << 20):
        record(WARN, "memory", detail + f", but {swap_used / (1 << 20):.0f} MiB "
               "of swap is in use - paging during a run shows up as latency "
               "outliers")
    elif available < (1 << 30):
        record(WARN, "memory", detail + " - under 1 GiB. Raise the VM to 4 GiB.")
    else:
        record(OK, "memory", detail)


def check_cpu_scaling() -> None:
    """Frequency drift across a run would separate conditions by time, not cause.

    Usually absent in a VM, which is a small mercy: a fixed guest frequency is
    one fewer confound. Randomised interleaving is the real defence against it,
    but knowing the governor is worth a sentence in the methodology.
    """
    base = "/sys/devices/system/cpu/cpu0/cpufreq"
    try:
        with open(f"{base}/scaling_governor", encoding="ascii") as fh:
            gov = fh.read().strip()
    except OSError:
        record(OK, "cpu frequency scaling",
               "no cpufreq interface (typical in a VM) - guest sees a fixed "
               "frequency, so no governor-driven drift")
        return
    if gov == "performance":
        record(OK, "cpu frequency scaling", f"governor = {gov}")
    else:
        record(WARN, "cpu frequency scaling",
               f"governor = {gov} - frequency may drift during the run. "
               "Interleaved trial ordering absorbs this, but consider: "
               "sudo cpupower frequency-set -g performance")


def check_rapl() -> None:
    """Expected to be unavailable in a guest. Recorded as evidence, not assumed."""
    root = "/sys/class/powercap"
    if not os.path.isdir(root):
        record(WARN, "RAPL energy counters",
               "no /sys/class/powercap - energy is not measurable here, as "
               "expected inside a VM. This is the documented reason the study "
               "measures a timing and resource-utilisation channel.")
        return
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name, "energy_uj")
        try:
            with open(path, encoding="ascii") as fh:
                value = int(fh.read().strip())
            record(OK, "RAPL energy counters",
                   f"{path} readable ({value} uJ) - a genuine energy channel is "
                   "available. Worth reporting alongside the timing channel.")
            return
        except (OSError, ValueError):
            continue
    record(WARN, "RAPL energy counters",
           "powercap present but no readable energy_uj - masked by the "
           "hypervisor, as expected in a guest")


def check_disk() -> None:
    rows = TOTAL_TRIALS * C.BATCHES_PER_TRIAL
    need = rows * BYTES_PER_ROW
    try:
        free = shutil.disk_usage(".").free
    except OSError as exc:
        record(WARN, "disk space", f"cannot determine free space: {exc}")
        return
    detail = (f"{free / (1 << 30):.1f} GiB free; trace will be about "
              f"{need / (1 << 20):.0f} MiB ({rows:,} rows)")
    if free > max(MIN_FREE_BYTES, need * 4):
        record(OK, "disk space", detail)
    else:
        record(FAIL, "disk space", detail + " - not enough headroom")


# ---------------------------------------------------------------------------
# What the configured run will cost
# ---------------------------------------------------------------------------
def estimate_runtime() -> None:
    """Time one batch against the live stack and extrapolate.

    This is a floor, not a prediction: it measures the current ruleset, and the
    deep configurations traverse 256 more rules per packet than this. Quote it
    to decide whether to start a run now, not in the dissertation.
    """
    payload = b"\x00" * C.PAYLOAD_BYTES
    addr = (C.PROBE_HOST, C.PROBE_PORT)
    # The collector insists on CLOCK_MONOTONIC_RAW; here a rough figure is
    # enough, so fall back rather than fail on a platform without it.
    if hasattr(time, "CLOCK_MONOTONIC_RAW"):
        now_ns = lambda: time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    else:
        now_ns = time.perf_counter_ns
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        listener.bind(addr)
        listener.setblocking(False)
    except OSError:
        record(WARN, "estimated runtime", "probe port busy - cannot measure")
        listener.close()
        sender.close()
        return

    try:
        for _ in range(C.PACKETS_PER_BATCH):     # warm the path
            sender.sendto(payload, addr)
        t0 = now_ns()
        for _ in range(C.PACKETS_PER_BATCH):
            sender.sendto(payload, addr)
        t1 = now_ns()
    except OSError as exc:
        record(WARN, "estimated runtime", f"probe send failed: {exc}")
        return
    finally:
        listener.close()
        sender.close()

    per_batch_s = (t1 - t0) / 1e9
    probe_s = per_batch_s * TOTAL_BATCHES

    # Each trial reloads the ruleset; on a deep config that is a 257-rule file
    # through `nft -f`, which is not negligible at 2,000 trials.
    reload_s = 0.0
    if shutil.which("nft"):
        t0 = time.monotonic()
        run(["nft", "list", "ruleset"])
        reload_s = (time.monotonic() - t0) * TOTAL_TRIALS

    total_min = (probe_s + reload_s) / 60
    record(OK, "estimated runtime",
           f"about {total_min:.0f} min for {TOTAL_TRIALS:,} trials "
           f"({probe_s / 60:.0f} min probing + {reload_s / 60:.0f} min ruleset "
           f"reloads). Lower bound - deep chains cost more per packet than the "
           f"ruleset loaded right now.")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
CHECKS = (
    check_platform,
    check_root,
    check_cpus,
    check_packages,
    check_nft,
    check_stale_table,
    check_foreign_rules,
    check_probe_port,
    check_clock,
    check_affinity,
    check_parallelism,
    check_load,
    check_memory,
    check_cpu_scaling,
    check_rapl,
    check_disk,
)

MARK = {OK: "  ok  ", WARN: " warn ", FAIL: " FAIL "}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", metavar="PATH", default=None,
                    help="also write the report as JSON, for the appendix")
    ap.add_argument("--skip-estimate", action="store_true",
                    help="skip the runtime estimate (it sends 400 packets)")
    args = ap.parse_args()

    print("=" * 70)
    print(" CST4990 preflight")
    print("=" * 70)

    for check in CHECKS:
        try:
            check()
        except Exception as exc:                      # never abort the report
            record(WARN, check.__name__, f"check itself failed: {exc!r}")

    if not args.skip_estimate:
        try:
            estimate_runtime()
        except Exception as exc:
            record(WARN, "estimated runtime", f"check itself failed: {exc!r}")

    width = max(len(t) for _, t, _ in results)
    for level, title, detail in results:
        print(f"[{MARK[level]}] {title:<{width}}  {detail}")

    fails = [title for lvl, title, _ in results if lvl == FAIL]
    warns = [title for lvl, title, _ in results if lvl == WARN]

    print("-" * 70)
    if fails:
        print(f"NOT READY - {len(fails)} blocking issue(s): {', '.join(fails)}")
        print("Fix these before collecting. A run started now would produce")
        print("numbers that cannot be defended in the viva.")
    elif warns:
        print(f"READY, with {len(warns)} caveat(s): {', '.join(warns)}")
        print("None of these blocks collection, but each one belongs in the")
        print("methodology chapter's threats-to-validity discussion.")
    else:
        print("READY - all checks clean.")
    print("-" * 70)

    if args.json:
        payload = {
            "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "verdict": "not_ready" if fails else "ready",
            "parameters": {
                "trials": TOTAL_TRIALS,
                "batches_per_trial": BATCHES_PER_TRIAL_TOTAL,
                "packets_per_batch": C.PACKETS_PER_BATCH,
                "noise_workers": C.NOISE_WORKERS,
            },
            "checks": [
                {"level": lvl, "check": t, "detail": d} for lvl, t, d in results
            ],
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"report written to {args.json}")

    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
