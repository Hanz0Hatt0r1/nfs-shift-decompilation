# SHIFT Skinning / Animation status

## Skin input ABI

- MEB 310 → BLENDWEIGHT0, FLOAT32x4
- MEB 580 → BLENDINDICES0, UINT8x4

Influence pairing and bone-index validity are checked explicitly.

## SkinPose

`SHIFT.SkinPose/1` is the runtime render pose source. It carries one 3x4 matrix per bone in skinning space.

`SHIFT.BindSkeleton/1` stores bind-local BAB/BAS information separately.

## CPU reference

`SkinnedDraw/1 + SkinPose/1 → SkinnedMeshReference/1`

Four-influence linear blend skinning is available for positions; direction streams use direction-only transforms.

## BAB animation runtime

The old “opaque tail only” description is obsolete.

The current decoder reconstructs the source-backed bank variants 0/1/2, channel dispatch types 0–9, channel metadata and proven interpolation paths, including quaternion slerp.

Remaining uncertainties stay explicit, notably unresolved Euler axis/order details and unconsumed trailing payload bytes.

## Render/GLES

Skinned draws flow through RenderCommand/1 into the GLES31Skinning/1 contract. The parity gate checks attribute ABI, influence layout, pose layout/space/bone count and deterministic pose/palette hashes.

## Remaining work

Resolve the remaining BAB semantics, produce runtime poses from proven animation data and expand real-resource validation.
