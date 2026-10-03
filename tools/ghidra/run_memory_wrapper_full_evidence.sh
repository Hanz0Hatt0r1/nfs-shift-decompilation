#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_memory_wrapper_full_evidence.sh \
    <SHIFT.exe.c> <ghidra-export-dir> \
    <project-dir> <project-name> <program-name> <output-dir>

Example:
  GHIDRA_HOME=/opt/ghidra ./tools/ghidra/run_memory_wrapper_full_evidence.sh \
    /path/to/SHIFT.exe.c out/shift_ghidra_database \
    /home/pes/ghidra_projects/shift shift SHIFT.exe \
    out/memory_wrapper_full_evidence

This runner joins source wrapper callsites, targeted wrapper forwarding,
source-argument -> backend-storage provenance, repeated provenance patterns,
targeted backend instruction/diagnostic evidence, proven allocation-size and
released-pointer source roles, cross-branch released-pointer forwarding into the
FUN_0064f260 alternate backend, retail static memory evidence, behavior-only
release-byte observations, and a conservative runtime wrapper manifest.
Release-flag/delete-kind and ownership semantics remain unassigned.
EOF
}

if [[ $# -ne 6 ]]; then
  usage >&2
  exit 2
fi

: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

SOURCE=$1
GHIDRA_EXPORT=$2
PROJECT_DIR=$3
PROJECT_NAME=$4
PROGRAM_NAME=$5
OUT_DIR=$6
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
LIVE_DUMP_DIR=$(cd -- "$SCRIPT_DIR/../shift_live_dump" && pwd)

if [[ ! -f "$SOURCE" ]]; then
  echo "error: recovered source not found: $SOURCE" >&2
  exit 1
fi
if [[ ! -d "$GHIDRA_EXPORT" ]]; then
  echo "error: Ghidra export directory not found: $GHIDRA_EXPORT" >&2
  exit 1
fi

SOURCE=$(cd -- "$(dirname -- "$SOURCE")" && pwd)/$(basename -- "$SOURCE")
GHIDRA_EXPORT=$(cd -- "$GHIDRA_EXPORT" && pwd)
mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)

CALLSITES_JSON="$OUT_DIR/memory_wrapper_callsites.json"
FORWARDING_DIR="$OUT_DIR/forwarding"
FORWARDING_JSON="$FORWARDING_DIR/memory_wrapper_forwarding.json"
ARGUMENT_JOIN_JSON="$OUT_DIR/memory_wrapper_argument_join.json"
PATTERNS_JSON="$OUT_DIR/memory_wrapper_provenance_patterns.json"
BACKEND_DIR="$OUT_DIR/backend"
BACKEND_INSTRUCTIONS="$BACKEND_DIR/memory_backend_instructions.jsonl"
BACKEND_JSON="$BACKEND_DIR/memory_backend_evidence.json"
DIAGNOSTIC_SLICE_JSON="$BACKEND_DIR/memory_allocation_diagnostic_slice.json"
FREE_DIAGNOSTIC_SLICE_JSON="$BACKEND_DIR/memory_free_diagnostic_slice.json"
RELEASE_BYTE_BEHAVIOR_JSON="$BACKEND_DIR/memory_release_byte_behavior.json"
ALLOCATION_SIZE_ROLE_JSON="$OUT_DIR/memory_allocation_size_role_join.json"
RELEASE_POINTER_CHAIN_JSON="$OUT_DIR/memory_release_pointer_chain.json"
RELEASE_ALTERNATE_BACKEND_JSON="$OUT_DIR/memory_release_alternate_backend.json"
RELEASED_POINTER_ROLE_JSON="$OUT_DIR/memory_released_pointer_role_join.json"
STATIC_SUMMARY_JSON="$OUT_DIR/memory_retail_static_summary.json"
SOURCE_SEMANTIC_SUMMARY_JSON="$OUT_DIR/memory_source_semantic_summary.json"
RUNTIME_MANIFEST_JSON="$OUT_DIR/memory_wrapper_runtime_manifest.json"

python3 "$LIVE_DUMP_DIR/extract_memory_wrapper_callsites.py" \
  "$SOURCE" \
  --ghidra-export "$GHIDRA_EXPORT" \
  --json-out "$CALLSITES_JSON"

"$SCRIPT_DIR/run_memory_wrapper_forwarding.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$FORWARDING_DIR"

python3 "$LIVE_DUMP_DIR/join_memory_wrapper_argument_evidence.py" \
  "$CALLSITES_JSON" \
  --forwarding "$FORWARDING_JSON" \
  --json-out "$ARGUMENT_JOIN_JSON"

python3 "$LIVE_DUMP_DIR/summarize_memory_wrapper_argument_patterns.py" \
  "$ARGUMENT_JOIN_JSON" \
  --json-out "$PATTERNS_JSON"

"$SCRIPT_DIR/run_memory_backend_evidence.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$GHIDRA_EXPORT" \
  "$BACKEND_DIR"

python3 "$LIVE_DUMP_DIR/join_allocation_size_role.py" \
  "$ARGUMENT_JOIN_JSON" \
  --diagnostic-slice "$DIAGNOSTIC_SLICE_JSON" \
  --json-out "$ALLOCATION_SIZE_ROLE_JSON"

python3 "$SCRIPT_DIR/analyze_release_pointer_chain.py" \
  "$BACKEND_INSTRUCTIONS" \
  --free-slice "$FREE_DIAGNOSTIC_SLICE_JSON" \
  --forwarding "$FORWARDING_JSON" \
  --json-out "$RELEASE_POINTER_CHAIN_JSON"

python3 "$SCRIPT_DIR/analyze_release_alternate_backend.py" \
  "$RELEASE_POINTER_CHAIN_JSON" \
  --forwarding "$FORWARDING_JSON" \
  --json-out "$RELEASE_ALTERNATE_BACKEND_JSON"

python3 "$LIVE_DUMP_DIR/join_released_pointer_role.py" \
  "$ARGUMENT_JOIN_JSON" \
  --release-chain "$RELEASE_POINTER_CHAIN_JSON" \
  --json-out "$RELEASED_POINTER_ROLE_JSON"

python3 "$SCRIPT_DIR/summarize_memory_retail_static_evidence.py" \
  --forwarding "$FORWARDING_JSON" \
  --backend "$BACKEND_JSON" \
  --allocation-slice "$DIAGNOSTIC_SLICE_JSON" \
  --free-slice "$FREE_DIAGNOSTIC_SLICE_JSON" \
  --release-chain "$RELEASE_POINTER_CHAIN_JSON" \
  --release-byte "$RELEASE_BYTE_BEHAVIOR_JSON" \
  --json-out "$STATIC_SUMMARY_JSON"

python3 "$LIVE_DUMP_DIR/summarize_memory_source_semantics.py" \
  --static-summary "$STATIC_SUMMARY_JSON" \
  --allocation-size-role "$ALLOCATION_SIZE_ROLE_JSON" \
  --released-pointer-role "$RELEASED_POINTER_ROLE_JSON" \
  --json-out "$SOURCE_SEMANTIC_SUMMARY_JSON"

python3 "$LIVE_DUMP_DIR/build_memory_wrapper_runtime_manifest.py" \
  --forwarding "$FORWARDING_JSON" \
  --static-summary "$STATIC_SUMMARY_JSON" \
  --source-summary "$SOURCE_SEMANTIC_SUMMARY_JSON" \
  --json-out "$RUNTIME_MANIFEST_JSON"

echo "memory wrapper callsites: $CALLSITES_JSON"
echo "memory wrapper forwarding: $FORWARDING_JSON"
echo "memory wrapper argument join: $ARGUMENT_JOIN_JSON"
echo "memory wrapper provenance patterns: $PATTERNS_JSON"
echo "memory backend evidence: $BACKEND_JSON"
echo "memory allocation-size role join: $ALLOCATION_SIZE_ROLE_JSON"
echo "memory release-pointer chain: $RELEASE_POINTER_CHAIN_JSON"
echo "memory release alternate backend: $RELEASE_ALTERNATE_BACKEND_JSON"
echo "memory released-pointer role join: $RELEASED_POINTER_ROLE_JSON"
echo "memory retail static summary: $STATIC_SUMMARY_JSON"
echo "memory source semantic summary: $SOURCE_SEMANTIC_SUMMARY_JSON"
echo "memory wrapper runtime manifest: $RUNTIME_MANIFEST_JSON"
