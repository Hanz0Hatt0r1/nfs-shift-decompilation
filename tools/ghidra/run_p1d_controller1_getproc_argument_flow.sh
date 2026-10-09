#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_p1d_controller1_getproc_argument_flow.sh \
    <project-dir> <project-name> <program-name> <shift-ghidra.sqlite> <output-dir>

Runs the existing read-only targeted instruction exporter for the six
Controller #1 worker-reachable GetProcAddress caller functions, then adjudicates
all 11 pinned lpProcName arguments.
EOF
}

if [[ $# -ne 5 ]]; then
  usage >&2
  exit 2
fi

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
SQLITE=$4
OUT_DIR=$5

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
PLAN="$ROOT/evidence/p1d_controller1_getproc_argument_worklist.json"
INSTRUCTIONS="$OUT_DIR/p1d_controller1_getproc_instructions.jsonl"
RESULT="$OUT_DIR/p1d_controller1_getproc_argument_flow.json"

mkdir -p -- "$OUT_DIR"
mapfile -t TARGETS < <(python3 - "$PLAN" <<'PY'
import json, sys
payload=json.load(open(sys.argv[1], encoding='utf-8'))
for row in payload['targets']:
    print(row['function'])
PY
)

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$INSTRUCTIONS" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_p1d_controller1_getproc_argument_flow.py" \
  "$INSTRUCTIONS" "$SQLITE" "$PLAN" --output "$RESULT"

python3 - "$RESULT" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding='utf-8'))
s=p['surface']
a=p['adjudication']
print('P1D Controller #1 GetProcAddress argument flow')
print('  expected calls:', s['expected_getprocaddress_call_count'])
print('  exact literal names:', s['recovered_literal_name_count'])
print('  unresolved names:', s['unresolved_name_count'])
print('  APC literal calls:', s['apc_name_call_count'])
print('  direct named resolver surface rejected:', a['direct_named_resolver_surface_rejected'])
print('  Controller #1 timing exhaustive:', a['controller1_timing_exhaustive'])
PY

echo "instruction export: $INSTRUCTIONS"
echo "argument-flow result: $RESULT"
