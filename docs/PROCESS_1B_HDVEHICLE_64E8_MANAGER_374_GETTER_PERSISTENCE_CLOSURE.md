# Process 1B — Participants Manager getter persistence closure

## Scope

This slice completes exact `FUN_00489ad0` return-value persistence after the immediate local/register and delayed GPR→stack surfaces were bounded separately. PC retail 1.02 machine transfer is authoritative; the Ghidra SQLite export is navigation-only.

## Result

The whole retail image contains 394 direct calls to `FUN_00489ad0`. Exact-root alias tracking finds nine stack saves and zero object-field or absolute-global stores of the live getter result.

Six stack saves are already covered by the merged/green getter-local and delayed GPR→stack contracts. The remaining three delayed EAX→stack cases are:

- `FUN_00460c80`: `0x00460df2 -> [ebp-0xc]` at `0x00460e01`; reload at `0x00460ef9` is used only for `+0x2fc/+0x2d8` loop access.
- `FUN_00498b80`: `0x00498c63 -> [ebp-0x4]` at `0x00498c72`; reload at `0x00498ce4` is used only for `+0x2c4/+0x2a0` entry lookup.
- `FUN_00499de0`: `0x0049a0ea -> [ebp-0xc]` at `0x0049a0f6`; reload at `0x0049a16f` is forwarded to `FUN_004939e0 -> FUN_0040f290`, which immediately transitions to `manager+0x2a0` iteration and does not write manager `+0x374`.

No exact getter-result alias is persisted into an object field or absolute global.

## Adjudication

Exact getter-result persistence through registers, stack locals, object fields and globals is closed-negative for creating a new manager `+0x374` value. Arithmetic/non-immediate reconstruction of the singleton root remains open. The `0x004b86cf` literal candidate therefore remains fail-closed and provider count remains 7.
