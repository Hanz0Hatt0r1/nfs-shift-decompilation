# Phase 183 — Draw-local D3D9 runtime state snapshots

## Goal

Eliminate false same-instance correlations caused by aggregating D3D9 state at
frame scope.

A frame can contain multiple mesh submissions and multiple state changes. The
strict runtime gate therefore needs the state that existed at the exact
`DrawIndexedPrimitive` boundary.

## New evidence

`SHIFT.D3D9RuntimeBindingEvidence/1` now exposes:

- `frames[*].draw_snapshots[*]`
- `trace.draw_snapshot_count`
- `same_instance_gate.requirements.indexed_draw_state_snapshot`

Each draw snapshot records the state active immediately before the captured
indexed draw:

- `draw_index`
- `draw`
- `vertex_declaration`
- `vertex_shader`
- `pixel_shader`
- `stream_sources`
- `index_binding`
- `constant_writes`
- `texture_bindings`

The existing frame-level aggregate remains available for compatibility and
diagnostics. It is not sufficient by itself for strict same-instance proof.

## Gate semantics

The strict `same_instance_gate` now evaluates descriptor matches against the
declaration captured in the draw snapshot itself.

A declaration/resource state observed later in the same frame cannot authenticate
an earlier draw.

The accepted chain is therefore:

```text
MEB resource identity
        |
        v
draw-local vertex declaration
        |
        v
MEB Type/Usage/Channel -> runtime declaration record
        |
        v
exact DrawIndexedPrimitive boundary
```

The gate remains fail-closed when any required link is absent.

## Regression coverage

The test suite covers two important cases:

1. A valid BMW declaration is present, a different declaration is bound for the
actual draw, and the original declaration is restored later in the frame.
The gate must remain blocked.

2. A valid same-instance draw is accepted and the resulting candidate records
its exact `draw_index` and draw parameters.

## Boundary

This phase does **not** claim that a retail runtime capture exists.

The remaining external proof target is still an authentic BMW M3 retail D3D9
capture containing the target draw, followed by exact correlation of:

- MEB resource identity;
- vertex declaration;
- indexed draw;
- VS/PS byte identity;
- constant register/value state;
- sampler/resource bindings.

Only that externally captured chain can unlock the first non-synthetic render.
