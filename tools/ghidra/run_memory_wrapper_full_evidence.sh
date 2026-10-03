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

This runner joins three independent layers without assigning semantic argument
roles: source wrapper callsites, targeted Ghidra instruction forwarding, and the
mechanical source-argument -> backend-storage provenance join.
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

echo "memory wrapper callsites: $CALLSITES_JSON"
echo "memory wrapper forwarding: $FORWARDING_JSON"
echo "memory wrapper argument join: $ARGUMENT_JOIN_JSON"
