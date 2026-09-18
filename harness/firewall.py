"""nftables ruleset generation, application and counter readback.

Each FirewallConfig is compiled to a complete ruleset and loaded atomically
with `nft -f -`. Atomic replacement matters: a partially-applied ruleset would
leak a transient state into the traces.
"""

from __future__ import annotations

import shutil
import subprocess

from config import (
    FILLER_PORT_BASE,
    NFT_FAMILY,
    NFT_TABLE,
    PROBE_PORT,
    FirewallConfig,
)

# Fall back to the standard install path if `which` can't see it (e.g. a
# restricted sudo PATH) rather than failing before we even try to run it.
NFT = shutil.which("nft") or "/usr/sbin/nft"


class FirewallError(RuntimeError):
    """Raised when nft rejects a ruleset or is unavailable."""


def _run_nft(args: list[str], stdin: str | None = None) -> str:
    """Invoke nft, raising FirewallError with nft's own message on failure."""
    proc = subprocess.run(
        [NFT, *args],
        input=stdin,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # nft's own diagnostics land on stderr in most versions but on stdout
        # in a few, so check both rather than silently swallowing the message.
        detail = (proc.stderr or proc.stdout).strip()
        raise FirewallError(f"nft {' '.join(args)} failed: {detail}")
    return proc.stdout


def build_ruleset(cfg: FirewallConfig) -> str:
    """Render the complete nft script for one configuration.

    The leading `table`/`delete table` pair is the standard idiom for an
    idempotent flush: it guarantees the table exists before deletion, so the
    script never fails on a clean system.

    Filler rules are emitted individually rather than as a set, because a set
    lookup is O(1) and would defeat the point - we need the chain to be
    traversed linearly so that rule depth has a measurable cost.
    """
    filler = "\n".join(
        f"        udp dport {FILLER_PORT_BASE + i} drop"
        for i in range(cfg.filler_rules)
    )
    # `policy accept` on the chain, not the target rule, matters: only the
    # probe port's own rule decides accept/drop, so the configured verdict is
    # never masked by a chain-wide default.
    return f"""\
table {NFT_FAMILY} {NFT_TABLE}
delete table {NFT_FAMILY} {NFT_TABLE}

table {NFT_FAMILY} {NFT_TABLE} {{
    chain input {{
        type filter hook input priority filter; policy accept;
{filler}
        udp dport {PROBE_PORT} counter {cfg.verdict}
    }}
}}
"""


def apply_config(cfg: FirewallConfig) -> None:
    """Load a configuration, replacing any previous one atomically."""
    _run_nft(["-f", "-"], stdin=build_ruleset(cfg))


def teardown() -> None:
    """Remove our table, leaving any pre-existing firewall untouched.

    We only ever delete the table we created, never `nft flush ruleset` - the
    latter would wipe the host's own rules.
    """
    _run_nft(
        ["-f", "-"],
        stdin=(
            f"table {NFT_FAMILY} {NFT_TABLE}\n"
            f"delete table {NFT_FAMILY} {NFT_TABLE}\n"
        ),
    )


def read_counter() -> tuple[int, int]:
    """Return (packets, bytes) matched by the target rule.

    Used by the reactive noise injector to detect policy-trigger events, and
    as a sanity check that probe traffic is actually reaching the chain.
    """
    out = _run_nft(["-j", "list", "table", NFT_FAMILY, NFT_TABLE])
    import json  # only needed here, so kept out of the module-level imports

    # nft's JSON dump is a flat list of table/chain/rule objects; a rule's
    # match expressions (verdict, counter, ...) are nested inside its own
    # "expr" list, so the counter has to be found by walking both levels.
    for item in json.loads(out).get("nftables", []):
        rule = item.get("rule")
        if not rule:
            continue
        for expr in rule.get("expr", []):
            counter = expr.get("counter")
            if isinstance(counter, dict) and "packets" in counter:
                return int(counter["packets"]), int(counter["bytes"])
    raise FirewallError("no counter found on target rule")


def preflight() -> None:
    """Fail fast, with a fixable message, before a long collection run."""
    # Only complain here if nft is neither on PATH nor a plausible absolute
    # fallback path; an absolute path is trusted and checked properly by the
    # `list ruleset` call below, which also confirms we're allowed to read it.
    if not shutil.which(NFT) and not NFT.startswith("/"):
        raise FirewallError("nft not found - run setup_guest.sh first")
    try:
        _run_nft(["list", "ruleset"])
    except FirewallError as exc:
        raise FirewallError(
            f"cannot read the ruleset ({exc}). Run the collector under sudo."
        ) from exc
