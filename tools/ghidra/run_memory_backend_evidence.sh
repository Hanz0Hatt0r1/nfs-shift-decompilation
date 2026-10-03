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
cross-check allocation/free diagnostics and the release backend chain, then
attempts fail-closed local slices for the allocation `%d` and free `%p`
diagnostic varargs plus behavior-only tracking of the release-path entry DL byte.

The raw targeted export is preserved as memory_backend_instructions_v2.jsonl so
structured p-code remains available to newer analyzers. Existing memory analyzers
consume the separately normalized memory_backend_instructions.jsonl v1
compatibility copy.
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
INSTRUCTIONS_V2="$OUT_DIR/memory_backend_instructions_v2.jsonl"
INSTRUCTIONS="$OUT_DIR/memory_backend_instructions.jsonl"
REPORT="$OUT_DIR/memory_backend_evidence.json"
ALLOCATION_SLICE="$OUT_DIR/memory_allocation_diagnostic_slice.json"
FREE_SLICE="$OUT_DIR/memory_free_diagnostic_slice.json"
RELEASE_BYTE_BEHAVIOR="$OUT_DIR/memory_release_byte_behavior.json"

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS_V2" \
  FUN_00638020 \
  FUN_006382b0 \
  FUN_0064f260 \
  FUN_0064f4c0 \
  FUN_0064f3a0 \
  FUN_00657c30

python3 "$SCRIPT_DIR/normalize_function_instruction_export.py" \
  "$INSTRUCTIONS_V2" \
  "$INSTRUCTIONS"

python3 "$SCRIPT_DIR/analyze_memory_backend_evidence.py" \
  "$INSTRUCTIONS" \
  --ghidra-export "$GHIDRA_EXPORT" \
  --json-out "$REPORT"

python3 "$SCRIPT_DIR/analyze_allocation_diagnostic_slice.py" \
  "$INSTRUCTIONS" \
  --ghidra-export "$GHIDRA_EXPORT" \
  --json-out "$ALLOCATION_SLICE"

python3 "$SCRIPT_DIR/analyze_free_diagnostic_slice.py" \
  "$INSTRUCTIONS" \
  --ghidra-export "$GHIDRA_EXPORT" \
  --json-out "$FREE_SLICE"

python3 "$SCRIPT_DIR/analyze_release_byte_behavior.py" \
  "$INSTRUCTIONS" \
  --json-out "$RELEASE_BYTE_BEHAVIOR"

echo "memory backend instruction export v2: $INSTRUCTIONS_V2"
echo "memory backend instruction compatibility export: $INSTRUCTIONS"
echo "memory backend evidence report: $REPORT"
echo "memory allocation diagnostic slice: $ALLOCATION_SLICE"
echo "memory free diagnostic slice: $FREE_SLICE"
echo "memory release-byte behavior: $RELEASE_BYTE_BEHAVIOR"
