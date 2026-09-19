#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for ECOAVES OrbitalOS.
#
# The project runtime is stdlib-only. Tests need pytest; the visual Matrix HUD
# needs pygame. We install these into the SYSTEM interpreter (not a repo-local
# .venv): with environment builds the repo is re-checked out into /workspace on
# each boot and .venv/ is gitignored, so a repo-local venv would not survive.
# System site-packages live outside /workspace and persist in the build.
# This mirrors the README's own `python3 -m pip install pytest pygame`.
set -euo pipefail

sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends python3-pip fonts-dejavu-core

# Ubuntu marks the system interpreter externally-managed (PEP 668); this VM is
# disposable, so installing directly with --break-system-packages is intended.
# Use sudo so packages land in /usr/local/lib/.../dist-packages (always on
# sys.path for any user), which survives an environment build's fresh checkout.
sudo python3 -m pip install --break-system-packages --upgrade "pytest>=8.0" "pygame>=2.6"

echo "OrbitalOS environment ready. Run tests with: python3 -m pytest"
