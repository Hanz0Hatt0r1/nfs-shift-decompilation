# Phase 475 — specialized-provider reset ABI

## Goal

Phase 475 decodes the callable ABI behind vtable slot `+0x1c` for both specialized providers.

## Exact signatures

Provider 0:

`void FUN_007d3150(undefined4 param_1)`

Provider 1:

`void FUN_007d48a0(undefined4 param_1)`

Both functions immediately dispatch `param_1` through a `switch`.

## Selector domains

Provider 0 contains exactly cases `0..39`.

Provider 1 contains exactly cases `0..33`.

No `default` case is present in either reset function.

The case number selects the corresponding reset block. Earlier phases established that each block writes one exact `1.0` seed at `row_pointer[case] + 8*case` and clears its associated storage slots.

## Vtable relation

Both provider vtables place the reset function at `+0x1c`. Therefore the lifecycle surface is now:

`vtable +0x1c(selector) → reset case → storage initialization`

This is stronger than treating reset as an opaque helper because the selector domain and dispatch shape are now proven.

## Interpretation boundary

The selector is recorded as an opaque 32-bit parameter. Although its values align one-for-one with recovered pivot indices and diagonal seeds, the phase does not rename the selector semantically.

No C++ class hierarchy, physical units, or matrix ownership are inferred.
