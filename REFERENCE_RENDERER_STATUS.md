# Desktop reference renderer

`reference_renderer.py` is the first renderer executable that consumes only neutral mesh IR. It rasterizes indexed triangles with a deterministic orthographic MVP, optional per-vertex RGBA, depth testing and a PPM output path. It deliberately omits material/shader execution; its role is to be a geometry oracle before the GLES 3.1 backend.

Inputs can be the JSON emitted by `meb_format.mesh_to_jsonable()` after BFF decoding has already happened. The renderer itself has no dependency on `BFF`, `LZX`, `MEB` parsing or the original game runtime.

## Phase 35: RenderCommand execution

The reference renderer now consumes `SHIFT.RenderCommand/1` directly. It validates the final submission contract, verifies command vertex count/index ranges against the supplied neutral mesh, then reuses the deterministic geometry rasterizer. Shader source and material state remain validation inputs, not software shader execution.

## Phase 42: textured RenderCommand CLI

The reference renderer now exposes `--render-command --textured --mesh ... --texture ...` for deterministic UV0 texture execution. The command still passes through `RenderCommandValidation/1`; DDS bytes are decoded by `texture_reference.py` and sampled using the explicit sampler reference.


## Phase 44/45: current reference-renderer scope

The reference renderer now has two deterministic execution surfaces: geometry-only `RenderCommand/1` execution and a UV0 software texture path backed by DDS reference decode/sampling. It is still intentionally not a software HLSL interpreter; material lighting/blending operations remain an explicit next layer.


## Phase 48: pixel shader reference execution

The textured reference renderer can optionally execute the embedded `SHIFT.ShaderProgram/1` pixel IR per covered fragment. The initial bounded path supports `TEXCOORD0` and sampler `s0` and reuses the deterministic DDS sampler; unsupported shader inputs/opcodes remain explicit blockers rather than guessed behavior.


## Phase 49: material constant path

The shader-backed reference render path can now source numeric material values from `MaterialUniformBinding/1` automatically. This enables constant-driven shader operations such as texture tinting while retaining strict type/register validation.


## Phase 50: multi-texture shader reference execution

The shader-backed reference path now supports multiple 2D sampler registers through an explicit `texture_images` map. The command's `d3d9_sampler_register` and embedded sampler state determine which reference image/state is supplied to each `sN`. Missing sampler images remain hard execution errors.


## Phase 51: semantic TEXCOORD layers

The shader-backed reference renderer now maps `TEXCOORD0..4` declarations to MEB UV property layers `130..134` by semantic index, interpolating the selected layer into the shader register declared by the pixel program. Missing required layers are explicit execution errors; COLOR0/1 remains outside this automatic path because its channel order is still unresolved.


## Phase 52: normal/tangent/binormal semantic inputs

The shader-backed reference renderer now accepts `NORMAL0`, `TANGENT0` and `BINORMAL0` pixel inputs and interpolates them from neutral MEB mesh attributes into declared D3D9 input registers. Values are passed through unchanged; normalization remains an explicit shader operation. Missing required attributes are hard execution errors.


## Phase 54: vertex-shader reference execution

The shader-backed desktop oracle now optionally executes the embedded SHIFT.ShaderProgram/1 vertex stage before rasterization. Supported MEB-backed vertex inputs are POSITION0, TEXCOORD0..4, NORMAL0, TANGENT0 and BINORMAL0; the vertex outputs are linked to pixel inputs by semantic (usage,index), independent of physical register numbers. POSITION0/POSITIONT0 is treated as clip-space output for this path, while non-position varyings are perspective-correctly interpolated before pixel execution.

When a vertex program is present, CPU-side world/MVP transforms are not applied a second time. Unsupported vertex semantics, missing outputs, non-finite clip positions and unmatched VS/PS semantics remain hard errors.


## Phase 55: alternate MEB TEXCOORD family

The shader-backed reference renderer now resolves MEB properties `230..234` as the established 3-component `TEXCOORD0..4` UVW family. Layouts that contain the 230-family can therefore feed the existing VS/PS semantic path without fabricating 130-family data. A mesh that contains both 130-family and 230-family properties for one semantic is rejected as an ABI collision rather than silently selecting one declaration.


## Phase 56: skin input semantics

The integrated VS reference path now accepts the already-proven `BLENDWEIGHT0` and `BLENDINDICES0` MEB attributes. Bone weights enter the shader as float4; bone indices are widened from their proven UINT8x4 storage to numeric float4 shader inputs without normalization. This phase only wires the input ABI; it does not apply bone matrices or claim animated deformation.


## Phase 57: explicit external sampler resources

The shader-backed reference renderer now preserves `external_samplers` in the RenderCommand contract and accepts explicit `sampler2D` images through `external_texture_images={sN: image}`. The legacy material image fallback is never assigned to a required external sampler register. Resource type is checked against the embedded shader sampler declaration; `samplerCube`, `sampler3D` and `sampler1D` remain explicit unsupported resource types rather than being coerced to 2D.


## Phase 58: cube-map external resources

The shader reference now executes `samplerCube` against `SHIFT.ReferenceCubeTexture/1`, a six-face resource with explicit `px/nx/py/ny/pz/nz` RGBA8 images. D3D9 cube lookup consumes the three-component direction vector and resolves the major-axis face before sampling that face as a 2D image. `sampler3D` and `sampler1D` remain unsupported.


## Phase 59: native DDS cubemap decode

`decode_dds()` now recognizes a complete DDS cubemap (`DDSCAPS2_CUBEMAP` plus all six face flags), advances by the full per-face mip-chain stride, decodes each base level into the existing RGBA8 reference image ABI, and returns a `SHIFT.ReferenceCubeTexture/1` resource. Incomplete face flags or truncated face/mip payloads are hard errors.


## Phase 60: skinning bridge preparation

Phase 60 does not change the renderer entry point yet; instead it provides a validated `SHIFT.SkinnedMeshReference/1` mesh adapter that can be consumed by the existing reference rasterizer. This keeps the next VS/PS integration change small and testable.


## Phase 61: skinned reference render entry point

`render_skinned_draw_reference()` now applies the explicit `SHIFT.SkinPose/1` through `SHIFT.SkinnedMeshReference/1` and feeds the resulting neutral mesh into the existing desktop geometry oracle. This establishes one rendering surface for static and skinned geometry while deliberately keeping shader/material execution as a separate layer.


## Phase 62: skinned VS→PS reference

`render_skinned_draw_reference()` can opt into the embedded shader oracle: it materializes `SHIFT.SkinnedMeshReference/1`, then executes vertex and pixel ShaderProgram/1 with the existing semantic linkage and rasterization path. Skinning and shader execution therefore share one deterministic desktop reference surface.


## Phase 65: explicit extended semantic streams

The desktop reference renderer can now accept a caller-supplied `semantic_rows` mapping for shader semantics that are proven at the shader interface but whose MEB source property is unresolved. `TEXCOORD5` is the first intended use: the BMW bodywork shader pair establishes the semantic linkage, while the renderer refuses to fabricate a MEB property id.

Explicit streams are available to both VS and PS stages and are linked by `(usage,index)`. Missing streams remain hard errors.
