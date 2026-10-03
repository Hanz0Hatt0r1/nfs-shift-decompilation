#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra tools/ghidra/run_fun_00765470_body_owner_receiver.sh \
    <project-dir> <project-name> <program-name> <out-dir>

Read-only proof pipeline:
  Ghidra project -> exact FUN_00765470 instruction/p-code export
                 -> ECX all-path provenance at CALL 0x0076582a
                 -> SHIFT.Fun00765470BodyOwnerReceiverProvenance/1

This does not execute the target program.
EOF
}

if [[ $# -ne 4 ]]; then
  usage >&2
  exit 2
fi

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
OUT_DIR=$4
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd -- "$SCRIPT_DIR/../.." && pwd)

mkdir -p "$OUT_DIR"
INSTRUCTIONS="$OUT_DIR/fun_00765470_instructions.jsonl"
REPORT="$OUT_DIR/fun_00765470_body_owner_receiver.json"

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS" \
  0x00765470

python3 "$ROOT_DIR/tools/ghidra/analyze_fun_00765470_body_owner_receiver.py" \
  "$INSTRUCTIONS" \
  --json-out "$REPORT"

printf 'instructions: %s\n' "$INSTRUCTIONS"
printf 'report: %s\n' "$REPORT"
