# Phase 734 next blocker

Phase 734 derives `FUN_007675f0 param_3` natively from the same-pass four `FUN_00765c40` load terms and current persistent `BODY0+0x120`, preserving the exact PC f64 `9.81` constant and the f32 spill/clamp boundary. Production `ContactOuterSessionInput` no longer supplies that scalar.

The next precise Process 2 blocker is the remaining scalar provenance in `FUN_007675f0`:

- `base_scalar`;
- `projected_scalar`;
- `alignment_scalar`.

The preferred next work is to trace the already-native `FUN_00759c90` aggregate and adjacent `FUN_00769ef0`/`FUN_007675f0` machine intermediates into those three fields, preserving exact f32/f64 boundaries and without assigning physical semantics.

A parallel bounded target remains the Phase 733 node-cache runtime join through `FUN_00717cd0` and the source `FUN_00769ef0` null/parent/child active-path gates.
