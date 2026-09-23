# SHIFT Skinning / Animation status

`SHIFT.Skinning/1` формализует MEB skinning inputs: property 310 = FLOAT4 weights и property 580 = UINT8x4 bone indices.

`skinning.py` теперь содержит:
- проверку парности weights/indices и диапазона bone indices;
- deterministic CPU reference skinning для positions;
- rotation-only reference transform для normals/tangents;
- optional source-weight normalization для случаев, когда исходный набор весов требует нормализации при runtime upload.

`SHIFT.SkinnedDraw/1` допускает draw only when mesh is skinned, a resolved pose has the expected bone count, each bone has a valid 3x4/4x4 matrix, and provided influence arrays are valid.

`resource_formats.analyze_decoded_resource()` now recognizes binary `.bab` resources and routes them through the verified BAB parser, preserving the opaque animation tail with offset/size/SHA-256 instead of classifying it as unknown binary data.

BAB bone records и BAS hierarchy уже парсятся существующими parsers. BAB animation tail пока хранится как opaque payload с offset/size/SHA-256; keyframe grammar не угадывается.

## Phase 23: shader readiness boundary

`SHIFT.SkinnedDraw/1` now requires each selected material to carry a valid `SHIFT.LinkedShaderPair/1`, and rejects explicit shader translation errors. This keeps the CPU/reference and future GLES skinning paths aligned with the same shader readiness contract as `StaticDraw/1`.
## Phase 24: bind-pose equivalence

`skinned_reference.validate_bind_pose()` now provides a deterministic `SHIFT.SkinBindPoseCheck/1` report for an explicit `SHIFT.SkinPose/1`. It reports maximum Euclidean position error, per-vertex mismatches, tolerance, and influence validation without deriving the pose from BAS/BAB.

## Phase 25: BAB corpus fingerprinting

`bab_corpus.py` groups parsed BAB analyses by exact bone-name skeleton signatures and compares preserved animation-tail SHA-256/size metadata. It intentionally treats the post-table payload as opaque; no keyframe grammar is inferred from heuristics.
