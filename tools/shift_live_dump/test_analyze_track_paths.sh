#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/snapshot-000000/regions" "$tmp/snapshot-000001/regions"
python3 - "$tmp" <<'PY'
import json
import pathlib
import struct
import sys

root = pathlib.Path(sys.argv[1])
base = 0x00200000
size = 0x1000
blob = bytearray(size)

# Synthetic Path object using the offsets recovered from SHIFT.exe.c.
poff = 0x100
struct.pack_into("<III", blob, poff, 0x00401000, 0, 1)
struct.pack_into("<fff", blob, poff + 0x10, 1.0, 0.0, 0.25)
struct.pack_into("<f", blob, poff + 0x1C, 12.5)
struct.pack_into("<I", blob, poff + 0x20, 0x00500000)
blob[poff + 0x24:poff + 0x28] = bytes((0, 0, 0, 1))

# Synthetic AISegmentPath using the confirmed FUN_006d0fe0 vtable.
soff = 0x220
struct.pack_into("<III", blob, soff, 0x00AFCA70, 0, 1)
struct.pack_into("<IIIf", blob, soff + 0x10, 8, 1, 0x00500800, 120.0)
struct.pack_into("<IIff", blob, soff + 0x20, 0, 1, 15.0, 20.0)
struct.pack_into("<If", blob, soff + 0x30, 2, 1.0)

for n in range(2):
    snap = root / f"snapshot-{n:06d}"
    (snap / "regions" / "anon.bin").write_bytes(blob)
    manifest = {
        "format": "SHIFT-LIVE-MEMORY-SNAPSHOT/1",
        "pid": 1,
        "mode": "writable",
        "page_size": 4096,
        "backend": "test",
        "maps_count": 3,
        "selected_count": 1,
        "bytes_requested": size,
        "bytes_read": size,
        "bytes_failed": 0,
        "regions": [{
            "start": base,
            "end": base + size,
            "size": size,
            "perms": "rwxp",
            "path": "",
            "file": "regions/anon.bin",
        }],
    }
    (snap / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    (snap / "maps.txt").write_text(
        "00400000-00b81000 r-xp 0 00:00 0 /game/SHIFT.exe\n"
        "00500000-00501000 rwxp 0 00:00 0\n"
        "00500800-00501800 rwxp 0 00:00 0\n",
        encoding="utf-8",
    )
PY

python3 "$self_dir/analyze_track_paths.py" "$tmp" --out "$tmp/out" --top 20 --target-top 8 >/tmp/track_path_test.out
cat /tmp/track_path_test.out

python3 "$self_dir/analyze_track_paths.py" "$tmp" --out "$tmp/out-filtered" --top 20 --target-top 8 \
  --exclude-source-range 0x00200120:0x4 >/tmp/track_path_filter_test.out
cat /tmp/track_path_filter_test.out

python3 - "$tmp/out/track_path_analysis.json" "$tmp/out-filtered/track_path_analysis.json" <<'PY'
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
filtered = json.loads(open(sys.argv[2], encoding="utf-8").read())
assert result["candidate_counts"]["Path"] >= 1, result["candidate_counts"]
assert result["candidate_counts"]["AISegmentPath"] >= 1, result["candidate_counts"]
assert result["stable_external_pointer_count"] >= 2, result["stable_external_pointer_count"]
assert result["pointer_target_clusters"], "expected pointer clusters"
assert result["next_capture_windows"], "expected capture windows"
assert result["path_root_targets"], "expected Path StartNode targets"
assert result["path_root_targets"][0]["target"] == 0x00500000
assert result["path_root_windows"][0]["start"] == 0x004e0000
assert result["path_root_windows"][0]["size"] == 0x00040000
assert filtered["stable_external_pointer_count"] == 1, filtered["stable_external_pointer_count"]
assert filtered["excluded_source_ranges"] == [{"start": 0x00200120, "end": 0x00200124}], filtered["excluded_source_ranges"]
print("track path analyzer test: PASS")
PY

python3 "$self_dir/analyze_track_paths.py" "$tmp" --out "$tmp/out-skip-pointers" --top 20 --target-top 8   --skip-pointer-analysis >/tmp/track_path_skip_test.out
cat /tmp/track_path_skip_test.out

python3 - "$tmp/out-skip-pointers/track_path_analysis.json" <<'PY'
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert result["stable_external_pointer_count"] == 0
assert result["pointer_target_clusters"] == []
assert result["path_root_targets"], "Path roots must still be analyzed when pointer analysis is skipped"
assert result["path_root_targets"][0]["target"] == 0x00500000
print("track path skip-pointer test: PASS")
PY
