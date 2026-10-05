#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${1:-${ROOT_DIR}/out/bmw_body0_runtime_probe}"
DURATION="${SHIFT_BMW_BODY0_CAPTURE_SECONDS:-20}"
SAMPLE_MS="${SHIFT_BMW_BODY0_SAMPLE_MS:-50}"

mkdir -p "${OUT_DIR}"

exec python3 "${ROOT_DIR}/tools/shift_live_dump/capture_bmw_body0.py" \
  --output "${OUT_DIR}" \
  --duration "${DURATION}" \
  --sample-ms "${SAMPLE_MS}" \
  "${@:2}"
