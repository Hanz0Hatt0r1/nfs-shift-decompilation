#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 || $# -gt 6 ]]; then
  echo "Usage: GHIDRA_HOME=/opt/ghidra $0 <project-dir> <project-name> SHIFT.exe <output.jsonl.gz> [offset] [limit]" >&2
  exit 2
fi

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
OUTPUT=$4
OFFSET=${5:-0}
LIMIT=${6:-0}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
NFS_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
REVENGINSTR_REPO=${REVENGINSTR_REPO:-"$NFS_ROOT/../revenginstr"}
GENERIC_RUNNER="$REVENGINSTR_REPO/scripts/run_ghidra_function_instructions.sh"

if [[ "$PROGRAM_NAME" != "SHIFT.exe" ]]; then
  echo "error: expected the analyzed PC retail program SHIFT.exe" >&2
  exit 2
fi
if [[ "$OUTPUT" != *.gz ]]; then
  echo "error: full function corpora must use .gz output" >&2
  exit 2
fi
if [[ ! "$OFFSET" =~ ^[0-9]+$ || ! "$LIMIT" =~ ^[0-9]+$ ]]; then
  echo "error: offset and limit must be non-negative integers" >&2
  exit 2
fi
if [[ ! -f "$GENERIC_RUNNER" ]]; then
  echo "error: revenginstr Ghidra exporter not found: $GENERIC_RUNNER" >&2
  echo "hint: set REVENGINSTR_REPO to the generic tooling checkout" >&2
  exit 1
fi

exec bash "$GENERIC_RUNNER" \
  "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$OUTPUT" --all "$OFFSET" "$LIMIT"
