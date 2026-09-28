# Phase 482 — scalar reset dispatcher

## Goal

Phase 482 isolates the exact scalar-reset function used by the frame solver orchestration.

## `FUN_007b2210`

Signature:

`void __thiscall FUN_007b2210(void *this,int param_1)`

`param_1` is the scalar selector supplied by the caller.

## Builtin path

When `physics_system+0x48 == 0`, the function:

1. clears every element in logical row `param_1`;
2. clears every element in logical column `param_1`;
3. writes `1.0` to the diagonal `[param_1][param_1]`;
4. clears RHS cell `param_1`.

## Provider path

When `physics_system+0x48 != 0`, the function performs one virtual call through provider vtable `+0x1c`, propagating `param_1` as the selector.

This directly connects the per-scalar frame reset to the provider reset functions decoded in Phases 475/480/481.

## Call topology

`FUN_007b3f40` contains three source call groups to `FUN_007b2210`:

- JOINT/HINGE group: width 3;
- second constraint group: width 2;
- BAR group: width 1.

The exact callsites are source lines 814124, 814138 and 814150.

## Lifecycle consequence

The frame path is now precisely:

`provider +0x20 cleanup`
→ common/body preparation
→ `FUN_007b2210(selector)` for each active constraint scalar
→ provider `+0x18` solve.

`+0x1c` reset is therefore a **per-scalar frame initialization hook** when a provider is selected, not a separate rare lifecycle API.

## Scope boundary

The phase does not assign a semantic matrix meaning to `param_1`, and it does not reconstruct the coefficient-producing logic surrounding these resets.
