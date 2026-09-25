# Phase 247 — BAB animation runtime reconstruction

Phase 247 converts the previously opaque BAB animation tail into an evidence-backed
runtime decoder without touching the renderer.

## Recovered runtime boundary

The decompiled retail source contains a common animation-bank reader FUN_00680690,
three runtime bank variants (FUN_00683b10, FUN_00683e20, FUN_00684180), and a
channel dispatcher FUN_00684320.

The new bab_animation_runtime.py follows that boundary:

- common bank prefix: flags, record count, resource/bank id, base records, vector metadata and name;
- mode 0: three per-bone channel arrays for translation/rotation/scale;
- mode 1: frame quantum/count, one primary channel and one channel per bone;
- mode 2: one optional channel per bone;
- per-channel metadata: serialized subtype/flags, name and metadata word.

## Channel types

| Type | Reconstructed storage | Sampling evidence |
|---:|---|---|
| 0 | uniform vec3 frame sequence | linear |
| 1 | uniform quaternion frame sequence | quaternion slerp |
| 2 | time + vec3 keyframes | linear |
| 3 | time + vec4 keyframes | linear |
| 4 | constant vec3 | constant |
| 5 | constant vec4 | constant |
| 6 | constant Euler3 | converted by FUN_004d8c10; axis/order unresolved |
| 7 | uniform scalar frame sequence | linear |
| 8 | time + scalar keyframes | linear |
| 9 | constant u32 | constant |

Type 1 is positively tied to FUN_00446150, whose recovered implementation is
spherical quaternion interpolation followed by normalization.

Type 6 conversion is reconstructed from FUN_004d8c10, but the source-side axis/order
convention is not established, so the module exposes that uncertainty.

## Reconstruction boundaries

The parser is strict about byte bounds and invalid presence flags. strict=False
returns a machine-readable blocker instead of fabricating a partial pose. Trailing
bytes are preserved as an explicit blocker.

This phase does not infer parent-pose composition, inverse-bind matrices, clip
selection, or final animation-driven vehicle state.

The next non-rendering target is SGB scene semantics: recover NODE/FLAT/SUMM records
and connect transforms, resource references and track assembly using source/runtime
evidence.
