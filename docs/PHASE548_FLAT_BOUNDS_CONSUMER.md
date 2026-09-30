# Phase 548 — FLAT bounds consumer closure

Phase 546 deliberately kept FLAT leaf `+0x20..+0x34` as a corpus-verified
candidate. Phase 547 carried that candidate into the neutral
`SHIFT.SGBScenePlacement/1` contract as advisory-only data.

Phase 548 closes the missing source consumer.

## Retail call path

At the direct-record query call site, `FUN_006afb20` passes the FLAT leaf to
`FUN_006aef20`.

When the query object exposes its secondary spatial interface,
`FUN_006aef20` dispatches vtable `+0x2c` with:

```text
leaf  + 0x20
query + 0x20
```

The leaf argument is exactly 24 bytes / six floats before the runtime pointer
at `+0x38`.

This makes the block source-consumed spatial query data rather than dead or
purely statistical bytes.

## AABB layout

The four-variant Silverstone Era3 corpus supplies the structural validation:

- 21,580 / 21,580 leaves have ordered first-three <= last-three components;
- 21,580 / 21,580 source-backed sphere centers lie inside those bounds;
- 21,580 / 21,580 min/max midpoints match the sphere center within 1e-4;
- maximum observed midpoint error is `6.103515625e-05`.

The IR therefore exposes:

```text
FLAT leaf +0x20..+0x2b -> min_xyz
FLAT leaf +0x2c..+0x37 -> max_xyz
```

with evidence state `source-consumed-corpus-validated-aabb`.

The concrete class behind the query interface remains unnamed.

## Placement propagation

`SHIFT.SGBPlacementJoin/1` now carries the field as `spatial_bounds`.

`SHIFT.SGBScenePlacement/1` requires it for every FLAT/SUMM placement and
adds `spatial_bounds` to `proven_geometry`.

The previous `bounds_candidate/advisory-only` path is removed.

PART/NODE placement is unchanged: it remains partition-AABB precision until a
more precise source-backed object placement is proven.

## Boundary

Phase 548 does not change the Phase 547 render-admission gate:

- world transform is still not emitted;
- draw admission remains false;
- object/resource-to-render-node mapping is still required.

The next scene step is therefore the real transform/resource handoff rather
than additional FLAT byte interpretation.
