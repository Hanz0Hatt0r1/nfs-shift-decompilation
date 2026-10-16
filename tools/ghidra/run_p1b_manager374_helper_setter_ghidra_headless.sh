#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra \
    bash tools/ghidra/run_p1b_manager374_helper_setter_ghidra_headless.sh \
    <project-dir> <project-name> <program-name> <output-dir>

The project must already contain the analyzed PC retail SHIFT.exe program.
The output directory must not exist or must be empty.

Optional environment:
  SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS=1800
    Bounds the read-only headless export when GNU timeout is available.
EOF
}

if [[ $# -ne 4 ]]; then
  usage >&2
  exit 2
fi

: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

PROJECT_DIR=$1
PROJECT_NAME=$2
PROGRAM_NAME=$3
REQUESTED_OUT=$4
TIMEOUT_SECONDS=${SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS:-1800}

if [[ ! "$TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ANALYZE_HEADLESS="$GHIDRA_HOME/support/analyzeHeadless"
EXPORTER="$SCRIPT_DIR/ShiftCompactInstructionStreamExporter.java"
BRIDGE="$SCRIPT_DIR/run_p1b_manager374_helper_setter_ghidra_frontier.py"
ADAPTER="$SCRIPT_DIR/adapt_revenginstr_compact_instruction_stream.py"

if [[ ! -x "$ANALYZE_HEADLESS" ]]; then
  echo "error: analyzeHeadless not found or not executable: $ANALYZE_HEADLESS" >&2
  exit 1
fi
if [[ ! -f "$BRIDGE" ]]; then
  echo "error: Ghidra helper-setter bridge missing: $BRIDGE" >&2
  exit 1
fi
NFS_REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
SHARED_REPO=$(printenv REVENGINSTR_REPO || true)
if [[ -z "$SHARED_REPO" ]]; then SHARED_REPO="$NFS_REPO_ROOT/../revenginstr"; fi
SHARED_RUNNER="$SHARED_REPO/scripts/run_ghidra_compact_instruction_stream.sh"
SHARED_EXPORTER="$SHARED_REPO/ghidra/ExportGhidraCompactInstructionStream.java"
USE_SHARED_EXPORTER=0
if [[ -x "$SHARED_RUNNER" && -f "$SHARED_EXPORTER" ]]; then
  USE_SHARED_EXPORTER=1
elif [[ ! -f "$EXPORTER" ]]; then
  echo "error: compact instruction exporter missing: $EXPORTER" >&2
  exit 1
fi
if (( USE_SHARED_EXPORTER == 1 )) && [[ ! -f "$ADAPTER" ]]; then
  echo "error: shared compact instruction adapter missing: $ADAPTER" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required" >&2
  exit 1
fi
if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "error: Ghidra project directory does not exist: $PROJECT_DIR" >&2
  exit 2
fi
PROJECT_DIR=$(cd -- "$PROJECT_DIR" && pwd)

OUT_PARENT_RAW=$(dirname -- "$REQUESTED_OUT")
OUT_BASENAME=$(basename -- "$REQUESTED_OUT")
mkdir -p -- "$OUT_PARENT_RAW"
OUT_PARENT=$(cd -- "$OUT_PARENT_RAW" && pwd)
OUT_DIR="$OUT_PARENT/$OUT_BASENAME"

if [[ -e "$OUT_DIR" ]]; then
  if [[ ! -d "$OUT_DIR" ]]; then
    echo "error: output path exists and is not a directory: $OUT_DIR" >&2
    exit 2
  fi
  if find "$OUT_DIR" -mindepth 1 -print -quit | grep -q .; then
    echo "error: output directory must be empty: $OUT_DIR" >&2
    exit 2
  fi
fi

# Fail before opening the project if a previous headless run for the exact same
# project/program is still alive. Never kill or mutate the existing process.
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
  echo "hint: stop the stale session, then rerun this command" >&2
  exit 3
fi

STAGE_ROOT=$(mktemp -d "$OUT_PARENT/.p1b-helper-setter-ghidra.XXXXXX")
COMPAT_SCRIPT_DIR=$(mktemp -d)
PUBLISHED=0
cleanup() {
  rm -rf -- "$COMPAT_SCRIPT_DIR"
  if [[ $PUBLISHED -eq 0 ]]; then
    rm -rf -- "$STAGE_ROOT"
  else
    rmdir -- "$STAGE_ROOT" 2>/dev/null || true
  fi
}
trap cleanup EXIT

RESULT_DIR="$STAGE_ROOT/result"
mkdir -p -- "$RESULT_DIR"
STREAM="$STAGE_ROOT/compact_instruction_stream.jsonl.gz"
HEADLESS_LOG="$STAGE_ROOT/ghidra_headless.log"

if (( USE_SHARED_EXPORTER == 1 )); then
  GENERIC_STREAM="$STAGE_ROOT/generic_compact_instruction_stream.jsonl.gz"
  set +e
  REVENGINSTR_GHIDRA_HEADLESS_TIMEOUT_SECONDS="$TIMEOUT_SECONDS" \
    "$SHARED_RUNNER" "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" \
    "$GENERIC_STREAM" >"$HEADLESS_LOG" 2>&1
  HEADLESS_STATUS=$?
  set -e
  if [[ $HEADLESS_STATUS -ne 0 ]]; then
    cat "$HEADLESS_LOG" >&2 || true
    if [[ $HEADLESS_STATUS -eq 124 || $HEADLESS_STATUS -eq 137 ]]; then
      echo "error: Ghidra headless did not complete within ${TIMEOUT_SECONDS}s" >&2
    fi
    exit "$HEADLESS_STATUS"
  fi
  if [[ ! -s "$GENERIC_STREAM" ]]; then
    cat "$HEADLESS_LOG" >&2 || true
    echo "error: shared exporter produced no compact instruction stream" >&2
    exit 1
  fi
  python3 "$ADAPTER" "$GENERIC_STREAM" "$STREAM"
  python3 - "$GENERIC_STREAM" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).unlink()
PY
else
  # Isolate only the local fallback exporter from scripts unrelated to this export.
  cp -- "$EXPORTER" "$COMPAT_SCRIPT_DIR/ShiftCompactInstructionStreamExporter.java"
  HEADLESS_CMD=(
    "$ANALYZE_HEADLESS" "$PROJECT_DIR" "$PROJECT_NAME"
    -process "$PROGRAM_NAME" -readOnly -noanalysis
    -scriptPath "$COMPAT_SCRIPT_DIR"
    -postScript ShiftCompactInstructionStreamExporter.java "$STREAM"
  )
  HEADLESS_STATUS=0
  if command -v timeout >/dev/null 2>&1; then
    set +e
    timeout --signal=TERM --kill-after=10s "${TIMEOUT_SECONDS}s" \
      "${HEADLESS_CMD[@]}" >"$HEADLESS_LOG" 2>&1
    HEADLESS_STATUS=$?
    set -e
  else
    set +e
    "${HEADLESS_CMD[@]}" >"$HEADLESS_LOG" 2>&1
    HEADLESS_STATUS=$?
    set -e
  fi
  if [[ $HEADLESS_STATUS -eq 124 || $HEADLESS_STATUS -eq 137 ]]; then
    cat "$HEADLESS_LOG" >&2 || true
    echo "error: Ghidra headless did not complete within ${TIMEOUT_SECONDS}s" >&2
    exit "$HEADLESS_STATUS"
  fi
  if [[ $HEADLESS_STATUS -ne 0 ]]; then
    cat "$HEADLESS_LOG" >&2 || true
    exit "$HEADLESS_STATUS"
  fi
fi

if [[ ! -s "$STREAM" ]]; then
  cat "$HEADLESS_LOG" >&2 || true
  echo "error: Ghidra exporter produced no compact instruction stream" >&2
  exit 1
fi

python3 "$BRIDGE" "$STREAM" --out-dir "$RESULT_DIR"

# Preserve the exact corroborating input and headless log beside the generated
# contracts. The acquisition JSON already records both the file and canonical
# instruction-stream hashes.
mv -- "$STREAM" "$RESULT_DIR/compact_instruction_stream.jsonl.gz"
mv -- "$HEADLESS_LOG" "$RESULT_DIR/ghidra_headless.log"

# Final publication guard: refuse to publish if the bridge contract or its
# fail-closed semantic boundary drifted unexpectedly.
python3 - "$RESULT_DIR/ghidra_acquisition.json" "$RESULT_DIR/frontier.json" <<'PY'
import json
import sys
from pathlib import Path

acquisition = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
frontier = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

assert acquisition.get("format") == "SHIFT.P1B.Manager374GhidraHelperSetterAcquisition/1"
assert acquisition.get("ready") is True
assert frontier.get("format") == "SHIFT.P1B.Manager374HelperSetterRetailFrontier/1"

auth = acquisition.get("authority", {})
assert auth.get("raw_executable_sha256_verified_in_this_run") is False
assert auth.get("canonical_instruction_stream_sha256")
assert auth.get("canonical_instruction_stream_sha256") == frontier.get("authority", {}).get(
    "canonical_instruction_stream_sha256"
)

adj = acquisition.get("adjudication", {})
assert adj.get("ghidra_helper_setter_probe_bundle_execution_complete") is True
assert adj.get("ghidra_helper_setter_candidate_frontier_composed") is True
assert adj.get("retail_helper_setter_probe_bundle_execution_complete") is False
assert adj.get("retail_helper_setter_candidate_frontier_composed") is False
for key in (
    "global_helper_non_vtable_indirect_setter_surface_complete",
    "external_or_unknown_origin_outer_alias_surface_complete",
    "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete",
    "unrecognized_runtime_transform_root_origin_surface_complete",
    "global_manager_root_origin_surface_complete",
    "manager_374_join_to_hdvehicle_4330_complete",
    "last_literal_0x004b86cf_rejected",
    "p1_3_control_producer_complete",
):
    assert adj.get(key) is False, key
assert adj.get("external_provider_count") == 7
PY

# Publish only after exporter, bridge and contract guards all succeed. Keeping
# staging under the destination parent makes the final rename filesystem-local.
if [[ -d "$OUT_DIR" ]]; then
  rmdir -- "$OUT_DIR"
fi
mv -- "$RESULT_DIR" "$OUT_DIR"
PUBLISHED=1

echo "P1B Ghidra helper-setter acquisition ready: $OUT_DIR"
