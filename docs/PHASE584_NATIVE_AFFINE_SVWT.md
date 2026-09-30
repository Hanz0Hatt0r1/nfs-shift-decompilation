# Phase 584 — semantic affine SVWT execution

Phase 583 upgrades the native geometry ABI to SVGP v3 and preserves exact
SHIFT vertex property IDs in every attribute record. That removes the semantic
ambiguity that forced Phase 582 to stop at pure translation.

Phase 584 uses those property IDs in the native Vulkan material executor to
apply non-singular, positive-orientation affine scene transforms without
assigning any reconstructed D3D9 material constant register.

## Execution path

`native_vulkan/src/vulkan_bundle_execute.cpp` now consumes:

```text
geometry.svpk (SVGP v3)
+ world_transform.svwt
→ semantic vertex transform
→ Vulkan vertex-buffer upload
→ material draw
```

The transform still happens in the dedicated native scene channel before GPU
upload. Retail material constant banks remain untouched.

## Matrix convention

The SVWT source convention remains:

- row-major 4x4 storage;
- D3D row-vector multiplication;
- translation in indices 12..14;
- affine last column `[0, 0, 0, 1]`.

For source point `p`:

`p_world = p_object * world`.

## Semantic transforms

SVGP v3 property IDs determine which vertex fields are modified.

### POSITION — property 200

POSITION0 must remain:

- property 200;
- Vulkan location 0;
- FLOAT3.

It is transformed as an affine point:

`p' = p * L + t`.

### NORMAL — property 220

NORMAL may use FLOAT3 or FLOAT4 storage. Only xyz is modified; any fourth
component is preserved.

The xyz vector uses inverse-transpose of the affine 3x3 linear part:

`n' = normalize(n * inverse(L)^T)`.

### TANGENT — property 240

TANGENT may use FLOAT3 or FLOAT4 storage. xyz uses the direct linear transform:

`t' = normalize(t * L)`.

Any fourth component is preserved.

### TANGENT2 — property 250

TANGENT2 follows the same direct-linear normalized xyz rule as TANGENT.

UV, color, blend weights, blend indices and other properties remain unchanged.

## Admission policy

The affine kernel requires:

- finite SVWT scalars;
- affine D3D row-vector form;
- non-singular 3x3 linear part;
- positive determinant for non-translation execution;
- SVGP v3 when the linear part is not identity;
- unique semantic attributes for 200/220/240/250;
- FLOAT3/FLOAT4 direction storage for normal/tangent fields.

Legacy SVGP v1/v2 packets remain executable for pure translation because the
old ABI proves only POSITION0=property 200.

A non-translation v1/v2 transform fails closed with:

`SVWT non-translation transform requires SVGP v3 semantic property IDs`.

## Reflection boundary

Negative-determinant transforms remain blocked.

The executor emits:

`SVWT reflection transform is blocked until tangent handedness semantics are proven`.

This avoids silently preserving or flipping a possible tangent handedness
component without source/runtime evidence.

## Native execution diagnostics

`SHIFT.VulkanBundleExecution/1` now reports:

- `world_transform_mode`;
- `world_transform_determinant`;
- `world_translation_xyz`;
- `world_transform_properties`;
- `world_transform_probe`.

The probe contains the first transformed POSITION/NORMAL/TANGENT/TANGENT2 xyz
values when those semantics are present.

The Python bundle runner exposes the same fields in its structured `native`
result.

## Linux Vulkan proof

The existing translation smoke remains.

Phase 584 adds a dedicated SVGP v3 material fixture with:

- POSITION 200;
- NORMAL 220;
- TANGENT 240;
- TANGENT2 250.

Its matrix combines:

- a 90-degree XY rotation;
- non-uniform positive scale;
- translation `[10, 20, 30]`.

The determinant is 24.

CI checks the native numerical probes:

- POSITION: `[10, 22, 30]`;
- NORMAL: approximately `[-0.5547002, 0.8320503, 0]`;
- TANGENT: approximately `[-0.8320503, 0.5547002, 0]`;
- TANGENT2: `[0, 0, 1]`.

The distinct NORMAL/TANGENT results prove inverse-transpose and direct-linear
paths are not being conflated.

CI also verifies two fail-closed cases:

1. a rotated legacy SVGP v2 bundle is rejected because semantic IDs are absent;
2. a reflected SVGP v3 bundle is rejected because tangent handedness behavior
   is not yet proven.

## Boundary after Phase 584

General positive-orientation affine SVWT execution is now available in the
standalone native material executor.

Phase 584 does not yet:

- make `native_runtime` consume SVWT;
- make `SHIFT.NativeSceneVulkanSet/1` executable directly by the runtime;
- resolve renderer-owned external scene resources;
- infer tangent handedness under reflections;
- replace authentic Silverstone shader-capture requirements.

The next code step is to move the same proven transform contract into the
multi-draw/runtime scene path, preferably without duplicating the transform
implementation.
