#!/usr/bin/env bash
set -euo pipefail

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/analysis"

cat >"$tmp/analysis/track_path_analysis.json" <<'EOF'
{
  "aiw_runtime_edge_count": 4
}
EOF

cat >"$tmp/analysis/aiw_waypoints.csv" <<'EOF'
source,index,x,y,z,branch_id,bitfields,prev,next,alt,link_flags,sector,lap_distance,corner_speed,special_event,special_data
test.aiw:track.aiw,0,1,2,3,0,0,30,10,-1,0,0,0,0,0,0
test.aiw:track.aiw,10,5,2,3,0,0,0,20,-1,0,0,1,0,0,0
test.aiw:track.aiw,20,9,2,3,0,0,10,30,-1,0,0,2,0,0,0
test.aiw:track.aiw,30,13,2,3,0,0,20,0,-1,0,0,3,0,0,0
EOF

cat >"$tmp/analysis/aiw_next_edges.csv" <<'EOF'
aiw_source,from_waypoint,to_waypoint,branch_id,link_flags,from_lap_distance,to_lap_distance,lap_distance_delta
test.aiw:track.aiw,0,10,0,0,0,1,1
test.aiw:track.aiw,10,20,0,0,1,2,1
test.aiw:track.aiw,20,30,0,0,2,3,1
test.aiw:track.aiw,30,0,0,0,3,0,-3
EOF

cat >"$tmp/analysis/aiw_runtime_edges.csv" <<'EOF'
aiw_source,from_waypoint,to_waypoint,from_runtime_address,to_runtime_address,runtime_delta,branch_id,link_flags,position_match_error
test.aiw:track.aiw,0,10,0x201000,0x201024,36,0,0,0
test.aiw:track.aiw,10,20,0x201024,0x201048,36,0,0,0
test.aiw:track.aiw,20,30,0x201048,0x20106c,36,0,0,0
test.aiw:track.aiw,30,0,0x20106c,0x201000,-108,0,0,0
EOF

python3 "$self_dir/validate_aiw_runtime_graph.py" "$tmp/analysis" \
  --out "$tmp/analysis/validation.json" \
  --require-complete --require-unambiguous

python3 - "$tmp/analysis/validation.json" <<'PY'
import csv
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert result["format"] == "SHIFT-LIVE-MEMORY-AIW-RUNTIME-GRAPH/1", result
assert result["source_count"] == 1, result
assert result["runtime_edge_candidate_count"] == 4, result
assert result["runtime_edge_group_count"] == 4, result
assert result["ambiguous_edge_group_count"] == 0, result
source = result["sources"][0]
assert source["status"] == "complete-unambiguous", source
assert source["dominant_forward_stride"] == 36, source
assert source["dominant_forward_stride_count"] == 3, source
assert source["negative_runtime_edge_count"] == 1, source
assert source["runtime_edge_coverage"] == 1.0, source
assert source["unambiguous_edge_coverage"] == 1.0, source

with open(
    sys.argv[1].replace("validation.json", "aiw_runtime_edge_groups.csv"),
    newline="", encoding="utf-8"
) as fh:
    rows = list(csv.DictReader(fh))
assert len(rows) == 4, rows
assert [int(row["candidate_count"]) for row in rows] == [1, 1, 1, 1], rows
assert [int(row["min_error_runtime_delta"]) for row in rows] == [36, 36, 36, -108], rows
print("AIW runtime graph validation test: PASS")
PY

cat >"$tmp/analysis/aiw_runtime_edges.csv" <<'EOF'
aiw_source,from_waypoint,to_waypoint,from_runtime_address,to_runtime_address,runtime_delta,branch_id,link_flags,position_match_error
test.aiw:track.aiw,0,10,0x201000,0x201024,36,0,0,0
test.aiw:track.aiw,0,10,0x301000,0x301030,48,0,0,0.01
test.aiw:track.aiw,10,20,0x201024,0x201048,36,0,0,0
test.aiw:track.aiw,20,30,0x201048,0x20106c,36,0,0,0
test.aiw:track.aiw,30,0,0x20106c,0x201000,-108,0,0,0
EOF

python3 "$self_dir/validate_aiw_runtime_graph.py" "$tmp/analysis" \
  --out "$tmp/analysis/ambiguous.json"

python3 - "$tmp/analysis/ambiguous.json" <<'PY'
import json
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert result["ambiguous_edge_group_count"] == 1, result
source = result["sources"][0]
assert source["status"] == "complete-ambiguous", source
assert source["max_candidates_per_edge"] == 2, source
assert source["runtime_edge_group_count"] == 4, source
assert source["runtime_edge_coverage"] == 1.0, source
print("AIW runtime ambiguity test: PASS")
PY

set +e
python3 "$self_dir/validate_aiw_runtime_graph.py" "$tmp/analysis" \
  --out "$tmp/analysis/ambiguous-strict.json" \
  --require-unambiguous >/tmp/aiw_runtime_graph_strict.out 2>&1
status=$?
set -e
test "$status" -eq 2

echo "AIW runtime graph strict gate test: PASS"
