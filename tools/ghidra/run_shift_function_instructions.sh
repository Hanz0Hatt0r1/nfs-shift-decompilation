#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_shift_function_instructions.sh \
    <project-dir> <project-name> <program-name> <output-jsonl> \
    <function-address> [function-address ...]

Addresses may be written as 0x00886900, 00886900, or FUN_00886900.
The Ghidra project must already contain an analyzed SHIFT.exe program.

Optional environment:
  SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS=300
    Bounds the headless project-open/script run when GNU timeout is available.
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

# Target lists are often populated with `mapfile -t`. A file containing a blank
# line produces one empty array element, which previously reached Ghidra as an
# empty script argument and generated a confusing "requested functions not
# found:" failure. Drop empty/whitespace-only entries before invoking Ghidra and
# fail locally when nothing usable remains.
RAW_TARGETS=("$@")
TARGETS=()
IGNORED_EMPTY_TARGETS=0
for target in "${RAW_TARGETS[@]}"; do
  trimmed=${target#"${target%%[![:space:]]*}"}
  trimmed=${trimmed%"${trimmed##*[![:space:]]}"}
  if [[ -z "$trimmed" ]]; then
    ((IGNORED_EMPTY_TARGETS += 1))
    continue
  fi
  TARGETS+=("$trimmed")
done

if (( ${#TARGETS[@]} == 0 )); then
  echo "error: no non-empty function targets were supplied" >&2
  echo "hint: inspect the generated target list before running Ghidra" >&2
  echo "hint: sed -n 'l' <target-file>" >&2
  exit 2
fi
if (( IGNORED_EMPTY_TARGETS > 0 )); then
  echo "warning: ignored ${IGNORED_EMPTY_TARGETS} empty function target(s)" >&2
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

# A previous timed-out/aborted AnalyzeHeadless may keep the project open even
# after its launching shell has exited. Fail before starting another contender
# instead of waiting for a project lock for the full timeout window. We match
# only headless sessions for this exact project directory and program; GUI
# sessions and unrelated projects are never killed or modified here.
CONFLICTING_HEADLESS=()
if command -v pgrep >/dev/null 2>&1; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if [[ "$line" == *"ghidra.app.util.headless.AnalyzeHeadless"* \
       && "$line" == *"$PROJECT_DIR"* \
       && "$line" == *"-process $PROGRAM_NAME"* ]]; then
      CONFLICTING_HEADLESS+=("$line")
    fi
  done < <(pgrep -af 'ghidra\.app\.util\.headless\.AnalyzeHeadless' || true)
fi

if (( ${#CONFLICTING_HEADLESS[@]} > 0 )); then
  echo "error: existing Ghidra headless session(s) already target this project/program" >&2
  printf '  %s\n' "${CONFLICTING_HEADLESS[@]}" >&2
  echo "hint: stop those stale AnalyzeHeadless/java processes, then rerun this command" >&2
  echo "hint: pgrep -af 'AnalyzeHeadless|Ghidra'" >&2
  exit 3
fi

mkdir -p -- "$(dirname -- "$OUT_FILE")"
OUT_DIR=$(cd -- "$(dirname -- "$OUT_FILE")" && pwd)
OUT_FILE="$OUT_DIR/$(basename -- "$OUT_FILE")"

# Keep Ghidra's Java script compiler isolated from the rest of tools/ghidra.
# Ghidra compiles Java files it discovers under -scriptPath, so pointing it at
# the repository directory can make an unrelated script's API incompatibility
# abort this targeted export. Copy only the requested exporter into a temporary
# script directory and compile exactly that source.
COMPAT_SCRIPT_DIR=$(mktemp -d)
cleanup() {
  rm -rf -- "$COMPAT_SCRIPT_DIR"
}
trap cleanup EXIT
cp -- "$SCRIPT_DIR/ShiftFunctionInstructionExporter.java" \
  "$COMPAT_SCRIPT_DIR/ShiftFunctionInstructionExporter.java"

# This exporter is observational only. -readOnly tells Ghidra that any incidental
# program changes are disposable and avoids requesting a writable processing
# session for the existing project.
HEADLESS_CMD=(
  "$ANALYZE_HEADLESS"
  "$PROJECT_DIR" "$PROJECT_NAME"
  -process "$PROGRAM_NAME"
  -readOnly
  -noanalysis
  -scriptPath "$COMPAT_SCRIPT_DIR"
  -postScript ShiftFunctionInstructionExporter.java "$OUT_FILE" "${TARGETS[@]}"
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
  echo "hint: close any GUI instance using this project and check for stale AnalyzeHeadless/java processes" >&2
  echo "hint: pgrep -af 'AnalyzeHeadless|Ghidra|java'" >&2
  exit "$HEADLESS_STATUS"
fi
if [[ $HEADLESS_STATUS -ne 0 ]]; then
  exit "$HEADLESS_STATUS"
fi

python3 "$SCRIPT_DIR/validate_function_instruction_export.py" \
  "$OUT_FILE" "${TARGETS[@]}"

echo "instruction export ready: $OUT_FILE"
