---
name: shader-re
description: >-
  Evidence-driven D3D9 shader reverse engineering for SHIFT: bytecode/IR analysis,
  CTAB constants, sampler registers, VS/PS semantic linkage, GLSL ES 3.1 generation,
  compiler validation, permutation identity, and reference-oracle parity.
---
# SHIFT shader reverse-engineering workflow

Keep three representations aligned:

1. recovered D3D9 shader bytecode and reflection;
2. neutral SHIFT.ShaderProgram/1 IR;
3. generated GLSL ES 3.1 plus the desktop reference evaluator.

Shader source text is not a replacement for bytecode evidence. A generated shader is
accepted only when its inputs, outputs, sampler registers, constants and supported
operations are traceable to the IR.

## Permutation rules

Select FXO programs from sampler/constant/interface evidence. Never use archive order
as a tie-breaker. When several candidates remain equally supported, report
`ambiguous` rather than silently selecting one.

Every unique selected pair should carry `SHIFT.ShaderPermutationIdentity/1`. Its
canonical fingerprint is independent of the blob's container offset and retains
the exact per-stage byte hashes plus reflection needed to reproduce the identity.

## Backend gate

Run `glslangValidator` when available. Treat `invalid` as a submission blocker;
`unavailable` is an environment limitation and must remain explicit.

## References

Shader programming workflow inspiration:
https://github.com/gamedev-skills/awesome-gamedev-agent-skills/tree/main/skills/shader-programming