#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_s5_retail_instruction_bundle.sh \
    <project-dir> <project-name> <program-name> <functions-jsonl> <output-dir>

Exports the exact union of all S5 targeted retail instruction surfaces once,
then splits that export into exact 3/5/9-function inputs for the existing
scheduler, rate-accessor and corrected BManager analyzers. Static analysis only;
it does not execute the retail game or use runtime capture.
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
BUNDLE="$OUT_DIR/s5_retail_instruction_bundle.jsonl"
SCHEDULER="$OUT_DIR/s5_scheduler_accumulator_instructions.jsonl"
RATE_ACCESSOR="$OUT_DIR/s5_physics_manager_rate_accessor_instructions.jsonl"
BMANAGER="$OUT_DIR/s5_bmanager_dispatch_instructions.jsonl"

SCHEDULER_FRONTIER="$OUT_DIR/s5_scheduler_accumulator_frontier.json"
SCHEDULER_VALUE="$OUT_DIR/s5_scheduler_accumulator_value_provenance.json"
SCHEDULER_PUSH="$OUT_DIR/s5_scheduler_push_producer_value_provenance.json"
RATE_ALIAS="$OUT_DIR/s5_physics_manager_rate_accessor_alias.json"
BMANAGER_FRONTIER="$OUT_DIR/s5_bmanager_dispatch_frontier.json"

# Stable exact union: scheduler first, rate-only additions second, then the
# corrected BManager registration/list/timing/default-dispatch additions.
TARGETS=(
  FUN_007155e9
  FUN_00715380
  FUN_00713050
  FUN_0070fe90
  FUN_0041903c
  FUN_0070fe99
  FUN_0070fae0
  FUN_00647d80
  FUN_00647ef0
  FUN_0065b8b0
  FUN_006626a0
  FUN_00662880
  FUN_00d36000
  FUN_006485b0
  FUN_00662600
)

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$BUNDLE" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/split_s5_retail_instruction_bundle.py" \
  "$BUNDLE" \
  "$OUT_DIR"

python3 "$SCRIPT_DIR/analyze_s5_scheduler_accumulator_slice.py" \
  "$SCHEDULER" \
  "$FUNCTIONS_JSONL" \
  "$REPO_ROOT/evidence/physics_manager_scheduler_entry_owner.json" \
  --json-out "$SCHEDULER_FRONTIER"

python3 "$SCRIPT_DIR/analyze_s5_scheduler_accumulator_value_provenance.py" \
  "$SCHEDULER" \
  "$SCHEDULER_FRONTIER" \
  --json-out "$SCHEDULER_VALUE"

python3 "$SCRIPT_DIR/analyze_s5_scheduler_push_producer.py" \
  "$SCHEDULER" \
  "$SCHEDULER_FRONTIER" \
  "$SCHEDULER_VALUE" \
  --json-out "$SCHEDULER_PUSH"

python3 "$SCRIPT_DIR/analyze_s5_physics_manager_rate_accessor.py" \
  "$RATE_ACCESSOR" \
  "$FUNCTIONS_JSONL" \
  "$REPO_ROOT/evidence/physics_manager_scheduler_entry_owner.json" \
  "$REPO_ROOT/src/physics/physics_system_runtime.py" \
  --json-out "$RATE_ALIAS"

python3 "$SCRIPT_DIR/analyze_s5_bmanager_dispatch_slice.py" \
  "$BMANAGER" \
  "$FUNCTIONS_JSONL" \
  "$REPO_ROOT/evidence/physics_manager_scheduler_entry_owner.json" \
  --json-out "$BMANAGER_FRONTIER"

echo "S5 retail instruction bundle: $BUNDLE"
echo "S5 exact bundle manifest: $OUT_DIR/s5_retail_instruction_bundle_manifest.json"
echo "S5 scheduler PUSH producer: $SCHEDULER_PUSH"
echo "S5 Physics Manager rate-accessor alias: $RATE_ALIAS"
echo "S5 corrected BManager dispatch frontier: $BMANAGER_FRONTIER"
