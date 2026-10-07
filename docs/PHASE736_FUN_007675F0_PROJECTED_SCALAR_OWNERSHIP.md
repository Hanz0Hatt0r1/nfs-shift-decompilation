# Phase 736 — FUN_007675f0 projected-scalar ownership

Phase 736 removes the last directly supplied scalar from the production `FUN_007675f0` session payload. The value historically called `projected_scalar` is derived from the first output of `FUN_00759c90` and the already-recovered probe-derived planar direction.

PC retail is authoritative. Xbox recomp is used only to accelerate and independently corroborate the cross-platform control-flow match.

## PC caller join

`FUN_007675f0` calls `FUN_00759c90(this, &first_output, &second_output)` before its strict distance/speed gate. The caller then:

1. narrows `first_output.x` from f64 to f32;
2. narrows `first_output.z` from f64 to f32;
3. uses the existing f32 X/Z planar direction;
4. evaluates `X*dirX + dirY*0.0 + Z*dirZ` in source order;
5. spills the final projected value to f32;
6. later uses that value in the visible force expression.

The exact caller span `0x0076779f..0x007677e2` is hash-locked in the Phase736 evidence.

A precision witness now protects the visible narrowing order, not merely a numerically close result. With first-output lanes `(-0.4847484798108193, 0, 17707.45002995104)` and planar delta `(2.147281910352325, 0, 0.055313743475557536)`, the source-staged path stores f32 bits `0x43e3c0c7`; an all-double projection rounded only at the end produces `0x43e3c0c8`.

## FUN_00759c90 first output

Retail `FUN_00759c90` iterates exactly three records beginning at `HDVehicle+0x7f0`. Ghidra expresses the loop step as `pdVar3 += 0x150` on a `double*`, which is a byte stride of `0xa80` (`0x150 * 8`). Phase736 locks both `0x7f0` and `0xa80` as native constants so the pointer-unit distinction cannot regress.

For each record the first output accumulates:

```text
vector(+0xb0) * scalar(+0x00)
+ vector(+0x98) * scalar(-0x08)
```

The record point at `+0xf8` contributes only to the function's second output. Phase736 therefore exposes `execute_fun_00759c90_weighted_total()` as the exact caller-relevant first-output reduction and reuses it from the existing full Phase660 aggregate implementation.

The Phase736 join deliberately does not depend on the historical Phase660 `transformed_total` or `scalar_output` convenience outputs. They remain compatibility/history surface and are not evidence for the `FUN_007675f0` projection join.

## Native production boundary

Production `ContactOuterSessionInput` no longer carries `projected_scalar`. It now carries the earlier fixed three-record `FUN_00759c90` boundary. Inside the native outer kernel:

- `execute_fun_00759c90_weighted_total()` builds the first output;
- `execute_fun_007675f0_projected_scalar()` reproduces the caller's f64→f32 narrowing and X/Z projection;
- historical fixtures may still provide an explicit projected scalar through a compatibility-only field.

This narrows the contact-outer payload but does not eliminate a whole top-level provider, so the active external-provider count remains seven.

## Xbox recomp corroboration

Xbox `sub_825939F0` in `nfs_shift_recomp.223.cpp` calls `sub_825899C0`, reloads the first output X/Z as f64, narrows them to f32, and forms the same directional projection before the strict gate. This corroborates the PC mapping but does not override PC x86 floating-point behavior.

## Remaining boundary

The three record producers/storage refresh owners behind `HDVehicle+0x7f0` remain external. Phase736 does not assign physical semantics or units to those records or their aggregate.

The next safe target is to trace ownership and refresh timing of those three records, or to continue the later `FUN_00753810`/`FUN_007ba9e0` contribution-vector path if that yields a narrower independently provable slice.
