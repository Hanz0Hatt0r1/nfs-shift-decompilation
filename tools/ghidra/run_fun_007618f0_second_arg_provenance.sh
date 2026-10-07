#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_fun_007618f0_second_arg_provenance.sh \
    <project-dir> <project-name> <program-name> <full-evidence-root> <output-dir>

The full evidence root must contain binary.json, functions.jsonl and
callgraph.jsonl from ShiftEvidenceExporter.java for the same retail SHIFT.exe.
EOF
}

if [[ $# -ne 5 ]]; then
  usage >&2
  exit 2
fi

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
EVIDENCE_ROOT=$4
OUT_DIR=$5

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)

WORKLIST="$OUT_DIR/fun_007618f0_second_arg_worklist.json"
TARGETS_FILE="$OUT_DIR/fun_007618f0_second_arg_targets.txt"
INSTRUCTIONS="$OUT_DIR/fun_007618f0_second_arg_instructions.jsonl"
REPORT="$OUT_DIR/fun_007618f0_second_arg_provenance.json"

python3 "$SCRIPT_DIR/build_fun_007618f0_second_arg_worklist.py" \
  "$EVIDENCE_ROOT" \
  --json-out "$WORKLIST" \
  --targets-out "$TARGETS_FILE"

mapfile -t TARGETS < "$TARGETS_FILE"
"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$INSTRUCTIONS" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_fun_007618f0_second_arg_provenance.py" \
  "$WORKLIST" "$INSTRUCTIONS" \
  --json-out "$REPORT"

echo "FUN_007618f0 second-argument provenance ready: $REPORT"
