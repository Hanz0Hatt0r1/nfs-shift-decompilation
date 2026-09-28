# Phase 477 — exact provider execution sequence

## Goal

Phase 477 turns the source body of `FUN_007b3f40` into a machine-readable execution sequence with the exact branch boundary, call order, count fields, and strides.

## Exact order

1. Backend branch on `physics_system+0x48`.
   - provider active → vtable `+0x20` cleanup;
   - builtin → inline zeroing of matrix rows and RHS.
2. `FUN_007b3ed0` common preparation.
3. `FUN_007bb8d0` for each BODY: count `+0x10`, base `+0x14`, stride `0x170`.
4. `FUN_007bc680` for each BODY: same count/base/stride.
5. `FUN_007ba570` for each BODY: same body geometry plus `physics_system+0x40/+0x44` arguments.
6. JOINT/HINGE scalar accumulation through `FUN_007b2210`, count `+0x18`, base `+0x1c`, stride `0xa0`; width 3 when the record flag has bit 0 set.
7. Second `FUN_007b2210` loop for HINGE/BAR-type records at `+0x24`, count `+0x20`, stride `0xa0`; width 2 when the record flag has bit 0 set.
8. BAR accumulation through `FUN_007b2210`, count `+0x28`, base `+0x2c`, stride `0xb8`; width 1 when the record flag has bit 0 set.
9. Final backend dispatch:
   - provider active → vtable `+0x18` solve;
   - otherwise → `FUN_007b0f20(physics_system+0x4c, physics_system+0x3c, physics_system+0x40, physics_system+0x34)`.

## Why this matters

The sequence establishes the precise point at which the provider sees caller-populated state: after common body/constraint preparation and immediately before the provider `+0x18` solve.

This aligns directly with the Phase 463 provider GDB capture hook.

## Scope boundary

`FUN_007b2210` is represented only by call topology and source-derived width. Its scalar coefficient formulas remain a separate reconstruction task. The common preparation functions are likewise kept as opaque source identifiers.

No provider class identity, matrix semantic, or physical unit is inferred.
