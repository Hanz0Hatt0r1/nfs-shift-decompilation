#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_memory_backend_evidence.sh \
    <project-dir> <project-name> <program-name> <ghidra-export-dir> <output-dir>

Example:
  GHIDRA_HOME=/opt/ghidra ./tools/ghidra/run_memory_backend_evidence.sh \
    /home/pes/ghidra_projects/shift shift SHIFT.exe \
    out/shift_ghidra_database out/memory_backend_evidence

The full Ghidra export directory must contain callgraph.jsonl and
strings_xrefs.jsonl. The runner exports only the six backend functions needed to
cross-check allocation/free diagnostics and the release backend chain.
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
GHIDRA_EXPORT=$4
OUT_DIR=$5
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
if [[ -d "$GHIDRA_EXPORT" ]]; then
  GHIDRA_EXPORT=$(cd -- "$GHIDRA_EXPORT" && pwd)
fi
INSTRUCTIONS="$OUT_DIR/memory_backend_instructions.jsonl"
REPORT="$OUT_DIR/memory_backend_evidence.json"

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS" \
  FUN_00638020 \
  FUN_006382b0 \
  FUN_0064f260 \
  FUN_0064f4c0 \
  FUN_0064f3a0 \
  FUN_00657c30

python3 "$SCRIPT_DIR/analyze_memory_backend_evidence.py" \
  "$INSTRUCTIONS" \
  --ghidra-export "$GHIDRA_EXPORT" \
  --json-out "$REPORT"

echo "memory backend instruction export: $INSTRUCTIONS"
echo "memory backend evidence report: $REPORT"
