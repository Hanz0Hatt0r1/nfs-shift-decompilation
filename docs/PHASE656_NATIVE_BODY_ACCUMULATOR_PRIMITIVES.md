# Phase 656 — native BODY accumulator primitives

Phase 656 ports the remaining low-level BODY accumulator helpers used by the recovered SDF constraint and wheel/contact response paths.

## Source-backed helpers

The native physics library now exposes three retail boundaries:

- `FUN_007baa70`: add a contribution vector to BODY `+0x60/+0x68/+0x70` and add `point_or_lever_arm × contribution` to `+0x48/+0x50/+0x58`;
- `FUN_007baaf0`: apply the exact negative of the same update;
- `FUN_007ba9e0`: first compute `world_point - BODY origin`, where the origin is stored at `+0x00/+0x08/+0x10`, then execute the positive accumulator update.

The implementation remains deliberately neutral about force, impulse, torque and physical units. It preserves only the arithmetic and the proven storage relationship.

## Post-solve reuse

The native post-solve row kernel no longer contains a private copy of the JOINT/BAR cross-product accumulator arithmetic. Positive and negative JOINT/BAR BODY updates now call the same `FUN_007baa70` / `FUN_007baaf0` primitives directly.

HINGE post-solve rows remain separate because the recovered HINGE branch writes its two scalar combinations directly into the angular accumulator channels rather than using the point-cross-vector helper.

## Regression

`shift_runtime_body_accumulator_primitives_check` covers:

- exact positive update;
- exact negative update;
- `FUN_007ba9e0` origin subtraction;
- cancellation of a matched positive/negative pair over non-zero initial BODY state;
- fail-closed rejection of non-finite inputs.

Existing post-solve regressions continue to exercise the same JOINT/BAR path through the shared primitives.

## Remaining motion boundary

This phase does not advance BODY origin `+0x00/+0x08/+0x10` or the basis at `+0xd4..+0xf4`. No source-backed pose writer has yet been established from the indexed evidence, so vehicle motion integration remains a separate evidence gate rather than being approximated.
