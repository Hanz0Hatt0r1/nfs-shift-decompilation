# SHIFT shader assembly -> Android Shader IR status

Implemented the next shader-port layer after FX/FXO discovery.

## Implemented

- D3D9 instruction-token decoder for the SHIFT SM2/SM3 shader cache.
- 5-bit register-type decoding from bits 28..30 + 11..12.
- Destination write masks and result modifiers.
- Source swizzles, source modifiers, and relative-addressing detection.
- DCL semantic declarations.
- DEF/DEFI/DEFB literal payload preservation.
- Sampler, constant, temporary and input/output register discovery.
- Instruction/control metadata including predicate bit and instruction length.
- Neutral `ShaderProgram` IR independent of OpenGL/Vulkan.
- First-pass GLSL ES 3.1 emission for the common arithmetic/texture subset.
- CLI:
  - `analyze-shader-asm`
  - `translate-shader`

## Full RENDER validation

`RENDER.bff`:

- 2,050 vertex shader blobs
- 2,050 pixel shader blobs
- 4,100 shader blobs total
- 142,605 decoded instruction tokens
- 38 unique opcodes
- 0 parser errors
- 0 unknown opcodes in the observed corpus

The opcode histogram reproduces the previously measured corpus counts exactly, which is a useful regression check for token walking.

## Important limitation

The GLSL backend is deliberately a **first-pass semantic lowering**, not yet the final production renderer. Structured control flow, exact sampler state, TEXLDD/TEXLDL gradients/LOD, relative constant addressing, SINCOS variants, and full CTAB-to-material binding still need dedicated lowering.

The compiled D3D9 token stream remains the exact fallback representation; no original shader is discarded when the GLSL translator does not yet understand an instruction.


## Phase 13

GLSL ES 3.1 lowering now covers the D3D9 ABS opcode and the DDX/DDY derivative aliases (DSX/DSY), keeping these common semantic operations out of the unsupported path.
