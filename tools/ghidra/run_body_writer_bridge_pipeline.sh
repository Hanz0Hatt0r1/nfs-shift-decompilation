#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/path/to/ghidra ./tools/ghidra/run_body_writer_bridge_pipeline.sh \
    <ghidra-export-dir> <project-dir> <project-name> <program-name> <output-dir>

Example:
  GHIDRA_HOME=/opt/ghidra ./tools/ghidra/run_body_writer_bridge_pipeline.sh \
    out/shift_ghidra_database \
    /home/pes/ghidra_projects/shift shift SHIFT.exe \
    out/body_writer_bridge

Environment:
  SHIFT_BODY_FRONTIER_MAX_DEPTH    direct-callgraph depth (default: 2)
  SHIFT_BODY_FRONTIER_MAX_TARGETS  targeted function limit (default: 128)

The pipeline is target-selection evidence only. It does not prove that a base
register is a BODY pointer or that a candidate is a persistent-state writer.
EOF
}

if [[ $# -ne 5 ]]; then
  usage >&2
  exit 2
fi

: "${GHIDRA_HOME:?Set GHIDRA_HOME to the Ghidra installation directory}"

GHIDRA_EXPORT=$1
PROJECT_DIR=$2
PROJECT_NAME=$3
PROGRAM_NAME=$4
OUT_DIR=$5
MAX_DEPTH=${SHIFT_BODY_FRONTIER_MAX_DEPTH:-2}
MAX_TARGETS=${SHIFT_BODY_FRONTIER_MAX_TARGETS:-128}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

if [[ ! -d "$GHIDRA_EXPORT" ]]; then
  echo "error: Ghidra export directory not found: $GHIDRA_EXPORT" >&2
  exit 1
fi
case "$MAX_DEPTH" in
  ''|*[!0-9]*) echo "error: SHIFT_BODY_FRONTIER_MAX_DEPTH must be a positive integer" >&2; exit 2 ;;
esac
case "$MAX_TARGETS" in
  ''|*[!0-9]*) echo "error: SHIFT_BODY_FRONTIER_MAX_TARGETS must be a positive integer" >&2; exit 2 ;;
esac
if (( MAX_DEPTH < 1 || MAX_TARGETS < 1 )); then
  echo "error: frontier depth/target limits must be >= 1" >&2
  exit 2
fi

GHIDRA_EXPORT=$(cd -- "$GHIDRA_EXPORT" && pwd)
mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)

FRONTIER_JSON="$OUT_DIR/physics_vehicle_callgraph_frontier.json"
TARGETS_TXT="$OUT_DIR/physics_vehicle_instruction_targets.txt"
INSTRUCTIONS_JSONL="$OUT_DIR/physics_vehicle_frontier_instructions.jsonl"
ACCESSES_JSON="$OUT_DIR/physics_vehicle_register_relative_accesses.json"
CANDIDATES_JSON="$OUT_DIR/body_writer_bridge_candidates.json"
JOIN_JSON="$OUT_DIR/body_writer_bridge_frontier_join.json"
MANIFEST_JSON="$OUT_DIR/body_writer_bridge_pipeline_manifest.json"

python3 "$SCRIPT_DIR/build_proven_callgraph_frontier.py" \
  "$GHIDRA_EXPORT" \
  --subsystem physics \
  --subsystem vehicle \
  --max-depth "$MAX_DEPTH" \
  --max-targets "$MAX_TARGETS" \
  --json-out "$FRONTIER_JSON" \
  --targets-out "$TARGETS_TXT"

mapfile -t TARGETS < "$TARGETS_TXT"
if (( ${#TARGETS[@]} == 0 )); then
  echo "error: callgraph frontier produced no instruction-export targets" >&2
  exit 1
fi

"$SCRIPT_DIR/run_shift_function_instructions.sh" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  "$PROGRAM_NAME" \
  "$INSTRUCTIONS_JSONL" \
  "${TARGETS[@]}"

python3 "$SCRIPT_DIR/analyze_register_relative_accesses.py" \
  "$INSTRUCTIONS_JSONL" \
  --json-out "$ACCESSES_JSON"

python3 "$SCRIPT_DIR/build_body_writer_bridge_candidates.py" \
  "$ACCESSES_JSON" \
  --json-out "$CANDIDATES_JSON"

python3 "$SCRIPT_DIR/join_body_writer_candidates_to_frontier.py" \
  "$CANDIDATES_JSON" \
  --frontier "$FRONTIER_JSON" \
  --json-out "$JOIN_JSON"

python3 - "$FRONTIER_JSON" "$ACCESSES_JSON" "$CANDIDATES_JSON" "$JOIN_JSON" "$MANIFEST_JSON" <<'PY'
import json
import sys
from pathlib import Path

frontier_path, accesses_path, candidates_path, join_path, manifest_path = map(Path, sys.argv[1:])
frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
accesses = json.loads(accesses_path.read_text(encoding="utf-8"))
candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
joined = json.loads(join_path.read_text(encoding="utf-8"))
manifest = {
    "format": "SHIFT.BodyWriterBridgePipelineManifest/1",
    "frontier": str(frontier_path),
    "register_relative_accesses": str(accesses_path),
    "bridge_candidates": str(candidates_path),
    "frontier_join": str(join_path),
    "instruction_export_target_count": frontier.get("instruction_export_target_count", 0),
    "register_relative_access_count": accesses.get("access_count", 0),
    "bridge_candidate_count": candidates.get("candidate_count", 0),
    "combined_bridge_group_count": candidates.get("combined_bridge_group_count", 0),
    "proven_slice_root_candidate_count": joined.get("proven_slice_root_candidate_count", 0),
    "frontier_candidate_count": joined.get("frontier_candidate_count", 0),
    "outside_frontier_candidate_count": joined.get("outside_frontier_candidate_count", 0),
    "scope": {
        "body_pointer_provenance_resolved": False,
        "persistent_state_writer_proven": False,
        "integration_order_proven": False,
        "pose_integration_proven": False,
    },
}
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "BODY writer callgraph frontier: $FRONTIER_JSON"
echo "BODY writer instruction targets: $TARGETS_TXT"
echo "BODY writer p-code instructions: $INSTRUCTIONS_JSONL"
echo "BODY writer register-relative accesses: $ACCESSES_JSON"
echo "BODY writer bridge candidates: $CANDIDATES_JSON"
echo "BODY writer frontier join: $JOIN_JSON"
echo "BODY writer pipeline manifest: $MANIFEST_JSON"
