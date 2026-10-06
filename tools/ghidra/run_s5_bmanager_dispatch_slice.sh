#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_s5_bmanager_dispatch_slice.sh \
    <project-dir> <project-name> <program-name> <functions-jsonl> <output-dir>

Exports only the narrow BManager/cPhysicsManager S5 dispatch-registration slice
from an already analyzed SHIFT.exe project, then builds a fail-closed frontier.
The functions-jsonl argument must be the matching retail Ghidra export used for
ABI validation. No game/runtime execution is performed.
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
INSTRUCTIONS="$OUT_DIR/s5_bmanager_dispatch_instructions.jsonl"
FRONTIER="$OUT_DIR/s5_bmanager_dispatch_frontier.json"

TARGETS=(
  FUN_00647b70
  FUN_00647c60
  FUN_00647cf0
  FUN_00647da0
  FUN_0065bb50
  FUN_00d36000
  FUN_006485b0
  FUN_00662600
  FUN_0070fe90
)

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_s5_bmanager_dispatch_slice.py" \
  "$INSTRUCTIONS" \
  "$FUNCTIONS_JSONL" \
  "$REPO_ROOT/evidence/physics_manager_scheduler_entry_owner.json" \
  --json-out "$FRONTIER"

echo "S5 targeted instruction slice: $INSTRUCTIONS"
echo "S5 BManager dispatch frontier: $FRONTIER"
