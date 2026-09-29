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
size = 0x401000
blob = bytearray(size)

# Synthetic Path object using the offsets recovered from SHIFT.exe.c.
poff = 0x100
struct.pack_into("<III", blob, poff, 0x00401000, 0, 1)
struct.pack_into("<fff", blob, poff + 0x10, 1.0, 0.0, 0.25)
struct.pack_into("<f", blob, poff + 0x1C, 12.5)
struct.pack_into("<I", blob, poff + 0x20, 0x00610000)
blob[poff + 0x24:poff + 0x28] = bytes((0, 0, 0, 1))

# A second Path deliberately straddles the 4 MiB streaming boundary.
# It also points at the same stable StartNode; --top must not hide it from
# the root-following pass.
boundary_poff = 0x400000 - 0x20
struct.pack_into("<III", blob, boundary_poff, 0x00401000, 0, 1)
struct.pack_into("<fff", blob, boundary_poff + 0x10, 0.0, 1.0, 0.5)
struct.pack_into("<f", blob, boundary_poff + 0x1C, 24.5)
struct.pack_into("<I", blob, boundary_poff + 0x20, 0x00610000)
blob[boundary_poff + 0x24:boundary_poff + 0x28] = bytes((1, 0, 0, 1))

# An Incident.PathOwner candidate sits exactly at the end of the region.
# This guards the scanner against using a too-short fixed tail limit.
ioff = size - 0xFC
struct.pack_into("<I", blob, ioff, 0x00401000)
struct.pack_into("<IIfff f III", blob, ioff + 0xD4, 1, 0x00610000, 1.0, 2.0, 3.0, 10.0, 1, 1, 0)

# Synthetic AISegmentPath using the confirmed FUN_006d0fe0 vtable.
soff = 0x220
struct.pack_into("<III", blob, soff, 0x00AFCA70, 0, 1)
struct.pack_into("<IIIf", blob, soff + 0x10, 8, 1, 0x00610800, 120.0)
struct.pack_into("<IIff", blob, soff + 0x20, 0, 1, 15.0, 20.0)
struct.pack_into("<If", blob, soff + 0x30, 2, 1.0)

# Runtime AI nodes with the same positions as a tiny synthetic AIW.
for index, pos in enumerate(((1.0, 2.0, 3.0), (5.0, 2.0, 3.0), (9.0, 2.0, 3.0), (13.0, 2.0, 3.0))):
    struct.pack_into("<fff", blob, 0x500 + index * 0x20, *pos)

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
        "00610000-00611000 rwxp 0 00:00 0\n"
        "00610800-00611800 rwxp 0 00:00 0\n",
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
assert result["candidate_counts"]["Incident.PathOwner"] >= 1, result["candidate_counts"]
assert result["stable_external_pointer_count"] >= 2, result["stable_external_pointer_count"]
assert result["pointer_target_clusters"], "expected pointer clusters"
assert result["next_capture_windows"], "expected capture windows"
assert result["path_root_targets"], "expected Path StartNode targets"
assert result["path_root_targets"][0]["target"] == 0x00610000
assert result["path_root_windows"][0]["start"] == 0x005f0000
assert result["path_root_windows"][0]["size"] == 0x00040000
assert filtered["stable_external_pointer_count"] == 2, filtered["stable_external_pointer_count"]
with open(sys.argv[2].replace("track_path_analysis.json", "stable_external_pointers.csv"), newline="", encoding="utf-8") as fh:\n    rows = list(csv.DictReader(fh))\nassert all(0x00200120 not in json.loads(row["sources"]) for row in rows), rows
assert filtered["excluded_source_ranges"] == [{"start": 0x00200120, "end": 0x00200124}], filtered["excluded_source_ranges"]
print("track path analyzer test: PASS")
PY

python3 "$self_dir/analyze_track_paths.py" "$tmp" --out "$tmp/out-skip-pointers" --top 20 --target-top 8 --skip-pointer-analysis >/tmp/track_path_skip_test.out
cat /tmp/track_path_skip_test.out


python3 "$self_dir/analyze_track_paths.py" "$tmp" --out "$tmp/out-top1" --top 1 --target-top 8 --skip-pointer-analysis >/tmp/track_path_top1_test.out
cat /tmp/track_path_top1_test.out

python3 - "$tmp/out-top1/track_path_analysis.json" <<'PY'
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert len(result["path_root_targets"]) == 1, result["path_root_targets"]
root = result["path_root_targets"][0]
assert root["target"] == 0x00610000
assert root["candidate_count"] >= 2, root
print("track path top-limit/root retention test: PASS")
PY

cat > "$tmp/test.aiw" <<'AIW'
[Waypoint]
number_waypoints=4
lap_length=120.000000
\0
wp_pos=(1.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(3,1,-1,0)
\1
wp_pos=(5.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(0,2,-1,0)
\2
wp_pos=(9.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(1,3,-1,0)
\3
wp_pos=(13.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(2,0,-1,0)
AIW

python3 "$self_dir/analyze_track_paths.py" "$tmp" --out "$tmp/out-aiw"   --top 20 --target-top 8 --skip-pointer-analysis   --aiw "$tmp/test.aiw" --aiw-range 0x00200500:0x80   >/tmp/track_path_aiw_test.out
cat /tmp/track_path_aiw_test.out

python3 - "$tmp/out-aiw/track_path_analysis.json" <<'PY'
import csv
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert len(result["aiw_sources"]) == 1, result["aiw_sources"]
assert result["aiw_sources"][0]["number_waypoints"] == 4
assert result["aiw_match_count"] == 4, result["aiw_match_count"]
seq = result["aiw_runtime_sequences"]
assert seq, "expected AIW runtime sequence"
assert seq[0]["first_waypoint"] == 0, seq
assert seq[0]["last_waypoint"] == 3, seq
assert seq[0]["matched_waypoints"] == 4, seq
assert seq[0]["stride"] == 0x20, seq
assert seq[0]["runtime_root"] == 0x002004f0, seq
assert seq[0]["position_offset"] == 0x10, seq
print("track path AIW correlation test: PASS")
PY

python3 - "$tmp/out-skip-pointers/track_path_analysis.json" <<'PY'
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert result["stable_external_pointer_count"] == 0
assert result["pointer_target_clusters"] == []
assert result["path_root_targets"], "Path roots must still be analyzed when pointer analysis is skipped"
assert result["path_root_targets"][0]["target"] == 0x00610000
print("track path skip-pointer test: PASS")
PY
