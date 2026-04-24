#!/usr/bin/env bash
# Build a single-file executable of CSV_Tools on macOS or Linux.
#
# Requirements (developer machine only):
#   * Python 3.10+
#   * python3 -m pip install pyinstaller
#
# The resulting binary lands in dist/CSV_Tools and has no runtime deps.
# Note: PyInstaller builds are platform-specific — run this on each OS you
# want a binary for.

set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[build] ERROR: python3 is not on PATH. Install Python 3.10+ first."
    exit 1
fi

if ! python3 -c "import PyInstaller" >/dev/null 2>&1; then
    echo "[build] Installing PyInstaller into the current Python environment..."
    python3 -m pip install --disable-pip-version-check --quiet pyinstaller
fi

echo "[build] Cleaning previous build output..."
rm -rf build dist

echo "[build] Running PyInstaller..."
python3 -m PyInstaller CSV_Tools.spec --noconfirm

echo
echo "[build] Done.  Executable: dist/CSV_Tools"
echo "[build] Copy it anywhere; it will create input/ and output/ on first run."
