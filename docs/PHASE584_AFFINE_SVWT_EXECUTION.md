# Phase 584 — semantic-aware affine SVWT execution

Phase 583 upgrades the native geometry packet to SVGP v3 and preserves the
numeric SHIFT vertex property ID in every native attribute record.

That closes the information gap which forced Phase 582 to execute only pure
translation. Phase 584 uses the new semantic ABI to execute general
non-singular affine scene transforms in the standalone native Vulkan material
path.

## Input contracts

Phase 584 consumes the existing pair:

- `SHIFT.VulkanGeometryPacket/1` / SVGP;
- `SHIFT.VulkanWorldTransformPacket/1` / SVWT.

No retail D3D9 material constant register is assigned.

The world transform remains an independent scene/native transport channel.

## Matrix convention

SVWT keeps the source-backed D3D row-vector convention.

For the upper 3x3 linear block `A` and translation `t`:

`p_world = p_object * A + t`.

The packet must still be affine:

- m03 = 0;
- m13 = 0;
- m23 = 0;
- m33 = 1;
- all scalars finite.

Phase 584 additionally requires a non-singular 3x3 linear block.

Singular transforms fail closed before any GPU upload.

## Semantic transforms

SVGP v3 identifies the fields directly:

- 200 — POSITION;
- 220 — NORMAL;
- 240 — TANGENT;
- 250 — TANGENT2.

The executor applies:

### POSITION 200

```text
p' = p * A + t
```

POSITION must remain FLOAT3.

### NORMAL 220

Normals use the mathematically correct row-vector normal transform:

```text
n' = normalize(n * transpose(inverse(A)))
```

This preserves orthogonality under non-uniform scale.

### TANGENT 240 / TANGENT2 250

Direction bases use the affine linear block without translation:

```text
t' = normalize(t * A)
```

UV, color, blend weights, blend indices and all unrelated properties remain
unchanged.

A transformed direction which collapses to zero fails closed.

## Legacy SVGP v1/v2 policy

Old packets do not contain semantic property IDs.

Phase 584 therefore keeps an intentionally asymmetric compatibility rule:

- pure translation remains accepted;
- a legacy packet containing only POSITION may execute a general affine point
  transform;
- a legacy packet with additional unknown attributes rejects any non-identity
  3x3 transform.

This prevents rotation/scale from silently leaving an unknown normal/tangent
stream in object space.

## Native execution report

`SHIFT.VulkanBundleExecution/1` now reports:

- `world_transform_mode`;
- `world_transform_determinant`;
- `world_translation_xyz`;
- `world_transformed_properties`;
- first-vertex diagnostic probes for POSITION/NORMAL/TANGENT/TANGENT2.

The probe values exist to freeze the native math in CI; they are not gameplay
or renderer inputs.

The Python bundle runner surfaces the structured mode/determinant/property
fields and retains the full native report.

## Linux Vulkan proof

The main material smoke now emits SVGP v3 with:

- POSITION 200;
- NORMAL 220;
- TANGENT 240;
- TANGENT2 250.

It applies this row-major D3D matrix:

```text
[ 0   2   0   0 ]
[-1   0   0   0 ]
[ 0   0  0.5  0 ]
[0.1 0.2 0.3  1 ]
```

This combines:

- a 90-degree in-plane rotation;
- non-uniform scale;
- translation.

The determinant is 1.

CI requires the material executor to report:

- mode `affine-semantic-v3`;
- properties `[200, 220, 240, 250]`;
- first transformed POSITION `[0.65, -1.1, 0.3]`;
- first transformed NORMAL `[0, 1, 0]`;
- first transformed TANGENT `[-1, 0, 0]`;
- first transformed TANGENT2 `[0, 0, 1]`.

## Negative proof

The Linux workflow also proves two fail-closed cases:

1. a singular v3 affine matrix is rejected;
2. a downgraded legacy v2 packet with several non-position attributes rejects
   rotation because the old binary cannot identify their semantics.

The same legacy v2 packet still executes translation successfully.

## Boundary after Phase 584

The standalone native material executor now has a complete semantic-aware
affine scene-transform path for the supported FLOAT3 scene bases.

The next integration gap is not transform math. It is scene scheduling:

- `SHIFT.NativeSceneVulkanSet/1` already owns ordered proven scene children;
- each child already carries its own SVWT;
- `native_runtime` still accepts the BMW-specific bundle-set prepare contract.

The next safe phase is therefore a neutral prepared scene-set admission layer
which reuses the established child SPIR-V/interface/native gates and feeds the
ordered Phase 580/584 children to `native_runtime` without relabeling them as
BMW.
