---
name: shader-re
description: >-
  Evidence-driven D3D9 shader reverse engineering for SHIFT.
---
# SHIFT shader reverse-engineering workflow

## Representations

Keep aligned:

1. D3D9 token/bytecode evidence;
2. `SHIFT.ShaderProgram/1`;
3. generated GLSL ES 3.1;
4. desktop reference execution.

Generated GLSL never replaces token/IR evidence.

## Permutations

Select FXO programs by sampler, constant, semantic and specialization evidence. Archive order is never a semantic tie-breaker. Equal candidates remain ambiguous.

## Validation

Use `glslangValidator` when available.

- `valid` may proceed;
- `invalid` blocks;
- `unavailable` remains an environment limitation.

## Current gaps

Complete D3D9 control flow, all relative-addressing variants, exact sampler/LOD semantics and the full BMW material model remain open.
