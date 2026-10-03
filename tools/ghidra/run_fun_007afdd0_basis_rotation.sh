#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_fun_007afdd0_basis_rotation.sh \
    <project-dir> <project-name> <program-name> <output-dir>

Example:
  GHIDRA_HOME=/opt/ghidra ./tools/ghidra/run_fun_007afdd0_basis_rotation.sh \
    /home/pes/ghidra_projects/shift shift SHIFT.exe out/fun_007afdd0_basis_rotation

The Ghidra project must already contain an analyzed SHIFT.exe program. The
runner exports only FUN_007afdd0 with machine instructions plus structured
p-code varnodes and builds the fail-closed Phase 680 precision/order report.
It does not run the game.
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
INSTRUCTIONS="$OUT_DIR/fun_007afdd0_instructions.jsonl"
REPORT="$OUT_DIR/fun_007afdd0_basis_rotation_static.json"

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS" \
  FUN_007afdd0

python3 "$SCRIPT_DIR/validate_function_instruction_export.py" \
  "$INSTRUCTIONS" \
  FUN_007afdd0

python3 "$SCRIPT_DIR/analyze_fun_007afdd0_basis_rotation.py" \
  "$INSTRUCTIONS" \
  --json-out "$REPORT"

echo "FUN_007afdd0 instruction export: $INSTRUCTIONS"
echo "FUN_007afdd0 static precision report: $REPORT"
EOF
