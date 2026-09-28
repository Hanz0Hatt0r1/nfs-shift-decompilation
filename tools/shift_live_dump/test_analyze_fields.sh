#!/usr/bin/env bash
set -euo pipefail

ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT

python3 - "$ROOT" <<'PY'
import json
import struct
import sys
from pathlib import Path

root = Path(sys.argv[1])
start = 0x100000
size = 4096
for n in range(4):
    snap = root / f"snapshot-{n:06d}"
    region_dir = snap / "regions"
    region_dir.mkdir(parents=True)
    data = bytearray(size)
    struct.pack_into("<f", data, 0x40, 10.0 + n * 0.5)
    struct.pack_into("<i", data, 0x44, 100 + n * 10)
    struct.pack_into("<Q", data, 0x48, start + 0x100 + n * 8)
    if n:
        data[0x200 + n] = n
    (region_dir / "100000.bin").write_bytes(data)
    manifest = {
        "format": "SHIFT-LIVE-MEMORY-SNAPSHOT/1",
        "pid": 1,
        "regions": [{
            "start": start,
            "end": start + size,
            "size": size,
            "perms": "rwxp",
            "path": "",
            "file": "regions/100000.bin",
        }],
    }
    (snap / "manifest.json").write_text(json.dumps(manifest) + "\n")
PY

OUT="$ROOT/result"
python3 "$(dirname "$0")/analyze_fields.py" "$ROOT"   --out "$OUT" --scope anonymous --min-transitions 1 --top 100

test -s "$OUT/field_candidates.csv"
test -s "$OUT/structure_candidates.csv"
test -s "$OUT/field_analysis.json"
test -s "$OUT/region_scope.csv"

python3 - "$OUT" <<'PY'
import csv
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
rows = list(csv.DictReader((out / "field_candidates.csv").open()))
assert any(r["type"] == "f32" and int(r["address"]) == 0x100040 for r in rows)
assert any(r["type"] == "i32" and int(r["address"]) == 0x100044 for r in rows)
report = json.loads((out / "field_analysis.json").read_text())
assert report["snapshot_count"] == 4
assert report["analyzed_blocks"] == 1
print("field analyzer smoke test: PASS")
PY
