#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "Usage: GHIDRA_HOME=/opt/ghidra $0 <isolated-project-dir> <project-name> <program-name> <plan.tsv> <output.tsv>" >&2
  exit 2
fi
: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

PROJECT_DIR=$(cd -- "$1" && pwd)
PROJECT_NAME=$2
PROGRAM_NAME=$3
PLAN=$4
OUTPUT=$5

# This batch mutates only the isolated project copy used for recovery.
if [[ "$(basename -- "$PROJECT_DIR")" != "shift-recovered-mass-20261017" || "$PROJECT_NAME" != "shift" ]]; then
  echo "error: refusing to mutate a project other than the isolated shift-recovered-mass-20261017 copy" >&2
  exit 1
fi
[[ -f "$PLAN" ]] || { echo "error: plan not found: $PLAN" >&2; exit 1; }
mkdir -p -- "$(dirname -- "$OUTPUT")"
OUTPUT="$(cd -- "$(dirname -- "$OUTPUT")" && pwd)/$(basename -- "$OUTPUT")"

SCRIPT_DIR=$(mktemp -d)
trap 'rm -rf -- "$SCRIPT_DIR"' EXIT
cp -- "$(dirname -- "$0")/RecoverP1bAddressTakenFunctionsBatch2.java" "$SCRIPT_DIR/"

"$GHIDRA_HOME/support/analyzeHeadless" \
  "$PROJECT_DIR" "$PROJECT_NAME" \
  -process "$PROGRAM_NAME" \
  -noanalysis \
  -commit "Recover verified P1B address-taken callers batch 2" \
  -scriptPath "$SCRIPT_DIR" \
  -postScript RecoverP1bAddressTakenFunctionsBatch2.java "$PLAN" "$OUTPUT"
