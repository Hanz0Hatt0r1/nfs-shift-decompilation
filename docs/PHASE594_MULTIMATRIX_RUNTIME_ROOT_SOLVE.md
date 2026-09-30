# Phase 594 — runtime-observed MultiMatrix root solve

Phase 551 proves the SceneGraph root-update transport and Phase 550 proves the
static MultiMatrix arithmetic:

`world[i] = local[i] * world[parent_low_byte]`.

The remaining MatrixNumber problem is not the arithmetic itself. It is knowing
the current root world matrix when the concrete per-instance SceneGraph update
history is unavailable.

Phase 594 adds a fail-closed inverse solve for that current root state.

## Contract

New contract:

`SHIFT.SGBMultiMatrixRootSolve/1`

implemented in:

`src/scene/sgb_multimatrix.py`.

Inputs:

- one source-backed LOD/HIERARCHY MATRIX table;
- the selected MatrixNumber/runtime slot index;
- one exact runtime-observed world matrix for that selected slot.

For a root-connected static mode-1 chain:

```text
world[selected]
  = local[selected] * local[parent] * ... * root
```

Phase 594 computes:

```text
root
  = inverse(local[selected] * local[parent] * ...) * observed_world
```

using the established D3D row-vector convention.

## Fail-closed rules

The solve is rejected when:

- the selected slot is out of range;
- the parent chain does not reach slot 0 through earlier slots;
- a parent index is invalid/out of range;
- the cumulative local transform is non-affine or singular;
- the observed matrix is invalid/non-finite;
- re-evaluating the existing MultiMatrix contract with the solved root does not
  reproduce the observed selected-slot world within the configured tolerance.

The solve never changes the established evaluator. Acceptance is defined by
running the solved root back through `SHIFT.SGBMultiMatrixEvaluation/1`.

## OBJECT handoff integration

`build_object_render_handoff()` gains an optional
`parent_selected_slot_world_matrix`.

Root-source priority is:

1. explicit supplied root world matrix;
2. proven SceneGraph update history;
3. runtime-observed selected-slot root solve;
4. unknown root history — existing blocked numeric path.

Therefore a real SceneGraph update history always takes precedence over an
inverse runtime solve.

The handoff records the complete
`runtime_selected_slot_root_solve` summary beside the ordinary root-transform
state.

## Important boundary

Phase 594 solves the **current root world matrix** required to explain one exact
runtime-observed selected slot.

It does **not** recover:

- how many SceneGraph updates occurred;
- their ordering or timing;
- the retail world-matrix shader register;
- streaming/LOD decisions;
- an OBJECT↔runtime-draw identity by itself.

Accordingly:

`scenegraph_update_history_recovered = false`.

This closes a mathematical state-reconstruction primitive, not the historical
event stream.

## CLI

The root importer exposes:

```bash
python shift_importer.py sgb-multimatrix-root-solve \
  owner-object.json \
  2 \
  observed-world.json \
  out/root-solve.json
```

`observed-world.json` may be either a raw 16-value matrix or an object
containing `selected_world_matrix`, `world_matrix`, or
`observed_world_matrix`.

A Phase 591 row can therefore provide the matrix value once an independent
OBJECT/runtime identity join exists.

## Next

The remaining integration step is to prove such an identity join for previously
blocked MatrixNumber OBJECTs. It must be independent of the later
RenderBinding/native binding index so it does not become circular evidence.

Authentic Silverstone capture content remains the external evidence gate.
