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

# Ghidra 12.1 removed DefinedDataIterator.definedStrings(Program).  Prepare a
# temporary source copy that uses Listing.getDefinedData(true) plus
# Data.hasStringValue(), both stable APIs in current Ghidra releases.
COMPAT_SCRIPT_DIR=$(mktemp -d)
trap 'rm -rf -- "$COMPAT_SCRIPT_DIR"' EXIT
python3 "$SCRIPT_DIR/prepare_shift_export.py" \
  "$SCRIPT_DIR/ShiftEvidenceExporter.java" \
  "$COMPAT_SCRIPT_DIR/ShiftEvidenceExporter.java"

"$ANALYZE_HEADLESS" \
  "$PROJECT_DIR" "$PROJECT_NAME" \
  -process "$PROGRAM_NAME" \
  -noanalysis \
  -scriptPath "$COMPAT_SCRIPT_DIR" \
  -postScript ShiftEvidenceExporter.java "$OUT_DIR"

python3 "$SCRIPT_DIR/validate_shift_export.py" "$OUT_DIR"

echo "export ready: $OUT_DIR"
