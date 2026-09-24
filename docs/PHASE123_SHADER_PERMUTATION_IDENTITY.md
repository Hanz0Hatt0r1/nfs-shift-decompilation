# Phase 123 — stable shader permutation identity

`SHIFT.ShaderPermutationIdentity/1` gives a content-derived identity for one exact D3D9 vertex/pixel shader pair.

The identity fingerprint contains:

- VS and PS shader-model versions;
- exact VS and PS byte SHA-256 values;
- instruction counts and unsupported-opcode lists;
- VS/PS semantic inputs/outputs;
- pixel sampler declarations and sampler types;
- reflected pixel constants.

Blob offsets are intentionally excluded from the canonical fingerprint. `pair_byte_sha256` and the per-stage byte hashes remain available for direct byte-level provenance.

`MaterialBinding/1` now exposes this identity for the selected candidate and the BMW golden gate requires it whenever shader selection is unique. This prevents a render from being considered golden merely because a sampler-set heuristic selected a permutation.

## Next

Use the exact BMW material slice with this identity to run the actual shader-reference path, validate GLSL with `glslangValidator` when available, and record the first real-material image hash.

## Phase 126 integration

`SHIFT.ShaderPermutationIdentity/1` now carries vertex constant register usage as well as pixel constant usage, allowing the BMW runtime parity gate to compare `MaterialUniformBinding/1` across both shader stages.
