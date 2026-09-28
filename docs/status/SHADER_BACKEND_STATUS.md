# Shader backend status

## Canonical pipeline

`FX/FXO → D3D9 token decoder → SHIFT.ShaderProgram/1 → GLSL ES 3.1 / software reference`

## Implemented

- SM2/SM3 D3D9 token decoding;
- register, mask, modifier, swizzle and relative-addressing metadata;
- DCL/DEF/DEFI/DEFB reflection;
- sampler/constant/temp/input/output discovery;
- common arithmetic/vector operations;
- CMP/LRP;
- TEX/TEXLDD/TEXLDL reference operations;
- DSX/DSY reference operations;
- bounded IFC/ELSE/ENDIF and LOOP/REP lowering;
- deterministic VS/PS linkage by (usage,index);
- CTAB sampler/constant propagation;
- GLSL ES 3.1 lowering for the supported subset;
- optional glslangValidator compile/link validation;
- vertex-shader a0 relative constant reads in the software oracle.

## Boundaries

The D3D9 token/IR representation remains authoritative. Generated GLSL is a lowering target.

Still incomplete:

- all loop-register/aL addressing forms;
- every relative-addressing variant;
- complete sampler gradient/LOD semantics;
- complete D3D9 instruction/control-flow coverage;
- production BMW lighting/blending;
- all runtime specialization flags.

Unsupported operations remain visible blockers.

## Validation

`valid` compiler evidence may proceed; `invalid` blocks the path; `unavailable` is retained as an environment limitation.

## Current focus

The reference execution layer now covers structured conditionals (`IF`/`IFC`/`ELSE`/`ENDIF`) and the D3D9 matrix/sign operations already represented by the parser/GLSL backend. Unsupported operations remain explicit blockers.


Expand exact BMW shader/material coverage while using the software reference renderer as the deterministic oracle.
