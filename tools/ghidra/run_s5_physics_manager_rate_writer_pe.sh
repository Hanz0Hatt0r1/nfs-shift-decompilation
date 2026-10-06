#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./tools/ghidra/run_s5_physics_manager_rate_writer_pe.sh \
    <SHIFT.exe> <SHIFT.exe.c> <functions.jsonl> <callgraph.jsonl> <output.json>

Runs the file-backed retail cPhysicsManager +0x388 writer proof without launching
the game and without requiring Ghidra to be installed. SHIFT.exe.c and the JSONL
files are static exports from the already analyzed matching retail program.
EOF
}

if [[ $# -ne 5 ]]; then
  usage >&2
  exit 2
fi

SHIFT_EXE=$1
DECOMPILER_C=$2
FUNCTIONS_JSONL=$3
CALLGRAPH_JSONL=$4
OUTPUT=$5
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

for input in "$SHIFT_EXE" "$DECOMPILER_C" "$FUNCTIONS_JSONL" "$CALLGRAPH_JSONL"; do
  if [[ ! -f "$input" ]]; then
    echo "error: required static input not found: $input" >&2
    exit 2
  fi
done

python3 "$SCRIPT_DIR/analyze_s5_physics_manager_rate_writer_pe.py" \
  "$SHIFT_EXE" \
  "$DECOMPILER_C" \
  "$FUNCTIONS_JSONL" \
  "$CALLGRAPH_JSONL" \
  "$REPO_ROOT/evidence/physics_manager_scheduler_entry_owner.json" \
  --json-out "$OUTPUT"

echo "S5 Physics Manager +0x388 writer provenance: $OUTPUT"
