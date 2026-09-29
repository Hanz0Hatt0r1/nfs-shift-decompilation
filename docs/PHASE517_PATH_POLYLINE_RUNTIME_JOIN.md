# Phase 517 — Path.StartNode to AIPolylinePath array joins

Phase 517 closes the direct runtime object-graph join between the recovered Path object and the concrete AIPolylinePath node array.

## Join rule

For every validated `Path.StartNode`, the analyzer searches every currently scanned `AIPolylinePath` candidate whose `array` field is exactly the same runtime pointer. No spatial proximity or address ordering is used for the join.

Each join records:

- Path address and StartNode pointer;
- PolylinePath owner and its array pointer;
- Path and Polyline node counts plus equality;
- validated node sequence lengths and completion flags;
- stable snapshot counts;
- candidate count for ambiguous shared arrays;
- descriptive evidence class: `pointer+count+sequence`, `pointer+count`, or `pointer-only`.

Candidate ownership is evaluated before `--top` truncation so a lower-ranked PolylinePath candidate cannot silently disappear from an exact pointer join.

## Output

`path_polyline_links.csv` is emitted beside `path_start_node_links.csv` and `aipolylinepath_nodes.csv`. `track_path_analysis.json` contains `path_polyline_link_count`.

## Interpretation

The join proves runtime field-level connectivity only. It does not assign gameplay semantics to the Path or PolylinePath object. Multiple owners remain visible instead of choosing one heuristically.

## Verification

`tools/shift_live_dump/test_join_path_start_nodes.sh` covers:

- exact pointer + count + sequence matches;
- shared StartNode pointers with multiple PolylinePath candidates;
- count mismatches preserved as `pointer-only` evidence.