# Phase 582 — neutral Vulkan single-draw runtime admission

Phase 579 introduced the neutral atomic `SHIFT.VulkanDrawBundle/1`.
Phase 581 added the native `SHIFT.VulkanWorldTransformPacket/1` transport.

Before Phase 582, the shared SPIR-V/interface/runtime path still admitted only
the BMW-specific atomic bundle format.

Phase 582 makes the single-draw preparation and native asset-loading boundary
neutral while keeping BMW compatibility and keeping world-transform execution
explicitly unresolved.

## Supported atomic bundle formats

The shared preparation/runtime boundary now recognizes:

- `SHIFT.BMWVulkanBundle/1`;
- `SHIFT.VulkanDrawBundle/1`.

The legacy BMW API names remain compatibility aliases so existing tools and
tests do not need an all-at-once rename.

## SPIR-V compiler

`vulkan_bundle_spirv.py` now exposes:

`compile_vulkan_bundle()`.

It accepts either supported atomic bundle format and records:

`source_bundle_format`.

The existing:

`compile_bmw_vulkan_bundle()`

remains as a compatibility wrapper.

The compiled shader report stays:

`SHIFT.VulkanBundleSPIRV/1`.

No shader semantics are changed by this phase.

## Descriptor/interface gate

`vulkan_bundle_interface_gate.py` now exposes:

`validate_vulkan_interface()`.

For legacy BMW input it preserves:

`SHIFT.BMWVulkanInterfaceGate/1`.

For neutral input it emits:

`SHIFT.VulkanInterfaceGate/1`.

The descriptor policy itself is unchanged:

- set 0 binding 14: vertex constant buffer;
- set 0 binding 15: pixel constant buffer;
- set 1: D3D9 sampler register preserved as Vulkan binding;
- sampler2D/cube resources must be actually supplied.

The BMW-named validator remains a compatibility alias.

## Runner admission

The runner now exposes neutral:

`run_vulkan_bundle()`

while preserving:

`run_bmw_vulkan_bundle()`.

A neutral `SHIFT.VulkanDrawBundle/1` requires, in addition to the existing
native submission gate:

`SHIFT.VulkanDrawRuntimeProvenanceGate/1`.

That gate must be present and ready even in `prepare_only` mode.

This prevents a neutral bundle that has lost its Phase 577–579 runtime evidence
from being compiled and treated as a scene-capable native asset.

The neutral runner result format is:

`SHIFT.VulkanBundleRunner/1`.

BMW input retains the legacy runner format.

## Native runtime admission

`native_runtime/shift_runtime` now accepts a prepared neutral atomic bundle
through `--bundle`.

For neutral bundles the runtime requires:

- `SHIFT.VulkanDrawBundle/1` manifest identity;
- ready `SHIFT.NativeSubmissionGate/1`;
- ready `SHIFT.VulkanDrawRuntimeProvenanceGate/1`;
- ready `SHIFT.VulkanBundleSPIRV/1`;
- ready neutral or legacy Vulkan interface gate.

The geometry packet ABI remains unchanged.

The runtime reports the actual atomic source as:

`SHIFT.VulkanDrawBundle/1`

instead of relabeling a neutral draw as BMW.

## SVWT loading

If a bundle contains:

`world_transform.svwt`

the native runtime validates:

- magic `SVWT`;
- version 1;
- convention 1;
- exactly 64 matrix payload bytes;
- finite scalars;
- affine D3D row-vector last column `[0,0,0,1]`.

The matrix is stored in `BundleAssets` as an exact 16-float native asset.

It is not written into material constant buffers, descriptors or push
constants.

The frame-loop telemetry therefore reports:

- `bundle_world_transforms_loaded`;
- `bundle_world_transform_execution = "not-applied"`.

This is an asset-admission milestone, not transform execution.

## Linux Vulkan smoke

The Vulkan workflow now derives a neutral runtime fixture from the established
mixed-resource BMW smoke bundle:

1. copy the already-valid atomic assets;
2. switch the bundle contract to `SHIFT.VulkanDrawBundle/1`;
3. add a ready runtime-provenance gate;
4. run the neutral compiler/interface preparation path with
   `glslangValidator`;
5. attach the Phase 581 SVWT translation packet;
6. execute `native_runtime --bundle` for three frames with validation layers.

CI asserts:

- geometry source is `SHIFT.VulkanDrawBundle/1`;
- three frames render;
- one SVWT packet is loaded;
- SVWT execution is still reported as `not-applied`;
- Vulkan validation reports zero errors.

The fixture validates the contract transition without pretending that the
synthetic BMW geometry is a real Silverstone scene draw.

## Remaining boundary

Phase 582 deliberately does not generalize the ordered BMW bundle-set prepare
format.

`SHIFT.NativeSceneVulkanSet/1` still needs its own neutral set-preparation
gate before native runtime can consume the Phase 580 ordered scene directly.

It also does not execute SVWT in the material vertex path.

## Next

The next safe step is neutral ordered scene-set preparation:

`SHIFT.NativeSceneVulkanSet/1 -> per-child neutral prepare gates -> native
ordered set admission`.

That step should preserve Phase 580 draw order and require every child to pass
the Phase 582 neutral single-draw gates.

Actual SVWT application should remain a separate subsequent phase unless a
dedicated non-retail transform descriptor/push-constant channel is introduced
and validated without altering reconstructed D3D9 material constant identity.
