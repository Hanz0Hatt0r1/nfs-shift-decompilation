# SHIFT shader assembly / ShaderProgram status

## Canonical representation

`FXO blob → D3D9 token stream → SHIFT.ShaderProgram/1 → GLSL ES 3.1 / software reference`

The token stream and neutral IR remain authoritative.

## Decoder

Implemented:

- SM2/SM3 token decoding;
- register/mask/modifier/swizzle metadata;
- relative-addressing detection;
- DCL/DEF/DEFI/DEFB preservation;
- sampler/constant/temp/input/output discovery;
- instruction/control metadata.

## Backend

The current stack supports a bounded set of arithmetic, texture, derivative, comparison and control-flow operations plus semantic VS/PS linkage. The software oracle additionally evaluates the documented vertex-shader a0 constant-address form.

## RENDER corpus evidence

The established corpus snapshot records:

- 2,050 vertex shader blobs;
- 2,050 pixel shader blobs;
- 4,100 shader blobs total;
- 142,605 decoded instruction tokens;
- 38 unique opcodes;
- 0 parser errors.

These counts describe corpus parsing, not complete backend compatibility.

## Remaining gaps

Complete loop-register/aL semantics, all relative addressing variants, sampler gradient/LOD behavior, full D3D9 control flow, production BMW lighting/blending and runtime specialization remain open.
