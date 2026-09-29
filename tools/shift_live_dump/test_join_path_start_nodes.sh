#!/usr/bin/env bash
set -euo pipefail

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

python3 - "$self_dir/analyze_track_paths.py" <<'PY'
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("track_path_analyzer", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

path_links = [
    {
        "path_address": 0x8101010,
        "start_node": 0x33580000,
        "target_vtable_match": True,
        "array_count": 4,
        "node_sequence": 4,
        "node_sequence_complete": True,
        "stable_snapshots": 10,
    },
    {
        "path_address": 0x81040D0,
        "start_node": 0x33630000,
        "target_vtable_match": True,
        "array_count": 5,
        "node_sequence": 4,
        "node_sequence_complete": False,
        "stable_snapshots": 10,
    },
    {
        "path_address": 0x8107190,
        "start_node": 0,
        "target_vtable_match": False,
        "array_count": None,
        "node_sequence": 0,
        "node_sequence_complete": False,
        "stable_snapshots": 10,
    },
]

polyline_candidates = [
    {
        "address": 0x70001000,
        "array": 0x33580000,
        "nodes": 4,
        "array_node_sequence": 4,
        "array_node_sequence_complete": True,
        "stable_snapshots": 10,
    },
    {
        "address": 0x70002000,
        "array": 0x33630000,
        "nodes": 4,
        "array_node_sequence": 4,
        "array_node_sequence_complete": True,
        "stable_snapshots": 10,
    },
    {
        "address": 0x70003000,
        "array": 0x33630000,
        "nodes": 5,
        "array_node_sequence": 5,
        "array_node_sequence_complete": True,
        "stable_snapshots": 8,
    },
]

rows = module.join_path_start_nodes_to_polylines(path_links, polyline_candidates)
assert len(rows) == 3, rows

first = rows[0]
assert first["path_address"] == 0x8101010, first
assert first["start_node"] == first["polyline_array"] == 0x33580000, first
assert first["node_count_match"], first
assert first["node_sequence_match"], first
assert first["join_evidence"] == "pointer+count+sequence", first
assert first["candidate_count"] == 1, first

second = rows[1]
assert second["start_node"] == 0x33630000, second
assert second["candidate_count"] == 2, second
assert second["node_count_match"], second
assert second["node_sequence_match"], second
assert second["join_evidence"] == "pointer+count+sequence", second

third = rows[2]
assert third["candidate_count"] == 2, third
assert not third["node_count_match"], third
assert third["join_evidence"] == "pointer-only", third
print("Path.StartNode -> AIPolylinePath.array join test: PASS")
PY
