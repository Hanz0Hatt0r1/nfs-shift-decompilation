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
