#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra bash ./tools/ghidra/run_release_wrapper_callsite_evidence.sh \
    <project-dir> <project-name> <program-name> <ghidra-export-dir> <output-dir>

Optional environment:
  SHIFT_RELEASE_WRAPPER_MAX_CALLERS=500
    Maximum number of direct caller functions exported in one targeted pass.

This workflow uses callgraph.jsonl to find direct callers of FUN_00886930 and
FUN_00886950, exports only those caller instruction bodies, and recovers the
physical values supplied to ECX/DL/stack wrapper storage. It does not require
SHIFT.exe.c and does not assign semantic meaning to DL.
EOF
}

if [[ $# -ne 5 ]]; then
  usage >&2
  exit 2
fi

: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
GHIDRA_EXPORT=$4
OUT_DIR=$5
MAX_CALLERS=${SHIFT_RELEASE_WRAPPER_MAX_CALLERS:-500}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

if [[ ! "$MAX_CALLERS" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: SHIFT_RELEASE_WRAPPER_MAX_CALLERS must be a positive integer" >&2
  exit 2
fi
if [[ ! -d "$GHIDRA_EXPORT" ]]; then
  echo "error: Ghidra export directory not found: $GHIDRA_EXPORT" >&2
  exit 1
fi
GHIDRA_EXPORT=$(cd -- "$GHIDRA_EXPORT" && pwd)
mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)

INVENTORY="$OUT_DIR/release_wrapper_caller_inventory.json"
TARGETS_FILE="$OUT_DIR/release_wrapper_caller_targets.txt"
INSTRUCTIONS="$OUT_DIR/release_wrapper_caller_instructions.jsonl"
REPORT="$OUT_DIR/release_wrapper_callsite_evidence.json"

python3 "$SCRIPT_DIR/build_release_wrapper_caller_inventory.py" \
  "$GHIDRA_EXPORT" \
  --max-callers "$MAX_CALLERS" \
  --json-out "$INVENTORY" \
  --targets-out "$TARGETS_FILE"

mapfile -t TARGETS < "$TARGETS_FILE"
if (( ${#TARGETS[@]} == 0 )); then
  echo "error: no direct FUN_00886930/FUN_00886950 callers were found" >&2
  exit 1
fi

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$INSTRUCTIONS" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_release_wrapper_callsites.py" \
  "$INVENTORY" "$INSTRUCTIONS" \
  --json-out "$REPORT"

echo "release wrapper caller inventory: $INVENTORY"
echo "release wrapper caller instructions: $INSTRUCTIONS"
echo "release wrapper callsite evidence: $REPORT"
