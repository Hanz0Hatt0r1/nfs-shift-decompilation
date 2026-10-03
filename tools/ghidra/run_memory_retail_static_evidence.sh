#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra bash ./tools/ghidra/run_memory_retail_static_evidence.sh \
    <project-dir> <project-name> <program-name> <ghidra-export-dir> <output-dir>

Example:
  GHIDRA_HOME=/opt/ghidra \
  bash ./tools/ghidra/run_memory_retail_static_evidence.sh \
    /home/pes/ghidra_projects/shift shift SHIFT.exe \
    out/shift_ghidra_database out/memory_retail_static_evidence

This runner requires the analyzed Ghidra project plus the structured full Ghidra
export. It does not require SHIFT.exe.c or any recovered/decompiler source file.
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

if [[ ! -d "$GHIDRA_EXPORT" ]]; then
  echo "error: Ghidra export directory not found: $GHIDRA_EXPORT" >&2
  exit 1
fi
GHIDRA_EXPORT=$(cd -- "$GHIDRA_EXPORT" && pwd)
mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)

FORWARDING_DIR="$OUT_DIR/forwarding"
FORWARDING_JSON="$FORWARDING_DIR/memory_wrapper_forwarding.json"
BACKEND_DIR="$OUT_DIR/backend"
BACKEND_INSTRUCTIONS="$BACKEND_DIR/memory_backend_instructions.jsonl"
BACKEND_JSON="$BACKEND_DIR/memory_backend_evidence.json"
ALLOCATION_SLICE_JSON="$BACKEND_DIR/memory_allocation_diagnostic_slice.json"
FREE_SLICE_JSON="$BACKEND_DIR/memory_free_diagnostic_slice.json"
RELEASE_BYTE_JSON="$BACKEND_DIR/memory_release_byte_behavior.json"
RELEASE_CHAIN_JSON="$OUT_DIR/memory_release_pointer_chain.json"
SUMMARY_JSON="$OUT_DIR/memory_retail_static_summary.json"

"$SCRIPT_DIR/run_memory_wrapper_forwarding.sh" \
  "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$FORWARDING_DIR"

"$SCRIPT_DIR/run_memory_backend_evidence.sh" \
  "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$GHIDRA_EXPORT" "$BACKEND_DIR"

python3 "$SCRIPT_DIR/analyze_release_pointer_chain.py" \
  "$BACKEND_INSTRUCTIONS" \
  --free-slice "$FREE_SLICE_JSON" \
  --forwarding "$FORWARDING_JSON" \
  --json-out "$RELEASE_CHAIN_JSON"

python3 "$SCRIPT_DIR/summarize_memory_retail_static_evidence.py" \
  --forwarding "$FORWARDING_JSON" \
  --backend "$BACKEND_JSON" \
  --allocation-slice "$ALLOCATION_SLICE_JSON" \
  --free-slice "$FREE_SLICE_JSON" \
  --release-chain "$RELEASE_CHAIN_JSON" \
  --release-byte "$RELEASE_BYTE_JSON" \
  --json-out "$SUMMARY_JSON"

echo "retail wrapper forwarding: $FORWARDING_JSON"
echo "retail backend evidence: $BACKEND_JSON"
echo "retail release-pointer chain: $RELEASE_CHAIN_JSON"
echo "retail static summary: $SUMMARY_JSON"
