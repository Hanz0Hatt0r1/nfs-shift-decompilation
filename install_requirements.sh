#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON_BIN was not found in PATH." >&2
    echo "Install Python 3.9+ and re-run this script." >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    echo "ERROR: Python 3.9 or newer is required." >&2
    "$PYTHON_BIN" --version >&2 || true
    exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Creating virtual environment: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "ERROR: virtual environment Python was not created: $VENV_PYTHON" >&2
    echo "Your Python installation may be missing the venv module." >&2
    exit 1
fi

echo "Installing Python dependencies from requirements-dev.txt..."
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r "$ROOT_DIR/requirements-dev.txt"

echo
echo "Requirements installed successfully."
echo "Activate the environment with:"
echo "  source \"$VENV_DIR/bin/activate\""
echo
echo "Run the test suite with:"
echo "  python -m pytest -q"

if command -v glslangValidator >/dev/null 2>&1; then
    echo
echo "Optional toolchain: glslangValidator is available."
else
    echo
echo "Optional toolchain: glslangValidator is not installed."
    echo "On Debian/Ubuntu: sudo apt-get install glslang-tools"
fi
