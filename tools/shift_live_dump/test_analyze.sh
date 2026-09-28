#!/usr/bin/env bash
set -euo pipefail
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/snapshot-000000/regions" "$tmp/snapshot-000001/regions"
python3 - "$tmp" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1])
for n,data in enumerate((b"A"*4096,b"B"*4096)):
    d=root/f"snapshot-{n:06d}"; (d/"regions"/"anon.bin").write_bytes(data)
    m={"format":"SHIFT-LIVE-MEMORY-SNAPSHOT/1","pid":1,"mode":"writable",
       "page_size":4096,"backend":"test","maps_count":1,"selected_count":1,
       "bytes_requested":len(data),"bytes_read":len(data),"bytes_failed":0,
       "regions":[{"start":4096,"end":8192,"size":4096,"perms":"rw-p",
                   "path":"","file":"regions/anon.bin"}]}
    (d/"manifest.json").write_text(json.dumps(m))
PY
python3 "$(dirname "$0")/analyze.py" "$tmp" --out "$tmp/out" --block-size-kib 4 --top 20
grep -q '"analyzed_regions": 1' "$tmp/out/analysis.json"
grep -q ',4096,' "$tmp/out/block_candidates.csv"
echo "analyzer smoke test: PASS"
