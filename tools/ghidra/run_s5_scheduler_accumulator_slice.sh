#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_s5_scheduler_accumulator_slice.sh \
    <project-dir> <project-name> <program-name> <output-dir>

Exports only the remaining S5 scheduler-accumulator producer slice from an
already analyzed retail SHIFT.exe project, then builds the fail-closed writer
surface, local accumulator value provenance and upper pushed-value producer
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
VALUE_PROVENANCE="$OUT_DIR/s5_scheduler_accumulator_value_provenance.json"
ARGUMENT_PRODUCER="$OUT_DIR/s5_scheduler_timing_argument_producer.json"

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

python3 "$SCRIPT_DIR/analyze_s5_scheduler_accumulator_value_provenance.py" \
  "$INSTRUCTIONS" \
  "$FRONTIER" \
  --json-out "$VALUE_PROVENANCE"

python3 "$SCRIPT_DIR/analyze_s5_scheduler_timing_argument_producer.py" \
  "$INSTRUCTIONS" \
  "$FRONTIER" \
  "$VALUE_PROVENANCE" \
  --json-out "$ARGUMENT_PRODUCER"

echo "S5 targeted accumulator instruction slice: $INSTRUCTIONS"
echo "S5 scheduler accumulator frontier: $FRONTIER"
echo "S5 scheduler accumulator value provenance: $VALUE_PROVENANCE"
echo "S5 scheduler timing argument producer frontier: $ARGUMENT_PRODUCER"
