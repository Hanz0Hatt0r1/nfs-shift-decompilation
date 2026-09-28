# Phase 480 — unified specialized-provider reset domain

## Goal

Phase 480 centralizes reset storage-domain construction for the specialized providers.

The domain now includes **both** direct zero assignments and all 8-byte slots covered by reset `FUN_0040cec0` bulk-clears. Unit-diagonal `1.0` seeds are kept as a separate set.

## Canonical sets

`reset_zero`
— storage slots explicitly zeroed by reset, directly or through bulk clear.

`reset_unit`
— one exact `1.0` seed slot per reset selector case.

`reset_touched`
— union of `reset_zero` and `reset_unit`.

## Verified static counts

Provider 0: 410 reset-zero slots, 40 unit seeds, 410 touched slots.

Provider 1: 280 reset-zero slots, 34 unit seeds, 314 touched slots.

These values explain why provider 1 has 34 cleanup-only slots while still having 34 pivot unit seeds.

## Integration

Phase 469 reset-delta analysis and Phase 472 input-footprint analysis now consume this helper. Cleanup equality is reported separately and no longer decides whether reset-domain analysis is usable.

## Scope boundary

This is a storage-domain contract. It does not assign matrix coordinates, physical meaning, or provider class identity.
