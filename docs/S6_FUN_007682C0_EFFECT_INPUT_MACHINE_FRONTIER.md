# S6 — `FUN_007682c0` effect-input and PC x87 magnitude frontier

## Blocker reduced

After `SHIFT.Fun007682c0Body0DeltaDestination/1`, the visible BODY0 `+0x50`
application is internal. The remaining adjacent boundary is effect production.
This slice closes two previously broad parts of that boundary:

1. exact PC source provenance for all visible inputs feeding
   `FUN_007682c0`, `FUN_0075ada0`, and `FUN_007595d0`;
2. the two PC x87 magnitude paths and the `FUN_007682c0` speed-factor f32
   checkpoint, without substituting host `std::sqrt`.

`FUN_007595d0` response machine parity remains open.

## PC authority

```text
SHIFT.exe.c SHA-256
512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9

SHIFT.exe MD5
705af8b420e5eb1e3834ac43d5533c6b
```

The Xbox 360 recomp may be used to accelerate later structural searches, but
none of the positive claims in this slice depend on Xbox semantics.

## Caller input provenance

`FUN_00769ef0` supplies the two explicit arguments to `FUN_007682c0`.

The first is the f32 field at:

```text
HDVehicle + 0x4068
```

No physical name is assigned.

The second is a clamped load-like ratio formed from four f64 vehicle fields and
the chassis BODY value at `+0x120`:

```text
numerator =
    *(f64 *)(HDVehicle + 0x0b38) +
    *(f64 *)(HDVehicle + 0x15b8) +
    *(f64 *)(HDVehicle + 0x2038) +
    *(f64 *)(HDVehicle + 0x2ab8)

denominator = *(f64 *)(BODY0 + 0x120) * 9.81
param_2 = clamp(f32(numerator / denominator), 0, 1)
```

The existing BMW identity contract supplies the `HDVehicle+0x33a0 -> BODY0`
join used by this source window.

## `FUN_007682c0` machine magnitude

The PC function loads three f64 BODY motion lanes:

```text
BODY0 +0x78
BODY0 +0x80
BODY0 +0x88
```

It evaluates their squared magnitude on x87, calls `__CIsqrt`, then stores the
result to f32 at `0x00768305`. It subsequently evaluates `(speed-5)/15` and
stores that result to f32 at `0x0076832c` before the source clamp.

The PC helper at `0x00900d30` is no longer treated as an opaque CRT call. On the
positive path it checks/establishes x87 control word `0x027f` and executes:

```text
0x00900d6c  FSQRT
```

The native implementation therefore executes x87 `FSQRT` directly under the
same control word and restores the host control word afterwards.

## `FUN_0075ada0` planar magnitude

The geometry helper has additional f32 boundaries that a host-double shortcut
would lose:

```text
BODY0 +0x78 f64 -> f32 store at 0x0075adb5
BODY0 +0x88 f64 -> f32 store at 0x0075adbb
x^2+z^2         -> f32 store at 0x0075add7
__CIsqrt        -> FSQRT
sqrt result     -> f32 store at 0x0075ade2
```

The native regression includes a rounding witness for which the real checkpoint
path and `f32(std::sqrt(f64_x^2 + f64_z^2))` differ by one f32 ULP. This prevents
future simplification back to host-double magnitude arithmetic.

## `FUN_007595d0` inputs now explicit

The response helper reads:

```text
BODY0 +0x20   f64 -> f32
BODY0 +0x120  f64 -> f32
HDVehicle +0x4054 f32
```

and receives the following caller values:

```text
HDVehicle+0x4068
angle limit selected by DAT_00c128cc
FUN_007682c0 speed factor
1.0
0.5235988
1.0
FUN_0075ada0 reciprocal output (or 0)
```

This closes input provenance but does not yet claim exact response arithmetic.
The retail `FUN_007595d0` machine path contains many x87 stack operations and
explicit f32 store/reload checkpoints; source-level algebra alone is not enough
to close it.

## Native contract

```text
SHIFT.Fun007682c0MachineMagnitude/1
native_runtime/include/shift_fun_007682c0_machine_magnitude.hpp
native_runtime/src/fun_007682c0_machine_magnitude.cpp
```

Machine-readable frontier:

```text
SHIFT.Fun007682c0EffectInputMachineFrontier/1
evidence/fun_007682c0_effect_input_machine_frontier.json
```

## Remaining exact blocker

```text
FUN_007595d0 response x87/f32 parity
  -> exact response result before 0x007683c8 return consumption
  -> final response * param_2 f32 checkpoint at 0x007683d9
  -> source-proven runtime field wiring
  -> replace broad external FUN_007682c0 effect provider
```

No runtime capture or original-game execution is required for the work completed
in this slice.
