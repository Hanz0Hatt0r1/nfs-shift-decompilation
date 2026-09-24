# Shader backend status

Current pipeline:

D3D9 FXO -> register/operand parser -> `SHIFT.ShaderProgram/1` -> GLSL ES 3.1.

Implemented:
- neutral JSON shader IR;
- common arithmetic/vector operations;
- CMP/LRP;
- TEX/TEXLDD/TEXLDL;
- DSX/DSY;
- basic IFC/ELSE/ENDIF and bounded LOOP/REP lowering;
- deterministic VS/PS semantic linkage by `(usage,index)`;
- sampler/constant reflection propagated into material binding;
- GLES 3.1 compilation regression coverage with `glslangValidator` in CI;
- unsupported instructions remain explicit comments instead of being silently dropped.

Current evidence from the supplied SHIFT 1.02 install:
- the Dropbox copy contains the original `SHIFT.exe` and a Ghidra project for it;
- `Pakfiles/Dir/RENDER.bff` and `Pakfiles/Dir/VEHICLES.bff` are present;
- the vehicle corpus includes BMW M3 E36/E46/E92 and M3 GT2 packages, giving us concrete render golden-path targets;
- the supplied Ghidra project contains a decompiler export `SHIFT.exe.c`, but the connector cannot stream that 39 MB text export as one fetch, so runtime call-site evidence still needs to be extracted from the project in smaller pieces.

Known limitations:
- exact aL/loop-register constant addressing (a0 relative addressing is implemented in the software reference with explicit tie guards);
- exact D3D9 sampler-state -> BMT/DDS state binding;
- exact VS/PS permutation selection against runtime specialization flags;
- exact loop-register semantics;
- final MGEO/VHF -> DrawPacket execution path.

Next target: use the BMW M3 package as the golden path for exact sampler/vertex-packing evidence, then lock the resulting material draw packet before moving deeper into MGEO/VHF and skinning.

## Phase 38: linked GLES shader validation

`shader_backend.validate_linked_shader_pair()` now validates a `SHIFT.LinkedShaderPair/1` by compiling vertex/fragment stages separately and, when `glslangValidator` is available, linking the pair with `-l`. The result is `SHIFT.GLESShaderValidation/1` with explicit `valid`, `invalid`, or `unavailable` status and machine-readable blocking reasons.

## Phase 39: RenderCommand integration

The GLES shader compiler validator can now be attached to `SHIFT.RenderCommand/1` on demand. This keeps expensive compiler work out of the default render-link pass while making compile/link evidence part of the final submission contract when requested.

## Phase 46: software shader execution oracle

`shader_reference.py` now executes a strict subset of parsed D3D9 `ShaderProgram` instructions in software, including arithmetic, dot/cross/normalize, scalar/vector math, texture reads and explicit source/write modifiers. Unsupported control-flow and unknown opcodes return machine-readable `unsupported` status; missing inputs/textures return `error`. This is a reference oracle, not a claim of full HLSL compatibility.


## Phase 49: material constant execution

`shader_reference.py` now converts `SHIFT.MaterialUniformBinding/1` float register bindings into deterministic D3D9-style `c/c2/c3/c4` vec4 banks. Scalar/vector values and float4x4 row registers are supported; non-float or non-register-set-2 bindings are explicit `unsupported` states.


## Phase 53: relative constant addressing

The software shader reference now executes D3D9 vertex-shader a0 relative constant reads and MOVA writes. Constant indices are resolved as the signed 11-bit base index plus the selected a0 component; out-of-range constant reads retain the D3D9 zero-vector behavior. The oracle refuses non-vertex use, non-a0 relative tokens and exact rounding ties instead of guessing undocumented behavior.


## Phase 54: vertex stage reference boundary

The software reference executor now exposes all written shader outputs to the renderer, enabling a bounded vertex-stage execution path. POSITION/TEXCOORD/NORMAL/TANGENT/BINORMAL semantics that are already represented in the neutral MEB contract can flow through the VS->PS reference boundary; unresolved semantics remain explicit blockers.


## Phase 56: proven skin input semantics

Vertex input validation now recognizes `BLENDWEIGHT0` and `BLENDINDICES0` alongside POSITION/TEXCOORD/NORMAL/TANGENT/BINORMAL. The reference renderer sources these values from the neutral MEB mesh, while the separate skinning matrix/pose path remains intentionally unimplemented.


## Phase 58: samplerCube reference resource

The software executor now supports `samplerCube` when the bound resource is `SHIFT.ReferenceCubeTexture/1`. The cube resource is deliberately explicit and separate from 2D images; `sampler3D`/`sampler1D` remain unsupported.


## Phase 59: DDS cubemap input

The texture reference decoder now produces six-face cube resources from complete DDS cubemaps, preserving the existing RGBA8 software-resource ABI. SamplerCube execution can therefore consume either explicitly assembled faces or a decoded DDS cubemap.
