# Phase 582 — translation-only SVWT material execution

Phase 581 freezes the source-backed SGB world transform into
`SHIFT.VulkanWorldTransformPacket/1` (`SVWT`) and proves the Python/native
matrix convention. The packet is transported with a Vulkan draw bundle but is
not consumed by the material executor.

Phase 582 closes the first real execution slice.

## Native execution rule

`native_vulkan/src/vulkan_bundle_execute.cpp` now looks for the optional
`world_transform.svwt` sidecar after loading `geometry.svpk`.

The packet is independently checked again for:

- magic `SVWT`;
- version 1;
- D3D-row-to-GLSL-column convention tag 1;
- exact 64-byte matrix payload;
- finite matrix scalars;
- affine D3D row-vector last column.

No retail material constant register is assigned.

## Why translation-only

SVGP v2 carries location/format/offset/stride, but it does not carry the
original SHIFT property/semantic identifier in its native attribute records.

That is enough to identify POSITION0 because the existing contract requires
exactly one FLOAT3 attribute at Vulkan location 0. It is not enough to
reliably distinguish all normal/tangent bases in the native executor.

Therefore Phase 582 admits only matrices whose upper-left 3x3 is identity.

For those matrices:

`p_world.xyz = p_object.xyz + translation.xyz`

is applied directly to every POSITION0 value before the vertex buffer is
uploaded.

A rotation, scale, shear, reflection or other non-identity linear transform
fails closed with:

`SVWT native material execution supports translation-only until the geometry ABI carries semantic IDs`.

Pure translation does not require normal/tangent modification, so this slice
does not corrupt lighting bases.

## Execution report

`SHIFT.VulkanBundleExecution/1` now records:

- `world_transform_present`;
- `world_transform_executed`;
- `world_translation_xyz`.

The Python Vulkan runner parses this native JSON and exposes the same fields
under its `native` result instead of requiring callers to grep stdout.

## Linux Vulkan proof

The material smoke bundle receives a dedicated SVWT translation of
`[0.1, 0, 0]`.

CI requires the native material executor to report:

`world_transform_executed = true`.

A second copy of the same prepared bundle receives a 90-degree rotation SVWT.
CI requires the executor to reject it with the translation-only blocker.

This gives one positive and one negative native material-path proof.

## Compatibility

Bundles without `world_transform.svwt` retain the prior execution path.

BMW material constants remain untouched. The SVWT channel is independent of
the reconstructed D3D9 constant banks.

The `native_runtime` XCB/swapchain material path does not yet consume SVWT;
Phase 582 closes the standalone native material executor first.

## Next

There are two safe follow-up directions:

1. carry semantic IDs in a new native geometry ABI so general affine matrices
   can update POSITION/NORMAL/TANGENT/TANGENT2 correctly; or
2. add a dedicated native shader transform channel whose placement relative to
   view/projection is explicitly defined rather than mapped onto a guessed
   retail constant register.

After general affine execution is available, the same transform contract can
be admitted in the `native_runtime` multi-draw/scene-set path.
