# Process 1B — manager+0x374 getter local alias surface

## Scope

This slice follows exact `FUN_00489ad0` return values that are saved immediately to stack locals instead of being dispatched directly through `ECX`. PC retail 1.02 machine transfer is authoritative; Ghidra SQLite is navigation/fingerprint support only.

## Result

There are no immediate `push eax` stack-argument forwards after the getter. Exactly two immediate local saves exist.

`FUN_0051dd30` stores the manager root into `[ebp-0x4]` at `0x0051dd44`. The only later use reloads that exact value into `ECX` at `0x0051dda0` and calls thunk `0x004893d0`, whose target `FUN_004d3760` immediately converts the receiver to `manager+0x2d8` at `0x004d3769`. It iterates that collection and compares participant-object `+0x100`; it does not write `manager+0x374`.

`FUN_0051e370` stores the getter result into `[ebp-0x8]` at `0x0051e3ae`. That local is loaded only at `0x0051e424` and `0x0051e473`. The first load reads `manager+0x2d4` and `manager+0x374`, using the selected object only to read `+0x100`. The second load reads `manager+0x2c4` and indexes `manager+0x2a0`. The alias is never written through and is not passed to another callee.

## Adjudication

Immediate getter-local storage and immediate getter stack-argument forwarding are closed-negative as sources of a new `manager+0x374` value. Delayed object-field storage, aliases reconstructed from another manager pointer, and aliases returned through unrelated APIs remain open. The final literal candidate `0x004b86cf` therefore remains fail-closed and provider count remains 7.
