# Phase 402 — SDF post-solve application

`FUN_007b4110` closes the per-frame SDF solver loop by consuming the solved scalar vector at `PhysicsSystem +0x40` and applying each constraint's response back to runtime bodies.

## JOINT

Each JOINT consumes three consecutive doubles beginning at sample `+0x30`. The three values are passed as a vector to `FUN_007baa70` for the positive body and `FUN_007baaf0` for the negative body. The positive lever arm is the JOINT sample point at `+0x18`; the negative lever arm comes from the negative-side sample pointer `+0x84 +0x18`. The record stride is `0xA0`.

## HINGE

Each HINGE consumes two doubles beginning at sample `+0x94`. The positive body receives `solved0 * sample.angular + solved1 * sample.linear` into `+0x48/+0x50/+0x58`; the negative body receives the exact subtraction. No linear accumulator is changed by this HINGE branch. The record stride is `0xA0`.

## BAR

Each BAR consumes one double beginning at `+0x30`. The scalar multiplies BAR direction `+0x40/+0x48/+0x50`, and the resulting vector is applied through `FUN_007baa70`/`FUN_007baaf0` to positive/negative bodies using their point offsets at `+0x18`. The record stride is `0xB8`.

## Result

This phase provides an executable source-backed post-solve kernel while keeping body-state channels as raw offsets rather than assigning unsupported physical units.
