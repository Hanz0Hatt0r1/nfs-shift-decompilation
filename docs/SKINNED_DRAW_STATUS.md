# Skinned draw status

## SHIFT.SkinnedDraw/1

The skinned renderer path is now represented as an explicit neutral contract.
A packet is render-ready only when the following evidence is present:

- SHIFT.VertexLayout/1 has one BLENDWEIGHT0 attribute from property 310.
- SHIFT.VertexLayout/1 has one BLENDINDICES0 attribute from property 580.
- Weights are FLOAT32x4, indices are UINT8x4, and both are non-normalized.
- The mesh skinning summary confirms a valid paired skin stream. When older
  DrawPackets do not carry the summary, it is derived only from the explicit
  vertex-layout attributes; no per-vertex data is guessed.
- SHIFT.BindSkeleton/1 has complete coverage (1.0), a positive bone count,
  one link per bone, and a 12-float row-major 3x4 local matrix for every bone.
- The resulting SHIFT.BonePalette/1 preserves the bind matrices and the
  original BAB animation payload offset/size/hash. The payload remains opaque
  until its keyframe grammar is proven.
- Shader/material selection is unique, the selected shader pair is unique, and
  any material texture uses an explicit FXO/CTAB sampler register. External
  samplers remain explicit renderer requirements.

The contract intentionally records a four-influence palette interface:
BLENDWEIGHT0 + BLENDINDICES0, four values each, with indices addressing
[0, bone_count - 1].

This phase does not decode animation keyframes, compose parent matrices into
global pose matrices, or issue GL calls. Those are separate evidence-backed
steps.


### Automatic DrawPacket linkage

build_draw_packets() can now consume SHIFT.BAB and SHIFT.BAS analysis records. For a skinned MEB it attaches SHIFT.BindSkeleton/1 only when one unique BAB/BAS pair is supported by exact MEB bone-name evidence:

- BAB bone order equals the complete MEB skeleton.bone_names list.
- BAS node names are unique and cover exactly the same name set.
- More than one exact pair is reported as ambiguous; the packet is not made render-ready by choosing one arbitrarily.
- No BAB/BAS match is not fatal to static packet construction; the packet carries skeleton_resolution diagnostics and remains unsuitable for a ready skinned draw.


### Bind-local versus skinning pose

SHIFT.BindSkeleton/1 records local bind transforms from the verified BAB/BAS link. Those matrices are not treated as GPU skin matrices. SHIFT.SkinnedDraw/1 is render-ready only when a separate SHIFT.SkinPose/1 is supplied with one 3x4 matrix per bone and `matrix_space=skinning`. The skin pose is the only matrix source accepted by the GLES 3.1 palette contract.

This separation leaves animation decoding and bind-pose/inverse-bind semantics explicit: no parent composition or inverse-bind operation is implied by the BAB parser.
