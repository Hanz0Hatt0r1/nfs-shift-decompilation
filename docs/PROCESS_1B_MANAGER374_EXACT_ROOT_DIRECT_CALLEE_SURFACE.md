# Process 1B — manager+0x374 exact-root direct callee surface

## Scope

This slice follows the exact return value of `FUN_00489ad0` when it is transferred unchanged into `ECX` and immediately dispatched as a direct thiscall receiver. The PC retail 1.02 executable is authoritative; Ghidra SQLite is navigation/fingerprint support only.

## Result

The exact-root direct callee surface contains nine distinct callees. Eight immediately change receiver domain to `manager+0x2a0` and/or `manager+0x2d8` and do not write `manager+0x374`.

The only positive direct target writer is `FUN_00d60660` (entry thunk `0x00487240`). Its write at `0x00d606f3` stores the selected `manager+0x2a0` entry into `manager+0x374` after a successful `FUN_00485290` transition and the post-load entry-state check. The `manager+0x2a0` storage domain is already proven allocator-owned and disjoint from fixed global `HDVehicle+0x4330`.

The other direct targets are `FUN_00471ed0`, `FUN_0045b760`, `FUN_005083b0`, `FUN_004892c0`, `FUN_00d610c0`, `FUN_00d61310`, `FUN_00d61e00`, and `FUN_0040f290`. Their exact manager-root handling transitions into the `+0x2a0` or `+0x2d8` subobjects before descendant work; none directly writes `+0x374`.

## Adjudication

This closes direct thiscall-style exact-root forwarding as a source of `HDVehicle+0x4330` into `manager+0x374`. It does not close escaped forms where the getter result is stored, pushed as a stack argument, returned through another object, or reconstructed by another alias. Therefore the global manager join remains open, `0x004b86cf` remains fail-closed, and provider count stays 7.
