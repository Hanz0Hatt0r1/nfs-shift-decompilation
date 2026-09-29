#!/usr/bin/env bash
set -euo pipefail

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/analysis"

cat >"$tmp/analysis/aiw_runtime_edges.csv" <<'EOF'
aiw_source,from_waypoint,to_waypoint,from_runtime_address,to_runtime_address,runtime_delta,branch_id,link_flags,position_match_error
track.aiw,0,10,0x201010,0x201034,36,0,0,0.01
track.aiw,10,20,0x201034,0x201058,36,0,0,0.02
track.aiw,20,0,0x201058,0x201010,-72,0,0,0.03
EOF

cat >"$tmp/analysis/aiw_runtime_matches.csv" <<'EOF'
aiw_source,waypoint_index,branch_id,runtime_address,region_start,region_offset,distance,x,y,z
track.aiw,0,0,0x201010,0x200000,0x1010,0.01,1,2,3
track.aiw,10,0,0x201034,0x200000,0x1034,0.01,5,2,3
track.aiw,20,0,0x201058,0x200000,0x1058,0.01,9,2,3
EOF

cat >"$tmp/analysis/aipolylinepath_nodes.csv" <<'EOF'
path_address,array_address,index,address,vtable,x,y,dx,dy,distance
0x700100,0x201000,0,0x201010,0xAFBFA8,1,3,1,0,0
0x700100,0x201000,1,0x201034,0xAFBFA8,5,3,1,0,4
0x700100,0x201000,2,0x201058,0xAFBFA8,9,3,1,0,8
EOF

cat >"$tmp/analysis/path_polyline_links.csv" <<'EOF'
path_address,start_node,polyline_address,polyline_array,path_node_count,polyline_node_count,node_count_match,path_node_sequence,polyline_node_sequence,node_sequence_match,path_node_sequence_complete,polyline_node_sequence_complete,candidate_count,path_stable_snapshots,polyline_stable_snapshots,join_evidence
0x700100,0x201000,0x700100,0x201000,3,3,True,3,3,True,True,True,1,10,10,pointer+count+sequence
EOF

python3 "$self_dir/validate_track_path_instance_graph.py" "$tmp/analysis" \
  --require-node-owner --require-same-array --require-stride

python3 - "$tmp/analysis/track_path_instance_graph.json" <<'PY'
import csv
import json
import sys

result=json.loads(open(sys.argv[1],encoding="utf-8").read())
assert result["format"] == "SHIFT-LIVE-MEMORY-TRACK-PATH-INSTANCE-GRAPH/1", result
assert result["normalized_runtime_edge_count"] == 3, result
assert result["runtime_instance_edge_candidate_count"] == 3, result
assert result["runtime_edge_node_owner_coverage"] == 1.0, result
assert result["same_array_candidate_count"] == 3, result
assert result["runtime_stride_match_candidate_count"] == 3, result

with open(sys.argv[1].replace("track_path_instance_graph.json","track_path_instance_edges.csv"),newline="",encoding="utf-8") as fh:
    rows=list(csv.DictReader(fh))
assert [int(r["node_index_delta"]) for r in rows] == [1,1,-2], rows
assert [int(r["expected_runtime_delta"]) for r in rows] == [36,36,-72], rows
assert all(r["runtime_stride_match"] == "True" for r in rows), rows
assert all(r["same_array"] == "True" for r in rows), rows
print("track path instance graph test: PASS")
PY

cp "$tmp/analysis/track_path_instance_edges.csv" "$tmp/analysis/baseline_edges.csv"
python3 - "$tmp/analysis/track_path_instance_edges.csv" <<'PY'
from pathlib import Path
p=Path(__import__("sys").argv[1])
s=p.read_text()
s=s.replace(",0x201034,36,",",0x201040,48,")
p.write_text(s)
PY

set +e
python3 "$self_dir/validate_track_path_instance_graph.py" "$tmp/analysis" \
  --require-node-owner --require-same-array --require-stride >/tmp/track_path_instance_strict.out 2>&1
status=$?
set -e
test "$status" -eq 2
echo "track path instance strict stride gate test: PASS"
