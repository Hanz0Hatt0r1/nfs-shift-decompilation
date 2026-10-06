#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_s5_physics_manager_rate_accessor_slice.sh \
    <project-dir> <project-name> <program-name> <functions-jsonl> <output-dir>

Exports only the S5 Physics Manager scheduler-rate accessor chain from an
already analyzed retail SHIFT.exe project, then proves the return alias and the
+0x388 receiver relationship fail-closed. No game/runtime execution occurs.
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
FUNCTIONS_JSONL=$4
OUT_DIR=$5
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

if [[ ! -f "$FUNCTIONS_JSONL" ]]; then
  echo "error: functions.jsonl not found: $FUNCTIONS_JSONL" >&2
  exit 2
fi

mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
INSTRUCTIONS="$OUT_DIR/s5_physics_manager_rate_accessor_instructions.jsonl"
FRONTIER="$OUT_DIR/s5_physics_manager_rate_accessor_alias.json"

TARGETS=(
  FUN_00713050
  FUN_0070fe90
  FUN_0041903c
  FUN_0070fe99
  FUN_0070fae0
)

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_s5_physics_manager_rate_accessor.py" \
  "$INSTRUCTIONS" \
  "$FUNCTIONS_JSONL" \
  "$REPO_ROOT/evidence/physics_manager_scheduler_entry_owner.json" \
  "$REPO_ROOT/src/physics/physics_system_runtime.py" \
  --json-out "$FRONTIER"

echo "S5 rate-accessor instruction slice: $INSTRUCTIONS"
echo "S5 Physics Manager rate-accessor alias: $FRONTIER"
