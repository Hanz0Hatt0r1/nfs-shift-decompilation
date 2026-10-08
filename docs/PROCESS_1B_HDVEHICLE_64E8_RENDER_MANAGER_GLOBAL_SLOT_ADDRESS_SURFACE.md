# Process 1B — render-manager global-slot address surface

## Scope

This slice checks whether retail code can reach the canonical render-manager slot `DAT_00bc185c` through a hidden fixed-address reconstruction rather than one of the already enumerated direct references.

## Raw occurrence partition

The whole PE contains exactly 115 little-endian occurrences of `0x00bc185c`. Machine classification accounts for all 115:

- 112 direct loads from `DAT_00bc185c`;
- 2 direct stores to `DAT_00bc185c`;
- 1 literal materialization of the slot address at `0x004fb9af`.

That one literal is immediately dereferenced before `outer+0x780` is derived, so it is an address-of-slot use, not an outer-root value literal.

## Bounded arithmetic reconstruction

A whole-text bounded scan covers 38,128 `mov r32,imm32` seeds and follows same-register immediate `add/sub` plus same-register `lea` for at most 15 instructions, stopping on calls, jumps, returns, or register overwrite.

It observes 267 arithmetic transitions. The only production of exact `0x00bc185c` is the known literal at `0x004fb9af`; there are zero non-literal productions.

## Adjudication

All raw fixed-address references to the canonical slot are classified, and the simple straight-line constant-arithmetic bypass is closed-negative.

This is deliberately not a global symbolic proof. Unknown-memory-derived addresses, opaque helper returns, external injection, and two-unknown-origin reconstruction remain open.

The manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion and provider removal remain fail-closed. Provider count remains 7.
