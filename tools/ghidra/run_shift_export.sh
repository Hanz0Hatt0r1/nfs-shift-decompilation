#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_shift_export.sh \
    <project-dir> <project-name> <program-name> <output-dir>

Example:
  GHIDRA_HOME="$HOME/ghidra_11.4_PUBLIC" \
    ./tools/ghidra/run_shift_export.sh \
    "$HOME/ghidra-projects" shift SHIFT.exe out/shift_ghidra_database

The Ghidra project must already contain an analyzed SHIFT.exe program. The
script uses -process and -noanalysis so the existing analysis database is read
without rerunning analyzers.
EOF
}

if [[ $# -ne 4 ]]; then
  usage >&2
  exit 2
fi

: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
OUT_DIR=$4
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ANALYZE_HEADLESS="$GHIDRA_HOME/support/analyzeHeadless"

if [[ ! -x "$ANALYZE_HEADLESS" ]]; then
  echo "error: analyzeHeadless not found or not executable: $ANALYZE_HEADLESS" >&2
  exit 1
fi

mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)

"$ANALYZE_HEADLESS" \
  "$PROJECT_DIR" "$PROJECT_NAME" \
  -process "$PROGRAM_NAME" \
  -noanalysis \
  -scriptPath "$SCRIPT_DIR" \
  -postScript ShiftEvidenceExporter.java "$OUT_DIR"

python3 "$SCRIPT_DIR/validate_shift_export.py" "$OUT_DIR"

echo "export ready: $OUT_DIR"
