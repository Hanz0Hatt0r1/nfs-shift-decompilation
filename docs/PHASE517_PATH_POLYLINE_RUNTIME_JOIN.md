# Phase 517 — Path.StartNode to AIPolylinePath array joins

Phase 517 closes a direct runtime object-graph join that was previously analyzed in two independent passes.

## Join

For every validated `Path.StartNode`, the analyzer now looks for an `AIPolylinePath` whose `array` field is the exact same runtime pointer. The join is emitted only for the concrete `AIPolyPathNode` array target already validated by the existing path pass.

Each row records the path address, shared node-array address, PolylinePath owner, node-count equality, node-sequence equality, stable snapshot counts, and a compact `join_evidence` classification:

- `pointer+count+sequence`
- `pointer+count`
- `pointer-only`

The classification is descriptive; it does not assign gameplay semantics to the path.

## Output

`path_polyline_links.csv` is emitted beside the existing `path_start_node_links.csv` and `aipolylinepath_nodes.csv`. `track_path_analysis.json` now exposes `path_polyline_link_count`.

## Evidence use

An exact pointer join connects two independently identified runtime structures through the recovered object fields. Matching node counts and complete node sequences provide additional internal consistency. Mismatches are retained rather than discarded so the capture can be investigated without silently selecting one interpretation.
