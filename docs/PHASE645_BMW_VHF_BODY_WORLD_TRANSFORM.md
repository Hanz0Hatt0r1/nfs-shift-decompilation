# Phase 645 — canonical BMW VHF body world transform

## Playable-slice blocker reduced

Phase 643 requires every vehicle draw entering the neutral native scene-set to
carry a source-backed world matrix so the existing SVWT path can serialize and
execute it. Phase 644 automated the retail corpus -> Phase 533 -> Phase 643
orchestration, but inspection of the real Phase 533 producer exposed a concrete
retail blocker:

```text
build_real_bmw_material_slice()
  packet.node.matrix = null
  -> StaticDraw.world_matrix = null
  -> RenderCommand.world_matrix = null
  -> BMWMaterialSliceSet.world_matrix = null
  -> Phase 643 rejects vehicle-world-matrix-source-missing
```

The Phase 644 orchestration tests were correct contract tests, but they did not
claim the retail Phase 533 producer already supplied an instance transform.
Phase 645 closes that real-corpus gap from an existing source-backed resource:
the BMW VHF vehicle hierarchy.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Source identity

The existing Phase 154 VHF path reads the retail resource:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

and resolves its MATRIX hierarchy before attaching a world matrix to each
selected OBJECT node.

Phase 645 selects exactly one OBJECT satisfying all three identities:

```text
node name = BMW_M3_E36_KIT00_BODY_LODA
resource  = vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb
SHA-256   = exact SHIFT.BMWGoldenAssetManifest/1 resource SHA
```

Path matching is normalized but otherwise exact. A name-only, path-only or
SHA-only hit is not sufficient. Zero or multiple exact matches fail closed.

This ties the VHF matrix to the same canonical MEB already used by Phase 533,
Phase 643 and the durable Process 3 vehicle renderer identity.

## Matrix convention bridge

The Phase 154 VHF reference adapter evaluates hierarchy matrices as row-major
**column-vector** affine matrices:

```text
[ A00 A01 A02 tx ]
[ A10 A11 A12 ty ]
[ A20 A21 A22 tz ]
[  0   0   0   1 ]

p_world_column = M_vhf * p_object_column
```

Translation therefore occupies flattened indices `3/7/11`.

The merged Phase 581/584 SVWT contract is row-major D3D **row-vector** affine:

```text
[ A00 A01 A02 0 ]
[ A10 A11 A12 0 ]
[ A20 A21 A22 0 ]
[ tx  ty  tz  1 ]

p_world_row = p_object_row * M_svwt
```

Translation occupies flattened indices `12/13/14`.

These representations are exactly equivalent under:

```text
M_svwt = transpose(M_vhf)
```

Phase 645 performs only this exact 4x4 transpose. It rejects non-finite values,
non-affine VHF matrices, and a converted matrix that does not satisfy the SVWT
row-vector affine shape.

New contract:

```text
SHIFT.BMWVHFBodyWorldTransform/1
```

implemented by:

```text
src/bmw/bmw_vhf_body_world_transform.py
```

The report preserves both source and target matrices, matrix number, exact MEB
path/SHA and the explicit convention conversion.

## Phase 533 attachment

`apply_bmw_vhf_body_world_transform()` consumes a ready
`SHIFT.BMWMaterialSliceSet/1` and the ready VHF transform.

Before attaching the matrix it revalidates:

- canonical body MEB path;
- exact MEB SHA agreement between Phase 529 and VHF/Golden evidence;
- finite D3D row-vector affine matrix;
- any pre-existing non-null RenderCommand world matrix must equal the VHF matrix
  exactly, otherwise the operation blocks;
- the resulting RenderCommand still passes the ordinary RenderCommand validator.

The output deliberately remains:

```text
SHIFT.BMWMaterialSliceSet/1
```

because Phase 529 already defines `world_matrix` as part of the combined
RenderCommand and already equality-checks it across primitive slices. Phase 645
does not relabel a BMW-specific Vulkan manifest as a neutral scene object; it
fills an existing legal field using stronger resource evidence.

The original Phase 533 `material_slice_set.json` is kept unchanged. Phase 644 now
writes a separate derived artifact:

```text
vehicle-material-slice-set-with-vhf-transform.json
```

and only that derived set is passed to Phase 643.

## Phase 644 retail-corpus correction

The playable corpus path is now:

```text
BMW_M3_E36.bff
+ BMW_M3_E36_Cockpit.bff
+ RENDER.bff
  -> Phase 533 complete material admission
  -> original BMWMaterialSliceSet (world_matrix=null)

BMW_M3_E36.bff
+ canonical BMW golden MEB identity
  -> exact VHF BODY_LODA object
  -> VHF hierarchy world matrix
  -> exact transpose to SVWT convention

original material set
+ proven VHF transform
  -> derived BMWMaterialSliceSet (world_matrix=proven VHF matrix)
  -> Phase 643 Silverstone + BMW neutral scene-set
```

Thus Phase 644 no longer depends on a transform the retail Phase 533 producer
does not emit.

## What Phase 645 does not prove

The VHF matrix is a **resource/vehicle-assembly bind transform**. It is not the
persistent physics pose.

Phase 645 does not consume or claim:

- Process 1 active update-child -> vehicle solver-base pointer continuity;
- Phase 698 positive BODY selection;
- Phase 700 selected runtime BODY pose;
- BODY origin/basis -> vehicle root transform mapping;
- BODY0 local frame == MEB object local frame;
- dynamic per-tick vehicle world transform;
- camera-follow target.

Process 1 #1188 proves chassis semantics for BODY 0. Process 2 Phase 702 freezes
that index in the native identity ABI, but positive Phase 698/700 admission still
waits on the remaining active-object continuity proof. Phase 645 therefore keeps
its VHF transform static.

## Relationship to the BODY->SVWT frontier

Existing source-backed physics arithmetic already proves that BODY basis
`+0xd4..+0xf4` transforms a BODY-local column vector as:

```text
world_offset_column = B * local_column
```

and BAR refresh adds BODY `+0x00/+0x08/+0x10` as world origin. Combined with the
SVWT row-vector convention, a BODY-local-to-world matrix would use a transposed
linear block and BODY origin translation **if the local frames were identical**.

Phase 645 does not promote that conditional statement into a renderer mapping.
Instead it contributes the missing resource side of the bind problem: the exact
canonical MEB object's VHF transform relative to the vehicle hierarchy is now
explicit and reproducible.

The remaining transform proof can therefore be stated more narrowly as:

```text
proven BODY0 pose frame
<-> VHF vehicle-root/body-MEB frame relationship
```

rather than an unspecified “renderer object identity” problem.

## Regression coverage

`tests/test_bmw_vhf_body_world_transform.py` verifies:

- exact name/path/SHA object identity;
- exact column-vector -> row-vector transpose;
- translation relocation `3/7/11 -> 12/13/14`;
- source affine rejection;
- Phase 529 ABI preservation after attachment;
- conflicting pre-existing matrix rejection;
- MEB SHA disagreement rejection;
- no Phase 700/dynamic-transform promotion.

`tests/test_native_playable_scene_bootstrap.py` additionally verifies:

- Phase 645 executes between Phase 533 and Phase 643;
- Phase 643 receives the derived transform-bearing set, not the raw Phase 533
  file;
- failure to prove the VHF transform prevents scene composition;
- the transform report and derived set are persisted as explicit artifacts.

## Next blocker

After Phase 645, a real corpus no longer needs an invented identity world matrix
to place the canonical BMW body in the composite scene.

The next dynamic transform blocker is:

```text
prove *record+0x340 -> FUN_007615c0 vehicle solver-base continuity
-> admit BODY0 through Phase 698/700
-> prove BODY0 pose frame -> VHF vehicle-root/body-MEB frame composition
-> replace/update only source_group=vehicle SVWT per simulation step
```

Until those joins are proven, the static VHF matrix remains the correct
fail-closed vehicle assembly transform for resource-driven bootstrap.
