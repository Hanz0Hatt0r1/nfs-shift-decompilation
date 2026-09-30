# Phase 581 — execute SGB world transforms in Vulkan scene geometry

Phase 580 resolves every runtime-proven scene draw into an ordered
`SHIFT.VulkanDrawBundle/1` child set, but the SGB world matrix is still only
preserved as metadata.

Phase 581 closes that preparation boundary without guessing the original D3D9
world-matrix constant register.

## Strategy

The scene transform is applied to neutral geometry before the Vulkan packet is
written.

This is intentionally a preparation-time transform:

`object-space neutral geometry -> proven SGB world matrix -> world-space SVGP`

It is not claimed to reproduce the retail shader's internal transform register
ABI.

The existing BMW and geometry-only paths remain object-space by default.

## Matrix convention

The recovered SGB/MultiMatrix path uses D3D-style row-vector composition.

For a flattened 4x4 matrix, translation is carried by elements 12..14 and a
point is evaluated as:

`[x y z 1] * M`.

Phase 581 accepts only finite affine matrices with:

- m03 = 0;
- m13 = 0;
- m23 = 0;
- m33 = 1;
- a non-singular upper 3x3 linear transform.

Perspective/non-affine or singular matrices fail closed.

## Vertex semantics

When scene transform baking is requested:

- POSITION / property 200 is transformed as an affine point;
- NORMAL / property 220 uses inverse-transpose of the 3x3 linear part and is
  renormalized;
- TANGENT / property 240 uses the linear 3x3 transform and is renormalized;
- TANGENT2 / property 250 uses the same direction-vector rule;
- UV, color, bone-weight and bone-index fields are not modified.

The transform is applied only to attributes already admitted by the normal
Vulkan vertex ABI.

## Geometry packet contract

`export_vulkan_geometry_packet(..., apply_world_matrix=True)` now emits
scene-transform metadata:

- requested/executed state;
- mode `cpu-baked-row-vector-affine`;
- source world matrix;
- list of transformed vertex properties;
- inverse-transpose normal rule when applicable.

The SVGP binary version and header layout are unchanged. Existing consumers do
not need a packet ABI change.

## VulkanDrawBundle contract

`build_vulkan_draw_bundle()` gains the explicit
`apply_scene_transform` option.

Without it, the Phase 579 behavior remains unchanged:

- world matrix is preserved;
- scene submission remains blocked by the transform boundary.

With it:

- geometry is baked into SGB world space;
- `scene_transform.execution_status = baked-into-geometry`;
- the world-transform scene blocker is cleared;
- `boundary.scene_world_transform_executed = true`.

The root CLI exposes:

```bash
python shift_importer.py vulkan-draw-bundle \
  render-command.json neutral-mesh.json out/vulkan-draw \
  --apply-scene-transform
```

## NativeSceneVulkanSet

Phase 580 scene orchestration now enables scene-transform baking automatically
for every runtime-proven child.

`SHIFT.NativeSceneVulkanSet/1` reports native-scene submission ready only
when:

- every admitted child bundle is ready;
- every ready child confirms its scene transform was executed;
- no unresolved external runtime sampler/resource remains.

The ordered set therefore no longer carries a world-transform blocker for a
valid affine SGB scene matrix.

## Important limitation

Phase 581 does not yet make `native_runtime` consume
`SHIFT.NativeSceneVulkanSet/1` directly.

The current Linux runtime and bundle preparation/execution helpers are still
centered on the established BMW bundle/set formats. Phase 581 prepares correct
world-space child geometry while keeping that native scene-set admission as a
separate gate.

This also means transform changes that would occur dynamically at runtime are
not implemented by this phase; each bundle contains the world transform known
at preparation time.

## Regression coverage

Tests cover:

- D3D row-vector translation/rotation;
- inverse-transpose normal transformation;
- tangent transformation;
- non-affine matrix rejection;
- legacy object-space bundle behavior;
- explicit generic bundle transform execution;
- automatic transform execution for NativeSceneVulkanSet children;
- removal of the world-transform native-scene blocker;
- world-space SVGP vertex bytes.

## Next

Generalize the existing SPIR-V/interface/native bundle preparation layer from
BMW-only set naming/format checks to an ordered neutral scene bundle-set
contract, then let `native_runtime` consume the transformed Phase 581 child
set.

Authentic Silverstone D3D9 capture evidence is still required to produce real
runtime-proven scene shader admissions; Phase 581 only closes the already
proven placement transform boundary.
