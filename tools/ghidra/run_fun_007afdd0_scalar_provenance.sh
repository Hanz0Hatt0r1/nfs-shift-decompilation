#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_fun_007afdd0_scalar_provenance.sh \
    <project-dir> <project-name> <program-name> <output-dir>

This is a static-only continuation of Phase 680. It reuses the existing targeted
FUN_007afdd0 instruction/p-code export, verifies the Phase 680 freeze, then
emits the Phase 692 scalar-provenance frontier. It never executes SHIFT.exe.
EOF
}

if [[ $# -ne 4 ]]; then
  usage >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
OUT_DIR=$4

"$SCRIPT_DIR/run_fun_007afdd0_basis_rotation.sh" "$1" "$2" "$3" "$OUT_DIR"

OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
INSTRUCTIONS="$OUT_DIR/fun_007afdd0_instructions.jsonl"
STATIC_REPORT="$OUT_DIR/fun_007afdd0_basis_rotation_static.json"
PROVENANCE_REPORT="$OUT_DIR/fun_007afdd0_scalar_provenance.json"

python3 "$SCRIPT_DIR/analyze_fun_007afdd0_scalar_provenance.py" \
  "$INSTRUCTIONS" \
  "$STATIC_REPORT" \
  --json-out "$PROVENANCE_REPORT"

echo "FUN_007afdd0 scalar provenance: $PROVENANCE_REPORT"
