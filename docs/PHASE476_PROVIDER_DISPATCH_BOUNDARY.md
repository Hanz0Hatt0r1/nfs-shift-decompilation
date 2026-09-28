# Phase 476 — specialized-provider dispatch boundary

## Goal

Phase 476 records the exact transition from provider selection to provider execution in the retail physics system.

## Selection: `FUN_007b3820`

Source line: 813669.

The function queries provider candidates through `FUN_007d2e70`, probes acceptance at vtable `+0x14`, and on acceptance stores the selected provider at `physics_system+0x48`.

It then rebinds:

`+0x0c → physics_system+0x3c`
`+0x04 → physics_system+0x40`
`+0x08 → physics_system+0x44`
`+0x2c → per-body +0xa8 workspace-size field`

## Execution: `FUN_007b3f40`

Source line: 814057.

When a provider is active, the order is:

`provider vtable +0x20 cleanup`
→ common BODY/constraint preparation
→ `FUN_007b2210(selector)` per active constraint scalar
→ provider `vtable +0x1c(selector)`
→ `provider vtable +0x18 solve`

When the provider pointer is null, the same orchestration reaches the builtin `FUN_007b0f20` path instead.

## Important lifecycle distinction

The provider reset function at vtable `+0x1c` is a selector-driven per-scalar reset. `FUN_007b2210` calls it for each active constraint scalar inside `FUN_007b3f40`. The provider `+0x20` cleanup remains a separate broader storage cleanup at the start of the frame solve path.

## Why this matters

This creates a precise runtime timeline for future captures:

`provider selection/rebind → cleanup → common/body preparation → per-scalar +0x1c reset dispatch → provider solve`

The Phase 463 GDB hook can now be correlated with this boundary: its solve breakpoint is the `+0x18` execution point, while Phase 464 observes the mutation caused by that call.

## Scope boundary

The common preparation functions are source identifiers only. Their internal semantics remain separate. No C++ provider class or physical matrix meaning is inferred.
