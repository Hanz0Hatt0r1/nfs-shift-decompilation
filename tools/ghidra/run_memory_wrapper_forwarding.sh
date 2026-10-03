#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_memory_wrapper_forwarding.sh \
    <project-dir> <project-name> <program-name> <output-dir>

The Ghidra project must already contain an analyzed SHIFT.exe program. The
runner exports only the five retail memory-wrapper functions, validates the
instruction JSONL, and immediately builds SHIFT-MEMORY-WRAPPER-FORWARDING/1.
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

mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)

INSTRUCTIONS="$OUT_DIR/memory_wrapper_instructions.jsonl"
FORWARDING="$OUT_DIR/memory_wrapper_forwarding.json"

TARGETS=(
  FUN_008868c0
  FUN_008868d0
  FUN_00886900
  FUN_00886930
  FUN_00886950
)

bash "$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$INSTRUCTIONS" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_memory_wrapper_forwarding.py" \
  "$INSTRUCTIONS" \
  --json-out "$FORWARDING"

python3 - "$FORWARDING" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
report = json.loads(path.read_text(encoding="utf-8"))
if report.get("format") != "SHIFT-MEMORY-WRAPPER-FORWARDING/1":
    raise SystemExit(f"unexpected forwarding format: {report.get('format')!r}")
print(f"forwarding wrappers: {report.get('wrapper_count')}")
print(f"confirmed forwarding: {report.get('confirmed_wrapper_forwarding_count')}")
print(f"all wrapper forwarding confirmed: {report.get('all_wrapper_forwarding_confirmed')}")
PY

echo "memory wrapper forwarding ready: $FORWARDING"
