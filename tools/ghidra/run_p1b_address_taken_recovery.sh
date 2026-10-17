#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "Usage: GHIDRA_HOME=/opt/ghidra $0 <project-dir> <project-name> <program-name> <output.tsv>" >&2
  exit 2
fi
: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
OUTPUT=$4
SCRIPT_DIR=$(mktemp -d)
trap 'rm -rf -- "$SCRIPT_DIR"' EXIT
cp -- "$(dirname -- "$0")/RecoverP1bAddressTakenFunctions.java" "$SCRIPT_DIR/"

"$GHIDRA_HOME/support/analyzeHeadless" \
  "$PROJECT_DIR" "$PROJECT_NAME" \
  -process "$PROGRAM_NAME" \
  -noanalysis \
  -commit "Recover verified P1B address-taken bodies" \
  -scriptPath "$SCRIPT_DIR" \
  -postScript RecoverP1bAddressTakenFunctions.java "$OUTPUT"
