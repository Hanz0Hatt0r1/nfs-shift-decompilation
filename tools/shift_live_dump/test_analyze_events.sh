#!/usr/bin/env bash
set -euo pipefail
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/snapshot-000000/regions" "$tmp/snapshot-000001/regions" "$tmp/snapshot-000002/regions"
python3 - "$tmp" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1])
# 4 KiB block: small change on transition 0, large one-time spike on transition 1.
payloads = [b"A"*4096, b"B"*128 + b"A"*3968, b"C"*4096]
for n,data in enumerate(payloads):
    d=root/f"snapshot-{n:06d}"; (d/"regions").mkdir(exist_ok=True)
    (d/"regions"/"anon.bin").write_bytes(data)
    m={"format":"SHIFT-LIVE-MEMORY-SNAPSHOT/1","pid":1,"mode":"writable",
       "page_size":4096,"backend":"test","maps_count":1,"selected_count":1,
       "bytes_requested":4096,"bytes_read":4096,"bytes_failed":0,
       "regions":[{"start":4096,"end":8192,"size":4096,"perms":"rw-p",
                   "path":"","file":"regions/anon.bin"}]}
    (d/"manifest.json").write_text(json.dumps(m))
PY
python3 "$(dirname "$0")/analyze_events.py" "$tmp" --out "$tmp/out" --block-size-kib 4 --top 20
grep -q '^1,snapshot-000001,snapshot-000002,' "$tmp/out/transition_summary.csv"
grep -q ',1,4096,4224,2,' "$tmp/out/event_blocks.csv"
grep -q '"peak_transition": 1' "$tmp/out/event_analysis.json"
grep -q ',1,' "$tmp/out/event_clusters.csv"
echo "event analyzer smoke test: PASS"
