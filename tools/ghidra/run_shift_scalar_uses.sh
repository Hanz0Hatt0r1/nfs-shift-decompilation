#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_shift_scalar_uses.sh \
    <project-dir> <project-name> <program-name> <output.jsonl> <scalar-hex>

The Ghidra project must already contain an analyzed SHIFT.exe program.
Set REVENGINSTR_REPO to the shared checkout when it is outside this repository's sibling directory.
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
OUT_FILE=$4
SCALAR=$5
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ANALYZE_HEADLESS="$GHIDRA_HOME/support/analyzeHeadless"
if [[ ! -x "$ANALYZE_HEADLESS" ]]; then
  echo "error: analyzeHeadless not found or not executable: $ANALYZE_HEADLESS" >&2
  exit 1
fi

mkdir -p -- "$(dirname -- "$OUT_FILE")"
OUT_DIR=$(cd -- "$(dirname -- "$OUT_FILE")" && pwd)
OUT_FILE="$OUT_DIR/$(basename -- "$OUT_FILE")"

NFS_REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
SHARED_REPO=$(printenv REVENGINSTR_REPO || true)
if [[ -z "$SHARED_REPO" ]]; then
  SHARED_REPO="$NFS_REPO_ROOT/../revenginstr"
fi
SHARED_RUNNER="$SHARED_REPO/scripts/run_ghidra_scalar_uses.sh"
SHARED_EXPORTER="$SHARED_REPO/ghidra/ExportGhidraScalarUses.java"

COMPAT_SCRIPT_DIR=$(mktemp -d)
cleanup() {
  rm -rf -- "$COMPAT_SCRIPT_DIR"
}
trap cleanup EXIT

if [[ -x "$SHARED_RUNNER" && -f "$SHARED_EXPORTER" ]]; then
  GENERIC_OUT_FILE="$COMPAT_SCRIPT_DIR/scalar-uses.jsonl"
  GHIDRA_HOME="$GHIDRA_HOME" "$SHARED_RUNNER" \
    "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$GENERIC_OUT_FILE" "$SCALAR"
  python3 "$SCRIPT_DIR/adapt_revenginstr_scalar_uses.py" "$GENERIC_OUT_FILE" "$OUT_FILE"
else
  cp -- "$SCRIPT_DIR/ShiftScalarUseExporter.java" \
    "$COMPAT_SCRIPT_DIR/ShiftScalarUseExporter.java"
  "$ANALYZE_HEADLESS" \
    "$PROJECT_DIR" "$PROJECT_NAME" \
    -recursive \
    -process "$PROGRAM_NAME" \
    -readOnly \
    -noanalysis \
    -scriptPath "$COMPAT_SCRIPT_DIR" \
    -postScript ShiftScalarUseExporter.java "$OUT_FILE" "$SCALAR"
fi
