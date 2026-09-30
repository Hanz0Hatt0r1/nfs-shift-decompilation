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
ioff = size - 0x124
struct.pack_into("<I", blob, ioff, 0x00401000)
struct.pack_into("<IIfff f III", blob, ioff + 0xD4, 1, 0x00610000, 1.0, 2.0, 3.0, 10.0, 1, 1, 0)
struct.pack_into("<fff", blob, ioff + 0x30, 11.0, 12.0, 13.0)
struct.pack_into("<fffff", blob, ioff + 0x100, 20.0, 0.5, 2.0, 3.0, 25.0)
struct.pack_into("<IIII", blob, ioff + 0x114, 2, 7, 3, 1)

# Synthetic AISegmentPath using the fields explicitly reflected by
# FUN_006d0690.
soff = 0x220
struct.pack_into("<III", blob, soff, 0x00AFCA70, 0, 1)
struct.pack_into("<IIIf", blob, soff + 0x10, 8, 1, 0x00610800, 120.0)
struct.pack_into("<I", blob, soff + 0x20, 0)
struct.pack_into("<I", blob, soff + 0x24, 1)
struct.pack_into("<f", blob, soff + 0x28, 15.0)
struct.pack_into("<f", blob, soff + 0x2c, 20.0)
struct.pack_into("<I", blob, soff + 0x30, 2)
struct.pack_into("<f", blob, soff + 0x34, 1.0)

# Synthetic AIPolylinePath using the concrete vtable recovered from
# FUN_006cc390. Its array points at a count-prefixed AIPolyPathNode array.
poff = 0x300
poly_array_local = 0x2000
poly_array_addr = base + poly_array_local
struct.pack_into("<III", blob, poff, 0x00AFC678, 0, 1)
struct.pack_into("<IIffIff", blob, poff + 0x10, 4, poly_array_addr, 160.0, 10.0, 1, 2.5, 12.0)
struct.pack_into("<I", blob, poly_array_local - 4, 4)

false_poly_off = 0x380
struct.pack_into("<III", blob, false_poly_off, 0x00AECCF8, 0, 1)
struct.pack_into("<IIffIff", blob, false_poly_off + 0x10, 8, 0x00610800, 160.0, 10.0, 1, 2.5, 12.0)

# AIPolyPathNode array. The node's 2D x/y corresponds to AIW x/z.
node_base = poly_array_local
for index, x in enumerate((1.0, 5.0, 9.0, 13.0)):
    noff = node_base + index * 0x24
    struct.pack_into("<III", blob, noff, 0x00AFBFA8, 0, 1)
    struct.pack_into("<fffff", blob, noff + 0x10, x, 3.0, 1.0, 0.0, float(index * 4))

# Same shape with a generic executable vtable must not count.
false_node_off = node_base + 4 * 0x24
struct.pack_into("<III", blob, false_node_off, 0x00AECCF8, 0, 1)
struct.pack_into("<fffff", blob, false_node_off + 0x10, 17.0, 3.0, 1.0, 0.0, 16.0)

# Keep the original generic float3 correlation fixture too.
# The earlier copy of waypoint 0 is valid, but does not begin the chain.
struct.pack_into("<fff", blob, 0x400, 101.03, 2.0, 3.0)
for index, pos in enumerate(((101.0, 2.0, 3.0), (105.0, 2.0, 3.0), (109.0, 2.0, 3.0), (113.0, 2.0, 3.0))):
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
        "00200000-00601000 rwxp 0 00:00 0\n"
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

# Direct Path.StartNode -> AIPolyPathNode[] resolver regression.
python3 - "$self_dir/analyze_track_paths.py" "$tmp" <<'PY2'
import sys
from pathlib import Path
script = Path(sys.argv[1])
root = Path(sys.argv[2])
ns = {"__name__": "track_path_test"}
exec(compile(script.read_text(encoding="utf-8"), str(script), "exec"), ns)
sns = ns["snapshots"](root)
mans = [ns["load_manifest"](s / "manifest.json") for s in sns]
idx = [{int(r["start"]): r for r in m.get("regions", [])} for m in mans]
mm = ns["maps"](sns[0] / "maps.txt")
rows = ns["resolve_path_start_nodes"](
    [{"address": 0x00200100, "start_node": 0x00202000}],
    sns, idx, mm,
)
assert len(rows) == 1, rows
r = rows[0]
assert r["target_vtable"] == 0x00AFBFA8, r
assert r["target_vtable_match"], r
assert r["link_type"] == "AIPolyPathNodeArray", r
assert r["array_count"] == 4, r
assert r["array_count_stable"], r
assert r["node_sequence"] == 4, r
assert r["node_sequence_complete"], r
print("track path StartNode link test: PASS")
PY2
python3 - "$tmp/out/track_path_analysis.json" "$tmp/out-filtered/track_path_analysis.json" <<'PY'
import csv
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
filtered = json.loads(open(sys.argv[2], encoding="utf-8").read())
assert result["candidate_counts"]["Path"] >= 1, result["candidate_counts"]
assert result["candidate_counts"]["AISegmentPath"] == 1, result["candidate_counts"]
with open(sys.argv[1].replace("track_path_analysis.json", "aisegmentpath.csv"), newline="", encoding="utf-8") as fh:
    segment_rows = list(csv.DictReader(fh))
assert len(segment_rows) == 1, segment_rows
row = segment_rows[0]
assert int(row["nodes"]) == 8, row
assert int(row["side"]) == 1, row
assert int(row["array"]) == 0x00610800, row
assert float(row["length"]) == 120.0, row
assert int(row["cyclic"]) == 0, row
assert int(row["narrow"]) == 1, row
assert float(row["spacing"]) == 15.0, row
assert float(row["path_dist"]) == 20.0, row
assert int(row["current"]) == 2, row
assert float(row["edge_step"]) == 1.0, row
assert result["candidate_counts"]["Incident.PathOwner"] == 1, result["candidate_counts"]
with open(sys.argv[1].replace("track_path_analysis.json", "incident_pathowner.csv"), newline="", encoding="utf-8") as fh:
    incident_rows = list(csv.DictReader(fh))
assert len(incident_rows) == 1, incident_rows
incident = incident_rows[0]
assert float(incident["incident_x"]) == 11.0, incident
assert float(incident["incident_y"]) == 12.0, incident
assert float(incident["incident_z"]) == 13.0, incident
assert float(incident["incident_path_dist"]) == 20.0, incident
assert float(incident["incident_timer"]) == 0.5, incident
assert float(incident["interest_level"]) == 2.0, incident
assert float(incident["min_spacing"]) == 3.0, incident
assert float(incident["track_dist"]) == 25.0, incident
assert int(incident["race_flag"]) == 2, incident
assert int(incident["area_index"]) == 7, incident
assert int(incident["n_marshals"]) == 3, incident
assert int(incident["n_flag_marshals"]) == 1, incident
assert result["candidate_counts"]["AIPolylinePath"] == 1, result["candidate_counts"]
assert result["candidate_counts"]["AIPolyPathNode"] == 4, result["candidate_counts"]
with open(sys.argv[1].replace("track_path_analysis.json", "aipolylinepath.csv"), newline="", encoding="utf-8") as fh:
    poly_rows = list(csv.DictReader(fh))
assert len(poly_rows) == 1, poly_rows
assert int(poly_rows[0]["vtable"]) == 0x00AFC678, poly_rows
assert int(poly_rows[0]["array"]) == 0x00202000, poly_rows
assert int(poly_rows[0]["array_count"]) == 4, poly_rows
assert poly_rows[0]["array_count_match"] == "True", poly_rows
assert int(poly_rows[0]["array_node_vtable"]) == 0x00AFBFA8, poly_rows
assert poly_rows[0]["array_node_vtable_match"] == "True", poly_rows
assert int(poly_rows[0]["array_node_sequence"]) == 4, poly_rows
with open(sys.argv[1].replace("track_path_analysis.json", "aipolylinepath_nodes.csv"), newline="", encoding="utf-8") as fh:
    node_rows = list(csv.DictReader(fh))
assert len(node_rows) == 4, node_rows
assert [float(row["x"]) for row in node_rows] == [1.0, 5.0, 9.0, 13.0], node_rows
assert [int(row["address"], 0) for row in node_rows] == [0x00202000, 0x00202024, 0x00202048, 0x0020206C], node_rows
assert [float(row["distance"]) for row in node_rows] == [0.0, 4.0, 8.0, 12.0], node_rows
assert result["stable_external_pointer_count"] >= 2, result["stable_external_pointer_count"]
assert result["pointer_target_clusters"], "expected pointer clusters"
assert result["next_capture_windows"], "expected capture windows"
assert result["path_root_targets"], "expected Path StartNode targets"
assert result["path_root_targets"][0]["target"] == 0x00610000
assert result["path_root_windows"][0]["start"] == 0x005f0000
assert result["path_root_windows"][0]["size"] == 0x00040000
assert filtered["stable_external_pointer_count"] == 2, filtered["stable_external_pointer_count"]
with open(sys.argv[2].replace("track_path_analysis.json", "stable_external_pointers.csv"), newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))
assert all(0x00200120 not in json.loads(row["sources"]) for row in rows), rows
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
\\0
wp_pos=(1.0300,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(30,10,-1,0)
\10
wp_pos=(5.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(0,20,-1,0)
\20
wp_pos=(9.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(10,30,-1,0)
\30
wp_pos=(13.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(20,0,-1,0)
AIW

python3 "$self_dir/analyze_track_paths.py" "$tmp" --out "$tmp/out-aiw"   --top 20 --target-top 8 --skip-pointer-analysis   --aiw "$tmp/test.aiw" --aiw-range 0x00202000:0x100 --runtime-root 0x00201ff0   --aiw-node-plane xz >/tmp/track_path_aiw_test.out
cat /tmp/track_path_aiw_test.out

python3 - "$tmp/out-aiw/track_path_analysis.json" <<'PY'
import csv
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert len(result["aiw_sources"]) == 1, result["aiw_sources"]
assert result["aiw_sources"][0]["number_waypoints"] == 4
assert result["aiw_match_count"] == 4, result["aiw_match_count"]
assert result["aiw_next_edge_count"] == 4, result["aiw_next_edge_count"]
assert result["aiw_runtime_edge_count"] == 4, result["aiw_runtime_edge_count"]
with open(sys.argv[1].replace("track_path_analysis.json", "aiw_runtime_edges.csv"), newline="", encoding="utf-8") as fh:
    runtime_edges = list(csv.DictReader(fh))
assert len(runtime_edges) == 4, runtime_edges
assert [int(e["runtime_delta"]) for e in runtime_edges] == [0x24, 0x24, 0x24, -0x6C], runtime_edges
with open(sys.argv[1].replace("track_path_analysis.json", "aiw_next_edges.csv"), newline="", encoding="utf-8") as fh:
    edges = list(csv.DictReader(fh))
assert [(int(e["from_waypoint"]), int(e["to_waypoint"])) for e in edges] == [
    (0, 10), (10, 20), (20, 30), (30, 0)
], edges
seq = result["aiw_runtime_sequences"]
assert seq, "expected AIW runtime sequence"
assert seq[0]["first_waypoint"] == 0, seq
assert seq[0]["last_waypoint"] == 30, seq
assert seq[0]["matched_waypoints"] == 4, seq
assert seq[0]["stride"] == 0x24, seq
assert seq[0]["runtime_root"] == 0x00201ff0, seq
assert seq[0]["position_offset"] == 0x10, seq
print("track path AIW correlation test: PASS")
PY

cat > "$tmp/generic.aiw" <<'AIW'
[Waypoint]
number_waypoints=4
\0
wp_pos=(101.0300,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(3,1,-1,0)
\1
wp_pos=(105.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(0,2,-1,0)
\2
wp_pos=(109.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(1,3,-1,0)
\3
wp_pos=(113.0000,2.0000,3.0000)
wp_branchID=(0)
WP_PTRS=(2,0,-1,0)
AIW

python3 "$self_dir/analyze_track_paths.py" "$tmp" --out "$tmp/out-generic-aiw" \
  --top 20 --target-top 8 --skip-pointer-analysis --aiw "$tmp/generic.aiw" \
  --aiw-range 0x00200400:0x180 --runtime-root 0x002004f0 >/tmp/track_path_generic_aiw_test.out

python3 - "$tmp/out-generic-aiw/track_path_analysis.json" <<'PY'
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert result["aiw_match_count"] == 5, result["aiw_match_count"]
seq = result["aiw_runtime_sequences"]
assert len(seq) == 1, seq
assert seq[0]["matched_waypoints"] == 4, seq
assert seq[0]["runtime_start"] == 0x00200500, seq
assert seq[0]["stride"] == 0x20, seq
print("track path generic AIW duplicate/bucket test: PASS")
PY

python3 - "$tmp/out-skip-pointers/track_path_analysis.json" <<'PY'
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert result["stable_external_pointer_count"] == 0
assert result["pointer_target_clusters"] == []
assert result["path_root_targets"], "Path roots must still be analyzed when pointer analysis is skipped"
assert result["path_root_targets"][0]["target"] == 0x00610000
assert result["candidate_counts"]["AIPolylinePath"] == 1, result["candidate_counts"]
print("track path skip-pointer test: PASS")
PY
