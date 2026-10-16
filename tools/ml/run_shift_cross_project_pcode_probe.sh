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
  NEVERGONE_REPO               Path to nevergone-recomp; enables model transfer probe
  NEVERGONE_MODEL_DIR          Override P-code-only model directory
  REVENGINSTR_REPO             Path to revenginstr; defaults to ../revenginstr when present
  SHIFT_FOREIGN_MIN_SIMILARITY Foreign-project family-similarity floor (default 0.70)
  SHIFT_FOREIGN_MIN_CONTRAST   Foreign-project contrast-margin floor (default 0.05)

The Ghidra project must already contain an analyzed SHIFT.exe. The runner uses
-noanalysis/-readOnly and never changes semantic/provenance gates.

When revenginstr is available it owns the generic P-code exporter/audit/OOD guard.
The historical Shift-local implementations remain a temporary compatibility fallback.
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
ANALYZE="$GHIDRA_HOME/support/analyzeHeadless"
SCRIPT_DIR="$ROOT/tools/ghidra"

[[ -x "$ANALYZE" ]] || { echo "error: analyzeHeadless not executable: $ANALYZE" >&2; exit 1; }
mkdir -p "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd)
CORPUS="$OUT_DIR/shift-pcode.jsonl"
CLASSIFIED="$OUT_DIR/nevergone-v4-transfer.jsonl"
GUARDED="$OUT_DIR/nevergone-v4-transfer-foreign-guard.jsonl"
SUMMARY="$OUT_DIR/cross-project-audit.json"

use_revenginstr=0
if [[ -n "$REVENGINSTR_REPO" \
   && -f "$REVENGINSTR_REPO/scripts/run_ghidra_pcode_export.sh" \
   && -f "$REVENGINSTR_REPO/src/revenginstr/pcode/audit.py" \
   && -f "$REVENGINSTR_REPO/src/revenginstr/ood/foreign_guard.py" ]]; then
  use_revenginstr=1
fi

if [[ "$use_revenginstr" == "1" ]]; then
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
else
  echo "== portable core: Shift compatibility fallback =="
  echo "warning: revenginstr not found; set REVENGINSTR_REPO or clone it next to this repository" >&2
  ARGS=("$CORPUS" "$MAX_FUNCTIONS")
  if [[ -n "$NAME_FILTER" ]]; then
    ARGS+=("$NAME_FILTER")
  fi
  ML_SCRIPT_DIR=$(mktemp -d)
  trap 'rm -rf -- "$ML_SCRIPT_DIR"' EXIT
  cp "$SCRIPT_DIR/ShiftMlPcodeCorpusExporter.java" "$ML_SCRIPT_DIR/"
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
    "$CORPUS" --output "$SUMMARY"
fi

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
  python3 "$CLASSIFIER" "$MODEL_DIR" "$CORPUS" --output "$CLASSIFIED"

  echo
  echo "== monotone foreign-project OOD guard =="
  if [[ "$use_revenginstr" == "1" ]]; then
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
    python3 "$ROOT/tools/ml/guard_shift_foreign_pcode_predictions.py" \
      "$CLASSIFIED" \
      --min-similarity "$FOREIGN_MIN_SIMILARITY" \
      --min-contrast "$FOREIGN_MIN_CONTRAST" \
      --output "$GUARDED"

    python3 "$ROOT/tools/ml/audit_shift_cross_project_pcode.py" \
      "$CORPUS" \
      --classified "$GUARDED" \
      --output "$SUMMARY"
  fi
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
