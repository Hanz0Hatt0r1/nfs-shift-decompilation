#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_shift_function_instructions.sh \
    <project-dir> <project-name> <program-name> <output-jsonl> \
    <function-address> [function-address ...]

Addresses may be written as 0x00886900, 00886900, or FUN_00886900.
The Ghidra project must already contain an analyzed SHIFT.exe program.
EOF
}

if [[ $# -lt 5 ]]; then
  usage >&2
  exit 2
fi

: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
OUT_FILE=$4
shift 4
TARGETS=("$@")

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ANALYZE_HEADLESS="$GHIDRA_HOME/support/analyzeHeadless"

if [[ ! -x "$ANALYZE_HEADLESS" ]]; then
  echo "error: analyzeHeadless not found or not executable: $ANALYZE_HEADLESS" >&2
  exit 1
fi

mkdir -p -- "$(dirname -- "$OUT_FILE")"
OUT_DIR=$(cd -- "$(dirname -- "$OUT_FILE")" && pwd)
OUT_FILE="$OUT_DIR/$(basename -- "$OUT_FILE")"

# Keep Ghidra's Java script compiler isolated from the rest of tools/ghidra.
# Ghidra compiles Java files it discovers under -scriptPath, so pointing it at
# the repository directory can make an unrelated script's API incompatibility
# abort this targeted export. Copy only the requested exporter into a temporary
# script directory and compile exactly that source.
COMPAT_SCRIPT_DIR=$(mktemp -d)
cleanup() {
  rm -rf -- "$COMPAT_SCRIPT_DIR"
}
trap cleanup EXIT
cp -- "$SCRIPT_DIR/ShiftFunctionInstructionExporter.java" \
  "$COMPAT_SCRIPT_DIR/ShiftFunctionInstructionExporter.java"

"$ANALYZE_HEADLESS" \
  "$PROJECT_DIR" "$PROJECT_NAME" \
  -process "$PROGRAM_NAME" \
  -noanalysis \
  -scriptPath "$COMPAT_SCRIPT_DIR" \
  -postScript ShiftFunctionInstructionExporter.java "$OUT_FILE" "${TARGETS[@]}"

python3 "$SCRIPT_DIR/validate_function_instruction_export.py" \
  "$OUT_FILE" "${TARGETS[@]}"

echo "instruction export ready: $OUT_FILE"
