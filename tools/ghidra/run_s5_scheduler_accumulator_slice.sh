#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_s5_scheduler_accumulator_slice.sh \
    <project-dir> <project-name> <program-name> <output-dir>

Exports only the remaining S5 scheduler-accumulator producer slice from an
already analyzed retail SHIFT.exe project, then builds a fail-closed static
frontier. No original-game/runtime execution or capture is performed.
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
REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
INSTRUCTIONS="$OUT_DIR/s5_scheduler_accumulator_instructions.jsonl"
FRONTIER="$OUT_DIR/s5_scheduler_accumulator_frontier.json"

TARGETS=(
  FUN_007155e9
  FUN_00715380
  FUN_00713050
)

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_s5_scheduler_accumulator_slice.py" \
  "$INSTRUCTIONS" \
  "$REPO_ROOT/functions.jsonl" \
  "$REPO_ROOT/evidence/physics_manager_scheduler_entry_owner.json" \
  --json-out "$FRONTIER"

echo "S5 targeted accumulator instruction slice: $INSTRUCTIONS"
echo "S5 scheduler accumulator frontier: $FRONTIER"
