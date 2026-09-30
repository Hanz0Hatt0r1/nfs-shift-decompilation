# Phase 549 — initial SGB MultiMatrix world evaluation

Phase 549 closes the numeric **initial** world-transform path for binary SGB
OBJECTs whose `MatrixNumber` selects a MultiMatrix slot.

It does not claim the later dynamic MultiMatrix operation modes.

## Exact matrix product

The earlier decompiler prototype hides one input to `FUN_00401610`.
PE disassembly around the `FUN_006b1620` case-1 call resolves it:

```text
EDX       = local[source_slot]
stack arg = world[parent_byte]
ECX       = output
```

`FUN_00401610 -> FUN_00401619` therefore computes:

```text
world[slot] = local[source_slot] * world[parent_byte]
```

using the same row-major / row-vector matrix convention already proven for
OBJECT explicit transforms. Translation occupies flat indices 12..14.

## MultiMatrix storage

`FUN_006b144b` allocates:

- local matrix array, stride `0x40`;
- world/secondary matrix array, stride `0x40`;
- metadata array, stride `0x10`.

Initial metadata contains:

- world pointer at metadata `+0x00`;
- operation type 1 at `+0x08`;
- parent byte at `+0x0b`;
- source-slot byte at `+0x0c`.

`FUN_0068cbb0` builds the local matrix from WXYZ quaternion, XYZ offset and
uniform scale, then copies local to world.

`FUN_006b1620` begins at slot 1. Slot 0 therefore remains its initial local
copy, while later type-1 slots are recomputed with the product above.

## Context ownership and inheritance

The HIERARCHY render constructor `FUN_006ab4a0` and LOD render constructor
`FUN_006b4050` have the same split:

- with no incoming context, their serialized MATRIX table creates a new
  MultiMatrix;
- with an incoming context, no new MultiMatrix is created. The wrapper
  `MatrixNumber` selects a slot in the inherited context and child vfunc
  `+0x24` receives that same context.

This explains the retail HIERARCHY → LOD → OBJECT graph without applying the
nested LOD's serialized one-matrix table a second time.

## Production Silverstone closure

`evidence/silverstone_era3_multimatrix_observation.json` covers all four
supplied Silverstone Era3 visual SGBs.

Across the corpus:

- 40,940 OBJECT payloads have an initial numeric world matrix;
- 39,309 use a MultiMatrix world slot;
- 1,631 use explicit OBJECT transforms;
- 20,130 containers own a MultiMatrix context;
- 1,556 containers inherit one;
- 21,690 owned world slots are evaluated;
- structural blockers: 0.

Observed owned context shapes are only:

```text
LOD        : one slot, parents [-1]
HIERARCHY  : three slots, parents [-1, 0, 0]
```

## Dynamic boundary

MultiMatrix supports operation types 2, 3, 5 and 6 in
`FUN_006b1620`. Phase 549 does not emulate those later runtime mutations.

The contract is therefore explicitly scoped to
`initial-static-multimatrix-state`.

## Output

`SHIFT.SGBMultiMatrixWorldTransformSet/1` contains:

- every owned context and its local/world slots;
- inherited-container slot selections;
- every OBJECT numeric initial world matrix;
- the source functions and matrix convention used to derive it.

The next step is to join these numeric transforms to
`SHIFT.SGBScenePlacement/1` and the Phase 548 resource render handoff, while
keeping draw admission fail-closed on actual render-resource mapping.
