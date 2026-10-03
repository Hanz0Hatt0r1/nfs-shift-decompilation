#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_memory_wrapper_forwarding.sh \
    <project-dir> <project-name> <program-name> <output-dir>

Example:
  GHIDRA_HOME=/opt/ghidra ./tools/ghidra/run_memory_wrapper_forwarding.sh \
    /home/pes/ghidra_projects/shift shift SHIFT.exe out/memory_wrapper_forwarding

The Ghidra project must already contain an analyzed SHIFT.exe program. The
runner exports only the five known memory-wrapper functions and immediately
builds SHIFT-MEMORY-WRAPPER-FORWARDING/1 evidence from that instruction slice.
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

mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
INSTRUCTION_JSONL="$OUT_DIR/memory_wrapper_instructions.jsonl"
FORWARDING_JSON="$OUT_DIR/memory_wrapper_forwarding.json"

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTION_JSONL" \
  FUN_008868c0 \
  FUN_008868d0 \
  FUN_00886900 \
  FUN_00886930 \
  FUN_00886950

python3 "$SCRIPT_DIR/analyze_memory_wrapper_forwarding.py" \
  "$INSTRUCTION_JSONL" \
  --json-out "$FORWARDING_JSON"

echo "memory wrapper instruction export: $INSTRUCTION_JSONL"
echo "memory wrapper forwarding report: $FORWARDING_JSON"
