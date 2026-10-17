#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
if [[ $# -lt 4 ]]; then
  echo "usage: $0 <corpus.jsonl.gz> <manifest.json> <address-spaces.json> <output-dir> [lowerer options...]" >&2
  exit 2
fi

CORPUS=$1
MANIFEST=$2
ADDRESS_SPACES=$3
OUTPUT_DIR=$4
shift 4
REVENGINSTR_REPO=${REVENGINSTR_REPO:-"$ROOT/../revenginstr"}
PYTHON=${PYTHON:-python3}

if [[ ! -f "$REVENGINSTR_REPO/src/revenginstr/pcode/c_lowering_corpus.py" ]]; then
  echo "error: revenginstr P-code C corpus lowerer not found in $REVENGINSTR_REPO" >&2
  exit 1
fi

export PYTHONPATH="$REVENGINSTR_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m revenginstr.pcode.c_lowering_corpus \
  "$CORPUS" "$MANIFEST" "$ADDRESS_SPACES" "$OUTPUT_DIR" "$@"
