# Phase 494 — live provider scalar-reset effect capture

## Goal

Phase 494 observes the provider reset functions directly at vtable `+0x1c` and records the minimal effect needed to validate each scalar reset.

Provider 0 reset entry: `FUN_007d3150`.

Provider 1 reset entry: `FUN_007d48a0`.

Both functions are `__thiscall` with selector at `[ESP+0x04]`.

## Captured sentinel cells

For selector `N` the probe reads:

`diagonal = row_pointer[N] + 8*N`

`output = output_vector_base + 8*N`

The entry snapshot stores both values before reset. A `gdb.FinishBreakpoint` captures the same cells after the provider reset returns.

## Validation

The runtime effect validator requires:

- exact provider vtable identity;
- selector inside the provider scalar domain;
- exact diagonal address;
- exact output address;
- post-reset diagonal value `1.0`;
- post-reset output value `0.0`.

A monotonic `reset_event_count` links the effect event back to the Phase 485 `FUN_007b2210` dispatch stream.

## Why this matters

Phases 485–493 reconstructed the selector dispatch, its caller group, event order and static storage footprint. Phase 494 now measures a real provider reset effect on live memory.

This is the first runtime check that directly validates the source-derived `selector → reset case → storage sentinel` chain.

## Scope boundary

The probe captures only two sentinel cells, not the complete reset case footprint. A successful sentinel check therefore validates the central reset effect without claiming every case-local zero write was observed.