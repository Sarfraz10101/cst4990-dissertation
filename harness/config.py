"""Central configuration for the CST4990 side-channel experiments.

Every tunable lives here so the dissertation's methodology chapter can quote
exact parameter values, and so a marker can reproduce the run from one file.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Probe traffic
# ---------------------------------------------------------------------------
# We probe over loopback. This matters: on the loopback path the receiving
# INPUT hook is evaluated synchronously in the sending process's context, so
# the measured sendto() latency contains the nftables chain traversal cost.
# Probing a real NIC would push filtering into a softirq on another core and
# the signal would be lost in scheduling noise.
PROBE_HOST = "127.0.0.1"
PROBE_PORT = 9999
PAYLOAD_BYTES = 64

# Filler rules occupy a port range disjoint from PROBE_PORT so they are
# evaluated but never match the probe.
FILLER_PORT_BASE = 20000

# ---------------------------------------------------------------------------
# Measurement geometry
# ---------------------------------------------------------------------------
# One "batch" = PACKETS_PER_BATCH sendto() calls timed as a unit. Batching
# amortises Python interpreter overhead (~1 us/call) against the effect we
# want (~1-20 us of chain traversal), lifting SNR without dropping to C.
PACKETS_PER_BATCH = 200
BATCHES_PER_TRIAL = 50

# Batches discarded at the start of each trial, to exclude cold-cache and
# first-touch effects from the recorded data.
WARMUP_BATCHES = 10

# Trials per (config x condition) cell. The proposal specified 25; we raise
# it because 25 samples per class cannot support a meaningful confusion
# matrix. 250 x 4 configs x 2 conditions = 2000 trials, still only minutes
# of wall-clock. Deviating upward from a proposed minimum is always
# defensible; deviating downward is not.
TRIALS_PER_CELL = 250

# Seed for trial ordering and noise scheduling. Fixed for reproducibility.
RANDOM_SEED = 20260821

# ---------------------------------------------------------------------------
# Firewall configurations: the secret the attacker tries to recover
# ---------------------------------------------------------------------------
SHALLOW_DEPTH = 0     # target rule is first in the chain
DEEP_DEPTH = 256      # 256 non-matching rules evaluated before the target


@dataclass(frozen=True)
class FirewallConfig:
    """One firewall state the attacker must distinguish."""

    name: str
    verdict: str      # "accept" or "drop"
    filler_rules: int  # rules evaluated before the target rule

    @property
    def depth_label(self) -> str:
        return "shallow" if self.filler_rules == SHALLOW_DEPTH else "deep"


CONFIGS = (
    FirewallConfig("accept_shallow", "accept", SHALLOW_DEPTH),
    FirewallConfig("accept_deep", "accept", DEEP_DEPTH),
    FirewallConfig("drop_shallow", "drop", SHALLOW_DEPTH),
    FirewallConfig("drop_deep", "drop", DEEP_DEPTH),
)

CHANCE_ACCURACY = 1.0 / len(CONFIGS)  # 0.25 - the floor a perfect defence hits

# ---------------------------------------------------------------------------
# Defence: algorithmic power-noise injection
# ---------------------------------------------------------------------------
# Worker COUNT uses processes, not threads: CPython's GIL means threads
# cannot saturate multiple cores, so a threaded injector would produce far
# less entropy in the execution footprint than intended.
NOISE_WORKERS = 3

# Poisson arrival rate for noise bursts (bursts per second, per worker).
NOISE_BURST_RATE_HZ = 120.0

# Burst duration is drawn uniformly from this range (seconds).
NOISE_BURST_MIN_S = 0.0005
NOISE_BURST_MAX_S = 0.0040

# Reactive mode polls the nftables counter and injects on packet-count
# change, matching the proposal's "whenever security policies are triggered".
NOISE_POLL_INTERVAL_S = 0.005

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
NFT_TABLE = "cst4990"
NFT_FAMILY = "inet"
DATA_DIR = "data"
