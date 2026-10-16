#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

OUT_DIR="${1:-$ROOT/out/ml-cross-project}"
DEFAULT_REVENGINSTR="$(cd "$ROOT/.." && pwd)/revenginstr"
REVENGINSTR_REPO="${REVENGINSTR_REPO:-$DEFAULT_REVENGINSTR}"
SIMILARITY_FLOOR="${SHIFT_FOREIGN_MIN_SIMILARITY:-0.70}"
CONTRAST_FLOOR="${SHIFT_FOREIGN_MIN_CONTRAST:-0.05}"

SOURCE_CORPUS="${SHIFT_PARITY_CORPUS:-$OUT_DIR/shift-pcode.jsonl}"
BASE_CLASSIFIED="${SHIFT_PARITY_CLASSIFIED:-$OUT_DIR/nevergone-v4-transfer.jsonl}"
GENERIC_CORPUS="$OUT_DIR/shift-pcode.revenginstr.jsonl"
SHIFT_GUARDED="$OUT_DIR/nevergone-v4-transfer.shift-guard.jsonl"
GENERIC_GUARDED="$OUT_DIR/nevergone-v4-transfer.revenginstr-guard.jsonl"
SHIFT_AUDIT="$OUT_DIR/cross-project-audit.shift-compat.json"
GENERIC_AUDIT="$OUT_DIR/cross-project-audit.revenginstr.json"
PARITY="$OUT_DIR/revenginstr-pcode-parity.json"
GENERIC_GUARD_SUMMARY="$OUT_DIR/revenginstr-foreign-guard-summary.json"

for required in \
  "$SOURCE_CORPUS" \
  "$BASE_CLASSIFIED" \
  "$REVENGINSTR_REPO/pyproject.toml" \
  "$REVENGINSTR_REPO/src/revenginstr/pcode/audit.py" \
  "$REVENGINSTR_REPO/src/revenginstr/ood/foreign_guard.py"; do
  [[ -f "$required" ]] || { echo "missing: $required" >&2; exit 2; }
done

mkdir -p "$OUT_DIR"
export PYTHONPATH="$REVENGINSTR_REPO/src${PYTHONPATH:+:$PYTHONPATH}"

python3 - <<'PY'
from revenginstr.pcode.audit import FORMAT as AUDIT_FORMAT
from revenginstr.ood.foreign_guard import FORMAT as GUARD_FORMAT
assert AUDIT_FORMAT == "REVENGINSTR.PcodeAudit/1"
assert GUARD_FORMAT == "REVENGINSTR.ForeignGuard/1"
PY

echo "== Shift retained corpus -> revenginstr outer contract =="
python3 tools/ml/adapt_shift_pcode_to_revenginstr.py \
  "$SOURCE_CORPUS" "$GENERIC_CORPUS"

echo
echo "== historical Shift foreign guard =="
python3 tools/ml/guard_shift_foreign_pcode_predictions.py \
  "$BASE_CLASSIFIED" \
  --min-similarity "$SIMILARITY_FLOOR" \
  --min-contrast "$CONTRAST_FLOOR" \
  --output "$SHIFT_GUARDED"

echo
echo "== shared revenginstr foreign guard =="
python3 -m revenginstr.ood.foreign_guard \
  "$BASE_CLASSIFIED" \
  --similarity-floor "$SIMILARITY_FLOOR" \
  --contrast-floor "$CONTRAST_FLOOR" \
  --summary "$GENERIC_GUARD_SUMMARY" \
  --output "$GENERIC_GUARDED"

echo
echo "== historical Shift P-code audit =="
python3 tools/ml/audit_shift_cross_project_pcode.py \
  "$SOURCE_CORPUS" \
  --classified "$SHIFT_GUARDED" \
  --output "$SHIFT_AUDIT"

echo
echo "== shared revenginstr P-code audit =="
python3 -m revenginstr.pcode.audit \
  "$GENERIC_CORPUS" \
  --classified "$GENERIC_GUARDED" \
  --output "$GENERIC_AUDIT"

echo
echo "== strict Shift -> revenginstr P-code/OOD parity gate =="
python3 tools/ml/audit_shift_revenginstr_pcode_parity.py \
  "$SHIFT_GUARDED" \
  "$GENERIC_GUARDED" \
  "$SHIFT_AUDIT" \
  "$GENERIC_AUDIT" \
  --strict \
  --output "$PARITY"

echo
echo "== parity outputs =="
echo "generic corpus: $GENERIC_CORPUS"
echo "Shift guarded: $SHIFT_GUARDED"
echo "revenginstr guarded: $GENERIC_GUARDED"
echo "Shift audit: $SHIFT_AUDIT"
echo "revenginstr audit: $GENERIC_AUDIT"
echo "parity: $PARITY"
