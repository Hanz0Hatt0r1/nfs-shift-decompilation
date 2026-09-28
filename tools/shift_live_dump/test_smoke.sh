#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
make >/dev/null
rm -rf smoke-a smoke-b smoke-diff
sleep 10 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT
./shift-live-dump snapshot "$PID" smoke-a --regions writable --backend auto >/dev/null
./shift-live-dump snapshot "$PID" smoke-b --regions writable --backend auto >/dev/null
./shift-live-dump diff smoke-a smoke-b smoke-diff >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
m=json.loads(Path("smoke-a/manifest.json").read_text())
assert m["format"] == "SHIFT-LIVE-MEMORY-SNAPSHOT/1"
assert m["selected_count"] > 0
assert m["bytes_requested"] == m["bytes_read"] + m["bytes_failed"]
PY
rm -rf smoke-a smoke-b smoke-diff
