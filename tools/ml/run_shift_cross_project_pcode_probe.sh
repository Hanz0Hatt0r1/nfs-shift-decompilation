#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/opt/ghidra \
  ./tools/ml/run_shift_cross_project_pcode_probe.sh \
    <project-dir> <project-name> <program-name> <output-dir>

Optional environment:
  SHIFT_ML_MAX_FUNCTIONS       Number of internal functions to export (default 1000)
  SHIFT_ML_NAME_CONTAINS      Optional qualified-name substring filter
  NEVERGONE_REPO              Path to nevergone-recomp; enables model transfer probe
  NEVERGONE_MODEL_DIR         Override P-code-only model directory
  SHIFT_FOREIGN_MIN_SIMILARITY Foreign-project family-similarity floor (default 0.70)
  SHIFT_FOREIGN_MIN_CONTRAST   Foreign-project contrast-margin floor (default 0.05)

The Ghidra project must already contain an analyzed SHIFT.exe. The runner uses
-noanalysis/-readOnly, isolates the ML exporter from unrelated Ghidra scripts,
and never changes semantic/provenance gates.
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
OUT_DIR=$4
MAX_FUNCTIONS=${SHIFT_ML_MAX_FUNCTIONS:-1000}
NAME_FILTER=${SHIFT_ML_NAME_CONTAINS:-}
FOREIGN_MIN_SIMILARITY=${SHIFT_FOREIGN_MIN_SIMILARITY:-0.70}
FOREIGN_MIN_CONTRAST=${SHIFT_FOREIGN_MIN_CONTRAST:-0.05}
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
ANALYZE="$GHIDRA_HOME/support/analyzeHeadless"
SCRIPT_DIR="$ROOT/tools/ghidra"

[[ -x "$ANALYZE" ]] || { echo "error: analyzeHeadless not executable: $ANALYZE" >&2; exit 1; }
mkdir -p "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
CORPUS="$OUT_DIR/shift-pcode.jsonl"
CLASSIFIED="$OUT_DIR/nevergone-v4-transfer.jsonl"
GUARDED="$OUT_DIR/nevergone-v4-transfer-foreign-guard.jsonl"
SUMMARY="$OUT_DIR/cross-project-audit.json"

ARGS=("$CORPUS" "$MAX_FUNCTIONS")
if [[ -n "$NAME_FILTER" ]]; then
  ARGS+=("$NAME_FILTER")
fi

# Headless Ghidra tries to compile every Java file in -scriptPath. Keep this
# probe isolated so unrelated legacy scripts cannot inject compiler warnings or
# fail because of API changes that are irrelevant to the ML exporter.
ML_SCRIPT_DIR=$(mktemp -d)
trap 'rm -rf -- "$ML_SCRIPT_DIR"' EXIT
cp "$SCRIPT_DIR/ShiftMlPcodeCorpusExporter.java" "$ML_SCRIPT_DIR/"

echo "== SHIFT portable high-P-code export =="
"$ANALYZE" \
  "$PROJECT_DIR" "$PROJECT_NAME" \
  -process "$PROGRAM_NAME" \
  -noanalysis \
  -readOnly \
  -scriptPath "$ML_SCRIPT_DIR" \
  -postScript ShiftMlPcodeCorpusExporter.java "${ARGS[@]}"

echo
echo "== portable representation audit =="
python3 "$ROOT/tools/ml/audit_shift_cross_project_pcode.py" \
  "$CORPUS" \
  --output "$SUMMARY"

if [[ -n "${NEVERGONE_REPO:-}" ]]; then
  MODEL_DIR=${NEVERGONE_MODEL_DIR:-$HOME/.local/share/nevergone-ml-v2/models/production-code-domain-v4}
  CLASSIFIER="$NEVERGONE_REPO/tools/ml/classify_nevergone_pcode.py"
  if [[ ! -f "$CLASSIFIER" ]]; then
    echo "error: Nevergone classifier not found: $CLASSIFIER" >&2
    exit 2
  fi
  if [[ ! -f "$MODEL_DIR/classifier.joblib" ]]; then
    echo "error: Nevergone P-code-only model not found: $MODEL_DIR/classifier.joblib" >&2
    exit 2
  fi

  echo
  echo "== Nevergone v4 -> SHIFT cross-project OOD probe =="
  python3 "$CLASSIFIER" \
    "$MODEL_DIR" \
    "$CORPUS" \
    --output "$CLASSIFIED"

  echo
  echo "== monotone foreign-project OOD guard =="
  python3 "$ROOT/tools/ml/guard_shift_foreign_pcode_predictions.py" \
    "$CLASSIFIED" \
    --min-similarity "$FOREIGN_MIN_SIMILARITY" \
    --min-contrast "$FOREIGN_MIN_CONTRAST" \
    --output "$GUARDED"

  python3 "$ROOT/tools/ml/audit_shift_cross_project_pcode.py" \
    "$CORPUS" \
    --classified "$GUARDED" \
    --output "$SUMMARY"
else
  echo
  echo "NEVERGONE_REPO not set; skipped model-transfer OOD probe."
fi

echo
echo "== cross-project probe outputs =="
echo "corpus: $CORPUS"
echo "audit: $SUMMARY"
if [[ -f "$CLASSIFIED" ]]; then
  echo "classified: $CLASSIFIED"
fi
if [[ -f "$GUARDED" ]]; then
  echo "foreign guarded: $GUARDED"
fi
