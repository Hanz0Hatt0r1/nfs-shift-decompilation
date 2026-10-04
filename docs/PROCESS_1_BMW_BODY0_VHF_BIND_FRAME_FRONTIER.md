# Process 1 — BMW BODY0 ↔ VHF bind-frame frontier

## Playable-slice blocker reduced

The vertical-slice transform path now has both ends prepared:

```text
physics:
  persistent BODY snapshots
  -> proven BMW chassis BODY 0
  -> Phase 698 selection
  -> Phase 700 exact origin+basis handoff

renderer/resources:
  canonical BMW body MEB
  -> Phase 645 source-backed VHF bind transform
  -> Phase 646 per-step D3D row-vector transform transport
```

The remaining semantic transform problem is no longer “find the renderer object”
or “invent a world-matrix transport”.  It is one frame relation:

```text
BODY0 local frame at bind time
  -> VHF vehicle-root frame used by the canonical body MEB
```

This block freezes that frontier without assuming the two frames are identical.
No original `SHIFT.exe` execution and no new runtime capture are used.

The machine-readable contract is:

```text
SHIFT.BMWBody0VHFBindFrameFrontier/1
```

implemented by:

```text
tools/ghidra/build_bmw_body0_vhf_bind_frame_frontier.py
```

## Inputs already proven elsewhere

### Persistent BODY pose convention

The BODY frame evidence gives persistent origin at:

```text
+0x00 / +0x08 / +0x10
```

and the 3x3 basis at:

```text
+0xd4 .. +0xf4
```

The source-backed arithmetic used by Phase 645 establishes the column-vector
relationship:

```text
world_offset_column = B * local_column
```

Therefore a BODY pose with origin `O` has the homogeneous column-vector form:

```text
M_BODY_col = [ B  O ]
             [ 0  1 ]
```

and its exact D3D/SVWT row-vector representation is the transpose:

```text
M_BODY_row = transpose(M_BODY_col)
```

No axis remap is inserted by this frontier.

### Phase 645 VHF bind transform

`SHIFT.BMWVHFBodyWorldTransform/1` selects the canonical body object by exact
name/path/SHA and converts its VHF hierarchy matrix to the established D3D
row-vector convention by an exact 4x4 transpose.

This transform is an object-local -> VHF vehicle-root/assembly bind transform.
It is not a persistent physics pose.

### Phase 646 transport

Phase 646 accepts a complete finite non-singular D3D row-vector affine matrix per
fixed step and applies it only to authoritative `source_group=vehicle` draws from
an immutable object-space baseline.

Thus renderer-side transport no longer needs to be solved in Process 1.

## Exact composition

Define:

```text
M_vhf_bind        canonical body-MEB object local -> VHF vehicle root
M_BODY0_bind      BODY0 local -> VHF vehicle root at bind/assembly time
M_BODY0_runtime   current persistent BODY0 local -> world
```

Then object-local -> current world in column-vector notation is:

```text
M_object_world_col =
    M_BODY0_runtime_col
  * inverse(M_BODY0_bind_col)
  * M_vhf_bind_col
```

The same mapping in the Phase 646 row-vector convention is:

```text
M_object_world =
    M_vhf_bind
  * inverse(M_BODY0_bind)
  * M_BODY0_runtime
```

The multiplication order is part of the contract.  The Python oracle implements
full affine inversion and 4x4 multiplication and has a regression where the
three translations are deliberately different, so an order reversal cannot pass
silently.

## The one missing static witness

Current evidence does **not** prove `M_BODY0_bind`.

In particular this block does not assume:

```text
M_BODY0_bind = identity
BODY0 local frame = MEB object local frame
BODY0 local frame = VHF vehicle root
```

A future positive proof is carried as:

```text
SHIFT.BMWBody0BindFrameProof/1
```

with:

```text
status = ready
evidence_state = proven-static
body_index = 0
body_name = body
frame_relation = BODY0-local-to-VHF-vehicle-root
matrix_convention = row-major D3D row-vector affine
body0_local_to_vhf_vehicle_root_row_matrix = 16 finite scalars
```

and non-empty source/static target provenance.  The proof is rejected if it says
an identity matrix was merely assumed, if it depends on original-game execution,
or if it uses a new runtime capture.

An identity matrix is not intrinsically forbidden; it is legal only if static
evidence independently proves that exact result.

## Targeted static worklist

The current finite worklist is intentionally conservative.

### `FUN_007b6900` — SDF loader anchor

The existing parser contract proves this loader recognizes BODY `pos` and `ori`
fields.  The next proof must trace the **exact BODY index 0** descriptor values;
it must not simply rename those fields as the final runtime transform.

### `FUN_007b3670` — 0x170-byte BODY builder

Existing construction evidence proves this function lowers SDF BODY records into
the persistent BODY domain.  The required proof is exact value continuity for
BODY0 pose-related descriptor vectors into the runtime BODY record or into a
subsequent setter.

### `FUN_007b7840` — pose-writer candidate

Existing writer evidence verifies that this function can write BODY origin and
basis under flags.  It is **not** yet proven to own bind initialization.

The targeted next stage is therefore:

```text
callers/references of FUN_007b7840
+ exact instruction/p-code inputs
+ BODY0 index/pointer provenance
+ ordering relative to FUN_007b3670 construction
```

If another writer actually owns initialization, the proof must follow that
writer instead; the frontier fails closed rather than preserving the candidate.

## Interaction with the current BODY-owner blocker

Process 1 `SHIFT.GlobalVehicleBodyOwnerIdentity/1` remains blocked on the missing
retail `SHIFT.GhidraFunctionInstructions/2` row for `FUN_00765470`.

This frontier treats BODY-owner admission and bind-frame proof as independent:

```text
BODY-owner positive   bind-frame positive   result
-------------------   -------------------   ------------------------------
false                 false                 blocked on both
true                  false                 transform formula ready, bind blocked
false                 true                  bind known, retail pose admission blocked
true                  true                  Phase 646 matrix producer ready
```

That separation is deliberate.  Static bind-frame analysis can proceed without
faking the currently inaccessible targeted instruction row, and the eventual
positive owner proof can drop into the already-frozen transform equation.

## Process 2 / Process 3 handoff

After both proofs are positive:

```text
Phase 700 SelectedVehicleBodyPose(BODY 0)
  origin[3] + basis[9]
        |
        v
M_BODY0_runtime
        |
        + M_BODY0_bind (proven static)
        + Phase 645 M_vhf_bind
        v
M_object_world (D3D row-vector affine)
        |
        v
Phase 646 vehicle-world-transform transport
```

No second renderer matrix convention or BODY pose ABI is introduced.

## Current evidence status

With current `main`:

```text
formula_ready                         = true
BODY0_bind_frame_proven               = false
retail_BODY0_pose_admission_ready     = false
phase646_world_matrix_producer_ready  = false
vehicle_world_transform_ready         = false
```

The two remaining direct evidence requests are:

1. obtain the already-defined retail `FUN_00765470` receiver result so Phase 703
   can admit BODY0 through Phase 700;
2. prove `M_BODY0_bind` from the static initialization/writer chain above.

## Fail-closed policy

This frontier rejects:

- any chassis BODY other than exact BMW BODY index 0;
- disagreement among Process 1 BODY-owner readiness flags;
- reintroduction of the obsolete update-child equality gate;
- an upstream claim that the world transform is already ready;
- a Phase 645 input that already claims BODY/physics pose consumption;
- non-finite, non-affine, or singular matrices;
- a bind proof without static target provenance;
- a bind proof produced by identity assumption;
- a bind proof using original-game execution or new runtime capture.

The unit tests use synthetic positive matrices only to verify transport and matrix
order.  They are explicitly not retail evidence.
