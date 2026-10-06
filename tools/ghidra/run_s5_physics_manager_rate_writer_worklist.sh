#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_s5_physics_manager_rate_writer_worklist.sh \
    <project-dir> <project-name> <program-name> <functions-jsonl> <output-dir>

Builds a bounded static candidate worklist for machine STOREs at displacement
+0x388 near the source-backed Physics Manager/accessor/scheduler surface.
Address-window selection is discovery-only and never proves class membership.
No game/runtime execution or capture is performed.
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

if [[ ! -f "$FUNCTIONS_JSONL" ]]; then
  echo "error: functions.jsonl not found: $FUNCTIONS_JSONL" >&2
  exit 2
fi

mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
SELECTION="$OUT_DIR/s5_physics_manager_rate_writer_target_selection.json"
TARGET_NAMES="$OUT_DIR/s5_physics_manager_rate_writer_target_names.txt"
INSTRUCTIONS="$OUT_DIR/s5_physics_manager_rate_writer_instructions.jsonl"
ACCESSES="$OUT_DIR/s5_physics_manager_rate_writer_register_relative_accesses.json"
WORKLIST="$OUT_DIR/s5_physics_manager_rate_writer_worklist.json"

python3 "$SCRIPT_DIR/select_s5_physics_manager_rate_writer_targets.py" \
  "$FUNCTIONS_JSONL" \
  --json-out "$SELECTION" \
  --names-out "$TARGET_NAMES"

mapfile -t TARGETS < "$TARGET_NAMES"
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "error: bounded Physics Manager rate-writer target selection is empty" >&2
  exit 1
fi

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_register_relative_accesses.py" \
  "$INSTRUCTIONS" \
  --json-out "$ACCESSES"

python3 "$SCRIPT_DIR/analyze_s5_physics_manager_rate_writer_candidates.py" \
  "$SELECTION" \
  "$ACCESSES" \
  --json-out "$WORKLIST"

echo "S5 rate-writer target selection: $SELECTION"
echo "S5 rate-writer instruction slice: $INSTRUCTIONS"
echo "S5 rate-writer register-relative accesses: $ACCESSES"
echo "S5 rate-writer candidate worklist: $WORKLIST"
