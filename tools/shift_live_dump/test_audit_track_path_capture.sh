#!/usr/bin/env bash
set -euo pipefail

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/analysis"

cat >"$tmp/analysis/track_path_analysis.json" <<'EOF'
{
  "format": "SHIFT-LIVE-MEMORY-TRACK-PATH-ANALYSIS/1",
  "snapshots": 10,
  "common_regions": 832,
  "candidate_counts": {
    "Path": 2,
    "AIPolylinePath": 1
  }
}
EOF

cat >"$tmp/analysis/path.csv" <<'EOF'
address,start_node,vtable
0x81040d0,0x33630000,0x456
EOF

cat >"$tmp/analysis/aipolylinepath.csv" <<'EOF'
address,array,nodes,vtable
0x70001000,0x33630000,4,0xafc678
EOF

cat >"$tmp/analysis/path_root_targets.csv" <<'EOF'
target,candidate_count,candidate_addresses,mapping_start,mapping_end,mapping_perms
0x33630000,2,"[""0x81040d0"",""0x8107190""]",0x33400000,0x34000000,rwxp
EOF

cat >"$tmp/analysis/path_root_ranges.txt" <<'EOF'
0x33610000:0x40000  # targets=0x33630000
EOF

cat >"$tmp/analysis/aiw_waypoints.csv" <<'EOF'
source,index,x,y,z,next
track.aiw,0,1,0,3,1
track.aiw,1,5,0,3,0
EOF

cat >"$tmp/analysis/aiw_next_edges.csv" <<'EOF'
aiw_source,from_waypoint,to_waypoint
track.aiw,0,1
track.aiw,1,0
EOF

cat >"$tmp/analysis/aiw_runtime_matches.csv" <<'EOF'
aiw_source,waypoint_index,runtime_address,distance
track.aiw,0,0x33630000,0
track.aiw,1,0x33630024,0
EOF

cat >"$tmp/analysis/aiw_runtime_sequences.csv" <<'EOF'
aiw_source,first_waypoint,last_waypoint,matched_waypoints,runtime_start,runtime_end,stride,stride_count,coverage
track.aiw,0,1,2,0x33630000,0x33630024,36,1,1
EOF

cat >"$tmp/analysis/aipolylinepath_nodes.csv" <<'EOF'
path_address,array_address,index,address,vtable,x,y,dx,dy,distance
0x70001000,0x33630000,0,0x33630000,0xafbfa8,1,3,1,0,0
0x70001000,0x33630000,1,0x33630024,0xafbfa8,5,3,1,0,4
EOF

cat >"$tmp/analysis/aiw_runtime_edges.csv" <<'EOF'
aiw_source,from_waypoint,to_waypoint,from_runtime_address,to_runtime_address,runtime_delta,position_match_error
track.aiw,0,1,0x33630000,0x33630024,36,0
track.aiw,1,0,0x33630024,0x33630000,-36,0
EOF

cat >"$tmp/analysis/path_polyline_links.csv" <<'EOF'
path_address,start_node,polyline_address,polyline_array,path_node_count,polyline_node_count,node_count_match,path_node_sequence,polyline_node_sequence,node_sequence_match,join_evidence
0x81040d0,0x33630000,0x70001000,0x33630000,2,2,True,2,2,True,pointer+count+sequence
EOF

cat >"$tmp/analysis/track_path_instance_edges.csv" <<'EOF'
aiw_source,from_waypoint,to_waypoint,from_runtime_address,to_runtime_address
track.aiw,0,1,0x33630000,0x33630024
track.aiw,1,0,0x33630024,0x33630000
EOF

python3 "$self_dir/audit_track_path_capture.py" "$tmp/analysis" \
  --out "$tmp/analysis/handoff.json" \
  --full-capture full.capture \
  --aiw source.zip \
  --aiw-entry grandprix

python3 - "$tmp/analysis/handoff.json" <<'PY'
import json, sys
r=json.loads(open(sys.argv[1],encoding="utf-8").read())
assert r["format"]=="SHIFT-LIVE-MEMORY-TRACK-PATH-CAPTURE-HANDOFF/1",r
assert r["status"]=="ready",r
assert r["path_roots"]["high_value_targets"]==["0x33630000"],r
assert r["evidence"]["instance_graph_ready"] is True,r
assert "0x33630000" in r["recommended_commands"]["rerun_runtime_correlation"],r
print("track path capture handoff ready test: PASS")
PY

rm "$tmp/analysis/track_path_instance_edges.csv"
python3 "$self_dir/audit_track_path_capture.py" "$tmp/analysis" \
  --out "$tmp/analysis/blocked.json" \
  --strict >/tmp/track_path_handoff_strict.out 2>&1
status=$?
test "$status" -eq 2
python3 - "$tmp/analysis/blocked.json" <<'PY'
import json, sys
r=json.loads(open(sys.argv[1],encoding="utf-8").read())
assert r["status"]=="runtime-correlation-blocked",r
assert r["evidence"]["instance_graph_ready"] is False,r
assert any("track_path_instance_edges.csv" in x for x in r["blocking_reasons"]),r
print("track path capture handoff strict gate test: PASS")
PY
