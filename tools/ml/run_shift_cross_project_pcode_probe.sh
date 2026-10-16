#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  GHIDRA_HOME=/opt/ghidra \
  ./tools/ml/run_shift_cross_project_pcode_probe.sh \
    <project-dir> <project-name> <program-name> <output-dir>

Optional environment:
  SHIFT_ML_MAX_FUNCTIONS        Number of internal functions to export (default 1000)
  SHIFT_ML_NAME_CONTAINS       Optional qualified-name substring filter
  REVENGINSTR_REPO             Path to revenginstr; defaults to ../revenginstr when present
  REVENGINSTR_MODEL_DIR        Validated REVENGINSTR.SelectiveClassifier/1 model directory
  NEVERGONE_REPO               Optional path to nevergone-recomp for its v4 model
  NEVERGONE_MODEL_DIR          Override Nevergone v4 model directory
  SHIFT_FOREIGN_MIN_SIMILARITY Foreign-project family-similarity floor (default 0.70)
  SHIFT_FOREIGN_MIN_CONTRAST   Foreign-project contrast-margin floor (default 0.05)

The Ghidra project must already contain an analyzed SHIFT.exe. The runner uses
-noanalysis/-readOnly and never changes semantic/provenance gates.

revenginstr owns the generic P-code exporter/audit/OOD guard and is required.
A generic classifier is used only when REVENGINSTR_MODEL_DIR is explicitly set;
there is intentionally no unvalidated automatic model switch. The historical
Nevergone v4 transfer model remains available when NEVERGONE_REPO is provided.
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
DEFAULT_REVENGINSTR=$(cd -- "$ROOT/.." && pwd)/revenginstr
REVENGINSTR_REPO=${REVENGINSTR_REPO:-}
if [[ -z "$REVENGINSTR_REPO" && -f "$DEFAULT_REVENGINSTR/pyproject.toml" ]]; then
  REVENGINSTR_REPO="$DEFAULT_REVENGINSTR"
fi
[[ -n "$REVENGINSTR_REPO" ]] || {
  echo "error: revenginstr is required; set REVENGINSTR_REPO or clone it next to this repository" >&2
  exit 2
}
[[ -f "$REVENGINSTR_REPO/scripts/run_ghidra_pcode_export.sh" ]] || {
  echo "error: revenginstr exporter not found in $REVENGINSTR_REPO" >&2
  exit 2
}
[[ -f "$REVENGINSTR_REPO/src/revenginstr/pcode/audit.py" ]] || {
  echo "error: revenginstr P-code audit not found in $REVENGINSTR_REPO" >&2
  exit 2
}
[[ -f "$REVENGINSTR_REPO/src/revenginstr/ood/foreign_guard.py" ]] || {
  echo "error: revenginstr foreign guard not found in $REVENGINSTR_REPO" >&2
  exit 2
}
mkdir -p "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
CORPUS="$OUT_DIR/shift-pcode.jsonl"
SUMMARY="$OUT_DIR/cross-project-audit.json"
CLASSIFIED=""
GUARDED=""

echo "== portable core: revenginstr =="
echo "revenginstr: $REVENGINSTR_REPO"
export PYTHONPATH="$REVENGINSTR_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
EXPORT_ARGS=(
  "$PROJECT_DIR" "$PROJECT_NAME" "$PROGRAM_NAME" "$CORPUS" "$MAX_FUNCTIONS"
)
if [[ -n "$NAME_FILTER" ]]; then
  EXPORT_ARGS+=("$NAME_FILTER")
fi
GHIDRA_HOME="$GHIDRA_HOME" \
  bash "$REVENGINSTR_REPO/scripts/run_ghidra_pcode_export.sh" "${EXPORT_ARGS[@]}"

echo
echo "== portable representation audit =="
python3 -m revenginstr.pcode.audit "$CORPUS" --output "$SUMMARY"

if [[ -n "${REVENGINSTR_MODEL_DIR:-}" ]]; then
  if [[ ! -f "$REVENGINSTR_MODEL_DIR/classifier.joblib" ]]; then
    echo "error: revenginstr model not found: $REVENGINSTR_MODEL_DIR/classifier.joblib" >&2
    exit 2
  fi
  if [[ ! -f "$REVENGINSTR_REPO/src/revenginstr/ml/selective.py" ]]; then
    echo "error: revenginstr selective classifier module not found" >&2
    exit 2
  fi

  CLASSIFIED="$OUT_DIR/revenginstr-selective-transfer.jsonl"
  GUARDED="$OUT_DIR/revenginstr-selective-transfer-foreign-guard.jsonl"
  echo
  echo "== revenginstr selective model -> SHIFT cross-project OOD probe =="
  python3 -c \
    'import sys; from revenginstr.ml.selective import infer_main; raise SystemExit(infer_main(sys.argv[1:]))' \
    "$REVENGINSTR_MODEL_DIR" \
    "$CORPUS" \
    --output "$CLASSIFIED"

  echo
  echo "== monotone foreign-project OOD guard =="
  python3 -m revenginstr.ood.foreign_guard \
    "$CLASSIFIED" \
    --similarity-floor "$FOREIGN_MIN_SIMILARITY" \
    --contrast-floor "$FOREIGN_MIN_CONTRAST" \
    --output "$GUARDED"

  python3 -m revenginstr.pcode.audit \
    "$CORPUS" \
    --classified "$GUARDED" \
    --output "$SUMMARY"
elif [[ -n "${NEVERGONE_REPO:-}" ]]; then
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

  CLASSIFIED="$OUT_DIR/nevergone-v4-transfer.jsonl"
  GUARDED="$OUT_DIR/nevergone-v4-transfer-foreign-guard.jsonl"
  echo
  echo "== Nevergone v4 -> SHIFT cross-project OOD probe =="
  python3 "$CLASSIFIER" "$MODEL_DIR" "$CORPUS" --output "$CLASSIFIED"

  echo
  echo "== monotone foreign-project OOD guard =="
  python3 -m revenginstr.ood.foreign_guard \
    "$CLASSIFIED" \
    --similarity-floor "$FOREIGN_MIN_SIMILARITY" \
    --contrast-floor "$FOREIGN_MIN_CONTRAST" \
    --output "$GUARDED"

  python3 -m revenginstr.pcode.audit \
    "$CORPUS" \
    --classified "$GUARDED" \
    --output "$SUMMARY"
else
  echo
  echo "REVENGINSTR_MODEL_DIR and NEVERGONE_REPO are unset; skipped model-transfer OOD probe."
fi

echo
echo "== cross-project probe outputs =="
echo "corpus: $CORPUS"
echo "audit: $SUMMARY"
if [[ -n "$CLASSIFIED" && -f "$CLASSIFIED" ]]; then
  echo "classified: $CLASSIFIED"
fi
if [[ -n "$GUARDED" && -f "$GUARDED" ]]; then
  echo "foreign guarded: $GUARDED"
fi
