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
- exact relative constant addressing;
- exact D3D9 sampler-state -> BMT/DDS state binding;
- exact VS/PS permutation selection against runtime specialization flags;
- exact loop-register semantics;
- final MGEO/VHF -> DrawPacket execution path.

Next target: use the BMW M3 package as the golden path for exact sampler/vertex-packing evidence, then lock the resulting material draw packet before moving deeper into MGEO/VHF and skinning.

## Phase 38: linked GLES shader validation

`shader_backend.validate_linked_shader_pair()` now validates a `SHIFT.LinkedShaderPair/1` by compiling vertex/fragment stages separately and, when `glslangValidator` is available, linking the pair with `-l`. The result is `SHIFT.GLESShaderValidation/1` with explicit `valid`, `invalid`, or `unavailable` status and machine-readable blocking reasons.
