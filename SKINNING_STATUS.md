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


## Phase 26: BAB corpus CLI

The opaque BAB corpus fingerprint report is now exposed through `shift_importer.py bab-corpus`, using the standard resource-analysis JSON container and producing `SHIFT.BABCorpusReport/1`.


## Phase 27: BAB payload differential analysis

`bab_payload_diff.py` and `shift_importer.py bab-payload-diff` compare preserved BAB bytes by exact hashes, common prefix/suffix, overlap equality and fixed block matches. The report assigns no animation semantics and is intended as evidence input for later keyframe decoding.


## Phase 60: skinned mesh CPU reference

`skinned_reference.py` now exposes `SHIFT.SkinnedMeshReference/1`, which turns a validated `SHIFT.SkinnedDraw/1` and explicit `SHIFT.SkinPose/1` into a transformed neutral mesh. Position uses the existing four-influence linear-blend reference; NORMAL/TANGENT/BINORMAL use the direction-only transform. UV, color and influence streams remain unchanged. No parent-pose composition, inverse-bind inference or BAB keyframe decoding is introduced.


## Phase 61: desktop render bridge

Explicit SkinPose deformation is now connected to the desktop geometry oracle through `render_skinned_draw_reference()`. This provides an end-to-end position/raster smoke path for skinned draws while preserving the separation between pose application and BAB animation decoding.


## Phase 62: shader-backed skinned reference

`render_skinned_draw_reference()` connects the explicit CPU SkinPose deformation to the existing shader reference renderer. The path is intentionally deterministic: vertex and pixel programs, texture resources and constants must be supplied explicitly. BAB animation decoding remains independent.


`render_command.py` now carries `SHIFT.Skinning/1` inside RenderCommand/1 for skinned submissions. This is metadata/ABI transport only: SkinPose is still explicit, and no BAB animation data is synthesized.


## Phase 64: GLES handoff from RenderCommand

A skinned RenderCommand can now produce the existing `SHIFT.GLES31Skinning/1` contract directly. The adapter validates draw kind/readiness and reuses the serialized SkinPose/palette payload; no new animation semantics are inferred.


## Phase 71: command-level shader reference

SkinPose deformation is now reachable from the same RenderCommand source used by the GLES handoff, while the desktop oracle reuses the exact VS→PS reference path. This is the intended CPU-side oracle for future Android/backend parity tests.
