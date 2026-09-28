#!/usr/bin/env bash
set -euo pipefail
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src/snapshot-000000/regions" "$tmp/src/snapshot-000001/regions"
python3 - "$tmp" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
for n, fill in enumerate((b"A", b"B")):
    snap = root / "src" / f"snapshot-{n:06d}"
    data = fill * 0x10000
    (snap / "regions" / "anon.bin").write_bytes(data)
    manifest = {
        "format": "SHIFT-LIVE-MEMORY-SNAPSHOT/1",
        "pid": 1, "mode": "writable", "page_size": 4096,
        "backend": "test", "maps_count": 1, "selected_count": 1,
        "bytes_requested": len(data), "bytes_read": len(data), "bytes_failed": 0,
        "regions": [{
            "start": 0x100000, "end": 0x110000, "size": len(data),
            "perms": "rw-p", "path": "", "file": "regions/anon.bin"
        }]
    }
    (snap / "manifest.json").write_text(json.dumps(manifest))
PY
python3 "$(dirname "$0")/extract_ranges.py"   "$tmp/src" "$tmp/out" --preset none --range 0x102000:0x1000
python3 - "$tmp" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
for n, expected in enumerate((b"A", b"B")):
    snap = root / "out" / f"snapshot-{n:06d}"
    m = json.loads((snap / "manifest.json").read_text())
    assert m["selected_count"] == 1
    r = m["regions"][0]
    assert r["start"] == 0x102000 and r["size"] == 0x1000
    assert (snap / r["file"]).read_bytes() == expected * 0x1000
assert json.loads((root / "out" / "extract_ranges.json").read_text())["total_bytes"] == 0x2000
PY
echo "range extractor smoke test: PASS"
