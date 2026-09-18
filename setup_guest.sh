#!/usr/bin/env bash
# Provision the Lubuntu guest for the CST4990 side-channel experiments.
#
#   bash setup_guest.sh              # install and verify
#   bash setup_guest.sh --quiet      # also stop noisy background services
#
# Service changes use `systemctl stop`, never `disable`, so a reboot restores
# the VM to normal. Nothing here is permanent.

set -euo pipefail

QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

VENV="$HOME/cst4990-venv"

say() { printf '\n==> %s\n' "$*"; }

say "Installing packages"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    nftables \
    python3 python3-pip python3-venv \
    linux-tools-common

say "Creating virtualenv at $VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet numpy pandas scikit-learn scipy matplotlib

say "Checking nftables"
sudo nft list ruleset >/dev/null && echo "  nft OK ($(sudo nft --version))"

say "Checking timer resolution"
"$VENV/bin/python" - <<'PY'
import time
for name in ("monotonic", "perf_counter"):
    info = time.get_clock_info(name)
    print(f"  {name:13s} resolution = {info.resolution * 1e9:8.1f} ns")
print(f"  CLOCK_MONOTONIC_RAW available: {hasattr(time, 'CLOCK_MONOTONIC_RAW')}")
PY

say "Guest CPU topology"
echo "  vCPUs: $(nproc)"
if [[ "$(nproc)" -lt 2 ]]; then
    cat <<'WARN'
  WARNING: only 1 vCPU. The noise injector cannot run concurrently with the
  victim on a single core, so the defence will simply time-slice the probe
  rather than inject a parallel power footprint. Shut the VM down and raise it
  to 4 vCPUs (see README, "Reconfigure the VM").
WARN
fi

if [[ "$QUIET" == "1" ]]; then
    say "Stopping background services (until next reboot)"
    for svc in unattended-upgrades apt-daily.timer apt-daily-upgrade.timer \
               snapd.service snapd.socket man-db.timer motd-news.timer; do
        if systemctl list-unit-files | grep -q "^${svc}"; then
            sudo systemctl stop "$svc" 2>/dev/null && echo "  stopped $svc" || true
        fi
    done
    echo "  reboot to restore all services"
fi

say "Done"
cat <<EOF

Next:
  source $VENV/bin/activate
  cd harness
  sudo -E python3 snr_check.py          # does the leak exist? ~30 seconds
  sudo -E python3 collect.py --dry-run  # smoke test the full pipeline
EOF
