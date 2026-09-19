#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for ECOAVES OrbitalOS.
# Runtime is stdlib-only; this prepares a venv with the dev (pytest) and
# matrix (pygame) extras so tests and the visual HUD both work.
set -euo pipefail

cd "$(dirname "$0")/.."

# System packages: venv/pip tooling plus a monospace font pygame falls back to.
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  python3.12-venv \
  python3-pip \
  fonts-dejavu-core

# Create the virtualenv only if it is missing or broken.
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,matrix]"

echo "OrbitalOS environment ready. Use .venv/bin/python (or activate .venv)."
