#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_shift_instruction_slices.sh \
    <project-dir> <project-name> <program-name> <output-jsonl> \
    <address[:hex-length]> [address[:hex-length] ...]

Example targets: 0x0045f620:0x80 0x0045f630:0x40
The Ghidra project must already contain an analyzed SHIFT.exe program.
EOF
}

if [[ $# -lt 5 ]]; then usage >&2; exit 2; fi
: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"
PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
OUT_FILE=$4
shift 4
TARGETS=("$@")
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
if [[ -d "$PROJECT_DIR" ]]; then PROJECT_DIR=$(cd -- "$PROJECT_DIR" && pwd); fi
mkdir -p -- "$(dirname -- "$OUT_FILE")"
OUT_DIR=$(cd -- "$(dirname -- "$OUT_FILE")" && pwd)
OUT_FILE="$OUT_DIR/$(basename -- "$OUT_FILE")"

COMPAT_SCRIPT_DIR=$(mktemp -d)
cleanup() { rm -rf -- "$COMPAT_SCRIPT_DIR"; }
trap cleanup EXIT
cp -- "$SCRIPT_DIR/ShiftInstructionSliceExporter.java" \
  "$COMPAT_SCRIPT_DIR/ShiftInstructionSliceExporter.java"

HEADLESS_CMD=(
  "$ANALYZE_HEADLESS"
  "$PROJECT_DIR" "$PROJECT_NAME"
  -process "$PROGRAM_NAME"
  -readOnly
  -noanalysis
  -scriptPath "$COMPAT_SCRIPT_DIR"
  -postScript ShiftInstructionSliceExporter.java "$OUT_FILE" "${TARGETS[@]}"
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
if [[ $HEADLESS_STATUS -ne 0 ]]; then exit "$HEADLESS_STATUS"; fi

python3 - "$OUT_FILE" "$PROGRAM_NAME" "${TARGETS[@]}" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
program = sys.argv[2]
expected = [arg.split(':', 1)[0].lower() for arg in sys.argv[3:]]
rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
if len(rows) != len(expected):
    raise SystemExit(f"error: expected {len(expected)} slice rows, got {len(rows)}")
seen = []
for row in rows:
    if row.get('format') != 'SHIFT.GhidraInstructionSlice/1':
        raise SystemExit('error: instruction-slice format drift')
    if row.get('program') != program:
        raise SystemExit(f"error: program identity drift: {row.get('program')!r} != {program!r}")
    start = str(row.get('start') or '').lower()
    seen.append(start)
    if row.get('exact_instruction_at_start') is not True:
        raise SystemExit(f"error: no exact instruction at slice start {start}")
    if not isinstance(row.get('instructions'), list) or not row['instructions']:
        raise SystemExit(f"error: empty instruction slice {start}")
if seen != expected:
    raise SystemExit(f"error: slice target order drift: expected={expected}, got={seen}")
print(f"instruction slice export: PASS ({len(rows)} slices)")
PY

echo "instruction slice export ready: $OUT_FILE"
