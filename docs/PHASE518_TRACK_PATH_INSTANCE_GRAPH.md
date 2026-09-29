# Phase 518 — AIW to track-path runtime instance graph

Phase 518 adds a fail-closed cross-check across the existing AIW/runtime edge correlation, validated `AIPolyPathNode` arrays, and the exact `Path.StartNode` to `AIPolylinePath.array` join from Phase 517.

## Join chain

`AIW waypoint -> aiw_runtime_matches.csv -> AIPolyPathNode.address -> AIPolylinePath.array -> Path.StartNode`

The tool emits every candidate endpoint-owner combination. It does not collapse multiple owners or select a gameplay interpretation.

For each candidate edge it records the path owner on both endpoints, array owner on both endpoints, node indices, runtime address delta, the expected delta from the recovered `0x24` node stride, same-array/path checks, and the number of exact `Path/AIPolylinePath` joins for the source array.

## Gate modes

`--require-node-owner` requires every normalized runtime edge to have at least one validated node-owner candidate.

`--require-same-array` requires every emitted candidate to keep both endpoints in the same validated node array.

`--require-stride` requires `runtime_delta == node_index_delta * 0x24` for every emitted candidate.

`--require-path-polyline-join` requires every normalized runtime edge candidate to be backed by an exact `Path.StartNode == AIPolylinePath.array` join for its source array and path owner.

These are evidence gates only. A stride-consistent candidate is a structural memory-layout consistency check, not a semantic claim about how the game drives the path.

## Outputs

`track_path_instance_graph.json` contains aggregate coverage and consistency counts. `track_path_instance_edges.csv` contains the full candidate-level join, including ambiguous endpoint ownership.
