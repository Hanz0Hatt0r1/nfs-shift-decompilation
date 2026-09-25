# Phase 185 — Versioned draw-state snapshot contract

## Goal

Make the exact `DrawIndexedPrimitive` state a standalone, versioned contract and
prevent malformed draw snapshots from reaching same-instance proof.

## Snapshot format

`SHIFT.D3D9DrawStateSnapshot/1` contains the draw identity plus the state needed
by downstream runtime consumers:

- `frame` and `draw_index`;
- draw parameters;
- declaration, VS and PS bindings;
- stream/index bindings;
- full binding history for forensic analysis;
- normalized `active_stream_sources`;
- normalized `active_texture_bindings`;
- `constant_state` with the latest observed vector registers;
- draw-local shader permutation identity.

`d3d9_draw_snapshot_schema.py` validates this structure. Generated snapshots are
validated during runtime report construction, and invalid snapshots cannot become
same-instance candidates.

## Active-state normalization

History is retained for diagnosis, but renderer-facing consumers use the normalized
active bindings. A later binding replaces the earlier state for that stream or
texture stage at the draw boundary.

## Downstream effect

Shader selection, shader join, vertex-input parity, runtime render contract, draw
range correlation and the BMW golden gate all operate on the same exact draw
identity. Frame-level aggregates remain only as an explicit compatibility path for
legacy reports without snapshots.

## Evidence boundary

This phase still does not claim an authentic retail capture. The remaining external
requirement is one real BMW M3 D3D9 capture whose single draw instance proves the
MEB identity, declaration, draw range, VS/PS identity, constants and sampler
resources together.

## Regression coverage

The tests cover active stream/texture overwrite semantics, malformed snapshots,
cross-draw shader/range splits, exact draw selection and mixed legacy/snapshot
reports.
