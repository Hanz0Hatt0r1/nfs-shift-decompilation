# Phase 466 — specialized-provider reset profile

## Goal

Phase 466 extracts the provider-specific reset helpers that initialize their packed solver workspaces before numerical execution.

## Provider 0

`FUN_007d3150` contains exactly 40 switch cases (`0..39`). Every case writes the IEEE-754 binary64 value `1.0` exactly once, and that address satisfies:

`diagonal = row_pointer[case] + 8*case`

The same cases also write a collection of related storage addresses to zero and, in later rows, perform bulk `FUN_0040cec0` clears. The extractor records these operations without assigning semantic matrix roles.

## Provider 1

`FUN_007d48a0` contains exactly 34 switch cases (`0..33`). Every case likewise writes one exact `1.0` seed, with the same diagonal geometry relative to the provider-1 row-pointer table.

## Why this matters

This gives the numerical capture pipeline a source-backed reset profile independent of the later provider solve. It distinguishes **reset-time initialization** from solve-time factor/update mutations measured by Phases 463–465.

## Important boundary

A unit-diagonal reset does not prove that the reset workspace is the solver's input matrix. Zeroed slots may serve staging, output, or intermediate purposes. The contract therefore records exact storage writes only and does not infer matrix semantics or physical units.

Run locally with:

    python specialized_provider_reset_profile_runtime.py SHIFT.exe.c
