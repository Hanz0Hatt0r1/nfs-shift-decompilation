# Phase 473 — specialized-provider solver ABI

## Goal

Phase 473 records the exact C-level entry shape of the two specialized provider solver functions and contrasts it with the builtin solver ABI.

## Specialized providers

Provider 0:

`void FUN_007c7200(void)`

Provider 1:

`void FUN_007cdfc0(void)`

Both functions use fixed global storage rather than explicit matrix/RHS arguments. The already recovered provider state regions are:

- row-pointer table;
- packed factor workspace;
- output vector.

## Builtin solver

The retail decompilation gives:

`void __thiscall FUN_007b0f20(void *this,int param_1,int param_2,int param_3)`

The runtime probe maps the stack positions to:

`this` → solver state,
`param_1` → row-pointer table,
`param_2` → RHS/solution vector,
`param_3` → scalar count.

## Capture implication

Builtin capture must decode solver arguments from the call stack. Provider capture must **not** attempt to decode matrix/RHS arguments from provider stack positions, because the provider solver itself is parameterless and operates on the fixed global state regions.

This distinction is now explicit in the ABI contract and aligns Phase 463's GDB hook with the actual source signature.

## Scope boundary

The ABI contract does not assign C++ provider class names or physical semantics. It only records function shape and state-location ownership already established by the earlier phases.
