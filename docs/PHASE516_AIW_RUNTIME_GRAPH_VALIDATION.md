# Phase 516 — AIW runtime graph validation

Phase 516 adds a deterministic validation layer above the concrete
`aiw_runtime_edges.csv` output from the track-path analyzer.

## Goal

The analyzer already correlates static AIW `WP_PTRS.next` links with concrete
runtime waypoint addresses. Phase 516 turns that raw edge list into a compact,
machine-readable graph report without selecting an unproven semantic mapping.

## New tool

```bash
python3 tools/shift_live_dump/validate_aiw_runtime_graph.py \\
  capture/track_path_analysis \\
  --require-complete
```

The validator reads:

- `aiw_waypoints.csv`
- `aiw_next_edges.csv`
- `aiw_runtime_edges.csv`
- optionally `track_path_analysis.json` for count parity

and writes:

- `aiw_runtime_graph_validation.json`
- `aiw_runtime_edge_groups.csv`

## Validation dimensions

For each AIW source the report records:

- normalized explicit `WP_PTRS.next` edge count;
- runtime candidate and unique edge-group counts;
- missing runtime edge groups;
- ambiguous edge groups where one explicit AIW edge has multiple runtime pairs;
- dominant positive runtime stride and its coverage;
- negative runtime deltas, which expose array-wrap candidates when present;
- runtime edge and unambiguous edge coverage;
- aggregate position-match error.

The tool deliberately does not collapse ambiguous candidates into a single
runtime graph. Multiple candidates remain evidence requiring additional capture
or a stronger same-instance constraint.

## Gate modes

`--require-complete` returns exit code `2` when an explicit normalized AIW edge
has no runtime candidate.

`--require-unambiguous` returns exit code `2` when any explicit edge has more
than one runtime-address candidate.

These gates are intended for capture review rather than as proof that the
runtime object has a particular gameplay semantic.

## Evidence state

The output is a validator/reporting layer over existing runtime correlations.
It does not upgrade static or runtime evidence by itself. A complete,
unambiguous graph is still only a concrete memory-to-AIW correlation until the
runtime object identity and consumer path are joined.
