#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_shift_global_references.sh \
    <project-dir> <project-name> <program-name> <output-jsonl> \
    <global-address> [global-address ...]

Addresses may be written as 0x00bc185c, 00bc185c, or DAT_00bc185c.
The Ghidra project must already contain an analyzed SHIFT.exe program.

Optional environment:
  SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS=300
EOF
}

if [[ $# -lt 5 ]]; then
  usage >&2
  exit 2
fi

: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
OUT_FILE=$4
shift 4

RAW_TARGETS=("$@")
TARGETS=()
for target in "${RAW_TARGETS[@]}"; do
  trimmed=${target#"${target%%[![:space:]]*}"}
  trimmed=${trimmed%"${trimmed##*[![:space:]]}"}
  [[ -n "$trimmed" ]] && TARGETS+=("$trimmed")
done

if (( ${#TARGETS[@]} == 0 )); then
  echo "error: no non-empty global targets were supplied" >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ANALYZE_HEADLESS="$GHIDRA_HOME/support/analyzeHeadless"
TIMEOUT_SECONDS=${SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS:-300}

if [[ ! "$TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
fi
if [[ ! -x "$ANALYZE_HEADLESS" ]]; then
  echo "error: analyzeHeadless not found or not executable: $ANALYZE_HEADLESS" >&2
  exit 1
fi
if [[ -d "$PROJECT_DIR" ]]; then
  PROJECT_DIR=$(cd -- "$PROJECT_DIR" && pwd)
fi

mkdir -p -- "$(dirname -- "$OUT_FILE")"
OUT_DIR=$(cd -- "$(dirname -- "$OUT_FILE")" && pwd)
OUT_FILE="$OUT_DIR/$(basename -- "$OUT_FILE")"

NFS_REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
SHARED_REPO=$(printenv REVENGINSTR_REPO || true)
if [[ -z "$SHARED_REPO" ]]; then
  SHARED_REPO="$NFS_REPO_ROOT/../revenginstr"
fi
SHARED_EXPORTER="$SHARED_REPO/ghidra/ExportGhidraAddressReferences.java"
USE_SHARED_EXPORTER=0
EXPORTER_NAME=ShiftGlobalReferenceExporter.java
EXPORTER_SOURCE="$SCRIPT_DIR/$EXPORTER_NAME"
if [[ -f "$SHARED_EXPORTER" ]]; then
  USE_SHARED_EXPORTER=1
  EXPORTER_NAME=ExportGhidraAddressReferences.java
  EXPORTER_SOURCE=$SHARED_EXPORTER
fi

COMPAT_SCRIPT_DIR=$(mktemp -d)
cleanup() {
  rm -rf -- "$COMPAT_SCRIPT_DIR"
}
trap cleanup EXIT
cp -- "$EXPORTER_SOURCE" "$COMPAT_SCRIPT_DIR/$EXPORTER_NAME"
GENERIC_OUT_FILE="$COMPAT_SCRIPT_DIR/address-references.jsonl"
OUT_FILE_FOR_GHIDRA=$OUT_FILE
if (( USE_SHARED_EXPORTER == 1 )); then
  OUT_FILE_FOR_GHIDRA=$GENERIC_OUT_FILE
fi

HEADLESS_CMD=(
  "$ANALYZE_HEADLESS"
  "$PROJECT_DIR" "$PROJECT_NAME"
  -process "$PROGRAM_NAME"
  -readOnly
  -noanalysis
  -scriptPath "$COMPAT_SCRIPT_DIR"
  -postScript "$EXPORTER_NAME" "$OUT_FILE_FOR_GHIDRA" "${TARGETS[@]}"
)

HEADLESS_STATUS=0
if command -v timeout >/dev/null 2>&1; then
  set +e
  timeout --signal=TERM --kill-after=10s "${TIMEOUT_SECONDS}s" "${HEADLESS_CMD[@]}"
  HEADLESS_STATUS=$?
  set -e
else
  set +e
  "${HEADLESS_CMD[@]}"
  HEADLESS_STATUS=$?
  set -e
fi

if [[ $HEADLESS_STATUS -eq 124 || $HEADLESS_STATUS -eq 137 ]]; then
  echo "error: Ghidra headless did not complete within ${TIMEOUT_SECONDS}s" >&2
  exit "$HEADLESS_STATUS"
fi
if [[ $HEADLESS_STATUS -ne 0 ]]; then
  exit "$HEADLESS_STATUS"
fi

if (( USE_SHARED_EXPORTER == 1 )); then
  python3 "$SCRIPT_DIR/adapt_revenginstr_address_references.py" \
    "$GENERIC_OUT_FILE" "$OUT_FILE"
fi

python3 "$SCRIPT_DIR/validate_global_reference_export.py" \
  "$OUT_FILE" "${TARGETS[@]}"

echo "global-reference export ready: $OUT_FILE"
