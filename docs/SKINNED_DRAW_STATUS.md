# Skinned draw status

## SHIFT.SkinnedDraw/1

Render readiness requires:

- paired MEB 310/580 influence streams;
- valid influence ranges and bone indices;
- exact skeleton linkage where required;
- explicit SkinPose/1 with expected bone count;
- valid unique shader pair;
- ready material/external resources.

## Skin pose

Render consumes explicit 3x4 skinning matrices. BAB/BAS bind-local transforms remain separate.

## Reference path

`SkinnedDraw/1 + SkinPose/1 → SkinnedMeshReference/1 → reference VS/PS → raster`

## GLES parity

The RenderCommand/1 skinned payload converts into GLES31Skinning/1 and is checked for attribute ABI, four-influence layout, pose layout/space/bone count and deterministic palette hashes.

## Animation

BAB runtime grammar is partially reconstructed. Runtime pose production and unresolved animation semantics remain separate work.
